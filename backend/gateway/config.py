"""
config.py - Configuration constants and settings for the Gateway service

Centralized configuration management for the realtime speech gateway service.
Contains all environment variables, constants, and language mappings.
"""

import os

# === Redis Configuration ===
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# === Gateway Configuration ===
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "5026"))
HEALTH_PORT = int(os.getenv("HEALTH_PORT", "8080"))

# === VAD Configuration (Dual VAD system) ===
SILENCE_THRESHOLD_SECONDS = float(os.getenv("SILENCE_THRESHOLD_SECONDS", "1.0"))
SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", "16000"))
# Removed unused SILENCE_RATIO_THRESHOLD

# Dual VAD parameters (matching audio_recorder.py)
WEBRTC_SENSITIVITY = int(os.getenv("WEBRTC_SENSITIVITY", "3"))  # 0-3, 3=most aggressive
SILERO_SENSITIVITY = float(os.getenv("SILERO_SENSITIVITY", "0.7"))  # 0.0-1.0, higher=more sensitive
INT16_MAX_ABS_VALUE = 32768.0

# === Redis Streams/Queues ===
AUDIO_JOBS_STREAM = "audio_jobs"
RESULTS_CHANNEL_PREFIX = "results:"
SESSION_PREFIX = "session:"

# === Batch and timing configuration ===
PRE_SPEECH_BUFFER_SECONDS = float(os.getenv("PRE_SPEECH_BUFFER_SECONDS", "2.0"))  # Include N seconds of audio before speech detection
MINIMUM_NEW_AUDIO_SECONDS = float(os.getenv("MINIMUM_NEW_AUDIO_SECONDS", "1.0"))  # Minimum new audio seconds required before sending a job #lower = more realtime
MAX_QUEUE_DEPTH = int(os.getenv("MAX_QUEUE_DEPTH", "100"))
# Max audio buffer duration in seconds (hard limit). The longer the buffer, the more latency.
MAX_AUDIO_BUFFER_SECONDS = float(os.getenv("MAX_AUDIO_BUFFER_SECONDS", "10.0"))
# Whether to send a final job when max audio buffer is exceeded
SEND_FINAL_JOB_ON_MAX_BUFFER = True  # Set to True (recommended) (this means including the last audio chunk (silent chunks (possibly having some more speech though))) and send as a final job

# === Language configuration ===
DEFAULT_SOURCE_LANGUAGE = os.getenv("DEFAULT_SOURCE_LANGUAGE", "en")
DEFAULT_TARGET_LANGUAGE = os.getenv("DEFAULT_TARGET_LANGUAGE", "vi")

# === Session configuration ===
SESSION_EXPIRATION_SECONDS = int(os.getenv("SESSION_EXPIRATION_SECONDS", "900"))  # 15 minutes default

# === Audio enhancement configuration ===
ENABLE_AUDIO_ENHANCEMENT = os.getenv("ENABLE_AUDIO_ENHANCEMENT", "true").lower() == "true"
AUDIO_VOLUME_BOOST_DB = float(os.getenv("AUDIO_VOLUME_BOOST_DB", "7.0"))  # dB increase for louder audio


