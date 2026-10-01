"""Runtime provider switching (Groq ↔ Ollama) without a restart."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools import llm_factory


@pytest.fixture(autouse=True)
def _restore_env(monkeypatch):
    """Never leak a switched provider into other tests."""
    monkeypatch.setenv("TOM_LLM_PROVIDER", os.environ.get("TOM_LLM_PROVIDER", ""))
    yield


@pytest.fixture
def groq_ready(monkeypatch):
    monkeypatch.setenv("TOM_LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(llm_factory, "groq_model", lambda slot="primary": "groq-main")


@pytest.fixture
def ollama_ready(monkeypatch):
    monkeypatch.setenv("TOM_LLM_PROVIDER", "ollama")
    monkeypatch.setattr(llm_factory, "ollama_installed_models",
                        lambda: ["llama3.2:3b", "nomic-embed-text:latest"])


# ── llm_factory.set_provider ─────────────────────────────────────────────────

def test_set_provider_accepts_groq_and_ollama(monkeypatch):
    monkeypatch.delenv("TOM_LLM_PROVIDER", raising=False)
    assert llm_factory.set_provider("groq") == "groq"
    assert llm_factory.provider() == "groq"
    assert llm_factory.set_provider("ollama") == "ollama"
    assert llm_factory.provider() == "ollama"


def test_set_provider_accepts_local_aliases():
    for alias in ("local", "local-llm", "local_llm", "OLLAMA"):
        assert llm_factory.set_provider(alias) == "ollama"


def test_set_provider_rejects_unknown_names():
    with pytest.raises(ValueError):
        llm_factory.set_provider("openai")
    with pytest.raises(ValueError):
        llm_factory.set_provider("")


def test_set_provider_clears_model_caches(monkeypatch):
    llm_factory._GROQ_MODEL_CACHE.update({"when": 1.0, "names": ["stale"]})
    llm_factory._OLLAMA_MODEL_CACHE.update({"when": 1.0, "names": ["stale:latest"]})
    llm_factory.set_provider("ollama")
    assert llm_factory._GROQ_MODEL_CACHE["names"] == []
    assert llm_factory._OLLAMA_MODEL_CACHE["names"] == []


# ── llm_factory.ollama_dropdown_models ───────────────────────────────────────

def test_ollama_dropdown_excludes_embedding_models(ollama_ready):
    assert llm_factory.ollama_dropdown_models() == ["llama3.2:3b"]


def test_ollama_dropdown_falls_back_when_server_is_down(monkeypatch):
    monkeypatch.setenv("TOM_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "gemma4:latest")
    monkeypatch.setattr(llm_factory, "ollama_installed_models", lambda: [])
    assert llm_factory.ollama_dropdown_models() == ["gemma4:latest"]


# ── llm_factory.persist_provider ─────────────────────────────────────────────

def test_persist_provider_replaces_and_appends(tmp_path):
    env = tmp_path / ".env"
    env.write_text("TOM_LLM_PROVIDER=groq\nOTHER=1\n#TOM_LLM_PROVIDER=ollama\n",
                   encoding="utf-8")
    llm_factory.persist_provider("ollama", env_path=env)
    lines = env.read_text(encoding="utf-8").splitlines()
    assert lines.count("TOM_LLM_PROVIDER=ollama") == 1
    assert lines[0] == "TOM_LLM_PROVIDER=ollama"
    assert "OTHER=1" in lines
    assert "#TOM_LLM_PROVIDER=ollama" in lines  # comments are left alone


def test_persist_provider_appends_when_absent(tmp_path):
    env = tmp_path / ".env"
    env.write_text("OTHER=1", encoding="utf-8")
    llm_factory.persist_provider("groq", env_path=env)
    text = env.read_text(encoding="utf-8")
    assert "TOM_LLM_PROVIDER=groq" in text


def test_persist_provider_survives_a_missing_file(tmp_path):
    llm_factory.persist_provider("groq", env_path=tmp_path / "no" / "such" / ".env")


# ── TomAgent.switch_provider ─────────────────────────────────────────────────

def _bare_agent():
    """A TomAgent without __init__ — only the slots switch_provider touches."""
    import agent as agent_mod
    tom = agent_mod.TomAgent.__new__(agent_mod.TomAgent)

    def fake_make(model, max_tokens=4096):
        return ("llm", model, max_tokens)

    tom._make_llm = fake_make
    tom.model_name = "old"
    tom.fast_model_name = "old"
    tom.code_model_name = "old"
    tom.llm = tom.fast_llm = tom.chat_llm = tom.code_llm = None
    tom.llm_provider = "groq"

    class _Parser:
        def __init__(self, llm=None):
            self.llm = llm

    import tools.nlp_parser as nlp_mod
    original = nlp_mod.CommandParser
    nlp_mod.CommandParser = _Parser
    try:
        yield tom
    finally:
        nlp_mod.CommandParser = original


def test_switch_provider_to_ollama(groq_ready, monkeypatch):
    # Start on Groq, with a local Ollama that has llama3.2 pulled.
    monkeypatch.setattr(llm_factory, "ollama_installed_models",
                        lambda: ["llama3.2:3b", "nomic-embed-text:latest"])
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")
    monkeypatch.setattr(llm_factory, "persist_provider", lambda *a, **k: None)
    for tom in _bare_agent():
        result = tom.switch_provider("ollama")
    assert result == {"provider": "ollama", "model": "llama3.2:3b", "changed": True}
    assert tom.llm_provider == "ollama"
    assert tom.model_name == "llama3.2:3b"
    assert tom.llm == ("llm", "llama3.2:3b", 4096)
    assert tom.chat_llm == ("llm", "llama3.2:3b", 256)


def test_switch_provider_to_groq(ollama_ready, monkeypatch):
    # Start on Ollama (ollama_ready); a Groq key and model are configured.
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(llm_factory, "groq_model", lambda slot="primary": "groq-main")
    monkeypatch.setattr(llm_factory, "persist_provider", lambda *a, **k: None)
    for tom in _bare_agent():
        result = tom.switch_provider("groq")
    assert result == {"provider": "groq", "model": "groq-main", "changed": True}
    assert tom.llm_provider == "groq"


def test_switch_provider_keeps_running_when_groq_key_is_missing(ollama_ready, monkeypatch):
    # TOM_LLM_PROVIDER=ollama but no key: switching to Groq must fail WITHOUT
    # breaking the running local setup (provider env stays "ollama" ... after
    # rollback it is restored to the old value "ollama" — same thing here).
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")
    for tom in _bare_agent():
        with pytest.raises(RuntimeError) as err:
            tom.switch_provider("groq")
        assert "GROQ_API_KEY" in str(err.value)
        assert tom.llm_provider == "groq"  # attribute untouched by the rollback
        assert llm_factory.provider() == "ollama"  # env rolled back


def test_switch_provider_rolls_back_when_ollama_is_down(groq_ready, monkeypatch):
    monkeypatch.setattr(llm_factory, "ollama_installed_models", lambda: [])
    monkeypatch.setattr(llm_factory, "persist_provider", lambda *a, **k: None)
    for tom in _bare_agent():
        with pytest.raises(RuntimeError) as err:
            tom.switch_provider("ollama")
        assert "ollama serve" in str(err.value)
        assert llm_factory.provider() == "groq"


def test_switch_provider_to_the_same_provider_is_a_noop(groq_ready, monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", "groq-main")
    for tom in _bare_agent():
        result = tom.switch_provider("groq")
    assert result == {"provider": "groq", "model": "old", "changed": False}
