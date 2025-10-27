"""
result_publisher.py - Result publishing for STT Worker

Handles publishing transcription results to Redis pub/sub channels
and forwarding transcriptions to translation workers when needed.
"""

import json
import time
import logging
from typing import Dict, Any
import redis.asyncio as redis

from config import RESULTS_CHANNEL_PREFIX, TRANSCRIPTIONS_STREAM


class ResultPublisher:
    """Publishes transcription results to Redis"""

    def __init__(self, redis_client: redis.Redis, logger: logging.Logger):
        self.redis = redis_client
        self.logger = logger

    async def publish_result(self, result: Dict[str, Any]):
        """Publish result to Redis pub/sub channel"""
        channel = f"{RESULTS_CHANNEL_PREFIX}{result['client_id']}"
        self.logger.info(f"Publishing result: audio_duration={result.get('audio_duration', 'MISSING')}, processing_time={result.get('processing_time', 'MISSING')}, status={result.get('status', 'MISSING')}, text_len={len(result.get('text', ''))}")
        # Publish as UTF-8 encoded bytes for consistent handling
        await self.redis.publish(channel, json.dumps(result).encode('utf-8'))

    async def publish_transcription_for_translation(self, result: Dict[str, Any]):
        """When translation is enabled, publish transcription to shared stream for translation workers."""
        try:
            if result.get("status") != "ok":
                return
            text = (result.get("text") or "").strip()
            if not text:
                return
            if not self._parse_bool(result.get("translation_enabled", False)):
                return

            # Prepare mapping (strings preferred for Redis Stream entries)
            payload = {
                "job_id": str(result.get("job_id", "")),
                "client_id": str(result.get("client_id", "")),
                "segment_id": str(result.get("segment_id", "")),
                "text": text,
                "source_lang": str(result.get("source_lang", "en")),
                "target_lang": str(result.get("target_lang", "vi")),
                "is_final": "true" if self._parse_bool(result.get("is_final", False)) else "false",
                "timestamp": str(result.get("timestamp", time.time())),
                "audio_duration": result.get("audio_duration", 0.0)
            }
            await self.redis.xadd(TRANSCRIPTIONS_STREAM, payload)
            self.logger.info(f"Published transcription to stream '{TRANSCRIPTIONS_STREAM}' for client {payload['client_id']}")
        except Exception as e:
            self.logger.error(f"Error publishing transcription for translation: {e}")

    @staticmethod
    def _parse_bool(value: Any) -> bool:
        """Parse boolean from various string formats"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)
