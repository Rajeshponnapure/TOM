"""Model-slot resolution and .env persistence (no Ollama server needed)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools import llm_factory

INSTALLED = ["qwen2.5-coder:latest", "nomic-embed-text:latest", "llama3.2:3b"]


@pytest.fixture
def ollama(monkeypatch):
    """Pretend Ollama is the provider and has INSTALLED models pulled."""
    monkeypatch.setenv("TOM_LLM_PROVIDER", "ollama")
    for key in ("OLLAMA_MODEL", "OLLAMA_FAST_MODEL", "OLLAMA_CODE_MODEL", "OLLAMA_EMBED_MODEL"):
        monkeypatch.delenv(key, raising=False)
    installed = list(INSTALLED)
    monkeypatch.setattr(llm_factory, "ollama_installed_models", lambda: list(installed))
    return installed


def test_primary_slot_reads_ollama_model(ollama, monkeypatch):
    # The primary slot is OLLAMA_MODEL, not OLLAMA_PRIMARY_MODEL.
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")
    assert llm_factory.resolve_model("primary") == "llama3.2:3b"


def test_installed_configured_model_is_kept(ollama, monkeypatch):
    monkeypatch.setenv("OLLAMA_FAST_MODEL", "qwen2.5-coder:latest")
    assert llm_factory.resolve_model("fast") == "qwen2.5-coder:latest"


def test_missing_model_falls_back_to_same_stem(ollama):
    # Default fast model qwen2.5-coder:7b-instruct is missing; another tag exists.
    assert llm_factory.resolve_model("fast") == "qwen2.5-coder:latest"


def test_chat_slot_never_falls_back_to_embedding_model(ollama):
    ollama[:] = ["nomic-embed-text:latest", "llama3.2:3b"]
    assert llm_factory.resolve_model("primary") == "llama3.2:3b"


def test_embed_slot_falls_back_to_embedding_model(ollama, monkeypatch):
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large:latest")
    assert llm_factory.resolve_model("embed") == "nomic-embed-text:latest"


def test_nothing_suitable_keeps_configured_name(ollama):
    ollama[:] = ["nomic-embed-text:latest"]
    assert llm_factory.resolve_model("primary") == "gemma4:latest"


def test_unreachable_server_keeps_configured_name(ollama):
    ollama[:] = []
    assert llm_factory.resolve_model("primary") == "gemma4:latest"
    assert llm_factory.resolve_model("unknown-slot") == "gemma4:latest"


def test_groq_provider_slots(monkeypatch):
    monkeypatch.setenv("TOM_LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_MODEL", "groq-main")
    monkeypatch.delenv("OLLAMA_EMBED_MODEL", raising=False)
    assert llm_factory.resolve_model("primary") == "groq-main"
    # Embeddings still come from Ollama, never a Groq chat model.
    assert llm_factory.resolve_model("embed") == "nomic-embed-text:latest"


def test_persist_model_env_replaces_and_appends(tmp_path):
    from agent import TomAgent
    env = tmp_path / ".env"
    env.write_text("OLLAMA_MODEL=old  # my note\nexport OLLAMA_FAST_MODEL=old\nOTHER=1", encoding="utf-8")
    TomAgent._persist_model_env("llama3.2:3b", "OLLAMA", env_path=env)
    lines = env.read_text(encoding="utf-8").splitlines()
    assert lines.count("OLLAMA_MODEL=llama3.2:3b") == 1
    assert lines.count("OLLAMA_FAST_MODEL=llama3.2:3b") == 1
    assert lines.count("OLLAMA_CODE_MODEL=llama3.2:3b") == 1
    assert "OTHER=1" in lines
    assert not any("old" in line for line in lines)


def test_persist_model_env_uses_provider_prefix(tmp_path):
    from agent import TomAgent
    env = tmp_path / ".env"  # does not exist yet
    TomAgent._persist_model_env("groq-main", "GROQ", env_path=env)
    text = env.read_text(encoding="utf-8")
    assert "GROQ_MODEL=groq-main" in text
    assert "OLLAMA_MODEL" not in text


def test_unreachable_llm_hint_names_the_fix(ollama, monkeypatch):
    # httpx reports a down Ollama as "All connection attempts failed", which
    # alone doesn't tell the user to start Ollama — the hint must.
    import agent
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        try:
            raise ConnectionRefusedError("[Errno 111] Connection refused")
        except ConnectionRefusedError as inner:
            raise RuntimeError("All connection attempts failed") from inner
    except RuntimeError as exc:
        hint = agent._llm_unreachable_hint(exc)
    assert "ollama serve" in hint and "localhost:11434" in hint

    monkeypatch.setenv("TOM_LLM_PROVIDER", "groq")
    assert "GROQ_API_KEY" in agent._llm_unreachable_hint(ConnectionError("x"))

    assert agent._llm_unreachable_hint(ValueError("bad json")) == ""
