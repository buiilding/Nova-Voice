#!/usr/bin/env python3
"""
debug_audio_monitor.py - Debug tool to monitor and save audio sent to workers

This script monitors the Redis audio_jobs stream and saves all audio chunks
to WAV files for analysis and debugging.

Usage:
    python debug_audio_monitor.py [options]

Options:
    --save-dir DIR    Save audio chunks to directory (default: debug_audio)
    --client-id ID    Monitor specific client only
    --quiet           Suppress verbose output
    --help            Show this help message

Requirements:
    pip install redis[hiredis] numpy scipy
"""

import redis
import base64
import os
import time
import wave

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
AUDIO_JOBS_STREAM = "audio_jobs"
DEBUG_AUDIO_DIR = "debug_audio"
SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 2 bytes for 16-bit audio

def save_audio_chunk(client_id, audio_bytes, segment_id):
    """Saves an audio chunk to a WAV file."""
    if not os.path.exists(DEBUG_AUDIO_DIR):
        os.makedirs(DEBUG_AUDIO_DIR)

    timestamp = int(time.time() * 1000)
    filename = f"{timestamp}_{segment_id}_{client_id}.wav"
    filepath = os.path.join(DEBUG_AUDIO_DIR, filename)

    try:
        with wave.open(filepath, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(SAMPLE_WIDTH)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_bytes)
        print(f"Saved audio chunk to {filepath}")
    except Exception as e:
        print(f"Error saving audio chunk: {e}")

def listen_for_audio_jobs():
    """Listens to the Redis stream for audio jobs and saves the audio."""
    print(f"Connecting to Redis at {REDIS_URL}...")
    r = redis.from_url(REDIS_URL)
    print("Connected to Redis.")
    print(f"Listening for audio jobs on stream '{AUDIO_JOBS_STREAM}'...")

    last_id = '$'  # Start listening for new messages
    while True:
        try:
            # Block and wait for new messages
            response = r.xread({AUDIO_JOBS_STREAM: last_id}, block=0, count=1)
            if response:
                stream, messages = response[0]
                last_id, job_data = messages[0]
                
                # Decode job data from bytes
                decoded_job_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in job_data.items()}

                if 'audio_bytes_b64' in decoded_job_data:
                    client_id = decoded_job_data.get('client_id', 'unknown_client')
                    segment_id = decoded_job_data.get('segment_id', 'unknown_segment')
                    audio_b64 = decoded_job_data['audio_bytes_b64']
                    
                    try:
                        audio_bytes = base64.b64decode(audio_b64)
                        save_audio_chunk(client_id, audio_bytes, segment_id)
                    except (base64.binascii.Error, ValueError) as e:
                        print(f"Error decoding base64 audio data: {e}")
                
        except redis.exceptions.ConnectionError as e:
            print(f"Redis connection error: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)
            # Re-initialize connection
            r = redis.from_url(REDIS_URL)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            time.sleep(5)


if __name__ == "__main__":
    listen_for_audio_jobs()