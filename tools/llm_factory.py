"""
LLM factory — one place that builds every chat model TOM uses.

Providers (TOM_LLM_PROVIDER):
  * "groq"   — hosted, OpenAI-compatible models via langchain-groq. Active by
               default whenever GROQ_API_KEY is set in .env.
  * "ollama" — fully local via langchain-ollama, plus the aliases "local" /
               "local-llm". Selected ONLY when the user asks for it explicitly.

TOM never silently swaps to a local model: while a Groq key is configured the
hosted provider stays in charge until TOM_LLM_PROVIDER=ollama says otherwise.
The one thing that is always local is the RAG embedding encoder — Groq has no
embeddings endpoint (see resolve_model("embed")), which is not a chat fallback.

Every caller gets a LangChain chat model with the same `.ainvoke()` surface,
so the rest of TOM never needs to know which provider is active.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
# Reasoning models spend part of the token budget on hidden reasoning; a tiny
# max_tokens (TOM's chat slot uses 256) can leave the visible answer empty.
_GROQ_MIN_TOKENS = 1024
# Groq accounts differ in which multimodal models they can reach, so there is
# no hard-coded default: empty means "this account has no hosted vision model".
_LOCAL_PROVIDER_ALIASES = ("ollama", "local", "local-llm", "local_llm")


def provider() -> str:
    """Active provider: "groq" (hosted) or "ollama" (local, opt-in only)."""
    value = (os.environ.get("TOM_LLM_PROVIDER") or "").strip().lower()
    if value in _LOCAL_PROVIDER_ALIASES:
        return "ollama"
    if value == "groq":
        return "groq"
    # Unset or unrecognised: hosted when it can actually run, local otherwise.
    return "groq" if (os.environ.get("GROQ_API_KEY") or "").strip() else "ollama"


def groq_vision_model() -> str:
    """Hosted vision model id for image analysis; "" when none is configured."""
    return (os.environ.get("GROQ_VISION_MODEL") or "").strip()


def _env_file_value(key: str) -> str:
    """Value for `key` as written in the project's .env ("" when absent)."""
    path = Path(__file__).resolve().parents[1] / ".env"
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            if name.strip() == key:
                return value.strip().strip('"').strip("'")
    except OSError:
        return ""
    return ""


def provider_env_conflict() -> str:
    """Message for a shell variable that overrides TOM_LLM_PROVIDER in .env.

    An exported variable normally wins over .env (tests and headless scripts
    depend on that), but a stale `TOM_LLM_PROVIDER=ollama` left in an old
    terminal silently sends TOM back to the local model. Returns "" when there
    is nothing to report.
    """
    process_value = (os.environ.get("TOM_LLM_PROVIDER") or "").strip()
    if not process_value:
        return ""
    file_value = _env_file_value("TOM_LLM_PROVIDER")
    if file_value and file_value.lower() == process_value.lower():
        return ""
    return (f"Heads-up: TOM_LLM_PROVIDER={process_value} is set in this shell and overrides "
            f".env ({file_value or 'not set'}). TOM is running on {describe()}. "
            "Unset it (Remove-Item Env:TOM_LLM_PROVIDER) if .env should decide.")


def groq_model(slot: str = "primary") -> str:
    """Model id for a slot when running on Groq. Slot: primary | fast | code."""
    base = os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL).strip() or DEFAULT_GROQ_MODEL
    if slot == "fast":
        return os.environ.get("GROQ_FAST_MODEL", "").strip() or base
    if slot == "code":
        return os.environ.get("GROQ_CODE_MODEL", "").strip() or base
    return base


# ── Groq model listing (desktop dropdown) ────────────────────────────────────
# The desktop dropdown must offer exactly what the ACTIVE provider can serve.
# Groq has no local-model concept, so an Ollama tag such as "gemma4:latest" must
# never reach it: the dropdown used to persist that name as GROQ_MODEL and every
# chat call then failed with Groq's "model not found".
_GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"
_GROQ_USER_AGENT = "TOM/1.0"
_GROQ_MODEL_CACHE_SECONDS = 300
_GROQ_MODEL_CACHE: dict = {"when": 0.0, "names": []}
# Groq serves more than chat models (speech-to-text, TTS, guard and embedding
# endpoints); none of those belong in a chat dropdown.
_GROQ_NON_CHAT_MARKERS = ("whisper", "tts", "orpheus", "guard", "embed", "rerank")


def is_groq_chat_model(name: str) -> bool:
    """True when `name` could be a Groq chat model id.

    Groq ids are namespaced ("openai/gpt-oss-120b") or bare
    ("llama-3.3-70b-versatile"). Ollama tags always carry a ":tag" suffix, so a
    colon proves the name belongs to the local provider — or that the configured
    Groq id was overwritten by one — and is rejected.
    """
    name = (name or "").strip()
    if not name or ":" in name:
        return False
    lowered = name.lower()
    return not any(marker in lowered for marker in _GROQ_NON_CHAT_MARKERS)


def groq_configured_models() -> list:
    """Groq model ids pinned in .env, in slot order (primary, fast, code)."""
    names: list = []
    for slot in ("primary", "fast", "code"):
        name = groq_model(slot)
        if name and name not in names:
            names.append(name)
    return names


def groq_available_models(api_key: str = "", timeout: float = 5.0) -> list:
    """Model ids the Groq key can reach, straight from the API (5 min cache).

    Returns [] when the key is missing or Groq is unreachable, so callers fall
    back to the ids configured in .env. Never calls Ollama.
    """
    import time as _time
    key = (api_key or os.environ.get("GROQ_API_KEY", "")).strip()
    if not key:
        return []
    now = _time.time()
    cached = _GROQ_MODEL_CACHE["names"]
    if cached and now - _GROQ_MODEL_CACHE["when"] < _GROQ_MODEL_CACHE_SECONDS:
        return list(cached)
    try:
        import json as _json
        import urllib.request as _ur
        # Groq sits behind Cloudflare, which answers 403 to the literal default
        # urllib user-agent; any other UA (this one included) is accepted.
        request = _ur.Request(_GROQ_MODELS_URL, method="GET",
                              headers={"Authorization": f"Bearer {key}",
                                       "User-Agent": _GROQ_USER_AGENT})
        with _ur.urlopen(request, timeout=timeout) as resp:
            payload = _json.loads(resp.read().decode("utf-8"))
        names = [m.get("id", "") for m in payload.get("data", []) if m.get("id")]
        if names:
            _GROQ_MODEL_CACHE.update({"when": now, "names": names})
            return names
        return list(cached)
    except Exception:
        return list(cached)


def groq_dropdown_models(timeout: float = 5.0) -> list:
    """Chat models the desktop dropdown may offer while Groq is the provider.

    Live account models first, then the ids pinned in .env so the current
    setting stays selectable. Ollama-shaped entries are dropped even when they
    came from .env: that is how a GROQ_MODEL corrupted by the old dropdown gets
    healed instead of offered again. Never returns a "model:tag" name.
    """
    names: list = []
    for name in groq_available_models(timeout=timeout):
        if is_groq_chat_model(name) and name not in names:
            names.append(name)
    for name in groq_configured_models():
        if is_groq_chat_model(name) and name not in names:
            names.append(name)
    return names


def groq_model_switch_rejection(model_name: str) -> str:
    """Why the desktop dropdown must refuse `model_name` while Groq is active.

    "" means the switch is safe; anything else is the message for the user. A
    colon is Ollama's "<model>:<tag>" shape, so refusing it here guarantees no
    local tag can ever be persisted as GROQ_MODEL again.
    """
    name = (model_name or "").strip()
    if name and is_groq_chat_model(name):
        return ""
    return (f"'{name}' is not a Groq chat model, so the model was left unchanged. "
            "Groq is the active provider — pick a Groq model from the dropdown, "
            f"or set TOM_LLM_PROVIDER=ollama in .env to run '{name or 'it'}' locally.")


# ── Ollama model resolution ──────────────────────────────────────────────────
# Slot defaults. Every slot is overridable in .env via OLLAMA_MODEL,
# OLLAMA_FAST_MODEL, OLLAMA_CODE_MODEL, OLLAMA_EMBED_MODEL.
_SLOT_DEFAULTS = {
    "primary": "gemma4:latest",
    "fast":    "qwen2.5-coder:7b-instruct",
    "code":    "qwen2.5-coder:7b-instruct",
    "embed":   "nomic-embed-text:latest",
}
# The primary slot is OLLAMA_MODEL (not OLLAMA_PRIMARY_MODEL).
_SLOT_ENV = {
    "primary": "OLLAMA_MODEL",
    "fast":    "OLLAMA_FAST_MODEL",
    "code":    "OLLAMA_CODE_MODEL",
    "embed":   "OLLAMA_EMBED_MODEL",
}


def _is_embed_model(name: str) -> bool:
    """Embedding-only models (nomic-embed-text, mxbai-embed-large, ...) cannot chat."""
    return "embed" in name.lower()


def _configured_model(slot: str) -> str:
    return (os.environ.get(_SLOT_ENV[slot], "") or "").strip() or _SLOT_DEFAULTS[slot]

_OLLAMA_MODEL_CACHE = {"when": 0.0, "names": []}


def ollama_installed_models() -> list:
    """Names of models currently installed on the Ollama server (60 s cache).

    Returns [] when the server is unreachable and nothing has been cached —
    callers then fall back to the configured name.
    """
    import time as _time
    now = _time.time()
    cached = _OLLAMA_MODEL_CACHE["names"]
    if cached and now - _OLLAMA_MODEL_CACHE["when"] < 60:
        return list(cached)
    try:
        import json as _json
        import urllib.request as _ur
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        with _ur.urlopen(f"{base_url}/api/tags", timeout=5) as resp:
            payload = _json.loads(resp.read().decode("utf-8"))
        names = [m.get("name", "") for m in payload.get("models", []) if m.get("name")]
        if names:
            _OLLAMA_MODEL_CACHE.update({"when": now, "names": names})
        return names
    except Exception:
        return list(cached)


def resolve_model(slot: str = "primary") -> str:
    """Configured model for a slot, resolved against what Ollama actually has.

    Order: .env override -> slot default -> (if that is not installed) another
    tag of the same model -> the first installed model of the right kind
    (embedding model for the embed slot, chat model otherwise). Prevents the
    404 "model not found" failure when a configured model was never pulled.
    """
    slot = slot if slot in _SLOT_DEFAULTS else "primary"
    if provider() != "ollama":
        # Embeddings always come from Ollama (RAG); chat slots come from Groq.
        return _configured_model("embed") if slot == "embed" else groq_model(slot)
    candidate = _configured_model(slot)
    installed = ollama_installed_models()
    if not installed or candidate in installed:
        # Server unreachable (keep configured name - caller reports the real
        # error later) or the configured model exists.
        return candidate
    want_embed = slot == "embed"
    stem = candidate.split(":")[0]
    same_stem = [m for m in installed if m.split(":")[0] == stem]
    right_kind = [m for m in installed if _is_embed_model(m) == want_embed]
    if not (same_stem or right_kind):
        # Nothing suitable is installed; keep the configured name so the real
        # "ollama pull" error surfaces instead of a confusing wrong-kind model.
        return candidate
    resolved = (same_stem or right_kind)[0]
    print(f"[LLM_FACTORY] {slot} model '{candidate}' is not installed on Ollama; "
          f"using '{resolved}' instead. Permanent fix: ollama pull {candidate}")
    return resolved


def make_chat_model(model: str, max_tokens: int = 4096, temperature: float = 0.1) -> Any:
    """Build a chat model for the active provider.

    `model` is the Ollama model name; it is ignored on Groq (the Groq model is
    chosen by GROQ_MODEL / GROQ_FAST_MODEL / GROQ_CODE_MODEL through the caller).
    """
    if provider() == "groq":
        return make_groq_model(model, max_tokens=max_tokens, temperature=temperature)

    from langchain_ollama import ChatOllama

    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

    # Auto-repair: if the requested model is not installed, Ollama answers
    # every call with 404 "model not found". Swap in a model that IS
    # installed so TOM keeps working (the desktop app shows the real
    # "ollama pull <name>" fix at startup).
    try:
        installed = ollama_installed_models()
        if installed and model not in installed:
            # Same-model/other-tag fallback first (e.g. 'qwen2.5-coder:latest'
            # when only that tag exists), then any installed chat model.
            stem = model.split(":")[0]
            tag_match = next((m for m in installed if m.split(":")[0] == stem), None)
            chat_match = next((m for m in installed if not _is_embed_model(m)), None)
            resolved = tag_match or chat_match or model
            if resolved != model:
                print(f"[LLM_FACTORY] Model '{model}' not installed on Ollama - "
                      f"using '{resolved}' instead. Permanent fix: ollama pull {model}")
                model = resolved
    except Exception:
        pass  # never let the safety net break model construction

    kwargs: dict = {
        "model": model,
        "base_url": base_url,
        "temperature": temperature,
        "num_predict": max_tokens,
    }
    # Qwen 3.x models emit their reasoning separately. With TOM's compact
    # chat budget, the reasoning can consume every generated token and leave
    # the visible response empty. Disable it for normal assistant responses.
    if "qwen3" in model.lower():
        kwargs["reasoning"] = False
    return ChatOllama(**kwargs)


def make_groq_model(model: str, max_tokens: int = 4096, temperature: float = 0.1) -> Any:
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("TOM_LLM_PROVIDER=groq but GROQ_API_KEY is not set. "
                           "Add it to .env or switch TOM_LLM_PROVIDER back to ollama.")
    try:
        from langchain_groq import ChatGroq
    except ImportError as exc:  # pragma: no cover - dependency hint
        raise RuntimeError("langchain-groq is not installed. Fix: pip install langchain-groq") from exc

    kwargs: dict = {
        "model": model,
        "api_key": api_key,
        "temperature": temperature,
        "max_tokens": max(int(max_tokens), _GROQ_MIN_TOKENS),
        "max_retries": 2,
        "timeout": float(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "120")),
    }
    # Qwen3 emits <think> blocks unless reasoning output is hidden.
    if "qwen" in model.lower():
        kwargs["reasoning_format"] = "hidden"
    return ChatGroq(**kwargs)


def describe() -> str:
    """Human-readable one-liner for status screens."""
    if provider() == "groq":
        return f"Groq ({groq_model('primary')})"
    return f"Ollama ({resolve_model('primary')})"
