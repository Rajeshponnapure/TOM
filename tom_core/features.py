"""R9 feature flags. Every advanced capability is OFF unless the owner turns it on in .env."""
from __future__ import annotations

import os

FLAGS = {
    "watchers": "TOM_WATCHERS",                  # C11 proactive monitoring
    "workflows": "TOM_WORKFLOWS",                # C12 workflow learning
    "cloud_escalation": "TOM_CLOUD_ESCALATION",  # RRM-007 cloud fallback (also needs key, policy, limit)
}
# Remote access (PRD §11 network security) is deliberately not implemented: TOM opens no listening
# socket at all (tests/test_advanced_features.py keeps it that way). Adding it needs its own
# authenticated, encrypted transport and a security review first.


def enabled(name: str) -> bool:
    return os.environ.get(FLAGS[name], "").strip().lower() in ("1", "true", "yes", "on")
