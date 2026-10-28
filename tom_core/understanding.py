"""Understand every message before acting: action, target, content, conditions, constraints, confirmations.

Owner request (2026-10-21): "whatever message I give, go into the brain, analyze the message, the context,
the condition, what it should do — and make the loop fast." The rule-based parser already answers in a few
milliseconds; the model parse that followed it on every task added 1-3 s. Here the rule-based result is
checked: when the intent is recognised and its required details are present, it is used as-is and the
model is skipped; only an unclear or incomplete request goes to the model.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

# Details an intent cannot work without ("a|b" = either is enough).
REQUIRED: Dict[str, List[str]] = {
    "open_app": ["app_name"],
    "close_app": ["app_name"],
    "whatsapp_message": ["person_name", "message_body"],
    "write_email": ["email_address|person_name"],
    "send_email": ["email_address|person_name"],
    "create_presentation": ["subject"],
    "create_word_doc": ["subject"],
    "create_excel": ["subject"],
    "create_pdf": ["subject"],
    "web_search": ["subject"],
    "file_operation": [],
}

_CONDITION = re.compile(
    r"\b(if|unless|only if|when|whenever|before|after|as long as|in case)\b\s+([^,.;]+?)(?=(?:,|\.|;|$| and then | then ))",
    re.I)
_CONSTRAINT = re.compile(
    r"\b(only|just|exactly|at most|at least|no more than|without|don'?t|do not|never|except|make sure|ensure)\b"
    r"\s+([^,.;]+?)(?=(?:,|\.|;|$| and | but ))", re.I)
_ASK_FIRST = re.compile(r"\b(ask me|confirm with me|check with me|show me (?:the )?(?:names|options|list)|"
                        r"let me (?:choose|pick|decide)|before (?:you )?send)", re.I)
_REFERENCE = re.compile(r"\b(it|that|this|them|those|the same|again|the last one|the previous)\b", re.I)


@dataclass
class Understanding:
    action: str
    target: str = ""
    content: str = ""
    conditions: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    ask_first: bool = False
    references_context: bool = False
    missing: List[str] = field(default_factory=list)
    confident: bool = False

    def summary(self) -> str:
        bits = [f"action={self.action}"]
        if self.target:
            bits.append(f"target={self.target}")
        if self.content:
            bits.append(f"content={self.content[:60]}")
        if self.conditions:
            bits.append("conditions=" + "; ".join(self.conditions))
        if self.constraints:
            bits.append("constraints=" + "; ".join(self.constraints))
        if self.ask_first:
            bits.append("will confirm before acting")
        if self.missing:
            bits.append("missing=" + ", ".join(self.missing))
        return " | ".join(bits)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def _have(parsed: Dict[str, Any], spec: str) -> bool:
    return any(str(parsed.get(k) or "").strip() for k in spec.split("|"))


def analyze(command: str, parsed: Dict[str, Any]) -> Understanding:
    text = (command or "").strip()
    intent = str(parsed.get("intent") or "chat")
    target = next((str(parsed[k]) for k in ("person_name", "email_address", "app_name", "file_name", "recipient_name")
                   if parsed.get(k)), "")
    content = str(parsed.get("message_body") or parsed.get("subject") or "")
    conditions = [f"{m.group(1).lower()} {m.group(2).strip()}" for m in _CONDITION.finditer(text)]
    constraints = [f"{m.group(1).lower()} {m.group(2).strip()}" for m in _CONSTRAINT.finditer(text)]
    missing = [s.replace("|", " or ") for s in REQUIRED.get(intent, []) if not _have(parsed, s)]
    ask_first = bool(_ASK_FIRST.search(text)) or str(parsed.get("confirm_contact") or "") == "1"
    refs = bool(_REFERENCE.search(text)) and (len(text.split()) <= 8 or not target)
    confident = not refs and ((intent in REQUIRED and not missing) or (intent == "chat" and len(text.split()) <= 12))
    return Understanding(action=intent, target=target, content=content, conditions=conditions,
                         constraints=constraints, ask_first=ask_first, references_context=refs,
                         missing=missing, confident=confident)
