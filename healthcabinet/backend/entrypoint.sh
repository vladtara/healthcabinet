#!/bin/sh
set -e

echo "Running database migrations..."
alembic -c alembic/alembic.ini upgrade head
echo "Migrations complete."

echo "Starting server..."
if [ "${UVICORN_RELOAD:-false}" = "true" ]; then
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
