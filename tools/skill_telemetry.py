"""Skill usage telemetry for TOM.

Tracks which routed skills are actually used and whether the execution
completed, failed, or degraded. This keeps capability reports grounded in
runtime evidence instead of static files alone.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from tools.project_paths import project_path


class SkillTelemetry:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else project_path("tom_logs", "skill_usage.json")

    def _now(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "skills": {}}
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("skills"), dict):
                return data
        except Exception:
            pass
        return {"version": 1, "skills": {}}

    def _save(self, data: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=str(self.path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, sort_keys=True)
            os.replace(tmp_name, self.path)
        finally:
            if os.path.exists(tmp_name):
                try:
                    os.remove(tmp_name)
                except OSError:
                    pass

    @staticmethod
    def _preview(command: str, limit: int = 180) -> str:
        compact = " ".join(str(command).split())
        return compact[:limit]

    def record_route(
        self,
        skill_name: str,
        execution_mode: str,
        status: str,
        elapsed_seconds: float = 0.0,
        failure_reason: str = "",
        command: str = "",
    ) -> None:
        if not skill_name:
            return
        data = self._load()
        skills = data.setdefault("skills", {})
        entry = skills.setdefault(
            skill_name,
            {
                "execution_mode": execution_mode,
                "routed_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "total_runtime_seconds": 0.0,
                "last_used_at": "",
                "last_status": "",
                "last_failure_reason": "",
                "last_command": "",
            },
        )
        entry["execution_mode"] = execution_mode
        entry["routed_count"] = int(entry.get("routed_count", 0)) + 1
        if status == "success":
            entry["success_count"] = int(entry.get("success_count", 0)) + 1
        else:
            entry["failure_count"] = int(entry.get("failure_count", 0)) + 1
        entry["total_runtime_seconds"] = round(
            float(entry.get("total_runtime_seconds", 0.0)) + max(0.0, float(elapsed_seconds)),
            3,
        )
        entry["last_used_at"] = self._now()
        entry["last_status"] = status
        entry["last_failure_reason"] = failure_reason[:300]
        entry["last_command"] = self._preview(command)
        self._save(data)

    def summary(self, limit: int = 20) -> Dict[str, Any]:
        data = self._load()
        rows: List[Dict[str, Any]] = []
        for name, entry in data.get("skills", {}).items():
            routed = int(entry.get("routed_count", 0))
            success = int(entry.get("success_count", 0))
            failures = int(entry.get("failure_count", 0))
            rows.append(
                {
                    "skill": name,
                    "execution_mode": entry.get("execution_mode", "unknown"),
                    "routed_count": routed,
                    "success_count": success,
                    "failure_count": failures,
                    "success_rate": round((success / routed) * 100, 1) if routed else 0.0,
                    "last_used_at": entry.get("last_used_at", ""),
                    "last_status": entry.get("last_status", ""),
                    "last_failure_reason": entry.get("last_failure_reason", ""),
                    "last_command": entry.get("last_command", ""),
                }
            )
        rows.sort(key=lambda r: (-r["routed_count"], r["skill"]))
        return {
            "tracked_skills": len(rows),
            "total_routes": sum(r["routed_count"] for r in rows),
            "skills": rows[:limit],
            "path": str(self.path),
        }

    def format_summary(self, limit: int = 20) -> str:
        report = self.summary(limit=limit)
        lines = [
            "Skill usage telemetry",
            f"Tracked skills: {report['tracked_skills']}",
            f"Total routed skill uses: {report['total_routes']}",
            f"Store: {report['path']}",
            "",
        ]
        if not report["skills"]:
            lines.append("No skill routes have been recorded yet.")
            return "\n".join(lines)
        lines.append("| Skill | Mode | Routes | Success | Fail | Success Rate | Last Status |")
        lines.append("|---|---|---:|---:|---:|---:|---|")
        for row in report["skills"]:
            lines.append(
                f"| {row['skill']} | {row['execution_mode']} | {row['routed_count']} | "
                f"{row['success_count']} | {row['failure_count']} | "
                f"{row['success_rate']}% | {row['last_status']} |"
            )
        return "\n".join(lines)
