"""
LLM factory — one place that builds every chat model TOM uses.

Providers (TOM_LLM_PROVIDER):
  * "ollama" (default) — fully local via langchain-ollama.
  * "groq"            — hosted, OpenAI-compatible models via langchain-groq.
                        Useful on machines that cannot run a large local model.

Every caller gets a LangChain chat model with the same `.ainvoke()` surface,
so the rest of TOM never needs to know which provider is active.
"""

from __future__ import annotations

import os
from typing import Any

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
# Reasoning models spend part of the token budget on hidden reasoning; a tiny
# max_tokens (TOM's chat slot uses 256) can leave the visible answer empty.
_GROQ_MIN_TOKENS = 1024


def provider() -> str:
    value = (os.environ.get("TOM_LLM_PROVIDER") or "ollama").strip().lower()
    return value if value in ("ollama", "groq") else "ollama"


def groq_model(slot: str = "primary") -> str:
    """Model id for a slot when running on Groq. Slot: primary | fast | code."""
    base = os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL).strip() or DEFAULT_GROQ_MODEL
    if slot == "fast":
        return os.environ.get("GROQ_FAST_MODEL", "").strip() or base
    if slot == "code":
        return os.environ.get("GROQ_CODE_MODEL", "").strip() or base
    return base


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
