# Stage 1: Build frontend
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2: Python backend + built frontend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy built frontend from stage 1
COPY --from=frontend-build /frontend/dist /app/frontend/dist

# Default env vars (overridden by Azure/Railway environment variables)
ENV ALLOWED_ORIGINS=*
ENV DEBUG=False
ENV PORT=8080

EXPOSE ${PORT}

# Start server with debug output
COPY backend/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Run as non-root user
RUN addgroup --system --gid 1001 sira && \
    adduser --system --uid 1001 --gid 1001 --no-create-home sira && \
    chown -R sira:sira /app
USER sira

CMD ["/bin/sh", "/app/start.sh"]
