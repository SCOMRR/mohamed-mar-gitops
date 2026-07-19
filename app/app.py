import os
import socket
from flask import Flask, jsonify
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
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
