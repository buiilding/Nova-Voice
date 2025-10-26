"""
redis_consumer.py - Shared Redis Stream consumer for worker services

Provides a standardized way for workers to consume jobs from Redis Streams
using consumer groups. Handles connection management, message processing,
and error handling.
"""

import asyncio
import logging
from typing import Dict, Any, Callable, Optional
import redis.asyncio as redis
from redis.exceptions import ConnectionError


class RedisStreamConsumer:
    """Consumes jobs from Redis Streams using consumer groups"""

    def __init__(self, redis_url: str, stream_name: str, consumer_group: str,
                 consumer_id: str, logger: logging.Logger,
                 message_processor: Callable[[str, Dict[str, Any]], None]):
        """
        Initialize Redis stream consumer

        Args:
            redis_url: Redis connection URL
            stream_name: Name of the Redis stream to consume from
            consumer_group: Consumer group name
            consumer_id: Unique consumer ID within the group
            logger: Logger instance
            message_processor: Async function to process each message (message_id, message_data)
        """
        self.redis_url = redis_url
        self.stream_name = stream_name
        self.consumer_group = consumer_group
        self.consumer_id = consumer_id
        self.logger = logger
        self.message_processor = message_processor
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis"""
        self.redis = redis.Redis.from_url(self.redis_url, decode_responses=False)
        await self.redis.ping()
        self.logger.info(f"Connected to Redis for stream consumption: {self.stream_name}")

    async def _read_stream_messages(self):
        """Read messages from Redis stream"""
        return await self.redis.xreadgroup(
            self.consumer_group,
            self.consumer_id,
            {self.stream_name: ">"},
            count=1,
            block=1000
        )

    async def _process_stream_message(self, message_id: str, message_data: Dict[str, Any]):
        """Process a single message from the stream"""
        try:
            # Decode bytes to strings for message_data (Redis with decode_responses=False)
            decoded_message_data = {}
            for key, value in message_data.items():
                if isinstance(key, bytes):
                    key = key.decode('utf-8')
                if isinstance(value, bytes):
                    value = value.decode('utf-8')
                decoded_message_data[key] = value

            # Extract job info for logging
            job_id = decoded_message_data.get("job_id", "unknown")
            client_id = decoded_message_data.get("client_id", "unknown")
            self.logger.debug(f"Received job message {message_id}: job_id={job_id}, client_id={client_id}")

            # Process the message
            await self.message_processor(message_id, decoded_message_data)

            # Acknowledge and delete message
            await self.redis.xack(self.stream_name, self.consumer_group, message_id)
            await self.redis.xdel(self.stream_name, message_id)

        except Exception as e:
            job_id = decoded_message_data.get("job_id", "unknown") if 'decoded_message_data' in locals() else "unknown"
            self.logger.error(f"Error processing job {job_id}: {e}")

    async def consume_jobs(self):
        """Consume jobs from Redis Stream using consumer groups"""
        while True:
            try:
                messages = await self._read_stream_messages()

                for stream_name, message_list in messages:
                    for message_id, message_data in message_list:
                        await self._process_stream_message(message_id, message_data)

            except ConnectionError as e:
                self.logger.error(f"Redis connection error: {e}")
                await asyncio.sleep(5)
            except Exception as e:
                self.logger.error(f"Error consuming jobs: {e}")
                await asyncio.sleep(1)
