"""Groq model listing for the desktop dropdown (no network, no tkinter).

The dropdown used to be filled from Ollama's /api/tags whatever the provider,
and the chosen name was persisted as GROQ_MODEL — after which every chat call
failed with Groq's "model not found". These tests lock in the fix: while Groq is
active the dropdown offers Groq chat models only, and an Ollama tag can never be
accepted or written back to .env.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import urllib.request

import pytest

from tools import llm_factory

PAYLOAD = {"data": [
    {"id": "openai/gpt-oss-120b"},
    {"id": "llama-3.3-70b-versatile"},
    {"id": "whisper-large-v3"},
    {"id": "canopylabs/orpheus-v1-english"},
    {"id": "meta-llama/llama-prompt-guard-2-22m"},
    {"id": "gemma4:latest"},          # never a real Groq id; must still be dropped
]}


class _FakeResponse:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def _stub_api(monkeypatch, payload=PAYLOAD, error=None):
    """Point llm_factory's models call at a fake API; returns the request list."""
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append(request)
        if error is not None:
            raise error
        return _FakeResponse(payload)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return calls


@pytest.fixture
def groq_env(monkeypatch):
    """Groq active, a key present, an empty model cache and a stubbed API."""
    monkeypatch.setenv("TOM_LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    for key in ("GROQ_MODEL", "GROQ_FAST_MODEL", "GROQ_CODE_MODEL"):
        monkeypatch.delenv(key, raising=False)
    llm_factory._GROQ_MODEL_CACHE.update({"when": 0.0, "names": []})
    return _stub_api(monkeypatch)


# ── Name shape ───────────────────────────────────────────────────────────────

def test_ollama_tags_are_never_groq_chat_models():
    # "<model>:<tag>" is Ollama's shape, which Groq has no concept of.
    assert not llm_factory.is_groq_chat_model("gemma4:latest")
    assert not llm_factory.is_groq_chat_model("nomic-embed-text:latest")
    assert not llm_factory.is_groq_chat_model("qwen2.5-coder:7b-instruct")


def test_groq_ids_are_accepted():
    assert llm_factory.is_groq_chat_model("openai/gpt-oss-120b")
    assert llm_factory.is_groq_chat_model("llama-3.3-70b-versatile")
    assert llm_factory.is_groq_chat_model("allam-2-7b")


def test_audio_and_guard_models_are_not_offered():
    assert not llm_factory.is_groq_chat_model("whisper-large-v3-turbo")
    assert not llm_factory.is_groq_chat_model("canopylabs/orpheus-v1-english")
    assert not llm_factory.is_groq_chat_model("playai-tts")
    assert not llm_factory.is_groq_chat_model("meta-llama/llama-prompt-guard-2-86m")


def test_blank_names_are_rejected():
    assert not llm_factory.is_groq_chat_model("")
    assert not llm_factory.is_groq_chat_model("   ")
    assert not llm_factory.is_groq_chat_model(None)


# ── Dropdown contents ────────────────────────────────────────────────────────

def test_dropdown_lists_account_models_without_ollama_tags(groq_env):
    models = llm_factory.groq_dropdown_models()
    # The configured/default model still leads the list.
    assert models[0] == llm_factory.groq_model("primary")
    assert "llama-3.3-70b-versatile" in models
    assert not [m for m in models if ":" in m]
    assert "whisper-large-v3" not in models
    assert "canopylabs/orpheus-v1-english" not in models


def test_dropdown_falls_back_to_configured_models_when_groq_is_unreachable(groq_env, monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    _stub_api(monkeypatch, error=OSError("network down"))
    assert llm_factory.groq_dropdown_models() == ["llama-3.3-70b-versatile"]


def test_dropdown_heals_a_groq_model_corrupted_with_an_ollama_tag(groq_env, monkeypatch):
    # What the old dropdown wrote into .env: an Ollama tag as GROQ_MODEL.
    monkeypatch.setenv("GROQ_MODEL", "gemma4:latest")
    models = llm_factory.groq_dropdown_models()
    assert "gemma4:latest" not in models
    assert models == [m for m in models if llm_factory.is_groq_chat_model(m)]
    assert not [m for m in models if ":" in m]


def test_configured_slots_are_listed_in_order_without_duplicates(monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-120b")
    monkeypatch.setenv("GROQ_FAST_MODEL", "openai/gpt-oss-20b")
    monkeypatch.setenv("GROQ_CODE_MODEL", "openai/gpt-oss-120b")
    assert llm_factory.groq_configured_models() == ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]


def test_configured_models_default_to_the_hosted_default(monkeypatch):
    for key in ("GROQ_MODEL", "GROQ_FAST_MODEL", "GROQ_CODE_MODEL"):
        monkeypatch.delenv(key, raising=False)
    assert llm_factory.groq_configured_models() == [llm_factory.DEFAULT_GROQ_MODEL]


# ── API call ─────────────────────────────────────────────────────────────────

def test_available_models_returns_nothing_without_a_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    calls = _stub_api(monkeypatch)
    assert llm_factory.groq_available_models() == []
    assert calls == []


def test_available_models_sends_a_user_agent_groq_accepts(groq_env):
    # Cloudflare in front of api.groq.com answers 403 to the literal default
    # urllib user-agent, which silently emptied the dropdown.
    llm_factory.groq_available_models()
    request = groq_env[0]
    assert request.get_header("User-agent") != "Python-urllib/3.11"
    assert request.get_header("Authorization") == "Bearer test-key"


def test_available_models_are_cached_between_calls(groq_env):
    llm_factory.groq_available_models()
    llm_factory.groq_available_models()
    assert len(groq_env) == 1


def test_available_models_survive_a_failing_api(groq_env, monkeypatch):
    _stub_api(monkeypatch, error=OSError("network down"))
    assert llm_factory.groq_available_models() == []


# ── Switch guard ─────────────────────────────────────────────────────────────

def test_switch_guard_allows_a_groq_model():
    assert llm_factory.groq_model_switch_rejection("openai/gpt-oss-120b") == ""


def test_switch_guard_refuses_an_ollama_tag():
    message = llm_factory.groq_model_switch_rejection("gemma4:latest")
    assert "gemma4:latest" in message
    assert "unchanged" in message
    assert "ollama" in message.lower()


def test_switch_guard_refuses_a_non_chat_model():
    assert llm_factory.groq_model_switch_rejection("whisper-large-v3") != ""


def test_switch_guard_refuses_an_empty_selection():
    assert llm_factory.groq_model_switch_rejection("") != ""
