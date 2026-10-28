"""Deterministic policy engine (PRD §11, R3): every side-effecting tool call is classified, checked
against workspace/protected-path rules and either allowed, sent for approval, or blocked — without
asking a model. docs/security/tool-permissions.md is the human-readable version of these rules."""
from tom_core.policy.engine import ActionClass, Decision, PolicyEngine, ToolCall, get_policy

__all__ = ["ActionClass", "Decision", "PolicyEngine", "ToolCall", "get_policy"]
