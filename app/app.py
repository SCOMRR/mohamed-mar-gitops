import os
import socket
from flask import Flask, jsonify
from prometheus_flask_exporter import PrometheusMetrics

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.flask import FlaskInstrumentor

resource = Resource.create({"service.name": "mohamed-mar-app"})
provider = TracerProvider(resource=resource)
otlp_exporter = OTLPSpanExporter(
    endpoint="otel-collector.mohamed-mar.svc.cluster.local:4317",
    insecure=True
)
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(provider)

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
metrics = PrometheusMetrics(app)  # expose /metrics automatiquement

STUDENT = "Mohamed-MAR"
VERSION = os.environ.get("APP_VERSION", "dev")
metrics.info("app_info", "Application info", student=STUDENT, version=VERSION)

@app.route("/")
def home():
    return f"""
    <html>
      <head><title>{STUDENT} - GitOps Platform</title></head>
      <body style="font-family: sans-serif; text-align:center; margin-top: 10%;">
        <h1>👋 {STUDENT}</h1>
        <h3>Plateforme GitOps observable sur Kubernetes</h3>
        <p>Version: {VERSION}</p>
        <p>Pod: {socket.gethostname()}</p>
      </body>
    </html>
    """

@app.route("/healthz")
def health():
    return jsonify(status="ok", student=STUDENT), 200

@app.route("/api/info")
def info():
    return jsonify(
        student=STUDENT,
        version=VERSION,
        hostname=socket.gethostname()
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)