"""
model_manager.py - Model management for STT Worker

Handles Faster-Whisper model loading, initialization, and management.
Provides methods for model validation and warm-up.
"""

import time
import numpy as np
import logging
from faster_whisper import WhisperModel
from typing import Optional, Tuple, List

from .config import (
    MODEL_SIZE, DEVICE, COMPUTE_TYPE, DOWNLOAD_ROOT,
    BEAM_SIZE, BEST_OF
)


class STTModelManager:
    """Manages the Faster-Whisper model lifecycle"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.model: Optional[WhisperModel] = None

    def load_model(self) -> WhisperModel:
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
            self._warm_up_model()

            load_time = time.time() - start_time
            self.logger.info(f"Model loaded and warmed up successfully in {load_time:.2f}s")
            return self.model

        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            raise

    def _warm_up_model(self):
        """Warm up the model with dummy audio to ensure it's ready"""
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

    def is_model_loaded(self) -> bool:
        """Check if the model is loaded and ready"""
        return self.model is not None

    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        if not self.model:
            return {"loaded": False}

        return {
            "loaded": True,
            "model_size": MODEL_SIZE,
            "device": DEVICE,
            "compute_type": COMPUTE_TYPE
        }
