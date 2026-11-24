#!/bin/sh
# Migrate, seed the Egypt demo trip (idempotent), then serve.
set -e
alembic upgrade head
python scripts/seed_egypt.py
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
