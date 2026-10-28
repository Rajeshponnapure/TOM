"""Cloud escalation gate (PRD RRM-007, R9). Off unless ALL of these are configured:

    TOM_CLOUD_ESCALATION=1          the feature flag
    GROQ_API_KEY=...                provider credentials
    TOM_CLOUD_DATA_POLICY=...       "no-personal-data" (requests mentioning files, email, contacts or
                                    memories stay local) or "allow"
    TOM_CLOUD_DAILY_LIMIT=N         max cloud requests per day (the cost limit); 0 = none allowed

Used only when local inference has failed (e.g. out of memory after the one local retry).
"""
from __future__ import annotations

import json
import os
import re
from datetime import date
from typing import Tuple

from tom_core import features
from tools.project_paths import project_path

_PERSONAL = re.compile(r"\b(file|folder|document|email|e-mail|inbox|contact|whatsapp|password|memory|"
                       r"remember|address|phone|bank|invoice|[A-Za-z]:[\\/])", re.I)


def _usage_file() -> str:
    return str(project_path("tom_brain", "cloud_usage.json"))


def _used_today() -> int:
    try:
        with open(_usage_file(), encoding="utf-8") as fh:
            data = json.load(fh)
        return int(data.get(date.today().isoformat(), 0))
    except (OSError, ValueError):
        return 0


def allowed(text: str = "") -> Tuple[bool, str]:
    if not features.enabled("cloud_escalation"):
        return False, "cloud escalation is off (TOM_CLOUD_ESCALATION)"
    if not os.environ.get("GROQ_API_KEY", "").strip():
        return False, "no cloud provider key is configured"
    policy = os.environ.get("TOM_CLOUD_DATA_POLICY", "").strip().lower()
    if policy not in ("no-personal-data", "allow"):
        return False, "no data-sharing policy is set (TOM_CLOUD_DATA_POLICY)"
    try:
        limit = int(os.environ.get("TOM_CLOUD_DAILY_LIMIT", "0"))
    except ValueError:
        limit = 0
    if limit <= 0:
        return False, "no cloud cost limit is set (TOM_CLOUD_DAILY_LIMIT)"
    if _used_today() >= limit:
        return False, f"today's cloud limit of {limit} requests is used up"
    if policy == "no-personal-data" and _PERSONAL.search(text or ""):
        return False, "the request involves personal data, which the data policy keeps on this PC"
    return True, f"cloud escalation allowed ({_used_today()}/{limit} used today)"


def record_use() -> None:
    path = _usage_file()
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        data = {}
    today = date.today().isoformat()
    data = {today: int(data.get(today, 0)) + 1}          # keep only today
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
