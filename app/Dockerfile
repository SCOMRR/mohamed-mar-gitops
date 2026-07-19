FROM python:3.12-slim

LABEL maintainer="Mohamed MAR"
LABEL app="mohamed-mar-gitops-app"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Utilisateur non-root (bonne pratique sécurité)
RUN useradd -m appuser
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz')" || exit 1

CMD ["python", "app.py"]
