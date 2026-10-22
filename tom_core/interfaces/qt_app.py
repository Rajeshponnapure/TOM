"""TOM — PySide6 desktop interface (runs beside the Tkinter app; ADR-003).

A client of TaskService, never a second brain (PRD §12.2): requests go through
TomAgent.execute_task(..., interface="desktop-qt"); the task list reads the shared task store, so
tasks started from the Tk app or the CLI appear here too and can be cancelled from here (AT-012).

PRD §14 coverage: task list + timeline, active task, status, resource panel (CPU/RAM/VRAM every
2 s, §6.5), approvals with the exact action, model name + local/cloud route, privacy routes,
push-to-talk voice (§7), and a visible emergency stop.
"""
from __future__ import annotations

import asyncio
import html
import os
import sys
import threading
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QColor, QFont, QKeySequence, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton, QSplitter, QTableWidget,
    QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget,
)

from tom_core.voice import push_to_talk

APP_NAME = os.environ.get("TOM_PRODUCT_NAME", "TOM")      # branding stays configurable (§S8)
TALK_LABEL = "🎙  Push to talk"

STATE_COLORS = {
    "CREATED": "#8b95a7", "RUNNING": "#4f9dff", "AWAITING_APPROVAL": "#f5a524", "BLOCKED": "#f5a524",
    "NEEDS_INPUT": "#f5a524", "SUCCEEDED": "#2fbf71", "UNVERIFIED": "#c9a227", "FAILED": "#ef5350",
    "REJECTED": "#ef5350", "CANCELLED": "#8b95a7",
}

STYLE = """
QWidget { background: #0f1420; color: #e6e9ef; font-family: 'Segoe UI', sans-serif; font-size: 10pt; }
QFrame#panel { background: #161d2b; border: 1px solid #222c3f; border-radius: 10px; }
QLabel#h { color: #9fb0c8; font-weight: 600; font-size: 9pt; letter-spacing: 0.5px; }
QLabel#title { font-size: 15pt; font-weight: 700; }
QLineEdit { background: #0b0f18; border: 1px solid #2a3550; border-radius: 8px; padding: 9px 12px; }
QLineEdit:focus { border-color: #4f9dff; }
QPushButton { background: #22304a; border: 1px solid #2f3f5f; border-radius: 8px; padding: 8px 14px; }
QPushButton:hover { background: #2a3b5c; }
QPushButton:disabled { color: #5d6b83; background: #18202f; }
QPushButton#primary { background: #2e6fd8; border-color: #3a7be6; font-weight: 600; }
QPushButton#primary:hover { background: #3a7be6; }
QPushButton#danger { background: #a3262a; border-color: #c4373c; font-weight: 700; }
QPushButton#danger:hover { background: #c4373c; }
QPushButton#talk:checked { background: #2fbf71; border-color: #36d27d; color: #08130c; }
QTableWidget { background: #0b0f18; border: 1px solid #222c3f; border-radius: 8px; gridline-color: #1b2333; }
QHeaderView::section { background: #161d2b; color: #9fb0c8; border: none; padding: 6px; }
QTableWidget::item:selected { background: #22304a; }
QTextBrowser { background: #0b0f18; border: 1px solid #222c3f; border-radius: 8px; padding: 8px; }
QProgressBar { background: #0b0f18; border: 1px solid #222c3f; border-radius: 6px; height: 12px; text-align: center; }
QProgressBar::chunk { background: #4f9dff; border-radius: 6px; }
"""


# ── background plumbing ──────────────────────────────────────────────────

class AgentHost(QObject):
    """Owns TomAgent and an asyncio loop on a worker thread; talks to the UI through signals."""

    ready = Signal(dict)
    failed = Signal(str)
    result = Signal(str, dict)            # request text, result dict
    progress = Signal(str)
    approval_needed = Signal(object, object)   # ApprovalRequest, reply callback

    def __init__(self, agent_factory: Callable[[], Any]) -> None:
        super().__init__()
        self._factory = agent_factory
        self.agent: Any = None
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, name="tom-qt-agent-loop", daemon=True)

    def start(self) -> None:
        self._thread.start()
        threading.Thread(target=self._build, name="tom-qt-agent-build", daemon=True).start()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _build(self) -> None:
        try:
            agent = self._factory()
            agent.approval_manager.provider = self._ask_approval
            try:
                import agent as agent_module
                agent_module.set_progress_callback(self.progress.emit)
            except Exception:
                pass
            self.agent = agent
            self.ready.emit({"model": getattr(agent, "model_name", "?"),
                             "provider": getattr(agent, "llm_provider", "?")})
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")

    def _ask_approval(self, request: Any) -> bool:
        """Called on a task thread: block it until the user answers on the UI thread."""
        answered = threading.Event()
        box: Dict[str, bool] = {"ok": False}

        def reply(ok: bool) -> None:
            box["ok"] = bool(ok)
            answered.set()
        self.approval_needed.emit(request, reply)
        answered.wait(timeout=600)          # an unanswered prompt is a "no" (fail safe)
        return box["ok"]

    def submit(self, text: str, interface: str = "desktop-qt") -> None:
        if self.agent is None:
            return

        async def _go() -> None:
            try:
                res = await self.agent.execute_task(text, interface=interface)
            except asyncio.CancelledError:
                res = {"status": "cancelled", "message": "Stopped.", "task_state": "CANCELLED"}
            except Exception as exc:
                res = {"status": "error", "message": f"{type(exc).__name__}: {exc}"}
            self.result.emit(text, res if isinstance(res, dict) else {"message": str(res)})
        asyncio.run_coroutine_threadsafe(_go(), self.loop)

    def stop(self) -> None:
        """Cancel whatever is still running on the loop (tasks are recorded CANCELLED), then stop it."""
        def _shutdown() -> None:
            for task in asyncio.all_tasks(self.loop):
                task.cancel()
            self.loop.call_soon(self.loop.stop)     # after the cancellations have been delivered
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(_shutdown)


class ResourceSampler(QObject):
    """CPU / RAM / VRAM every 2 s on its own thread (PRD §6.5; nvidia-smi must not block the UI)."""

    sample = Signal(dict)

    def __init__(self, interval: float = 2.0) -> None:
        super().__init__()
        self.interval = interval
        self._stop = threading.Event()

    @Slot()
    def run(self) -> None:
        from tom_core.resources.gpu import query_gpu_memory
        try:
            import psutil
        except ImportError:
            psutil = None
        while not self._stop.is_set():
            data: Dict[str, Any] = {}
            if psutil is not None:
                vm = psutil.virtual_memory()
                data.update(cpu=psutil.cpu_percent(interval=None), ram_used=vm.used / 2**30,
                            ram_total=vm.total / 2**30, ram_avail=vm.available / 2**30)
            gpu = query_gpu_memory()
            if gpu is not None:
                data.update(vram_used=gpu.used_mb, vram_total=gpu.total_mb, vram_free=gpu.free_mb)
            self.sample.emit(data)
            self._stop.wait(self.interval)

    def stop(self) -> None:
        self._stop.set()


# ── dialogs ──────────────────────────────────────────────────────────────

class ApprovalDialog(QDialog):
    """Shows exactly what will happen before it happens (PRD §11.2 approval gate)."""

    def __init__(self, request: Any, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Approval required")
        self.setModal(True)
        self.setMinimumWidth(520)
        lay = QVBoxLayout(self)
        risk = str(getattr(request, "risk_level", "medium")).upper()
        head = QLabel(f"<b>{html.escape(str(getattr(request, 'action', 'action')))}</b>"
                      f" &nbsp;<span style='color:#f5a524'>risk: {html.escape(risk)}</span>")
        lay.addWidget(head)
        body = QTextBrowser()
        details = getattr(request, "details", {}) or {}
        rows = "".join(f"<tr><td style='color:#9fb0c8;padding-right:10px'>{html.escape(str(k))}</td>"
                       f"<td>{html.escape(str(v))}</td></tr>" for k, v in details.items())
        body.setHtml(f"<p>{html.escape(str(getattr(request, 'summary', ''))).replace(chr(10), '<br>')}</p>"
                     + (f"<table>{rows}</table>" if rows else ""))
        body.setMinimumHeight(160)
        lay.addWidget(body)
        buttons = QDialogButtonBox()
        self.approve = buttons.addButton("Approve", QDialogButtonBox.AcceptRole)
        self.reject_btn = buttons.addButton("Reject", QDialogButtonBox.RejectRole)
        self.approve.setObjectName("primary")
        self.reject_btn.setDefault(True)                     # Enter rejects: approving is a deliberate act
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)


# ── main window ──────────────────────────────────────────────────────────

class TomWindow(QMainWindow):
    voice_heard = Signal(str)
    voice_status = Signal(str)

    def __init__(self, agent_factory: Callable[[], Any], *, start_sampler: bool = True,
                 voice_factory: Optional[Callable[[], Any]] = None) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — Personal AI Operating Agent")
        self.resize(1440, 880)
        self.host = AgentHost(agent_factory)
        self._voice_factory = voice_factory
        self.voice: Any = None
        self._selected_task: Optional[str] = None
        self._speak_next = False          # set when a request came from push-to-talk: answer aloud
        self._listening = False           # a push-to-talk capture/recognition is running
        self._build_ui()
        self._wire()
        self.host.start()
        self.sampler_thread: Optional[QThread] = None
        if start_sampler:
            self._start_sampler()
        self.task_timer = QTimer(self)
        self.task_timer.timeout.connect(self.refresh_tasks)
        self.task_timer.start(1000)

    # layout ----------------------------------------------------------------
    def _panel(self, title: str) -> tuple:
        frame = QFrame(objectName="panel")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 10, 12, 12)
        lbl = QLabel(title.upper(), objectName="h")
        lay.addWidget(lbl)
        return frame, lay

    def _build_ui(self) -> None:
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(14, 12, 14, 14)

        top = QHBoxLayout()
        title = QLabel(APP_NAME, objectName="title")
        self.status_lbl = QLabel("Starting… loading models and memory")
        self.status_lbl.setStyleSheet("color:#9fb0c8")
        self.stop_all_btn = QPushButton("■  EMERGENCY STOP", objectName="danger")
        self.stop_all_btn.setToolTip("Cancel every running task (all TOM windows) and stop speaking.  Ctrl+.")
        top.addWidget(title)
        top.addSpacing(16)
        top.addWidget(self.status_lbl, 1)
        top.addWidget(self.stop_all_btn)
        outer.addLayout(top)

        split = QSplitter(Qt.Horizontal)

        # left: tasks
        left, ll = self._panel("Tasks — all interfaces")
        self.task_table = QTableWidget(0, 4)
        self.task_table.setHorizontalHeaderLabels(["State", "Request", "From", "Time"])
        self.task_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.task_table.setEditTriggers(QTableWidget.NoEditTriggers)
        ll.addWidget(self.task_table, 3)
        self.task_detail = QTextBrowser()
        self.task_detail.setPlaceholderText("Select a task to see its timeline.")
        ll.addWidget(self.task_detail, 2)
        self.cancel_btn = QPushButton("Cancel selected task")
        self.cancel_btn.setEnabled(False)
        ll.addWidget(self.cancel_btn)
        split.addWidget(left)

        # centre: conversation
        centre, cl = self._panel("Conversation")
        self.chat = QTextBrowser()
        self.chat.setOpenExternalLinks(False)
        cl.addWidget(self.chat, 1)
        self.progress_lbl = QLabel("")
        self.progress_lbl.setStyleSheet("color:#6f8fb8")
        cl.addWidget(self.progress_lbl)
        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask TOM to do something…  (Enter to send)")
        self.input.setEnabled(False)
        self.send_btn = QPushButton("Send", objectName="primary")
        self.send_btn.setEnabled(False)
        self.talk_btn = QPushButton(TALK_LABEL, objectName="talk")
        self.talk_btn.setCheckable(True)
        self.talk_btn.setEnabled(False)
        self.talk_btn.setToolTip("Click and speak one request; it ends when you stop talking, or click "
                                 "again when you're done. TOM answers aloud.  Ctrl+Space")
        self.hush_btn = QPushButton("Stop speaking")
        row.addWidget(self.input, 1)
        row.addWidget(self.send_btn)
        row.addWidget(self.talk_btn)
        row.addWidget(self.hush_btn)
        cl.addLayout(row)
        split.addWidget(centre)

        # right: system
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        res, resl = self._panel("Resources")
        grid = QGridLayout()
        self.bars: Dict[str, QProgressBar] = {}
        self.bar_lbls: Dict[str, QLabel] = {}
        for i, key in enumerate(("CPU", "RAM", "VRAM")):
            grid.addWidget(QLabel(key), i, 0)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setTextVisible(False)
            self.bars[key] = bar
            grid.addWidget(bar, i, 1)
            lbl = QLabel("—")
            lbl.setMinimumWidth(120)
            self.bar_lbls[key] = lbl
            grid.addWidget(lbl, i, 2)
        resl.addLayout(grid)
        rl.addWidget(res)
        model, ml = self._panel("Model")
        self.model_lbl = QLabel("—")
        self.model_lbl.setWordWrap(True)
        ml.addWidget(self.model_lbl)
        rl.addWidget(model)
        priv, pl = self._panel("Where your data goes")
        self.privacy_lbl = QLabel("—")
        self.privacy_lbl.setWordWrap(True)
        self.privacy_lbl.setTextFormat(Qt.RichText)
        pl.addWidget(self.privacy_lbl)
        rl.addWidget(priv)
        voice, vl = self._panel("Voice")
        self.voice_lbl = QLabel("Push-to-talk. Speech is recognised on this machine by default.")
        self.voice_lbl.setWordWrap(True)
        vl.addWidget(self.voice_lbl)
        rl.addWidget(voice)
        rl.addStretch(1)
        split.addWidget(right)

        split.setSizes([420, 700, 320])
        outer.addWidget(split, 1)
        self.setCentralWidget(root)
        self.refresh_privacy()

    def _wire(self) -> None:
        self.send_btn.clicked.connect(self.send)
        self.input.returnPressed.connect(self.send)
        self.stop_all_btn.clicked.connect(self.emergency_stop)
        self.cancel_btn.clicked.connect(self.cancel_selected)
        self.task_table.itemSelectionChanged.connect(self._on_select)
        self.talk_btn.toggled.connect(self._on_talk)
        self.hush_btn.clicked.connect(self._hush)
        self.host.ready.connect(self._on_ready)
        self.host.failed.connect(self._on_failed)
        self.host.result.connect(self._on_result)
        self.host.progress.connect(lambda m: self.progress_lbl.setText(m[:160]))
        self.host.approval_needed.connect(self._on_approval)
        self.voice_heard.connect(self._on_voice_heard)
        self.voice_status.connect(self.voice_lbl.setText)
        stop = QAction(self)
        stop.setShortcut(QKeySequence("Ctrl+."))
        stop.triggered.connect(self.emergency_stop)
        talk = QAction(self)
        talk.setShortcut(QKeySequence("Ctrl+Space"))
        talk.triggered.connect(lambda: self.talk_btn.isEnabled() and self.talk_btn.toggle())
        self.addActions([stop, talk])

    def _start_sampler(self) -> None:
        self.sampler = ResourceSampler()
        self.sampler_thread = QThread(self)
        self.sampler.moveToThread(self.sampler_thread)
        self.sampler_thread.started.connect(self.sampler.run)
        self.sampler.sample.connect(self._on_sample)
        self.sampler_thread.start()

    # chat ------------------------------------------------------------------
    def _append(self, who: str, text: str, color: str = "#e6e9ef") -> None:
        body = html.escape(text).replace("\n", "<br>")
        self.chat.append(f"<p style='margin:6px 0'><b style='color:{color}'>{html.escape(who)}</b><br>{body}</p>")
        self.chat.moveCursor(QTextCursor.End)

    @Slot()
    def send(self, text: Optional[str] = None, interface: str = "desktop-qt") -> None:
        text = (text if isinstance(text, str) else self.input.text()).strip()
        if not text or self.host.agent is None:
            return
        self.input.clear()
        self._append("You", text, "#7fb2ff")
        self.status_lbl.setText("Working…")
        from tom_core.policy import get_policy
        get_policy().resume()            # a new request from the user lifts an emergency stop
        self.host.submit(text, interface)

    @Slot(str, dict)
    def _on_result(self, request: str, result: dict) -> None:
        state = str(result.get("task_state", result.get("status", "")))
        color = STATE_COLORS.get(state, "#e6e9ef")
        message = str(result.get("message", "")) or "(no message)"
        self._append(f"{APP_NAME}  ·  {state}" if state else APP_NAME, message, color)
        self.progress_lbl.setText("")
        self.status_lbl.setText("Ready")
        self.refresh_tasks()
        if getattr(self, "_speak_next", False):
            self._speak_next = False
            self._speak(message)

    # tasks -----------------------------------------------------------------
    def _store(self):
        tasks = getattr(self.host.agent, "tasks", None)
        return tasks.store if tasks is not None else None

    @Slot()
    def refresh_tasks(self) -> None:
        store = self._store()
        if store is None:
            return
        records = store.list(60)
        self.task_table.blockSignals(True)          # rebuilding rows must not clear the selection
        try:
            self.task_table.clearSelection()
            self.task_table.setRowCount(len(records))
            for i, rec in enumerate(records):
                state = QTableWidgetItem(rec.state.value)
                state.setForeground(QColor(STATE_COLORS.get(rec.state.value, "#e6e9ef")))
                state.setData(Qt.UserRole, rec.id)
                when = rec.created_at[11:19] if len(rec.created_at) >= 19 else rec.created_at
                for col, item in enumerate((state, QTableWidgetItem(rec.text[:200]),
                                            QTableWidgetItem(rec.interface), QTableWidgetItem(when))):
                    self.task_table.setItem(i, col, item)
                if rec.id == self._selected_task:
                    self.task_table.selectRow(i)
        finally:
            self.task_table.blockSignals(False)
        self._show_detail()

    def _on_select(self) -> None:
        rows = self.task_table.selectionModel().selectedRows()
        self._selected_task = self.task_table.item(rows[0].row(), 0).data(Qt.UserRole) if rows else None
        self._show_detail()

    def _show_detail(self) -> None:
        store = self._store()
        rec = store.get(self._selected_task) if (store and self._selected_task) else None
        self.cancel_btn.setEnabled(bool(rec and not rec.terminal))
        if rec is None:
            return
        lines = [f"<b>{html.escape(rec.text)}</b>",
                 f"<span style='color:{STATE_COLORS.get(rec.state.value, '#fff')}'>{rec.state.value}</span>"
                 f" · {html.escape(rec.interface)} · id {rec.id}"]
        if rec.outcome:
            lines.append(f"<i>{html.escape(rec.outcome[:400])}</i>")
        if rec.error:
            lines.append(f"<span style='color:#ef5350'>{html.escape(rec.error)}</span>")
        lines.append("<br>".join(f"<span style='color:#6f8fb8'>{html.escape(e['at'][11:19])}</span> "
                                 f"{html.escape(e['kind'])} {html.escape(e['message'])}" for e in rec.events))
        self.task_detail.setHtml("<br>".join(lines))

    @Slot()
    def cancel_selected(self) -> None:
        tasks = getattr(self.host.agent, "tasks", None)
        if tasks and self._selected_task:
            tasks.cancel_task(self._selected_task)
            self.status_lbl.setText("Cancellation requested")

    @Slot()
    def emergency_stop(self) -> None:
        """PRD §11.2: stop all new execution now — every running task in every TOM window."""
        from tom_core.policy import get_policy
        get_policy().halt("emergency stop pressed in the desktop app")   # no new tool calls start
        tasks = getattr(self.host.agent, "tasks", None)
        cancelled = set()
        if tasks is not None:
            cancelled.update(tasks.cancel_all())                      # this window's tasks, immediately
            for rec in tasks.store.list(200, active_only=True):        # other windows/CLI pick it up in ~1 s
                if tasks.store.request_cancel(rec.id):
                    cancelled.add(rec.id)
        n = len(cancelled)
        self._hush()
        if self.voice is not None and hasattr(self.voice, "cancel_listening"):
            self.voice.cancel_listening()        # an open microphone is dropped, not sent
        self.status_lbl.setText(f"Emergency stop: {n} cancellation(s) requested")
        self._append("System", f"Emergency stop — {n} task cancellation(s) requested; speech stopped.", "#ef5350")

    # approvals ---------------------------------------------------------------
    @Slot(object, object)
    def _on_approval(self, request: Any, reply: Callable[[bool], None]) -> None:
        dlg = ApprovalDialog(request, self)
        reply(dlg.exec() == QDialog.Accepted)

    # resources / model / privacy ---------------------------------------------
    @Slot(dict)
    def _on_sample(self, d: dict) -> None:
        if "cpu" in d:
            self.bars["CPU"].setValue(int(d["cpu"]))
            self.bar_lbls["CPU"].setText(f"{d['cpu']:.0f}%")
            self.bars["RAM"].setValue(int(100 * d["ram_used"] / max(d["ram_total"], 0.01)))
            self.bar_lbls["RAM"].setText(f"{d['ram_avail']:.1f} GB free")
        if "vram_total" in d:
            self.bars["VRAM"].setValue(int(100 * d["vram_used"] / max(d["vram_total"], 1)))
            self.bar_lbls["VRAM"].setText(f"{d['vram_free'] / 1024:.1f} GB free")

    def refresh_privacy(self) -> None:
        try:
            from tom_core.privacy import current_routes
            rows = []
            for r in current_routes():
                tag = ("<span style='color:#ef5350'>CLOUD</span>" if r.cloud
                       else "<span style='color:#2fbf71'>LOCAL</span>")
                rows.append(f"{tag} &nbsp;{html.escape(r.name)}<br>"
                            f"<span style='color:#8b95a7'>{html.escape(r.provider)}</span>")
            self.privacy_lbl.setText("<br><br>".join(rows))
        except Exception as exc:
            self.privacy_lbl.setText(f"unavailable: {html.escape(str(exc))}")

    @Slot(dict)
    def _on_ready(self, info: dict) -> None:
        route = "cloud" if info.get("provider") == "groq" else "local"
        self.model_lbl.setText(f"<b>{html.escape(str(info.get('model')))}</b><br>"
                               f"provider: {html.escape(str(info.get('provider')))} ({route})")
        self.status_lbl.setText("Ready")
        for w in (self.input, self.send_btn, self.talk_btn):
            w.setEnabled(True)
        self.input.setFocus()
        self.refresh_privacy()
        self.refresh_tasks()
        recovered = getattr(getattr(self.host.agent, "tasks", None), "recovered", [])
        if recovered:
            self._append("System", f"{len(recovered)} task(s) were interrupted by the last shutdown and "
                                   "are marked BLOCKED — they were not re-run. Check them in the task list.",
                         "#f5a524")

    @Slot(str)
    def _on_failed(self, message: str) -> None:
        self.status_lbl.setText("TOM could not start")
        QMessageBox.critical(self, f"{APP_NAME} could not start", message)

    # voice (push-to-talk, PRD §7) ----------------------------------------------
    def _voice(self):
        if self.voice is None:
            if self._voice_factory is not None:
                self.voice = self._voice_factory()
            else:
                os.environ.setdefault("VOICE_INPUT_ENABLED", "true")
                os.environ.setdefault("VOICE_OUTPUT_ENABLED", "true")
                from tools.voice_tools import VoiceTools
                self.voice = VoiceTools()
                push_to_talk.prepare(self.voice)
        return self.voice

    @Slot(bool)
    def _on_talk(self, on: bool) -> None:
        if not on:
            # Clicked again while listening: the request is complete, recognise it now.
            if self._listening and self.voice is not None:
                push_to_talk.finish(self.voice)
                self.talk_btn.setText("Recognising…")
            return
        if self._listening:
            # The previous request is still being recognised; one microphone user at a time.
            self.talk_btn.setChecked(False)
            return
        self._listening = True
        self.talk_btn.setText("■  Done")

        def _listen() -> None:
            try:
                v = self._voice()
                error = push_to_talk.prepare(v) if self._voice_factory is None else ""
                if error:
                    heard = push_to_talk.Heard("", f"Voice input could not start: {error}")
                else:
                    self.voice_status.emit("Listening… speak now.")
                    heard = push_to_talk.capture(v)
            except Exception as exc:
                heard = push_to_talk.Heard("", f"Voice error: {exc}")
            self.voice_status.emit(heard.message)
            self.voice_heard.emit(heard.text)
        threading.Thread(target=_listen, name="tom-qt-listen", daemon=True).start()

    @Slot(str)
    def _on_voice_heard(self, text: str) -> None:
        self._listening = False
        self.talk_btn.setChecked(False)
        self.talk_btn.setText(TALK_LABEL)
        if text:
            self._speak_next = True
            self.send(text, interface="voice")

    def _speak(self, message: str) -> None:
        v = self._voice()
        threading.Thread(target=lambda: v.speak(message[:600]), name="tom-qt-speak", daemon=True).start()

    @Slot()
    def _hush(self) -> None:
        if self.voice is not None:
            self.voice.stop_speaking()

    # shutdown ----------------------------------------------------------------
    def closeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        self.task_timer.stop()
        if self.sampler_thread is not None:
            self.sampler.stop()
            self.sampler_thread.quit()
            self.sampler_thread.wait(3000)
        if self.voice is not None:
            try:
                self.voice.stop_speaking()
                self.voice.cancel_listening()
                self.voice.release_recognizer()
            except Exception:
                pass
        self.host.stop()
        super().closeEvent(event)


def _default_agent_factory():
    from agent import TomAgent
    return TomAgent()


def main(argv: Optional[List[str]] = None) -> int:
    from tom_core.voice.workers import maybe_run_worker
    if maybe_run_worker(argv):
        return 0
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
    try:
        from tools.crash_guard import install as _cg_install
        _cg_install("desktop-qt")
    except Exception:
        pass
    app = QApplication.instance() or QApplication(sys.argv if argv is None else argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(STYLE)
    app.setFont(QFont("Segoe UI", 10))
    win = TomWindow(_default_agent_factory)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
