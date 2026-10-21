"""Microphone capture that keeps the whole request (PRD Â§7: push-to-talk + voice activity detection).

speech_recognition's listen() ended a request at the first 0.8 s pause, cut it at 15 s, and dropped
quiet trailing words once its dynamic energy threshold crept up. This recorder instead:

* waits up to `start_timeout` for speech and keeps `pre_roll` seconds from before the detected
  onset, so words spoken the instant Talk is pressed are not lost;
* ends only after `end_silence` seconds of continuous quiet *after* speech, at `max_seconds`, or as
  soon as the user presses Talk again (`stop` event) â€” the user decides when a request is finished;
* judges "quiet" against the noise floor Ã— keep_ratio, where the floor is the pre-speech estimate
  or, if higher, the 10th-percentile level of the last 3 s. The running estimate keeps a floor that
  was guessed too low (noisy room, speech at the press) from recording until max_seconds; it stays
  near the room's noise during speech because speech always contains gaps. (A rule based on the
  median of recent speech was tried and rejected: falling intonation at the end of a sentence plus
  a 1.3 s pause already counted as 2 s of quiet â€” measured with synthesized speech.)

`record()` only needs a `read()` that returns the next chunk of 16-bit mono PCM, so it is tested
with recorded audio instead of a microphone. Durations are measured in audio time, not wall time.
"""
from __future__ import annotations

import math
import sys
import threading
from array import array
from collections import deque
from dataclasses import dataclass
from typing import Callable, Deque, List, Optional, Tuple

_FLOOR_WINDOW_S = 2.0          # pre-speech audio the noise floor is estimated from
_RUNNING_FLOOR_S = 3.0         # audio the running floor is estimated from once speech started
_SPEECH_ONSET_S = 0.1          # this much continuous loud audio means speech has started
_KEEP_TRAILING_QUIET_S = 0.4   # quiet kept after the last word (the rest only slows ASR down)
_FLOOR_GUESS = 300.0           # assumed room noise until 0.3 s of audio says otherwise
_MAX_FLOOR = 2500.0            # a floor above this is speech caught at the press, not room noise


@dataclass(frozen=True)
class CaptureSettings:
    start_timeout: float = 8.0
    end_silence: float = 2.5
    max_seconds: float = 60.0
    pre_roll: float = 1.0
    min_threshold: float = 250.0     # 16-bit RMS: nothing quieter ever counts as speech
    speech_ratio: float = 3.0        # speech starts above noise floor Ã— this
    keep_ratio: float = 1.8          # ...and continues while above floor Ã— this


@dataclass
class Recording:
    pcm: bytes                       # 16-bit mono PCM; empty when no speech was heard
    sample_rate: int
    sample_width: int
    reason: str                      # silence | stopped | max | no_speech | eof
    seconds: float                   # length of `pcm`
    noise_floor: Optional[float]     # pass back in next time, so the next press starts calibrated


def rms16(chunk: bytes) -> float:
    """Root-mean-square level of little-endian 16-bit PCM (0 â€“ 32768)."""
    samples = array("h")
    samples.frombytes(chunk[: len(chunk) - len(chunk) % 2])
    if not samples:
        return 0.0
    if sys.byteorder == "big":
        samples.byteswap()
    return math.sqrt(sum(s * s for s in samples) / len(samples))


def _percentile(values: List[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))]


def _trim(window: Deque[Tuple[float, float]], seconds: float) -> None:
    total = sum(s for _, s in window)
    while total > seconds and len(window) > 1:
        total -= window.popleft()[1]


def record(read: Callable[[], bytes], sample_rate: int, *, sample_width: int = 2,
           settings: CaptureSettings = CaptureSettings(), stop: Optional[threading.Event] = None,
           on_level: Optional[Callable[[float], None]] = None,
           noise_floor: Optional[float] = None) -> Recording:
    """Record one spoken request from `read()` (each call returns the next PCM chunk)."""
    bytes_per_second = float(sample_rate * sample_width)
    history: Deque[Tuple[float, float]] = deque()      # (level, seconds) before speech
    recent: Deque[Tuple[float, float]] = deque()       # (level, seconds) of the last 3 s
    pre: Deque[Tuple[bytes, float]] = deque()          # (chunk, seconds) pre-roll
    frames: List[bytes] = []
    quiet_chunks: List[float] = []                     # durations of the quiet run at the end
    speaking = False
    waited = recorded = quiet = loud = heard_for = 0.0
    floor = noise_floor
    reason = "eof"

    while True:
        if stop is not None and stop.is_set():
            reason = "stopped"
            break
        chunk = read()
        if not chunk:
            break
        secs = len(chunk) / bytes_per_second
        level = rms16(chunk)
        if on_level is not None:
            on_level(min(1.0, level / 8000.0))
        recent.append((level, secs))
        _trim(recent, _RUNNING_FLOOR_S)

        if not speaking:
            heard_for += secs
            history.append((level, secs))
            _trim(history, _FLOOR_WINDOW_S)
            estimate = _percentile([lv for lv, _ in history], 0.1)
            known = noise_floor if noise_floor else (_FLOOR_GUESS if heard_for < 0.3 else None)
            floor = min(estimate, known) if known else estimate
            floor = min(floor, _MAX_FLOOR)
            pre.append((chunk, secs))
            while sum(s for _, s in pre) > settings.pre_roll and len(pre) > 1:
                pre.popleft()
            loud = loud + secs if level > max(settings.min_threshold, floor * settings.speech_ratio) else 0.0
            if loud >= _SPEECH_ONSET_S:
                speaking = True
                frames = [c for c, _ in pre]
                recorded = sum(s for _, s in pre)
                pre.clear()
                continue
            waited += secs
            if waited >= settings.start_timeout:
                reason = "no_speech"
                break
            continue

        frames.append(chunk)
        recorded += secs
        running = _percentile([lv for lv, _ in recent], 0.1)
        if level < max(settings.min_threshold * 0.8, max(floor or 0.0, running) * settings.keep_ratio):
            quiet += secs
            quiet_chunks.append(secs)
        else:
            quiet = 0.0
            quiet_chunks = []
        if quiet >= settings.end_silence:
            reason = "silence"
            break
        if recorded >= settings.max_seconds:
            reason = "max"
            break

    if not speaking:
        return Recording(b"", sample_rate, sample_width, "no_speech" if reason == "eof" else reason,
                         0.0, floor)
    # Drop most of the trailing silence: it carries no words and only slows recognition down.
    keep, trailing = 0, 0.0
    for secs in quiet_chunks:
        if trailing + secs > _KEEP_TRAILING_QUIET_S:
            break
        keep += 1
        trailing += secs
    drop = len(quiet_chunks) - keep
    if drop:
        frames = frames[:-drop]
    pcm = b"".join(frames)
    return Recording(pcm, sample_rate, sample_width, reason, len(pcm) / bytes_per_second, floor)
