"""Shared fixture for the R1 characterization suite.

One real TomAgent per module (construction costs ~3 s), with every outside
dependency replaced so the tests are fast, offline and deterministic:

  * no LLM      — understand_command uses the regex parser, _invoke_llm is scripted
  * no Hindsight — HINDSIGHT_ENABLED=0
  * no user data — chat memory, experience log, RAG, evolution and telemetry are
                   redirected or switched off, and the CWD (which decides where
                   safety_log.txt goes) is a temp directory
  * approvals    — answered by a test-controlled provider, never the console
"""
import asyncio
import os
import sys
import tempfile
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class Approvals:
    """Records every approval request and answers with ``self.answer``."""

    def __init__(self):
        self.asked = []
        self.answer = False

    def __call__(self, request):
        self.asked.append(request)
        return self.answer


class ScriptedLLM:
    """Stands in for TomAgent._invoke_llm; ``reply`` may be a str or an exception."""

    def __init__(self):
        self.calls = []
        self.reply = "Hello! I'm TOM."

    async def __call__(self, chain, payload, task_name, llm=None):
        self.calls.append(task_name)
        if isinstance(self.reply, BaseException):
            raise self.reply
        return SimpleNamespace(content=self.reply)


@pytest.fixture(scope="module")
def tom():
    workdir = tempfile.mkdtemp(prefix="tom_char_")
    mp = pytest.MonkeyPatch()
    mp.chdir(workdir)
    mp.setenv("TOM_LLM_PROVIDER", "ollama")
    mp.setenv("HINDSIGHT_ENABLED", "0")
    mp.setenv("TOM_WORKSPACE_DIR", os.path.join(workdir, "workspace"))
    try:
        from agent import TomAgent
        from tools.chat_memory import ChatMemory

        agent = TomAgent()
        agent.chat_memory = ChatMemory(file_path=os.path.join(workdir, "chat_memory.json"))
        agent.rag = None
        agent.evolution = None
        agent.skill_telemetry = None
        mp.setattr(agent.file_tools, "open_file", lambda path: None)  # never launch Word/Excel
        experiences = []
        mp.setattr(agent.learner, "log_experience",
                   lambda cmd, outcome, data: experiences.append(cmd) or {"id": len(experiences)})

        async def regex_parse(command):
            return agent.nlp_parser.parse(command)
        mp.setattr(agent, "understand_command", regex_parse)

        agent.llm_stub = ScriptedLLM()
        mp.setattr(agent, "_invoke_llm", agent.llm_stub)
        agent.approvals = Approvals()
        agent.approval_manager.provider = agent.approvals
        agent.workdir = workdir
        yield agent
    finally:
        mp.undo()


@pytest.fixture
def run(tom):
    """Reset per-test state, then return a sync runner for execute_task."""
    tom.approvals.asked.clear()
    tom.approvals.answer = False
    tom.llm_stub.calls.clear()
    tom.llm_stub.reply = "Hello! I'm TOM."

    def _run(command):
        return asyncio.run(tom.execute_task(command))
    return _run
