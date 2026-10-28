from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


def _norm_value(value: Any) -> str:
    return " ".join(str(value).split()).casefold()


class ApprovalLedger:
    """Approvals the user granted, bound to the exact payload, expiring after `ttl` seconds.

    PRD §S3: "Approvals must be tied to exact action payload and expire when payload changes."
    A guarded tool consumes the matching grant, so an approval given at the agent's gate is used
    once by the tool that performs it — and a changed recipient/message/path needs a new one.
    """

    def __init__(self, ttl: float = 300.0) -> None:
        self.ttl = ttl
        self._grants: List[Tuple[str, Dict[str, str], float, str]] = []
        self._lock = threading.Lock()

    def grant(self, action: str, details: Dict[str, Any]) -> str:
        ref = uuid.uuid4().hex[:12]
        payload = {str(k): _norm_value(v) for k, v in (details or {}).items()}
        with self._lock:
            self._grants.append((action, payload, time.time() + self.ttl, ref))
        return ref

    def consume(self, action: str, payload: Dict[str, Any]) -> Optional[str]:
        """The approval reference if a live grant covers every key of `payload`, else None."""
        want = {str(k): _norm_value(v) for k, v in (payload or {}).items()}
        now = time.time()
        with self._lock:
            self._grants = [g for g in self._grants if g[2] > now]
            for i, (act, have, _exp, ref) in enumerate(self._grants):
                if act == action and all(have.get(k) == v for k, v in want.items()):
                    del self._grants[i]
                    return ref
        return None


@dataclass(slots=True)
class ApprovalRequest:
    action: str
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)
    risk_level: str = "medium"


class ApprovalManager:
    """Human approval gate for sensitive actions.

    The default implementation uses a console prompt so the current desktop app
    can keep working without extra UI wiring. A custom prompt provider can be
    injected later by the Tkinter or FastAPI front end.
    """

    def format_request(self, request: ApprovalRequest) -> str:
        lines = [
            "APPROVAL REQUIRED",
            f"Action: {request.action}",
            f"Summary: {request.summary}",
            f"Risk: {request.risk_level}",
        ]

        if request.details:
            lines.append("Details:")
            for key, value in request.details.items():
                lines.append(f"- {key}: {value}")

        lines.append("Type 'yes' to approve or 'no' to cancel.")
        return "\n".join(lines)

    # Set by a GUI front end: takes the request, returns True to approve.
    # When unset, approval falls back to a console prompt.
    provider: Optional[Callable[[ApprovalRequest], bool]] = None

    def __init__(self) -> None:
        self.ledger = ApprovalLedger()

    def request_approval(
        self,
        request: ApprovalRequest,
        prompt_fn: Optional[Callable[[str], str]] = None,
    ) -> bool:
        approved = self._ask(request, prompt_fn)
        if approved:
            # The guarded tool that performs this action consumes the grant (tom_core.tools.guard).
            self.ledger.grant(request.action, request.details)
        return approved

    def _ask(self, request: ApprovalRequest, prompt_fn: Optional[Callable[[str], str]] = None) -> bool:
        if prompt_fn is None and self.provider is not None:
            try:
                return bool(self.provider(request))
            except Exception as exc:
                print(f"[APPROVAL] Prompt failed ({exc}); action denied.")
                return False
        prompt = prompt_fn or input
        print(self.format_request(request))
        try:
            response = prompt("Approval: ").strip().lower()
        except (EOFError, RuntimeError, OSError):
            # No console attached (pythonw / frozen GUI exe): deny rather
            # than crash the task with "EOF when reading a line".
            print("[APPROVAL] No console available to ask for approval; action denied.")
            return False
        return response in {"yes", "y", "approve", "approved", "confirm"}
