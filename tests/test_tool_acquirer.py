"""Tool acquisition — install a library, clone+inspect a repo (read-only),
scaffold a tool. It must validate inputs, never pass junk to pip, only clone
allowed public hosts, and never execute downloaded code.
"""
import asyncio
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools.tool_acquirer import ToolAcquirer


@pytest.fixture
def acq(tmp_path, monkeypatch):
    monkeypatch.setenv("TOM_WORKSPACE_DIR", str(tmp_path / "ws"))
    return ToolAcquirer()


# ── install_package: validation + subprocess handling ───────────────────────

@pytest.mark.parametrize("bad", [
    "requests; rm -rf /",
    "requests && evil",
    "https://evil/x",
    "../../etc/passwd",
    "two words",
    "",
])
def test_install_rejects_bad_specs_without_calling_pip(acq, bad, monkeypatch):
    called = {"ran": False}
    monkeypatch.setattr("subprocess.run", lambda *a, **k: called.__setitem__("ran", True))
    res = acq.install_package(bad)
    assert res["status"] == "error"
    assert called["ran"] is False


def test_install_valid_name_runs_pip_and_reports_success(acq, monkeypatch):
    def fake_run(args, **kwargs):
        assert args[:4] == [sys.executable, "-m", "pip", "install"]
        return types.SimpleNamespace(returncode=0, stdout="Successfully installed requests", stderr="")
    monkeypatch.setattr("subprocess.run", fake_run)
    res = acq.install_package("requests")
    assert res["status"] == "success"
    assert res["package"] == "requests"


def test_install_reports_pip_failure(acq, monkeypatch):
    monkeypatch.setattr("subprocess.run",
                        lambda *a, **k: types.SimpleNamespace(returncode=1, stdout="", stderr="No matching distribution"))
    res = acq.install_package("totallynotarealpkg999")
    assert res["status"] == "error"


# ── clone_repo: host allowlist + read-only ───────────────────────────────────

def test_clone_refuses_non_allowed_hosts(acq):
    assert acq.clone_repo("https://evil.example.com/x")["status"] == "blocked"
    assert acq.clone_repo("http://github.com/a/b")["status"] == "blocked"  # not https
    assert acq.clone_repo("git@github.com:a/b.git")["status"] == "blocked"


def test_clone_allowed_host_reads_but_does_not_run(acq, monkeypatch):
    def fake_run(args, **kwargs):
        # Simulate git clone: create the dest dir with a README.
        dest = args[-1]
        os.makedirs(dest, exist_ok=True)
        with open(os.path.join(dest, "README.md"), "w", encoding="utf-8") as f:
            f.write("# Demo repo\nHello.")
        with open(os.path.join(dest, "main.py"), "w", encoding="utf-8") as f:
            f.write("print('should never run')")
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr("subprocess.run", fake_run)
    res = acq.clone_repo("https://github.com/owner/demo")
    assert res["status"] == "success"
    assert "Demo repo" in res["message"]
    assert "main.py" in res["files"]
    # The clone is on disk but nothing from it was executed (no exception, and
    # the module was never imported — presence on disk is all we assert).
    assert os.path.isdir(res["path"])


def test_clone_handles_missing_git(acq, monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError("git not found")
    monkeypatch.setattr("subprocess.run", boom)
    res = acq.clone_repo("https://github.com/owner/demo")
    assert res["status"] == "error"
    assert "git" in res["message"].lower()


# ── save_tool: writes for review, no execution ───────────────────────────────

def test_save_tool_writes_a_module(acq):
    res = acq.save_tool("CSV Converter", "def convert():\n    return True")
    assert res["status"] == "success"
    assert os.path.isfile(res["path"])
    body = open(res["path"], encoding="utf-8").read()
    assert "Acquired tool" in body and "def convert" in body


def test_save_tool_rejects_empty_code(acq):
    assert acq.save_tool("x", "   ")["status"] == "error"


def test_list_acquired_runs(acq):
    assert acq.list_acquired()["status"] == "success"


# ── agent-level detection + extraction (pure) ────────────────────────────────

def test_agent_detects_acquire_requests():
    from agent import TomAgent as T
    assert T._is_acquire_tool_request("install requests")
    assert T._is_acquire_tool_request("pip install numpy==1.26")
    assert T._is_acquire_tool_request("install the pandas library")
    assert T._is_acquire_tool_request("get the parser from github.com/owner/repo")
    assert T._is_acquire_tool_request("build a tool that converts csv to json")
    assert T._is_acquire_tool_request("list acquired tools")
    assert not T._is_acquire_tool_request("remove duplicates from the data")
    assert not T._is_acquire_tool_request("make a website for my shop")
    # Regression: an email address whose domain is a forge must NOT be read as a
    # clone request (bare "github.com" lives inside boss@github.com).
    assert not T._is_acquire_tool_request("write an email to boss@github.com for sick leave")
    assert not T._is_acquire_tool_request("send an email to x@gitlab.com saying hello")
    assert not T._is_acquire_tool_request("email the team about our github.com migration")


@pytest.mark.parametrize("cmd,pkg", [
    ("install requests", "requests"),
    ("pip install numpy==1.26", "numpy==1.26"),
    ("install the pandas library", "pandas"),
    ("add the httpx package", "httpx"),
])
def test_extract_package(cmd, pkg):
    from agent import TomAgent as T
    assert T._extract_package(cmd) == pkg
