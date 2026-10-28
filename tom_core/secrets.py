"""Ask the owner for an API key when a feature needs one, then keep it.

A feature that needs a credential (an LLM provider, a cloud asset or image service, a weather or
maps key) calls `ensure("openai")`: if the key is already in the environment it returns it; if not it
returns a `needs_key` prompt the agent shows the owner. When the owner replies with the value, the
agent calls `save(...)`, which writes it to TOM's `.env` (via `tools.project_paths.env_file`) and
into this process, so the very next call to `ensure` succeeds and the key survives a restart.

Keys live only on this machine, in the owner's own `.env`. They are never printed back, never sent
anywhere by this module, and because each is stored under a `*_API_KEY` / `*_TOKEN` style name the
redactor (`tom_core.observability.redact`) masks the value in every log, task record and export.
"""
from __future__ import annotations

import os
import re
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional

_LOCK = threading.Lock()


@dataclass(frozen=True)
class Service:
    name: str
    env_vars: List[str]                       # the variable(s) this service needs
    label: str = ""                           # human name
    get_key_url: str = ""                      # where the owner creates a key
    free: bool = False                         # no key needed at all

    @property
    def title(self) -> str:
        return self.label or self.name.title()


# Services TOM can use. "free" ones need no key (listed so TOM can say so instead of asking).
_SERVICES: Dict[str, Service] = {
    s.name: s for s in [
        Service("openai", ["OPENAI_API_KEY"], "OpenAI", "https://platform.openai.com/api-keys"),
        Service("anthropic", ["ANTHROPIC_API_KEY"], "Anthropic (Claude)", "https://console.anthropic.com/settings/keys"),
        Service("groq", ["GROQ_API_KEY"], "Groq", "https://console.groq.com/keys"),
        Service("gemini", ["GEMINI_API_KEY"], "Google Gemini", "https://aistudio.google.com/app/apikey"),
        Service("openweather", ["OPENWEATHER_API_KEY"], "OpenWeatherMap", "https://home.openweathermap.org/api_keys"),
        Service("googlemaps", ["GOOGLE_MAPS_API_KEY"], "Google Maps", "https://console.cloud.google.com/google/maps-apis/credentials"),
        Service("elevenlabs", ["ELEVENLABS_API_KEY"], "ElevenLabs", "https://elevenlabs.io/app/settings/api-keys"),
        Service("stability", ["STABILITY_API_KEY"], "Stability AI", "https://platform.stability.ai/account/keys"),
        Service("replicate", ["REPLICATE_API_TOKEN"], "Replicate", "https://replicate.com/account/api-tokens"),
        Service("huggingface", ["HUGGINGFACE_API_TOKEN"], "Hugging Face", "https://huggingface.co/settings/tokens"),
        Service("github", ["GITHUB_TOKEN"], "GitHub", "https://github.com/settings/tokens"),
        Service("sketchfab", ["SKETCHFAB_API_TOKEN"], "Sketchfab", "https://sketchfab.com/settings/password"),
        # needs no key
        Service("polyhaven", [], "Poly Haven (CC0 assets)", "", free=True),
        Service("openmeteo", [], "Open-Meteo weather", "", free=True),
    ]
}

# Alternative spellings the owner might type, mapped to the canonical service name.
_ALIASES = {
    "open ai": "openai", "chatgpt": "openai", "gpt": "openai",
    "claude": "anthropic", "anthropic claude": "anthropic",
    "google gemini": "gemini", "google ai": "gemini",
    "weather": "openweather", "openweathermap": "openweather",
    "maps": "googlemaps", "google maps": "googlemaps",
    "eleven labs": "elevenlabs", "11labs": "elevenlabs",
    "stability ai": "stability", "stable diffusion": "stability",
    "hugging face": "huggingface", "hf": "huggingface",
    "poly haven": "polyhaven", "polyhaven cc0": "polyhaven",
}

_KEYISH = re.compile(r"(?i)(key|token|secret|password|pass|credential)")


def resolve(name: str) -> Optional[Service]:
    n = (name or "").strip().lower()
    n = _ALIASES.get(n, n)
    if n in _SERVICES:
        return _SERVICES[n]
    # match on a known env var name too ("set OPENAI_API_KEY ...")
    up = name.strip().upper()
    for svc in _SERVICES.values():
        if up in svc.env_vars:
            return svc
    return None


def _env_file():
    from tools.project_paths import env_file
    return env_file()


def get(var: str) -> str:
    return (os.environ.get(var) or "").strip()


def missing(service: str) -> List[str]:
    """Which required env vars for `service` are not set. Empty = ready (or needs no key)."""
    svc = resolve(service)
    if svc is None:
        return []
    return [v for v in svc.env_vars if not get(v)]


def have(service: str) -> bool:
    svc = resolve(service)
    return bool(svc) and not missing(service)


@dataclass
class KeyPrompt:
    """Returned to the agent when a feature needs a key the owner hasn't given yet."""
    service: str
    env_var: str
    message: str
    status: str = "needs_key"
    response_type: str = "api_key"
    extra: Dict[str, str] = field(default_factory=dict)

    def as_result(self) -> Dict[str, object]:
        return {"status": self.status, "response_type": self.response_type,
                "service": self.service, "env_var": self.env_var, "message": self.message, **self.extra}


def ensure(service: str) -> Dict[str, object]:
    """`{"status":"success","key":...,"env_var":...}` when the key is present (or none is needed),
    else a `needs_key` prompt dict to show the owner."""
    svc = resolve(service)
    if svc is None:
        return {"status": "error", "message": f"I don't have a known API-key slot for '{service}'. "
                "Tell me the exact environment variable name and I'll store it."}
    if svc.free or not svc.env_vars:
        return {"status": "success", "key": "", "env_var": "", "free": True,
                "message": f"{svc.title} needs no API key."}
    miss = missing(service)
    if not miss:
        var = svc.env_vars[0]
        return {"status": "success", "key": get(var), "env_var": var}
    var = miss[0]
    where = f" You can create one at {svc.get_key_url}." if svc.get_key_url else ""
    msg = (f"I need your {svc.title} API key to do that.{where}\n"
           f"Paste it here and I'll save it to your .env as {var} (kept on this machine, never shown "
           f"again in logs). Or say \"cancel\".")
    return KeyPrompt(service=svc.name, env_var=var, message=msg).as_result()


def looks_like_key(text: str) -> bool:
    """A bare credential: one long token of key characters, no spaces (so it isn't a sentence)."""
    t = (text or "").strip().strip("\"'")
    return bool(re.fullmatch(r"[A-Za-z0-9._\-]{12,}", t))


def save(env_var: str, value: str, *, audit_ok: bool = True) -> Dict[str, object]:
    """Write `env_var=value` to TOM's .env and into this process. Returns a redaction-safe result."""
    value = (value or "").strip().strip("\"'")
    env_var = (env_var or "").strip()
    if not env_var or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", env_var):
        return {"status": "error", "message": f"'{env_var}' is not a valid environment variable name."}
    if not value:
        return {"status": "error", "message": "No value was given to save."}
    path = _env_file()
    try:
        with _LOCK:
            lines: List[str] = []
            found = False
            if path.exists():
                lines = path.read_text(encoding="utf-8").splitlines()
            for i, line in enumerate(lines):
                if re.match(rf"\s*(export\s+)?{re.escape(env_var)}\s*=", line):
                    lines[i] = f"{env_var}={value}"
                    found = True
                    break
            if not found:
                lines.append(f"{env_var}={value}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.environ[env_var] = value                        # redactor now masks this value everywhere
    except Exception as exc:
        return {"status": "error", "message": f"Could not save the key: {exc}"}
    if audit_ok:
        try:
            from tom_core.tools.guard import audit
            audit({"event": "secret_saved", "env_var": env_var, "value": value})   # value redacted by audit()
        except Exception:
            pass
    return {"status": "success", "response_type": "api_key", "env_var": env_var,
            "message": f"Saved. {env_var} is set for this session and written to your .env."}


def status_report() -> Dict[str, object]:
    """Which services have a key, which don't, which need none — never the values."""
    ready, needed, free = [], [], []
    for svc in _SERVICES.values():
        if svc.free or not svc.env_vars:
            free.append(svc.title)
        elif not missing(svc.name):
            ready.append(f"{svc.title} ({svc.env_vars[0]})")
        else:
            needed.append(f"{svc.title} ({svc.env_vars[0]})")
    lines = ["API keys TOM can use (values are never shown):"]
    if ready:
        lines.append("  Set: " + ", ".join(sorted(ready)))
    if needed:
        lines.append("  Not set yet: " + ", ".join(sorted(needed)))
    if free:
        lines.append("  No key needed: " + ", ".join(sorted(free)))
    return {"status": "success", "response_type": "api_key",
            "ready": ready, "needed": needed, "free": free, "message": "\n".join(lines)}
