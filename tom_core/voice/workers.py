"""Isolated worker processes for native speech engines.

Why a process and not a thread: WinRT speech and CTranslate2/onnxruntime/torch cannot share a
process safely (access violation, see voice/__init__.py), an ASR model takes seconds to load and
should stay warm, and a crash inside a native engine must not take TOM down (PRD §S4: subsystems
degrade independently).

Protocol — one JSON object per line:
  worker → client  {"event": "ready", ...info}            once, after loading
                   {"event": "error", "message": ...}      fatal start-up failure, then exit
                   {"id": n, "ok": true|false, ...}        one reply per request
  client → worker  {"id": n, "op": "...", ...args}
                   {"op": "shutdown"}
"""
from __future__ import annotations

import itertools
import json
import os
import subprocess
import sys
import threading
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any, Dict, List, Optional

from tools.project_paths import PROJECT_ROOT, project_path

LOG_DIR = project_path("tom_logs")
WORKER_FLAG = "--tom-voice-worker"


class WorkerError(RuntimeError):
    pass


def worker_command(kind: str) -> List[str]:
    """Command line that starts worker `kind` ("asr" | "tts"), source checkout or frozen exe."""
    if getattr(sys, "frozen", False):
        # PyInstaller: re-launch the same exe; its main() calls maybe_run_worker() first.
        return [sys.executable, WORKER_FLAG, kind]
    return [sys.executable, "-u", "-m", f"tom_core.voice.{kind}_worker"]


def maybe_run_worker(argv: Optional[List[str]] = None) -> bool:
    """Entry hook for frozen builds: run a worker instead of the app when asked to. Returns True if it ran."""
    argv = list(sys.argv if argv is None else argv)
    if WORKER_FLAG not in argv:
        return False
    kind = argv[argv.index(WORKER_FLAG) + 1]
    if kind == "asr":
        from tom_core.voice import asr_worker as mod
    elif kind == "tts":
        from tom_core.voice import tts_worker as mod
    else:
        raise SystemExit(f"unknown worker kind: {kind}")
    mod.main()
    return True


class WorkerProcess:
    """Client side of one worker. Thread-safe; lazily started; restarted once if it dies."""

    def __init__(self, kind: str, *, env: Optional[Dict[str, str]] = None,
                 start_timeout: float = 120.0, command: Optional[List[str]] = None) -> None:
        self.kind = kind
        self._env = env or {}
        self._start_timeout = start_timeout
        self._command = command or worker_command(kind)
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.RLock()
        self._pending: Dict[int, Future] = {}
        self._ids = itertools.count(1)
        self._ready: Optional[Future] = None
        self.info: Dict[str, Any] = {}
        self.last_error = ""

    # ── lifecycle ────────────────────────────────────────────────────────
    @property
    def alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self) -> Dict[str, Any]:
        """Start the worker (if needed) and wait until it reports ready. Raises WorkerError."""
        with self._lock:
            if self.alive and self._ready is not None and self._ready.done() and not self._ready.exception():
                return self.info
            if not self.alive:
                self._spawn()
            ready = self._ready
        try:
            self.info = ready.result(timeout=self._start_timeout)
        except FutureTimeout:
            self.stop()
            raise WorkerError(f"{self.kind} worker did not become ready within {self._start_timeout:.0f}s") from None
        except WorkerError:
            self.stop()
            raise
        return self.info

    def _spawn(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        env.update(self._env)
        env["PYTHONIOENCODING"] = "utf-8"
        env["HF_HUB_OFFLINE"] = "1"          # never download a model from a worker
        env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        log = open(LOG_DIR / f"voice_{self.kind}_worker.log", "a", encoding="utf-8")
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        self._proc = subprocess.Popen(
            self._command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log,
            cwd=str(PROJECT_ROOT), env=env, creationflags=flags,
            text=True, encoding="utf-8", bufsize=1)
        log.close()  # the child holds its own handle
        self._ready = Future()
        threading.Thread(target=self._read_loop, args=(self._proc, self._ready),
                         name=f"tom-{self.kind}-worker-reader", daemon=True).start()

    def _read_loop(self, proc: subprocess.Popen, ready: Future) -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            event = msg.get("event")
            if event == "ready" and not ready.done():
                ready.set_result({k: v for k, v in msg.items() if k != "event"})
            elif event == "error" and not ready.done():
                self.last_error = str(msg.get("message", "worker failed to start"))
                ready.set_exception(WorkerError(self.last_error))
            elif "id" in msg:
                with self._lock:
                    fut = self._pending.pop(msg["id"], None)
                if fut is not None and not fut.done():
                    fut.set_result(msg)
        # Process ended: fail everything still waiting on it.
        reason = f"{self.kind} worker exited (code {proc.poll()}); see tom_logs/voice_{self.kind}_worker.log"
        if not ready.done():
            ready.set_exception(WorkerError(self.last_error or reason))
        with self._lock:
            pending, self._pending = self._pending, {}
        for fut in pending.values():
            if not fut.done():
                fut.set_exception(WorkerError(reason))

    def stop(self) -> None:
        with self._lock:
            proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            if proc.poll() is None and proc.stdin:
                proc.stdin.write(json.dumps({"op": "shutdown"}) + "\n")
                proc.stdin.flush()
                proc.wait(timeout=3)
        except Exception:
            pass
        if proc.poll() is None:
            proc.kill()

    # ── requests ─────────────────────────────────────────────────────────
    def request(self, op: str, timeout: float = 60.0, **args: Any) -> Dict[str, Any]:
        """Send one request; restart the worker once if it has died. Raises WorkerError."""
        for attempt in (1, 2):
            self.start()
            fut: Future = Future()
            with self._lock:
                proc = self._proc
                req_id = next(self._ids)
                self._pending[req_id] = fut
            try:
                assert proc is not None and proc.stdin is not None
                proc.stdin.write(json.dumps({"id": req_id, "op": op, **args}) + "\n")
                proc.stdin.flush()
                reply = fut.result(timeout=timeout)
            except FutureTimeout:
                with self._lock:
                    self._pending.pop(req_id, None)
                raise WorkerError(f"{self.kind} worker did not answer '{op}' within {timeout:.0f}s") from None
            except (OSError, ValueError, WorkerError) as exc:   # broken pipe / dead worker
                with self._lock:
                    self._pending.pop(req_id, None)
                self.stop()
                if attempt == 2:
                    raise WorkerError(str(exc)) from None
                continue
            if not reply.get("ok"):
                raise WorkerError(str(reply.get("error", f"{op} failed")))
            return reply
        raise WorkerError("unreachable")


def serve(handle, ready_info: Dict[str, Any]) -> None:
    """Worker-side loop: announce ready, then answer requests from stdin until shutdown/EOF.

    `handle(op, args) -> dict` returns the reply fields; exceptions become ok=false replies.
    Only protocol lines go to the real stdout — callers redirect fd 1 to stderr before importing
    native libraries (see protocol_stdout) so library prints can't corrupt the stream.
    """
    out = protocol_stdout()
    _emit(out, {"event": "ready", **ready_info})
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        op = msg.pop("op", "")
        if op == "shutdown":
            break
        req_id = msg.pop("id", None)
        try:
            reply = {"id": req_id, "ok": True, **(handle(op, msg) or {})}
        except Exception as exc:  # report, keep serving
            reply = {"id": req_id, "ok": False, "error": f"{type(exc).__name__}: {exc}"}
        _emit(out, reply)


_PROTOCOL_OUT = None


def protocol_stdout():
    """A private handle on the original stdout; fd 1 itself is pointed at stderr afterwards."""
    global _PROTOCOL_OUT
    if _PROTOCOL_OUT is None:
        sys.stdout.flush()
        _PROTOCOL_OUT = os.fdopen(os.dup(1), "w", encoding="utf-8", buffering=1)
        os.dup2(2, 1)
        sys.stdout = sys.stderr
    return _PROTOCOL_OUT


def fail_startup(message: str) -> None:
    _emit(protocol_stdout(), {"event": "error", "message": message})
    sys.exit(1)


def _emit(out, obj: Dict[str, Any]) -> None:
    out.write(json.dumps(obj, ensure_ascii=False) + "\n")
    out.flush()
