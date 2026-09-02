#!/bin/sh
set -e

# Wait for postgres if needed or run migrations
echo "[MediAI] Running database migrations..."
alembic upgrade head || {
    echo "[MediAI] Warning: Alembic upgrade encountered an issue or database is already up to date."
}

echo "[MediAI] Starting application server..."
exec "$@"
