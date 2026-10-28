"""R3 — policy engine, approval ledger, guard and typed tool registry (PRD AT-002/003/004, TOM-MIG-004)."""
import asyncio
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tom_core.policy.engine import ActionClass, PolicyEngine, ToolCall  # noqa: E402
from tom_core.tools import guard  # noqa: E402
from tom_core.tools.registry import ToolRegistry  # noqa: E402
from tools.approval import ApprovalLedger, ApprovalManager  # noqa: E402


@pytest.fixture
def ws(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    return root


@pytest.fixture
def policy(ws, tmp_path, monkeypatch):
    engine = PolicyEngine(workspace_roots=[str(ws)], protected_paths=[str(tmp_path / "protected")])
    monkeypatch.setattr("tom_core.policy.engine._POLICY", engine)
    return engine


class Approver(ApprovalManager):
    def __init__(self, answer=True):
        super().__init__()
        self.answer, self.asked = answer, []
        self.provider = lambda req: (self.asked.append(req), self.answer)[1]


@pytest.fixture
def approver(monkeypatch):
    a = Approver(True)
    monkeypatch.setattr(guard, "_approval_manager", a)
    return a


def run(coro):
    return asyncio.run(coro)


# ── policy engine ────────────────────────────────────────────────────────
def test_classes_map_to_the_approval_matrix(policy, ws):
    ev = lambda cls, paths=(): policy.evaluate(ToolCall("t", cls, paths=paths)).verdict  # noqa: E731
    assert ev(ActionClass.OBSERVE) == "allow"
    assert ev(ActionClass.REVERSIBLE) == "allow"
    assert ev(ActionClass.WORKSPACE_WRITE, [str(ws / "a.txt")]) == "allow"
    assert ev(ActionClass.MATERIAL_CHANGE) == "approve"
    assert ev(ActionClass.DESTRUCTIVE_OR_EXTERNAL) == "approve"
    assert ev(ActionClass.PRIVILEGED) == "approve"
    assert ev(ActionClass.BLOCKED) == "block"


def test_workspace_boundary_cannot_be_escaped(policy, ws, tmp_path):        # AT-004
    outside = policy.evaluate(ToolCall("fs.write_text", ActionClass.WORKSPACE_WRITE, paths=[str(tmp_path / "x.txt")]))
    traversal = policy.evaluate(ToolCall("fs.write_text", ActionClass.WORKSPACE_WRITE,
                                         paths=[str(ws / ".." / "x.txt")]))
    assert outside.verdict == "approve" and traversal.verdict == "approve"     # needs separate authorization
    protected = policy.evaluate(ToolCall("fs.write_text", ActionClass.WORKSPACE_WRITE,
                                         paths=[str(tmp_path / "protected" / "policy.py")]))
    assert protected.verdict == "block"


def test_privileged_actions_are_never_available_to_autonomous_runs(policy):
    assert policy.evaluate(ToolCall("x", ActionClass.PRIVILEGED, actor="autonomous")).verdict == "block"
    assert policy.evaluate(ToolCall("x", ActionClass.PRIVILEGED, actor="desktop")).verdict == "approve"


def test_emergency_stop_blocks_everything_but_observation(policy):
    policy.halt("test")
    assert policy.evaluate(ToolCall("x", ActionClass.REVERSIBLE)).verdict == "block"
    assert policy.evaluate(ToolCall("x", ActionClass.OBSERVE)).verdict == "allow"
    policy.resume()
    assert policy.evaluate(ToolCall("x", ActionClass.REVERSIBLE)).verdict == "allow"


# ── approval ledger: bound to the exact payload, used once, expires ──────
def test_ledger_grants_are_payload_bound_single_use_and_expire():
    ledger = ApprovalLedger(ttl=60)
    ledger.grant("whatsapp_message", {"to": "Ravi", "message": "On my way", "extra": "metadata"})
    assert ledger.consume("whatsapp_message", {"to": "Ravi", "message": "Running late"}) is None   # changed text
    assert ledger.consume("whatsapp_message", {"to": "ravi", "message": "On  my way"})            # same payload
    assert ledger.consume("whatsapp_message", {"to": "Ravi", "message": "On my way"}) is None      # used up
    expired = ApprovalLedger(ttl=-1)
    expired.grant("send_email", {"to": "a@b.c"})
    assert expired.consume("send_email", {"to": "a@b.c"}) is None


# ── guard: approval gate (AT-003) and audit ──────────────────────────────
def test_an_earlier_approval_of_the_same_payload_is_used_without_asking_twice(policy, approver):
    approver.request_approval(__import__("tools.approval", fromlist=["ApprovalRequest"]).ApprovalRequest(
        action="whatsapp_message", summary="Send", details={"to": "Ravi", "message": "hi"}))
    approver.asked.clear()
    out = guard.enforce("whatsapp.send", ActionClass.DESTRUCTIVE_OR_EXTERNAL,
                        payload={"to": "Ravi", "message": "hi"}, approval_action="whatsapp_message")
    assert out.allowed and out.approval_ref and approver.asked == []


def test_rejection_prevents_the_action(policy, monkeypatch):
    monkeypatch.setattr(guard, "_approval_manager", Approver(False))
    out = guard.enforce("fs.delete", ActionClass.DESTRUCTIVE_OR_EXTERNAL, payload={"path": "C:/x"})
    assert not out.allowed and out.refusal()["status"] == "cancelled"


def test_no_approval_channel_means_no_action(policy, monkeypatch):
    monkeypatch.setattr(guard, "_approval_manager", None)
    assert not guard.enforce("email.send", ActionClass.DESTRUCTIVE_OR_EXTERNAL, payload={"to": "a"}).allowed


def test_decisions_are_audited_with_secrets_redacted(policy, approver):
    guard.enforce("shell.run", ActionClass.MATERIAL_CHANGE,
                  payload={"command": "deploy --token sk-test-SECRET1234567890abcdef"})
    from tools.project_paths import project_path
    lines = project_path("tom_logs", "audit.jsonl").read_text(encoding="utf-8").strip().splitlines()
    last = json.loads(lines[-1])
    assert last["tool"] == "shell.run" and last["verdict"] == "allow"
    assert "SECRET1234567890" not in lines[-1]


# ── registry: schema validation (AT-002), policy, timeouts ───────────────
def test_invalid_arguments_are_rejected_before_anything_runs(policy, approver):
    from tom_core.tools.registry import get_registry
    reg = get_registry()
    out = run(reg.call("fs.largest_files", {"path": "C:/", "count": "lots"}))
    assert out["status"] == "error" and out["error_class"] == "invalid_args" and "count" in out["message"]
    assert run(reg.call("no.such.tool"))["error_class"] == "unknown_tool"
    assert run(reg.call("web.fetch", {"url": "file:///C:/Windows/win.ini"}))["error_class"] == "invalid_args"


def test_grants_restrict_a_role_to_its_tools(policy, approver):
    from tom_core.tools.registry import get_registry
    out = run(get_registry().call("fs.delete", {"path": "C:/x"}, allowed=["web.search"]))
    assert out["error_class"] == "not_granted"


def test_timeouts_are_enforced(policy, approver):
    import time
    from pydantic import BaseModel

    from tom_core.tools.registry import ToolSpec

    class NoArgs(BaseModel):
        pass
    reg = ToolRegistry()
    reg.register(ToolSpec("slow", "sleeps", NoArgs, lambda: time.sleep(2), timeout=0.2))
    assert run(reg.call("slow"))["error_class"] == "timeout"


# ── built-in tools do real work and prove it ─────────────────────────────
def test_filesystem_tools_inside_the_workspace(policy, approver, ws):
    from tom_core.tools.registry import get_registry
    reg = get_registry()
    w = run(reg.call("fs.write_text", {"path": str(ws / "notes" / "a.txt"), "content": "hello"}))
    assert w["status"] == "success" and w["verified"] is True and approver.asked == []
    again = run(reg.call("fs.write_text", {"path": str(ws / "notes" / "a.txt"), "content": "v2", "overwrite": True}))
    assert again["verified"] and os.path.isfile(again["backup"])                   # FR-012 recovery point
    (ws / "big.bin").write_bytes(b"x" * 5000)
    top = run(reg.call("fs.largest_files", {"path": str(ws), "count": 1}))
    assert top["output"][0]["path"].endswith("big.bin")
    listing = run(reg.call("fs.list_dir", {"path": str(ws)}))
    assert {e["name"] for e in listing["output"]} == {"notes", "big.bin"}
    read = run(reg.call("fs.read_text", {"path": str(ws / "notes" / "a.txt")}))
    assert read["output"] == {"text": "v2", "untrusted": True}


def test_writing_outside_the_workspace_asks_first(policy, approver, tmp_path):
    from tom_core.tools.registry import get_registry
    approver.answer = False
    out = run(get_registry().call("fs.write_text", {"path": str(tmp_path / "outside.txt"), "content": "x"}))
    assert out["status"] == "cancelled" and not (tmp_path / "outside.txt").exists()
    assert approver.asked and "outside the workspace" in approver.asked[0].summary


def test_read_only_shell_commands_run_and_others_need_approval(policy, approver):
    from tom_core.tools.builtin import ShellArgs, shell_class
    assert shell_class(ShellArgs(command="git status")) is ActionClass.OBSERVE
    assert shell_class(ShellArgs(command="pip install requests")) is ActionClass.MATERIAL_CHANGE
    assert shell_class(ShellArgs(command="git status && del /q *")) is ActionClass.MATERIAL_CHANGE
    approver.answer = False
    from tom_core.tools.registry import get_registry
    out = run(get_registry().call("shell.run", {"command": "pip install definitely-not-a-package"}))
    assert out["status"] == "cancelled"


def test_git_checkpoint_keeps_the_working_tree(policy, approver, tmp_path):
    import shutil
    import subprocess
    if not shutil.which("git"):
        pytest.skip("git not installed")
    repo = tmp_path / "repo"
    repo.mkdir()
    g = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True)  # noqa: E731
    g("init")
    g("config", "user.email", "t@t")
    g("config", "user.name", "t")
    (repo / "f.txt").write_text("one")
    g("add", ".")
    g("commit", "-m", "init")
    (repo / "f.txt").write_text("two (uncommitted)")
    from tom_core.tools.registry import get_registry
    out = run(get_registry().call("git.checkpoint", {"repo": str(repo), "label": "before edit"}))
    assert out["verified"] and (repo / "f.txt").read_text() == "two (uncommitted)"
    assert g("show", f"{out['output']['ref']}:f.txt").stdout == "two (uncommitted)"


def test_policy_parity_across_interfaces(policy, monkeypatch):                # TOM-MIG-004
    import tom_core.tasks.service as svc
    monkeypatch.setattr(guard, "_approval_manager", Approver(False))
    verdicts = set()
    for iface in ("desktop", "voice", "cli", "desktop-qt", "autonomous"):
        token = svc._current_interface.set(iface)
        try:
            verdicts.add(guard.enforce("fs.delete", ActionClass.DESTRUCTIVE_OR_EXTERNAL,
                                       payload={"path": "C:/x"}).decision.verdict)
        finally:
            svc._current_interface.reset(token)
    assert verdicts == {"block"}
