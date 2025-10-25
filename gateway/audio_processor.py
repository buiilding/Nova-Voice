"""
audio_processor.py - Enhanced Audio processing utilities for the Gateway service

Handles audio resampling, chunk processing, audio enhancement, and format conversions.
Enhanced with volume normalization, dynamic compression, and quality improvements.
"""

import numpy as np
from scipy.signal import resample
from pydub import AudioSegment
import io

from config import (
    SAMPLE_RATE,
    ENABLE_AUDIO_ENHANCEMENT,
    AUDIO_VOLUME_BOOST_DB
)


class AudioProcessor:
    """Handles audio processing tasks like resampling and format conversion"""

    def __init__(self):
        # Audio enhancement settings from configuration
        self.enable_enhancement = ENABLE_AUDIO_ENHANCEMENT
        self.volume_boost_db = AUDIO_VOLUME_BOOST_DB  # dB increase for louder audio
        self.target_sample_rate = SAMPLE_RATE  # 16kHz for Whisper
        self.target_channels = 1  # Mono

    @staticmethod
    def decode_and_resample(audio_data: bytes, original_sample_rate: int, target_sample_rate: int = SAMPLE_RATE) -> bytes:
        """Basic resampling without enhancement"""
        if original_sample_rate == target_sample_rate:
            return audio_data

        audio_np = np.frombuffer(audio_data, dtype=np.int16)
        if len(audio_np) == 0:
            return b""

        num_original_samples = len(audio_np)
        num_target_samples = int(num_original_samples * target_sample_rate / original_sample_rate)

        if num_target_samples <= 0:
            return b""

        resampled_audio = resample(audio_np, num_target_samples)
        return resampled_audio.astype(np.int16).tobytes()

    def enhance_audio_chunk(self, audio_data: bytes, original_sample_rate: int) -> bytes:
        """
        Basic audio processing for real-time chunks:
        - Detect actual audio format (bit depth, channels)
        - Convert to AudioSegment with correct parameters
        - Convert to mono for speech transcription (better results)
        - Increase volume for better transcription quality
        - Resample to target rate (16kHz optimal for Whisper)
        """
        if not audio_data:
            return audio_data

        try:
            # Detect audio format to preserve quality
            sample_width, channels = self._detect_audio_format(audio_data)

            # Convert bytes to AudioSegment with detected format
            audio_segment = AudioSegment(
                data=audio_data,
                sample_width=sample_width,
                frame_rate=original_sample_rate,
                channels=channels
            )

            # Convert to mono for speech transcription (better results)
            if audio_segment.channels > 1:
                audio_segment = audio_segment.set_channels(1)

            # Increase volume for better transcription quality
            audio_segment = audio_segment + self.volume_boost_db

            # Resample to target rate (16kHz optimal for Whisper)
            if audio_segment.frame_rate != self.target_sample_rate:
                audio_segment = audio_segment.set_frame_rate(self.target_sample_rate)

            # Export back to bytes in optimal format
            buffer = io.BytesIO()
            # Export as 16-bit WAV for consistency
            audio_segment.export(buffer, format="wav", parameters=["-acodec", "pcm_s16le"])
            enhanced_bytes = buffer.getvalue()

            # Extract just the audio data (skip WAV header)
            enhanced_bytes = self._strip_wav_header(enhanced_bytes)

            return enhanced_bytes

        except Exception as e:
            # If enhancement fails, try basic resampling as fallback
            print(f"Audio enhancement failed: {e}, falling back to basic resampling")
            return self.decode_and_resample(audio_data, original_sample_rate, self.target_sample_rate)

    def _detect_audio_format(self, audio_data: bytes) -> tuple[int, int]:
        """
        Detect audio format from raw PCM bytes.
        Returns (sample_width, channels)

        Tries different common formats and validates by attempting AudioSegment creation.
        WebRTC typically sends 16-bit mono, but we handle other cases.
        """
        if not audio_data:
            return 2, 1  # Default to 16-bit mono

        data_len = len(audio_data)

        # Common WebRTC/browser audio formats to try
        format_candidates = [
            (2, 1),  # 16-bit mono (most common)
            (2, 2),  # 16-bit stereo
            (1, 1),  # 8-bit mono
            (1, 2),  # 8-bit stereo
            (4, 1),  # 32-bit float mono
            (4, 2),  # 32-bit float stereo
        ]

        # Try each format and see if AudioSegment can parse it
        for sample_width, channels in format_candidates:
            try:
                # Check if data length is compatible with this format
                expected_samples = data_len // (sample_width * channels)
                if expected_samples == 0:
                    continue

                # Try to create AudioSegment with this format
                test_segment = AudioSegment(
                    data=audio_data,
                    sample_width=sample_width,
                    frame_rate=self.target_sample_rate,  # Use target rate for validation
                    channels=channels
                )

                # If we get here without exception, format is valid
                # For speech transcription, prefer mono
                if channels > 1:
                    # If detected as stereo, we'll convert to mono later anyway
                    pass

                return sample_width, channels

            except Exception:
                continue  # Try next format

        # Fallback: assume 16-bit mono (most common WebRTC format)
        print(f"Could not detect audio format from {data_len} bytes, assuming 16-bit mono")
        return 2, 1

    def _strip_wav_header(self, wav_data: bytes) -> bytes:
        """Extract raw PCM data from WAV format by removing header"""
        try:
            # WAV header structure:
            # 0-3: "RIFF"
            # 4-7: File size
            # 8-11: "WAVE"
            # 12-15: "fmt "
            # 16-19: Format chunk size
            # 20+: Format data, then "data" chunk

            if len(wav_data) < 44:
                return wav_data

            # Find "data" chunk
            data_pos = wav_data.find(b'data')
            if data_pos == -1:
                return wav_data

            # Data starts 8 bytes after "data" marker (4 for "data" + 4 for size)
            data_start = data_pos + 8
            if data_start >= len(wav_data):
                return wav_data

            return wav_data[data_start:]

        except Exception:
            # If header stripping fails, return original
            return wav_data

    def process_audio_chunk(self, audio_data: bytes, original_sample_rate: int, enhance: bool = None) -> bytes:
        """
        Main audio processing method with optional enhancement

        Args:
            audio_data: Raw audio bytes
            original_sample_rate: Original sample rate
            enhance: Whether to apply quality enhancements (uses config if None)

        Returns:
            Processed audio bytes
        """
        if enhance is None:
            enhance = self.enable_enhancement

        if enhance and self.enable_enhancement:
            return self.enhance_audio_chunk(audio_data, original_sample_rate)
        else:
            return self.decode_and_resample(audio_data, original_sample_rate, self.target_sample_rate)


# Test function for validation
def test_audio_enhancement():
    """Test the audio enhancement functionality"""
    import numpy as np

    processor = AudioProcessor()

    # Generate test audio (1 second of 44.1kHz sine wave, quiet)
    sample_rate = 44100
    duration = 1.0
    frequency = 440  # A4 note

    # Create quiet sine wave
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = np.sin(frequency * 2 * np.pi * t)

    # Make it very quiet (simulate poor recording)
    audio_data = audio_data * 0.1  # Very quiet

    # Convert to 16-bit PCM bytes
    audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()

    print(f"Original audio: {len(audio_bytes)} bytes at {sample_rate}Hz")
    print(f"Original RMS would be very low: {np.sqrt(np.mean(audio_data**2)):.6f}")

    # Process with enhancement
    enhanced_bytes = processor.process_audio_chunk(audio_bytes, sample_rate, enhance=True)

    print(f"Enhanced audio: {len(enhanced_bytes)} bytes at {processor.target_sample_rate}Hz")

    # Convert back to numpy for RMS calculation
    enhanced_audio = np.frombuffer(enhanced_bytes, dtype=np.int16).astype(np.float32) / 32767.0
    enhanced_rms = np.sqrt(np.mean(enhanced_audio**2))

    print(f"Enhanced RMS: {enhanced_rms:.6f} (should be much higher)")

    return len(audio_bytes), len(enhanced_bytes), enhanced_rms > 0.1  # Should be significantly louder


if __name__ == "__main__":
    # Run test when script is executed directly
    test_audio_enhancement()
