#!/bin/bash
set -e

echo "Starting Translation Worker..."
echo "Worker ID: ${WORKER_ID:-translation-$RANDOM}"
echo "Redis URL: ${REDIS_URL:-redis://localhost:6379}"
echo "NLLB Model: ${NLLB_MODEL:-facebook/nllb-200-distilled-600M}"
echo "Force CPU: ${FORCE_CPU:-false}"
echo "Health Port: ${HEALTH_PORT_TRANSLATION:-8082}"

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

