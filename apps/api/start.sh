#!/bin/bash
set -e

echo "Starting SmartPlex API..."
echo "PORT: ${PORT:-8080}"
echo "Working directory: $(pwd)"
echo "PYTHONPATH: ${PYTHONPATH:-/app}"

# Run the FastAPI application from the app directory
cd /app/apps/api || cd .
exec poetry run uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}" --log-level info