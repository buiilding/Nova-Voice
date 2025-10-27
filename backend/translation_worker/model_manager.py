"""
model_manager.py - Model management for Translation Worker

Handles NLLB model loading, initialization, and management.
Provides methods for model validation and memory management.
"""

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import logging
from typing import Optional, Tuple

from config import NLLB_MODEL, DEVICE, MAX_SEQUENCE_LENGTH


class TranslationModelManager:
    """Manages the NLLB translation model lifecycle"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.model: Optional[AutoModelForSeq2SeqLM] = None
        self.tokenizer: Optional[AutoTokenizer] = None

    def load_model(self) -> Tuple[AutoModelForSeq2SeqLM, AutoTokenizer]:
        """Load the NLLB model and tokenizer"""
        try:
            self.logger.info(f"Loading NLLB model: {NLLB_MODEL} on {DEVICE}")

            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(NLLB_MODEL)

            # Load model
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                NLLB_MODEL,
                torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
                device_map="auto" if DEVICE == "cuda" else None,
                max_memory={0: "4GB", "cpu": "8GB"} if DEVICE == "cuda" else None
            )

            # Move to device if not using device_map
            if DEVICE == "cuda" and not hasattr(self.model, 'hf_device_map'):
                self.model = self.model.to(DEVICE)

            # Set model to evaluation mode
            self.model.eval()

            self.logger.info(f"Model loaded successfully on {DEVICE}")
            return self.model, self.tokenizer

        except Exception as e:
            self.logger.error(f"Error loading NLLB model: {e}")
            raise

    def is_model_loaded(self) -> bool:
        """Check if the model is loaded and ready"""
        return self.model is not None and self.tokenizer is not None

    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        if not self.is_model_loaded():
            return {"loaded": False}

        return {
            "loaded": True,
            "model_name": NLLB_MODEL,
            "device": DEVICE,
            "max_sequence_length": MAX_SEQUENCE_LENGTH,
            "model_parameters": sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        }

    def get_max_sequence_length(self) -> int:
        """Get the maximum sequence length for the model"""
        return MAX_SEQUENCE_LENGTH
