"""
TOM Autonomous Agent — Self-Planning, Researching, Working, and Verification System.
Tom can break down complex tasks, research solutions, execute subtasks,
verify results, and learn from outcomes — all autonomously.
"""
import asyncio
import json
import os
import time
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

try:
    from tools.skill_manager import SkillManager
except ImportError:
    SkillManager = None

from tools.project_paths import project_path_str


class AutonomousAgent:
    """
    Self-directed autonomous agent that:
    1. Plans: decomposes complex tasks into subtasks
    2. Researches: gathers information from web, knowledge base, tools
    3. Executes: runs subtasks with appropriate tools
    4. Verifies: checks results and iterates if needed
    5. Learns: stores outcomes for future improvement
    """

    def __init__(self, tom_agent=None, llm=None, skill_manager: SkillManager = None):
        self.tom_agent = tom_agent
        self.llm = llm
        self.skill_manager = skill_manager

        self._work_dir = project_path_str("tom_brain", "autonomous")
        os.makedirs(self._work_dir, exist_ok=True)

        self._session_log: List[Dict] = []
        self._current_task: Optional[Dict] = None
        self._subtasks: List[Dict] = []
        self._completed_subtasks: List[Dict] = []

    async def execute(self, task_description: str, context: Dict = None) -> Dict[str, Any]:
        """
        Main entry point: plan → research → execute → verify → reflect.
        """
        start_time = time.time()

        # Phase 1: Plan
        plan = await self._plan(task_description, context or {})
        self._current_task = plan

        # Phase 2: Research (for each subtask that needs it)
        for subtask in plan.get("subtasks", []):
            if subtask.get("needs_research", False):
                research = await self._research(subtask)
                subtask["research"] = research

        # Phase 3: Execute subtasks
        results = []
        for subtask in plan.get("subtasks", []):
            result = await self._execute_subtask(subtask)
            results.append(result)
            self._completed_subtasks.append(result)

            # Phase 4: Verify
            if not result.get("skipped", False):
                verification = await self._verify(subtask, result)
                result["verification"] = verification

                if not verification.get("passed", True) and result.get("retries", 0) < 2:
                    result["retries"] = result.get("retries", 0) + 1
                    retry_result = await self._execute_subtask(subtask, retry=True)
                    retry_result["retries"] = result["retries"]
                    retry_result["verification"] = await self._verify(subtask, retry_result)
                    results[-1] = retry_result

        # Phase 5: Reflect & Learn
        final_result = {
            "status": "completed",
            "task": task_description,
            "subtasks_count": len(plan.get("subtasks", [])),
            "completed_count": len(results),
            "duration_seconds": round(time.time() - start_time, 1),
            "subtasks": results,
            "reflection": await self._reflect(task_description, plan, results),
        }

        self._session_log.append(final_result)
        self._save_session()

        return final_result

    async def _plan(self, task: str, context: Dict) -> Dict[str, Any]:
        """Decompose a complex task into structured subtasks."""
        subtasks = []

        if self.llm:
            prompt = f"""You are TOM's planning engine. Break this task into subtasks:

Task: {task}
Context: {json.dumps(context, indent=2)[:500]}

Return a JSON list of subtasks, each with:
- "id": unique number
- "description": what to do
- "tool_needed": which tool (web_search, file_io, code, browser, email, document, data_analysis, voice, system, analyze_file, ask_user)
- "needs_research": true/false
- "depends_on": list of subtask IDs this depends on
- "success_criteria": how to verify success

Output ONLY valid JSON array, no other text."""
            try:
                response = await self.llm.agenerate([prompt])
                text = response.generations[0][0].text.strip()
                # Extract JSON array
                import re
                json_match = re.search(r"\[.*\]", text, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    if isinstance(parsed, list):
                        subtasks = parsed
            except Exception:
                pass

        if not subtasks:
            subtasks = [{
                "id": 1, "description": task,
                "tool_needed": "ask_user",
                "needs_research": False,
                "depends_on": [],
                "success_criteria": "Task completed successfully"
            }]

        return {"original_task": task, "subtasks": subtasks}

    async def _research(self, subtask: Dict) -> Dict[str, Any]:
        """Research information needed for a subtask."""
        result = {"sources": [], "summary": ""}

        description = subtask.get("description", "")
        query = f"How to {description}"[:200]

        # Web search
        if self.tom_agent and hasattr(self.tom_agent, "search_web"):
            try:
                search_result = await self.tom_agent.search_web(query)
                if isinstance(search_result, dict):
                    result["sources"] = search_result.get("results", [])
                    result["summary"] = search_result.get("summary", "")
            except Exception:
                pass

        # LLM knowledge
        if self.llm:
            try:
                prompt = f"Research topic: {description}\nProvide a concise summary of key information needed."
                response = await self.llm.agenerate([prompt])
                knowledge = response.generations[0][0].text.strip()
                if knowledge:
                    result["llm_knowledge"] = knowledge
            except Exception:
                pass

        return result

    async def _execute_subtask(self, subtask: Dict, retry: bool = False) -> Dict[str, Any]:
        """Execute a single subtask using the appropriate tool."""
        result = {
            "subtask_id": subtask.get("id"),
            "description": subtask.get("description"),
            "status": "pending",
            "output": "",
            "error": None,
            "retries": 0,
        }

        tool = subtask.get("tool_needed", "ask_user")
        description = subtask.get("description", "")

        try:
            if tool == "web_search" and self.tom_agent:
                out = await self.tom_agent.search_web(description)
                result["output"] = str(out.get("summary", out))[:2000]
                result["status"] = "completed"

            elif tool == "data_analysis":
                out = await self.tom_agent.execute_task(f"Analyze data: {description}")
                result["output"] = str(out.get("message", out))[:2000]
                result["status"] = "completed"

            elif tool == "document" and self.tom_agent:
                out = await self.tom_agent.execute_task(f"Create document: {description}")
                result["output"] = str(out.get("message", out))[:2000]
                result["status"] = "completed"

            elif tool == "code":
                out = await self.tom_agent.execute_task(f"Write code: {description}")
                result["output"] = str(out.get("message", out))[:2000]
                result["status"] = "completed"

            elif tool == "browser" and self.tom_agent:
                out = await self.tom_agent.execute_task(f"Browse web: {description}")
                result["output"] = str(out.get("message", out))[:2000]
                result["status"] = "completed"

            elif tool == "email" and self.tom_agent:
                out = await self.tom_agent.execute_task(f"Handle email: {description}")
                result["output"] = str(out.get("message", out))[:2000]
                result["status"] = "completed"

            elif tool == "analyze_file" and self.tom_agent:
                out = await self.tom_agent.execute_task(f"Analyze file: {description}")
                result["output"] = str(out.get("message", out))[:2000]
                result["status"] = "completed"

            elif tool == "system":
                out = await self.tom_agent.execute_task(f"System: {description}")
                result["output"] = str(out.get("message", out))[:2000]
                result["status"] = "completed"

            else:
                # Use LLM for general reasoning
                if self.llm:
                    prompt = f"Task: {description}\nProvide a detailed solution or answer."
                    response = await self.llm.agenerate([prompt])
                    result["output"] = response.generations[0][0].text.strip()[:2000]
                    result["status"] = "completed"
                else:
                    result["status"] = "skipped"
                    result["output"] = "No LLM or tools available for this subtask"

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)[:500]

        return result

    async def _verify(self, subtask: Dict, result: Dict) -> Dict[str, Any]:
        """Verify that a subtask was completed successfully."""
        verification = {"passed": True, "checks": [], "issues": []}

        if result.get("status") == "failed":
            verification["passed"] = False
            verification["issues"].append("Subtask execution failed")
            return verification

        criteria = subtask.get("success_criteria", "")
        if criteria and self.llm:
            try:
                prompt = f"""Verify this result:
Task: {subtask.get('description')}
Success Criteria: {criteria}
Output: {result.get('output', '')[:1000]}

Does the output satisfy the success criteria? Answer only: PASS or FAIL + brief reason."""
                response = await self.llm.agenerate([prompt])
                text = response.generations[0][0].text.strip()
                if text.startswith("FAIL"):
                    verification["passed"] = False
                    verification["issues"].append(text)
                verification["checks"].append(text[:200])
            except Exception:
                verification["checks"].append("Verification skipped (LLM error)")

        return verification

    async def _reflect(self, task: str, plan: Dict, results: List[Dict]) -> str:
        """Reflect on the overall execution and extract learnings."""
        if not self.llm:
            return "Reflection requires LLM"

        summary = {
            "total": len(results),
            "completed": sum(1 for r in results if r.get("status") == "completed"),
            "failed": sum(1 for r in results if r.get("status") == "failed"),
            "skipped": sum(1 for r in results if r.get("status") == "skipped"),
        }

        prompt = f"""Reflect on this autonomous task execution:

Task: {task}
Results: {json.dumps(summary)}
Plan had {len(plan.get('subtasks', []))} subtasks.

Provide a brief reflection: what went well, what could be improved, and key learnings."""
        try:
            response = await self.llm.agenerate([prompt])
            return response.generations[0][0].text.strip()[:500]
        except Exception:
            return "Reflection completed (no LLM feedback)"

    def _save_session(self):
        """Save session log for learning."""
        path = os.path.join(self._work_dir, "autonomous_sessions.json")
        try:
            existing = []
            if os.path.exists(path):
                with open(path, "r") as f:
                    existing = json.load(f)
            existing.append({
                "timestamp": datetime.now().isoformat(),
                "task": self._current_task.get("original_task", "") if self._current_task else "",
                "summary": {
                    "subtasks": len(self._subtasks),
                    "completed": len(self._completed_subtasks),
                }
            })
            existing = existing[-50:]  # keep last 50
            with open(path, "w") as f:
                json.dump(existing, f, indent=2)
        except Exception:
            pass

    def get_stats(self) -> Dict[str, Any]:
        """Get autonomous agent statistics."""
        return {
            "sessions": len(self._session_log),
            "current_task": self._current_task.get("original_task") if self._current_task else None,
            "subtasks_pending": len(self._subtasks) - len(self._completed_subtasks),
            "subtasks_completed": len(self._completed_subtasks),
        }
