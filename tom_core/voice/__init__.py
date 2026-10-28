"""Voice adapters (PRD §7): capture, ASR and TTS are separate and independently replaceable.

Heavy native engines run in worker processes (see workers.py). WinRT speech must never be
imported into TOM's own process: loading it first makes onnxruntime, torch and CTranslate2
crash with an access violation (measured 2026-10-21, docs/migration/baseline.md §8).
"""
from tom_core.voice.config import VoiceConfig, load_config

__all__ = ["VoiceConfig", "load_config"]
