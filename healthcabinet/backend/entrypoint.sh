#!/bin/sh
set -e

echo "Running database migrations..."
/app/.venv/bin/alembic -c alembic/alembic.ini upgrade head
echo "Migrations complete."

echo "Starting server..."
if [ "${UVICORN_RELOAD:-false}" = "true" ]; then
  exec /app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi

exec /app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
