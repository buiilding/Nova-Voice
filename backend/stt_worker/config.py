"""
config.py - Configuration constants and settings for the STT Worker service

Centralized configuration management for the STT worker service.
Contains all environment variables, constants, and validation logic.
"""

import os


# === Redis Configuration ===
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
WORKER_ID = os.getenv("WORKER_ID", f"stt-{os.getpid()}")
CONSUMER_GROUP = os.getenv("CONSUMER_GROUP", "stt_workers")

# Redis Streams
AUDIO_JOBS_STREAM = "audio_jobs"
RESULTS_CHANNEL_PREFIX = "results:"
TRANSCRIPTIONS_STREAM = os.getenv("TRANSCRIPTIONS_STREAM", "transcriptions")

# === Model Configuration ===
MODEL_SIZE = os.getenv("MODEL_SIZE", "large-v3")
DEVICE = os.getenv("DEVICE", "cuda")
COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "int8_float16" if DEVICE == "cuda" else "int8")
DOWNLOAD_ROOT = os.getenv("DOWNLOAD_ROOT")

# === Transcription Parameters ===
BEAM_SIZE = int(os.getenv("BEAM_SIZE", "1"))
INITIAL_PROMPT = os.getenv("INITIAL_PROMPT")
SUPPRESS_TOKENS = [-1]  # was []
VAD_FILTER = os.getenv("VAD_FILTER", "false").lower() == "true"
BEST_OF = int(os.getenv("BEST_OF", "1"))

# === Worker Configuration ===
PENDING_ACK_TTL = int(os.getenv("PENDING_ACK_TTL", "300"))  # 5 minutes

# === Health Check Configuration ===
HEALTH_PORT = int(os.getenv("HEALTH_PORT_STT", "8081"))


def validate_configuration():
    """Validate configuration and provide helpful error messages"""
    issues = []

    # Validate Redis URL
    if not REDIS_URL or not REDIS_URL.startswith("redis://"):
        issues.append(f"Invalid REDIS_URL: {REDIS_URL}. Must start with 'redis://'")

    # Validate model size
    valid_model_sizes = ["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3"]
    if MODEL_SIZE not in valid_model_sizes:
        issues.append(f"Invalid MODEL_SIZE: {MODEL_SIZE}. Must be one of: {', '.join(valid_model_sizes)}")

    # Validate device
    valid_devices = ["cpu", "cuda"]
    if DEVICE not in valid_devices:
        issues.append(f"Invalid DEVICE: {DEVICE}. Must be one of: {', '.join(valid_devices)}")

    # Validate beam size
    if BEAM_SIZE < 1:
        issues.append(f"Invalid BEAM_SIZE: {BEAM_SIZE}. Must be >= 1")

    # Validate health port
    if not (1024 <= HEALTH_PORT <= 65535):
        issues.append(f"Invalid HEALTH_PORT: {HEALTH_PORT}. Must be between 1024 and 65535")

    return issues


def print_configuration():
    """Print current configuration for debugging"""
    print("=== STT Worker Configuration ===")
    print(f"Redis URL: {REDIS_URL}")
    print(f"Worker ID: {WORKER_ID}")
    print(f"Consumer Group: {CONSUMER_GROUP}")
    print(f"Model Size: {MODEL_SIZE}")
    print(f"Device: {DEVICE}")
    print(f"Compute Type: {COMPUTE_TYPE}")
    print(f"Beam Size: {BEAM_SIZE}")
    print(f"VAD Filter: {VAD_FILTER}")
    print(f"Best Of: {BEST_OF}")
    print(f"Health Port: {HEALTH_PORT}")
    print("===============================")
