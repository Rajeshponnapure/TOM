"""Typed tool registry (PRD §12.1, FR-004/005/007, NFR-004, AT-002).

A tool is a narrow operation with a pydantic argument schema, an action class for the policy
engine, a timeout and a structured result. registry.call():
    1. validates the arguments against the schema — invalid calls are rejected before anything runs
       and logged with secrets redacted (AT-002);
    2. passes the call through tom_core.tools.guard (policy + approval + audit);
    3. runs the handler with a timeout (sync handlers in a worker thread);
    4. returns {"status", "tool", "output", "evidence", "error_class", "message"}.
The planner (tom_core.planning) emits calls by tool name; models never execute anything directly.
"""
from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Type

from pydantic import BaseModel, ValidationError

from tom_core.policy.engine import ActionClass
from tom_core.tools.guard import aenforce, audit, record_outcome


@dataclass
class ToolSpec:
    name: str
    description: str
    args: Type[BaseModel]
    handler: Callable[..., Any]                      # handler(**validated_args) -> dict | value
    action_class: ActionClass = ActionClass.OBSERVE
    timeout: float = 60.0
    approval_action: str = ""
    paths: Callable[[BaseModel], Iterable[str]] = field(default=lambda a: ())
    payload: Callable[[BaseModel], Dict[str, Any]] = field(default=lambda a: a.model_dump())
    # A class decided per call (e.g. a shell command on the read-only allowlist is OBSERVE).
    classify: Optional[Callable[[BaseModel], ActionClass]] = None

    def schema_line(self) -> str:
        fields = ", ".join(f"{k}: {v.annotation.__name__ if hasattr(v.annotation, '__name__') else v.annotation}"
                           + ("" if v.is_required() else f" = {v.default!r}")
                           for k, v in self.args.model_fields.items())
        return f"{self.name}({fields}) — {self.description} [{self.action_class.value}]"


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> ToolSpec:
        self._tools[spec.name] = spec
        return spec

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def names(self) -> List[str]:
        return sorted(self._tools)

    def catalogue(self, allowed: Optional[Iterable[str]] = None) -> str:
        """One line per tool, for planner/specialist prompts (only the granted ones)."""
        keep = set(allowed) if allowed is not None else None
        return "\n".join(s.schema_line() for n, s in sorted(self._tools.items()) if keep is None or n in keep)

    async def call(self, name: str, args: Optional[Dict[str, Any]] = None, *,
                   allowed: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        spec = self._tools.get(name)
        if spec is None:
            return self._fail(name, "unknown_tool", f"There is no tool called '{name}'.")
        if allowed is not None and name not in set(allowed):
            audit({"event": "grant_denied", "tool": name})
            return self._fail(name, "not_granted", f"'{name}' is not among the tools this role may use.")
        try:
            parsed = spec.args.model_validate(args or {})
        except ValidationError as exc:
            problems = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())
            audit({"event": "invalid_args", "tool": name, "problems": problems})
            return self._fail(name, "invalid_args", f"Invalid arguments for {name}: {problems}")

        action_class = spec.classify(parsed) if spec.classify else spec.action_class
        gate = await aenforce(name, action_class, payload=spec.payload(parsed), paths=list(spec.paths(parsed)),
                              approval_action=spec.approval_action or None)
        if not gate.allowed:
            return {**gate.refusal(), "tool": name, "error_class": "policy", "output": None, "evidence": ""}
        try:
            if inspect.iscoroutinefunction(spec.handler):
                raw = await asyncio.wait_for(spec.handler(**parsed.model_dump()), timeout=spec.timeout)
            else:
                raw = await asyncio.wait_for(asyncio.to_thread(spec.handler, **parsed.model_dump()),
                                             timeout=spec.timeout)
        except asyncio.TimeoutError:
            result = self._fail(name, "timeout", f"{name} did not finish within {spec.timeout:.0f}s.")
            record_outcome(name, result)
            return result
        except Exception as exc:
            result = self._fail(name, "exception", f"{name} failed: {type(exc).__name__}: {exc}")
            record_outcome(name, result)
            return result
        result = self._normalize(name, raw)
        record_outcome(name, result)
        return result

    @staticmethod
    def _fail(name: str, error_class: str, message: str) -> Dict[str, Any]:
        return {"status": "error", "tool": name, "error_class": error_class, "message": message,
                "output": None, "evidence": ""}

    @staticmethod
    def _normalize(name: str, raw: Any) -> Dict[str, Any]:
        if isinstance(raw, dict) and "status" in raw:
            out = dict(raw)
        else:
            out = {"status": "success", "output": raw}
        out.setdefault("tool", name)
        out.setdefault("output", None)
        out.setdefault("evidence", "")
        out.setdefault("error_class", "" if out.get("status") == "success" else "tool_error")
        out.setdefault("message", "")
        return out


_REGISTRY: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """The registry with TOM's built-in typed tools (tom_core.tools.builtin) registered."""
    global _REGISTRY
    if _REGISTRY is None:
        registry = ToolRegistry()
        from tom_core.tools import builtin, diagnostics
        builtin.register_all(registry)
        diagnostics.register(registry)
        _REGISTRY = registry
    return _REGISTRY
