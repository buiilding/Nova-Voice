"""
redis_service.py - Redis operations for the Gateway service

Handles all Redis connectivity, session management, job publishing, and pub/sub operations.
Provides a clean interface for Redis interactions separate from business logic.
"""

import asyncio
import json
import base64
import time
import uuid
import threading
import logging
from typing import Dict, Any, Optional
import redis.asyncio as redis

from .config import (
    REDIS_URL, AUDIO_JOBS_STREAM, RESULTS_CHANNEL_PREFIX, SESSION_PREFIX,
    MAX_QUEUE_DEPTH, SAMPLE_RATE, SESSION_EXPIRATION_SECONDS
)
from .session import SpeechSession


class RedisService:
    """Handles all Redis operations for the gateway service"""

    def __init__(self, instance_id: str, logger: logging.Logger):
        self.redis = None
        self.instance_id = instance_id
        self.logger = logger

        # Per-client pubsub management for security
        self.client_pubsubs: Dict[str, asyncio.Task] = {}
        self.pubsub_lock = threading.Lock()

        # Track latest segment_id sent per client
        self.latest_segment_id_sent = {}
        # Track if a job is in flight per client
        self.job_in_flight = {}

    async def connect(self):
        """Connect to Redis"""
        print(f"[DEBUG] Gateway connecting to Redis: {REDIS_URL}")
        self.redis = redis.Redis.from_url(REDIS_URL, decode_responses=False)
        await self.redis.ping()
        print("[DEBUG] Gateway Redis connection successful")
        self.logger.info("Connected to Redis")

    async def load_session(self, client_id: str) -> SpeechSession:
        """Load session state from Redis"""
        session_key = f"{SESSION_PREFIX}{client_id}"
        session_data_raw = await self.redis.hgetall(session_key)

        # Decode bytes to strings
        session_data = {}
        for key, value in session_data_raw.items():
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            session_data[key] = value

        if session_data:
            # Load audio buffers separately
            audio_buffers = {}
            audio_buffer_key = f"{SESSION_PREFIX}{client_id}:audio_buffer"
            pre_speech_buffer_key = f"{SESSION_PREFIX}{client_id}:pre_speech_buffer"

            audio_buffer_data = await self.redis.get(audio_buffer_key)
            if audio_buffer_data:
                audio_buffers['audio_buffer'] = audio_buffer_data

            pre_speech_buffer_data = await self.redis.get(pre_speech_buffer_key)
            if pre_speech_buffer_data:
                audio_buffers['pre_speech_buffer'] = pre_speech_buffer_data

            return SpeechSession.from_dict(session_data, audio_buffers)
        else:
            return SpeechSession()

    async def save_session(self, client_id: str, session: SpeechSession):
        """Save session state to Redis"""
        session_key = f"{SESSION_PREFIX}{client_id}"
        session_data = session.to_dict()
        # Encode strings to bytes for Redis with decode_responses=False
        encoded_session_data = {}
        for key, value in session_data.items():
            if isinstance(key, str):
                key = key.encode('utf-8')
            if isinstance(value, str):
                value = value.encode('utf-8')
            encoded_session_data[key] = value
        await self.redis.hset(session_key, mapping=encoded_session_data)

        # Store audio buffers separately as binary data
        audio_buffers = session.get_audio_buffers()
        audio_buffer_key = f"{SESSION_PREFIX}{client_id}:audio_buffer"
        pre_speech_buffer_key = f"{SESSION_PREFIX}{client_id}:pre_speech_buffer"

        if audio_buffers['audio_buffer']:
            await self.redis.set(audio_buffer_key, audio_buffers['audio_buffer'])
        else:
            await self.redis.delete(audio_buffer_key)

        if audio_buffers['pre_speech_buffer']:
            await self.redis.set(pre_speech_buffer_key, audio_buffers['pre_speech_buffer'])
        else:
            await self.redis.delete(pre_speech_buffer_key)

        # Set expiration to clean up old sessions
        await self.redis.expire(session_key, SESSION_EXPIRATION_SECONDS)
        await self.redis.expire(audio_buffer_key, SESSION_EXPIRATION_SECONDS)
        await self.redis.expire(pre_speech_buffer_key, SESSION_EXPIRATION_SECONDS)

    async def delete_session(self, client_id: str):
        """Delete session from Redis"""
        session_key = f"{SESSION_PREFIX}{client_id}"
        audio_buffer_key = f"{SESSION_PREFIX}{client_id}:audio_buffer"
        pre_speech_buffer_key = f"{SESSION_PREFIX}{client_id}:pre_speech_buffer"

        await self.redis.delete(session_key, audio_buffer_key, pre_speech_buffer_key)

    async def publish_audio_job(self, client_id: str, session: SpeechSession, is_final: bool = False):
        """Publish audio segment to Redis Stream for workers"""
        buffer_size = len(session.audio_buffer)
        if buffer_size == 0:
            print(f"[DEBUG] [JOB_SKIP_EMPTY] Client {client_id} attempted to publish empty buffer")
            return

        print(f"[DEBUG] [JOB_PUBLISH_START] Client {client_id} publishing job: {buffer_size} bytes, is_final: {is_final}")

        # Check queue depth for backpressure
        queue_depth = await self.redis.xlen(AUDIO_JOBS_STREAM)
        if queue_depth > MAX_QUEUE_DEPTH:
            print(f"[DEBUG] [JOB_QUEUE_FULL] Client {client_id} queue depth {queue_depth} exceeds threshold {MAX_QUEUE_DEPTH}, job not published")
            self.logger.warning(f"Queue depth {queue_depth} exceeds threshold {MAX_QUEUE_DEPTH}")
            # Could implement throttling here
            return

        # Create job envelope
        job_id = f"{client_id}_{uuid.uuid4().hex[:8]}"
        audio_b64 = base64.b64encode(bytes(session.audio_buffer)).decode('utf-8')

        job_data = {
            "job_type": "audio_segment",
            "job_id": job_id,
            "client_id": client_id,
            "segment_id": f"{int(time.time() * 1000)}",  # timestamp-based segment ID
            "audio_bytes_b64": audio_b64,
            "sample_rate": SAMPLE_RATE,
            "source_lang": session.source_lang,
            "target_lang": session.target_lang,
            "translation_enabled": str(session.translation_enabled),  # Convert boolean to string for Redis
            "is_final": str(is_final),  # Convert boolean to string for Redis
            "timestamp": time.time(),
            "gateway_instance": self.instance_id
        }

        # Encode all values to bytes for Redis with decode_responses=False
        encoded_job_data = {}
        for key, value in job_data.items():
            if isinstance(key, str):
                key = key.encode('utf-8')
            if isinstance(value, str):
                value = value.encode('utf-8')
            encoded_job_data[key] = value

        print(f"[DEBUG] [JOB_DATA] Client {client_id} job {job_id}: lang={session.source_lang}->{session.target_lang}, final={is_final}, size={len(audio_b64)} chars b64")

        # Add to Redis Stream
        stream_id = await self.redis.xadd(AUDIO_JOBS_STREAM, encoded_job_data)

        print(f"[DEBUG] [JOB_PUBLISHED] Client {client_id} job {job_id} published to Redis stream '{AUDIO_JOBS_STREAM}' with ID {stream_id}")
        self.logger.info(f"Published audio job {job_id} for client {client_id}, size: {buffer_size} bytes")

        return stream_id

    async def subscribe_to_results(self):
        """Subscribe to results channel and forward to clients"""
        print(f"[DEBUG] Gateway results subscription task started - will subscribe to client channels dynamically")

        # This task doesn't need to do anything initially
        # Client channels are subscribed to when clients connect
        # and unsubscribed when they disconnect
        while True:
            await asyncio.sleep(60)  # Keep task alive

    async def subscribe_to_client_channel(self, client_id: str, result_forwarder):
        """Subscribe to a specific client's result channel"""
        with self.pubsub_lock:
            if client_id in self.client_pubsubs:
                return  # Already subscribed

            async def listen_to_client():
                pubsub = None
                channel = f"{RESULTS_CHANNEL_PREFIX}{client_id}"
                try:
                    pubsub = self.redis.pubsub()
                    await pubsub.subscribe(channel)
                    print(f"[DEBUG] Gateway subscribed to client channel: {channel}")

                    async for message in pubsub.listen():
                        if message['type'] == 'message':
                            try:
                                # Workers now publish UTF-8 encoded JSON bytes
                                message_data = message['data']

                                # Decode bytes to string
                                if isinstance(message_data, bytes):
                                    try:
                                        message_data = message_data.decode('utf-8')
                                    except UnicodeDecodeError as decode_error:
                                        print(f"[DEBUG] UTF-8 decode error for client {client_id}: {decode_error}")
                                        continue  # Skip this corrupted message
                                else:
                                    print(f"[DEBUG] Unexpected message data type for client {client_id}: {type(message_data)} (expected bytes)")
                                    continue

                                # Parse JSON
                                result_data = json.loads(message_data)
                                if result_data.get('client_id') == client_id:  # Double-check
                                    print(f"[DEBUG] Received result for client {client_id}: '{result_data.get('text', '')}'")
                                    await result_forwarder(result_data)
                            except json.JSONDecodeError as json_error:
                                print(f"[DEBUG] JSON decode error for client {client_id}: {json_error}")
                            except Exception as e:
                                print(f"[DEBUG] Error processing message for client {client_id}: {e}")
                except asyncio.CancelledError:
                    # Normal cancellation path
                    pass
                except Exception as e:
                    print(f"[DEBUG] Error in client channel subscription for {client_id}: {e}")
                finally:
                    # Ensure we unsubscribe and close pubsub to free resources
                    try:
                        if pubsub is not None:
                            try:
                                await pubsub.unsubscribe(channel)
                            except Exception:
                                pass
                            try:
                                await pubsub.aclose()
                            except Exception:
                                pass
                    except Exception:
                        pass
                    with self.pubsub_lock:
                        self.client_pubsubs.pop(client_id, None)

            task = asyncio.create_task(listen_to_client())
            self.client_pubsubs[client_id] = task
            print(f"[DEBUG] Started listening task for client {client_id}")

    async def unsubscribe_from_client_channel(self, client_id: str):
        """Unsubscribe from a specific client's result channel"""
        task = None
        with self.pubsub_lock:
            if client_id in self.client_pubsubs:
                task = self.client_pubsubs[client_id]
        if task is not None:
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=2.0)
            except asyncio.CancelledError:
                pass
            except asyncio.TimeoutError:
                print(f"[DEBUG] Timeout waiting for pubsub task to cancel for {client_id}")
            finally:
                with self.pubsub_lock:
                    self.client_pubsubs.pop(client_id, None)
                    print(f"[DEBUG] Unsubscribed from client channel for {client_id}")

    async def get_queue_depth(self) -> int:
        """Get current Redis stream queue depth"""
        try:
            return await self.redis.xlen(AUDIO_JOBS_STREAM)
        except:
            return -1
