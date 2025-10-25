#!/bin/bash
set -e

echo "Starting Translation Worker..."
echo "Worker ID: ${WORKER_ID:-translation-$RANDOM}"
echo "Redis URL: ${REDIS_URL:-redis://localhost:6379}"
echo "Use Stub Translation: ${USE_STUB_TRANSLATION:-true}"
echo "Health Port: ${HEALTH_PORT:-8082}"

# Wait for Redis to be ready
if [ -n "${REDIS_URL}" ]; then
    echo "Waiting for Redis..."
    while ! nc -z redis 6379; do
        sleep 1
    done
    echo "Redis is ready!"
fi

# Export worker ID if not set
export WORKER_ID=${WORKER_ID:-translation-$RANDOM}

exec python worker.py

