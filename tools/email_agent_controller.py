from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional


class EmailAgentController:
    """Start, stop, and inspect the standalone email-agent process."""

    def __init__(self) -> None:
        root_dir = Path(__file__).resolve().parents[1]
        self.root_dir = root_dir
        self.script_path = root_dir / "agents" / "email_agent" / "main.py"
        self.state_file = root_dir / "tom_logs" / "email_agent_state.json"
        self.pid_file = root_dir / "tom_logs" / "email_agent.pid"

    def _read_json(self, path: Path) -> Dict[str, Any]:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _pid_running(self, pid: int) -> bool:
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            try:
                result = subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        f"if (Get-Process -Id {pid} -ErrorAction SilentlyContinue) {{ exit 0 }} else {{ exit 1 }}",
                    ],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=creationflags,
                )
                if result.returncode == 0:
                    return True
            except Exception:
                pass
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                return str(pid) in result.stdout
            except Exception:
                return False
        try:
            os.kill(pid, 0)
            return True
        except Exception:
            return False

    def _read_pid(self) -> Optional[int]:
        try:
            if self.pid_file.exists():
                return int(self.pid_file.read_text(encoding="utf-8").strip())
        except Exception:
            return None
        return None

    def status(self) -> Dict[str, Any]:
        pid = self._read_pid()
        running = bool(pid and self._pid_running(pid))
        if not running and self.pid_file.exists():
            try:
                self.pid_file.unlink()
            except Exception:
                pass

        state = self._read_json(self.state_file)
        return {
            "status": state.get("status", "idle" if not running else "running"),
            "running": running,
            "pid": pid,
            "provider": state.get("provider"),
            "last_run_at": state.get("last_run_at"),
            "next_run_at": state.get("next_run_at"),
            "emails_reviewed": state.get("emails_reviewed", 0),
            "important_count": state.get("important_count", 0),
            "low_priority_count": state.get("low_priority_count", 0),
            "draft_reply_count": state.get("draft_reply_count", 0),
            "auto_replied_count": state.get("auto_replied_count", 0),
            "summary_lines": state.get("summary_lines", []),
            "main_screen_items": state.get("main_screen_items", []),
            "recent_runs": state.get("recent_runs", []),
            "message": state.get("message", ""),
        }

    def start(self) -> Dict[str, Any]:
        current = self.status()
        if current["running"]:
            return {
                "status": "already_running",
                "message": f"Email agent is already running (PID {current['pid']}).",
                **current,
            }

        if not self.script_path.exists():
            return {
                "status": "error",
                "message": f"Email agent entrypoint not found: {self.script_path}",
            }

        env = os.environ.copy()
        env.setdefault("EMAIL_AGENT_DAEMON", "true")

        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

        process = subprocess.Popen(
            [sys.executable, str(self.script_path), "--daemon"],
            cwd=str(self.root_dir),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
        )

        try:
            self.pid_file.parent.mkdir(parents=True, exist_ok=True)
            self.pid_file.write_text(str(process.pid), encoding="utf-8")
        except Exception:
            pass

        return {
            "status": "started",
            "message": f"Email agent started in the background (PID {process.pid}).",
            "pid": process.pid,
            "runtime_state": self.status(),
        }

    def stop(self) -> Dict[str, Any]:
        current = self.status()
        if not current["running"]:
            return {
                **current,
                "status": "not_running",
                "message": "Email agent is not running.",
            }

        pid = current.get("pid")
        if pid is None:
            return {
                "status": "error",
                "message": "Email agent PID is unavailable.",
            }

        try:
            if os.name == "nt":
                result = subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                time.sleep(0.5)
                if self._pid_running(pid):
                    detail = (result.stderr or result.stdout or "process still running").strip()
                    return {
                        "status": "error",
                        "message": f"Failed to stop email agent PID {pid}: {detail}",
                        "pid": pid,
                        "running": True,
                    }
            else:
                os.kill(pid, signal.SIGTERM)
        except Exception as exc:
            return {
                "status": "error",
                "message": f"Failed to stop email agent: {exc}",
            }

        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
        except Exception:
            pass

        return {
            "status": "stopped",
            "message": f"Email agent stop requested for PID {pid}.",
            "runtime_state": self.status(),
        }

    def summary(self) -> Dict[str, Any]:
        current = self.status()
        summary_lines = current.get("summary_lines", [])
        main_screen_items = current.get("main_screen_items", [])

        message_lines = [
            f"Running: {'yes' if current.get('running') else 'no'}",
            f"Last run: {current.get('last_run_at') or 'never'}",
            f"Emails reviewed: {current.get('emails_reviewed', 0)}",
            f"Important emails: {current.get('important_count', 0)}",
            f"Spam emails: {current.get('spam_count', current.get('low_priority_count', 0))}",
            f"Draft replies: {current.get('draft_reply_count', 0)}",
            f"Auto replied: {current.get('auto_replied_count', 0)}",
        ]

        if summary_lines:
            message_lines.append("Summary:")
            message_lines.extend([f"- {line}" for line in summary_lines])

        return {
            "status": current.get("status", "unknown"),
            "running": current.get("running", False),
            "message": "\n".join(message_lines),
            "main_screen_items": main_screen_items,
            "recent_runs": current.get("recent_runs", []),
            "last_run_at": current.get("last_run_at"),
            "next_run_at": current.get("next_run_at"),
        }
