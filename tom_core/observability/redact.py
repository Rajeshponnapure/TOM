"""Secret redaction (PRD FR-007, TOM-MIG-009, AT-010).

Applied to text *before* it reaches a log file, the task store or an export. Patterns cover the
credential shapes TOM handles (Groq, Hindsight, OpenAI/Anthropic-style keys, GitHub, Slack, Google,
AWS, JWTs, bearer tokens, key=value secrets) plus the values of secret-looking environment variables
loaded in this process, so a key pasted verbatim into a command is caught even if its shape is new.
"""
from __future__ import annotations

import os
import re
from typing import Any, Iterable, List

MASK = "[REDACTED]"

_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(?:gsk|hsk|sk|pk|rk)[-_](?:live[-_]|test[-_]|proj[-_]|ant[-_])?[A-Za-z0-9_\-]{16,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),       # JWT
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    # key=value / key: value where the key names a secret
    re.compile(r"(?i)\b([A-Z0-9_]*(?:api[_-]?key|secret|token|passwd|password|pwd|app[_-]?pass))"
               r"(\s*[:=]\s*)(\"[^\"]+\"|'[^']+'|\S+)"),
    # "my <...> key/password/token is <value>"
    re.compile(r"(?i)\b((?:api\s*)?(?:key|password|passcode|token|secret))(\s+(?:is|=|:)\s+)(\S{6,})"),
]

_SECRET_ENV = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|PASS|CREDENTIAL)", re.I)


def _env_secrets() -> List[str]:
    vals = []
    for k, v in os.environ.items():
        v = (v or "").strip()
        if _SECRET_ENV.search(k) and len(v) >= 8 and not os.path.exists(v):
            vals.append(v)
    return sorted(set(vals), key=len, reverse=True)


def redact(text: Any, extra_secrets: Iterable[str] = ()) -> str:
    """Return `text` with credentials replaced by [REDACTED]. Never raises."""
    try:
        out = str(text if text is not None else "")
    except Exception:
        return MASK
    if not out:
        return out
    for secret in list(extra_secrets) + _env_secrets():
        if secret and secret in out:
            out = out.replace(secret, MASK)
    for pat in _PATTERNS:
        if pat.groups >= 3:
            out = pat.sub(lambda m: m.group(1) + m.group(2) + MASK, out)
        else:
            out = pat.sub(MASK, out)
    return out
