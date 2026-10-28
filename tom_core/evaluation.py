"""Self-evaluation (PRD C18): score recent task outcomes, group failures by category, propose improvements.

Reads the durable task store only — nothing is sent anywhere. Improvements are proposals for the
owner to review, never applied automatically.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List

_CATEGORIES = [
    ("model timeout or unavailable", r"timeout|timed out|model .*not|ollama|connection refused"),
    ("out of memory", r"out of memory|cuda|requires more system memory"),
    ("not approved / blocked by policy", r"not approved|blocked|refused|policy"),
    ("missing input or unclear request", r"which|need(s)? (more|the)|clarif|not sure what|needs_input"),
    ("file or path problem", r"no (file|folder)|not found|permission|access is denied"),
    ("network / web", r"network|internet|dns|http|offline"),
    ("tool or code error", r"traceback|exception|error"),
]
_ADVICE = {
    "model timeout or unavailable": "Check that Ollama is running; consider TOM_FALLBACK_MODEL so a smaller model takes over.",
    "out of memory": "Lower TOM_NUM_CTX or close other GPU apps; the benchmark in docs/benchmarks shows each model's VRAM use.",
    "not approved / blocked by policy": "Expected when you said no. If an action you do often keeps asking, consider a reviewed workflow.",
    "missing input or unclear request": "Phrase requests with the target (file, person, folder) or set up a project profile.",
    "file or path problem": "Add the folder to TOM_WORKSPACE_ROOTS or check the path exists.",
    "network / web": "Check the internet connection; web research and cloud features need it.",
    "tool or code error": "Look at the task timeline (Tasks panel) for the failing step; report it if it repeats.",
}


def categorize(text: str) -> str:
    low = (text or "").lower()
    for name, rx in _CATEGORIES:
        if re.search(rx, low):
            return name
    return "other"


def evaluate(store, limit: int = 200) -> Dict[str, Any]:
    tasks = store.list(limit)
    states = Counter(t.state.value for t in tasks)
    finished = [t for t in tasks if t.terminal]
    good = states.get("SUCCEEDED", 0)
    failures = [t for t in finished if t.state.value in ("FAILED", "REJECTED", "BLOCKED")]
    cats = Counter(categorize(f"{t.error or ''} {t.outcome or ''} {t.result_status or ''}") for t in failures)
    by_type = Counter((t.response_type or "chat") for t in failures)
    score = round(100 * good / len(finished)) if finished else 0
    return {"tasks": len(tasks), "finished": len(finished), "states": dict(states), "success_rate": score,
            "failure_categories": cats.most_common(), "failing_kinds": by_type.most_common(5),
            "proposals": [_ADVICE[c] for c, _ in cats.most_common(3) if c in _ADVICE]}


def report_text(result: Dict[str, Any]) -> str:
    if not result["finished"]:
        return "No finished tasks to evaluate yet."
    s = result["states"]
    lines = [f"Last {result['tasks']} tasks: {result['success_rate']}% verified successes "
             f"({s.get('SUCCEEDED', 0)} succeeded, {s.get('UNVERIFIED', 0)} unverified, {s.get('FAILED', 0)} failed, "
             f"{s.get('REJECTED', 0)} refused, {s.get('CANCELLED', 0)} cancelled, {s.get('NEEDS_INPUT', 0)} needed input)."]
    if result["failure_categories"]:
        lines.append("Failure categories: " + ", ".join(f"{c} ({n})" for c, n in result["failure_categories"]))
    if result["failing_kinds"]:
        lines.append("Most failing kinds of request: " + ", ".join(f"{k} ({n})" for k, n in result["failing_kinds"]))
    if result["proposals"]:
        lines.append("Proposed improvements (for you to review):")
        lines += [f"- {p}" for p in result["proposals"]]
    return "\n".join(lines)


def task_report(store, task_id: str) -> str:
    """FR-019: one task as a readable report, secrets already redacted by the store."""
    data = store.export(task_id)
    lines: List[str] = [f"# TOM task report — {data.get('id', task_id)}", "",
                        f"- Request: {data.get('text', '')}", f"- Interface: {data.get('interface', '')}",
                        f"- State: {data.get('state', '')}", f"- Created: {data.get('created_at', '')}",
                        f"- Updated: {data.get('updated_at', '')}", ""]
    if data.get("outcome"):
        lines += ["## Outcome", "", str(data["outcome"]), ""]
    if data.get("error"):
        lines += ["## Error", "", str(data["error"]), ""]
    events: List[Dict[str, Any]] = data.get("events") or []
    if events:
        lines += ["## Timeline", ""] + [f"- {e.get('at', '')} · {e.get('kind', '')} · {str(e.get('message', ''))[:300]}"
                                        for e in events]
    return "\n".join(lines) + "\n"
