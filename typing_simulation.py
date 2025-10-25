"""
typing_simulation.py

Provides a reusable typing simulation module:
- Runs a background typing worker thread.
- Exposes start(), stop(), enqueue_text(), schedule_final_paste(), check_dependencies().
- Uses pyautogui + pyperclip to paste text quickly by replacing previous paste using undo+paste.
- Configurable via module-level constants.

Functions:
- start(): starts the typing worker thread (daemon).
- stop(): stops the typing worker thread and cleans up timers.
- enqueue_text(text): enqueues text for paste decisions.
- schedule_final_paste(): schedule a final paste (used on utterance_end).
- check_dependencies(): quick check for pyautogui and pyperclip availability.

Notes:
- The module is robust to missing typing dependencies: check_dependencies() will return False
  and the caller should decide whether to enable typing simulation.
"""

from __future__ import annotations
import time
import re
import threading
import queue
import pyautogui
import pyperclip

# ===== Configuration =====
PASTE_THROTTLE_DELAY = 1.0   # seconds between pastes
MIN_TEXT_LENGTH = 1          # minimum characters to consider pasting
PASTE_ON_PUNCTUATION = True  # paste immediately if text ends with .!? 
MOD_KEY = "command" if __import__("sys").platform == "darwin" else "ctrl"

# ===== Internal state / concurrency primitives =====
_text_queue: "queue.Queue[str]" = queue.Queue()
_stop_event = threading.Event()
_typing_thread: threading.Thread | None = None

_current_displayed_text = ""   # what we've last pasted (so we can replace)
_pending_text = ""             # latest text waiting for paste
_last_paste_time = 0.0
_reset_timer: threading.Timer | None = None
_session_start_index = None    # retained for parity with original behavior
_leading_separator = ""        # leading space inserted for the next utterance's pastes

# Lock to guard module-level variables that are mutated by threads
_state_lock = threading.Lock()


# ===== Utility functions =====
def _preprocess_text(text: str) -> str:
    """Normalize text and punctuation spacing.

    - Remove ellipses
    - Remove stray spaces before punctuation
    - Ensure a single space after sentence punctuation when more text follows
      (comma, semicolon, colon, exclamation, question, period),
      avoiding decimals like 3.14.
    - Collapse excess whitespace and trim.
    """
    if not text:
        return ""

    t = text
    # Remove ellipses (streamed ASR often emits ... transiently)
    t = t.replace("...", "")

    # Normalize any newlines/tabs to spaces early to simplify spacing logic
    t = re.sub(r"[\t\n\r]+", " ", t)

    # Remove spaces immediately before punctuation like ',', '!', '?', ';', ':'
    t = re.sub(r"\s+([,!?;:])", r"\1", t)
    # Remove spaces before a period unless it's a decimal number (e.g., '3 .14' -> '3.14')
    t = re.sub(r"\s+(\.)", r"\1", t)

    # Ensure exactly one space after , ! ? ; : when the next visible char is a word character
    # This avoids inserting a space before another punctuation mark (e.g., '?.' remains '?.')
    t = re.sub(r"([,!?;:])\s*(\w)", r"\1 \2", t)

    # Ensure space after a period when the next visible char is a word character, avoiding decimals like 3.14
    t = re.sub(r"(?<!\d)\.\s*(\w)", r". \1", t)

    # Compress multiple spaces
    t = re.sub(r"\s{2,}", " ", t)

    return t.strip()


def _should_paste_now(text: str) -> bool:
    """Decide whether to paste pending text now according to throttle & punctuation."""
    global _last_paste_time
    if not text:
        return False

    now = time.time()
    if (now - _last_paste_time) < PASTE_THROTTLE_DELAY:
        return False

    if PASTE_ON_PUNCTUATION and text[-1] in ".!?":
        return True

    return len(text) >= MIN_TEXT_LENGTH


def _paste_text(new_text: str):
    """
    Paste the new_text into the active input using clipboard paste + optional undo.
    Implementation intentionally replaces the previously pasted text to avoid jumbled output.
    """
    global _current_displayed_text, _last_paste_time, _session_start_index, _leading_separator

    if not new_text:
        return

    # Build effective text, prefixing a separator if needed (to separate utterances)
    with _state_lock:
        sep = _leading_separator
    effective_text = (sep + new_text) if sep else new_text

    # If same as current (after trimming for comparison), nothing to do
    if effective_text.strip() == _current_displayed_text.strip():
        return

    # Keep a minimal pause for automation responsiveness
    original_pause = pyautogui.PAUSE
    pyautogui.PAUSE = 0.01
    try:
        # One-time session setup: put caret at end and create a new line if needed
        if _session_start_index is None:
            pyautogui.hotkey(MOD_KEY, "end")
            pyautogui.hotkey("shift", "enter")
            time.sleep(0.02)
            _session_start_index = 0

        # If there's previously pasted text, undo it first to replace cleanly
        if _current_displayed_text:
            pyautogui.hotkey(MOD_KEY, "z")
            time.sleep(0.01)

        pyperclip.copy(effective_text)
        pyautogui.hotkey(MOD_KEY, "v")

        _current_displayed_text = effective_text
        _last_paste_time = time.time()

    finally:
        pyautogui.PAUSE = original_pause


def _reset_state():
    """Clear internal display/pending state and cancel timers."""
    global _current_displayed_text, _pending_text, _reset_timer
    with _state_lock:
        _current_displayed_text = ""
        _pending_text = ""
        if _reset_timer:
            _reset_timer.cancel()
        _reset_timer = None


# ===== Worker thread logic =====
def _typing_worker():
    """Background worker that consumes text queue and decides when to paste."""
    global _pending_text
    while not _stop_event.is_set():
        try:
            # Wait for new text (timeout allows checking stop event)
            new_text = _text_queue.get(timeout=0.1)
            new_text = _preprocess_text(new_text)

            with _state_lock:
                _pending_text = new_text

            if _should_paste_now(_pending_text):
                _paste_text(_pending_text)
                with _state_lock:
                    _pending_text = ""
                    # Once we have pasted at least once in the new utterance, clear the leading separator
                    # so subsequent updates within the same utterance do not accumulate spaces.
                    _leading_separator = ""
            # mark task done
            _text_queue.task_done()

        except queue.Empty:
            # No new text; maybe we have pending text to paste by throttle timing
            with _state_lock:
                pending = _pending_text
            if pending and _should_paste_now(pending):
                _paste_text(pending)
                with _state_lock:
                    _pending_text = ""
                    _leading_separator = ""
            continue
        except Exception as exc:
            print("[TYPING WORKER ERROR]", exc)
            continue


# ===== Public API =====
def check_dependencies() -> bool:
    """
    Quick sanity check for pyautogui & pyperclip.
    Returns True if both are available and working.
    """
    try:
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1
        test_text = "typing_sim_test"
        pyperclip.copy(test_text)
        if pyperclip.paste() != test_text:
            return False
        return True
    except Exception as e:
        print("[TYPING DEP CHECK FAILED]", e)
        return False


def start():
    """Start the typing worker (idempotent)."""
    global _typing_thread, _stop_event
    if _typing_thread and _typing_thread.is_alive():
        return
    _stop_event.clear()
    _typing_thread = threading.Thread(target=_typing_worker, daemon=True, name="typing_worker")
    _typing_thread.start()
    print("[TYPING] Worker started")


def stop():
    """Stop the typing worker and reset state (blocking until worker stops)."""
    global _stop_event
    _stop_event.set()
    # drain queue quickly
    try:
        while not _text_queue.empty():
            _text_queue.get_nowait()
            _text_queue.task_done()
    except Exception:
        pass
    _reset_state()
    print("[TYPING] Worker signalled to stop")


def enqueue_text(text: str):
    """Add text to queue for potential pasting. Thread-safe."""
    if not text:
        return
    # Keep queue small: drop older items if queue grows too large to always favor recent text
    MAX_Q = 4
    try:
        # If queue is too large, remove oldest items
        while _text_queue.qsize() >= MAX_Q:
            try:
                _text_queue.get_nowait()
                _text_queue.task_done()
            except queue.Empty:
                break
        _text_queue.put(text)
    except Exception as e:
        print("[ENQUEUE ERROR]", e)


def schedule_final_paste(delay: float = 0.5):
    """
    Schedule a final paste of any pending text after a short delay.
    Usually called on utterance_end to ensure final words are flushed.
    """
    global _reset_timer

    def _final_paste():
        global _pending_text, _current_displayed_text, _leading_separator
        # Snapshot current displayed to know if there is something to commit
        with _state_lock:
            pending = _pending_text
            had_displayed = bool(_current_displayed_text)

        # Flush any pending text first
        if pending:
            _paste_text(pending)
            with _state_lock:
                _pending_text = ""
            had_displayed = True

        # If we have displayed text (this utterance produced output), schedule a leading space
        # for the next utterance. This is prefixed to the next effective paste content.
        if had_displayed:
            with _state_lock:
                _leading_separator = " "

        # Mark current displayed text as committed so the next utterance does NOT undo it
        with _state_lock:
            _current_displayed_text = ""

    # Cancel previous timer if present
    if _reset_timer:
        _reset_timer.cancel()

    _reset_timer = threading.Timer(delay, _final_paste)
    _reset_timer.daemon = True
    _reset_timer.start()
