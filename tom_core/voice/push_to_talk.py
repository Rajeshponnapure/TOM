"""Push-to-talk (PRD §7): one press = one spoken request, recognised on this machine by default.

Shared by the PySide6 window and the Tkinter app so both behave the same: interrupt TOM if it is
still talking, listen until the user stops talking (tom_core.voice.capture) or presses Talk again
(finish), return the words (or a reason why there are none) plus a status line.
Callers run the words as a normal task with interface="voice"; nothing here executes anything.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

LISTEN_TIMEOUT_S = 8            # seconds to start speaking after the press
_SPEECH_STOP_WAIT_S = 2.0       # how long to wait for an interrupted reply to go quiet


@dataclass(frozen=True)
class Heard:
    text: str                   # "" when nothing usable was heard
    message: str                # one status line for the UI


def prepare(voice: Any, *, speak: bool = True) -> str:
    """Switch on the microphone (and, if `speak`, the speaker) of a VoiceTools. "" or an error message.

    speak=False leaves voice output as the user set it, e.g. the Tk app's Mute button.
    """
    voice.input_enabled = True
    if speak:
        voice.output_enabled = True
    if not voice._recognizer:
        voice._setup_input()
    if voice.output_enabled and not (voice._tts_adapter or voice._tts_engine):
        voice._setup_output()
    if not voice.input_enabled or not voice._recognizer:
        return voice._input_error or "Microphone unavailable."
    return ""


def finish(voice: Any) -> None:
    """Talk pressed again while listening: the request ends now and what was said is still sent."""
    stop = getattr(voice, "finish_listening", None)
    if stop is not None:
        stop()


def capture(voice: Any, timeout: int = LISTEN_TIMEOUT_S) -> Heard:
    """Listen for one request. Pressing while TOM is still speaking cuts the reply off first."""
    if getattr(voice, "_speaking", False):
        voice.stop_speaking()
        end = time.monotonic() + _SPEECH_STOP_WAIT_S
        while getattr(voice, "_speaking", False) and time.monotonic() < end:
            time.sleep(0.05)
    started = time.perf_counter()
    try:
        res = voice.listen_neural(timeout=timeout)
    except Exception as exc:
        return Heard("", f"Voice error: {exc}")
    text = str(res.get("text") or "").strip()
    if res.get("status") == "success" and text:
        config = getattr(voice, "config", None)
        where = "by Google (cloud)" if getattr(config, "asr_is_cloud", False) else "locally"
        return Heard(text, f"Heard in {time.perf_counter() - started:.1f}s "
                           f"(recognised {where} in {float(res.get('asr_seconds') or 0):.2f}s)")
    return Heard("", str(res.get("message") or "Didn't catch that."))
