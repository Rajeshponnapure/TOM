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


def test_provider_defaults_to_hosted_groq_when_a_key_is_configured(monkeypatch):
    """A configured Groq key means Groq, even with TOM_LLM_PROVIDER unset."""
    monkeypatch.delenv("TOM_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    assert llm_factory.provider() == "groq"
    assert llm_factory.resolve_model("primary") == llm_factory.groq_model("primary")


def test_local_provider_requires_an_explicit_opt_in(monkeypatch):
    """TOM never drifts back to local while a Groq key is present."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    for value in ("ollama", "OLLAMA", "local", "local-llm"):
        monkeypatch.setenv("TOM_LLM_PROVIDER", value)
        assert llm_factory.provider() == "ollama"
    monkeypatch.setenv("TOM_LLM_PROVIDER", "groq")
    assert llm_factory.provider() == "groq"


def test_provider_without_a_groq_key_stays_local(monkeypatch):
    monkeypatch.delenv("TOM_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert llm_factory.provider() == "ollama"


def test_a_shell_variable_that_overrides_env_is_reported(monkeypatch):
    """An exported value still wins (tests rely on it) — it just isn't silent."""
    monkeypatch.setattr(llm_factory, "_env_file_value", lambda key: "groq")
    monkeypatch.setenv("TOM_LLM_PROVIDER", "ollama")
    message = llm_factory.provider_env_conflict()
    assert "TOM_LLM_PROVIDER=ollama" in message
    assert ".env (groq)" in message
    assert "Ollama" in message                      # names what it is actually running

    monkeypatch.setenv("TOM_LLM_PROVIDER", "groq")  # agrees with .env → nothing to say
    assert llm_factory.provider_env_conflict() == ""

    monkeypatch.delenv("TOM_LLM_PROVIDER", raising=False)
    assert llm_factory.provider_env_conflict() == ""


def test_hosted_vision_model_is_opt_in(monkeypatch):
    monkeypatch.delenv("GROQ_VISION_MODEL", raising=False)
    assert llm_factory.groq_vision_model() == ""
    monkeypatch.setenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
    assert llm_factory.groq_vision_model() == "meta-llama/llama-4-scout-17b-16e-instruct"


def test_hosted_provider_uses_ocr_instead_of_a_local_vision_model(monkeypatch):
    """On Groq with no vision model, TOM must explain and use OCR — never Ollama."""
    import asyncio
    import agent as agent_mod
    monkeypatch.setenv("TOM_LLM_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_VISION_MODEL", raising=False)
    seen = {}

    async def fake_ocr(self, image_path, user_question, note=""):
        seen["note"] = note
        return {"status": "success", "message": "from OCR",
                "response_type": "image_analysis_ocr"}

    monkeypatch.setattr(agent_mod.TomAgent, "_analyze_image_with_ocr", fake_ocr)
    tom = agent_mod.TomAgent.__new__(agent_mod.TomAgent)
    result = asyncio.run(
        agent_mod.TomAgent._analyze_image_with_vision(tom, "screen.png", "what is this?"))
    assert result["response_type"] == "image_analysis_ocr"
    assert "GROQ_VISION_MODEL" in seen["note"]
    assert "TOM_LLM_PROVIDER=ollama" in seen["note"]   # how to switch to local on purpose


def test_groq_provider_slots(monkeypatch):
    monkeypatch.setenv("TOM_LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_MODEL", "groq-main")
    monkeypatch.delenv("OLLAMA_EMBED_MODEL", raising=False)
    assert llm_factory.resolve_model("primary") == "groq-main"
    # Embeddings still come from the local encoder, never a Groq chat model
    # (Groq has no embeddings endpoint) — that is not a chat fallback.
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
