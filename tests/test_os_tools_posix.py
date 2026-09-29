"""App discovery/launch on Linux/macOS (Windows keeps its own discovery chain)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import stat

import pytest

from tools.os_tools import OSTools

pytestmark = pytest.mark.skipif(os.name == "nt", reason="POSIX launch paths")


def _script(directory, name, body):
    path = directory / name
    path.write_text("#!/bin/sh\n" + body + "\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


@pytest.fixture
def env(tmp_path, monkeypatch):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}/usr/bin{os.pathsep}/bin")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "platform", "linux")
    apps = tmp_path / "applications"
    apps.mkdir()
    monkeypatch.setattr(OSTools, "_desktop_dirs", staticmethod(lambda: [str(apps)]))
    return SimpleNamespaceLike(bin=bindir, apps=apps, marker=tmp_path / "marker")


class SimpleNamespaceLike:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _open(name):
    return asyncio.run(OSTools().open_application(name))


def test_program_on_path_is_launched(env):
    _script(env.bin, "notepadish", f"echo started > {env.marker}")
    result = _open("notepadish")
    assert result["status"] == "success", result
    assert env.marker.read_text().strip() == "started"


def test_program_that_dies_immediately_is_not_reported_as_opened(env):
    _script(env.bin, "brokenapp", "exit 3")
    result = _open("brokenapp")
    assert result["status"] == "error" and "code 3" in result["message"]


def test_desktop_entry_is_found_by_its_display_name_and_launched(env):
    (env.apps / "org.fancy.Chat.desktop").write_text("[Desktop Entry]\nType=Application\nName=Fancy Chat\nExec=fancy\n")
    _script(env.bin, "gtk-launch", f'echo "$1" > {env.marker}')
    result = _open("fancy chat")
    assert result["status"] == "success", result
    assert env.marker.read_text().strip() == "org.fancy.Chat"


def test_unknown_app_reports_not_found(env):
    result = _open("definitely-not-installed-xyz")
    assert result["status"] == "error" and "Could not find" in result["message"]


def test_missing_launcher_for_desktop_entry_is_reported(env, monkeypatch):
    (env.apps / "solo.desktop").write_text("[Desktop Entry]\nName=Solo App\n")
    monkeypatch.setenv("PATH", str(env.bin))          # no gtk-launch / gio anywhere
    result = _open("solo app")
    assert result["status"] == "error" and "launcher" in result["message"]


def test_posix_system_trees_are_protected():
    from safety.guards import SafetyGuards
    guard = SafetyGuards()
    for path in ("/etc/passwd", "/usr/bin", "/bin", "/sys/kernel", "/System/Library", "/"):
        assert guard.check_file_path_safe(path) is False, path
    for path in ("/tmp/x", "/home/me/Downloads", "/mnt/data", "/Users/me/Downloads"):
        assert guard.check_file_path_safe(path) is True, path
