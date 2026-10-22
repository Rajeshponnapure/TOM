"""Autonomous (planner/executor) and Multi-Agent (specialists with tool grants) do real work.

Owner report 2026-10-21: Autonomous answered "list the 3 largest files" with instructions instead of
running anything; Multi-Agent sub-agents echoed "[CMO] Marketing assessment: <task>".
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tom_core.planning import Executor, Plan, Planner, Step, run_goal  # noqa: E402
from tom_core.tools.registry import get_registry  # noqa: E402


def _scripted(*replies):
    queue = list(replies)
    calls = []

    async def ask(system, user):
        calls.append((system, user))
        return queue.pop(0) if queue else "{}"
    ask.calls = calls
    return ask


def _plan(*steps, note=""):
    return json.dumps({"steps": list(steps), "note": note})


def test_the_planner_runs_real_tools_and_reports_the_output(tmp_path):
    (tmp_path / "big.bin").write_bytes(b"x" * 5000)
    (tmp_path / "small.txt").write_text("hi")
    ask = _scripted(_plan({"id": 1, "tool": "fs.largest_files", "args": {"path": str(tmp_path), "count": 1},
                           "why": "find the biggest file"}))
    report = asyncio.run(run_goal("show the largest file", ask, get_registry()))
    assert report.status == "success", report.text()
    assert "big.bin" in report.text()


def test_unknown_tools_are_dropped_not_described():
    ask = _scripted(_plan({"id": 1, "tool": "open_folder_and_look", "args": {}}), )
    report = asyncio.run(run_goal("do something", ask, get_registry()))
    assert report.results == [] and report.status == "needs_input"


def test_a_step_needing_a_failed_step_is_skipped_and_the_run_is_not_success(tmp_path):
    missing = str(tmp_path / "nope" / "missing.txt")
    plan = Plan("read then write", [
        Step(1, "fs.read_text", {"path": missing}),
        Step(2, "fs.write_text", {"path": str(tmp_path / "copy.txt"), "content": "{{1}}"}, depends_on=[1]),
    ])
    report = asyncio.run(Executor(get_registry()).run(plan))
    assert [r.status for r in report.results] == ["failed", "skipped"]
    assert report.status == "error"
    assert not (tmp_path / "copy.txt").exists()


def test_earlier_output_feeds_a_later_step(tmp_path, monkeypatch):
    monkeypatch.setenv("TOM_WORKSPACE_ROOTS", str(tmp_path))
    src = tmp_path / "a.txt"
    src.write_text("hello planner")
    out = tmp_path / "b.txt"
    plan = Plan("copy text", [
        Step(1, "fs.read_text", {"path": str(src)}),
        Step(2, "fs.write_text", {"path": str(out), "content": "{{1}}"}, depends_on=[1]),
    ])
    report = asyncio.run(Executor(get_registry()).run(plan))
    assert report.results[0].status == "succeeded", report.text()
    assert report.results[1].status in ("succeeded", "unverified"), report.text()
    assert "hello planner" in out.read_text()


def test_a_role_cannot_use_tools_outside_its_grant(tmp_path):
    ask = _scripted(_plan({"id": 1, "tool": "fs.delete", "args": {"path": str(tmp_path)}}))
    plan = asyncio.run(Planner(ask, get_registry(), allowed=["web.search"]).plan("delete it"))
    assert plan.steps == []                         # dropped at planning time
    out = asyncio.run(get_registry().call("fs.delete", {"path": str(tmp_path)}, allowed=["web.search"]))
    assert out["status"] != "success" and tmp_path.exists()   # and refused at call time


def test_autonomous_agent_uses_the_planner_and_is_honest_when_nothing_fits():
    from tools.autonomous_agent import AutonomousAgent

    class FakeLLM:
        async def ainvoke(self, messages):
            class R:
                content = json.dumps({"steps": [], "note": "No tool can play games."})
            return R()

    res = asyncio.run(AutonomousAgent(llm=FakeLLM()).execute("play minecraft for me"))
    assert res["status"] == "needs_input"
    assert "No tool can play games" in res["message"]
    assert res["verified"] is False


def test_multi_agent_coordinator_splits_work_and_specialists_answer_without_echoing():
    from tools.agent_orchestrator import AgentOrchestrator

    replies = [
        json.dumps({"assignments": [{"role": "cmo", "task": "write a launch tagline"},
                                    {"role": "cfo", "task": "estimate a $500 ad budget split"}]}),
        "Tagline: Ship faster with TOM.",     # thinking work: answered directly, no planning call
        "Split: $300 search, $200 social.",
    ]

    class FakeLLM:
        async def ainvoke(self, messages):
            class R:
                content = replies.pop(0)
            return R()

    orch = AgentOrchestrator(tom_agent=None, llm=FakeLLM())
    res = asyncio.run(orch.deploy_multi_agent_task("plan a small product launch"))
    assert res["status"] == "success"
    assert "Ship faster with TOM" in res["message"] and "$300 search" in res["message"]
    assert "Marketing Lead" in res["message"] and "Finance Lead" in res["message"]
    assert "assessment:" not in res["message"]
    assert replies == []
