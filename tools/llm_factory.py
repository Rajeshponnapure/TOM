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


def make_chat_model(model: str, max_tokens: int = 4096, temperature: float = 0.1) -> Any:
    """Build a chat model for the active provider.

    `model` is the Ollama model name; it is ignored on Groq (the Groq model is
    chosen by GROQ_MODEL / GROQ_FAST_MODEL / GROQ_CODE_MODEL through the caller).
    """
    if provider() == "groq":
        return make_groq_model(model, max_tokens=max_tokens, temperature=temperature)

    from langchain_ollama import ChatOllama

    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    return ChatOllama(model=model, base_url=base_url, temperature=temperature,
                      num_predict=max_tokens)


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
    return f"Ollama ({os.environ.get('OLLAMA_MODEL', 'gemma4:latest')})"
