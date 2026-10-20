"""PySide6 interface: drives the real window headless against a fake agent + real TaskService."""
import asyncio
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

from tom_core.interfaces import qt_app  # noqa: E402
from tom_core.tasks import TaskService  # noqa: E402
from tom_core.tasks.store import TaskStore  # noqa: E402
from tools.approval import ApprovalManager, ApprovalRequest  # noqa: E402


class FakeAgent:
    model_name = "qwen3:8b"
    llm_provider = "ollama"

    def __init__(self, db):
        self.approval_manager = ApprovalManager()
        self.approval_manager.provider = None
        self.tasks = TaskService(self._run, TaskStore(db), cancel_poll_seconds=0.05)

    async def _run(self, text):
        if text == "delete the report":
            ok = await asyncio.to_thread(self.approval_manager.request_approval, ApprovalRequest(
                action="delete_path", summary="Delete C:/work/report.docx?",
                details={"path": "C:/work/report.docx"}, risk_level="high"))
            return {"status": "success" if ok else "cancelled",
                    "message": "Deleted." if ok else "Delete cancelled.", "response_type": "delete"}
        if text == "long job":
            await asyncio.sleep(30)
        return {"status": "success", "response_type": "chat", "message": f"You said: {text}"}

    async def execute_task(self, text, interface=""):
        return await self.tasks.submit_task(text, interface or "unknown")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(app, tmp_path):
    w = qt_app.TomWindow(lambda: FakeAgent(str(tmp_path / "tasks.sqlite3")), start_sampler=False)
    _wait(app, lambda: w.input.isEnabled(), "agent ready")
    yield w
    w.close()


def _wait(app, cond, what, timeout=10.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        if cond():
            return
        time.sleep(0.02)
    raise AssertionError(f"timed out waiting for {what}")


def _states(w):
    return [w.task_table.item(r, 0).text() for r in range(w.task_table.rowCount())]


def test_a_request_round_trips_through_the_task_service(app, win):
    assert "qwen3:8b" in win.model_lbl.text() and "local" in win.model_lbl.text()
    win.input.setText("hello TOM")
    win.send()
    _wait(app, lambda: "You said: hello TOM" in win.chat.toPlainText(), "reply")
    win.refresh_tasks()
    assert _states(win) == ["SUCCEEDED"]
    assert win.task_table.item(0, 2).text() == "desktop-qt"


@pytest.mark.parametrize("answer,expected", [(QDialog.Accepted, "Deleted."), (QDialog.Rejected, "Delete cancelled.")])
def test_approval_dialog_shows_the_action_and_its_answer_is_honoured(app, win, monkeypatch, answer, expected):
    shown = []

    def fake_exec(dlg):
        shown.append(dlg.findChild(qt_app.QTextBrowser).toPlainText())
        return answer
    monkeypatch.setattr(qt_app.ApprovalDialog, "exec", fake_exec)
    win.send("delete the report")
    _wait(app, lambda: expected in win.chat.toPlainText(), "approval outcome")
    assert shown and "C:/work/report.docx" in shown[0]
    win.refresh_tasks()
    assert _states(win)[0] == ("UNVERIFIED" if answer == QDialog.Accepted else "REJECTED")


def test_emergency_stop_cancels_running_work(app, win):
    win.send("long job")
    _wait(app, lambda: (win.refresh_tasks() or True) and _states(win)[:1] == ["RUNNING"], "task running")
    win.emergency_stop()
    _wait(app, lambda: "CANCELLED" in win.chat.toPlainText(), "cancel reply")
    win.refresh_tasks()
    assert _states(win)[0] == "CANCELLED"


def test_task_selection_survives_refresh_and_shows_the_timeline(app, win):
    win.send("first")
    _wait(app, lambda: "You said: first" in win.chat.toPlainText(), "reply")
    win.refresh_tasks()
    win.task_table.selectRow(0)
    task_id = win._selected_task
    assert task_id
    for _ in range(3):
        win.refresh_tasks()
    assert win._selected_task == task_id
    assert "RUNNING" in win.task_detail.toPlainText() and "SUCCEEDED" in win.task_detail.toPlainText()


def test_resource_and_privacy_panels(app, win):
    win._on_sample({"cpu": 37.0, "ram_used": 20.0, "ram_total": 32.0, "ram_avail": 12.0,
                    "vram_used": 6000, "vram_total": 8151, "vram_free": 2151})
    assert win.bars["CPU"].value() == 37 and "12.0 GB free" in win.bar_lbls["RAM"].text()
    assert "2.1 GB free" in win.bar_lbls["VRAM"].text()
    assert "Prompts and replies" in win.privacy_lbl.text()
