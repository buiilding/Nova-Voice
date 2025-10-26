"""
result_publisher.py - Result publishing for Translation Worker

Handles publishing translation results to Redis pub/sub channels.
"""

import json
import logging
from typing import Dict, Any
import redis.asyncio as redis

from .config import RESULTS_CHANNEL_PREFIX


class ResultPublisher:
    """Publishes translation results to Redis"""

    def __init__(self, redis_client: redis.Redis, logger: logging.Logger):
        self.redis = redis_client
        self.logger = logger

    async def publish_result(self, result: Dict[str, Any]):
        """Publish result to Redis pub/sub channel"""
        channel = f"{RESULTS_CHANNEL_PREFIX}{result['client_id']}"

        # Ensure all values are JSON serializable
        serializable_result = self._make_json_serializable(result)

        self.logger.info(f"Publishing translation result: client={result.get('client_id')}, text_len={len(result.get('translation', ''))}")
        await self.redis.publish(channel, json.dumps(serializable_result).encode('utf-8'))

    def _make_json_serializable(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Convert any non-JSON serializable values to strings"""
        result = {}
        for key, value in obj.items():
            if isinstance(value, (int, float, str, bool, type(None))):
                result[key] = value
            elif isinstance(value, list):
                result[key] = [str(item) if not isinstance(item, (int, float, str, bool, type(None))) else item for item in value]
            else:
                result[key] = str(value)
        return result
