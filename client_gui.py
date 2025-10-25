"""
client_gui.py

Minimal, futuristic GUI client to control source/target language, select audio source
(microphone or system output), and toggle between Voice Typing and Live Subtitle modes.

Behavior:
- Press Voice Typing to connect and start keyboard pasting; press again to disconnect.
- Press Live Subtitle to connect and start overlay; press again to disconnect.
- Only one mode can be active at a time.
- Select either an input (microphone) or a system output device (but not both).
  On Linux, system output capture typically requires a monitor input device exposed by PulseAudio.

This GUI reuses the streaming logic from the CLI client and integrates with
typing_simulation and live_transcription modules.
"""

from __future__ import annotations

import sys
import asyncio
import json
import struct
import threading
import time
import requests
from dataclasses import dataclass
from typing import Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPalette, QColor, QFont

from websockets import connect
from websockets.exceptions import ConnectionClosed

import pyaudio

import typing_simulation as typing_sim
import live_transcription as live


SERVER_URI_DEFAULT = "ws://localhost:5026"
DISCOVERY_SERVICE_URL = "http://localhost:5025"


def list_input_devices() -> list[tuple[int, str]]:
    devices: list[tuple[int, str]] = []
    p = None
    try:
        p = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info.get('maxInputChannels', 0) > 0:
                devices.append((i, info.get('name', f'Device {i}')))
    except Exception as e:
        # Audio devices not available - return empty list
        print(f"Warning: Could not enumerate audio input devices: {e}")
        devices = []
    finally:
        if p is not None:
            try:
                p.terminate()
            except Exception:
                pass
    return devices


def list_output_devices() -> list[tuple[int, str]]:
    devices: list[tuple[int, str]] = []
    p = None
    try:
        p = pyaudio.PyAudio()
        # On Linux/PulseAudio, output capture devices typically appear as input devices with
        # names containing 'monitor'. We surface those under the Output section.
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            name = info.get('name', f'Device {i}')
            if info.get('maxInputChannels', 0) > 0 and ('monitor' in name.lower() or 'loopback' in name.lower()):
                devices.append((i, name))
    except Exception as e:
        # Audio devices not available - return empty list
        print(f"Warning: Could not enumerate audio output devices: {e}")
        devices = []
    finally:
        if p is not None:
            try:
                p.terminate()
            except Exception:
                pass
    return devices


def get_device_default_sample_rate(device_index: Optional[int]) -> int:
    if device_index is None:
        return 16000
    p = None
    try:
        p = pyaudio.PyAudio()
        info = p.get_device_info_by_index(int(device_index))
        rate = info.get('defaultSampleRate', 16000)
        return int(round(float(rate)))
    except Exception as e:
        print(f"Warning: Could not get device sample rate for device {device_index}: {e}")
        return 16000
    finally:
        if p is not None:
            try:
                p.terminate()
            except Exception:
                pass


def device_is_capturable(device_index: Optional[int]) -> bool:
    if device_index is None:
        return True
    p = None
    try:
        p = pyaudio.PyAudio()
        info = p.get_device_info_by_index(int(device_index))
        capturable = (info.get('maxInputChannels', 0) > 0)
        return bool(capturable)
    except Exception as e:
        print(f"Warning: Could not check if device {device_index} is capturable: {e}")
        return False
    finally:
        if p is not None:
            try:
                p.terminate()
            except Exception:
                pass


LANG_OPTIONS = [
    ("Auto", ""), ("English", "en"), ("Vietnamese", "vi"), ("Japanese", "ja"), ("Chinese", "zh"),
    ("Korean", "ko"), ("French", "fr"), ("German", "de"), ("Spanish", "es"), ("Italian", "it"),
    ("Portuguese", "pt"), ("Russian", "ru"), ("Arabic", "ar"), ("Hindi", "hi"), ("Thai", "th")
]


@dataclass
class ClientConfig:
    server_uri: str = SERVER_URI_DEFAULT
    source_lang: str = "en"
    target_lang: str = "vi"
    mode: str = "typing"  # typing | subtitle
    capture_device_index: Optional[int] = None
    capture_sample_rate: int = 16000


class ClientWorker:
    def __init__(self, status_callback):
        self.status_callback = status_callback
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self.ws_send_queue: Optional[asyncio.Queue] = None
        self.running = False
        self.config = ClientConfig()
        self._stop_event = threading.Event()
        # Resources for safe shutdown across threads
        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._audio_stream = None
        self._ws = None

    def _set_status(self, text: str):
        try:
            self.status_callback(text)
        except Exception:
            pass
            
    def discover_gateway(self) -> Optional[str]:
        """Discover the least-loaded gateway using the discovery service."""
        try:
            self._set_status("Discovering gateway...")
            response = requests.get(f"{DISCOVERY_SERVICE_URL}/discovery/least-loaded", timeout=5)

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    gateway = data['gateway']
                    gateway_uri = f"ws://localhost:{gateway['port']}"
                    self._set_status(f"Discovered gateway: {gateway['gateway_id']} (port {gateway['port']}, {gateway['connection_count']} connections)")
                    return gateway_uri
                else:
                    self._set_status(f"Discovery failed: {data.get('error', 'Unknown error')}")
            else:
                self._set_status(f"Discovery service error: {response.status_code}")

        except requests.exceptions.RequestException as e:
            self._set_status(f"Discovery network error: {str(e)}")
        except ValueError as e:
            self._set_status(f"Discovery data error: {str(e)}")
        except Exception as e:
            self._set_status(f"Discovery error: {str(e)}")

        # Fallback to default gateway
        self._set_status("Using default gateway")
        return self.config.server_uri

    # ==== Public controls ====
    def start(self, config: ClientConfig):
        if self.running:
            self.stop(wait=True)
        self.config = config
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.running = True

    def stop(self, wait: bool = True):
        self._stop_event.set()
        # Ask network client to shutdown gracefully
        try:
            if self.ws_send_queue is not None and self.loop is not None and not self.loop.is_closed():
                self.loop.call_soon_threadsafe(self.ws_send_queue.put_nowait, "__QUIT__")
        except Exception:
            pass
        # Wait for the thread to finish and ensure websocket is closed
        if wait and self.thread is not None:
            try:
                self.thread.join(timeout=5.0)
            except Exception:
                pass
            self.thread = None
        # Extra: ensure websocket is closed if still open
        if self._ws is not None:
            try:
                if not self._ws.closed:
                    asyncio.run(self._ws.close())
            except Exception:
                pass
            self._ws = None
        # Stop workers
        if self.config.mode == "typing":
            try:
                typing_sim.stop()
            except Exception:
                pass
        else:
            try:
                live.stop()
            except Exception:
                pass
        self.running = False

    def update_languages(self, source_lang: str, target_lang: str):
        self.config.source_lang = source_lang
        self.config.target_lang = target_lang
        if self.ws_send_queue is not None and self.loop is not None and self.running and not self.loop.is_closed():
            payload = json.dumps({
                "type": "set_langs",
                "source_language": source_lang,
                "target_language": target_lang,
            })
            try:
                self.loop.call_soon_threadsafe(self.ws_send_queue.put_nowait, payload)
            except Exception:
                pass

    def switch_mode(self, new_mode: str):
        """Switch local output mode without reconnecting to server/audio."""
        new_mode = (new_mode or "").strip().lower()
        if new_mode not in ("typing", "subtitle"):
            return
        if not self.running:
            # If not running, just update config; GUI will start when needed
            self.config.mode = new_mode
            return
        if self.config.mode == new_mode:
            return
        # Stop current mode's worker and start the other, keeping network/audio alive
        try:
            if new_mode == "typing":
                # Turn off overlay
                try:
                    live.stop()
                except Exception:
                    pass
                # Start typing
                try:
                    if typing_sim.check_dependencies():
                        typing_sim.start()
                    else:
                        # If typing deps missing, revert to subtitle
                        live.start()
                        new_mode = "subtitle"
                except Exception:
                    pass
            else:
                # Stop typing simulation
                try:
                    typing_sim.stop()
                except Exception:
                    pass
                # Start overlay
                try:
                    live.start()
                except Exception:
                    pass
        finally:
            self.config.mode = new_mode

    # ==== Internal asyncio client ====
    async def _send_audio_loop(self, ws, audio_stream, ws_send_queue: "asyncio.Queue[str]"):
        loop = asyncio.get_running_loop()
        try:
            while not self._stop_event.is_set():
                # Prioritize control messages
                try:
                    control = ws_send_queue.get_nowait()
                except asyncio.QueueEmpty:
                    control = None

                if control:
                    if control == "__QUIT__":
                        await ws.close()
                        return
                    await ws.send(control)
                    await asyncio.sleep(0)
                    continue

                # Add timeout to audio read to prevent indefinite blocking
                try:
                    data = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: audio_stream.read(1024, exception_on_overflow=False)),
                        timeout=0.1  # 100ms timeout
                    )
                except asyncio.TimeoutError:
                    # No audio data available, continue to check for stop event
                    await asyncio.sleep(0.01)
                    continue

                meta = json.dumps({"sampleRate": self.config.capture_sample_rate}).encode("utf-8")
                meta_len = struct.pack("<I", len(meta))
                try:
                    await ws.send(meta_len + meta + data)
                except ConnectionClosed:
                    return
        except asyncio.CancelledError:
            return
        except Exception:
            return

    async def _recv_loop(self, ws):
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue
                mtype = msg.get("type")
                if mtype == "status":
                    self._set_status("Connected")
                elif mtype == "realtime":
                    text = msg.get("text", "")
                    translation = msg.get("translation", "")
                    text_to_use = translation.strip() if translation.strip() else text
                    if self.config.mode == "typing":
                        typing_sim.enqueue_text(text_to_use)
                    else:
                        live.update_text(text_to_use)
                elif mtype == "final_translation":
                    final_text = msg.get("translation", "") or msg.get("text", "")
                    if self.config.mode == "typing":
                        typing_sim.enqueue_text(final_text)
                    else:
                        live.update_text(final_text)
                elif mtype == "utterance_end":
                    if self.config.mode == "typing":
                        typing_sim.schedule_final_paste()
        except Exception:
            pass
        finally:
            self._set_status("Disconnected")

    async def _run_client(self):
        self.ws_send_queue = asyncio.Queue()
        try:
            self._pyaudio = pyaudio.PyAudio()
        except Exception as e:
            self._set_status(f"Audio initialization failed: {e}")
            self._pyaudio = None
            return
        audio_stream = None
        # Prepare audio input (selected device) trying supported sample rates
        # Strict: open only at 16000 Hz as required by server pipeline; fallback to default if needed
        selected_index = self.config.capture_device_index if self.config.capture_device_index is not None else None
        if selected_index is not None and not device_is_capturable(selected_index):
            self._set_status("Selected device cannot capture")
            try:
                if self._pyaudio:
                    self._pyaudio.terminate()
            except Exception:
                pass
            self._pyaudio = None
            return
        # Try 16000 strictly first, then try device default if different
        tried_rates = []
        for r in (16000, get_device_default_sample_rate(selected_index)):
            r_int = int(r)
            if r_int in tried_rates:
                continue
            tried_rates.append(r_int)
            try:
                audio_stream = self._pyaudio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=r_int,
                    input=True,
                    frames_per_buffer=1024,
                    input_device_index=selected_index,
                )
                self.config.capture_sample_rate = r_int
                break
            except Exception:
                audio_stream = None
                continue
        if audio_stream is None:
            self._set_status("Audio open failed")
            try:
                if self._pyaudio:
                    self._pyaudio.terminate()
            except Exception:
                pass
            self._pyaudio = None
            return
        # record stream reference for external stop
        self._audio_stream = audio_stream

        # Start mode-specific workers
        if self.config.mode == "typing":
            try:
                if typing_sim.check_dependencies():
                    typing_sim.start()
                else:
                    self._set_status("Typing deps missing")
            except Exception:
                pass
            try:
                live.stop()
            except Exception:
                pass
        else:
            try:
                live.start()
            except Exception:
                pass
            try:
                typing_sim.stop()
            except Exception:
                pass

        try:
            # Discover best gateway
            gateway_uri = self.discover_gateway()
            self._set_status(f"Connecting to {gateway_uri}...")

            async with connect(gateway_uri, max_size=None) as ws:
                self._ws = ws
                self._set_status("Connected to gateway")

                # Request status and set languages
                await ws.send(json.dumps({"type": "get_status"}))
                await ws.send(json.dumps({
                    "type": "set_langs",
                    "source_language": self.config.source_lang,
                    "target_language": self.config.target_lang,
                }))

                send_task = asyncio.create_task(self._send_audio_loop(ws, audio_stream, self.ws_send_queue))
                recv_task = asyncio.create_task(self._recv_loop(ws))
                done, pending = await asyncio.wait([send_task, recv_task], return_when=asyncio.FIRST_COMPLETED)
                for t in pending:
                    t.cancel()
        except (OSError, ConnectionError, websockets.exceptions.WebSocketException) as e:
            self._set_status(f"Connection error: {str(e)}")
        except Exception as e:
            self._set_status(f"Unexpected error: {str(e)}")
        finally:
            self._ws = None
            try:
                if audio_stream is not None:
                    audio_stream.stop_stream()
                    audio_stream.close()
            except Exception:
                pass
            try:
                if self._pyaudio is not None:
                    self._pyaudio.terminate()
            except Exception:
                pass
            self._audio_stream = None
            self._pyaudio = None

    def _run_loop(self):
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._run_client())
        except Exception:
            pass
        finally:
            if self.loop is not None:
                try:
                    pending = asyncio.all_tasks(loop=self.loop)
                    for t in pending:
                        t.cancel()
                    if pending:
                        self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except Exception:
                    pass
                try:
                    self.loop.close()
                except Exception:
                    pass


class ClientWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Realtime Client")
        self.setMinimumSize(600, 220)

        # Futuristic minimal dark theme
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor(18, 18, 22))
        pal.setColor(QPalette.WindowText, QColor(235, 235, 245))
        pal.setColor(QPalette.Base, QColor(28, 28, 34))
        pal.setColor(QPalette.AlternateBase, QColor(38, 38, 46))
        pal.setColor(QPalette.Text, QColor(235, 235, 245))
        pal.setColor(QPalette.Button, QColor(28, 28, 34))
        pal.setColor(QPalette.ButtonText, QColor(235, 235, 245))
        self.setPalette(pal)

        font = QFont("Arial", 10)
        self.setFont(font)

        self.worker = ClientWorker(self._update_status)

        self._build_ui()
        self._populate_devices()

        self.active_mode: Optional[str] = None  # typing | subtitle | None
        self.statusBar().showMessage("Disconnected")

    def _build_ui(self):
        root = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Languages row
        langs_row = QHBoxLayout()
        langs_row.setSpacing(10)
        langs_row.addWidget(self._label("Source"))
        self.source_combo = QComboBox()
        for label, code in LANG_OPTIONS:
            self.source_combo.addItem(label, code)
        self.source_combo.setCurrentIndex(1)  # English
        langs_row.addWidget(self.source_combo)
        self.source_combo.currentIndexChanged.connect(self._on_lang_changed)
        langs_row.addWidget(self._label("Target"))
        self.target_combo = QComboBox()
        for label, code in LANG_OPTIONS:
            self.target_combo.addItem(label, code)
        # Vietnamese default
        idx_vi = next((i for i,(l,c) in enumerate(LANG_OPTIONS) if c == "vi"), 0)
        self.target_combo.setCurrentIndex(idx_vi)
        langs_row.addWidget(self.target_combo)
        self.target_combo.currentIndexChanged.connect(self._on_lang_changed)
        layout.addLayout(langs_row)

        # Audio capture device row (single dropdown with categories)
        audio_row = QHBoxLayout()
        audio_row.setSpacing(10)
        audio_row.addWidget(self._label("Capture"))
        self.device_combo = QComboBox()
        audio_row.addWidget(self.device_combo)
        layout.addLayout(audio_row)
        


        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #333;")
        layout.addWidget(sep)

        # Mode buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(14)
        self.voice_btn = QPushButton("Voice Typing")
        self.voice_btn.setCheckable(True)
        self.voice_btn.clicked.connect(self._toggle_voice_typing)
        self.subtitle_btn = QPushButton("Live Subtitle")
        self.subtitle_btn.setCheckable(True)
        self.subtitle_btn.clicked.connect(self._toggle_subtitle)
        for b in (self.voice_btn, self.subtitle_btn):
            b.setStyleSheet(self._button_style(active=False))
        btn_row.addWidget(self.voice_btn)
        btn_row.addWidget(self.subtitle_btn)
        layout.addLayout(btn_row)

        root.setLayout(layout)
        self.setCentralWidget(root)

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #aaa;")
        return lbl

    def _button_style(self, active: bool) -> str:
        if active:
            return (
                "QPushButton { background-color: #1DB954; color: #0a0a0a; border: none; padding: 10px 16px; }"
                "QPushButton:pressed { background-color: #18a34a; }"
            )
        return (
            "QPushButton { background-color: #2a2e33; color: #e5e5ef; border: 1px solid #3a3f45; padding: 10px 16px; }"
            "QPushButton:pressed { background-color: #33373c; }"
        )

    def _populate_devices(self):
        # Populate combined device list with categories
        self.device_combo.clear()
        inputs = list_input_devices()
        outputs = list_output_devices()
        has_devices = False

        # Add Input category header (disabled)
        if inputs:
            self.device_combo.addItem("— Input Devices —")
            self.device_combo.model().item(self.device_combo.count()-1).setEnabled(False)
            for idx, name in inputs:
                self.device_combo.addItem(f"[IN] {name} (#{idx})", ("in", idx))
                has_devices = True

        # Add Output category header (disabled)
        # Only include capturable outputs (monitor/loopback discovered earlier)
        if outputs:
            self.device_combo.addItem("— Output Devices —")
            self.device_combo.model().item(self.device_combo.count()-1).setEnabled(False)
            for idx, name in outputs:
                self.device_combo.addItem(f"[OUT] {name} (#{idx})", ("out", idx))
                has_devices = True

        if not has_devices:
            self.device_combo.addItem("No audio devices found", None)
            # Ensure the "no devices" item is also disabled to prevent selection
            self.device_combo.model().item(self.device_combo.count()-1).setEnabled(False)

    def _selected_device(self) -> Optional[int]:
        current_index = self.device_combo.currentIndex()
        if current_index >= 0:
            # Check if the selected item is enabled
            model = self.device_combo.model()
            if not model.item(current_index).isEnabled():
                return None  # Disabled item selected, treat as no selection

        data = self.device_combo.currentData()
        if isinstance(data, tuple) and len(data) == 2:
            # Return raw device index; capture path is always input for this client
            return int(data[1])
        return None

    def _set_active(self, mode: Optional[str]):
        self.active_mode = mode
        self.voice_btn.setChecked(mode == "typing")
        self.subtitle_btn.setChecked(mode == "subtitle")
        self.voice_btn.setStyleSheet(self._button_style(active=(mode == "typing")))
        self.subtitle_btn.setStyleSheet(self._button_style(active=(mode == "subtitle")))

    def _current_config(self, mode: str) -> ClientConfig:
        src = self.source_combo.currentData()
        tgt = self.target_combo.currentData()
        device_idx = self._selected_device()
        rate = get_device_default_sample_rate(device_idx)
        return ClientConfig(
            server_uri=SERVER_URI_DEFAULT,
            source_lang=src or "",
            target_lang=tgt or "",
            mode=mode,
            capture_device_index=device_idx,
            capture_sample_rate=rate,
        )

    def _on_lang_changed(self):
        src = self.source_combo.currentData() or ""
        tgt = self.target_combo.currentData() or ""
        # Update local config immediately
        self.worker.config.source_lang = src
        self.worker.config.target_lang = tgt
        # If connected, send runtime update to server
        if (self.worker.running and self.worker.ws_send_queue is not None and
            self.worker.loop is not None and not self.worker.loop.is_closed()):
            payload = json.dumps({
                "type": "set_langs",
                "source_language": src,
                "target_language": tgt,
            })
            try:
                self.worker.loop.call_soon_threadsafe(self.worker.ws_send_queue.put_nowait, payload)
            except Exception:
                pass
            

    def _toggle_voice_typing(self):
        if self.active_mode == "typing":
            # deactivate entirely
            self.worker.stop()
            self._set_active(None)
            self._update_status("Disconnected")
            return
        if self.active_mode == "subtitle" and self.worker.running:
            # Keep connection/audio; switch local output mode only
            self.worker.switch_mode("typing")
            self._set_active("typing")
            return
        # Not running; start fresh
        self._set_active("typing")
        self.worker.start(self._current_config("typing"))

    def _toggle_subtitle(self):
        if self.active_mode == "subtitle":
            # deactivate entirely
            self.worker.stop()
            self._set_active(None)
            self._update_status("Disconnected")
            return
        if self.active_mode == "typing" and self.worker.running:
            # Keep connection/audio; switch local output mode only
            self.worker.switch_mode("subtitle")
            self._set_active("subtitle")
            return
        # Not running; start fresh
        self._set_active("subtitle")
        self.worker.start(self._current_config("subtitle"))

    def _update_status(self, text: str):
        self.statusBar().showMessage(text)

    def closeEvent(self, event):
        try:
            self.worker.stop()
        except Exception:
            pass
        event.accept()


def main():
    app = QApplication(sys.argv)
    w = ClientWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()


