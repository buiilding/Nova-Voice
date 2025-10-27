"""
vad.py - Voice Activity Detection for the Gateway service

Contains WebRTC VAD and Silero VAD implementations with dual VAD coordination.
Handles speech detection logic for audio chunks.
"""

import threading
import numpy as np
import torch
import webrtcvad

from config import WEBRTC_SENSITIVITY, SILERO_SENSITIVITY, INT16_MAX_ABS_VALUE, SAMPLE_RATE


class VoiceActivityDetector:
    """Handles voice activity detection using dual VAD system (WebRTC + Silero)"""

    def __init__(self):
        # WebRTC VAD components
        self.webrtc_vad_model = None
        self.is_webrtc_speech_active = False

        # Silero VAD components
        self.silero_vad_model = None
        self.is_silero_speech_active = False
        self.silero_working = False

    def initialize_models(self):
        """Initialize WebRTC and Silero VAD models"""
        try:
            # Initialize WebRTC VAD
            self.webrtc_vad_model = webrtcvad.Vad()
            self.webrtc_vad_model.set_mode(WEBRTC_SENSITIVITY)
        except Exception as e:
            raise RuntimeError(f"Error initializing WebRTC VAD model: {e}")

        try:
            # Initialize Silero VAD
            self.silero_vad_model, _ = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                verbose=False
            )
        except Exception as e:
            raise RuntimeError(f"Error initializing Silero VAD model: {e}")

    def _is_webrtc_speech(self, chunk: bytes, all_frames_must_be_true: bool = False) -> bool:
        """WebRTC VAD speech detection. Input must be 16kHz, 16-bit PCM."""
        if self.webrtc_vad_model is None:
            return False

        # WebRTC VAD expects 10ms frames (160 samples at 16kHz)
        frame_length = 160  # 10ms at 16kHz
        frame_bytes = frame_length * 2  # 16-bit samples

        # Process frames
        speech_frames = 0
        total_frames = 0

        for i in range(0, len(chunk) - frame_bytes + 1, frame_bytes):
            frame = chunk[i:i + frame_bytes]
            if len(frame) == frame_bytes:
                if self.webrtc_vad_model.is_speech(frame, SAMPLE_RATE):
                    speech_frames += 1
                    if not all_frames_must_be_true:
                        self.is_webrtc_speech_active = True
                        return True
                total_frames += 1

        if all_frames_must_be_true:
            # Require majority of frames to contain speech
            speech_detected = speech_frames > total_frames // 2
            self.is_webrtc_speech_active = speech_detected
            return speech_detected
        else:
            self.is_webrtc_speech_active = False
            return False

    def _is_silero_speech(self, chunk: bytes) -> bool:
        """Silero VAD speech detection. Input must be 16kHz, 16-bit PCM."""
        if self.silero_vad_model is None:
            return False

        self.silero_working = True
        audio_chunk = np.frombuffer(chunk, dtype=np.int16)
        audio_chunk = audio_chunk.astype(np.float32) / INT16_MAX_ABS_VALUE

        # Silero VAD expects 512 samples for 16kHz audio
        # If we have more samples, process in chunks and take the max probability
        expected_samples = 512
        if len(audio_chunk) > expected_samples:
            # Process in chunks of 512 samples
            max_prob = 0.0
            for i in range(0, len(audio_chunk) - expected_samples + 1, expected_samples // 2):
                chunk_slice = audio_chunk[i:i + expected_samples]
                if len(chunk_slice) == expected_samples:
                    vad_prob = self.silero_vad_model(torch.from_numpy(chunk_slice), SAMPLE_RATE).item()
                    max_prob = max(max_prob, vad_prob)

            vad_prob = max_prob
        elif len(audio_chunk) == expected_samples:
            vad_prob = self.silero_vad_model(torch.from_numpy(audio_chunk), SAMPLE_RATE).item()
        else:
            # Pad with zeros if too short
            padded_chunk = np.zeros(expected_samples, dtype=np.float32)
            padded_chunk[:len(audio_chunk)] = audio_chunk
            vad_prob = self.silero_vad_model(torch.from_numpy(padded_chunk), SAMPLE_RATE).item()

        is_silero_speech_active = vad_prob > (1 - SILERO_SENSITIVITY)

        self.is_silero_speech_active = is_silero_speech_active
        self.silero_working = False
        return is_silero_speech_active

    def _check_voice_activity(self, data: bytes):
        """Check voice activity using dual VAD system"""
        # First quick performing check for voice activity using WebRTC
        self._is_webrtc_speech(data)

        if self.is_webrtc_speech_active:
            if not self.silero_working:
                self.silero_working = True
                # Run the intensive check in a separate thread
                threading.Thread(target=self._is_silero_speech, args=(data,)).start()

    def detect_speech_activity(self, audio_chunk: bytes) -> bool:
        """Dual VAD: detect if audio chunk contains speech using WebRTC + Silero"""
        if len(audio_chunk) == 0:
            return False

        # Check voice activity using dual VAD system
        self._check_voice_activity(audio_chunk)

        # Return True only if BOTH VAD systems agree
        return self.is_webrtc_speech_active and self.is_silero_speech_active
