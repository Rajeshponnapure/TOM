"""PRD gap closures (2026-10-22): pause (FR-006), step metadata + plan preview (FR-004/015, C17),
diagnostics (C09/C04), project profiles (FR-016), task report export (FR-019), self-evaluation (C18)."""
import asyncio
import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tom_core.policy import get_policy  # noqa: E402
from tom_core.policy.engine import ActionClass  # noqa: E402


def test_pause_holds_every_new_action_until_resume_and_stop_releases_it():
    from tom_core.tools.guard import enforce
    done = []
    get_policy().pause()
    t = threading.Thread(target=lambda: done.append(enforce("app.open", ActionClass.REVERSIBLE).allowed))
    t.start()
    time.sleep(0.5)
    assert done == []                                    # waiting at the gate, not refused, not run
    get_policy().unpause()
    t.join(3)
    assert done == [True]

    get_policy().pause()
    t = threading.Thread(target=lambda: done.append(enforce("app.open", ActionClass.REVERSIBLE).allowed))
    t.start()
    time.sleep(0.3)
    get_policy().halt("test")                            # emergency stop while paused: the call is refused
    t.join(3)
    assert done[-1] is False


def test_steps_carry_risk_timeout_verification_and_affected_paths(tmp_path):
    from tom_core.planning.planner import Planner, changes_things, preflight
    from tom_core.tools.registry import get_registry

    async def ask(system, user):
        return json.dumps({"steps": [
            {"id": 1, "tool": "fs_make_dir", "args": {"path": str(tmp_path / "out")}},
            {"id": 2, "tool": "fs_write_text", "args": {"path": str(tmp_path / "out" / "a.txt"), "content": "x"}}]})

    plan = asyncio.run(Planner(ask, get_registry()).plan("make a folder and a file"))
    s1, s2 = plan.steps
    assert (s1.risk, s2.risk) == ("WORKSPACE_WRITE", "WORKSPACE_WRITE")
    assert s2.timeout > 0 and "unverified" in s2.verify and str(tmp_path / "out" / "a.txt") in s2.touches
    text = preflight(plan)
    assert "affects:" in text and "Rollback" in text and changes_things(plan)


def test_a_multi_step_change_is_shown_and_confirmed_once_before_it_starts(tmp_path):
    from tom_core.tools import guard
    from tools.autonomous_agent import AutonomousAgent

    class Planned:
        async def ainvoke(self, messages):
            class R:
                content = json.dumps({"steps": [
                    {"id": 1, "tool": "fs_make_dir", "args": {"path": str(tmp_path / "x")}},
                    {"id": 2, "tool": "fs_make_dir", "args": {"path": str(tmp_path / "y")}}]})
            return R()

    class Deny:
        ledger = None
        asked = []

        def request_approval(self, req, prompt_fn=None):
            self.asked.append(req.action)
            return False

    deny = Deny()
    old = guard._approval_manager
    guard.set_approval_manager(deny)
    try:
        res = asyncio.run(AutonomousAgent(llm=Planned()).execute("make two folders"))
    finally:
        guard.set_approval_manager(old)
    assert deny.asked == ["run_plan"] and res["status"] == "cancelled"
    assert not (tmp_path / "x").exists() and "Plan:" in res["message"]


def _agent():
    import agent as agent_mod
    return agent_mod.TomAgent.__new__(agent_mod.TomAgent)


def test_diagnostics_and_duplicates_by_plain_words(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"z" * 40_000)
    (tmp_path / "copy of a.bin").write_bytes(b"z" * 40_000)
    (tmp_path / "other.bin").write_bytes(b"q" * 40_000)
    a = _agent()
    dup = asyncio.run(a._advanced_command(f"find duplicate files in {tmp_path}"))
    assert dup["status"] == "success" and "1 group" in dup["message"] and "copy of a.bin" in dup["message"]
    dns = asyncio.run(a._advanced_command("resolve localhost"))
    assert dns["status"] == "success" and "127.0.0.1" in dns["message"]


def test_project_profiles_detect_test_commands_and_resolve_by_name(tmp_path):
    from tom_core import projects
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    a = _agent()
    saved = asyncio.run(a._advanced_command(f"add project demo app at {tmp_path}"))
    assert saved["status"] == "success" and "python -m pytest -q" in saved["message"]
    assert projects.get("demo app")["root"] == str(tmp_path)
    assert projects.get(str(tmp_path / "src"))["name"] == "demo app"          # a path inside the project
    custom = asyncio.run(a._advanced_command(f"add project other at {tmp_path} with tests: pytest -x"))
    assert "pytest -x" in custom["message"]
    assert "demo app" in asyncio.run(a._advanced_command("list projects"))["message"]


def test_task_report_export_and_self_evaluation(tmp_path):
    from tom_core.tasks.models import TaskState
    from tom_core.tasks.store import TaskStore

    class Tasks:
        store = TaskStore(str(tmp_path / "t.sqlite3"))

    rec = Tasks.store.create("summarize my inbox with key gsk_TESTSECRET0123456789abcdef", "desktop")
    Tasks.store.transition(rec.id, TaskState.RUNNING)
    Tasks.store.transition(rec.id, TaskState.FAILED, error="Model timeout while running chat after 60s.")
    ok = Tasks.store.create("open notepad", "voice")
    Tasks.store.transition(ok.id, TaskState.RUNNING)
    Tasks.store.transition(ok.id, TaskState.SUCCEEDED, outcome="Opened Notepad")
    a = _agent()
    a.tasks = Tasks()
    out = a._export_task_report(rec.id)
    assert out["status"] == "success"
    text = open(out["path"], encoding="utf-8").read()
    assert "# TOM task report" in text and "gsk_TESTSECRET" not in text and "Model timeout" in text
    ev = asyncio.run(a._advanced_command("self evaluation"))
    assert "50% verified successes" in ev["message"] and "model timeout or unavailable (1)" in ev["message"]
    assert "Ollama" in ev["message"]                                           # a proposal, not an automatic change
