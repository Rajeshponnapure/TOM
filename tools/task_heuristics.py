"""
Pure decision logic for the universal task fallback (A1).

A command reaches the universal attempt ONLY when every gate passes —
conservative by design so casual chat never lands in the autonomous loop.
Disable instantly with TOM_UNIVERSAL_FALLBACK=0 (no redeploy needed).
"""

import os
import re

# Intents that mean "the user is talking, not tasking"
CHAT_INTENTS = {"chat", "question", "talk", "greeting", "unknown", "feedback",
                "give_feedback", ""}

ACTION_VERBS = (
    "create", "make", "build", "generate", "write", "convert", "organize",
    "organise", "rename", "move", "copy", "delete", "find", "download",
    "install", "setup", "set up", "configure", "fix", "clean", "extract",
    "merge", "split", "compress", "zip", "deploy", "schedule", "automate",
    "summarize", "summarise", "translate", "compile", "scan", "backup",
    "prepare", "draft", "compose", "design", "develop", "implement",
)


def should_attempt_universal(intent: str, command: str, enabled: bool = None) -> bool:
    """True only for clearly task-like commands with no concrete handler."""
    if enabled is None:
        enabled = os.environ.get("TOM_UNIVERSAL_FALLBACK", "1").strip().lower() \
            in ("1", "true", "yes", "on")
    if not enabled:
        return False
    intent = (intent or "").strip().lower()
    if intent in CHAT_INTENTS:
        # intent says chat — but trust an explicit imperative over a weak parse
        pass_through = False
    else:
        pass_through = True
    c = (command or "").strip().lower()
    words = c.split()
    if len(words) < 4:
        return False
    has_verb = any(re.search(rf"\b{re.escape(v)}\b", c) for v in ACTION_VERBS)
    if pass_through and has_verb:
        return True
    # chat-ish intent: require a STRONG imperative start to override
    return has_verb and words[0] in {v.split()[0] for v in ACTION_VERBS}
