"""tools/blender_control.py::BlenderControl -- every "create/build in Blender"
request used to report success while producing zero files on disk:

  * execute_script() fire-and-forget subprocess.Popen()'d Blender in the
    background and returned "success" the instant the process *launched*,
    without waiting for it to finish, checking its exit code, or reading its
    (DEVNULL'd) stdout/stderr.
  * None of the 15 script templates (cube/sphere/house/terrain/rig/etc, one
    "render" template excepted) ever called bpy.ops.wm.save_as_mainfile() or
    exported/rendered anything -- the whole scene was built in memory and
    discarded the moment Blender's headless process exited.

So "Blender create a house" always claimed success with nothing to show for
it. Blender isn't installed on this dev machine, so these tests fake the
Blender subprocess (matching the real contract: it's invoked as
`blender --background --python <script.py>` and reads a literal
`save_as_mainfile(filepath='...')` call out of that script) rather than
skipping verification entirely.
"""
import asyncio
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import tools.blender_control as bcmod
from tools.blender_control import BlenderControl
from tools.engine_router import EngineRouter


@pytest.fixture
def bc(monkeypatch, tmp_path):
    inst = BlenderControl()
    inst.blender_path = "FAKE_BLENDER"
    monkeypatch.setattr(bcmod, "project_path_str",
                         lambda *parts: str(tmp_path.joinpath(*parts)))
    return inst


ALL_TASK_KEYWORDS = [
    "cube", "sphere", "ball", "cylinder", "torus", "donut", "terrain",
    "landscape", "light", "material", "texture", "animation", "animate",
    "array", "pattern", "smooth", "subdivide", "curve", "path", "text",
    "rig", "skeleton", "render", "house", "building", "some random task",
]


def test_every_template_plus_finalize_wrapper_is_valid_python(bc, tmp_path):
    import ast
    for task in ALL_TASK_KEYWORDS:
        script = bc.generate_script(task)
        finalized, blend_path, _png_path = bc._finalize_script(script, str(tmp_path / "out"))
        ast.parse(finalized)  # raises SyntaxError on failure
        assert "save_as_mainfile" in finalized, task


def _fake_run_that_saves(cmd, capture_output, text, timeout):
    """Simulates a real Blender run: executes the save_as_mainfile() call it
    finds in the given script file, as real Blender would."""
    script_path = cmd[-1]
    src = open(script_path, encoding="utf-8").read()
    m = re.search(r"save_as_mainfile\(filepath='([^']+)'\)", src)
    if m:
        os.makedirs(os.path.dirname(m.group(1)), exist_ok=True)
        open(m.group(1), "w").close()
    return subprocess.CompletedProcess(cmd, 0, stdout="TOM scene created", stderr="")


def test_successful_run_reports_a_real_verifiable_path(bc, monkeypatch):
    monkeypatch.setattr(bcmod.subprocess, "run", _fake_run_that_saves)
    res = bc.generate_and_execute("build a house")
    assert res["status"] == "success"
    assert os.path.isfile(res["path"])


def test_two_back_to_back_runs_do_not_collide_on_output_dir(bc, monkeypatch):
    """Real bug caught while writing this test: an earlier fix used
    int(time.time()) (1-second resolution) for the output directory name.
    Two calls in the same second shared a directory, so a *second* run that
    produced nothing found the *first* run's leftover file and falsely
    reported success anyway."""
    monkeypatch.setattr(bcmod.subprocess, "run", _fake_run_that_saves)
    res1 = bc.generate_and_execute("build a house")
    res2 = bc.generate_and_execute("build a house")
    assert res1["path"] != res2["path"]
    assert os.path.isfile(res1["path"]) and os.path.isfile(res2["path"])


def test_exit_zero_but_no_file_is_reported_as_error_not_success(bc, monkeypatch):
    """The original bug, isolated: Blender exits cleanly but the scene was
    never saved (e.g. a template bug, or the user's script errored out after
    the point subprocess still considers a clean exit)."""
    def fake_run_silent_noop(cmd, capture_output, text, timeout):
        return subprocess.CompletedProcess(cmd, 0, stdout="ran but did nothing", stderr="")
    monkeypatch.setattr(bcmod.subprocess, "run", fake_run_silent_noop)
    res = bc.generate_and_execute("build a house")
    assert res["status"] == "error"
    assert "no .blend file was found" in res["message"]


def test_nonzero_exit_is_reported_as_error_with_diagnostic(bc, monkeypatch):
    def fake_run_crash(cmd, capture_output, text, timeout):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="Traceback: something broke")
    monkeypatch.setattr(bcmod.subprocess, "run", fake_run_crash)
    res = bc.generate_and_execute("build a house")
    assert res["status"] == "error"
    assert "something broke" in res["message"]


def test_timeout_is_reported_as_error_not_left_hanging(bc, monkeypatch):
    def fake_run_timeout(cmd, capture_output, text, timeout):
        raise subprocess.TimeoutExpired(cmd, timeout)
    monkeypatch.setattr(bcmod.subprocess, "run", fake_run_timeout)
    res = bc.generate_and_execute("build a house")
    assert res["status"] == "error"
    assert "did not finish" in res["message"]


def test_router_no_longer_hardcodes_success_for_blender(bc, monkeypatch):
    """A second, compounding bug one layer up: EngineRouter._run_blender()
    used to unconditionally wrap every result in self._ok(...), which hardcodes
    status="success" -- so even a correctly-detected engine-level failure still
    read as a success by the time it reached the caller. This also confirms
    path/paths now reach the top level so the router's own filesystem
    verification pass (_apply_verification) re-checks the artifact instead of
    silently skipping it (nested one level down inside "raw")."""
    router = EngineRouter()
    router._engines["blender"] = bc

    monkeypatch.setattr(bcmod.subprocess, "run", _fake_run_that_saves)
    ok_res = asyncio.run(router.execute("blender build a house", key="blender"))
    assert ok_res["status"] == "success"
    assert ok_res["verification"]["checked"] is True
    assert ok_res["verification"]["ok"] is True

    def fake_run_noop(cmd, capture_output, text, timeout):
        return subprocess.CompletedProcess(cmd, 0, stdout="did nothing", stderr="")
    monkeypatch.setattr(bcmod.subprocess, "run", fake_run_noop)
    fail_res = asyncio.run(router.execute("blender build a house", key="blender"))
    assert fail_res["status"] == "error"
