"""
translator.py - Translation logic for Translation Worker

Handles text translation using NLLB model with proper language mapping
and memory management.
"""

import torch
import logging
from typing import Optional, Dict, Any
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from .config import DEVICE
from .language_mappings import get_nllb_code


class Translator:
    """Handles text translation using NLLB model"""

    def __init__(self, model: AutoModelForSeq2SeqLM, tokenizer: AutoTokenizer, logger: logging.Logger):
        self.model = model
        self.tokenizer = tokenizer
        self.logger = logger

    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translate text from source language to target language

        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            Translated text
        """
        try:
            # Map language codes to NLLB format
            mapped_source = get_nllb_code(source_lang)
            mapped_target = get_nllb_code(target_lang)

            self.logger.debug(f"Translating: {source_lang} ({mapped_source}) -> {target_lang} ({mapped_target})")

            # Tokenize input
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            )

            # Move to device
            if DEVICE == "cuda":
                inputs = {k: v.to(DEVICE) for k, v in inputs.items()}

            # Set forced target language
            forced_bos_token_id = self.tokenizer.convert_tokens_to_ids(mapped_target)

            # Generate translation
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    forced_bos_token_id=forced_bos_token_id,
                    max_length=512,
                    num_beams=4,
                    early_stopping=True,
                    do_sample=False
                )

            # Decode output
            translated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            self.logger.debug(f"Translation result: '{text}' -> '{translated_text}'")
            return translated_text

        except Exception as e:
            self.logger.error(f"Translation error for '{text}': {e}")
            raise

    def get_supported_languages(self) -> list:
        """Get list of supported language codes"""
        # This would be expanded based on NLLB capabilities
        return [
            "en", "es", "fr", "de", "it", "pt", "ru", "ja", "zh", "ko",
            "ar", "hi", "vi", "nl", "sv", "cs", "pl", "tr", "uk", "ro"
        ]
