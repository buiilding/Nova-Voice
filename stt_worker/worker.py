"""
stt_worker.py - STT Worker Service with Redis Streams

This service consumes audio jobs from Redis Streams and performs speech-to-text transcription:
- Uses Faster-Whisper model for high-quality transcription with configurable parameters
- Consumes audio jobs from Redis Streams using consumer groups for horizontal scaling
- Processes base64-encoded audio with normalization and VAD filtering
- Publishes transcription results back to Redis pub/sub channels
- Integrates with translation pipeline by publishing to transcription streams when enabled
- Provides HTTP health check and metrics endpoints for monitoring
- Supports multiple languages with automatic language detection
- Tracks comprehensive metrics including processing times and success rates
"""

import asyncio
import json
import base64
import time
import os
import logging
import gc
import psutil
from typing import Any
import redis.asyncio as redis
from redis.exceptions import ConnectionError
import numpy as np
from faster_whisper import WhisperModel
from aiohttp import web
import aiohttp_cors

# === Configuration ===
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
WORKER_ID = os.getenv("WORKER_ID", f"stt-{os.getpid()}")
CONSUMER_GROUP = os.getenv("CONSUMER_GROUP", "stt_workers")

# Redis Streams
AUDIO_JOBS_STREAM = "audio_jobs"
RESULTS_CHANNEL_PREFIX = "results:"
TRANSCRIPTIONS_STREAM = os.getenv("TRANSCRIPTIONS_STREAM", "transcriptions")

# Model configuration
MODEL_SIZE = os.getenv("MODEL_SIZE", "large-v3")
DEVICE = os.getenv("DEVICE", "cuda")
COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "int8_float16" if DEVICE == "cuda" else "int8")
DOWNLOAD_ROOT = os.getenv("DOWNLOAD_ROOT")

# Transcription parameters
BEAM_SIZE = int(os.getenv("BEAM_SIZE", "1"))
INITIAL_PROMPT = os.getenv("INITIAL_PROMPT")
SUPPRESS_TOKENS = [-1] # was []
VAD_FILTER = os.getenv("VAD_FILTER", "false").lower() == "true"
BEST_OF = int(os.getenv("BEST_OF", "1"))

# Worker configuration
PENDING_ACK_TTL = int(os.getenv("PENDING_ACK_TTL", "300"))  # 5 minutes

# Health check
HEALTH_PORT = int(os.getenv("HEALTH_PORT", "8081"))


def validate_configuration():
    """Validate configuration and provide helpful error messages"""
    issues = []

    # Validate Redis URL
    if not REDIS_URL or not REDIS_URL.startswith("redis://"):
        issues.append(f"Invalid REDIS_URL: {REDIS_URL}. Must start with 'redis://'")

    # Validate model size
    valid_sizes = ["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3", "large"]
    if MODEL_SIZE not in valid_sizes:
        issues.append(f"Invalid MODEL_SIZE: {MODEL_SIZE}. Valid options: {', '.join(valid_sizes)}")

    # Validate device
    if DEVICE not in ["cpu", "cuda"]:
        issues.append(f"Invalid DEVICE: {DEVICE}. Must be 'cpu' or 'cuda'")

    # Validate compute type for CUDA
    if DEVICE == "cuda" and COMPUTE_TYPE not in ["default", "auto", "int8", "int8_float16", "int16", "float16", "float32"]:
        issues.append(f"Invalid COMPUTE_TYPE for CUDA: {COMPUTE_TYPE}")

    # Validate beam size
    if BEAM_SIZE < 1 or BEAM_SIZE > 10:
        issues.append(f"Invalid BEAM_SIZE: {BEAM_SIZE}. Must be between 1 and 10")

    # Validate health port
    if not (1024 <= HEALTH_PORT <= 65535):
        issues.append(f"Invalid HEALTH_PORT: {HEALTH_PORT}. Must be between 1024 and 65535")

    if issues:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {issue}" for issue in issues)
        raise ValueError(error_msg)

    print("✓ Configuration validation passed")


class STTWorker:
    def __init__(self):
        self.redis = None
        self.model = None
        self.worker_id = WORKER_ID
        self.consumer_group = CONSUMER_GROUP
        self.logger = logging.getLogger(f"STT-{self.worker_id}")

        # Metrics
        self.metrics = {
            "jobs_processed": 0,
            "jobs_failed": 0,
            "total_processing_time": 0.0,
            "uptime": time.time(),
            "memory_mb": 0.0,
            "gc_collections": 0
        }

        # Memory management
        self.last_gc_time = time.time()
        self.gc_interval = 300  # Run GC every 5 minutes

    def _parse_bool(self, value: Any) -> bool:
        """Parse boolean value from various formats (string, bool, etc.)"""
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return value != 0
        try:
            s = str(value).strip().lower()
            return s in {"1", "true", "yes", "y", "on"}
        except Exception:
            return False

    async def connect_redis(self):
        """Connect to Redis and setup consumer group"""
        self.logger.debug(f"Connecting to Redis: {REDIS_URL}")
        self.redis = redis.Redis.from_url(REDIS_URL, decode_responses=False)

        # Test connection
        await self.redis.ping()
        self.logger.debug("Redis connection successful")

        # Create consumer group if it doesn't exist
        try:
            await self.redis.xgroup_create(
                AUDIO_JOBS_STREAM,
                self.consumer_group,
                "$",
                mkstream=True
            )
            self.logger.info(f"Created consumer group {self.consumer_group}")
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
            self.logger.info(f"Consumer group {self.consumer_group} already exists")

        self.logger.info("Connected to Redis")

    def load_model(self):
        """Load the Faster-Whisper model"""
        start_time = time.time()

        try:
            self.logger.info(f"Loading Faster-Whisper model: {MODEL_SIZE} on {DEVICE}")

            self.model = WhisperModel(
                model_size_or_path=MODEL_SIZE,
                device=DEVICE,
                compute_type=COMPUTE_TYPE,
                device_index=0,
                download_root=DOWNLOAD_ROOT,
            )

            # Warm up the model with validation
            self.logger.info("Warming up model...")
            dummy_audio = np.random.randn(16000).astype(np.float32) * 0.01
            segments, info = self.model.transcribe(dummy_audio,
                                                   language="en",
                                                   beam_size=BEAM_SIZE,
                                                   temperature=0,
                                                   best_of=BEST_OF)

            # Convert generator to list to get segments count
            segments_list = list(segments)
            transcription = " ".join(segment.text for segment in segments_list)

            # Validate warm-up worked - just ensure model can process audio
            # Random noise may produce no transcription, which is normal
            self.logger.debug(f"Warm-up completed: {len(segments_list)} segments, '{transcription[:50]}...'")
            if len(segments_list) == 0 and not transcription.strip():
                self.logger.warning("Model warm-up produced no segments/transcription from random noise - this is usually normal")
            else:
                self.logger.debug("Model warm-up successful")

            load_time = time.time() - start_time
            self.logger.info(f"Model loaded and warmed up successfully in {load_time:.2f}s")

        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            raise

    def _monitor_memory(self):
        """Monitor memory usage and trigger GC if needed"""
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.metrics["memory_mb"] = memory_mb

            # Trigger garbage collection periodically
            current_time = time.time()
            if current_time - self.last_gc_time > self.gc_interval:
                collected = gc.collect()
                self.metrics["gc_collections"] += 1
                self.last_gc_time = current_time

                self.logger.debug(f"GC collected {collected} objects, memory: {memory_mb:.1f} MB")

        except Exception as e:
            self.logger.warning(f"Memory monitoring error: {e}")

    async def _read_stream_messages(self):
        """Read messages from Redis stream"""
        return await self.redis.xreadgroup(
            self.consumer_group,
            self.worker_id,
            {AUDIO_JOBS_STREAM: ">"},
            count=1,
            block=1000
        )

    async def _process_stream_message(self, message_id: str, message_data: dict[str, Any]):
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

            # Debug log the received message data
            job_id = decoded_message_data.get("job_id", "unknown")
            client_id = decoded_message_data.get("client_id", "unknown")
            self.logger.debug(f"Received job message {message_id}: job_id={job_id}, client_id={client_id}, keys={list(decoded_message_data.keys())}")

            result = await self.process_audio_job(decoded_message_data)
            await self.publish_result(result)
            await self.publish_transcription_for_translation(result)

            # Acknowledge and delete message
            await self.redis.xack(AUDIO_JOBS_STREAM, self.consumer_group, message_id)
            await self.redis.xdel(AUDIO_JOBS_STREAM, message_id)

        except Exception as e:
            self.logger.error(f"Error processing job {message_data.get('job_id', 'unknown') if isinstance(message_data.get('job_id'), str) else 'unknown'}: {e}")
            self.metrics["jobs_failed"] += 1

    def transcribe_audio(self, audio_data: bytes, language: str = "", use_vad_filter: bool = True) -> dict[str, Any]:
        """Transcribe audio data to text"""
        try:
            start_time = time.time()

            # Calculate audio duration (16kHz, int16 format = 2 bytes per sample)
            audio_duration = len(audio_data) / (2 * 16000)

            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            audio_float = audio_array.astype(np.float32) / 32768.0


            # Transcribe
            segments, info = self.model.transcribe(
                audio_float,
                language=language if language else None,
                beam_size=BEAM_SIZE,
                initial_prompt=INITIAL_PROMPT,
                suppress_tokens=SUPPRESS_TOKENS,
                best_of=BEST_OF,
                temperature=0,
                vad_filter=use_vad_filter
            )

            # Convert generator to list to get segments count
            segments_list = list(segments)
            transcription = " ".join(segment.text for segment in segments_list).strip()
            processing_time = time.time() - start_time

            result = {
                "text": transcription,
                "language": info.language,
                "language_probability": info.language_probability,
                "processing_time": processing_time,
                "audio_duration": audio_duration,
                "segments": len(segments_list)
            }

            self.logger.info(f"Transcription completed in {processing_time:.2f}s")
            return result

        except Exception as e:
            self.logger.error(f"Error transcribing audio: {e}")
            # Calculate audio duration even in error case
            audio_duration = len(audio_data) / (2 * 16000)
            return {
                "text": "",
                "error": str(e),
                "language": "",
                "language_probability": 0.0,
                "processing_time": 0.0,
                "audio_duration": audio_duration,
                "segments": 0
            }

    async def process_audio_job(self, job_data: dict[str, Any]) -> dict[str, Any]:
        """Process a single audio job"""
        # Extract job parameters
        job_id = job_data.get("job_id", "unknown")
        client_id = job_data.get("client_id", "unknown")
        source_lang = job_data.get("source_lang", "en")
        target_lang = job_data.get("target_lang", "vi")
        translation_enabled = self._parse_bool(job_data.get("translation_enabled", True))
        is_final = self._parse_bool(job_data.get("is_final", False))

        self.logger.info(f"Processing job {job_id} for client {client_id}")

        # Base result template
        result = {
            "status": "ok",
            "job_id": job_id,
            "client_id": client_id,
            "segment_id": job_data.get("segment_id", ""),
            "source_lang": source_lang,
            "target_lang": target_lang,
            "translation_enabled": translation_enabled,
            "is_final": is_final,
            "worker_id": self.worker_id,
            "timestamp": time.time(),
            "text": "",
            "language": "",
            "language_probability": 0.0,
            "processing_time": 0.0,
            "audio_duration": 0.0,
            "segments": 0
        }

        try:
            # Monitor memory usage
            self._monitor_memory()

            self.logger.info(f"Processing job {job_id} for client {client_id}")

            # Decode audio
            audio_b64 = job_data.get("audio_bytes_b64", "")
            audio_bytes = base64.b64decode(audio_b64)

            # Transcribe audio
            transcription_result = self.transcribe_audio(
                audio_bytes,
                language=source_lang,
                use_vad_filter=VAD_FILTER
            )

            # Update result with transcription data
            result.update({
                "text": transcription_result["text"],
                "language": transcription_result["language"],
                "language_probability": transcription_result["language_probability"],
                "processing_time": transcription_result["processing_time"],
                "audio_duration": transcription_result["audio_duration"],
                "segments": transcription_result["segments"]
            })

            # Update metrics
            self.metrics["jobs_processed"] += 1
            self.metrics["total_processing_time"] += transcription_result["processing_time"]

        except Exception as e:
            self.logger.error(f"Error processing job {job_id}: {e}")

            # Update result for error case
            result.update({
                "status": "error",
                "error": str(e),
                "processing_time": 0.0
            })

            # Update metrics
            self.metrics["jobs_failed"] += 1

        return result

    async def publish_result(self, result: dict[str, Any]):
        """Publish result to Redis pub/sub channel"""
        channel = f"{RESULTS_CHANNEL_PREFIX}{result['client_id']}"
        self.logger.info(f"Publishing result: audio_duration={result.get('audio_duration', 'MISSING')}, processing_time={result.get('processing_time', 'MISSING')}, status={result.get('status', 'MISSING')}, text_len={len(result.get('text', ''))}")
        # Publish as UTF-8 encoded bytes for consistent handling
        await self.redis.publish(channel, json.dumps(result).encode('utf-8'))

    async def publish_transcription_for_translation(self, result: dict[str, Any]):
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

    async def health_check_handler(self, request):
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "worker_id": self.worker_id,
            "model_loaded": self.model is not None,
            "timestamp": time.time(),
            "metrics": self.metrics
        })

    async def metrics_handler(self, request):
        """Metrics endpoint"""
        try:
            # Get stream info
            stream_info = await self.redis.xinfo_stream(AUDIO_JOBS_STREAM)
            pending_info = await self.redis.xpending(AUDIO_JOBS_STREAM, self.consumer_group)

            return web.json_response({
                "worker_id": self.worker_id,
                "stream_length": stream_info.get("length", 0),
                "pending_messages": pending_info.get("pending", 0),
                "metrics": self.metrics,
                "timestamp": time.time()
            })
        except Exception as e:
            return web.json_response({
                "worker_id": self.worker_id,
                "error": str(e),
                "metrics": self.metrics,
                "timestamp": time.time()
            })

    async def start_health_server(self):
        """Start health check HTTP server"""
        app = web.Application()
        app.router.add_get('/health', self.health_check_handler)
        app.router.add_get('/metrics', self.metrics_handler)
        
        # Disable aiohttp access logging
        logging.getLogger('aiohttp.access').setLevel(logging.CRITICAL)

        # Add CORS support
        cors = aiohttp_cors.setup(app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })

        for route in list(app.router.routes()):
            cors.add(route)

        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        # Explicitly disable access log at the site level
        site = web.TCPSite(runner, '0.0.0.0', HEALTH_PORT)
        await site.start()
        self.logger.info(f"Health server started on port {HEALTH_PORT}")

async def main():
    """Main STT worker service"""
    # Validate configuration
    validate_configuration()

    worker = STTWorker()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
    )

    try:
        # Connect to Redis
        await worker.connect_redis()

        # Load model
        worker.load_model()

        # Start health server
        await worker.start_health_server()

        # Log all configuration variables
        worker.logger.info("STT Worker initialization complete")
        worker.logger.info(f"Redis: {REDIS_URL}")
        worker.logger.info(f"Worker ID: {WORKER_ID}")
        worker.logger.info(f"Consumer Group: {CONSUMER_GROUP}")
        worker.logger.info(f"Audio Jobs Stream: {AUDIO_JOBS_STREAM}")
        worker.logger.info(f"Results Channel Prefix: {RESULTS_CHANNEL_PREFIX}")
        worker.logger.info(f"Transcriptions Stream: {TRANSCRIPTIONS_STREAM}")
        worker.logger.info(f"Model: {MODEL_SIZE} on {DEVICE}")
        worker.logger.info(f"Compute Type: {COMPUTE_TYPE}")
        worker.logger.info(f"Download Root: {DOWNLOAD_ROOT}")
        worker.logger.info(f"Transcription Parameters: BEAM_SIZE={BEAM_SIZE}, BEST_OF={BEST_OF}, VAD_FILTER={VAD_FILTER}")
        worker.logger.info(f"Initial Prompt: {INITIAL_PROMPT}")
        worker.logger.info(f"Pending ACK TTL: {PENDING_ACK_TTL}s")
        worker.logger.info(f"Health server on port {HEALTH_PORT}")

        worker.logger.info(f"Starting STT Worker {worker.worker_id}")

        # Start consuming jobs
        await worker.consume_jobs()

    except Exception as e:
        worker.logger.error(f"Worker startup error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())

