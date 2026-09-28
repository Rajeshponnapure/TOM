from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


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

    def request_approval(
        self,
        request: ApprovalRequest,
        prompt_fn: Optional[Callable[[str], str]] = None,
    ) -> bool:
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
