"""PolicyEngine: classify → check paths → allow / approve / block (PRD §11.2–11.3, FR-005/009/010/011/014).

Rules, in order:
  1. Emergency stop active → everything but OBSERVE is blocked (PRD §11.2 "prevents new tool calls").
  2. BLOCKED class → blocked.
  3. A path argument inside a protected location (Windows, Program Files, TOM's own policy/safety
     code, .git internals) → blocked for any write class. Paths are resolved with realpath first,
     so ".." and symlinks cannot escape (tool-permissions.md non-negotiable 5).
  4. PRIVILEGED from an autonomous actor → blocked (never available to autonomous loops).
  5. WORKSPACE_WRITE inside a workspace root → allowed; outside → needs approval ("separately
     authorized", FR-011 / AT-004).
  6. MATERIAL_CHANGE, DESTRUCTIVE_OR_EXTERNAL, PRIVILEGED → approval, bound to the exact payload.
  7. OBSERVE, REVERSIBLE → allowed (logged).
The model never decides any of this and cannot change it at runtime (FR-010): the rules are code,
and tool calls that try to write the policy files are blocked by rule 3.
"""
from __future__ import annotations

import enum
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from tools.project_paths import PROJECT_ROOT, workspace_root


class ActionClass(str, enum.Enum):
    OBSERVE = "OBSERVE"
    REVERSIBLE = "REVERSIBLE"
    WORKSPACE_WRITE = "WORKSPACE_WRITE"
    MATERIAL_CHANGE = "MATERIAL_CHANGE"
    DESTRUCTIVE_OR_EXTERNAL = "DESTRUCTIVE_OR_EXTERNAL"
    PRIVILEGED = "PRIVILEGED"
    BLOCKED = "BLOCKED"


WRITE_CLASSES = frozenset({ActionClass.WORKSPACE_WRITE, ActionClass.MATERIAL_CHANGE,
                           ActionClass.DESTRUCTIVE_OR_EXTERNAL, ActionClass.PRIVILEGED})
APPROVAL_CLASSES = frozenset({ActionClass.MATERIAL_CHANGE, ActionClass.DESTRUCTIVE_OR_EXTERNAL,
                              ActionClass.PRIVILEGED})


@dataclass
class ToolCall:
    tool: str                                   # registry name, e.g. "whatsapp.send"
    action_class: ActionClass
    payload: Dict[str, Any] = field(default_factory=dict)   # what an approval is bound to
    paths: Sequence[str] = ()                  # filesystem targets the call reads/writes
    actor: str = ""                            # interface / role: desktop, voice, autonomous, specialist:…
    task_id: Optional[str] = None


@dataclass
class Decision:
    verdict: str                               # allow | approve | block
    action_class: ActionClass
    reason: str

    @property
    def allowed(self) -> bool:
        return self.verdict == "allow"


def _norm(path: str) -> str:
    return os.path.normcase(os.path.realpath(os.path.expanduser(str(path))))


def _within(path: str, root: str) -> bool:
    try:
        return os.path.commonpath([_norm(path), _norm(root)]) == _norm(root)
    except ValueError:                          # different drives
        return False


def default_workspace_roots() -> List[str]:
    roots = [str(workspace_root())]
    extra = os.environ.get("TOM_WORKSPACE_ROOTS", "")
    roots += [p for p in extra.split(os.pathsep) if p.strip()]
    return roots


def default_protected_paths() -> List[str]:
    windir = os.environ.get("WINDIR", r"C:\Windows")
    paths = [windir, os.environ.get("ProgramFiles", r"C:\Program Files"),
             os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
             os.environ.get("ProgramData", r"C:\ProgramData")]
    root = Path(PROJECT_ROOT)
    # TOM's own enforcement code and configuration (§11.2 "policy integrity").
    paths += [str(root / "tom_core" / "policy"), str(root / "safety"), str(root / "config" / "policies.yaml"),
              str(root / ".git")]
    return [p for p in paths if p]


class PolicyEngine:
    def __init__(self, workspace_roots: Optional[Iterable[str]] = None,
                 protected_paths: Optional[Iterable[str]] = None) -> None:
        self._workspace_roots = list(workspace_roots) if workspace_roots is not None else None
        self._protected = list(protected_paths) if protected_paths is not None else None
        self._halted = threading.Event()
        self.halt_reason = ""

    # roots are read lazily so TOM_WORKSPACE_DIR / TOM_WORKSPACE_ROOTS set later still count
    @property
    def workspace_roots(self) -> List[str]:
        return self._workspace_roots if self._workspace_roots is not None else default_workspace_roots()

    @property
    def protected_paths(self) -> List[str]:
        return self._protected if self._protected is not None else default_protected_paths()

    # ── emergency stop (PRD §11.2) ───────────────────────────────────────
    def halt(self, reason: str = "emergency stop") -> None:
        self.halt_reason = reason
        self._halted.set()

    def resume(self) -> None:
        self._halted.clear()
        self.halt_reason = ""

    @property
    def halted(self) -> bool:
        return self._halted.is_set()

    # ── evaluation ───────────────────────────────────────────────────────
    def in_workspace(self, path: str) -> bool:
        return any(_within(path, root) for root in self.workspace_roots)

    def protected(self, path: str) -> Optional[str]:
        return next((p for p in self.protected_paths if _within(path, p)), None)

    def evaluate(self, call: ToolCall) -> Decision:
        cls = ActionClass(call.action_class)
        if self.halted and cls is not ActionClass.OBSERVE:
            return Decision("block", cls, f"Emergency stop is active ({self.halt_reason}); no new actions run.")
        if cls is ActionClass.BLOCKED:
            return Decision("block", cls, f"'{call.tool}' is not allowed (blocked pending review).")
        if cls in WRITE_CLASSES:
            for path in call.paths:
                hit = self.protected(path)
                if hit:
                    return Decision("block", cls, f"'{path}' is inside a protected location ({hit}).")
        if cls is ActionClass.PRIVILEGED and call.actor.startswith(("autonomous", "specialist")):
            return Decision("block", cls, "Privileged actions are not available to autonomous runs.")
        if cls is ActionClass.WORKSPACE_WRITE:
            outside = [p for p in call.paths if not self.in_workspace(p)]
            if outside:
                return Decision("approve", cls, f"Writes outside the workspace: {', '.join(outside[:3])}")
            return Decision("allow", cls, "workspace write")
        if cls in APPROVAL_CLASSES:
            return Decision("approve", cls, f"{cls.value.replace('_', ' ').lower()} needs your approval")
        return Decision("allow", cls, cls.value.lower())


_POLICY: Optional[PolicyEngine] = None
_LOCK = threading.Lock()


def get_policy() -> PolicyEngine:
    global _POLICY
    with _LOCK:
        if _POLICY is None:
            _POLICY = PolicyEngine()
        return _POLICY
