"""Folder requests must follow what the user said - the whole sentence, not a few keywords."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import file_ops
from tools.approval import ApprovalManager
from tools.engine_router import EngineRouter


@pytest.fixture
def machine(tmp_path, monkeypatch):
    """A 'laptop': a real Downloads folder, plus a sandbox folder that is ALSO called Downloads."""
    home = tmp_path / "home"
    real = home / "Downloads"
    sandbox = home / "OneDrive" / "Desktop" / "TOM" / "demo" / "sandbox" / "Downloads"
    desktop = home / "Desktop"
    for folder in (real, sandbox, desktop):
        folder.mkdir(parents=True)
    for name in ("real1.pdf", "real2.jpg", "real3.txt"):
        (real / name).write_text("x")
    for name in ("box1.pdf", "box2.pdf", "box3.png"):
        (sandbox / name).write_text("x")
    (desktop / "slides.pptx").write_text("x")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    for key in ("TOM_DOWNLOADS_DIR", "TOM_DESKTOP_DIR", "TOM_DOCUMENTS_DIR"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(file_ops, "JOURNAL_PATH", tmp_path / "journal.json")
    return SimpleNamespace(home=home, real=real, sandbox=sandbox, desktop=desktop)


def router(llm=None, answer=True):
    asked = []
    mgr = ApprovalManager()
    mgr.provider = lambda req: asked.append(req.summary) or answer
    engine = EngineRouter()
    engine._agent = SimpleNamespace(approval_manager=mgr, fast_llm=llm, llm=llm)
    return engine, asked


def run(engine, command):
    return asyncio.run(engine.execute(command))


def names(folder):
    return sorted(str(p.relative_to(folder)) for p in Path(folder).rglob("*") if p.is_file())


# ── the reported bug ─────────────────────────────────────────────────────────
def test_an_explicit_path_ending_in_downloads_is_not_swapped_for_the_real_downloads(machine):
    assert file_ops.resolve_folder(str(machine.sandbox)) == str(machine.sandbox)
    assert file_ops.resolve_folder("downloads") == str(machine.real)         # bare names still work
    assert file_ops.resolve_folder("my downloads") == str(machine.real)
    assert file_ops.resolve_folder("the Downloads folder") == str(machine.real)


def test_the_sentence_from_the_report_organizes_the_sandbox_and_leaves_the_real_folder_alone(machine):
    engine, asked = router()
    command = ('Hi Tom can you organize the files in my downloads folder That is at this '
               f'location :"{machine.sandbox}".')
    result = run(engine, command)
    assert result["status"] == "success", result
    assert names(machine.sandbox) == ["Documents/box1.pdf", "Documents/box2.pdf", "Images/box3.png"]
    assert names(machine.real) == ["real1.pdf", "real2.jpg", "real3.txt"]     # never touched
    assert str(machine.sandbox) in asked[0]                                  # the approval names the folder


def test_an_unquoted_path_and_a_trailing_full_stop_work_too(machine):
    engine, _ = router()
    run(engine, f"organize the files in {machine.sandbox}.")
    assert (machine.sandbox / "Documents" / "box1.pdf").exists() and (machine.real / "real1.pdf").exists()


def test_a_path_that_does_not_exist_is_reported_never_replaced_by_a_default(machine):
    engine, asked = router()
    missing = machine.home / "nope" / "Downloads"
    result = run(engine, f'organize the files in my downloads folder at "{missing}"')
    assert "not found" in result["message"].lower() and str(missing) in result["message"]
    assert not asked and names(machine.real) == ["real1.pdf", "real2.jpg", "real3.txt"]


def test_the_env_override_only_applies_to_bare_folder_names(machine, monkeypatch):
    monkeypatch.setenv("TOM_DOWNLOADS_DIR", str(machine.sandbox))
    assert file_ops.resolve_folder("downloads") == str(machine.sandbox)
    other = machine.home / "elsewhere" / "Downloads"
    other.mkdir(parents=True)
    assert file_ops.resolve_folder(str(other)) == str(other)                 # an explicit path always wins


def test_a_bare_folder_word_that_does_not_exist_is_never_resolved_relative_to_the_cwd(machine, monkeypatch, tmp_path):
    for f in list(machine.real.iterdir()):
        f.unlink()
    machine.real.rmdir()
    cwd = tmp_path / "cwd"
    (cwd / "downloads").mkdir(parents=True)
    (cwd / "downloads" / "stray.pdf").write_text("x")
    monkeypatch.chdir(cwd)
    engine, asked = router()
    result = run(engine, "organize my downloads folder")
    assert "not found" in result["message"].lower() and not asked
    assert (cwd / "downloads" / "stray.pdf").exists()


def test_no_folder_in_the_request_asks_instead_of_guessing_downloads(machine):
    engine, asked = router()
    result = run(engine, "organize my files by type")
    assert "which folder" in result["message"].lower() and not asked
    assert names(machine.real) == ["real1.pdf", "real2.jpg", "real3.txt"]


# ── undo follows the last organization, wherever it happened ─────────────────
def test_undo_without_a_folder_reverts_the_most_recent_organization(machine):
    engine, _ = router()
    run(engine, f'organize the files in "{machine.sandbox}"')
    assert not (machine.sandbox / "box1.pdf").exists()
    result = run(engine, "revert the changes that you just made")
    assert result["status"] == "success", result
    assert names(machine.sandbox) == ["box1.pdf", "box2.pdf", "box3.png"]
    assert names(machine.real) == ["real1.pdf", "real2.jpg", "real3.txt"]     # not touched by the undo


# ── understanding the whole sentence (with an LLM) ───────────────────────────
class FakeLLM:
    def __init__(self, payload):
        self.payload, self.calls = payload, []

    async def ainvoke(self, messages):
        self.calls.append(messages)
        text = self.payload if isinstance(self.payload, str) else json.dumps(self.payload)
        return SimpleNamespace(content=text)


def test_the_llm_fills_in_what_the_keyword_rules_cannot(machine):
    llm = FakeLLM({"operation": "move", "folder_text": "Desktop", "file_types": ["presentations"],
                   "destination_folder": "Decks"})
    engine, asked = router(llm)
    result = run(engine, "could you please gather all my slide decks that are sitting on the Desktop into a folder called Decks")
    assert result["status"] == "success", result
    assert (machine.desktop / "Decks" / "slides.pptx").exists()
    assert llm.calls, "the model was never asked"


def test_a_folder_the_llm_invents_is_rejected(machine):
    llm = FakeLLM({"operation": "organize", "folder_text": "C:\\Windows\\System32", "organize_by": "type"})
    engine, asked = router(llm)
    result = run(engine, "organize the stuff in my downloads folder")
    assert names(machine.real) != [] and (machine.real / "real1.pdf").parent.exists()
    assert str(machine.real) in asked[0] and "System32" not in asked[0]       # fell back to what the user said


def test_the_users_own_path_beats_whatever_the_llm_says(machine):
    llm = FakeLLM({"operation": "organize", "folder_text": "downloads", "organize_by": "type"})
    engine, _ = router(llm)
    run(engine, f'organize the files in my downloads folder at "{machine.sandbox}"')
    assert (machine.sandbox / "Documents" / "box1.pdf").exists() and (machine.real / "real1.pdf").exists()


@pytest.mark.parametrize("payload", ["not json at all", "{broken", {"operation": "delete_everything", "folder_text": "downloads"}])
def test_bad_llm_output_falls_back_to_the_rules(machine, payload):
    engine, asked = router(FakeLLM(payload))
    result = run(engine, "organize my downloads folder by type")
    assert result["status"] == "success" and (machine.real / "Documents" / "real1.pdf").exists()


def test_a_failing_llm_never_blocks_the_task(machine):
    class Down:
        async def ainvoke(self, messages):
            raise ConnectionError("model server unreachable")
    engine, _ = router(Down())
    assert run(engine, "organize my downloads folder by type")["status"] == "success"


def test_the_llm_cannot_turn_a_find_into_moves(machine):
    llm = FakeLLM({"operation": "organize", "folder_text": "downloads"})
    engine, asked = router(llm)
    result = run(engine, "find all pdfs in downloads")
    assert not asked and "Found" in result["message"] and (machine.real / "real1.pdf").exists()


# ── through the whole agent, as the desktop app runs it ──────────────────────
@pytest.fixture
def agent(machine, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOM_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("HINDSIGHT_ENABLED", "0")
    from agent import TomAgent
    tom = TomAgent()
    tom.asked = []
    tom.approval_manager.provider = lambda req: tom.asked.append(req.summary) or True

    async def regex_only(command):
        return tom.nlp_parser.parse(command)
    monkeypatch.setattr(tom, "understand_command", regex_only)
    return tom


def test_the_agent_works_in_the_folder_named_in_the_sentence(agent, machine):
    command = ('Hi Tom can you organize the files in my downloads folder That is at this '
               f'location :"{machine.sandbox}".')
    result = asyncio.run(agent.execute_task(command))
    assert result["status"] == "success", result
    assert names(machine.sandbox) == ["Documents/box1.pdf", "Documents/box2.pdf", "Images/box3.png"]
    assert names(machine.real) == ["real1.pdf", "real2.jpg", "real3.txt"]
    assert len(agent.asked) == 1 and str(machine.sandbox) in agent.asked[0]


def test_unusual_wording_reaches_the_file_engine_when_the_model_says_it_is_a_file_request(agent, machine, monkeypatch):
    async def understood(command):
        parsed = agent.nlp_parser.parse(command)
        parsed["intent"] = "file_operation"
        return parsed
    monkeypatch.setattr(agent, "understand_command", understood)
    agent.fast_llm = FakeLLM({"operation": "move", "folder_text": "Desktop", "file_types": ["slide decks"],
                              "destination_folder": "Decks"})
    result = asyncio.run(agent.execute_task("arrange my slide decks that are on the Desktop into a folder called Decks"))
    assert result["status"] == "success", result
    assert (machine.desktop / "Decks" / "slides.pptx").exists()
