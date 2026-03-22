#!/bin/sh
echo "=== SIRA Platform Startup ==="
echo "PORT=${PORT:-8080}"
echo "DATABASE_URL prefix: $(echo $DATABASE_URL | head -c 30)..."
echo "Working dir: $(pwd)"
echo "Files: $(ls -la app/main.py 2>&1)"
echo "Frontend: $(ls -la frontend/dist/index.html 2>&1)"
echo "=== Starting uvicorn ==="
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
