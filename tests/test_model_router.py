"""Automatic model choice per kind of work (tom_core.resources.model_router) — injected sizes/admission,
no Ollama or GPU calls."""
import asyncio
from types import SimpleNamespace

import pytest

from tom_core.resources import model_router as mr

SIZES = {"llama3.2:3b": 1925, "qwen3.5:4b": 3236, "qwen3:8b": 4987, "qwen3.5:9b": 6287,
         "deepseek-r1:8b": 4987, "qwen2.5-coder:14b": 8571}


def fits(*ok):
    def admit(m):
        if m in ok:
            return SimpleNamespace(model=m, decision="gpu", num_ctx=4096, reason="fits")
        return SimpleNamespace(model="llama3.2:3b", decision="fallback_model", num_ctx=2048, reason="too big")
    return admit


@pytest.mark.parametrize("task,cat", [
    ("fix_tests", "code"), ("code_help", "code"), ("scaffold_tool", "code"), ("document_docx", "writing"),
    ("website", "writing"), ("email_draft_for_send", "writing"), ("analysis", "reasoning"),
    ("autonomous_plan", "reasoning"), ("specialist", "reasoning"), ("whatsapp_extract", "structured"),
    ("website_answers", "structured"), ("chat", "chat"), ("general", "chat")])
def test_task_labels_map_to_kinds_of_work(task, cat):
    assert mr.category(task) == cat


def test_heavy_work_gets_the_strong_model_and_chat_the_fast_one():
    admit = fits("llama3.2:3b", "qwen3.5:4b", "qwen3:8b", "qwen3.5:9b")
    assert mr.choose("fix_tests", "llama3.2:3b", sizes=SIZES, admit=admit).model == "qwen3.5:9b"
    assert mr.choose("document_pptx", "llama3.2:3b", sizes=SIZES, admit=admit).model == "qwen3.5:9b"
    assert mr.choose("chat", "llama3.2:3b", sizes=SIZES, admit=admit).model == "llama3.2:3b"


def test_a_model_that_does_not_fit_right_now_is_skipped():
    admit = fits("llama3.2:3b", "qwen3.5:4b", "qwen3:8b")          # e.g. a game is holding VRAM
    c = mr.choose("analysis", "llama3.2:3b", sizes=SIZES, admit=admit)
    assert c.model == "qwen3:8b" and "fits" in c.reason


def test_missing_models_and_nothing_fitting_fall_back_to_the_given_model():
    assert mr.choose("analysis", "llama3.2:3b", sizes={"llama3.2:3b": 1925}, admit=fits("llama3.2:3b")).model \
        == "llama3.2:3b"
    c = mr.choose("analysis", "my-model", sizes=SIZES, admit=fits())
    assert c.model == "my-model" and "no preferred model fits" in c.reason


def test_unsuitable_models_are_never_chosen():
    admit = fits(*SIZES)
    for task in ("fix_tests", "website", "analysis", "whatsapp_extract", "chat"):
        assert mr.choose(task, "x", sizes=SIZES, admit=admit).model not in ("deepseek-r1:8b", "qwen2.5-coder:14b")


def test_chat_reuses_a_capable_model_already_in_gpu_memory():
    admit = fits("llama3.2:3b", "qwen3.5:4b", "qwen3:8b")
    warm = mr.choose("chat", "llama3.2:3b", sizes=SIZES, admit=admit, loaded=lambda: {"qwen3:8b": 6000})
    cold = mr.choose("chat", "llama3.2:3b", sizes=SIZES, admit=admit, loaded=lambda: {})
    assert warm.model == "qwen3:8b" and cold.model == "llama3.2:3b"
    # heavy work is not "sticky": it still asks for its own model
    assert mr.choose("fix_tests", "x", sizes=SIZES, admit=fits(*SIZES), loaded=lambda: {"llama3.2:3b": 2000}).model \
        == "qwen3.5:9b"


def test_a_pinned_model_is_used_even_if_it_must_split(monkeypatch):
    monkeypatch.setenv("TOM_MODEL_CODE", "qwen2.5-coder:14b")
    c = mr.choose("fix_tests", "llama3.2:3b", sizes=SIZES, admit=fits("qwen3.5:9b"))
    assert c.model == "qwen2.5-coder:14b" and "pinned" in c.reason


def test_the_agent_swaps_the_model_for_the_task(monkeypatch):
    from langchain_ollama import ChatOllama
    from agent import TomAgent
    monkeypatch.setenv("TOM_MODEL_ROUTING", "1")
    monkeypatch.setattr(mr, "choose", lambda task, cur: mr.Choice(
        "qwen3.5:9b" if mr.category(task) != "chat" else cur, mr.category(task), 4096, "test"))
    a = TomAgent.__new__(TomAgent)
    base = ChatOllama(model="llama3.2:3b", format="json", temperature=0.3)
    routed = a._route_model(base, "fix_tests")
    assert routed.model == "qwen3.5:9b" and routed.format == "json" and routed.temperature == 0.3
    assert routed.reasoning is False and routed.num_ctx == 4096
    assert a._route_model(base, "fix_tests") is routed                          # reused, not rebuilt
    assert a._route_model(base, "chat") is base and a.last_routed_model == "llama3.2:3b"


def test_routing_off_or_non_ollama_models_are_left_alone(monkeypatch):
    from agent import TomAgent
    a = TomAgent.__new__(TomAgent)
    other = object()
    monkeypatch.setenv("TOM_MODEL_ROUTING", "1")
    assert a._route_model(other, "fix_tests") is other
    from langchain_ollama import ChatOllama
    monkeypatch.setenv("TOM_MODEL_ROUTING", "0")
    m = ChatOllama(model="llama3.2:3b")
    assert a._route_model(m, "fix_tests") is m
