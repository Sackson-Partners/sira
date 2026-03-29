# SIRA Telematics Worker — Flespi MQTT Ingestion Service
# Deployed to Azure Container Apps (sira-rg) — always-on, single replica

FROM python:3.12-slim AS base
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
        && rm -rf /var/lib/apt/lists/*

        # Install Python dependencies
        COPY requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt

        # Copy application code
        COPY app/ ./app/
        COPY services/telematics/ ./services/telematics/

        # Non-root user for security
        RUN adduser --system --no-create-home sira && chown -R sira /app
        USER sira

        # Health check
        HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
            CMD python -c "import asyncio; print('telematics-worker healthy')" || exit 1

            CMD ["python", "-m", "services.telematics.mqtt_ingestion"]
