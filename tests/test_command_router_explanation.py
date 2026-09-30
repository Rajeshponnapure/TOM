"""_is_explanation_request() routes "explain how X works" questions to TOM's own
explanation feature -- but the original flat pattern list was both too broad and
too narrow at once, found by physically routing real questions:

  * Too broad: "what is"/"how do" are common in totally unrelated questions.
    "what is the weather in Paris" and "how do I get to the airport" were both
    hijacked into "explain how TOM works" instead of their real handler.
  * Too narrow: any action verb anywhere in the sentence disabled explanation
    detection entirely, even when the sentence unambiguously asks for an
    explanation. "explain how to send an email" was routed to actually SEND
    an email instead of explaining the feature.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools.command_router import CommandRouter


@pytest.fixture
def router():
    return CommandRouter()


@pytest.mark.parametrize("command", [
    "explain how the memory system works",
    "how does hindsight memory work",
    "what is RAG memory",
    "explain how to send an email",
    "explain how to create a word document",
    "how does the autonomous agent work",
    "describe how the orchestrator delegates tasks",
])
def test_genuine_explanation_requests_are_detected(router, command):
    route = router.route(command)
    assert route.handler == "explain_how_it_works", (command, route)


@pytest.mark.parametrize("command", [
    "what is the weather in Paris",
    "what is the weather today",
    "what are the ingredients for pasta",
    "how do i get to the airport",
    "what is a REST API",
])
def test_unrelated_questions_are_never_hijacked_into_self_explanation(router, command):
    route = router.route(command)
    assert route.handler != "explain_how_it_works", (command, route)


@pytest.mark.parametrize("command", [
    "send an email to john explaining the project",
    "create an excel spreadsheet about sales",
])
def test_real_actions_still_execute_not_explain(router, command):
    route = router.route(command)
    assert route.handler != "explain_how_it_works", (command, route)
