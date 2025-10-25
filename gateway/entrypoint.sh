#!/bin/bash
set -e

echo "Starting Gateway Service..."
echo "Redis URL: ${REDIS_URL:-redis://localhost:6379}"
echo "Gateway Port: ${GATEWAY_PORT:-5026}"
echo "Health Port: ${HEALTH_PORT:-8080}"

# Wait for Redis to be ready
if [ -n "${REDIS_URL}" ]; then
    echo "Waiting for Redis..."
    while ! nc -z redis 6379; do
        sleep 1
    done
    echo "Redis is ready!"
fi

exec python gateway.py

