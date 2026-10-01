"""Knowledge acquisition: "learn about X" researches the topic and saves a
curated note into the knowledge base, which then becomes usable. It must never
download-and-run code; this only writes a markdown note.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import agent as agent_mod
from agent import TomAgent


# ── pure helpers ─────────────────────────────────────────────────────────────

def test_is_learn_request():
    assert TomAgent._is_learn_request("learn about quantum computing")
    assert TomAgent._is_learn_request("teach yourself about rust borrow checking")
    assert TomAgent._is_learn_request("update your knowledge on llm agents")
    assert not TomAgent._is_learn_request("build me a website")
    assert not TomAgent._is_learn_request("delete the old folder")


@pytest.mark.parametrize("cmd,topic", [
    ("learn about quantum computing", "quantum computing"),
    ("teach yourself about the rust borrow checker", "the rust borrow checker"),
    ("research and remember kubernetes operators", "kubernetes operators"),
    ("add knowledge about GraphQL federation", "GraphQL federation"),
])
def test_learn_topic_extraction(cmd, topic):
    assert TomAgent._learn_topic(cmd).lower() == topic.lower()


# ── acquisition writes a note and reloads the engine ─────────────────────────

def test_acquire_knowledge_saves_a_note(tmp_path, monkeypatch):
    kdir = tmp_path / "knowledge"
    kdir.mkdir()
    # Redirect where the note is written, and stub the engine reload + research.
    monkeypatch.setattr(agent_mod, "project_path_str",
                        lambda *parts: str(tmp_path.joinpath(*parts)))
    import tools.knowledge_engine as ke
    monkeypatch.setattr(ke, "get_engine", lambda: object())

    tom = TomAgent.__new__(TomAgent)
    tom.rag = None

    async def _fake_research(topic):
        return f"Key facts about {topic}: it is well documented and testable."
    tom._research_topic = _fake_research

    res = asyncio.run(tom.acquire_knowledge("widget theory"))
    assert res["status"] == "success"
    note = kdir / "acquired_widget-theory.md"
    assert note.is_file()
    body = note.read_text(encoding="utf-8")
    assert "# Widget Theory" in body
    assert "Key facts about widget theory" in body


def test_acquire_knowledge_needs_a_topic():
    tom = TomAgent.__new__(TomAgent)
    res = asyncio.run(tom.acquire_knowledge("   "))
    assert res["status"] == "needs_input"


def test_acquire_knowledge_reports_research_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_mod, "project_path_str",
                        lambda *parts: str(tmp_path.joinpath(*parts)))
    tom = TomAgent.__new__(TomAgent)
    tom.rag = None

    async def _failed(topic):
        return "Could not research 'x'. Please check internet connection."
    tom._research_topic = _failed

    res = asyncio.run(tom.acquire_knowledge("obscure topic"))
    assert res["status"] == "error"
