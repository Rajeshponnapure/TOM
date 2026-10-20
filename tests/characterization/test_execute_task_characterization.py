"""R1 characterization tests — pin TOM's CURRENT observable behaviour.

These describe what TomAgent.execute_task() does today so the R2–R4 refactor
(TaskService facade, policy engine, durable task state) can prove it changed
nothing it did not mean to change (PRD supplement §S5 R1, TOM-MIG-002/008).

Tests marked ``xfail(strict=True)`` are the opposite: PRD requirements TOM does
NOT meet yet. They fail today on purpose. When a phase delivers the requirement,
the test starts passing, strict-xfail turns that into a failure, and the marker
must be removed — so a gap can't be closed (or reopened) silently.
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
    # Today a blocked result is the raw gate dict: it has no "status" key.
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

    async def fake_execute(command):
        seen.append(command)
        return {"status": "success", "message": "**Done.**"}
    monkeypatch.setattr(tom, "execute_task", fake_execute)

    result = asyncio.run(tom.generate_voice_response("create a word document about solar power"))
    assert seen == ["create a word document about solar power"]
    assert "**" not in result["message"]          # markdown stripped for speech


def test_voice_small_talk_goes_straight_to_the_model(tom, monkeypatch):
    async def fail_execute(command):
        raise AssertionError("small talk must not enter execute_task")
    monkeypatch.setattr(tom, "execute_task", fail_execute)
    tom.llm_stub.calls.clear()
    tom.llm_stub.reply = "Doing great, thanks!"

    result = asyncio.run(tom.generate_voice_response("how is your day going"))
    assert result["response_type"] == "voice_chat"
    assert tom.llm_stub.calls == ["voice"]


# ── Known gaps vs. the PRD (strict xfail: must flip when delivered) ──────

@pytest.mark.xfail(strict=True, reason="FR-003: tasks have no ID yet — delivered by R2 TaskService")
def test_every_result_carries_a_task_id(run):
    assert run("hello there").get("task_id")


@pytest.mark.xfail(strict=True, reason="Blocked results lack a 'status' key — fixed with the R2 result contract")
def test_blocked_results_carry_a_status(run):
    assert run("transfer my bitcoin to this wallet now").get("status") == "blocked"


@pytest.mark.xfail(strict=True, reason="TOM-MIG-009 / AT-010: audit log stores raw commands — R3 redaction")
def test_secrets_never_reach_the_audit_log(tom, run):
    secret = "gsk_TESTSECRET0123456789abcdef"
    run(f"hello there, my groq key is {secret}")
    assert secret not in _safety_log(tom)
