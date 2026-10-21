"""Voice configuration from the environment â€” local engines unless a cloud engine is chosen explicitly."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# Engines that send audio or text off the machine (ADR-005: opt-in only).
CLOUD_ASR_ENGINES = {"google"}
CLOUD_TTS_ENGINES = {"edge"}

_LOCAL_ASR_ALIASES = {"local", "faster_whisper", "faster-whisper", "whisper", "offline"}

# Where an existing faster-whisper cache may already hold models (searched in order).
DEFAULT_MODEL_DIRS = (
    r"C:\voice-agent-data\cache\huggingface\hub",
    str(Path.home() / ".cache" / "huggingface" / "hub"),
)

# Preferred local voices, best first. Owner decision 2026-10-21: US English (Zira is the female
# en-US voice every Windows install has); Indian English only if no US voice exists.
DEFAULT_LOCAL_VOICE_PREFERENCE = ("en-US", "Zira", "Mark", "David", "en-IN")
# Voice gender TOM asks for first: female | male | any. Owner decision 2026-10-21: female.
DEFAULT_TTS_GENDER = "female"
# Online Microsoft neural voices â€” US English â€” used only when TOM_TTS_ENGINE=edge.
EDGE_VOICES = {"female": "en-US-JennyNeural", "male": "en-US-GuyNeural"}
DEFAULT_EDGE_VOICE = EDGE_VOICES[DEFAULT_TTS_GENDER]
# Speaking rate: 1.0 is the voice's normal pace; owner asked for "a bit" faster (2026-10-21).
DEFAULT_TTS_RATE = 1.15
DEFAULT_EDGE_RATE = "+15%"


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or "").strip() or default


@dataclass(frozen=True)
class VoiceConfig:
    asr_engine: str = "local"                    # local | google
    asr_model: str = "large-v3-turbo"            # model name in the cache, or a model directory
    asr_model_dirs: List[str] = field(default_factory=lambda: list(DEFAULT_MODEL_DIRS))
    asr_language: Optional[str] = "en"           # None = auto-detect
    asr_device: str = "auto"                     # auto | cpu | cuda
    asr_vram_reserve_mb: int = 1536              # PRD Â§19 vram_reserve_gb: 1.5
    asr_hotwords: str = ""
    cuda_lib_dir: str = ""
    tts_engine: str = "local"                    # local | edge | sapi
    tts_voice_preference: List[str] = field(default_factory=lambda: list(DEFAULT_LOCAL_VOICE_PREFERENCE))
    tts_gender: Optional[str] = DEFAULT_TTS_GENDER   # female | male | None (any)
    tts_rate: float = DEFAULT_TTS_RATE           # WinRT speaking rate (0.5 â€“ 2.0 sensible)
    edge_voice: str = DEFAULT_EDGE_VOICE
    edge_rate: str = DEFAULT_EDGE_RATE
    listen_end_silence: float = 2.5              # quiet after speech that ends a request (s)
    listen_max_seconds: float = 60.0             # longest single request (s)

    @property
    def asr_is_cloud(self) -> bool:
        return self.asr_engine in CLOUD_ASR_ENGINES

    @property
    def tts_is_cloud(self) -> bool:
        return self.tts_engine in CLOUD_TTS_ENGINES

    def model_dir(self) -> Optional[str]:
        """First configured cache directory that actually holds the ASR model (no downloads)."""
        if os.path.isdir(self.asr_model):
            return None          # an explicit model directory needs no cache root
        folder = f"models--{_hub_repo(self.asr_model).replace('/', '--')}"
        for root in self.asr_model_dirs:
            snap = Path(root) / folder / "snapshots"
            if snap.is_dir() and any((s / "model.bin").is_file() for s in snap.iterdir()):
                return root
        return None


# Copy of faster_whisper.utils._MODELS (faster-whisper 1.2.1) so the main process can locate a
# cached model without importing CTranslate2. tests/test_voice_config.py checks it stays in sync.
FASTER_WHISPER_REPOS = {
    "tiny.en": "Systran/faster-whisper-tiny.en", "tiny": "Systran/faster-whisper-tiny",
    "base.en": "Systran/faster-whisper-base.en", "base": "Systran/faster-whisper-base",
    "small.en": "Systran/faster-whisper-small.en", "small": "Systran/faster-whisper-small",
    "medium.en": "Systran/faster-whisper-medium.en", "medium": "Systran/faster-whisper-medium",
    "large-v1": "Systran/faster-whisper-large-v1", "large-v2": "Systran/faster-whisper-large-v2",
    "large-v3": "Systran/faster-whisper-large-v3", "large": "Systran/faster-whisper-large-v3",
    "distil-large-v2": "Systran/faster-distil-whisper-large-v2",
    "distil-medium.en": "Systran/faster-distil-whisper-medium.en",
    "distil-small.en": "Systran/faster-distil-whisper-small.en",
    "distil-large-v3": "Systran/faster-distil-whisper-large-v3",
    "distil-large-v3.5": "distil-whisper/distil-large-v3.5-ct2",
    "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
    "turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
}


def _hub_repo(name: str) -> str:
    """faster-whisper short name (or an explicit repo id) â†’ Hugging Face repo id."""
    return name if "/" in name else FASTER_WHISPER_REPOS.get(name, f"Systran/faster-whisper-{name}")


def load_config() -> VoiceConfig:
    # VOICE_PAUSE_THRESHOLD / VOICE_PHRASE_TIME_LIMIT (speech_recognition endpointing) are no longer
    # read: tom_core.voice.capture uses TOM_VOICE_END_SILENCE / TOM_VOICE_MAX_SECONDS instead.
    # ASR engine: TOM_ASR_ENGINE wins, then the legacy VOICE_RECOGNITION_ENGINE, then local.
    asr = _env("TOM_ASR_ENGINE") or _env("VOICE_RECOGNITION_ENGINE") or "local"
    asr = asr.lower()
    asr = "local" if asr in _LOCAL_ASR_ALIASES else asr
    if asr not in ("local", "google"):
        asr = "local"

    language = _env("TOM_ASR_LANGUAGE", "en").lower()
    dirs = [d for d in (_env("TOM_ASR_MODEL_DIR"),) if d] + list(DEFAULT_MODEL_DIRS)

    tts = _env("TOM_TTS_ENGINE", "local").lower()
    if tts not in ("local", "edge", "sapi"):
        tts = "local"
    pref = [p.strip() for p in _env("TOM_TTS_VOICE").split(",") if p.strip()]
    gender = _env("TOM_TTS_GENDER", DEFAULT_TTS_GENDER).lower()
    gender = gender if gender in ("female", "male") else None

    def _num(name: str, default: float) -> float:
        try:
            return float(_env(name, str(default)))
        except ValueError:
            return default

    return VoiceConfig(
        asr_engine=asr,
        asr_model=_env("TOM_ASR_MODEL", "large-v3-turbo"),
        asr_model_dirs=list(dict.fromkeys(dirs)),
        asr_language=None if language in ("auto", "") else language,
        asr_device=_env("TOM_ASR_DEVICE", "auto").lower(),
        asr_vram_reserve_mb=int(_num("TOM_ASR_VRAM_RESERVE_MB", 1536)),
        asr_hotwords=_env("TOM_ASR_HOTWORDS"),
        cuda_lib_dir=_env("TOM_CUDA_LIB_DIR"),
        tts_engine=tts,
        tts_voice_preference=pref + [p for p in DEFAULT_LOCAL_VOICE_PREFERENCE if p not in pref],
        tts_gender=gender,
        tts_rate=max(0.5, min(3.0, _num("TOM_TTS_RATE", DEFAULT_TTS_RATE))),
        # TOM_VOICE is the legacy edge-tts voice setting; keep honouring it.
        edge_voice=_env("TOM_EDGE_VOICE") or _env("TOM_VOICE") or EDGE_VOICES[gender or DEFAULT_TTS_GENDER],
        edge_rate=_env("TOM_VOICE_RATE", DEFAULT_EDGE_RATE),
        listen_end_silence=max(0.6, min(10.0, _num("TOM_VOICE_END_SILENCE", 2.5))),
        listen_max_seconds=max(5.0, min(300.0, _num("TOM_VOICE_MAX_SECONDS", 60.0))),
    )
