"""
audio_processor.py - Audio processing and transcription for STT Worker

Handles audio data conversion, transcription using Faster-Whisper,
and result formatting.
"""

import time
import numpy as np
import logging
from typing import Dict, Any, Optional
from faster_whisper import WhisperModel

from config import (
    BEAM_SIZE, INITIAL_PROMPT, SUPPRESS_TOKENS, BEST_OF, VAD_FILTER
)


class AudioProcessor:
    """Handles audio transcription using Faster-Whisper"""

    def __init__(self, model: WhisperModel, logger: logging.Logger):
        self.model = model
        self.logger = logger

    def transcribe_audio(self, audio_data: bytes, language: str = "", use_vad_filter: Optional[bool] = None) -> Dict[str, Any]:
        """
        Transcribe audio data to text

        Args:
            audio_data: Raw audio bytes (16-bit PCM)
            language: Language code (optional, auto-detect if empty)
            use_vad_filter: Whether to use VAD filtering (uses config default if None)

        Returns:
            Dict containing transcription results and metadata
        """
        try:
            start_time = time.time()

            # Calculate audio duration (16kHz, int16 format = 2 bytes per sample)
            audio_duration = len(audio_data) / (2 * 16000)

            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            audio_float = audio_array.astype(np.float32) / 32768.0

            # Use VAD filter from config if not specified
            vad_filter = use_vad_filter if use_vad_filter is not None else VAD_FILTER

            # Transcribe
            segments, info = self.model.transcribe(
                audio_float,
                language=language if language else None,
                beam_size=BEAM_SIZE,
                initial_prompt=INITIAL_PROMPT,
                suppress_tokens=SUPPRESS_TOKENS,
                best_of=BEST_OF,
                temperature=0,
                vad_filter=vad_filter
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
