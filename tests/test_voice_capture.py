"""tom_core.voice.capture keeps the whole spoken request (owner report 2026-10-21: "it isn't taking
all my voice" — the old recorder ended at the first 0.8 s pause and cut requests at 15 s)."""
import math
import os
import random
import sys
import threading
from array import array

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tom_core.voice.capture import CaptureSettings, record, rms16  # noqa: E402

RATE = 16000
CHUNK = 1024
rng = random.Random(3)


def noise(seconds, rms=120):
    return array("h", [max(-32768, min(32767, int(rng.gauss(0, rms)))) for _ in range(int(seconds * RATE))]
                 ).tobytes()


def speech(seconds, amp=6000, noise_rms=120):
    """Voiced bursts with short gaps between "words", like real speech."""
    out = array("h")
    for i in range(int(seconds * RATE)):
        t = i / RATE
        voiced = (t % 0.35) < 0.27                       # 270 ms word, 80 ms gap
        s = amp * math.sin(2 * math.pi * 180 * t) if voiced else 0.0
        out.append(max(-32768, min(32767, int(s + rng.gauss(0, noise_rms)))))
    return out.tobytes()


def reader(pcm, on_chunk=None):
    pos = [0]

    def read():
        b = pcm[pos[0]: pos[0] + CHUNK * 2]
        pos[0] += CHUNK * 2
        if on_chunk:
            on_chunk(pos[0] / 2 / RATE)
        return b
    return read


def secs(pcm):
    return len(pcm) / 2 / RATE


S = CaptureSettings(start_timeout=8, end_silence=2.5, max_seconds=60)


def test_a_pause_shorter_than_end_silence_keeps_the_whole_request():
    audio = noise(1.0) + speech(2.0) + noise(1.8) + speech(2.0) + noise(5.0)
    rec = record(reader(audio), RATE, settings=S)
    assert rec.reason == "silence"
    # both halves (4 s) and the 1.8 s pause are kept; most trailing silence is dropped
    assert 5.8 <= rec.seconds <= 4.0 + 1.8 + 1.0 + 0.5, rec.seconds


def test_a_long_pause_ends_the_request():
    audio = noise(1.0) + speech(2.0) + noise(4.0) + speech(2.0)
    rec = record(reader(audio), RATE, settings=S)
    assert rec.reason == "silence" and rec.seconds < 4.0


def test_words_spoken_the_instant_talk_is_pressed_are_kept():
    audio = speech(3.0) + noise(4.0)
    rec = record(reader(audio), RATE, settings=S)
    assert rec.reason == "silence"
    assert rms16(rec.pcm[: CHUNK * 2]) > 1000          # the very first chunk is speech, not lost
    assert rec.seconds >= 3.0


def test_quiet_speech_counts_as_speech():
    audio = noise(1.0) + speech(3.0, amp=1200) + noise(4.0)
    rec = record(reader(audio), RATE, settings=S)
    assert rec.reason == "silence" and rec.seconds >= 3.0


def test_steady_noise_in_a_loud_room_does_not_record_until_the_limit():
    audio = speech(2.0, amp=9000, noise_rms=700) + noise(8.0, rms=700)
    rec = record(reader(audio), RATE, settings=S)
    assert rec.reason == "silence" and rec.seconds < 6.0


def test_pressing_talk_again_ends_the_request_and_keeps_what_was_said():
    stop = threading.Event()
    audio = noise(0.5) + speech(10.0)
    rec = record(reader(audio, on_chunk=lambda t: t > 3.0 and stop.set()), RATE, settings=S, stop=stop)
    assert rec.reason == "stopped" and 2.0 < rec.seconds < 3.5


def test_no_speech_means_no_audio():
    rec = record(reader(noise(10.0)), RATE, settings=CaptureSettings(start_timeout=3))
    assert rec.reason == "no_speech" and rec.pcm == b""
    assert rec.noise_floor is not None and rec.noise_floor < 250


def test_long_requests_are_not_cut_at_15_seconds():
    audio = noise(0.5) + speech(25.0) + noise(4.0)
    rec = record(reader(audio), RATE, settings=S)
    assert rec.reason == "silence" and rec.seconds >= 25.0


def test_max_seconds_is_a_hard_limit():
    rec = record(reader(noise(0.5) + speech(20.0)), RATE, settings=CaptureSettings(max_seconds=6))
    assert rec.reason == "max" and rec.seconds <= 6.2


# ── VoiceTools.listen_neural uses the recorder ───────────────────────────

class _ASR:
    def __init__(self):
        self.wavs = []

    def transcribe_wav(self, wav):
        self.wavs.append(wav)
        from tom_core.voice.asr import ASRResult
        return ASRResult(text="open chrome and then email my manager", engine="faster-whisper", seconds=0.3)


@pytest.fixture
def vt(monkeypatch):
    pytest.importorskip("speech_recognition")
    monkeypatch.setenv("VOICE_INPUT_ENABLED", "false")
    monkeypatch.setenv("VOICE_OUTPUT_ENABLED", "false")
    from contextlib import contextmanager
    from tools.voice_tools import VoiceTools
    v = VoiceTools()
    v.input_enabled, v._recognizer = True, object()
    v._asr = _ASR()
    v.mic_audio = noise(0.5) + speech(2.0) + noise(1.5) + speech(2.0) + noise(4.0)

    @contextmanager
    def fake_mic():
        yield reader(v.mic_audio, on_chunk=getattr(v, "on_chunk", None)), RATE, 2
    v._microphone = fake_mic
    return v


def test_listen_neural_records_the_whole_request_and_recognises_it(vt):
    res = vt.listen_neural(timeout=8)
    assert res["status"] == "success" and res["text"].startswith("open chrome")
    assert res["ended_by"] == "silence" and res["audio_seconds"] >= 5.5
    assert vt._asr.wavs and vt._asr.wavs[0][:4] == b"RIFF"


def test_cancel_listening_throws_the_audio_away(vt):
    vt.mic_audio = noise(0.5) + speech(10.0)
    vt.on_chunk = lambda t: t > 2.0 and vt.cancel_listening()
    assert vt.listen_neural(timeout=8)["status"] == "cancelled" and not vt._asr.wavs


def test_finish_listening_sends_what_was_said(vt):
    vt.mic_audio = noise(0.5) + speech(10.0)
    vt.on_chunk = lambda t: t > 2.0 and vt.finish_listening()
    res = vt.listen_neural(timeout=8)
    assert res["status"] == "success" and res["ended_by"] == "stopped"
