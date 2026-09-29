"""Natural-language file requests -> approved plan -> files really move (and undo)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import file_ops
from tools.approval import ApprovalManager
from tools.engine_router import EngineRouter

NAMES = ["a.pdf", "b.pdf", "photo.jpg", "song.mp3", "notes.txt", "setup.exe", "data.csv"]


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    folders = {}
    for name in ("Downloads", "Documents", "Desktop"):
        path = tmp_path / name
        path.mkdir()
        monkeypatch.setenv(f"TOM_{name.upper()}_DIR", str(path))
        folders[name] = path
    for n in NAMES:
        (folders["Downloads"] / n).write_text("x")
    (folders["Documents"] / "keep.pdf").write_text("x")
    monkeypatch.setattr(file_ops, "JOURNAL_PATH", tmp_path / "journal.json")
    return folders


def _router(answer=True):
    asked = []
    mgr = ApprovalManager()
    mgr.provider = lambda req: asked.append(req.summary) or answer
    router = EngineRouter()
    router._agent = SimpleNamespace(approval_manager=mgr)
    return router, asked


def _run(router, command):
    return asyncio.run(router.execute(command))


def _names(folder):
    return sorted(str(p.relative_to(folder)) for p in Path(folder).rglob("*") if p.is_file())


@pytest.mark.parametrize("command", [
    "move the pdfs in downloads to Invoices",
    "put my pdfs in downloads into a folder called Invoices",
    "move all pdfs in downloads into a folder named Invoices",
])
def test_move_request_moves_only_the_named_type_into_the_named_folder(sandbox, command):
    router, asked = _router()
    result = _run(router, command)
    assert result["status"] == "success", result
    assert _names(sandbox["Downloads"]) == sorted(
        ["Invoices/a.pdf", "Invoices/b.pdf", "photo.jpg", "song.mp3", "notes.txt", "setup.exe", "data.csv"])
    assert _names(sandbox["Documents"]) == ["keep.pdf"]          # other folders untouched
    assert len(asked) == 1 and "2 .pdf" in asked[0]              # approval named the exact count


def test_move_request_by_group(sandbox):
    router, _ = _router()
    assert _run(router, "move all my photos in downloads into a Pics folder")["status"] == "success"
    assert (sandbox["Downloads"] / "Pics" / "photo.jpg").is_file()


def test_declined_move_touches_nothing(sandbox):
    router, asked = _router(answer=False)
    result = _run(router, "move the pdfs in downloads to Invoices")
    assert result["status"] == "cancelled" and asked
    assert _names(sandbox["Downloads"]) == sorted(NAMES)


def test_move_without_a_destination_asks_instead_of_guessing(sandbox):
    router, asked = _router()
    result = _run(router, "move the pdfs in downloads to my desktop")
    assert "subfolder" in result["message"] and not asked
    assert _names(sandbox["Downloads"]) == sorted(NAMES)


def test_organize_then_undo_restores_everything(sandbox):
    router, _ = _router()
    assert _run(router, "organize my downloads folder by type")["status"] == "success"
    assert not (sandbox["Downloads"] / "a.pdf").exists()
    assert _run(router, "undo the last organization in downloads")["status"] == "success"
    assert _names(sandbox["Downloads"]) == sorted(NAMES)


@pytest.mark.parametrize("command,expected", [
    ("organize my pdf documents in downloads", "Downloads"),        # "documents" describes the files
    ("organize my documents folder", "Documents"),
    ("organize files by type/year in downloads", "Downloads"),      # "/year" is not a path
    ("move files from desktop to downloads", "desktop"),
    ("organize ~/Music/albums", "~/Music/albums"),
    ('tidy "D:\\Stuff\\Old" folder', "D:\\Stuff\\Old"),
])
def test_folder_is_the_one_the_user_meant(command, expected):
    assert EngineRouter._pick_folder(command).lower() == expected.lower()


@pytest.mark.parametrize("command", [
    "move the mouse to 100 100", "move to the next slide", "move the slides to the right",
    "put the milk to the fridge", "transfer money to john", "i moved my files yesterday",
])
def test_move_wording_does_not_hijack_other_requests(command):
    assert EngineRouter().detect(command.lower()) != "fileops"


def test_protected_system_folders_are_never_planned(tmp_path, monkeypatch):
    from safety.guards import SafetyGuards
    monkeypatch.setattr(SafetyGuards, "check_file_path_safe", lambda self, path: False)
    ops = file_ops.FileOps()
    (tmp_path / "x.pdf").write_text("x")
    for plan in (ops.plan_organize_by_type(str(tmp_path)),
                 ops.plan_move_by_extension(str(tmp_path), ".pdf", "P"),
                 ops.plan_move_by_group(str(tmp_path), "Images", "P"),
                 ops.plan_bulk_rename(str(tmp_path), "x", "y")):
        assert plan["status"] == "error" and "protected" in plan["message"]
    assert (tmp_path / "x.pdf").exists()


def test_windows_system_paths_are_recognised_as_protected():
    from safety.guards import SafetyGuards
    guard = SafetyGuards()
    for path in ("C:\\Windows\\System32", "c:/program files/app", "C:\\ProgramData\\x"):
        assert guard.check_file_path_safe(path) is False
