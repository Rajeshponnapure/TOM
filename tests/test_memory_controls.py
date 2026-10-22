"""R5 memory: provenance, confidence, retention, and AT-015 — the user inspects, corrects and deletes
memories, and the change holds on the next run."""
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tom_core.memory.local_store import LocalMemoryClient  # noqa: E402
from tools.hindsight_memory import TAG_PREFERENCE, TAG_TASK, HindsightMemory  # noqa: E402


def _client(tmp_path):
    return LocalMemoryClient(tmp_path / "memory.sqlite3")


def _texts(resp):
    return [r.text for r in resp.results]


def test_a_correction_replaces_the_old_memory_everywhere(tmp_path):
    c = _client(tmp_path)
    c.retain("b", "send reports as PDF", tags=[TAG_PREFERENCE])
    old_id = c.list_memories("b").items[0].id
    new_id = c.correct_memory(old_id, "send reports as Word documents")
    assert new_id and new_id != old_id
    assert _texts(c.recall("b", "reports")) == ["send reports as Word documents"]
    assert "PDF" not in c.reflect("b", "rules").text
    old = c.inspect_memory(old_id)
    assert str(old["superseded_by"]) == new_id                       # kept for audit, never used
    new = c.inspect_memory(new_id)
    assert new["confidence"] == 0.95 and new["source"] == "user" and new["provenance"]["corrects"] == old_id
    assert new["expires_at"] is None


def test_a_deleted_memory_never_comes_back(tmp_path):
    c = _client(tmp_path)
    when = "2026-10-01T10:00:00+00:00"
    c.retain("b", "the wifi password is on the fridge", timestamp=when)
    mid = c.list_memories("b").items[0].id
    assert c.delete_memory(mid)
    c.retain("b", "the wifi password is on the fridge", timestamp=when)   # same item replayed (offline queue)
    assert c.list_memories("b").items == []
    assert _client(tmp_path).list_memories("b").items == []                # and after a restart


def test_retention_rules_and_task_history(tmp_path):
    c = _client(tmp_path)
    old = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat(timespec="seconds")
    c.retain("b", "organized downloads last year", tags=[TAG_TASK], timestamp=old)
    c.retain("b", "always reply in English", tags=[TAG_PREFERENCE], timestamp=old)
    assert [i.text for i in c.list_memories("b").items] == ["always reply in English"]
    assert _client(tmp_path).expired == 1                               # pruned on the next start
    rule = c.list_memories("b").items[0]
    assert rule.confidence == 0.9


def test_provenance_records_the_interface_and_task(tmp_path):
    from tom_core.tasks import service
    c = _client(tmp_path)
    t1, t2 = service._current_task.set("task-123"), service._current_interface.set("desktop-qt")
    try:
        c.retain("b", "prefers dark mode", tags=[TAG_PREFERENCE])
    finally:
        service._current_task.reset(t1)
        service._current_interface.reset(t2)
    info = c.inspect_memory(c.list_memories("b").items[0].id)
    assert info["provenance"] == {"source": "tom", "interface": "desktop-qt", "task_id": "task-123"}


def test_a_version_1_store_is_upgraded_in_place(tmp_path):
    db = tmp_path / "memory.sqlite3"
    con = sqlite3.connect(db)
    con.executescript("""
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE memories (id INTEGER PRIMARY KEY, bank_id TEXT NOT NULL, content TEXT NOT NULL, context TEXT,
            tags TEXT NOT NULL DEFAULT '[]', metadata TEXT NOT NULL DEFAULT '{}', document_id TEXT,
            occurred_at TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'tom', UNIQUE (content, occurred_at));
        INSERT INTO meta VALUES ('schema_version', '1');
        INSERT INTO memories (bank_id, content, tags, occurred_at) VALUES ('b', 'old rule', '["preference"]', '2026-01-01');
    """)
    con.commit()
    con.close()
    c = LocalMemoryClient(db)
    items = c.list_memories("b").items
    assert [i.text for i in items] == ["old rule"] and items[0].confidence == 0.6


def _agent_with(tmp_path, monkeypatch):
    monkeypatch.delenv("HINDSIGHT_BASE_URL", raising=False)
    monkeypatch.setenv("HINDSIGHT_ENABLED", "1")
    import agent as agent_mod
    a = agent_mod.TomAgent.__new__(agent_mod.TomAgent)
    a.memory = HindsightMemory(bank_id="b", state_dir=tmp_path)
    return a


def test_at015_chat_commands_inspect_correct_and_forget(tmp_path, monkeypatch):
    a = _agent_with(tmp_path, monkeypatch)
    a.memory.retain("save invoices in Documents", tags=[TAG_PREFERENCE], wait=True)
    a.memory.retain("never email after 10 pm", tags=[TAG_PREFERENCE], wait=True)
    listing = a._memory_controls("show my memories")["message"]
    ids = {h.text: h.id for h in a.memory.list_memories()}
    assert f"#{ids['save invoices in Documents']}" in listing and "confidence 0.90" in listing

    shown = a._memory_controls(f"inspect memory {ids['save invoices in Documents']}")["message"]
    assert "Expires: never" in shown and "source tom" in shown

    fixed = a._memory_controls(f"correct memory {ids['save invoices in Documents']}: save invoices in Finance")
    assert fixed["status"] == "success"
    gone = a._memory_controls(f"forget memory #{ids['never email after 10 pm']}")
    assert gone["status"] == "success"

    # next run: a fresh wrapper over the same store sees only the corrected rule
    later = HindsightMemory(bank_id="b", state_dir=tmp_path)
    assert [h.text for h in later.list_memories()] == ["save invoices in Finance"]
    assert a._memory_controls("forget memory 9999")["status"] == "error"
    assert a._memory_controls("show memories please") is None            # not a control command
