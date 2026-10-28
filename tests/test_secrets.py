"""Credential store: ask for a key, save it to .env + env, and never leak the value."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tom_core import secrets
from tom_core.observability.redact import redact


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    monkeypatch.setenv("TOM_ENV_FILE", str(f))
    # start clean: no provider keys set
    for v in ("OPENAI_API_KEY", "GROQ_API_KEY", "STABILITY_API_KEY"):
        monkeypatch.delenv(v, raising=False)
    return f


def test_resolve_handles_aliases_and_env_var_names():
    assert secrets.resolve("chatgpt").name == "openai"
    assert secrets.resolve("Claude").name == "anthropic"
    assert secrets.resolve("OPENAI_API_KEY").name == "openai"
    assert secrets.resolve("nonsense") is None


def test_free_service_needs_no_key(env_file):
    r = secrets.ensure("polyhaven")
    assert r["status"] == "success" and r["free"] is True


def test_ensure_asks_when_missing(env_file):
    r = secrets.ensure("openai")
    assert r["status"] == "needs_key" and r["env_var"] == "OPENAI_API_KEY"
    assert "api key" in r["message"].lower() and "platform.openai.com" in r["message"]


def test_save_then_ensure_succeeds_and_persists(env_file, monkeypatch):
    out = secrets.save("OPENAI_API_KEY", "sk-test-ABC123456789")
    assert out["status"] == "success"
    assert os.environ["OPENAI_API_KEY"] == "sk-test-ABC123456789"      # live in this process
    assert "OPENAI_API_KEY=sk-test-ABC123456789" in env_file.read_text()  # written to .env
    r = secrets.ensure("openai")
    assert r["status"] == "success" and r["key"] == "sk-test-ABC123456789"


def test_save_updates_existing_line_not_duplicate(env_file):
    secrets.save("GROQ_API_KEY", "gsk_first_value_1234")
    secrets.save("GROQ_API_KEY", "gsk_second_value_5678")
    text = env_file.read_text()
    assert text.count("GROQ_API_KEY=") == 1 and "gsk_second_value_5678" in text


def test_saved_key_is_redacted_in_logs(env_file):
    secrets.save("STABILITY_API_KEY", "sk-stability-SECRETVALUE999")
    # a log line that happens to contain the key must come out masked
    assert "sk-stability-SECRETVALUE999" not in redact("flashing with key sk-stability-SECRETVALUE999")


def test_rejects_bad_var_name(env_file):
    assert secrets.save("not a var", "value123456789")["status"] == "error"
    assert secrets.save("OK_VAR", "")["status"] == "error"


def test_status_report_lists_but_never_shows_values(env_file):
    secrets.save("OPENAI_API_KEY", "sk-visible-TESTKEY-000")
    rep = secrets.status_report()
    assert "OpenAI" in rep["message"] and "sk-visible-TESTKEY-000" not in rep["message"]
    assert "Poly Haven" in rep["message"]        # a free service is listed as needing no key


def test_looks_like_key():
    assert secrets.looks_like_key("sk-abc123DEF456ghi")
    assert not secrets.looks_like_key("yes please save it")
    assert not secrets.looks_like_key("short")


# ── agent wiring: the set-command, and the ask -> save -> retry flow ──────
def test_agent_set_key_command_and_retry(env_file, monkeypatch):
    import asyncio
    import agent as agent_mod
    t = object.__new__(agent_mod.TomAgent)

    # "set my openai key to sk-..." stores it
    r = asyncio.run(agent_mod.TomAgent._secrets_command(t, "set my openai key to sk-demoKEY-12345678"))
    assert r["status"] == "success" and os.environ["OPENAI_API_KEY"] == "sk-demoKEY-12345678"

    # _require_key returns None (go ahead) once the key is present
    assert t._require_key("openai", "do the thing") is None

    # when missing, it records a pending retry and returns a prompt
    monkeypatch.delenv("STABILITY_API_KEY", raising=False)
    prompt = t._require_key("stability", "make an image of a cat")
    assert prompt["status"] == "needs_key"
    assert t._pending_key["command"] == "make an image of a cat"

    # the owner pastes the key -> saved, original command re-run
    ran = {}
    async def fake_exec(cmd):
        ran["cmd"] = cmd
        return {"status": "success", "message": "image made"}
    monkeypatch.setattr(t, "execute_task", fake_exec, raising=False)
    out = asyncio.run(agent_mod.TomAgent._answer_pending_key(t, "sk-stability-KEYVALUE-9999"))
    assert os.environ["STABILITY_API_KEY"] == "sk-stability-KEYVALUE-9999"
    assert ran["cmd"] == "make an image of a cat" and "image made" in out["message"]


def test_agent_pending_key_cancel(env_file, monkeypatch):
    import asyncio
    import agent as agent_mod
    t = object.__new__(agent_mod.TomAgent)
    t._pending_key = {"service": "openai", "env_var": "OPENAI_API_KEY",
                      "command": "x", "at": __import__("time").time()}
    out = asyncio.run(agent_mod.TomAgent._answer_pending_key(t, "cancel"))
    assert out["status"] == "cancelled" and t._pending_key is None
