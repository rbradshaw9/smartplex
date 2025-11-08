#!/bin/bash
set -e

echo "Starting SmartPlex API..."
echo "PORT: ${PORT:-8080}"
echo "PYTHONPATH: ${PYTHONPATH:-/app}"

# Run the FastAPI application
exec poetry run uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}" --log-level info