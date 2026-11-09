import json
import logging
import os
import sys
import threading
import time
import uuid
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv
from flask import Flask, jsonify, request
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
        # Ensure level is always present
        if 'level' not in log_record:
            log_record['level'] = record.levelname

# Configura o logger raiz com JSON formatter
handler = logging.StreamHandler()
handler.setFormatter(OpenTelemetryJsonFormatter(
    '%(timestamp)s %(levelname)s %(name)s %(message)s',
    timestamp=True
))
root_logger = logging.getLogger()
root_logger.handlers = [handler]
root_logger.setLevel(logging.INFO)

# Configure gunicorn loggers to use our handler
for logger_name in ['gunicorn', 'gunicorn.access', 'gunicorn.error']:
    gunicorn_logger = logging.getLogger(logger_name)
    gunicorn_logger.handlers = [handler]
    gunicorn_logger.setLevel(logging.INFO)
    gunicorn_logger.propagate = False

log = logging.getLogger(__name__)

# Carrega .env para desenvolvimento local
load_dotenv()

# --- Configuração ---
AWS_REGION = os.getenv("AWS_REGION")
SQS_QUEUE_URL = os.getenv("AWS_SQS_URL")
SQS_ENDPOINT = os.getenv("AWS_SQS_ENDPOINT")
DYNAMODB_TABLE_NAME = os.getenv("AWS_DYNAMODB_TABLE")
DYNAMODB_ENDPOINT = os.getenv("AWS_DYNAMODB_ENDPOINT")
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or os.getenv("OTEL_ENDPOINT")

if not all([AWS_REGION, SQS_QUEUE_URL, DYNAMODB_TABLE_NAME]):
    log.critical("Erro: AWS_REGION, AWS_SQS_URL, e AWS_DYNAMODB_TABLE devem ser definidos.")
    sys.exit(1)

# --- Clientes Boto3 ---
# Criamos a sessão uma vez
try:
    session = boto3.Session(region_name=AWS_REGION)
    dynamodb_kwargs = {"region_name": AWS_REGION}
    sqs_kwargs = {"region_name": AWS_REGION}
    if SQS_ENDPOINT:
        sqs_kwargs["endpoint_url"] = SQS_ENDPOINT
    sqs_client = session.client("sqs", **sqs_kwargs)
    if DYNAMODB_ENDPOINT:
        dynamodb_kwargs["endpoint_url"] = DYNAMODB_ENDPOINT
    dynamodb_client = session.client("dynamodb", **dynamodb_kwargs)
    log.info(f"Clientes Boto3 inicializados na região {AWS_REGION}")
except NoCredentialsError:
    log.critical("Credenciais da AWS não encontradas. Verifique seu ambiente.")
    sys.exit(1)
except ClientError as e:
    log.critical(f"Erro ao inicializar o Boto3: {e}")
    sys.exit(1)
    

# --- SQS Worker ---

def process_message(message):
    """ Processa uma única mensagem SQS e a insere no DynamoDB """
    try:
        log.info(f"Processando mensagem ID: {message['MessageId']}")
        body = json.loads(message['Body'])
        
        # Gera um ID único para o item no DynamoDB
        event_id = str(uuid.uuid4())
        
        # Constrói o item no formato do DynamoDB
        item = {
            'event_id': {'S': event_id},
            'user_id': {'S': body['user_id']},
            'flag_name': {'S': body['flag_name']},
            'result': {'BOOL': body['result']},
            'timestamp': {'S': body['timestamp']}
        }
        
        # Insere no DynamoDB
        dynamodb_client.put_item(
            TableName=DYNAMODB_TABLE_NAME,
            Item=item
        )
        
        log.info(f"Evento {event_id} (Flag: {body['flag_name']}) salvo no DynamoDB.")
        
        # Se tudo deu certo, deleta a mensagem da fila
        sqs_client.delete_message(
            QueueUrl=SQS_QUEUE_URL,
            ReceiptHandle=message['ReceiptHandle']
        )
        
    except json.JSONDecodeError:
        log.error(f"Erro ao decodificar JSON da mensagem ID: {message['MessageId']}")
        # Não deleta a mensagem, pode ser uma "poison pill"
    except ClientError as e:
        log.error(f"Erro do Boto3 (DynamoDB ou SQS) ao processar {message['MessageId']}: {e}")
        # Não deleta a mensagem, tenta novamente
    except (KeyError, TypeError) as e:
        log.error(f"Erro inesperado ao processar {message['MessageId']}: {e}")
        # Não deleta a mensagem, tenta novamente

def sqs_worker_loop():
    """ Loop principal do worker que ouve a fila SQS """
    log.info("Iniciando o worker SQS...")
    while True:
        try:
            # Long-polling: espera até 20s por mensagens
            response = sqs_client.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=10,  # Processa em lotes de até 10
                WaitTimeSeconds=20
            )
            
            messages = response.get('Messages', [])
            if not messages:
                # Nenhuma mensagem, continua o loop
                continue
                
            log.info(f"Recebidas {len(messages)} mensagens.")
            
            for message in messages:
                process_message(message)
                
        except (ClientError, ConnectionError) as e:
            log.error(f"Erro inesperado no loop principal do SQS: {e}")
            time.sleep(10)

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

        _resource = Resource.create({"service.name": "analytics-service"})
        _tracer_provider = TracerProvider(resource=_resource)
        _tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT.rstrip('/')}/v1/traces")))
        trace.set_tracer_provider(_tracer_provider)

        _metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=f"{OTEL_ENDPOINT.rstrip('/')}/v1/metrics"))
        _meter_provider = MeterProvider(resource=_resource, metric_readers=[_metric_reader])
        metrics.set_meter_provider(_meter_provider)
        _otel_enabled = True
        log.info(f"OpenTelemetry habilitado, exportando para {OTEL_ENDPOINT}")
    except Exception as e:  # noqa: BLE001
        log.warning(f"Falha ao inicializar OpenTelemetry: {e}")

# --- Servidor Flask (Apenas para Health Check) ---

from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
PrometheusMetrics(app, path="/metrics")

if _otel_enabled:
    try:
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        FlaskInstrumentor().instrument_app(app)
    except Exception as e:  # noqa: BLE001
        log.warning(f"Falha ao instrumentar Flask: {e}")

# --- HTTP Request Logging Middleware ---
@app.before_request
def log_request_start():
    request._start_time = time.time()

@app.after_request
def log_request_end(response):
    if hasattr(request, '_start_time'):
        duration_ms = (time.time() - request._start_time) * 1000
        log.info("HTTP request",
            extra={
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 2),
            }
        )
    return response

@app.route('/health')
def health():
    # Uma verificação de saúde real poderia checar a conexão com o DynamoDB/SQS
    return jsonify({"status": "ok"})

# --- Inicialização ---

def start_worker():
    """ Inicia o worker SQS em uma thread separada """
    worker_thread = threading.Thread(target=sqs_worker_loop, daemon=True)
    worker_thread.start()

# Inicia o worker SQS em uma thread de background
# Isso garante que ele inicie tanto com 'flask run' quanto com 'gunicorn'
start_worker()

if __name__ == '__main__':
    port = int(os.getenv("PORT", "8005"))
    app.run(host='0.0.0.0', port=port, debug=False)