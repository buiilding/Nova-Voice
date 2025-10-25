#!/usr/bin/env python3
"""
Live Subtitle Function with Real-Time Speech-to-Text Transcription

This module provides a live subtitle overlay that displays real-time transcription
as a semi-transparent rectangle at the bottom of the screen. It integrates with
the existing RealTimeSTT system for speech recognition.

Features:
- Real-time speech-to-text transcription
- Semi-transparent overlay at bottom of screen
- One sentence at a time display to prevent text accumulation
- Automatic text wrapping and positioning
- Thread-safe text updates
- Clean shutdown handling
- Audio device selection
- Multi-language support

Author: Nova Assistant
"""

import sys
import os
import threading
import time
import signal
import queue
import logging
from typing import Optional, Callable
import multiprocessing as mp
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPainter, QColor, QPalette

# Library module logging
logger = logging.getLogger(__name__)

# Module version: expose overlay as a reusable component. No STT imports here.
REALTIME_STT_AVAILABLE = False
AudioToTextRecorder = None

# Use spawn context for PyQt process isolation (avoids Qt main-thread warnings after fork)
_mp_ctx = mp.get_context("spawn")


def list_audio_devices():
    """List all available audio input devices with their indexes."""
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        
        devices = []
        print("\n=== Available Audio Input Devices ===")
        print("Index | Device Name")
        print("-" * 50)
        
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:  # Input device
                devices.append((i, device_info['name']))
                print(f"  {i:2d}  | {device_info['name']}")
        
        p.terminate()
        return devices
        
    except ImportError:
        print("PyAudio not available. Install with: pip install pyaudio")
        return []
    except Exception as e:
        print(f"Error listing audio devices: {e}")
        return []


def select_audio_device():
    """Prompt user to select an audio device."""
    devices = list_audio_devices()
    
    if not devices:
        print("No audio input devices found.")
        return None
    
    while True:
        try:
            choice = input(f"\nSelect audio device (0-{len(devices)-1}) or press Enter for default: ").strip()
            
            if not choice:  # Default device
                return None
            
            device_index = int(choice)
            if 0 <= device_index < len(devices):
                selected_device = devices[device_index]
                print(f"Selected: {selected_device[1]} (Index: {selected_device[0]})")
                return selected_device[0]
            else:
                print(f"Invalid choice. Please enter a number between 0 and {len(devices)-1}")
                
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\nCancelled by user.")
            return None


def select_language():
    """Prompt user to select language or auto-detect."""
    languages = [
        ("Auto-detect", ""),
        ("English", "en"),
        ("Vietnamese", "vi"),
        ("Japanese", "ja"),
        ("Chinese", "zh"),
        ("Korean", "ko"),
        ("French", "fr"),
        ("German", "de"),
        ("Spanish", "es"),
        ("Italian", "it"),
        ("Portuguese", "pt"),
        ("Russian", "ru"),
        ("Arabic", "ar"),
        ("Hindi", "hi"),
        ("Thai", "th")
    ]
    
    print("\n=== Language Selection ===")
    for i, (name, code) in enumerate(languages):
        print(f"  {i:2d} | {name}")
    
    while True:
        try:
            choice = input(f"\nSelect language (0-{len(languages)-1}) or press Enter for auto-detect: ").strip()
            
            if not choice:  # Auto-detect
                return ""
            
            lang_index = int(choice)
            if 0 <= lang_index < len(languages):
                selected_lang = languages[lang_index]
                print(f"Selected: {selected_lang[0]} ({selected_lang[1]})")
                return selected_lang[1]
            else:
                print(f"Invalid choice. Please enter a number between 0 and {len(languages)-1}")
                
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\nCancelled by user.")
            return ""


class LiveSubtitleOverlay(QWidget):
    """
    Transparent overlay window for displaying live subtitles.
    Displays one sentence at a time to prevent text accumulation.
    """
    
    def __init__(self, max_sentence_length: int = 100, ui_update_ms: int = 200):
        super().__init__()
        self.max_sentence_length = max_sentence_length
        self.current_sentence = ""
        self.text_queue = queue.Queue()
        self.last_update_time = 0
        # Minimum time between updates (seconds), tied to UI timer interval
        self.update_threshold = max(0.01, ui_update_ms / 1000.0)
        self.init_ui()
        self.setup_window_properties()
        
        # Timer for updating text from queue
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.process_text_queue)
        # Polling interval tied to debounce threshold
        self.update_timer.start(max(10, ui_update_ms))
        
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()

        # Spacer to push text to bottom
        layout.addStretch()

        # Subtitle label (single line)
        self.subtitle_label = QLabel("")
        self.subtitle_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.subtitle_label.setWordWrap(False)
        self.subtitle_label.setContentsMargins(50, 0, 50, 0)
        
        # Set font - larger and bold for better visibility
        font = QFont("Arial", 16, QFont.Bold)
        self.subtitle_label.setFont(font)
        
        # Set text color to white
        palette = self.subtitle_label.palette()
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        self.subtitle_label.setPalette(palette)
        
        # Add label to layout
        layout.addWidget(self.subtitle_label)

        # Bottom spacer and margins
        layout.addStretch()
        layout.setStretch(0, 8)
        layout.setStretch(1, 0)
        layout.setStretch(2, 1)
        layout.setContentsMargins(0, 0, 0, 30)

        self.setLayout(layout)
        
    def setup_window_properties(self):
        """Set up window properties for overlay behavior."""
        # Make window frameless and always on top
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        
        # Make window transparent but visible
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        # Do not capture mouse events; allow clicks to pass through to underlying apps
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        # Ensure child label does not capture mouse events either
        try:
            if hasattr(self, "subtitle_label") and self.subtitle_label is not None:
                self.subtitle_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        except Exception:
            pass
        # Avoid taking focus from other apps
        try:
            self.setWindowFlag(Qt.WindowDoesNotAcceptFocus, True)
        except Exception:
            pass
        try:
            self.setFocusPolicy(Qt.NoFocus)
        except Exception:
            pass
        
        # Get screen geometry and position window
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        self._screen_geometry = screen_geometry
        # Single-line height based on font metrics
        self._padding = 25
        self._bottom_margin = 60
        line_h = self.subtitle_label.fontMetrics().height()
        self._min_height = max(40, line_h + 2 * self._padding)
        
        # Position at bottom center
        subtitle_height = self._min_height  # Initial height
        self.setGeometry(
            screen_geometry.x(),
            screen_geometry.y() + screen_geometry.height() - subtitle_height - self._bottom_margin,
            screen_geometry.width(),
            subtitle_height
        )
        
    def paintEvent(self, event):
        """Custom paint event to create semi-transparent background for text."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Only draw background if there's text
        if self.current_sentence.strip():
            # Get text rectangle
            text_rect = self.subtitle_label.geometry()
            
            # Add padding around text
            background_rect = text_rect.adjusted(-self._padding, -self._padding, self._padding, self._padding)
            
            # Draw semi-transparent black background with rounded corners
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 200))  # More opaque for better readability
            painter.drawRoundedRect(background_rect, 15, 15)
    
    def update_subtitle(self, text: str):
        """Update the subtitle text (thread-safe)."""
        self.text_queue.put(text)
    
    def process_text_queue(self):
        """Process text updates from the queue with debouncing."""
        try:
            current_time = time.time()
            
            # Only process if enough time has passed since last update
            if current_time - self.last_update_time < self.update_threshold:
                return
                
            # Drain queue and apply only the latest text once per tick
            latest_text = None
            while not self.text_queue.empty():
                latest_text = self.text_queue.get_nowait()

            if latest_text is None:
                return

            # Limit displayed text length to max_sentence_length characters.
            display_text = latest_text
            max_len = max(0, int(self.max_sentence_length))
            if max_len and len(display_text) > max_len:
                # Keep most recent content visible
                tail = display_text[-max_len:]
                # Ensure ellipsis if truncated and space for it
                if len(display_text) > max_len:
                    if max_len > 1:
                        tail = "…" + display_text[-(max_len - 1):]
                    else:
                        tail = "…"
                display_text = tail

            if display_text == self.current_sentence:
                return

            self.current_sentence = display_text
            self.subtitle_label.setText(display_text)
            self.last_update_time = current_time

            # Single-line height only (no vertical growth)
            needed_height = self._min_height
            self.setGeometry(
                self.x(),
                self._screen_geometry.y() + self._screen_geometry.height() - needed_height - self._bottom_margin,
                self.width(),
                needed_height
            )

            self.repaint()
            self.update()
        except queue.Empty:
            pass
    
    def show_overlay(self):
        """Show the overlay window."""
        self.show()
        self.raise_()
        # Best-effort: make the entire window transparent for input at the windowing system level
        try:
            handle = self.windowHandle()
            if handle is not None and hasattr(Qt, 'WindowTransparentForInput'):
                # This flag lets pointer/keyboard input pass through the window to apps underneath
                handle.setFlag(Qt.WindowTransparentForInput, True)
        except Exception:
            pass
        # Linux/X11: enforce click-through by clearing the input shape region via XFixes
        try:
            if sys.platform.startswith("linux"):
                wid = int(self.winId())
                # Lazy import and configure ctypes only here to avoid import cost elsewhere
                import ctypes
                from ctypes import c_void_p, c_char_p, c_int, c_ulong
                try:
                    x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
                    xfixes = ctypes.cdll.LoadLibrary("libXfixes.so.3")
                except OSError:
                    x11 = None
                    xfixes = None
                if x11 is not None and xfixes is not None:
                    x11.XOpenDisplay.argtypes = [c_char_p]
                    x11.XOpenDisplay.restype = c_void_p
                    x11.XFlush.argtypes = [c_void_p]
                    x11.XCloseDisplay.argtypes = [c_void_p]
                    xfixes.XFixesCreateRegion.argtypes = [c_void_p, c_void_p, c_int]
                    xfixes.XFixesCreateRegion.restype = c_ulong
                    xfixes.XFixesSetWindowShapeRegion.argtypes = [c_void_p, c_ulong, c_int, c_int, c_int, c_ulong]
                    xfixes.XFixesDestroyRegion.argtypes = [c_void_p, c_ulong]
                    dpy = x11.XOpenDisplay(None)
                    if dpy:
                        try:
                            # 2 corresponds to ShapeInput
                            region = xfixes.XFixesCreateRegion(dpy, None, 0)
                            xfixes.XFixesSetWindowShapeRegion(dpy, c_ulong(wid), 2, 0, 0, region)
                            xfixes.XFixesDestroyRegion(dpy, region)
                            x11.XFlush(dpy)
                        finally:
                            x11.XCloseDisplay(dpy)
        except Exception:
            pass
    
    # No-op event handlers removed to reduce code size


class RealTranscriptionThread(QThread):
    """Thread for handling real-time transcription using RealTimeSTT."""
    
    text_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, language="en", model="medium", input_device_index=None, 
                 max_words=9, clear_delay=200):
        super().__init__()
        self.language = language
        self.model = model
        self.input_device_index = input_device_index
        self.audio_recorder = None
        self.is_running = False
        
        # Word-count based window parameters
        self.max_words = max_words
        self.clear_delay = clear_delay
        self.last_emitted_text = ""  # Track last emitted text to prevent duplicates
        
    def preprocess_text(self, text):
        """Preprocess text like in STT_RT_only.py."""
        text = text.lstrip()
        if text.startswith("..."):
            text = text[3:]
        text = text.lstrip()
        if text:
            text = text[0].upper() + text[1:]
        return text
    
    def _limit_to_last_words(self, text: str, max_words: int) -> str:
        """Return only the last max_words words of the given text."""
        if max_words <= 0:
            return ""
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[-max_words:])
        
    def text_detected(self, text):
        """Handle real-time transcription updates with fixed-size window (no accumulation)."""
        original = self.preprocess_text(text)
        display_text = self._limit_to_last_words(original, self.max_words)
        
        # Emit only when the display chunk changes
        if display_text and display_text != self.last_emitted_text:
            self.text_updated.emit(display_text)
            self.last_emitted_text = display_text
        
        # Keep audio recorder settings minimal for faster response
        if self.audio_recorder:
            # Use fixed short pause for consistent behavior
            self.audio_recorder.post_speech_silence_duration = 0.3
        
    def vad_start_handler(self):
        """Voice activity detection start handler."""
        logger.info("Voice activity detected.")
        
    def recording_start_handler(self):
        """Recording start handler."""
        logger.info("Recording started.")
        
    def recording_stop_handler(self):
        """Recording stop handler."""
        logger.info("Recording stopped after silence.")
        # Clear transient text on stop to avoid accumulation
        self.text_updated.emit("")
        
    def run(self):
        """Run the transcription thread."""
        self.is_running = True
        
        try:
            # Create recorder configuration like in STT_RT_only.py
            recorder_config = {
                'spinner': False,
                'language': self.language,
                'silero_sensitivity': 0.5,
                'device': 'cuda',
                'webrtc_sensitivity': 3,
                'silero_use_onnx': True,
                'post_speech_silence_duration': 0.03,
                'min_length_of_recording': 1.1,
                'min_gap_between_recordings': 0,
                'enable_realtime_transcription': True,
                'realtime_processing_pause': 0.02,
                'realtime_model_type': self.model,
                'on_realtime_transcription_update': self.text_detected,
                'on_vad_start': self.vad_start_handler,
                'on_recording_start': self.recording_start_handler,
                'on_recording_stop': self.recording_stop_handler,
                'silero_deactivity_detection': True,
                'beam_size_realtime': 3,
                'no_log_file': True,
                'initial_prompt_realtime': (
                    "End incomplete sentences with ellipses.\n"
                    "Examples:\n"
                    "Complete: The sky is blue.\n"
                    "Incomplete: When the sky...\n"
                    "Complete: She walked home.\n"
                    "Incomplete: Because he...\n"
                ),
                'realtime_only': True,
                'compute_type': 'default',
            }
            
            # Add input device if specified
            if self.input_device_index is not None:
                recorder_config['input_device_index'] = self.input_device_index
            
            # Create and start the audio recorder
            self.audio_recorder = AudioToTextRecorder(**recorder_config)
            
            # Keep the thread alive while transcription is running
            while self.is_running:
                try:
                    self.audio_recorder.text(lambda _: None)
                except Exception as e:
                    if self.is_running:  # Only log if we're supposed to be running
                        logger.error(f"Error in transcription loop: {e}")
                        self.error_occurred.emit(str(e))
                    break
                    
        except Exception as e:
            logger.error(f"Error in transcription thread: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self.is_running = False
    
    def stop(self):
        """Stop the transcription thread."""
        self.is_running = False
        if self.audio_recorder:
            try:
                self.audio_recorder.shutdown()
            except:
                pass


class MockTranscriptionThread(QThread):
    """Mock transcription thread for testing without audio dependencies."""
    
    text_updated = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        
    def run(self):
        """Run the mock transcription thread."""
        self.is_running = True
        
        try:
            # Simulate transcription with sample texts
            sample_texts = [
                "Hello, this is a test of the live subtitle system.",
                "Xin chào, đây là bài kiểm tra hệ thống phụ đề trực tiếp.",
                "こんにちは、これはライブ字幕システムのテストです。",
                "你好，这是实时字幕系统的测试。",
                "안녕하세요, 이것은 실시간 자막 시스템 테스트입니다.",
                "Bonjour, ceci est un test du système de sous-titres en direct.",
                "Hallo, dies ist ein Test des Live-Untertitelsystems.",
                "Hola, esto es una prueba del sistema de subtítulos en vivo.",
                "This is a longer sentence to test text wrapping and positioning in the overlay window.",
                ""  # Empty text to test clearing
            ]
            
            for text in sample_texts:
                if not self.is_running:
                    break
                self.text_updated.emit(text)
                time.sleep(3)  # Show each text for 3 seconds
            
            # Keep running with the last text
            while self.is_running:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Error in mock transcription thread: {e}")
        finally:
            self.is_running = False
    
    def stop(self):
        """Stop the transcription thread."""
        self.is_running = False


class LiveSubtitleManager:
    """Internal manager to host the Qt overlay in a separate process."""
    def __init__(self, ui_update_ms: int = 200):
        self.ui_update_ms = ui_update_ms
        self.process: Optional[mp.Process] = None
        self.control_queue: Optional[mp.Queue] = None

    @staticmethod
    def _overlay_process(control_queue: 'mp.Queue', ui_update_ms: int):
        # Create a minimal logger for the subprocess
        import logging as _logging
        _log = _logging.getLogger("live_subtitle_overlay")
        _logging.basicConfig(level=_logging.INFO)

        # Ignore Ctrl+C in the overlay process; parent handles shutdown
        try:
            signal.signal(signal.SIGINT, signal.SIG_IGN)
        except Exception:
            pass

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        overlay = LiveSubtitleOverlay(max_sentence_length=100, ui_update_ms=ui_update_ms)
        overlay.show_overlay()

        # Timer to poll control queue
        poll_timer = QTimer()
        def _poll():
            try:
                while True:
                    cmd, payload = control_queue.get_nowait()
                    if cmd == "update":
                        overlay.update_subtitle(str(payload or ""))
                    elif cmd == "clear":
                        overlay.update_subtitle("")
                    elif cmd == "quit":
                        try:
                            overlay.close()
                        except Exception:
                            pass
                        app.quit()
                        return
                    elif cmd == "visible":
                        visible = bool(payload)
                        overlay.setVisible(visible)
                    else:
                        _log.debug(f"Unknown command: {cmd}")
            except queue.Empty:
                pass
        poll_timer.timeout.connect(_poll)
        poll_timer.start(max(10, ui_update_ms))

        app.exec_()

    def start(self):
        if self.process and self.process.is_alive():
            return
        self.control_queue = _mp_ctx.Queue()
        self.process = _mp_ctx.Process(target=self._overlay_process, args=(self.control_queue, self.ui_update_ms), daemon=True)
        self.process.start()

    def stop(self):
        if self.control_queue:
            try:
                self.control_queue.put(("quit", None))
            except Exception:
                pass
        if self.process:
            self.process.join(timeout=2.0)
            if self.process.is_alive():
                # Ask OS to terminate
                self.process.terminate()
                try:
                    self.process.join(timeout=1.0)
                except Exception:
                    pass
            if self.process.is_alive():
                # Force kill if still hanging (rare with Qt event loops)
                try:
                    # Python 3.7+ provides kill(); fallback to os.kill otherwise
                    if hasattr(self.process, 'kill'):
                        self.process.kill()
                    else:
                        os.kill(self.process.pid, signal.SIGKILL)
                except Exception:
                    pass
        self.process = None
        self.control_queue = None

    def update(self, text: str):
        if self.control_queue:
            try:
                self.control_queue.put(("update", text))
            except Exception:
                pass

    def clear(self):
        if self.control_queue:
            try:
                self.control_queue.put(("clear", None))
            except Exception:
                pass

    def set_visible(self, visible: bool):
        if self.control_queue:
            try:
                self.control_queue.put(("visible", bool(visible)))
            except Exception:
                pass

    def is_running(self) -> bool:
        return bool(self.process and self.process.is_alive())


_manager_lock = threading.Lock()
_manager: Optional[LiveSubtitleManager] = None


def start(ui_update_ms: int = 200):
    """Start the live subtitle overlay in a background process."""
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = LiveSubtitleManager(ui_update_ms=ui_update_ms)
            _manager.start()


def stop():
    """Stop the live subtitle overlay process."""
    global _manager
    with _manager_lock:
        if _manager is not None:
            _manager.stop()
            _manager = None


def update_text(text: str):
    """Update the displayed subtitle text."""
    with _manager_lock:
        if _manager is not None:
            _manager.update(text)


def clear():
    """Clear the subtitle text."""
    with _manager_lock:
        if _manager is not None:
            _manager.clear()


def is_running() -> bool:
    with _manager_lock:
        return bool(_manager and _manager.is_running())


# Example usage and testing
if __name__ == "__main__":
    # This module is intended to be imported and controlled programmatically.
    print("live_transcription is a module. Import and call start(), update_text(), stop().")