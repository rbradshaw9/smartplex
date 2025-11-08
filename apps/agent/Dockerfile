# SmartPlex Agent Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        procps \
        htop \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Configure Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Copy Poetry files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry install --only=main && rm -rf $POETRY_CACHE_DIR

# Copy application code
COPY app/ ./app/

# Create non-root user (with access to system monitoring)
RUN adduser --disabled-password --gecos '' agentuser
RUN usermod -aG users agentuser
RUN chown -R agentuser:agentuser /app

# Create volume mount points for Plex data
RUN mkdir -p /data/media /data/config /data/logs
RUN chown -R agentuser:agentuser /data

USER agentuser

# Health check
HEALTHCHECK --interval=60s --timeout=15s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:9000/health/ || exit 1

# Expose port
EXPOSE 9000

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default environment for agent
ENV PLEX_URL=http://host.docker.internal:32400
ENV PLEX_LIBRARY_PATHS=/data/media
ENV SMARTPLEX_API_URL=http://host.docker.internal:8000
ENV AGENT_ID=agent-docker

# Run the agent
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]