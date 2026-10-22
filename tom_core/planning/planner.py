"""Plan a goal as typed tool calls, run them through the registry, report honestly (PRD §13, FR-004/008).

    plan = await Planner(ask, registry).plan("list the 3 largest files in my Downloads")
    report = await Executor(registry).run(plan)

* The planner may only use tools from the registry (optionally a role's granted subset); a step is
  {tool, args, why, expect, depends_on}. A later step can use an earlier step's text with "{{N}}".
* The executor runs each step through ToolRegistry.call — schema validation, policy gate (approval
  where needed), timeout — and never runs a step whose dependency failed.
* The report separates completed, failed, unverified and skipped steps (§13 step 10). The overall
  status is "success" only when every step succeeded; a write that reported success without
  verification evidence is "unverified", never "done".
Replaced the old AutonomousAgent behaviour, where steps with unknown tool names fell back to the
model *describing* how to do the task (owner report 2026-10-21: "list the 3 largest files" gave
21 s of "how to open a folder" instructions).
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

from tom_core.llm_json import parse_model_json
from tom_core.tools.registry import ToolRegistry

Ask = Callable[[str, str], Awaitable[str]]          # (system, user) -> model text

MAX_STEPS = 6
_REF = re.compile(r"\{\{\s*(\d+)\s*\}\}")


@dataclass
class Step:
    id: int
    tool: str
    args: Dict[str, Any] = field(default_factory=dict)
    why: str = ""
    expect: str = ""
    depends_on: List[int] = field(default_factory=list)


@dataclass
class Plan:
    goal: str
    steps: List[Step]
    note: str = ""                                   # e.g. why nothing could be planned


@dataclass
class StepResult:
    step: Step
    status: str                                      # succeeded | unverified | failed | skipped
    message: str = ""
    evidence: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Report:
    goal: str
    results: List[StepResult]
    seconds: float
    note: str = ""

    @property
    def status(self) -> str:
        if not self.results:
            return "needs_input"
        if all(r.status == "succeeded" for r in self.results):
            return "success"
        if any(r.status == "failed" for r in self.results):
            return "error" if not any(r.status == "succeeded" for r in self.results) else "partial"
        return "unverified"

    def text(self) -> str:
        if not self.results:
            return self.note or "I could not turn that into steps I can actually do."
        icons = {"succeeded": "done", "unverified": "done, not verified", "failed": "FAILED", "skipped": "skipped"}
        lines = [f"Plan for: {self.goal}"]
        for r in self.results:
            lines.append(f"{r.step.id}. [{icons[r.status]}] {r.step.tool} — {r.step.why or r.step.expect}")
            if r.message:
                body = r.message.strip().replace("\n", "\n     ")
                lines.append(f"     {body[:900]}")
        counts = {k: sum(1 for r in self.results if r.status == k) for k in icons}
        lines.append("Result: " + ", ".join(f"{v} {k}" for k, v in counts.items() if v) + f" ({self.seconds:.1f}s)")
        return "\n".join(lines)


_PLAN_SYSTEM = (
    "You turn a user's goal into a short plan of tool calls for TOM, a Windows assistant. "
    "Use ONLY these tools, exactly as named, with arguments matching their parameters:\n{tools}\n\n"
    "Rules: at most {max_steps} steps; use paths exactly as the user gives them, written with forward "
    "slashes (C:/Users/x/file.txt); only when the user names a known folder without a path use: home "
    "{home}, Desktop {desktop}, Downloads {downloads}; save NEW files in TOM's workspace {workspace} "
    "unless the user names another place; a later step may use an earlier step's output by "
    "writing {{{{N}}}} inside a string argument (N = step id); never invent tools; if the goal "
    "cannot be done with these tools, return an empty plan and say why in \"note\".\n"
    "Return ONLY JSON: {{\"steps\": [{{\"id\": 1, \"tool\": \"...\", \"args\": {{...}}, "
    "\"why\": \"...\", \"expect\": \"...\", \"depends_on\": []}}], \"note\": \"\"}}"
)


def _known_folders() -> Dict[str, str]:
    import os
    home = os.path.expanduser("~")
    desktop = os.path.join(os.environ.get("OneDrive", home), "Desktop")
    if not os.path.isdir(desktop):
        desktop = os.path.join(home, "Desktop")
    from tools.project_paths import workspace_root
    return {k: v.replace("\\", "/") for k, v in {
        "home": home, "desktop": desktop, "downloads": os.path.join(home, "Downloads"),
        "workspace": str(workspace_root())}.items()}


def _parse_json(text: str) -> Any:
    return parse_model_json(text)


_PATH_KEYS = {"path", "src", "dst", "repo", "cwd", "folder"}
_CONTROL = {"\t": "\\t", "\n": "\\n", "\r": "\\r", "\b": "\\b", "\f": "\\f"}
_DRIVE = re.compile(r"[A-Za-z]:[\\/]")


def _clean_path(value: Any) -> Any:
    """Undo the two ways small models mangle Windows paths: JSON escapes eaten out of single
    backslashes (C:\\tmp → C:<TAB>mp), and a full path glued onto a base folder (Desktop\\C:\\tmp)."""
    if not isinstance(value, str):
        return value
    for ch, esc in _CONTROL.items():
        value = value.replace(ch, esc)
    drives = list(_DRIVE.finditer(value))
    if len(drives) > 1:
        value = value[drives[-1].start():]
    return value


def _clean_args(args: Dict[str, Any]) -> Dict[str, Any]:
    return {k: (_clean_path(v) if k in _PATH_KEYS else v) for k, v in args.items()}


class Planner:
    def __init__(self, ask: Ask, registry: ToolRegistry, allowed: Optional[Iterable[str]] = None,
                 max_steps: int = MAX_STEPS) -> None:
        self.ask = ask
        self.registry = registry
        self.allowed = list(allowed) if allowed is not None else None
        self.max_steps = max_steps

    async def plan(self, goal: str, context: str = "") -> Plan:
        names = set(self.allowed or self.registry.names())
        # Small models cut dotted names ("fs.largest_files" -> "fs"); they copy underscore names.
        alias = {n.replace(".", "_"): n for n in names}
        tools = self.registry.catalogue(self.allowed)
        for a, n in alias.items():
            tools = tools.replace(f"{n}(", f"{a}(")
        system = _PLAN_SYSTEM.format(tools=tools, max_steps=self.max_steps, **_known_folders())
        user = f"Goal: {goal}" + (f"\n\nContext:\n{context}" if context else "")
        data, error = None, None
        for attempt in range(2):                    # one retry: small models sometimes break the JSON
            try:
                data = _parse_json(await self.ask(system, user if attempt == 0 else
                                                  user + "\n\nYour last answer was not valid JSON. Reply with the JSON only."))
                break
            except Exception as exc:
                error = exc
        if data is None:
            return Plan(goal, [], note=f"The planner's answer could not be read ({type(error).__name__}).")
        if isinstance(data, list):                  # a bare list of steps
            data = {"steps": data}
        if not isinstance(data, dict):
            data = {}
        steps, dropped = [], []
        for i, raw in enumerate((data or {}).get("steps") or [], 1):
            if isinstance(raw, dict) and raw.get("tool") in alias:
                raw["tool"] = alias[raw["tool"]]
            if not isinstance(raw, dict) or raw.get("tool") not in names:
                dropped.append(str(raw.get("tool") if isinstance(raw, dict) else raw)[:40])
                continue                                    # unknown or ungranted tool: dropped, not guessed
            steps.append(Step(id=int(raw.get("id") or i), tool=raw["tool"],
                              args=_clean_args(raw["args"]) if isinstance(raw.get("args"), dict) else {},
                              why=str(raw.get("why", ""))[:200], expect=str(raw.get("expect", ""))[:200],
                              depends_on=[int(d) for d in raw.get("depends_on") or [] if str(d).isdigit()]))
            if len(steps) >= self.max_steps:
                break
        note = str((data or {}).get("note", ""))[:400] if isinstance(data, dict) else ""
        if not steps and dropped:
            note = (f"The plan used tools TOM does not have ({', '.join(dropped)}), so nothing was run. "
                    + note).strip()
        elif not steps and (not note or note.lower().startswith("goal")):
            note = "No available tool fits this request, so nothing was run."
        return Plan(goal, steps, note=note)


class Executor:
    def __init__(self, registry: ToolRegistry, allowed: Optional[Iterable[str]] = None,
                 budget_seconds: float = 600.0) -> None:
        self.registry = registry
        self.allowed = list(allowed) if allowed is not None else None
        self.budget_seconds = budget_seconds

    @staticmethod
    def _fill(value: Any, outputs: Dict[int, str]) -> Any:
        if isinstance(value, str):
            return _REF.sub(lambda m: outputs.get(int(m.group(1)), m.group(0)), value)
        if isinstance(value, dict):
            return {k: Executor._fill(v, outputs) for k, v in value.items()}
        if isinstance(value, list):
            return [Executor._fill(v, outputs) for v in value]
        return value

    @staticmethod
    def _as_text(output: Any, message: str) -> str:
        """What a later step's {{N}} receives: the step's data (e.g. the file's text), not its summary."""
        if isinstance(output, dict) and isinstance(output.get("text"), str):
            return output["text"][:8000]
        if isinstance(output, str):
            return output[:8000]
        if output is not None:
            return json.dumps(output, default=str)[:8000]
        return message

    async def run(self, plan: Plan) -> Report:
        started = time.perf_counter()
        results: List[StepResult] = []
        outputs: Dict[int, str] = {}
        failed: set = set()
        for step in plan.steps:
            if time.perf_counter() - started > self.budget_seconds:
                results.append(StepResult(step, "skipped", "time budget used up"))
                failed.add(step.id)
                continue
            if any(d in failed for d in step.depends_on):
                results.append(StepResult(step, "skipped", "an earlier step it needs did not succeed"))
                failed.add(step.id)
                continue
            out = await self.registry.call(step.tool, self._fill(step.args, outputs), allowed=self.allowed)
            message = str(out.get("message") or "")
            if out.get("status") == "success":
                spec = self.registry.get(step.tool)
                writes = spec is not None and spec.action_class.value != "OBSERVE"
                status = "unverified" if writes and out.get("verified") is not True else "succeeded"
                outputs[step.id] = self._as_text(out.get("output"), message)
            else:
                status = "failed"
                failed.add(step.id)
            results.append(StepResult(step, status, message, str(out.get("evidence") or ""), out))
        return Report(plan.goal, results, time.perf_counter() - started, note=plan.note)


async def run_goal(goal: str, ask: Ask, registry: ToolRegistry, *, allowed: Optional[Iterable[str]] = None,
                   context: str = "") -> Report:
    plan = await Planner(ask, registry, allowed).plan(goal, context)
    if not plan.steps:
        return Report(goal, [], 0.0, note=plan.note or "No tool can do this, so nothing was run.")
    return await Executor(registry, allowed).run(plan)
