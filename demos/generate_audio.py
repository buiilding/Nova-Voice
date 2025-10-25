#!/usr/bin/env python3
"""
generate_audio.py - Generate test audio files for demo

This script generates synthetic audio files for testing the speech microservices.
"""

import numpy as np
import wave
import struct
import os

def generate_sine_wave(frequency, duration, sample_rate=16000, amplitude=0.5):
    """Generate a sine wave"""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    return amplitude * np.sin(2 * np.pi * frequency * t)

def generate_speech_like_audio(duration, sample_rate=16000):
    """Generate speech-like audio with varying frequencies"""
    audio = np.zeros(int(sample_rate * duration))

    # Mix different frequencies to simulate speech
    frequencies = [200, 400, 800, 1200, 2400]  # Formant frequencies
    for freq in frequencies:
        audio += generate_sine_wave(freq, duration, sample_rate, 0.1)

    # Add some noise
    noise = np.random.normal(0, 0.05, len(audio))
    audio += noise

    # Normalize
    audio = audio / np.max(np.abs(audio)) * 0.7

    return audio

def save_wav(filename, audio, sample_rate=16000):
    """Save audio as WAV file"""
    # Convert to int16
    audio_int16 = (audio * 32767).astype(np.int16)

    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())

def create_test_audio_files():
    """Create test audio files"""
    test_phrases = [
        ("hello_world", 2.0),
        ("how_are_you", 2.5),
        ("thank_you", 1.5),
        ("good_morning", 2.0),
        ("i_love_programming", 3.0),
        ("the_weather_is_nice", 2.5),
        ("can_you_help_me", 2.0),
        ("what_time_is_it", 2.0)
    ]

    os.makedirs("sample_audio", exist_ok=True)

    print("Generating test audio files...")

    for phrase_name, duration in test_phrases:
        # Generate speech-like audio
        audio = generate_speech_like_audio(duration)

        filename = f"sample_audio/{phrase_name}.wav"
        save_wav(filename, audio)

        print(f"Created {filename} ({duration}s)")

    print("\nAudio files generated in sample_audio/ directory")
    print("You can use these files with the demo client or modify the client to read real audio files.")

if __name__ == "__main__":
    create_test_audio_files()

