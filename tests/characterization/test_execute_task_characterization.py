"""R1 characterization tests — pin TOM's CURRENT observable behaviour.

These describe what TomAgent.execute_task() does today so the R2–R4 refactor
(TaskService facade, policy engine, durable task state) can prove it changed
nothing it did not mean to change (PRD supplement §S5 R1, TOM-MIG-002/008).

Gaps against the PRD are tracked with ``xfail(strict=True)``: they fail on purpose
until a phase delivers the requirement, then strict-xfail forces the marker off so
a gap can't be closed (or reopened) silently. The first three (task ids, blocked
status, secret redaction) were delivered by R2/R3 and are now ordinary tests.
"""
import asyncio
import ast
import os
import re
import tempfile
from pathlib import Path

import pytest

from tools.project_paths import PROJECT_ROOT

pytestmark = pytest.mark.characterization


def _safety_log(tom) -> str:
    path = Path(tom.safety.log_file)
    return path.read_text(encoding="utf-8") if path.exists() else ""


# ── Return contract ──────────────────────────────────────────────────────

@pytest.mark.parametrize("command", ["what can you do", "system status", "hello there"])
def test_normal_results_are_dicts_with_status_and_message(run, command):
    result = run(command)
    assert isinstance(result, dict)
    assert result.get("status") == "success", result
    assert isinstance(result.get("message"), str) and result["message"]


def test_chat_fallback_uses_the_llm_and_returns_its_text(tom, run):
    tom.llm_stub.reply = "Hi! What can I do for you?"
    result = run("hello there")
    assert result["response_type"] == "chat"
    assert result["message"] == "Hi! What can I do for you?"
    assert tom.llm_stub.calls == ["chat"]


# ── Deterministic meta commands (no model involved) ──────────────────────

@pytest.mark.parametrize("command,response_type", [
    ("what can you do", "capabilities"),
    ("system status", "health"),
])
def test_meta_commands_answer_without_any_llm_call(tom, run, command, response_type):
    tom.llm_stub.reply = AssertionError("meta commands must not reach the model")
    result = run(command)
    assert result["status"] == "success"
    assert result["response_type"] == response_type
    assert tom.llm_stub.calls == []


# ── Legacy keyword safety gate (SafetyGuards.is_action_safe) ─────────────

@pytest.mark.parametrize("command", [
    "transfer my bitcoin to this wallet now",
    "copy these files into C:\\Windows\\System32",
])
def test_hard_blocked_requests_stop_before_routing_or_approval(tom, run, command):
    result = run(command)
    # The raw gate dict is preserved (safe=False); R2 adds status="blocked" on top.
    assert result.get("safe") is False
    assert "blocked" in result["message"].lower()
    assert tom.approvals.asked == []
    assert tom.llm_stub.calls == []


def test_blocked_requests_are_written_to_the_audit_log(tom, run):
    run("transfer my bitcoin to this wallet now")
    assert "BLOCKED" in _safety_log(tom)


# ── Approval gate on a destructive action (AT-003 today) ─────────────────

def test_declined_delete_asks_once_and_leaves_the_file(tom, run):
    folder = tempfile.mkdtemp(prefix="tom_char_del_")
    target = os.path.join(folder, "notes.txt")
    Path(target).write_text("keep me", encoding="utf-8")

    tom.approvals.answer = False
    result = run(f"delete the file {target}")

    assert result["status"] == "cancelled", result
    assert os.path.exists(target)
    assert len(tom.approvals.asked) == 1
    assert tom.approvals.asked[0].action == "delete_path"
    assert target in tom.approvals.asked[0].summary


def test_deleting_inside_the_tom_install_is_refused_without_asking(tom, run):
    target = str(PROJECT_ROOT / "README.md")
    result = run(f"delete the file {target}")
    assert result["status"] == "blocked", result
    assert tom.approvals.asked == []
    assert (PROJECT_ROOT / "README.md").exists()


# ── Failure handling ─────────────────────────────────────────────────────

def test_a_failing_handler_becomes_an_error_result_not_an_exception(tom, run):
    tom.llm_stub.reply = RuntimeError("model exploded")
    result = run("hello there")
    assert result["status"] == "error"
    assert "model exploded" in result["message"]
    assert re.search(r"ERROR: \[FAILURE\] \| Target: hello there", _safety_log(tom))


def test_completion_is_logged_with_the_real_outcome(tom, run):
    run("hello there")
    assert re.search(r"COMPLETED: \[SUCCESS\] \| Target: hello there", _safety_log(tom))


def test_tasks_work_with_long_term_memory_switched_off(tom, run):
    assert tom.memory.available is False
    assert run("hello there")["status"] == "success"


# ── Interface parity seam (TOM-MIG-001) ──────────────────────────────────

def _calls_execute_task(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return any(isinstance(n, ast.Attribute) and n.attr == "execute_task" for n in ast.walk(tree))


@pytest.mark.parametrize("launcher", ["main.py", "tom_desktop_app.py"])
def test_cli_and_desktop_both_submit_through_execute_task(launcher):
    assert _calls_execute_task(PROJECT_ROOT / launcher)


def test_voice_action_requests_go_through_execute_task(tom, monkeypatch):
    seen = []

    async def fake_execute(command, interface=""):
        seen.append((command, interface))
        return {"status": "success", "message": "**Done.**"}
    monkeypatch.setattr(tom, "execute_task", fake_execute)

    result = asyncio.run(tom.generate_voice_response("create a word document about solar power"))
    assert seen == [("create a word document about solar power", "voice")]
    assert "**" not in result["message"]          # markdown stripped for speech


def test_voice_small_talk_is_a_task_too(tom, monkeypatch):
    """R10 / TOM-MIG-010: the CLI voice mode no longer has its own chat path that skipped the
    task service — small talk is a voice task like everything else (as push-to-talk already was)."""
    seen = []

    async def fake_execute(command, interface=""):
        seen.append((command, interface))
        return {"status": "success", "response_type": "chat", "message": "Doing *great*, thanks!"}
    monkeypatch.setattr(tom, "execute_task", fake_execute)

    result = asyncio.run(tom.generate_voice_response("how is your day going"))
    assert seen == [("how is your day going", "voice")]
    assert "*" not in result["message"]


# ── Former gap trackers, delivered (were strict xfail until R2/R3 landed) ─

def test_every_result_carries_a_task_id(tom, run):
    """FR-003 (R2): every request is a durable task with an id and a terminal state."""
    result = run("hello there")
    assert result.get("task_id") and result["task_state"] == "SUCCEEDED"
    rec = tom.tasks.get_task(result["task_id"])
    assert rec.state.value == "SUCCEEDED" and rec.text == "hello there"


def test_blocked_results_carry_a_status(tom, run):
    result = run("transfer my bitcoin to this wallet now")
    assert result.get("status") == "blocked" and result["task_state"] == "REJECTED"


def test_secrets_never_reach_the_audit_log(tom, run):
    """TOM-MIG-009 / AT-010 (R3 redaction): neither the audit log nor the task store keeps the key."""
    secret = "gsk_TESTSECRET0123456789abcdef"
    result = run(f"hello there, my groq key is {secret}")
    assert secret not in _safety_log(tom)
    assert secret not in tom.tasks.get_task(result["task_id"]).text
