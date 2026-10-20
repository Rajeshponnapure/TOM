"""Task lifecycle (PRD §13). UNVERIFIED is TOM's addition, see docs/migration/decisions.md ADR-008."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskState(str, Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    NEEDS_INPUT = "NEEDS_INPUT"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    VERIFYING = "VERIFYING"
    BLOCKED = "BLOCKED"
    SUCCEEDED = "SUCCEEDED"
    UNVERIFIED = "UNVERIFIED"   # finished and reported success, but without independent evidence (FR-008)
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


TERMINAL_STATES = frozenset({TaskState.SUCCEEDED, TaskState.UNVERIFIED, TaskState.FAILED,
                             TaskState.REJECTED, TaskState.CANCELLED, TaskState.NEEDS_INPUT})
# NEEDS_INPUT is terminal for now: the legacy handlers cannot resume a task, so the user re-asks.

# Allowed transitions (PRD §13 table, plus UNVERIFIED as a sibling of SUCCEEDED).
TRANSITIONS: Dict[TaskState, frozenset] = {
    TaskState.CREATED: frozenset({TaskState.PLANNING, TaskState.RUNNING, TaskState.CANCELLED, TaskState.REJECTED}),
    TaskState.PLANNING: frozenset({TaskState.AWAITING_APPROVAL, TaskState.READY, TaskState.NEEDS_INPUT,
                                   TaskState.FAILED, TaskState.CANCELLED}),
    TaskState.NEEDS_INPUT: frozenset({TaskState.PLANNING, TaskState.CANCELLED}),
    TaskState.AWAITING_APPROVAL: frozenset({TaskState.READY, TaskState.REJECTED, TaskState.CANCELLED,
                                            TaskState.BLOCKED}),
    TaskState.READY: frozenset({TaskState.RUNNING, TaskState.CANCELLED}),
    TaskState.RUNNING: frozenset({TaskState.VERIFYING, TaskState.PAUSED, TaskState.BLOCKED, TaskState.FAILED,
                                  TaskState.CANCELLED, TaskState.SUCCEEDED, TaskState.UNVERIFIED,
                                  TaskState.REJECTED, TaskState.NEEDS_INPUT}),
    TaskState.PAUSED: frozenset({TaskState.READY, TaskState.CANCELLED}),
    TaskState.VERIFYING: frozenset({TaskState.SUCCEEDED, TaskState.UNVERIFIED, TaskState.BLOCKED,
                                    TaskState.FAILED}),
    TaskState.BLOCKED: frozenset({TaskState.READY, TaskState.NEEDS_INPUT, TaskState.CANCELLED}),
}


def can_transition(old: TaskState, new: TaskState) -> bool:
    return new in TRANSITIONS.get(old, frozenset())


@dataclass
class TaskRecord:
    id: str
    text: str                      # redacted request text
    interface: str
    state: TaskState
    created_at: str
    updated_at: str
    parent_id: Optional[str] = None
    owner_pid: Optional[int] = None
    cancel_requested: bool = False
    outcome: str = ""              # redacted result message (truncated)
    result_status: str = ""        # the legacy handler's own status string
    response_type: str = ""
    error: str = ""
    events: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    def to_dict(self) -> Dict[str, Any]:
        d = dict(self.__dict__)
        d["state"] = self.state.value
        return d
