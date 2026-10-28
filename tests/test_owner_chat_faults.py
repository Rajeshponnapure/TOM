"""Faults from the owner's live chat on 2026-10-21, pinned so they cannot come back.

    user: Instead of explaining me the instructions, can you actually play the Minecraft game?
    TOM:  Got it — I'll remember that. (Saved to long-term memory …)      ← a question stored as a rule
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import memory_rules  # noqa: E402


@pytest.mark.parametrize("text", [
    "Instead of explaining me the instructions, can you actually play the Minecraft game?",
    "Okay, so do you know how to play Minecraft?",
    "I'm not telling you something but I'm asking",
    "What's the plan today?",
    "Hey",
    "can you open chrome instead of edge",
    "Instead of a summary, could you give me the full report",
])
def test_questions_and_requests_are_never_stored_as_rules(text):
    assert not memory_rules.is_preference_statement(text)
    assert not memory_rules.is_pure_preference(text)


@pytest.mark.parametrize("text", [
    "always put PDFs in Invoices",
    "No — PDFs always go in Invoices, not Documents.",
    "From now on, can you keep emails short?",
    "Can you always reply in two sentences?",
    "remember that my manager is Priya",
    "I prefer short answers",
])
def test_real_preferences_are_still_recognised(text):
    assert memory_rules.is_preference_statement(text)


def _agent():
    from agent import TomAgent
    return TomAgent.__new__(TomAgent)


def _route(category="chat", handler="generate_chat_response"):
    return type("Route", (), {"category": category, "handler": handler})()


def _skill(confidence=0.9):
    from tools.skill_manager import SkillRoute
    return SkillRoute(matched=True, skill_name="27-game-dev-skills", confidence=confidence)


@pytest.mark.parametrize("text,expected", [
    # ability questions get an honest chat answer, never a skill that role-plays
    ("instead of explaining me the instructions, can you actually play the minecraft game?", False),
    ("do you know how to play minecraft?", False),
    ("could you play chess with me", False),
    # real skill requests still use the skill
    ("explain how a game loop works", True),
    ("can you explain how a game loop works", True),
    ("how do i make a platformer in pygame", True),
    ("design a level for a puzzle game", True),
])
def test_skill_route_is_not_used_for_ability_questions(text, expected):
    assert _agent()._should_use_skill_route(_route(), _skill(), text) is expected


def test_clarification_points_back_at_the_previous_message():
    from agent import TomAgent
    a = _agent()
    a.chat_memory = type("M", (), {"messages": [
        {"role": "user", "text": "can you actually play the Minecraft game?"},
        {"role": "assistant", "text": "Got it — I'll remember that."},
        {"role": "user", "text": "I'm not telling you something but I'm asking"}]})()
    assert TomAgent._CLARIFICATION.search("I'm not telling you something but I'm asking")
    assert TomAgent._CLARIFICATION.search("no, I meant the other file")
    assert a._previous_user_message() == "can you actually play the Minecraft game?"


def test_conversation_state_stops_repeat_greetings():
    import time as _t
    a = _agent()
    now = str(int(_t.time()))
    a.chat_memory = type("M", (), {"messages": [{"role": "user", "text": "hi", "ts": now},
                                                {"role": "assistant", "text": "Hi!", "ts": now},
                                                {"role": "user", "text": "do you know Minecraft?", "ts": now}]})()
    assert a._conversation_state().startswith("ongoing")
    a.chat_memory = type("M", (), {"messages": [{"role": "user", "text": "Hey", "ts": now}]})()
    assert a._conversation_state().startswith("new")


def test_live_facts_never_claim_unchecked_system_numbers():
    facts = _agent()._live_facts("Hey")
    assert "Now:" in facts and "NOT checked" in facts
    assert "CPU" not in facts and "RAM" not in facts


def test_is_question():
    assert memory_rules.is_question("Instead of explaining, can you play it?")
    assert memory_rules.is_question("do you know Minecraft")
    assert not memory_rules.is_question("always put PDFs in Invoices")
    assert not memory_rules.is_question("Can you always reply briefly?")      # a standing request
