"""
language_mappings.py - Language Code Mappings for NLLB-200

Maps two-character ISO 639-1 language codes to NLLB-200 BCP-47 format codes.
NLLB-200 uses the format: {iso639-3}_{script}

Format explanation:
- ISO 639-3: Three-letter language code
- Script: Four-letter script code (Latn, Hans, Hant, Jpan, Cyrl, Arab, etc.)

Reference: https://huggingface.co/facebook/nllb-200-distilled-600M/blob/main/special_tokens_map.json
"""

# Language mapping for NLLB-200 translation
LANGUAGE_MAPPING = {
    # Two-char code -> NLLB-200 BCP-47 format
    "en": "eng_Latn",      # English (Latin script)
    "es": "spa_Latn",      # Spanish (Latin script)
    "fr": "fra_Latn",      # French (Latin script)
    "de": "deu_Latn",      # German (Latin script)
    "vi": "vie_Latn",      # Vietnamese (Latin script)
    "zh": "zho_Hans",      # Chinese Simplified (Hans script)
    "ja": "jpn_Jpan",      # Japanese (Japanese script)
    "hi": "hin_Deva",      # Hindi (Devanagari script)
}

# Additional supported languages (for reference/future expansion)
# Uncomment and add to LANGUAGE_MAPPING if needed
ADDITIONAL_LANGUAGES = {
    # Major European languages
    "it": "ita_Latn",      # Italian
    "pt": "por_Latn",      # Portuguese
    "nl": "nld_Latn",      # Dutch
    "pl": "pol_Latn",      # Polish
    "ru": "rus_Cyrl",      # Russian
    "uk": "ukr_Cyrl",      # Ukrainian
    "tr": "tur_Latn",      # Turkish
    "sv": "swe_Latn",      # Swedish
    "da": "dan_Latn",      # Danish
    "no": "nob_Latn",      # Norwegian Bokmål
    "fi": "fin_Latn",      # Finnish
    "el": "ell_Grek",      # Greek
    "cs": "ces_Latn",      # Czech
    "ro": "ron_Latn",      # Romanian
    
    # Asian languages
    "ko": "kor_Hang",      # Korean
    "th": "tha_Thai",      # Thai
    "id": "ind_Latn",      # Indonesian
    "bn": "ben_Beng",      # Bengali
    "ta": "tam_Taml",      # Tamil
    "te": "tel_Telu",      # Telugu
    "ur": "urd_Arab",      # Urdu
    "ar": "arb_Arab",      # Arabic (Standard)
    "he": "heb_Hebr",      # Hebrew
    
    # Chinese variants
    "zh-tw": "zho_Hant",   # Chinese Traditional
    "zh-cn": "zho_Hans",   # Chinese Simplified
}


def get_supported_languages():
    """
    Get list of all supported two-character language codes.
    
    Returns:
        list: List of supported language codes
    """
    return list(LANGUAGE_MAPPING.keys())


def get_nllb_code(lang_code: str) -> str:
    """
    Convert two-character language code to NLLB-200 format.
    
    Args:
        lang_code: Two-character ISO 639-1 code (e.g., 'en', 'vi')
        
    Returns:
        NLLB-200 BCP-47 format code (e.g., 'eng_Latn', 'vie_Latn')
        Returns original code if not found in mapping
    """
    return LANGUAGE_MAPPING.get(lang_code.lower(), lang_code)


def validate_language_pair(src_lang: str, tgt_lang: str) -> tuple[bool, str]:
    """
    Validate if a language pair is supported.
    
    Args:
        src_lang: Source language two-character code
        tgt_lang: Target language two-character code
        
    Returns:
        tuple: (is_valid, error_message)
    """
    supported = get_supported_languages()
    
    if src_lang.lower() not in supported:
        return False, f"Source language '{src_lang}' not supported. Supported: {supported}"
    
    if tgt_lang.lower() not in supported:
        return False, f"Target language '{tgt_lang}' not supported. Supported: {supported}"
    
    return True, ""


# Language names for display purposes
LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "vi": "Vietnamese",
    "zh": "Chinese (Simplified)",
    "ja": "Japanese",
    "hi": "Hindi",
}