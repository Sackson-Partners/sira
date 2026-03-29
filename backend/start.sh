#!/bin/sh
echo "=== SIRA Platform Startup ==="
echo "PORT=${PORT:-8080}"
echo "DATABASE_URL prefix: $(echo $DATABASE_URL | head -c 30)..."
echo "Working dir: $(pwd)"

# Run database migrations (idempotent — safe to run on every startup)
if [ -n "$DATABASE_URL" ] && [ "$DATABASE_URL" != "sqlite:///./sira.db" ]; then
    echo "=== Running database migrations ==="
    python -m alembic upgrade head
    if [ $? -ne 0 ]; then
        echo "ERROR: Migration failed — aborting startup"
        exit 1
    fi
    echo "=== Migrations complete ==="
fi

echo "=== Starting uvicorn ==="
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
