"""Workspace isolation + guarded deletion.

Two behaviours shipped together:
  * user deliverables (sites, scaffolds, docs) build in a Desktop workspace or an
    explicit path the user named -- never scattered inside the TOM repo;
  * deleting a file/folder always warns and asks first, and never touches the TOM
    install, system trees, or top-level personal roots.
"""
import asyncio
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools import project_paths
from tools.file_tools import FileTools
from safety.guards import SafetyGuards


@pytest.fixture
def outside_repo_dir():
    """A scratch dir OUTSIDE the TOM repo.

    pytest's basetemp is configured to .pytest_tmp INSIDE the repo, but the
    deletion guard (correctly) protects everything under the TOM tree — so
    delete-flow tests need a victim that lives elsewhere, like the real
    Desktop workspace would.
    """
    d = tempfile.mkdtemp(prefix="tom_ws_test_")
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ── workspace routing ────────────────────────────────────────────────────────

def test_workspace_root_honours_env_override(tmp_path, monkeypatch):
    target = tmp_path / "ws"
    monkeypatch.setenv("TOM_WORKSPACE_DIR", str(target))
    root = project_paths.workspace_root()
    assert root == target
    assert root.is_dir()


def test_relative_deliverable_lands_in_workspace_not_repo(tmp_path, monkeypatch):
    monkeypatch.setenv("TOM_WORKSPACE_DIR", str(tmp_path / "ws"))
    resolved = project_paths.resolve_deliverable_path("app/index.html", subfolder="My Site")
    assert resolved.startswith(str(tmp_path / "ws"))
    assert "My Site" in resolved
    # Resolved under the workspace, not the current working directory / repo.
    assert os.path.isabs(resolved)


def test_absolute_deliverable_path_is_respected(tmp_path, monkeypatch):
    monkeypatch.setenv("TOM_WORKSPACE_DIR", str(tmp_path / "ws"))
    abs_target = str(tmp_path / "custom" / "report.pdf")
    assert project_paths.resolve_deliverable_path(abs_target) == abs_target


def test_filetools_output_dir_is_the_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("TOM_WORKSPACE_DIR", str(tmp_path / "ws"))
    ft = FileTools()
    assert os.path.normcase(ft.output_dir) == os.path.normcase(str(tmp_path / "ws"))


def test_create_website_builds_under_the_given_root(tmp_path):
    ft = FileTools()
    root = str(tmp_path / "sites")
    res = asyncio.run(ft.create_website("bakery", "<h1>Hi</h1>", "body{}", target_root=root))
    assert res["status"] == "success"
    assert os.path.isfile(os.path.join(root, "bakery", "index.html"))


def test_create_file_lands_in_workspace_not_repo(tmp_path, monkeypatch):
    monkeypatch.setenv("TOM_WORKSPACE_DIR", str(tmp_path / "ws"))
    from agent import TomAgent
    tom = TomAgent.__new__(TomAgent)
    tom.file_tools = FileTools()
    res = asyncio.run(tom.execute_file_command("create a file notes.txt",
                                               {"file_name": "notes.txt"}))
    assert res["status"] == "success"
    assert os.path.isfile(str(tmp_path / "ws" / "notes.txt"))
    # Not written into the repo working directory.
    assert not os.path.isfile(os.path.join(os.getcwd(), "notes.txt"))


# ── deletion guard ───────────────────────────────────────────────────────────

@pytest.fixture
def guard():
    return SafetyGuards()


def test_project_root_is_protected_from_deletion(guard):
    protected, reason = guard.is_protected_from_deletion(str(project_paths.PROJECT_ROOT))
    assert protected and "TOM" in reason


def test_tom_source_file_is_protected(guard):
    # "delete agent.py" must never resolve to self-destruction.
    protected, _ = guard.is_protected_from_deletion(str(project_paths.PROJECT_ROOT / "agent.py"))
    assert protected


def test_drive_root_and_home_are_protected(guard):
    assert guard.is_protected_from_deletion("C:\\")[0]
    assert guard.is_protected_from_deletion(os.path.expanduser("~"))[0]


def test_system_dir_is_protected(guard):
    assert guard.is_protected_from_deletion("C:\\Windows\\System32")[0]


def test_an_ordinary_workspace_file_is_deletable(guard, outside_repo_dir):
    f = os.path.join(outside_repo_dir, "old_project")
    os.makedirs(f)
    protected, _ = guard.is_protected_from_deletion(f)
    assert not protected


# ── delete flow (approval-gated) ─────────────────────────────────────────────

class _Approver:
    """Stand-in for ApprovalManager: records requests, returns a fixed answer."""
    def __init__(self, answer):
        self.answer = answer
        self.requests = []

    def request_approval(self, request):
        self.requests.append(request)
        return self.answer


def test_delete_asks_before_removing_and_can_be_cancelled(outside_repo_dir):
    victim = os.path.join(outside_repo_dir, "keep.txt")
    with open(victim, "w", encoding="utf-8") as f:
        f.write("data")
    approver = _Approver(answer=False)  # user says "no"
    res = asyncio.run(FileTools().delete_path(victim, approval_manager=approver))
    assert res["status"] == "cancelled"
    assert os.path.exists(victim)     # untouched
    assert approver.requests          # it DID ask


def test_delete_removes_after_approval(outside_repo_dir):
    victim = os.path.join(outside_repo_dir, "junk")
    os.makedirs(victim)
    with open(os.path.join(victim, "a.txt"), "w", encoding="utf-8") as f:
        f.write("x")
    approver = _Approver(answer=True)  # user says "yes"
    res = asyncio.run(FileTools().delete_path(victim, approval_manager=approver,
                                              to_trash=False))
    assert res["status"] == "success"
    assert not os.path.exists(victim)


def test_delete_refuses_protected_target_even_with_approval(tmp_path):
    approver = _Approver(answer=True)
    res = asyncio.run(FileTools().delete_path(str(project_paths.PROJECT_ROOT),
                                              approval_manager=approver))
    assert res["status"] == "blocked"
    assert project_paths.PROJECT_ROOT.exists()
    assert not approver.requests  # blocked BEFORE ever asking


def test_delete_reports_missing_path_cleanly(tmp_path):
    res = asyncio.run(FileTools().delete_path(str(tmp_path / "nope"),
                                              approval_manager=_Approver(True)))
    assert res["status"] == "error"
    assert "does not exist" in res["message"]
