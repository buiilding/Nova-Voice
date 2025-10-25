"""
session.py - Session management for the Gateway service

Contains the SpeechSession dataclass, SpeechState enum, and session persistence logic.
Handles session state transitions and Redis-based session storage.
"""

import time
import base64
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

from config import SESSION_PREFIX, SILENCE_THRESHOLD_SECONDS, SAMPLE_RATE, DEFAULT_SOURCE_LANGUAGE, DEFAULT_TARGET_LANGUAGE


class SpeechState(Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    SILENCE = "silence"


@dataclass
class SpeechSession:
    state: SpeechState = SpeechState.INACTIVE
    audio_buffer: bytearray = None
    pre_speech_buffer: bytearray = None  # Rolling buffer for audio before speech detection
    silence_start_time: Optional[float] = None
    session_start_time: Optional[float] = None
    accumulated_audio_bytes: int = 0
    last_stt_send_time: Optional[float] = None
    last_published_len: int = 0
    silence_buffer_start_len: int = 0  # Buffer length when silence started (for excluding silence from threshold calc)
    source_lang: str = DEFAULT_SOURCE_LANGUAGE
    target_lang: str = DEFAULT_TARGET_LANGUAGE
    translation_enabled: bool = True

    def __post_init__(self):
        if self.audio_buffer is None:
            self.audio_buffer = bytearray()
        if self.pre_speech_buffer is None:
            self.pre_speech_buffer = bytearray()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for Redis storage (excludes audio buffers)"""
        data = asdict(self)
        # Remove audio buffers from dict - they'll be stored separately
        data.pop('audio_buffer', None)
        data.pop('pre_speech_buffer', None)
        data['state'] = self.state.value
        # Convert boolean to string for Redis compatibility
        data['translation_enabled'] = str(data['translation_enabled'])

        # Convert all values to strings for Redis compatibility
        for key, value in data.items():
            if value is None:
                data[key] = ""
            elif isinstance(value, (int, float)):
                data[key] = str(value)
            elif isinstance(value, bool):
                data[key] = str(value)
            elif not isinstance(value, str):
                data[key] = str(value)

        return data

    def get_audio_buffers(self) -> Dict[str, bytes]:
        """Get audio buffers as binary data for separate storage"""
        return {
            'audio_buffer': bytes(self.audio_buffer),
            'pre_speech_buffer': bytes(self.pre_speech_buffer)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], audio_buffers: Optional[Dict[str, bytes]] = None) -> 'SpeechSession':
        """Create from dict loaded from Redis"""
        # Audio buffers are now passed separately as binary data
        if audio_buffers:
            data['audio_buffer'] = bytearray(audio_buffers.get('audio_buffer', b''))
            data['pre_speech_buffer'] = bytearray(audio_buffers.get('pre_speech_buffer', b''))
        else:
            # Fallback for backward compatibility
            if 'audio_buffer' in data and isinstance(data['audio_buffer'], str):
                data['audio_buffer'] = bytearray(base64.b64decode(data['audio_buffer']))
            else:
                data['audio_buffer'] = bytearray()
            if 'pre_speech_buffer' in data and isinstance(data['pre_speech_buffer'], str):
                data['pre_speech_buffer'] = bytearray(base64.b64decode(data['pre_speech_buffer']))
            else:
                data['pre_speech_buffer'] = bytearray()

        if 'state' in data:
            data['state'] = SpeechState(data['state'])

        # Convert strings back to appropriate types
        if 'translation_enabled' in data:
            data['translation_enabled'] = data['translation_enabled'].lower() == 'true'

        # Convert numeric strings back to numbers
        if 'accumulated_audio_bytes' in data:
            try:
                data['accumulated_audio_bytes'] = int(data['accumulated_audio_bytes'])
            except (ValueError, TypeError):
                data['accumulated_audio_bytes'] = 0

        if 'last_published_len' in data:
            try:
                data['last_published_len'] = int(data['last_published_len'])
            except (ValueError, TypeError):
                data['last_published_len'] = 0

        if 'silence_buffer_start_len' in data:
            try:
                data['silence_buffer_start_len'] = int(data['silence_buffer_start_len'])
            except (ValueError, TypeError):
                data['silence_buffer_start_len'] = 0

        # Convert empty strings back to None for Optional[float] fields
        for key in ['silence_start_time', 'session_start_time', 'last_stt_send_time']:
            if key in data and data[key] == "":
                data[key] = None
            elif key in data and data[key] != "":
                try:
                    data[key] = float(data[key])
                except (ValueError, TypeError):
                    data[key] = None

        return cls(**data)

    def reset(self):
        """Reset session state (kept for backward compatibility)"""
        self.end_speech_session()

    def start_speech(self):
        self.state = SpeechState.ACTIVE
        self.session_start_time = time.time()
        self.silence_start_time = None
        self.silence_buffer_start_len = 0
        self.last_published_len = 0

    def detect_silence(self):
        if self.state == SpeechState.ACTIVE:
            self.state = SpeechState.SILENCE
            self.silence_start_time = time.time()

    def is_silence_timeout(self) -> bool:
        """Check if silence has been consistent for the full threshold duration"""
        if self.silence_start_time is None:
            return False
        return (time.time() - self.silence_start_time) >= SILENCE_THRESHOLD_SECONDS

    def end_speech_session(self):
        """Properly end speech session and clear all state"""
        self.state = SpeechState.INACTIVE
        self.audio_buffer.clear()
        self.pre_speech_buffer.clear()
        self.silence_start_time = None
        self.session_start_time = None
        self.accumulated_audio_bytes = 0
        self.last_stt_send_time = None
        self.last_published_len = 0
        self.silence_buffer_start_len = 0

    @property
    def buffer_seconds(self) -> float:
        """Get the current audio buffer duration in seconds"""
        return len(self.audio_buffer) / (SAMPLE_RATE * 2)

    @property
    def pre_speech_buffer_seconds(self) -> float:
        """Get the current pre-speech buffer duration in seconds"""
        return len(self.pre_speech_buffer) / (SAMPLE_RATE * 2)
