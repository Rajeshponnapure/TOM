"""TaskService / TaskStore (R2 + R4 basics) and secret redaction (R3 piece).

Maps to PRD acceptance tests: AT-001 lifecycle, AT-005 cancellation, AT-006 recovery,
AT-007 verification honesty, AT-010 redaction, AT-012 cross-interface state, TOM-MIG-007 rollback.
"""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tom_core.observability.redact import MASK, redact  # noqa: E402
from tom_core.tasks import TaskService, TaskState, open_store  # noqa: E402
from tom_core.tasks.service import classify  # noqa: E402
from tom_core.tasks.store import InvalidTransition, TaskStore  # noqa: E402


@pytest.fixture
def db(tmp_path):
    return str(tmp_path / "tasks.sqlite3")


# ── verification honesty (FR-008 / AT-007) ───────────────────────────────

@pytest.mark.parametrize("result,state", [
    ({"status": "success", "response_type": "chat", "message": "hi"}, TaskState.SUCCEEDED),
    ({"status": "success", "response_type": "word_doc", "message": "Created report.docx"}, TaskState.UNVERIFIED),
    ({"status": "success", "verified": True, "message": "tests pass"}, TaskState.SUCCEEDED),
    ({"status": "error", "message": "boom"}, TaskState.FAILED),
    ({"status": "unsupported", "message": "no executor"}, TaskState.FAILED),
    ({"status": "cancelled", "message": "Action cancelled by user."}, TaskState.REJECTED),
    ({"safe": False, "message": "Action blocked"}, TaskState.REJECTED),
    ({"status": "needs_input", "message": "Which file?"}, TaskState.NEEDS_INPUT),
    ("plain string", TaskState.UNVERIFIED),
])
def test_success_is_only_claimed_with_evidence(result, state):
    assert classify(result)[0] is state


# ── store ────────────────────────────────────────────────────────────────

def test_lifecycle_is_persisted_with_events(db):
    store = TaskStore(db)
    rec = store.create("make a report", "cli")
    store.transition(rec.id, TaskState.RUNNING)
    store.transition(rec.id, TaskState.UNVERIFIED, note="no evidence", outcome="Created report.docx")
    again = TaskStore(db).get(rec.id)                                   # a fresh connection sees it
    assert again.state is TaskState.UNVERIFIED and again.outcome == "Created report.docx"
    assert [e["message"].split(":")[0] for e in again.events] == ["CREATED", "RUNNING", "UNVERIFIED"]
    with pytest.raises(InvalidTransition):
        store.transition(rec.id, TaskState.RUNNING)                     # terminal states stay terminal


def test_task_text_and_outcome_are_redacted_before_storage(db):
    store = TaskStore(db)
    rec = store.create("email it, password=Hunter2pass! and key gsk_abcdefghijklmnopqrstuv", "desktop")
    store.transition(rec.id, TaskState.RUNNING)
    store.transition(rec.id, TaskState.FAILED, error="auth failed for sk-ant-api03-ZZZZZZZZZZZZZZZZZZZZ")
    saved = store.get(rec.id)
    blob = saved.text + saved.error + str(saved.events)
    assert "Hunter2pass!" not in blob and "gsk_abcdefghijklmnop" not in blob and "sk-ant-api03" not in blob


def test_restart_marks_orphaned_tasks_blocked_and_never_replays(db):
    store = TaskStore(db)
    mine = store.create("still mine", "cli")
    store.transition(mine.id, TaskState.RUNNING)
    orphan = store.create("send the newsletter", "desktop")
    store.transition(orphan.id, TaskState.RUNNING)
    store._db.execute("UPDATE tasks SET owner_pid=? WHERE id=?", (2_000_000_000, orphan.id))
    store._db.commit()

    assert TaskStore(db).recover_interrupted() == [orphan.id]
    rec = store.get(orphan.id)
    assert rec.state is TaskState.BLOCKED and "Not replayed" in rec.error
    assert store.get(mine.id).state is TaskState.RUNNING                # a live owner is left alone


def test_in_memory_store_when_persistence_is_switched_off(monkeypatch):
    monkeypatch.setenv("TOM_TASK_STORE", "0")
    assert open_store().path == ":memory:"


def test_newer_schema_is_refused(db):
    store = TaskStore(db)
    store._db.execute("UPDATE meta SET value='99' WHERE key='schema_version'")
    store._db.commit()
    with pytest.raises(RuntimeError, match="newer"):
        TaskStore(db)


# ── service ──────────────────────────────────────────────────────────────

def _service(db, runner, **kw):
    return TaskService(runner, TaskStore(db), **kw)


def test_submit_returns_the_result_with_task_identity(db):
    async def runner(text):
        return {"status": "success", "response_type": "chat", "message": f"echo {text}"}
    svc = _service(db, runner)
    result = asyncio.run(svc.submit_task("hello", "cli"))
    assert result["message"] == "echo hello" and result["task_state"] == "SUCCEEDED"
    rec = svc.get_task(result["task_id"])
    assert rec.interface == "cli" and rec.state is TaskState.SUCCEEDED


def test_a_crashing_handler_is_recorded_as_failed(db):
    async def runner(text):
        raise RuntimeError("model exploded")
    svc = _service(db, runner)
    with pytest.raises(RuntimeError):
        asyncio.run(svc.submit_task("hello", "cli"))
    rec = svc.list_tasks(1)[0]
    assert rec.state is TaskState.FAILED and "model exploded" in rec.error


def test_nested_requests_record_their_parent(db):
    svc = None

    async def runner(text):
        if text == "outer":
            inner = await svc.submit_task("inner", "autonomous")
            return {"status": "success", "response_type": "chat", "message": inner["task_id"]}
        return {"status": "success", "response_type": "chat", "message": "ok"}
    svc = _service(db, runner)
    outer = asyncio.run(svc.submit_task("outer", "cli"))
    assert svc.get_task(outer["message"]).parent_id == outer["task_id"]


def test_cancel_requested_from_another_interface_stops_the_task(db):
    """AT-005 + AT-012: a second process (here: a second store connection) cancels a running task."""
    started = asyncio.Event()

    async def runner(text):
        started.set()
        await asyncio.sleep(30)
        return {"status": "success", "message": "should never get here"}

    svc = _service(db, runner, cancel_poll_seconds=0.05)
    other_window = TaskStore(db)

    async def scenario():
        job = asyncio.create_task(svc.submit_task("long job", "desktop"))
        await started.wait()
        task_id = other_window.list(1, active_only=True)[0].id
        assert other_window.request_cancel(task_id)
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(job, timeout=5)
        return task_id

    task_id = asyncio.run(scenario())
    assert other_window.get(task_id).state is TaskState.CANCELLED


def test_emergency_stop_cancels_everything_running(db):
    async def runner(text):
        await asyncio.sleep(30)

    svc = _service(db, runner)

    async def scenario():
        jobs = [asyncio.create_task(svc.submit_task(f"job {i}", "cli")) for i in range(3)]
        await asyncio.sleep(0.05)
        assert len(svc.cancel_all()) == 3
        return await asyncio.gather(*jobs, return_exceptions=True)

    outcomes = asyncio.run(scenario())
    assert all(isinstance(o, asyncio.CancelledError) for o in outcomes)
    assert {r.state for r in svc.list_tasks(3)} == {TaskState.CANCELLED}


# ── agent facade + rollback flag (TOM-MIG-002 / TOM-MIG-007) ─────────────

def test_rollback_flag_runs_the_legacy_path(monkeypatch):
    monkeypatch.setenv("TOM_TASK_SERVICE", "0")
    monkeypatch.setenv("HINDSIGHT_ENABLED", "0")
    monkeypatch.setenv("TOM_LLM_PROVIDER", "ollama")
    from agent import TomAgent
    tom = TomAgent()
    assert tom.tasks is None
    result = asyncio.run(tom.execute_task("system status"))
    assert result["status"] == "success" and "task_id" not in result


# ── redaction ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("secret", [
    "gsk_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345", "hsk_0000aaaa1111bbbb2222cccc_3333dddd",
    "sk-ant-api03-abcdefghijklmnopqrstu", "sk-proj-abcdefghijklmnopqrstuvwx", "ghp_abcdefghijklmnopqrstuvwxyz0123",
    "xoxb-1234567890-abcdefghij", "AIzaSyA1234567890abcdefghijklmnopqrstu", "AKIAABCDEFGHIJKLMNOP",
    "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijklmnopqrstuv",
])
def test_known_credential_shapes_are_masked(secret):
    out = redact(f"here it is: {secret} ok")
    assert secret not in out and MASK in out and out.endswith(" ok")


@pytest.mark.parametrize("text,leak", [
    ("EMAIL_PASSWORD=abcd efgh", "abcd"),
    ('api_key: "s3cr3t-value-123"', "s3cr3t"),
    ("Authorization: Bearer abc.def.ghijklmnop", "abc.def"),
    ("my wifi password is Tr0ub4dor&3", "Tr0ub4dor"),
])
def test_secret_key_value_forms_are_masked(text, leak):
    assert leak not in redact(text)


def test_loaded_secret_env_values_are_masked_whatever_their_shape(monkeypatch):
    monkeypatch.setenv("SOME_SERVICE_TOKEN", "zz-unusual-shape-9911")
    assert "zz-unusual-shape-9911" not in redact("token zz-unusual-shape-9911 pasted")


def test_ordinary_text_is_left_alone():
    text = "Open Chrome and search the weather in Hyderabad at 9 AM."
    assert redact(text) == text
