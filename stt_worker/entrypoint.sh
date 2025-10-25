#!/bin/bash
set -e

echo "Starting STT Worker..."
echo "Worker ID: ${WORKER_ID:-stt-$RANDOM}"
echo "Redis URL: ${REDIS_URL:-redis://localhost:6379}"
echo "Model Size: ${MODEL_SIZE:-base}"
echo "Device: ${DEVICE:-auto}"
echo "Max Batch Size: ${MAX_BATCH_SIZE:-4}"
echo "Health Port: ${HEALTH_PORT:-8081}"

# Wait for Redis to be ready
if [ -n "${REDIS_URL}" ]; then
    echo "Waiting for Redis..."
    while ! nc -z redis 6379; do
        sleep 1
    done
    echo "Redis is ready!"
fi

# Export worker ID if not set
export WORKER_ID=${WORKER_ID:-stt-$RANDOM}

exec python worker.py

