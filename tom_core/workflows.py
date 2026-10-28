"""C12 workflow learning (opt-in: TOM_WORKFLOWS=1).

A plan TOM just ran for the user can be saved as a workflow. Literal paths in it become input
variables ({{input:folder}}), so the same steps can run on another folder. A saved workflow is a
*draft* until the user reviews and approves it — only approved workflows run. Running one uses the
normal executor: typed tools, the policy engine, approvals, checkpoints, failure handling.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from tom_core.planning.planner import Executor, Plan, Report, Step
from tools.project_paths import project_path

_NAME = re.compile(r"^[a-z0-9][a-z0-9 _-]{0,40}$")
_PATH = re.compile(r"^(?:[A-Za-z]:[\\/]|~[\\/]|/)")
_INPUT = re.compile(r"\{\{input:([a-z_][a-z0-9_]*)\}\}")
PATH_KEYS = ("path", "src", "dst", "repo", "folder", "cwd")


def _dir() -> str:
    d = str(project_path("tom_brain", "workflows"))
    os.makedirs(d, exist_ok=True)
    return d


def _file(name: str) -> str:
    return os.path.join(_dir(), name.strip().lower().replace(" ", "_") + ".json")


def parameterize(plan: Plan) -> Dict[str, Any]:
    """Turn literal paths into named inputs; the same path anywhere becomes the same input."""
    inputs: Dict[str, str] = {}
    by_value: Dict[str, str] = {}
    steps = []
    for st in plan.steps:
        args = {}
        for k, v in st.args.items():
            if k in PATH_KEYS and isinstance(v, str) and _PATH.match(v):
                if v not in by_value:
                    var = k if k not in inputs else f"{k}{len(inputs) + 1}"
                    by_value[v], inputs[var] = var, v
                args[k] = "{{input:%s}}" % by_value[v]
            else:
                args[k] = v
        steps.append({**st.__dict__, "args": args})
    return {"goal": plan.goal, "steps": steps, "inputs": inputs}


def save_draft(name: str, plan: Plan) -> Dict[str, Any]:
    if not _NAME.match(name.strip().lower()):
        raise ValueError("Use a short name: letters, digits, spaces, - or _.")
    if not plan.steps:
        raise ValueError("There are no steps to save.")
    wf = {**parameterize(plan), "name": name.strip().lower(), "status": "draft",
          "created": datetime.now().isoformat(timespec="seconds")}
    with open(_file(name), "w", encoding="utf-8") as fh:
        json.dump(wf, fh, indent=2)
    return wf


def load(name: str) -> Optional[Dict[str, Any]]:
    try:
        with open(_file(name), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def list_workflows() -> List[Dict[str, Any]]:
    out = []
    for f in sorted(os.listdir(_dir())):
        if f.endswith(".json"):
            wf = load(f[:-5])
            if wf:
                out.append(wf)
    return out


def describe(wf: Dict[str, Any]) -> str:
    lines = [f"Workflow '{wf['name']}' ({wf['status']}): {wf['goal']}",
             "Inputs: " + (", ".join(f"{k} (last: {v})" for k, v in wf["inputs"].items()) or "none")]
    lines += [f"  {s['id']}. {s['tool']} {json.dumps(s['args'])}" for s in wf["steps"]]
    return "\n".join(lines)


def approve(name: str) -> Dict[str, Any]:
    """The review step: the user has seen describe() and says it is right."""
    wf = load(name)
    if wf is None:
        raise KeyError(name)
    wf["status"] = "approved"
    wf["approved"] = datetime.now().isoformat(timespec="seconds")
    with open(_file(name), "w", encoding="utf-8") as fh:
        json.dump(wf, fh, indent=2)
    return wf


def _bind(value: Any, values: Dict[str, str]) -> Any:
    if isinstance(value, str):
        return _INPUT.sub(lambda m: values[m.group(1)], value)
    if isinstance(value, dict):
        return {k: _bind(v, values) for k, v in value.items()}
    if isinstance(value, list):
        return [_bind(v, values) for v in value]
    return value


async def run(name: str, registry, values: Optional[Dict[str, str]] = None, checkpoint=None) -> Report:
    wf = load(name)
    if wf is None:
        raise KeyError(name)
    if wf["status"] != "approved":
        raise PermissionError(f"Workflow '{name}' is a draft — review it and approve it before it can run.")
    merged = {**wf["inputs"], **(values or {})}
    unknown = set(values or {}) - set(wf["inputs"])
    if unknown:
        raise ValueError(f"Unknown input(s): {', '.join(sorted(unknown))}. Inputs: {', '.join(wf['inputs'])}")
    steps = [Step(**{**s, "args": _bind(s["args"], merged)}) for s in wf["steps"]]
    return await Executor(registry, checkpoint=checkpoint).run(Plan(wf["goal"], steps))
