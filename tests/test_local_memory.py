"""On-machine long-term memory (tom_core.memory.local_store) behind the existing HindsightMemory wrapper."""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tom_core.memory.local_store import LocalMemoryClient  # noqa: E402
from tools.hindsight_memory import TAG_CORRECTION, TAG_PREFERENCE, TAG_TASK, HindsightMemory  # noqa: E402


def _client(tmp_path, **kw):
    return LocalMemoryClient(tmp_path / "memory.sqlite3", **kw)


def test_retain_and_recall_with_word_stemming(tmp_path):
    c = _client(tmp_path)
    c.retain("b", "always put PDFs in Invoices, not Documents", tags=[TAG_PREFERENCE])
    c.retain("b", "Organized Downloads: 3 files moved", tags=[TAG_TASK])
    hits = c.recall("b", "where should my pdf invoice files go?").results
    assert hits and hits[0].text == "always put PDFs in Invoices, not Documents"
    assert hits[0].type == "opinion"
    assert c.recall("b", "the and for").results == []          # only stopwords → nothing, no error


def test_tag_filter_and_bank_isolation(tmp_path):
    c = _client(tmp_path)
    c.retain("b", "never move installers", tags=[TAG_CORRECTION])
    c.retain("b", "moved installers yesterday", tags=[TAG_TASK])
    c.retain("other-bank", "installers belong in Apps", tags=[TAG_PREFERENCE])
    hits = c.recall("b", "installers", tags=[TAG_PREFERENCE, TAG_CORRECTION]).results
    assert [h.text for h in hits] == ["never move installers"]


def test_journal_is_imported_once_and_left_untouched(tmp_path):
    journal = tmp_path / "journal.jsonl"
    rows = [{"content": "my manager is Priya", "tags": [TAG_PREFERENCE], "timestamp": "2026-09-28T10:00:00+00:00"},
            {"content": "PDFs go in Invoices", "tags": [TAG_CORRECTION], "timestamp": "2026-09-29T10:00:00+00:00",
             "metadata": {"user_words": "No — PDFs always go in Invoices"}}]
    journal.write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n", encoding="utf-8")
    before = journal.read_bytes()

    c = _client(tmp_path, seed_journal=journal)
    assert c.seeded == 2
    assert c.recall("any-bank", "who is my manager").results[0].text == "my manager is Priya"
    c.close()
    again = _client(tmp_path, seed_journal=journal)                 # second start: no duplicates
    assert again.seeded == 0 and again.list_memories("b").total == 2
    # The offline queue replays the same item under the real bank id: still stored once.
    again.retain("real-bank", "my manager is Priya", tags=[TAG_PREFERENCE],
                 timestamp=datetime(2026, 9, 28, 10, 0, tzinfo=timezone.utc))
    assert again.list_memories("real-bank").total == 2
    assert journal.read_bytes() == before


def test_reflect_lists_preferences_newest_first_without_structure(tmp_path):
    c = _client(tmp_path)
    c.retain("b", "PDFs go in Documents", tags=[TAG_PREFERENCE],
             timestamp=datetime(2026, 9, 1, tzinfo=timezone.utc))
    c.retain("b", "PDFs go in Invoices", tags=[TAG_CORRECTION], metadata={"user_words": "No, Invoices!"},
             timestamp=datetime(2026, 9, 2, tzinfo=timezone.utc))
    c.retain("b", "Organized Downloads", tags=[TAG_TASK])
    out = c.reflect("b", "what have you learned")
    assert out.text.splitlines() == ["- No, Invoices!", "- PDFs go in Documents"]
    assert out.structured_output is None


def test_delete_removes_it_from_search(tmp_path):
    c = _client(tmp_path)
    c.retain("b", "secret project codename Falcon", tags=[TAG_PREFERENCE])
    hit = c.recall("b", "falcon").results[0]
    assert c.delete_memory(hit.id)
    assert c.recall("b", "falcon").results == []


def test_wrapper_defaults_to_the_local_store(tmp_path, monkeypatch):
    monkeypatch.delenv("HINDSIGHT_BASE_URL", raising=False)
    monkeypatch.setenv("HINDSIGHT_API_KEY", "a-cloud-key-alone-must-not-opt-in")
    monkeypatch.setenv("HINDSIGHT_ENABLED", "1")
    mem = HindsightMemory(bank_id="b", state_dir=tmp_path)
    assert mem.available and mem.is_local
    assert "local store on this machine" in mem.status_line()
    assert mem.retain("always cc Ravi on budget emails", tags=[TAG_PREFERENCE], wait=True)
    assert mem.recall("budget email")[0].text == "always cc Ravi on budget emails"
    assert (tmp_path / "memory.sqlite3").is_file()
    assert mem.reflect("what have you learned")["ok"] is True
