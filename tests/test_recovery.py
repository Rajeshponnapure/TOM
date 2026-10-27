"""FR-012: every file TOM changes can be undone — one journal (tom_core.recovery), "undo your last change".
State lives under the test session's TOM_STATE_ROOT (conftest); nothing goes to the real Recycle Bin."""
import asyncio
import os
import time

import pytest

from tom_core import recovery
from tom_core.tools import builtin


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(recovery, "_dir", lambda: str(tmp_path / "recovery"))
    os.makedirs(tmp_path / "recovery", exist_ok=True)

    def fake_recycle(p):                                           # never the owner's real Recycle Bin
        import shutil
        (shutil.rmtree if os.path.isdir(p) else os.remove)(p)
        return True
    monkeypatch.setattr(builtin, "_recycle", fake_recycle)
    monkeypatch.setenv("TOM_WORKSPACE_ROOTS", str(tmp_path))
    yield


def test_an_overwritten_file_comes_back(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("original")
    assert builtin.write_text(str(f), "changed", overwrite=True)["status"] == "success"
    assert recovery.undo()["status"] == "success" and f.read_text() == "original"


def test_a_new_file_is_removed_and_a_new_folder_too(tmp_path):
    d = tmp_path / "poems"
    builtin.make_dir(str(d))
    builtin.write_text(str(d / "a.txt"), "x")
    recovery.undo()                                                # the file
    assert not (d / "a.txt").exists() and d.exists()
    recovery.undo()                                                # then the empty folder
    assert not d.exists()


def test_a_deleted_file_is_restored_from_the_copy_kept_first(tmp_path):
    f = tmp_path / "report.docx"
    f.write_bytes(b"precious")
    assert builtin.delete_path(str(f))["status"] == "success" and not f.exists()
    assert recovery.undo()["status"] == "success" and f.read_bytes() == b"precious"


def test_a_move_is_reversed(tmp_path):
    src, dst = tmp_path / "a.txt", tmp_path / "sub" / "a.txt"
    src.write_text("x")
    builtin.move_path(str(src), str(dst))
    recovery.undo()
    assert src.exists() and not dst.exists()


def test_a_folder_with_new_contents_is_left_alone(tmp_path):
    d = tmp_path / "keep"
    builtin.make_dir(str(d))
    (d / "mine.txt").write_text("owner's file")
    res = recovery.undo()
    assert res["status"] == "error" and (d / "mine.txt").exists()


def test_documents_and_websites_are_recorded_as_created():
    recovery.record("create", path="C:/W/proposal.docx")
    assert recovery.describe(recovery.entries(1)[0]) == "created C:/W/proposal.docx"


def test_edits_after_toms_change_are_detected(tmp_path):
    f = tmp_path / "n.txt"
    builtin.write_text(str(f), "tom")
    e = recovery.entries(1)[0]
    assert recovery.changed_since(e) is False
    later = time.time() + 60
    os.utime(f, (later, later))
    assert recovery.changed_since(e) is True


def _agent():
    from agent import TomAgent
    return TomAgent.__new__(TomAgent)


def test_the_owner_can_list_and_undo_changes_by_asking(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("v1")
    builtin.write_text(str(f), "v2", overwrite=True)
    builtin.write_text(str(tmp_path / "b.txt"), "new")
    a = _agent()
    listed = asyncio.run(a._recovery_command("show your recent changes"))
    assert "1." in listed["message"] and "b.txt" in listed["message"].split("\n")[1]
    assert asyncio.run(a._recovery_command("undo change 2"))["status"] == "success"
    assert f.read_text() == "v1" and (tmp_path / "b.txt").exists()
    assert asyncio.run(a._recovery_command("undo your last change"))["status"] == "success"
    assert not (tmp_path / "b.txt").exists()
    assert asyncio.run(a._recovery_command("undo"))["status"] == "error"          # nothing left


def test_undo_asks_first_and_a_no_changes_nothing(tmp_path, monkeypatch):
    from tom_core.tools import guard
    monkeypatch.setattr(guard, "_approval_manager", type("No", (), {"request_approval": lambda s, r, p=None: False})())
    f = tmp_path / "keep.txt"
    builtin.write_text(str(f), "x")
    res = asyncio.run(_agent()._recovery_command("undo your last change"))
    assert res["status"] != "success" and f.exists()


def test_other_undo_requests_are_not_taken():
    a = _agent()
    for text in ("undo the organization of my downloads", "undo my email", "what is undo"):
        assert asyncio.run(a._recovery_command(text)) is None
