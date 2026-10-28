"""Speech-to-text adapters. Each takes 16 kHz mono WAV bytes and returns an ASRResult.

LocalWhisperASR — faster-whisper in an isolated worker process; local files only (default).
GoogleASR       — SpeechRecognition's Google Web Speech API; audio leaves the machine (opt-in).
"""
from __future__ import annotations

import os
import re
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from tom_core.voice.config import VoiceConfig

# Phrases Whisper is known to invent from silence / noise (training-data artefacts).
_HALLUCINATIONS = {
    "thank you", "thank you.", "thanks for watching", "thanks for watching!", "thank you for watching",
    "you", "bye", "bye.", "subscribe", "please subscribe", ".", "...",
}


@dataclass
class ASRResult:
    text: str
    engine: str
    language: str = ""
    seconds: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


class ASRError(RuntimeError):
    pass


def clean_transcript(segments: Iterable[Dict[str, Any]]) -> str:
    """Join segment texts, dropping segments that are probably not speech."""
    kept: List[str] = []
    for seg in segments:
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        # Whisper's own signals: likely silence AND low confidence → not speech.
        if float(seg.get("no_speech_prob", 0.0)) > 0.6 and float(seg.get("avg_logprob", 0.0)) < -1.0:
            continue
        kept.append(text)
    joined = re.sub(r"\s+", " ", " ".join(kept)).strip()
    return "" if joined.lower() in _HALLUCINATIONS else joined


def find_cuda_runtime_dir(configured: str = "") -> str:
    """A folder holding the CUDA 12 cuBLAS runtime CTranslate2 needs, or "".

    Order: TOM_CUDA_LIB_DIR → a PATH entry that already has it → Ollama's bundled CUDA 12 runtime.
    Borrowing Ollama's copy avoids a ~1 GB download but follows Ollama's install layout; set
    TOM_CUDA_LIB_DIR to pin a different location.
    """
    dll = "cublas64_12.dll" if os.name == "nt" else "libcublas.so.12"
    candidates = [configured] if configured else []
    candidates += [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        candidates.append(str(Path(local) / "Programs" / "Ollama" / "lib" / "ollama" / "cuda_v12"))
    for folder in candidates:
        if folder and (Path(folder) / dll).is_file():
            return folder
    return ""


# Approximate VRAM for int8_float16 weights + encoder activations, used for admission only.
_VRAM_NEED_MB = {"tiny": 300, "base": 400, "small": 700, "medium": 1300, "turbo": 1200,
                 "large-v3-turbo": 1200, "distil": 1200, "large": 2200}


def vram_need_mb(model: str) -> int:
    name = model.lower()
    for key in ("large-v3-turbo", "turbo", "distil", "large", "medium", "small", "base", "tiny"):
        if key in name:
            return _VRAM_NEED_MB[key]
    return 2200


class ASREngine:
    name = "base"
    is_cloud = False

    def transcribe_wav(self, wav: bytes, language: Optional[str] = None) -> ASRResult:
        raise NotImplementedError

    def status(self) -> Dict[str, Any]:
        return {"engine": self.name, "cloud": self.is_cloud}

    def close(self) -> None:
        pass


class LocalWhisperASR(ASREngine):
    name = "faster-whisper"

    def __init__(self, config: VoiceConfig, *, worker=None) -> None:
        self.config = config
        self._worker = worker
        self._lock = threading.Lock()
        self.admission_reason = ""

    def _ensure_worker(self):
        with self._lock:
            if self._worker is not None:
                return self._worker
            from tom_core.resources.gpu import admit_gpu_job, query_gpu_memory
            from tom_core.voice.workers import WorkerProcess

            cfg = self.config
            if not os.path.isdir(cfg.asr_model) and cfg.model_dir() is None:
                raise ASRError(
                    f"Local speech model '{cfg.asr_model}' was not found in "
                    f"{', '.join(cfg.asr_model_dirs)}. TOM does not download models; point "
                    f"TOM_ASR_MODEL_DIR at a cache that has it, or opt in to cloud ASR "
                    f"(VOICE_RECOGNITION_ENGINE=google).")
            cuda_dir = find_cuda_runtime_dir(cfg.cuda_lib_dir)
            admission = admit_gpu_job(vram_need_mb(cfg.asr_model), cfg.asr_vram_reserve_mb,
                                      requested=cfg.asr_device,
                                      gpu=query_gpu_memory() if cfg.asr_device != "cpu" else None,
                                      cuda_available=bool(cuda_dir))
            self.admission_reason = admission.reason
            env = {
                "TOM_ASR_MODEL": cfg.asr_model,
                "TOM_ASR_DOWNLOAD_ROOT": cfg.model_dir() or "",
                "TOM_ASR_DEVICE_RESOLVED": admission.device,
                "TOM_CUDA_LIB_DIR_RESOLVED": cuda_dir if admission.device == "cuda" else "",
            }
            self._worker = WorkerProcess("asr", env=env, start_timeout=180.0)
            return self._worker

    def warm_up(self) -> Dict[str, Any]:
        """Start the worker and load the model now, so the first utterance is fast."""
        try:
            return self._ensure_worker().start()
        except Exception as exc:
            raise ASRError(str(exc)) from None

    def transcribe_wav(self, wav: bytes, language: Optional[str] = None) -> ASRResult:
        fd, path = tempfile.mkstemp(prefix="tom_asr_", suffix=".wav")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(wav)
            lang = language if language is not None else self.config.asr_language
            reply = self._ensure_worker().request(
                "transcribe", timeout=120.0, wav=path, language=lang, hotwords=self.config.asr_hotwords)
        except ASRError:
            raise
        except Exception as exc:
            raise ASRError(f"Local speech recognition failed: {exc}") from None
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
        return ASRResult(text=reply.get("text", ""), engine=self.name, language=reply.get("language", ""),
                         seconds=float(reply.get("seconds", 0.0)),
                         details={k: reply.get(k) for k in ("audio_seconds", "language_probability")})

    def status(self) -> Dict[str, Any]:
        info = dict(self._worker.info) if self._worker is not None else {}
        return {"engine": self.name, "cloud": False, "model": self.config.asr_model,
                "loaded": bool(self._worker is not None and self._worker.alive),
                "device": info.get("device", ""), "admission": self.admission_reason,
                "fallback": info.get("fallback", "")}

    def close(self) -> None:
        if self._worker is not None:
            self._worker.stop()


class GoogleASR(ASREngine):
    """Cloud ASR (opt-in only): audio is sent to Google's Web Speech API."""
    name = "google"
    is_cloud = True

    def __init__(self, language: Optional[str] = "en") -> None:
        # Indian English by default: better accent handling than en-US for this user (PRD §7).
        self.language = "en-IN" if (language or "en").lower() in ("en", "en-in") else language

    def transcribe_wav(self, wav: bytes, language: Optional[str] = None) -> ASRResult:
        import speech_recognition as sr
        audio = sr.AudioData(*_pcm_from_wav(wav))
        try:
            text = sr.Recognizer().recognize_google(audio, language=self.language)
        except sr.UnknownValueError:
            text = ""
        except sr.RequestError as exc:
            raise ASRError(f"Google speech service error: {exc}") from None
        return ASRResult(text=(text or "").strip(), engine=self.name, language=self.language)


def _pcm_from_wav(wav: bytes):
    """(frames, sample_rate, sample_width) — the arguments speech_recognition.AudioData takes."""
    import io
    import wave
    with wave.open(io.BytesIO(wav)) as w:
        return w.readframes(w.getnframes()), w.getframerate(), w.getsampwidth()


def make_asr(config: VoiceConfig) -> ASREngine:
    if config.asr_engine == "google":
        return GoogleASR(config.asr_language)
    return LocalWhisperASR(config)
