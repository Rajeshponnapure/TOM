"""Which data routes leave this machine right now (ADR-005, PRD NFR-006 / §7 disclosure).

Every route is local unless the owner opted in explicitly; this module only *reports* the
current routing so the UI, CLI and health report can disclose it. It never changes settings.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Route:
    name: str          # what kind of data
    provider: str      # who handles it
    cloud: bool        # True = leaves the machine
    how_to_change: str


def current_routes() -> List[Route]:
    from tom_core.voice import load_config
    from tools import llm_factory

    routes: List[Route] = []
    if llm_factory.provider() == "groq":
        routes.append(Route("Prompts and replies (LLM)", "Groq (cloud)", True,
                            "set TOM_LLM_PROVIDER=ollama to keep prompts local"))
    else:
        routes.append(Route("Prompts and replies (LLM)", "Ollama on this machine", False,
                            "opt in to Groq with TOM_LLM_PROVIDER=groq"))

    enabled = os.environ.get("HINDSIGHT_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")
    base = (os.environ.get("HINDSIGHT_BASE_URL") or "").strip()
    local_server = base.startswith(("http://localhost", "http://127.0.0.1"))
    if not enabled:
        routes.append(Route("Long-term memory", "off", False, "set HINDSIGHT_ENABLED=1"))
    elif not base or local_server:
        routes.append(Route("Long-term memory", "local store on this machine" if not base else f"Hindsight @ {base}",
                            False, "opt in to Hindsight Cloud with HINDSIGHT_BASE_URL"))
    else:
        routes.append(Route("Long-term memory", f"Hindsight @ {base} (cloud)", True,
                            "unset HINDSIGHT_BASE_URL to keep memory on this machine"))

    voice = load_config()
    routes.append(Route("Microphone audio (speech recognition)",
                        "Google (cloud)" if voice.asr_is_cloud else f"faster-whisper {voice.asr_model} on this machine",
                        voice.asr_is_cloud,
                        "VOICE_RECOGNITION_ENGINE=local" if voice.asr_is_cloud else "opt in: VOICE_RECOGNITION_ENGINE=google"))
    routes.append(Route("Spoken replies (text-to-speech)",
                        f"Microsoft online voice {voice.edge_voice} (cloud)" if voice.tts_is_cloud
                        else "Windows voices on this machine",
                        voice.tts_is_cloud,
                        "TOM_TTS_ENGINE=local" if voice.tts_is_cloud else "opt in: TOM_TTS_ENGINE=edge"))
    return routes


def disclosure_text() -> str:
    lines = []
    for r in current_routes():
        where = "LEAVES THIS MACHINE" if r.cloud else "stays local"
        lines.append(f"  [{where}] {r.name}: {r.provider}  ({r.how_to_change})")
    cloud = sum(1 for r in current_routes() if r.cloud)
    head = "All data stays on this machine." if cloud == 0 else f"{cloud} route(s) send data to a cloud service."
    return "Privacy routes: " + head + "\n" + "\n".join(lines)
