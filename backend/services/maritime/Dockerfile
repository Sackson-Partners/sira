# SIRA Maritime Worker — MarineTraffic AIS Polling Service
# Deployed to Azure Container Apps (sira-rg) — cron-based scaling

FROM python:3.12-slim AS base
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
        && rm -rf /var/lib/apt/lists/*

        COPY requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt

        COPY app/ ./app/
        COPY services/maritime/ ./services/maritime/

        RUN adduser --system --no-create-home sira && chown -R sira /app
        USER sira

        HEALTHCHECK --interval=60s --timeout=15s --start-period=30s --retries=3 \
            CMD curl -f http://localhost:8001/health || exit 1

            CMD ["python", "-m", "services.maritime.poller"]
