"""
TOM Autonomous Agent — plan a goal as typed tool calls, run them under the policy engine, report.

It used to plan with free-form "tool_needed" names the executor did not know, so most steps fell
back to the model *describing* how to do the task (owner report 2026-10-21: "list the 3 largest
files in the workspace" → 21 s of "how to open a folder" instructions). Now it is a thin wrapper
around tom_core.planning: the plan may only use registered tools (tom_core.tools.builtin), every
step passes schema validation, the policy engine and its timeout, and the report says exactly
which steps succeeded, failed, were skipped or could not be verified.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from tools.project_paths import project_path_str


class AutonomousAgent:
    def __init__(self, tom_agent=None, llm=None, skill_manager=None):
        self.tom_agent = tom_agent
        self.llm = llm
        self.skill_manager = skill_manager
        self._work_dir = project_path_str("tom_brain", "autonomous")
        os.makedirs(self._work_dir, exist_ok=True)
        self._session_log: List[Dict[str, Any]] = []
        self._current_task: Optional[str] = None

    async def _ask(self, system: str, user: str) -> str:
        """One model call; both texts are passed as values, so JSON braces in them are safe."""
        agent = self.tom_agent
        if agent is not None and hasattr(agent, "_invoke_llm"):
            # Not agent._safe_prompt: it escapes braces in system text, which would turn the
            # {system} placeholder itself into literal text.
            from langchain_core.prompts import ChatPromptTemplate
            prompt = ChatPromptTemplate.from_messages([("system", "{system}"), ("user", "{user}")])
            resp = await agent._invoke_llm(prompt, {"system": system, "user": user}, "autonomous_plan",
                                           getattr(agent, "llm", None))
            return getattr(resp, "content", "") or ""
        if self.llm is not None:
            from langchain_core.messages import HumanMessage, SystemMessage
            resp = await self.llm.ainvoke([SystemMessage(content=system), HumanMessage(content=user)])
            return getattr(resp, "content", "") or ""
        raise RuntimeError("No model is available to plan with.")

    async def execute(self, task_description: str, context: Optional[Dict] = None,
                      allowed: Optional[List[str]] = None) -> Dict[str, Any]:
        from tom_core.planning import run_goal
        from tom_core.tools.registry import get_registry

        self._current_task = task_description
        ctx = json.dumps(context, default=str)[:800] if context else ""
        report = await run_goal(task_description, self._ask, get_registry(), allowed=allowed, context=ctx,
                                checkpoint=self._checkpointer())
        return self._result(task_description, report)

    def _store(self):
        tasks = getattr(self.tom_agent, "tasks", None)
        return getattr(tasks, "store", None)

    def _checkpointer(self):
        """Each plan and step outcome goes into the task's event log (R4), so an interrupted run
        can be resumed without repeating finished steps or blindly redoing a half-done one."""
        from tom_core.tasks.service import current_task_id
        store, task_id = self._store(), current_task_id()
        if store is None or not task_id:
            return None
        return lambda kind, data: store.add_event(task_id, f"plan_{kind}", json.dumps(data, default=str))

    async def resume(self, task_id: str) -> Dict[str, Any]:
        """Continue an interrupted Autonomous run from its checkpoint."""
        from tom_core.planning.planner import Executor, restore_from_events
        from tom_core.tools.registry import get_registry
        store = self._store()
        rec = store.get(task_id) if store is not None else None
        if rec is None:
            return {"status": "error", "message": f"No task {task_id} to resume."}
        plan, previous = restore_from_events(rec.events)
        if plan is None:
            return {"status": "needs_input", "message": "That task has no readable plan checkpoint; ask again."}
        report = await Executor(get_registry(), checkpoint=self._checkpointer()).run(plan, previous=previous)
        return self._result(plan.goal, report)

    def _result(self, task_description: str, report) -> Dict[str, Any]:
        result = {
            "status": report.status if report.status != "partial" else "error",
            "partial": report.status == "partial",
            "message": report.text(),
            "task": task_description,
            "duration_seconds": round(report.seconds, 1),
            "steps": [{"id": r.step.id, "tool": r.step.tool, "args": r.step.args, "status": r.status,
                       "message": r.message[:500], "evidence": r.evidence} for r in report.results],
            # Only verified steps count as done (FR-008); the engine router re-checks declared paths.
            "verified": bool(report.results) and all(r.status == "succeeded" for r in report.results),
        }
        paths = [r.raw.get("path") for r in report.results if r.status == "succeeded" and r.raw.get("path")]
        if paths:
            result["paths"] = paths
        self._session_log.append({"task": task_description, "status": result["status"]})
        self._save_session(result)
        return result

    def _save_session(self, result: Dict[str, Any]) -> None:
        path = os.path.join(self._work_dir, "autonomous_sessions.json")
        try:
            existing = []
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            existing.append({"timestamp": datetime.now().isoformat(), "task": result.get("task", ""),
                             "status": result.get("status"), "steps": len(result.get("steps", []))})
            with open(path, "w", encoding="utf-8") as f:
                json.dump(existing[-50:], f, indent=2)
        except Exception:
            pass

    def get_stats(self) -> Dict[str, Any]:
        return {"sessions": len(self._session_log), "current_task": self._current_task,
                "last": self._session_log[-1] if self._session_log else None, "time": time.time()}
