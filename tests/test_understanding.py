"""Understand every message first (owner request 2026-10-21): action, target, content, conditions,
constraints and confirmations — instantly for clear requests, with the model only for unclear ones."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tom_core.understanding import analyze  # noqa: E402
from tools.nlp_parser import CommandParser  # noqa: E402

P = CommandParser(llm=None)


def u(text):
    return analyze(text, P.parse(text))


def test_conditions_and_confirmation_are_understood():
    x = u("open whatsapp and text mounish as hi if there are multiple people with the same name ask me which one")
    assert (x.action, x.target, x.content) == ("whatsapp_message", "mounish", "hi")
    assert x.ask_first and any(c.startswith("if there are multiple people") for c in x.conditions)


def test_constraints_are_kept():
    x = u("organise the pdfs only in my downloads folder and dont touch anything else")
    assert x.action == "file_operation"
    assert any("dont touch anything else" in c for c in x.constraints)


def test_missing_details_and_vague_references_are_not_confident():
    x = u("send a whatsapp message to mounish")
    assert not x.confident and x.missing == ["message_body"]
    assert not u("send it again").confident
    assert u("create a 10 slide presentation on climate change").confident


def test_clear_requests_skip_the_model_and_unclear_ones_use_it():
    calls = []

    class Model:
        async def ainvoke(self, messages):
            calls.append(messages[-1].content)

            class R:
                content = '{"intent": "file_operation", "subject": "files from yesterday"}'
            return R()

    p = CommandParser(llm=Model())
    clear = asyncio.run(p.parse_with_llm("send a whatsapp message to mounish saying hi"))
    assert calls == [] and clear["understanding"]["confident"]
    asyncio.run(p.parse_with_llm("can you sort out that thing with the files from yesterday please"))
    assert len(calls) == 1


def test_a_whatsapp_request_without_words_asks_instead_of_sending():
    import agent as agent_mod
    a = agent_mod.TomAgent.__new__(agent_mod.TomAgent)
    a.nlp_parser = P
    sent = []

    async def no_send(contact, message, confirm=False):
        sent.append((contact, message))
    a._send_whatsapp = no_send
    out = asyncio.run(a._execute_whatsapp("send a whatsapp message to mounish"))
    assert out["status"] == "needs_input" and "What should I say to mounish" in out["message"]
    assert sent == []
