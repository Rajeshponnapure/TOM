"""The one gate every side-effecting tool passes immediately before it acts (PRD FR-005, TOM-MIG-010).

    decision = enforce("whatsapp.send", ActionClass.DESTRUCTIVE_OR_EXTERNAL,
                       payload={"to": contact, "message": text}, approval_action="whatsapp_message")
    if not decision.allowed: return {"status": "blocked", "message": decision.reason}

* The PolicyEngine decides allow / approve / block — deterministically, never a model (FR-010).
* "approve" is satisfied by a matching grant in the ApprovalManager ledger (the user already said
  yes to this exact payload at the agent's gate) or by asking now through the trusted UI provider.
  With no approval channel registered the action is refused, never silently allowed.
* Every decision is written to tom_logs/audit.jsonl with actor/interface, task id, tool, target,
  policy result, approval reference and outcome — secrets redacted (PRD §11.2 Auditability).
"""
from __future__ import annotations

import asyncio
import contextvars
import json
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

from tom_core.observability.redact import redact
from tom_core.policy.engine import ActionClass, Decision, ToolCall, get_policy
from tools.project_paths import project_path

_approval_manager = None
_audit_lock = threading.Lock()
_inside_guarded: "contextvars.ContextVar[str]" = contextvars.ContextVar("tom_inside_guarded", default="")


def set_approval_manager(manager) -> None:
    """Called by TomAgent: the trusted approval channel (desktop dialog, Qt dialog, CLI prompt)."""
    global _approval_manager
    _approval_manager = manager


@dataclass
class Enforced:
    decision: Decision
    approval_ref: str = ""

    @property
    def allowed(self) -> bool:
        return self.decision.allowed

    @property
    def reason(self) -> str:
        return self.decision.reason

    def refusal(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """The result a tool returns instead of acting."""
        status = "cancelled" if "not approved" in self.reason else "blocked"
        out = {"status": status, "sent": False, "message": self.reason, "policy": self.decision.verdict}
        out.update(extra or {})
        return out


def _context() -> Dict[str, Any]:
    try:
        from tom_core.tasks.service import current_interface, current_task_id
        return {"actor": current_interface() or "direct", "task_id": current_task_id()}
    except Exception:
        return {"actor": "direct", "task_id": None}


def audit(event: Dict[str, Any]) -> None:
    """Append one redacted JSON line to tom_logs/audit.jsonl. Never raises."""
    try:
        path = project_path("tom_logs", "audit.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        line = redact(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **event}, default=str))
        with _audit_lock, open(path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


def _summary(tool: str, payload: Dict[str, Any], reason: str) -> str:
    shown = "; ".join(f"{k}: {str(v)[:160]}" for k, v in payload.items() if not str(k).startswith("_"))
    return f"TOM wants to run {tool}" + (f" — {shown}" if shown else "") + f"\n({reason})"


def _standing(env_name: Optional[str]) -> bool:
    import os
    return bool(env_name) and (os.environ.get(env_name) or "").strip().lower() in ("1", "true", "yes", "on")


def enforce(tool: str, action_class: ActionClass, *, payload: Optional[Dict[str, Any]] = None,
            paths: Iterable[str] = (), approval_action: Optional[str] = None,
            summary: Optional[str] = None, risk_level: str = "high",
            standing: Optional[str] = None, manager=None) -> Enforced:
    """Check a tool call right before it runs; ask for approval if needed. Synchronous (may block on
    the approval dialog) — async callers use `aenforce`.

    `standing` names the opt-in setting that pre-authorizes this kind of action for a background
    automation the user switched on themselves (e.g. EMAIL_AUTO_REPLY_ENABLED) — the PRD approval
    matrix's "configured policy". It only replaces the approval prompt: emergency stop, protected
    paths and blocked classes still apply, and the decision is audited as "standing:<setting>".
    """
    payload = dict(payload or {})
    get_policy().wait_if_paused()            # FR-006: while paused, a new action waits here
    ctx = _context()
    call = ToolCall(tool=tool, action_class=ActionClass(action_class), payload=payload, paths=list(paths),
                    actor=ctx["actor"], task_id=ctx["task_id"])
    decision = get_policy().evaluate(call)
    ref = ""
    if decision.verdict == "approve" and _standing(standing):
        ref = f"standing:{standing}"
        decision = Decision("allow", decision.action_class, f"pre-authorized by {standing}")
    if decision.verdict == "approve":
        action = approval_action or tool
        manager = manager or _approval_manager
        if manager is None:
            decision = Decision("block", decision.action_class,
                                f"{tool} needs approval, but no approval channel is available here.")
        else:
            ledger = getattr(manager, "ledger", None)
            ref = (ledger.consume(action, payload) or "") if ledger is not None else ""
            if not ref:
                from tools.approval import ApprovalRequest
                ok = manager.request_approval(ApprovalRequest(
                    action=action, summary=summary or _summary(tool, payload, decision.reason),
                    details=payload, risk_level=risk_level))
                if ok:
                    # the user said yes to this exact request just now; the ledger entry (when the
                    # approver records one) is consumed so it cannot be replayed
                    ref = (ledger.consume(action, payload) if ledger is not None else "") or "direct"
            decision = (Decision("allow", decision.action_class, f"approved ({ref})") if ref else
                        Decision("block", decision.action_class, f"{tool}: not approved — nothing was done."))
    audit({"event": "policy", "tool": tool, "class": call.action_class.value, "verdict": decision.verdict,
           "reason": decision.reason, "approval_ref": ref, "actor": call.actor, "task_id": call.task_id,
           "target": {k: str(v)[:200] for k, v in payload.items()}, "paths": [str(p) for p in call.paths]})
    return Enforced(decision, ref)


def guard_methods(cls, names, tool_prefix: str, action_class: ActionClass, approval_action: str,
                  target_arg: str = "target") -> None:
    """Wrap existing synchronous methods of `cls` so each call passes enforce() first.

    The first argument (or keyword `target_arg`) becomes the approval payload's "target". Used for
    tools that had no approval at all (dependency installs, self-updates — tool-permissions.md §2).
    """
    import functools
    for name in names:
        original = getattr(cls, name, None)
        if original is None or getattr(original, "_tom_guarded", False):
            continue

        def make(fn, method):
            @functools.wraps(fn)
            def wrapper(self, *args, **kwargs):
                if _inside_guarded.get() == tool_prefix:
                    return fn(self, *args, **kwargs)   # e.g. full_update → pull_updates: approved once
                target = args[0] if args else kwargs.get(target_arg, "")
                gate = enforce(f"{tool_prefix}.{method}", action_class, payload={"target": str(target or "")},
                               approval_action=approval_action)
                if not gate.allowed:
                    return gate.refusal()
                token = _inside_guarded.set(tool_prefix)
                try:
                    return fn(self, *args, **kwargs)
                finally:
                    _inside_guarded.reset(token)
            wrapper._tom_guarded = True
            return wrapper
        setattr(cls, name, make(original, name))


async def aenforce(*args, **kwargs) -> Enforced:
    """enforce() for async code: the approval dialog must not block the agent's event loop."""
    return await asyncio.to_thread(enforce, *args, **kwargs)


def record_outcome(tool: str, result: Any) -> None:
    """Audit the outcome of a tool that was allowed to run."""
    status = result.get("status") if isinstance(result, dict) else type(result).__name__
    message = result.get("message", "") if isinstance(result, dict) else ""
    audit({"event": "outcome", "tool": tool, "status": status, "message": str(message)[:300], **_context()})
