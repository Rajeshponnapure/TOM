from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


class InstagramAgentController:
    """Manage the standalone Instagram daemon process."""

    def __init__(self) -> None:
        root_dir = Path(__file__).resolve().parents[1]
        self.root_dir = root_dir
        self.script_path = root_dir / "agents" / "instagram_ai_news_agent" / "main.py"
        self.state_file = root_dir / "tom_logs" / "instagram_agent_state.json"
        self.pid_file = root_dir / "tom_logs" / "instagram_agent.pid"

    def _read_json(self, path: Path) -> Dict[str, Any]:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _pid_running(self, pid: int) -> bool:
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
            "last_run_at": state.get("last_run_at"),
            "next_run_at": state.get("next_run_at"),
            "posts_extracted": state.get("posts_extracted", 0),
            "ai_posts_found": state.get("ai_posts_found", 0),
            "report_generated": state.get("report_generated", False),
            "email_sent": state.get("email_sent", False),
            "report_path": state.get("report_path"),
            "errors": state.get("errors", []),
            "recent_runs": state.get("recent_runs", []),
        }

    def start(self) -> Dict[str, Any]:
        current = self.status()
        if current["running"]:
            return {
                "status": "already_running",
                "message": f"Instagram agent is already running (PID {current['pid']}).",
                "runtime_state": current,
            }

        if not self.script_path.exists():
            return {
                "status": "error",
                "message": f"Instagram agent entrypoint not found: {self.script_path}",
            }

        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

        process = subprocess.Popen(
            [sys.executable, str(self.script_path), "--daemon"],
            cwd=str(self.root_dir),
            env=os.environ.copy(),
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
            "message": f"Instagram agent started in the background (PID {process.pid}).",
            "pid": process.pid,
            "runtime_state": self.status(),
        }

    def stop(self) -> Dict[str, Any]:
        current = self.status()
        if not current["running"]:
            return {
                "status": "not_running",
                "message": "Instagram agent is not running.",
                "runtime_state": current,
            }

        pid = current.get("pid")
        if pid is None:
            return {
                "status": "error",
                "message": "Instagram agent PID is unavailable.",
            }

        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, capture_output=True, text=True)
            else:
                os.kill(pid, signal.SIGTERM)
        except Exception as exc:
            return {
                "status": "error",
                "message": f"Failed to stop Instagram agent: {exc}",
            }

        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
        except Exception:
            pass

        return {
            "status": "stopped",
            "message": f"Instagram agent stop requested for PID {pid}.",
            "runtime_state": self.status(),
        }

    def summary(self) -> Dict[str, Any]:
        current = self.status()
        message_lines = [
            f"Running: {'yes' if current.get('running') else 'no'}",
            f"Last run: {current.get('last_run_at') or 'never'}",
            f"Posts extracted: {current.get('posts_extracted', 0)}",
            f"AI posts found: {current.get('ai_posts_found', 0)}",
            f"Report generated: {'yes' if current.get('report_generated') else 'no'}",
            f"Email sent: {'yes' if current.get('email_sent') else 'no'}",
            f"Report path: {current.get('report_path') or 'N/A'}",
        ]

        errors = current.get("errors", []) or []
        if errors:
            message_lines.append("Errors:")
            message_lines.extend([f"- {err}" for err in errors[:5]])

        return {
            "status": current.get("status", "unknown"),
            "running": current.get("running", False),
            "message": "\n".join(message_lines),
            "last_run_at": current.get("last_run_at"),
            "next_run_at": current.get("next_run_at"),
            "report_path": current.get("report_path"),
            "recent_runs": current.get("recent_runs", []),
        }
