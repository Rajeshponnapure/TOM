"""Long-term memory (Hindsight) — unit + end-to-end behaviour tests.

No network: tests/fake_hindsight.py stands in for the real client.
The end-to-end test drives TomAgent with a scripted LLM and proves the core
promise: a correction given once changes what TOM does next time, even when
the new request is worded differently.
"""

import asyncio
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fake_hindsight import FakeHindsight  # noqa: E402
from tools import memory_rules  # noqa: E402
from tools.hindsight_memory import HindsightMemory, TAG_PREFERENCE  # noqa: E402


@pytest.fixture
def memory(tmp_path):
    mem = HindsightMemory(client=FakeHindsight(), bank_id="test-bank", state_dir=tmp_path / "mem")
    mem.enabled = True
    return mem


# ── memory layer ────────────────────────────────────────────────────────
def test_retain_then_recall_round_trip(memory):
    memory.retain("The user wants PDFs sorted into Invoices", tags=[TAG_PREFERENCE, "file_organization"])
    memory.flush()
    hits = memory.recall("where do PDFs go?")
    assert hits and "Invoices" in hits[0].text
    assert hits[0].is_preference
    assert memory.status()["retained"] == 1


def test_recall_filters_by_tag(memory):
    memory.retain("TOM organized Downloads; PDFs went to Documents", tags=["task"], wait=True)
    memory.retain("Always put PDFs in Invoices", tags=[TAG_PREFERENCE], wait=True)
    hits = memory.recall("PDFs", tags=[TAG_PREFERENCE])
    assert [h.text for h in hits] == ["Always put PDFs in Invoices"]


def test_offline_retains_queue_and_flush_later(tmp_path):
    client = FakeHindsight(fail=True)
    mem = HindsightMemory(client=client, bank_id="b", state_dir=tmp_path)
    mem.enabled = True
    assert mem.retain("never move installers", tags=[TAG_PREFERENCE], wait=True) is False
    assert mem.pending_count() == 1
    assert mem.recall("installers") == []          # degrades, never raises
    assert "recall" in mem.last_error
    client.fail = False
    assert mem.flush_pending() == 1
    assert mem.pending_count() == 0
    assert mem.recall("installers")[0].text == "never move installers"


def test_unconfigured_memory_is_safe(tmp_path, monkeypatch):
    monkeypatch.delenv("HINDSIGHT_API_KEY", raising=False)
    monkeypatch.delenv("HINDSIGHT_BASE_URL", raising=False)
    mem = HindsightMemory(bank_id="b", state_dir=tmp_path)
    assert not mem.available
    assert "HINDSIGHT_API_KEY" in mem.status_line()
    assert mem.recall("anything") == []
    assert mem.reflect("anything")["ok"] is False
    mem.retain("kept for later", tags=[TAG_PREFERENCE])
    assert mem.pending_count() == 1                   # synced once configured
    assert mem.recent_journal()[0]["content"] == "kept for later"


# ── rules ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize("text,expected", [
    ("always put PDFs in Invoices, not Documents", [".pdf files → Invoices/"]),
    ("The user wants PDF files in the Downloads folder to always be sorted into the Invoices folder.",
     [".pdf files → Invoices/"]),
    ("Never move installers — leave .exe files where they are.", ["leave installers where they are"]),
    ("Screenshots should go into a folder called Screenshots.", ["files named '*screenshot*' → Screenshots/"]),
    ("The user asked TOM to put images into Photos and videos into Media.", ["images → Photos/", "video → Media/"]),
    ("From now on put invoice PDFs into Finance/2026", ["files named '*invoice*' → Finance/2026/"]),
    ("keep my emails short", []),
    ("TOM moved 14 files in Downloads into Images and Documents subfolders.", []),
])
def test_parse_folder_rules(text, expected):
    assert [r.describe() for r in memory_rules.parse_folder_rules([text])] == expected


def test_structured_rules_from_reflect():
    rules = memory_rules.rules_from_structured(
        {"rules": [{"kind": "ext", "value": "pdf", "action": "move", "dest": "Invoices"},
                   {"kind": "group", "value": "Installers", "action": "skip"},
                   {"kind": "ext", "value": ".zip", "action": "move", "dest": ""}]})
    assert [r.describe() for r in rules] == [".pdf files → Invoices/", "leave installers where they are"]


@pytest.mark.parametrize("text,pure", [
    ("always put PDFs in Invoices", True),
    ("no, keep emails short", True),
    ("Remember that my manager is Priya", True),
    ("from now on sort pdfs into invoices and do it now", False),
    ("organize my downloads", None),
    ("I want a presentation about AI", None),
    ("No — PDFs always go in Invoices, not Documents.", True),
    ("Screenshots belong in Screenshots", True),
    ("No, organize the documents folder instead", False),
    ("write an email that never mentions price", None),
    ("what should I do today", None),
])
def test_preference_detection(text, pure):
    if pure is None:
        assert not memory_rules.is_preference_statement(text)
    else:
        assert memory_rules.is_preference_statement(text)
        assert memory_rules.is_pure_preference(text) is pure


def test_organizer_applies_rules(tmp_path):
    from tools.file_ops import FileOps
    for name in ["invoice_march.pdf", "notes.pdf", "setup.exe", "cat.png", "Screenshot 1.png"]:
        (tmp_path / name).write_text("x")
    rules = memory_rules.parse_folder_rules([
        "Screenshots go into Screenshots", "always put PDFs in Invoices", "never move installers"])
    plan = FileOps().plan_organize_by_type(str(tmp_path), rules=rules)
    dests = {os.path.basename(s): os.path.relpath(os.path.dirname(d), tmp_path) for s, d in plan["moves"]}
    assert dests == {"invoice_march.pdf": "Invoices", "notes.pdf": "Invoices",
                     "cat.png": "Images", "Screenshot 1.png": "Screenshots"}
    assert plan["kept"] == ["setup.exe"]
    assert {a["rule"] for a in plan["applied_rules"]} == {
        ".pdf files → Invoices/", "leave installers where they are", "files named '*screenshot*' → Screenshots/"}


# ── end to end: the before / after ──────────────────────────────────────
def _scripted_llm(reply='{"intent": "chat"}'):
    """A LangChain chat model that always answers `reply` and records prompts."""
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration, ChatResult

    class ScriptedLLM(BaseChatModel):
        reply: str = '{"intent": "chat"}'
        prompts: list = []

        @property
        def _llm_type(self) -> str:
            return "scripted"

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            self.prompts.append("\n".join(str(m.content) for m in messages))
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self.reply))])

    return ScriptedLLM(reply=reply, prompts=[])


@pytest.fixture
def tom(tmp_path, monkeypatch, memory):
    pytest.importorskip("langchain_core")
    try:
        import agent as agent_mod
    except ImportError as exc:  # optional desktop deps missing on CI
        pytest.skip(f"agent imports unavailable: {exc}")
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    monkeypatch.setenv("TOM_DOWNLOADS_DIR", str(downloads))
    from tools import hindsight_memory
    monkeypatch.setattr(hindsight_memory, "_instance", memory)
    a = agent_mod.TomAgent()
    a.memory = memory
    llm = _scripted_llm()
    a.llm = a.fast_llm = a.chat_llm = a.code_llm = llm
    a.nlp_parser.llm = llm
    a.approval_manager.request_approval = lambda req: True
    a._test_llm = llm
    return a, downloads


def _seed(folder, names):
    for n in names:
        (folder / n).write_text("x")


def test_correction_changes_next_run(tom):
    a, downloads = tom
    run = lambda cmd: asyncio.run(a.execute_task(cmd))  # noqa: E731

    # Session 1 — no memory: default grouping, PDFs land in Documents.
    _seed(downloads, ["invoice_march.pdf", "setup.exe", "cat.png"])
    first = run("organize my downloads")
    assert (downloads / "Documents" / "invoice_march.pdf").exists()
    assert (downloads / "Installers" / "setup.exe").exists()
    assert not first.get("memories_used")

    # The user corrects TOM once.
    ack = run("No — always put PDFs in Invoices, and never move installers")
    assert ack["response_type"] == "preference_saved"
    assert ".pdf files → Invoices/" in ack["message"]
    a.memory.flush()

    # Later session, different wording: TOM applies the correction unprompted.
    _seed(downloads, ["bank_statement.pdf", "zoom_installer.exe", "dog.jpg"])
    second = run("tidy up my downloads folder please")
    assert (downloads / "Invoices" / "bank_statement.pdf").exists()
    assert (downloads / "zoom_installer.exe").exists()          # left in place
    assert (downloads / "Images" / "dog.jpg").exists()
    assert second["message"].startswith("Remembering how you like this folder organized")
    assert ".pdf files → Invoices/" in second["memories_used"]

    # Outcomes were retained too, tagged for later recall.
    tags = [t for it in a.memory.client.items for t in it["tags"]]
    assert "task" in tags and "preference" in tags


def test_recalled_preferences_reach_llm_prompts(tom):
    a, _ = tom
    a.memory.retain("The user told TOM a standing instruction: \"keep my emails short and sign off as Rajesh\"",
                    tags=[TAG_PREFERENCE, "email"], wait=True)
    a._test_llm.reply = "SUBJECT: Budget\nBODY:\nHi Ravi, quick note on the budget.\nRajesh"
    result = asyncio.run(a.execute_task("email Ravi about the budget"))
    assert result["status"] == "success"
    assert result["response_type"] == "email_draft"
    assert any("sign off as Rajesh" in p for p in a._test_llm.prompts)   # memory was in the prompt
    assert result["message"].startswith("Remembering from earlier")


def test_memory_commands(tom):
    a, _ = tom
    a.memory.retain("always put PDFs in Invoices", tags=[TAG_PREFERENCE], wait=True)
    learned = asyncio.run(a.execute_task("what have you learned about me?"))
    assert "Invoices" in learned["message"]
    status = asyncio.run(a.execute_task("memory status"))
    assert "Long-term memory: ONLINE" in status["message"]
    recall = asyncio.run(a.execute_task("what do you remember about PDFs"))
    assert "Invoices" in recall["message"]
