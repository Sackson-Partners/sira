# SIRA AI Worker — Intelligence Engine (Claude API / OpenAI)
# Deployed to Azure Container Apps (sira-rg) — scales on queue depth

FROM python:3.12-slim AS base
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
        && rm -rf /var/lib/apt/lists/*

        COPY requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt

        COPY app/ ./app/
        COPY services/ai/ ./services/ai/

        RUN adduser --system --no-create-home sira && chown -R sira /app
        USER sira

        HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
            CMD python -c "import anthropic; print('ai-worker healthy')" || exit 1

            CMD ["python", "-m", "services.ai.worker"]
