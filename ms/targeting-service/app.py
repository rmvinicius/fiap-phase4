import logging
import os
import sys
from functools import wraps
from typing import Any

import psycopg2
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from prometheus_flask_exporter import PrometheusMetrics
from psycopg2.extras import Json, RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from pythonjsonlogger import jsonlogger

# Configura o logging estruturado JSON com trace_id do OpenTelemetry
class OpenTelemetryJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record: dict[str, Any], record: logging.LogRecord, message_dict: dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        # Adiciona trace_id e span_id do contexto OpenTelemetry
        try:
            from opentelemetry import trace
            span = trace.get_current_span()
            if span and span.get_span_context():
                ctx = span.get_span_context()
                if ctx.trace_id:
                    log_record['trace_id'] = format(ctx.trace_id, '032x')
                if ctx.span_id:
                    log_record['span_id'] = format(ctx.span_id, '016x')
        except (ImportError, AttributeError):
            # OpenTelemetry not available or span context not accessible
            pass

# Configura o logger raiz com JSON formatter
handler = logging.StreamHandler()
handler.setFormatter(OpenTelemetryJsonFormatter(
    '%(timestamp)s %(level)s %(name)s %(message)s',
    timestamp=True
))
root_logger = logging.getLogger()
root_logger.handlers = [handler]
root_logger.setLevel(logging.INFO)

log = logging.getLogger(__name__)

# Carrega .env para desenvolvimento local
load_dotenv() 

OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or os.getenv("OTEL_ENDPOINT")

# --- OpenTelemetry ---
_otel_enabled = False
if OTEL_ENDPOINT:
    try:
        from opentelemetry import metrics, trace
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        _resource = Resource.create({"service.name": "targeting-service"})
        _tracer_provider = TracerProvider(resource=_resource)
        _tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT.rstrip('/') }/v1/traces")))
        trace.set_tracer_provider(_tracer_provider)

        _metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=f"{OTEL_ENDPOINT.rstrip('/') }/v1/metrics"))
        _meter_provider = MeterProvider(resource=_resource, metric_readers=[_metric_reader])
        metrics.set_meter_provider(_meter_provider)
        _otel_enabled = True
        log.info(f"OpenTelemetry habilitado, exportando para {OTEL_ENDPOINT}")
    except Exception as e:  # noqa: BLE001
        log.warning(f"Falha ao inicializar OpenTelemetry: {e}")

app = Flask(__name__)
PrometheusMetrics(app, path="/metrics")

if _otel_enabled:
    try:
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        FlaskInstrumentor().instrument_app(app)
    except Exception as e:  # noqa: BLE001
        log.warning(f"Falha ao instrumentar Flask: {e}")

# --- Configuração ---
DATABASE_URL = os.getenv("DATABASE_URL")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL")

if not DATABASE_URL or not AUTH_SERVICE_URL:
    log.critical("Erro: DATABASE_URL e AUTH_SERVICE_URL devem ser definidos.")
    sys.exit(1)

# --- Pool de Conexão com o Banco ---
try:
    pool = SimpleConnectionPool(1, 5, dsn=DATABASE_URL)
    log.info("Pool de conexões com o PostgreSQL (targeting) inicializado.")
except psycopg2.OperationalError as e:
    log.critical(f"Erro fatal ao conectar ao PostgreSQL: {e}")
    sys.exit(1)

# --- Middleware de Autenticação (Idêntico ao flag-service) ---
def require_auth(f):
    """ Middleware para validar a chave de API contra o auth-service """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Authorization header obrigatório"}), 401
        
        try:
            validate_url = f"{AUTH_SERVICE_URL}/validate"
            response = requests.get(validate_url, headers={"Authorization": auth_header}, timeout=3)
            
            if response.status_code != 200:
                log.warning(f"Falha na validação da chave (status: {response.status_code})")
                return jsonify({"error": "Chave de API inválida"}), 401
        
        except requests.exceptions.Timeout:
            log.error("Timeout ao conectar com o auth-service")
            return jsonify({"error": "Serviço de autenticação indisponível (timeout)"}), 504 # Gateway Timeout
        except requests.exceptions.RequestException as e:
            log.error(f"Erro ao conectar com o auth-service: {e}")
            return jsonify({"error": "Serviço de autenticação indisponível"}), 503 # Service Unavailable

        return f(*args, **kwargs)
    return decorated

# --- Endpoints da API ---

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/rules', methods=['POST'])
@require_auth
def create_rule():
    """ Cria uma nova regra de segmentação para uma flag """
    data = request.get_json()
    if not data or 'flag_name' not in data or 'rules' not in data:
        return jsonify({"error": "'flag_name' e 'rules' (JSON) são obrigatórios"}), 400
    
    flag_name = data['flag_name']
    rules_obj = data['rules'] # O objeto JSON
    is_enabled = data.get('is_enabled', True)
    
    conn = None
    cur = None
    try:
        conn = pool.getconn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "INSERT INTO targeting_rules (flag_name, is_enabled, rules, created_at, updated_at) "
            "VALUES (%s, %s, %s, NOW(), NOW()) RETURNING *",
            (flag_name, is_enabled, Json(rules_obj)) # Usa Json() para serializar
        )
        new_rule = cur.fetchone()
        conn.commit()
        log.info(f"Regra para '{flag_name}' criada com sucesso.")
        return jsonify(new_rule), 201
    except psycopg2.IntegrityError:
        if conn: conn.rollback()
        log.warning(f"Tentativa de criar regra duplicada: '{flag_name}'")
        return jsonify({"error": f"Regra para a flag '{flag_name}' já existe"}), 409
    except psycopg2.Error as e:
        if conn: conn.rollback()
        log.error(f"Erro ao criar regra: {e}")
        return jsonify({"error": "Erro interno do servidor", "details": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: pool.putconn(conn)

@app.route('/rules/<string:flag_name>', methods=['GET'])
@require_auth
def get_rule(flag_name):
    """ Busca uma regra de segmentação pelo nome da flag """
    conn = None
    cur = None
    try:
        conn = pool.getconn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM targeting_rules WHERE flag_name = %s", (flag_name,))
        rule = cur.fetchone()
        if not rule:
            return jsonify({"error": "Regra não encontrada"}), 404
        return jsonify(rule)
    except psycopg2.Error as e:
        log.error(f"Erro ao buscar regra '{flag_name}': {e}")
        return jsonify({"error": "Erro interno do servidor", "details": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: pool.putconn(conn)

@app.route('/rules/<string:flag_name>', methods=['PUT'])
@require_auth
def update_rule(flag_name):
    """ Atualiza a regra de segmentação de uma flag """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Corpo da requisição obrigatório"}), 400

    fields = []
    values = []
    
    if 'rules' in data:
        fields.append("rules = %s")
        values.append(Json(data['rules'])) # Serializa o JSON
    if 'is_enabled' in data:
        fields.append("is_enabled = %s")
        values.append(data['is_enabled'])
    
    if not fields:
        return jsonify({"error": "Pelo menos um campo ('rules', 'is_enabled') é obrigatório"}), 400
    
    values.append(flag_name) # Adiciona o 'flag_name' para a cláusula WHERE
    
    query = f"UPDATE targeting_rules SET {', '.join(fields)} WHERE flag_name = %s RETURNING *"
    
    conn = None
    cur = None
    try:
        conn = pool.getconn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, tuple(values))
        
        if cur.rowcount == 0:
            return jsonify({"error": "Regra não encontrada"}), 404
            
        updated_rule = cur.fetchone()
        conn.commit()
        log.info(f"Regra para '{flag_name}' atualizada com sucesso.")
        return jsonify(updated_rule), 200
    except psycopg2.Error as e:
        if conn: conn.rollback()
        log.error(f"Erro ao atualizar regra '{flag_name}': {e}")
        return jsonify({"error": "Erro interno do servidor", "details": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: pool.putconn(conn)

@app.route('/rules/<string:flag_name>', methods=['DELETE'])
@require_auth
def delete_rule(flag_name):
    """ Deleta a regra de segmentação de uma flag """
    conn = None
    cur = None
    try:
        conn = pool.getconn()
        cur = conn.cursor()
        cur.execute("DELETE FROM targeting_rules WHERE flag_name = %s", (flag_name,))
        
        if cur.rowcount == 0:
            return jsonify({"error": "Regra não encontrada"}), 404
            
        conn.commit()
        log.info(f"Regra para '{flag_name}' deletada com sucesso.")
        return "", 204 # 204 No Content
    except psycopg2.Error as e:
        if conn: conn.rollback()
        log.error(f"Erro ao deletar regra '{flag_name}': {e}")
        return jsonify({"error": "Erro interno do servidor", "details": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: pool.putconn(conn)

if __name__ == '__main__':
    port = int(os.getenv("PORT", "8003"))
    app.run(host='0.0.0.0', port=port, debug=False)