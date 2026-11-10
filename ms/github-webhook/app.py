import logging
import os
import sys
from typing import Any

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from prometheus_flask_exporter import PrometheusMetrics
from pythonjsonlogger import jsonlogger


# Configura o logging estruturado JSON com trace_id do OpenTelemetry
class OpenTelemetryJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record: dict[str, Any], record: logging.LogRecord, message_dict: dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
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
            pass
        if 'level' not in log_record:
            log_record['level'] = record.levelname


handler = logging.StreamHandler()
handler.setFormatter(OpenTelemetryJsonFormatter(
    '%(timestamp)s %(levelname)s %(name)s %(message)s',
    timestamp=True
))
root_logger = logging.getLogger()
root_logger.handlers = [handler]
root_logger.setLevel(logging.INFO)

for logger_name in ['gunicorn', 'gunicorn.access', 'gunicorn.error']:
    gunicorn_logger = logging.getLogger(logger_name)
    gunicorn_logger.handlers = [handler]
    gunicorn_logger.setLevel(logging.INFO)
    gunicorn_logger.propagate = False

log = logging.getLogger(__name__)

# Carrega .env para desenvolvimento local
load_dotenv()

# --- Configuração ---
PORT = int(os.getenv("PORT", "8080"))
GH_TOKEN = os.getenv("GH_PAT")
GH_REPO = os.getenv("GH_REPO", "rmvinicius/fiap-phase4")
EVENT_TYPE = os.getenv("EVENT_TYPE", "fiap-5xx-alert")

OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or os.getenv("OTEL_ENDPOINT")

if not GH_TOKEN:
    log.critical("Erro: GH_PAT deve ser definido.")
    sys.exit(1)

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

        _resource = Resource.create({"service.name": "github-webhook"})
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

# --- Servidor Flask ---
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
    request._start_time = __import__('time').time()


@app.after_request
def log_request_end(response):
    if hasattr(request, '_start_time'):
        import time
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
    return jsonify({"status": "ok"})


@app.route('/webhook', methods=['POST'])
def webhook():
    """Recebe webhook do Grafana/Alertmanager e dispara repository_dispatch no GitHub Actions."""
    data = request.get_json(force=True, silent=True) or {}

    # Apenas alertas em estado firing disparam a automação
    if data.get("status") != "firing":
        log.info(f"Ignorando webhook com status: {data.get('status')}")
        return jsonify({"ignored": True, "status": data.get("status")}), 200

    labels = data.get("commonLabels", {})
    annotations = data.get("commonAnnotations", {})

    service = labels.get("service", "auth-service")
    namespace = labels.get("namespace", "application")
    alertname = labels.get("alertname", "High5xxErrorRate")

    log.info(f"Webhook recebido: alert={alertname} service={service} namespace={namespace}")

    url = f"https://api.github.com/repos/{GH_REPO}/dispatches"
    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json"
    }
    body = {
        "event_type": EVENT_TYPE,
        "client_payload": {
            "service": service,
            "namespace": namespace,
            "alertname": alertname,
            "status": data.get("status", ""),
            "summary": annotations.get("summary", ""),
            "description": annotations.get("description", "")
        }
    }

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=10)
        log.info(f"GitHub dispatch enviado: status={resp.status_code} body={resp.text}")
        if resp.status_code in (200, 201, 202, 204):
            return jsonify({"dispatched": True, "github_status": resp.status_code}), 200
        return jsonify({"dispatched": False, "github_status": resp.status_code, "error": resp.text}), resp.status_code
    except requests.RequestException as e:
        log.error(f"Erro ao enviar dispatch para o GitHub: {e}")
        return jsonify({"dispatched": False, "error": str(e)}), 502


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)
