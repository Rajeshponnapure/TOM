"""R4 durable execution: retry ceilings, checkpoints, pause/resume, resume-safe reconciliation (AT-006)."""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel  # noqa: E402

from tom_core.planning.planner import Executor, Plan, Step, restore_from_events  # noqa: E402
from tom_core.policy.engine import ActionClass  # noqa: E402
from tom_core.tools.registry import ToolRegistry, ToolSpec  # noqa: E402


class NoArgs(BaseModel):
    pass


def _registry(calls, flaky_failures=0, write_fails=False):
    reg = ToolRegistry()
    state = {"flaky": flaky_failures}

    def flaky():
        calls.append("read")
        if state["flaky"] > 0:
            state["flaky"] -= 1
            return {"status": "error", "error_class": "network", "message": "connection reset"}
        return {"status": "success", "output": {"text": "data"}, "message": "read ok"}

    def write():
        calls.append("write")
        if write_fails:
            return {"status": "error", "error_class": "network", "message": "lost"}
        return {"status": "success", "verified": True, "message": "written"}

    reg.register(ToolSpec("t.read", "read", NoArgs, flaky))
    reg.register(ToolSpec("t.write", "write", NoArgs, write, ActionClass.REVERSIBLE))
    return reg


def _run(executor, plan, **kw):
    return asyncio.run(executor.run(plan, **kw))


def test_transient_failures_of_read_only_steps_are_retried_within_the_ceiling():
    calls = []
    report = _run(Executor(_registry(calls, flaky_failures=2)), Plan("g", [Step(1, "t.read")]))
    assert report.status == "success" and calls == ["read"] * 3
    calls.clear()
    report = _run(Executor(_registry(calls, flaky_failures=5)), Plan("g", [Step(1, "t.read")]))
    assert report.status == "error" and calls == ["read"] * 3        # 1 try + 2 retries, then stop


def test_the_plan_wide_retry_budget_caps_retries_across_steps():
    calls = []
    plan = Plan("g", [Step(1, "t.read"), Step(2, "t.read")])
    _run(Executor(_registry(calls, flaky_failures=10), max_total_retries=1), plan)
    assert len(calls) == 3                                             # 2 tries + only 1 retry in total


def test_steps_that_change_things_are_never_retried():
    calls = []
    report = _run(Executor(_registry(calls, write_fails=True)), Plan("g", [Step(1, "t.write")]))
    assert report.status == "error" and calls == ["write"]


def test_every_step_is_checkpointed_and_an_interrupted_run_resumes_safely():
    calls, events = [], []
    ex = Executor(_registry(calls), checkpoint=lambda kind, data: events.append(
        {"kind": f"plan_{kind}", "message": json.dumps(data)}))
    plan = Plan("g", [Step(1, "t.read"), Step(2, "t.write", depends_on=[1]), Step(3, "t.read")])
    _run(ex, plan)
    assert [json.loads(e["message"]).get("state") for e in events if e["kind"] == "plan_step"] == \
        ["started", "succeeded", "started", "succeeded", "started", "succeeded"]

    # Simulate a crash after step 2 started: keep the plan, step 1 done, step 2 only "started".
    crashed = events[:4]
    restored, previous = restore_from_events(crashed)
    assert [s.id for s in restored.steps] == [1, 2, 3]
    calls.clear()
    report = _run(Executor(_registry(calls)), restored, previous=previous)
    states = [r.status for r in report.results]
    assert states == ["succeeded", "skipped", "succeeded"]
    assert calls == ["read"]                       # step 1 not repeated, step 2 (unknown outcome) not redone
    assert "outcome is unknown" in report.results[1].message


def test_pause_holds_the_next_step_until_resume():
    calls = []
    ex = Executor(_registry(calls))
    ex.pause()

    async def scenario():
        run = asyncio.create_task(ex.run(Plan("g", [Step(1, "t.read")])))
        await asyncio.sleep(0.5)
        assert calls == [] and ex.paused
        ex.resume()
        return await run

    report = asyncio.run(scenario())
    assert report.status == "success" and calls == ["read"]
