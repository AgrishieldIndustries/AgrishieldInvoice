#!/bin/bash
set -e

echo "==> Environment variables present:"
env | cut -d= -f1 | sort

echo "==> Running database migrations..."
alembic upgrade head

echo "==> Seeding database (skips if already seeded)..."
python -m app.seed

echo "==> Starting Agrishield API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
