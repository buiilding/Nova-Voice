"""
gateway.py - Horizontally Scalable WebSocket Gateway Service

This service acts as the entry point for clients, handling:
- WebSocket connections for audio streaming
- Dual Voice Activity Detection (VAD) system using WebRTC + Silero models
- Audio accumulation during active speech periods with pre-speech buffering
- Session state persistence in Redis for horizontal scaling
- Publishing audio segments to Redis Streams for worker processing (event-driven, not interval-based)
- Subscribing to results and forwarding to clients
- Language settings and translation management
- Flow control and job-in-flight tracking

Features:
- Dual VAD System: WebRTC (fast) + Silero (accurate) for robust speech detection
- Pre-speech Buffering: Maintains rolling buffer of audio before speech detection for better accuracy
- Speech State Management: INACTIVE → ACTIVE → SILENCE → INACTIVE state transitions
- Event-driven Processing: Publishes audio segments only when previous job result is received
- Buffer Management: Enforces max buffer limits with overflow handling and final job sending
- Flow Control: Prevents job flooding with per-client job-in-flight tracking
- Language Support: Handles multiple languages with automatic translation enable/disable
- Session Persistence: Stores client session state in Redis for horizontal scaling
- Real-time Results: Subscribes to transcription/translation results via Redis pub/sub
- Health Monitoring: Provides health check endpoints and metrics

DEBUG OUTPUT FORMAT:
[GATEWAY INITIALIZATION] - Configuration variables display at startup
Voice detected, activating buffer - When speech is first detected
Buffer's current size: X.XX - Dynamic buffer size display (updates in place)
Sent job (X.XX/Y.YYs) to STT_WORKER - Job sent with buffer sizes
Silence during recording: [====------] 0.7 / 2.0s - Silence progress bar (updates in place)
Exceeded SILENCE_THRESHOLD_SECONDS, resetting buffer - When silence timeout reached
Exceeded MAX_AUDIO_BUFFER_SECONDS, resetting buffer - When buffer overflow occurs
Received from STT_WORKER: "text" - Transcription result received
Received from TRANSLATION_WORKER: "text" - Translation result received
Sending "text" to client_id - Results forwarded to client
Client X connected - Client connection established
Client X ready - Client ready to receive messages
Client X sent start_over - Start over command received
Speech ended for client X - Speech session ended
Utterance_end sent to client X - Utterance end signal sent
"""

import asyncio
import json
import struct
import threading
import time
import base64
import uuid
import websockets
from typing import Optional, Dict, Any, Set, Tuple
import logging
import os
import gc
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import from our modular components
from config import (
    REDIS_URL, GATEWAY_PORT, HEALTH_PORT, SILENCE_THRESHOLD_SECONDS, SAMPLE_RATE,
    WEBRTC_SENSITIVITY, SILERO_SENSITIVITY, INT16_MAX_ABS_VALUE, AUDIO_JOBS_STREAM,
    RESULTS_CHANNEL_PREFIX, SESSION_PREFIX, PRE_SPEECH_BUFFER_SECONDS, MINIMUM_NEW_AUDIO_SECONDS, MAX_QUEUE_DEPTH,
    MAX_AUDIO_BUFFER_SECONDS, SEND_FINAL_JOB_ON_MAX_BUFFER,
    ENABLE_AUDIO_ENHANCEMENT, AUDIO_VOLUME_BOOST_DB, SESSION_EXPIRATION_SECONDS
)
from session import SpeechState, SpeechSession
from vad import VoiceActivityDetector
from audio_processor import AudioProcessor
from redis_service import RedisService
from websocket_handler import WebSocketHandler
from health import HealthMonitor


class GatewayService:
    def __init__(self):
        self.instance_id = str(uuid.uuid4())[:8]
        self.logger = logging.getLogger(f"GATEWAY-{self.instance_id}")

        # Initialize modular components
        self.redis_client = RedisService(self.instance_id, self.logger)
        self.vad_detector = VoiceActivityDetector()
        self.audio_processor = AudioProcessor()
        self.websocket_handler = WebSocketHandler(self, self.redis_client, self.audio_processor)
        self.health_monitor = HealthMonitor(self.instance_id, self.logger, self.redis_client, self)

        # WebSocket client management
        self.connected_clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.client_lock = threading.Lock()

        # Session caching for performance
        self.session_cache: Dict[str, Tuple[SpeechSession, float]] = {}  # client_id -> (session, cache_time)
        self.session_cache_ttl = 30.0  # 30 seconds TTL
        self.cache_lock = threading.Lock()

        # Metrics
        self.metrics = {
            "clients_connected": 0,
            "audio_chunks_processed": 0,
            "jobs_published": 0,
            "results_forwarded": 0,
            "errors": 0
        }


    async def connect_redis(self):
        """Connect to Redis using RedisClient"""
        await self.redis_client.connect()

    def initialize_vad_models(self):
        """Initialize VAD models using the VoiceActivityDetector"""
        try:
            self.logger.info("Initializing VAD models...")
            self.vad_detector.initialize_models()
            self.logger.info("VAD models initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing VAD models: {e}")
            raise

    def detect_speech_activity(self, audio_chunk: bytes) -> bool:
        """Detect speech activity using the VoiceActivityDetector"""
        return self.vad_detector.detect_speech_activity(audio_chunk)
    async def load_session(self, client_id: str) -> SpeechSession:
        """Load session state from cache or Redis using RedisClient"""
        current_time = time.time()

        # Check cache first
        with self.cache_lock:
            if client_id in self.session_cache:
                session, cache_time = self.session_cache[client_id]
                if current_time - cache_time < self.session_cache_ttl:
                    return session
                else:
                    # Cache expired, remove it
                    del self.session_cache[client_id]

        # Load from Redis
        session = await self.redis_client.load_session(client_id)

        # Cache the session
        with self.cache_lock:
            self.session_cache[client_id] = (session, current_time)

        return session

    async def save_session(self, client_id: str, session: SpeechSession):
        """Save session state to Redis using RedisClient and update cache"""
        await self.redis_client.save_session(client_id, session)

        # Update cache with fresh data
        with self.cache_lock:
            self.session_cache[client_id] = (session, time.time())

    async def delete_session(self, client_id: str):
        """Delete session from Redis using RedisClient and clear cache"""
        await self.redis_client.delete_session(client_id)

        # Remove from cache
        with self.cache_lock:
            self.session_cache.pop(client_id, None)

    def invalidate_session_cache(self, client_id: str):
        """Invalidate session cache for a specific client"""
        with self.cache_lock:
            self.session_cache.pop(client_id, None)

    async def publish_audio_job(self, client_id: str, session: SpeechSession, is_final: bool = False):
        """Publish audio segment to Redis Stream using RedisClient"""
        stream_id = await self.redis_client.publish_audio_job(client_id, session, is_final)
        if stream_id:
            self.metrics["jobs_published"] += 1

    async def publish_job_if_needed(self, client_id: str, session: SpeechSession, is_final: bool = False, force_publish: bool = False):
        """Publish audio job if there is new data, no job is in flight, and minimum new audio size is met (unless forced).
        When calculating minimum threshold after silence, only count NEW SPEECH data (excluding silence audio)."""
        job_in_flight = self.redis_client.job_in_flight.get(client_id, False)
        buffer_has_new_data = len(session.audio_buffer) > session.last_published_len
        new_audio_bytes = len(session.audio_buffer) - session.last_published_len
        new_audio_seconds = new_audio_bytes / (SAMPLE_RATE * 2)
        
        # Calculate speech-only bytes for threshold checking
        # If we have a silence marker, only count audio AFTER the silence marker as "new speech"
        if session.silence_buffer_start_len > 0 and session.silence_buffer_start_len > session.last_published_len:
            # We resumed speech after silence - only count audio after silence_buffer_start_len
            new_speech_bytes = max(0, len(session.audio_buffer) - session.silence_buffer_start_len)
            new_speech_seconds = new_speech_bytes / (SAMPLE_RATE * 2)
            self.logger.debug(f"[THRESHOLD_CALC] Client {client_id} resumed after silence: new_speech={new_speech_seconds:.2f}s (excluding {(session.silence_buffer_start_len - session.last_published_len) / (SAMPLE_RATE * 2):.2f}s silence)")
        else:
            # Normal case - no silence period to exclude
            new_speech_bytes = new_audio_bytes
            new_speech_seconds = new_audio_seconds
        
        new_audio_meets_minimum = new_speech_seconds >= MINIMUM_NEW_AUDIO_SECONDS

        if (force_publish or not job_in_flight) and buffer_has_new_data and (force_publish or new_audio_meets_minimum):
            job_buffer_size = len(session.audio_buffer) - session.last_published_len
            job_seconds = job_buffer_size / (SAMPLE_RATE * 2)
            self.logger.info(f"Sent {'final ' if is_final else ''}job ({job_seconds:.2f}s new audio, {new_speech_seconds:.2f}s new speech) to STT_WORKER for client {client_id}")
            await self.publish_audio_job(client_id, session, is_final)
            session.last_published_len = len(session.audio_buffer)
            # Reset silence marker after publishing
            session.silence_buffer_start_len = 0
            if not is_final:  # Don't mark final jobs as in-flight
                self.redis_client.job_in_flight[client_id] = True
            return True
        elif not new_audio_meets_minimum and not force_publish:
            self.logger.debug(f"[JOB_WAIT_MINIMUM] Client {client_id} waiting for minimum new speech ({new_speech_seconds:.2f}/{MINIMUM_NEW_AUDIO_SECONDS:.2f}s)")
        elif job_in_flight and not force_publish:
            self.logger.debug(f"[JOB_WAIT] Client {client_id} waiting for previous job to complete before sending new job")
        else:
            self.logger.debug(f"[JOB_SKIP] Client {client_id} no new audio data to send")
        return False

    async def subscribe_to_results(self):
        """Subscribe to results channel using RedisClient"""
        await self.redis_client.subscribe_to_results()


    def decode_and_resample(self, audio_data: bytes, original_sample_rate: int, target_sample_rate: int = SAMPLE_RATE) -> bytes:
        """Resample audio using the AudioProcessor"""
        return self.audio_processor.decode_and_resample(audio_data, original_sample_rate, target_sample_rate)

    async def process_audio_chunk(self, client_id: str, audio_chunk: bytes) -> bool:
        """Process audio chunk and send job only if no job is in flight for this client. When silence is detected, always send a final job before clearing the buffer."""
        self.logger.debug(f"[PROCESS_CHUNK] Client {client_id} processing audio chunk: {len(audio_chunk)} bytes")

        session = await self.load_session(client_id)

        self.logger.debug(f"[SESSION_STATE] Client {client_id} session state: {session.state.value}, buffer: {len(session.audio_buffer)} bytes, pre-speech: {len(session.pre_speech_buffer)} bytes")

        # Always maintain rolling pre-speech buffer for potential future speech detection
        pre_speech_max_bytes = int(PRE_SPEECH_BUFFER_SECONDS * SAMPLE_RATE * 2)
        original_pre_speech_len = len(session.pre_speech_buffer)
        session.pre_speech_buffer.extend(audio_chunk)
        if len(session.pre_speech_buffer) > pre_speech_max_bytes:
            excess_bytes = len(session.pre_speech_buffer) - pre_speech_max_bytes
            session.pre_speech_buffer = session.pre_speech_buffer[excess_bytes:]
            self.logger.debug(f"[PRE_SPEECH_TRIMMED] Client {client_id} pre-speech buffer trimmed by {excess_bytes} bytes")

        self.logger.debug(f"[BUFFER_UPDATED] Client {client_id} pre-speech buffer: {original_pre_speech_len} -> {len(session.pre_speech_buffer)} bytes")

        # Detect speech activity
        has_speech = self.detect_speech_activity(audio_chunk)
        self.logger.debug(f"[SPEECH_DETECTED] Client {client_id} speech detected: {has_speech}")

        # Max buffer enforcement
        max_audio_buffer_bytes = int(MAX_AUDIO_BUFFER_SECONDS * SAMPLE_RATE * 2)
        buffer_exceeded = False

        if has_speech:
            if session.state == SpeechState.INACTIVE:
                original_buffer_len = len(session.audio_buffer)
                session.audio_buffer.extend(session.pre_speech_buffer)
                session.accumulated_audio_bytes += len(session.pre_speech_buffer)
                session.start_speech()
                # Start silence timer when recording begins
                session.silence_start_time = time.time()
                self.logger.info(f"Voice detected, activating buffer for client {client_id}.")
            elif session.state == SpeechState.SILENCE:
                # Mark where silence buffer started before resuming speech
                session.silence_buffer_start_len = len(session.audio_buffer)
                session.start_speech()
                # Reset silence timer when resuming from silence
                session.silence_start_time = time.time()
                self.logger.debug(f"[SPEECH_RESUME] Client {client_id} speech resumed from silence, timer reset, silence buffer marked at {session.silence_buffer_start_len} bytes")
            elif session.state == SpeechState.ACTIVE:
                # Reset silence timer when speech is detected during active recording
                session.silence_start_time = time.time()
                self.logger.debug(f"[SPEECH_DETECTED_ACTIVE] Client {client_id} speech detected, resetting silence timer")

        # Detect when we're transitioning from speech to silence
        if session.state == SpeechState.ACTIVE and not has_speech:
            # No speech detected during active recording - entering silence period
            if session.silence_start_time is None:
                session.silence_start_time = time.time()
                session.silence_buffer_start_len = len(session.audio_buffer)
                self.logger.debug(f"[SILENCE_START] Client {client_id} entering silence period, marking buffer at {session.silence_buffer_start_len} bytes")

        # Once buffer is activated (ACTIVE state), accumulate ALL audio chunks regardless of speech detection
        if session.state == SpeechState.ACTIVE:
            original_buffer_len = len(session.audio_buffer)
            session.audio_buffer.extend(audio_chunk)
            session.accumulated_audio_bytes += len(audio_chunk)
            # Dynamic buffer size display
            print(f"\rBuffer's current size: {session.buffer_seconds:.2f}", end="", flush=True)

            # Enforce max buffer size
            if len(session.audio_buffer) > max_audio_buffer_bytes:
                self.logger.warning(f"Exceeded MAX_AUDIO_BUFFER_SECONDS, resetting buffer for client {client_id}")
                if SEND_FINAL_JOB_ON_MAX_BUFFER:
                    # Send a final job before clearing buffer and resetting session
                    await self.publish_job_if_needed(client_id, session, is_final=True, force_publish=True)
                else:
                    self.logger.debug(f"[FINAL_JOB_DISABLED] Client {client_id} final job sending disabled by config")
                # Clear buffer and reset session
                session.end_speech_session()
                await self.save_session(client_id, session)
                return True
        else:
            self.logger.debug(f"[NO_SPEECH] Client {client_id} no speech detected in audio chunk")

        # Continuous silence detection during ACTIVE recording
        if session.state == SpeechState.ACTIVE and session.silence_start_time is not None:
            silence_duration = time.time() - session.silence_start_time
            # Create progress bar for silence
            progress = min(silence_duration / SILENCE_THRESHOLD_SECONDS, 1.0)
            filled = int(progress * 10)
            bar = "=" * filled + "-" * (10 - filled)
            print(f"\rSilence during recording: [{bar}] {silence_duration:.1f} / {SILENCE_THRESHOLD_SECONDS:.1f}s", end="", flush=True)

            if silence_duration >= SILENCE_THRESHOLD_SECONDS:
                self.logger.info(f"Exceeded SILENCE_THRESHOLD_SECONDS, resetting buffer for client {client_id}")
                buffer_len = len(session.audio_buffer)
                # Always send a final job if there is any audio left, even if a job is in flight
                # Mark job as not in flight so final job can be sent
                self.redis_client.job_in_flight[client_id] = False
                await self.publish_job_if_needed(client_id, session, is_final=True, force_publish=True)
                # Only clear buffer after final job is sent
                session.end_speech_session()
                await self.save_session(client_id, session)
                return True

        # Only send a job if no job is in flight for this client and there is audio to send
        # BUT: During silence periods, don't send any jobs (wait for either speech resume or silence timeout)
        if session.state == SpeechState.ACTIVE:
            # Check if we're currently in a silence period
            in_silence_period = (session.silence_start_time is not None and 
                                 session.silence_buffer_start_len > 0 and 
                                 len(session.audio_buffer) > session.silence_buffer_start_len)
            
            if in_silence_period:
                self.logger.debug(f"[JOB_SKIP_SILENCE] Client {client_id} in silence period, not sending job")
            else:
                self.logger.debug(f"[JOB_CHECK] Client {client_id} job in flight: {self.redis_client.job_in_flight.get(client_id, False)}, buffer has new data: {len(session.audio_buffer) > session.last_published_len} ({len(session.audio_buffer)} > {session.last_published_len})")
                await self.publish_job_if_needed(client_id, session, is_final=False)

        await self.save_session(client_id, session)
        self.metrics["audio_chunks_processed"] += 1
        return False

    async def handle_client(self, websocket):
        """Handle individual client connection using WebSocketHandler"""
        await self.websocket_handler.handle_client(websocket)

    async def start_health_server(self):
        """Start health check HTTP server using HealthMonitor"""
        await self.health_monitor.start_health_server()

async def main():
    """Main gateway service"""
    service = GatewayService()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [GATEWAY] %(levelname)s: %(message)s'
    )

    try:
        # Connect to Redis
        await service.connect_redis()

        # Initialize VAD models (dual VAD system)
        service.initialize_vad_models()

        # Start health server
        await service.start_health_server()

        # Start results subscription
        service.logger.debug("Gateway starting results subscription task")
        asyncio.create_task(service.subscribe_to_results())
        service.logger.debug("Gateway results subscription task started")

        service.logger.info(f"Starting Gateway Service on port {GATEWAY_PORT}")
        service.logger.info(f"Health server on port {HEALTH_PORT}")
        service.logger.info(f"Redis: {REDIS_URL}")
        service.logger.info(f"Silence threshold: {SILENCE_THRESHOLD_SECONDS}s")
        service.logger.info(f"Pre-speech buffer: {PRE_SPEECH_BUFFER_SECONDS}s")
        service.logger.info(f"Minimum new audio: {MINIMUM_NEW_AUDIO_SECONDS}s")
        service.logger.info(f"Session expiration: {SESSION_EXPIRATION_SECONDS}s")

        # Print initialization variables
        buffer_size = int(MAX_AUDIO_BUFFER_SECONDS * SAMPLE_RATE * 2)  # Calculate buffer size in bytes
        service.logger.info("Gateway initialization complete")
        service.logger.info(f"Audio Configuration: SAMPLE_RATE={SAMPLE_RATE}, BUFFER_SIZE={buffer_size}")
        service.logger.info(f"VAD Configuration: WEBRTC_SENSITIVITY={WEBRTC_SENSITIVITY}, SILERO_SENSITIVITY={SILERO_SENSITIVITY}")
        service.logger.info(f"Buffer Configuration: PRE_SPEECH_BUFFER_SECONDS={PRE_SPEECH_BUFFER_SECONDS}, MINIMUM_NEW_AUDIO_SECONDS={MINIMUM_NEW_AUDIO_SECONDS}, MAX_AUDIO_BUFFER_SECONDS={MAX_AUDIO_BUFFER_SECONDS}")
        service.logger.info(f"Audio Enhancement: ENABLED={ENABLE_AUDIO_ENHANCEMENT}, VOLUME_BOOST={AUDIO_VOLUME_BOOST_DB}dB")

        # Start WebSocket server
        server = await websockets.serve(
            service.handle_client,
            "0.0.0.0",
            GATEWAY_PORT,
            max_size=None
        )

        await server.wait_closed()

    except Exception as e:
        service.logger.error(f"Gateway startup error: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    asyncio.run(main())

