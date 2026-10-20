"""Text-to-speech adapters. Each turns text into an audio file the caller plays (and can interrupt).

LocalWindowsTTS — Windows OneCore voices via a WinRT worker process; prefers English (India). Default.
EdgeTTS         — Microsoft online neural voices (en-IN-PrabhatNeural by default); text leaves the machine (opt-in).
"""
from __future__ import annotations

import asyncio
import os
import re
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from tom_core.voice.config import VoiceConfig


@dataclass
class SpeechClip:
    path: str
    engine: str
    voice: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


class TTSError(RuntimeError):
    pass


def choose_voice(voices: Sequence[Tuple[str, str]], preference: Sequence[str]) -> Optional[int]:
    """Index of the best voice. Each preference matches a language tag ("en-IN") or a name part ("Mark").

    Falls back to the first English voice, then to any voice. None only when there are no voices.
    """
    if not voices:
        return None
    for pref in preference:
        p = pref.strip().lower()
        if not p:
            continue
        for i, (name, lang) in enumerate(voices):
            if (lang or "").lower() == p or p in (name or "").lower():
                return i
    for i, (_name, lang) in enumerate(voices):
        if (lang or "").lower().startswith("en"):
            return i
    return 0


_MD = [
    (re.compile(r"```.*?```", re.S), " "),                 # code blocks are never read aloud
    (re.compile(r"`([^`]*)`"), r"\1"),
    (re.compile(r"!\[[^\]]*\]\([^)]*\)"), " "),            # images
    (re.compile(r"\[([^\]]+)\]\([^)]*\)"), r"\1"),         # links → their text
    (re.compile(r"https?://\S+"), "the link"),
    (re.compile(r"[*_#>|~]+"), " "),
    (re.compile(r"^\s*[-•]\s+", re.M), ""),
]


def speech_text(text: str) -> str:
    """Markdown/report text → something that sounds natural when spoken."""
    t = str(text or "")
    for pattern, repl in _MD:
        t = pattern.sub(repl, t)
    t = re.sub(r"\s*\n\s*\n\s*", ". ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r"\.\s*\.", ".", t)


class TTSEngine:
    name = "base"
    is_cloud = False

    def synthesize(self, text: str) -> SpeechClip:
        raise NotImplementedError

    def status(self) -> Dict[str, Any]:
        return {"engine": self.name, "cloud": self.is_cloud}

    def close(self) -> None:
        pass


class LocalWindowsTTS(TTSEngine):
    name = "windows"

    def __init__(self, config: VoiceConfig, *, worker=None) -> None:
        self.config = config
        self._worker = worker
        self.voice = ""

    def _ensure_worker(self):
        if self._worker is None:
            from tom_core.voice.workers import WorkerProcess
            self._worker = WorkerProcess("tts", start_timeout=30.0)
        return self._worker

    def voices(self) -> List[Dict[str, str]]:
        return list(self._ensure_worker().start().get("voices", []))

    def has_indian_english_voice(self) -> bool:
        return any(str(v.get("language", "")).lower() == "en-in" for v in self.voices())

    def synthesize(self, text: str) -> SpeechClip:
        try:
            reply = self._ensure_worker().request(
                "synth", timeout=30.0, text=text, preference=self.config.tts_voice_preference,
                rate=self.config.tts_rate)
        except Exception as exc:
            raise TTSError(f"Windows voice failed: {exc}") from None
        self.voice = reply.get("voice", "")
        return SpeechClip(path=reply["wav"], engine=self.name, voice=self.voice,
                          details={"language": reply.get("language", ""), "seconds": reply.get("seconds")})

    def status(self) -> Dict[str, Any]:
        return {"engine": self.name, "cloud": False, "voice": self.voice}

    def close(self) -> None:
        if self._worker is not None:
            self._worker.stop()


class EdgeTTS(TTSEngine):
    """Cloud TTS (opt-in only): the text is sent to Microsoft's online speech service."""
    name = "edge"
    is_cloud = True

    def __init__(self, config: VoiceConfig) -> None:
        self.voice = config.edge_voice
        self.rate = config.edge_rate
        self._n = 0

    def synthesize(self, text: str) -> SpeechClip:
        import edge_tts
        self._n += 1
        path = os.path.join(tempfile.gettempdir(), f"tom_edge_{os.getpid()}_{self._n}.mp3")
        try:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(edge_tts.Communicate(text[:2000], self.voice, rate=self.rate).save(path))
            finally:
                loop.close()
        except Exception as exc:
            raise TTSError(f"edge-tts failed: {exc}") from None
        return SpeechClip(path=path, engine=self.name, voice=self.voice)

    def status(self) -> Dict[str, Any]:
        return {"engine": self.name, "cloud": True, "voice": self.voice}


def make_tts(config: VoiceConfig) -> Optional[TTSEngine]:
    """The configured engine, or None for "sapi" (VoiceTools keeps its pyttsx3 path for that)."""
    if config.tts_engine == "edge":
        return EdgeTTS(config)
    if config.tts_engine == "local" and os.name == "nt":
        return LocalWindowsTTS(config)
    return None
