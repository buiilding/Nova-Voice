"""
config.py - Configuration constants and settings for the Translation Worker service

Centralized configuration management for the translation worker service.
Contains all environment variables, constants, and validation logic.
"""

import os


# === Redis Configuration ===
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
WORKER_ID = os.getenv("WORKER_ID", f"translation-{os.getpid()}")
CONSUMER_GROUP = os.getenv("CONSUMER_GROUP", "translation_workers")

# Redis Streams
TRANSCRIPTIONS_STREAM = os.getenv("TRANSCRIPTIONS_STREAM", "transcriptions")
RESULTS_CHANNEL_PREFIX = "results:"

# === Model Configuration ===
NLLB_MODEL = os.getenv("NLLB_MODEL", "facebook/nllb-200-distilled-600M")
DEVICE = "cuda" if os.getenv("FORCE_CPU", "false").lower() != "true" else "cpu"

# === Worker Configuration ===
HEALTH_PORT = int(os.getenv("HEALTH_PORT_TRANSLATION", "8082"))

# === Translation Configuration ===
MAX_SEQUENCE_LENGTH = int(os.getenv("MAX_SEQUENCE_LENGTH", "512"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1"))


def validate_configuration():
    """Validate configuration and provide helpful error messages"""
    issues = []

    # Validate Redis URL
    if not REDIS_URL or not REDIS_URL.startswith("redis://"):
        issues.append(f"Invalid REDIS_URL: {REDIS_URL}. Must start with 'redis://'")

    # Validate model name
    if not NLLB_MODEL or not NLLB_MODEL.startswith("facebook/nllb"):
        issues.append(f"Invalid NLLB_MODEL: {NLLB_MODEL}. Should be a valid NLLB model name")

    # Validate device
    valid_devices = ["cpu", "cuda"]
    if DEVICE not in valid_devices:
        issues.append(f"Invalid DEVICE: {DEVICE}. Must be one of: {', '.join(valid_devices)}")

    # Validate health port
    if not (1024 <= HEALTH_PORT <= 65535):
        issues.append(f"Invalid HEALTH_PORT: {HEALTH_PORT}. Must be between 1024 and 65535")

    # Validate sequence length
    if MAX_SEQUENCE_LENGTH <= 0:
        issues.append(f"Invalid MAX_SEQUENCE_LENGTH: {MAX_SEQUENCE_LENGTH}. Must be > 0")

    return issues


def print_configuration():
    """Print current configuration for debugging"""
    print("=== Translation Worker Configuration ===")
    print(f"Redis URL: {REDIS_URL}")
    print(f"Worker ID: {WORKER_ID}")
    print(f"Consumer Group: {CONSUMER_GROUP}")
    print(f"NLLB Model: {NLLB_MODEL}")
    print(f"Device: {DEVICE}")
    print(f"Max Sequence Length: {MAX_SEQUENCE_LENGTH}")
    print(f"Batch Size: {BATCH_SIZE}")
    print(f"Health Port: {HEALTH_PORT}")
    print("=======================================")
