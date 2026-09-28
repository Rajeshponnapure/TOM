"""In-memory stand-in for hindsight_client.Hindsight used by tests and the offline demo.

Mimics the parts of the real client TOM uses (create_bank, retain, recall,
reflect, list_memories) closely enough to exercise every code path without a
server. Recall ranks by word overlap with the query, newest first on ties.
"""

import re
from types import SimpleNamespace


def _words(text):
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) > 2}


class FakeHindsight:
    def __init__(self, fail=False):
        self.items = []
        self.banks = {}
        self.fail = fail
        self.calls = []

    def _maybe_fail(self, op):
        self.calls.append(op)
        if self.fail:
            raise ConnectionError(f"{op}: server unreachable")

    def create_bank(self, bank_id, **kwargs):
        self._maybe_fail("create_bank")
        self.banks[bank_id] = kwargs
        return SimpleNamespace(bank_id=bank_id)

    def retain(self, bank_id, content, **kwargs):
        self._maybe_fail("retain")
        self.items.append({"bank": bank_id, "text": content, "tags": kwargs.get("tags") or [],
                           "context": kwargs.get("context"), "id": str(len(self.items) + 1),
                           "mentioned_at": "2026-09-2%d" % min(len(self.items), 8)})
        return SimpleNamespace(success=True, bank_id=bank_id, items_count=1)

    def recall(self, bank_id, query, tags=None, **kwargs):
        self._maybe_fail("recall")
        q = _words(query)
        scored = []
        for idx, it in enumerate(self.items):
            if it["bank"] != bank_id:
                continue
            if tags and not set(tags) & set(it["tags"]):
                continue
            overlap = len(q & _words(it["text"]))
            if overlap:
                scored.append((overlap, idx, it))
        scored.sort(key=lambda x: (-x[0], -x[1]))
        results = [SimpleNamespace(text=it["text"], type="experience", tags=it["tags"], id=it["id"],
                                   mentioned_at=it["mentioned_at"], occurred_start=None)
                   for _s, _i, it in scored]
        return SimpleNamespace(results=results)

    def reflect(self, bank_id, query, response_schema=None, **kwargs):
        self._maybe_fail("reflect")
        prefs = [it["text"] for it in self.items if it["bank"] == bank_id and "preference" in it["tags"]]
        text = "\n".join(f"- {p}" for p in prefs) or "No preferences recorded yet."
        return SimpleNamespace(text=text, structured_output={"rules": []} if response_schema else None)

    def list_memories(self, bank_id, limit=100, **kwargs):
        self._maybe_fail("list_memories")
        items = [SimpleNamespace(text=it["text"], type="experience", tags=it["tags"], id=it["id"],
                                 mentioned_at=it["mentioned_at"], occurred_start=None)
                 for it in self.items if it["bank"] == bank_id]
        return SimpleNamespace(items=items[-limit:])
