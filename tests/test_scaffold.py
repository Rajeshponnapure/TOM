"""Project scaffolding + real build verification. The node/python/static checks run the actual
toolchain (fast + offline), so a green test means the generated project genuinely compiles."""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tom_core.coding import scaffold


@pytest.mark.parametrize("req,kind", [
    ("build me an android app for notes", "android"),
    ("make a react dashboard", "react"),
    ("create an express rest api", "node"),
    ("write a python cli tool", "python"),
    ("build a landing page website", "static"),
    ("a flutter app", "flutter"),
])
def test_detect_kind(req, kind):
    assert scaffold.detect_kind(req) == kind


def test_write_creates_all_files(tmp_path):
    sc = scaffold.build_scaffold("node", "My API")
    written = scaffold.write(sc, str(tmp_path))
    assert (tmp_path / "package.json").exists() and (tmp_path / "server.js").exists()
    assert len(written) == len(sc.files)
    # package.json names a valid slug
    import json
    assert json.loads((tmp_path / "package.json").read_text())["name"] == "my-api"


# ── real, offline build verification ───────────────────────────────────────
@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_node_project_passes_real_syntax_check(tmp_path):
    sc = scaffold.build_scaffold("node", "api")
    scaffold.write(sc, str(tmp_path))
    res = scaffold.verify(sc, str(tmp_path))
    assert res["status"] == "success" and res["verified"] is True


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_broken_js_is_reported_not_claimed_built(tmp_path):
    sc = scaffold.build_scaffold("node", "api")
    sc.files["server.js"] = "const x = ;\n"          # a genuine syntax error
    scaffold.write(sc, str(tmp_path))
    res = scaffold.verify(sc, str(tmp_path))
    assert res["status"] == "error" and "syntax" in res["message"].lower()


def test_python_project_really_compiles(tmp_path):
    sc = scaffold.build_scaffold("python", "tool")
    scaffold.write(sc, str(tmp_path))
    res = scaffold.verify(sc, str(tmp_path))
    assert res["status"] == "success" and res["verified"] is True


def test_broken_python_is_caught(tmp_path):
    sc = scaffold.build_scaffold("python", "tool")
    key = next(k for k in sc.files if k.endswith("main.py"))
    sc.files[key] = "def broken(:\n    pass\n"
    scaffold.write(sc, str(tmp_path))
    res = scaffold.verify(sc, str(tmp_path))
    assert res["status"] == "error"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_static_site_js_and_html_verified(tmp_path):
    sc = scaffold.build_scaffold("static", "Portfolio")
    scaffold.write(sc, str(tmp_path))
    res = scaffold.verify(sc, str(tmp_path))
    assert res["status"] == "success" and "HTML" in res["message"]


def test_android_scaffold_is_valid_but_build_is_deferred(tmp_path):
    sc = scaffold.build_scaffold("android", "Notes")
    scaffold.write(sc, str(tmp_path))
    assert (tmp_path / "app" / "build.gradle").exists()
    manifest = (tmp_path / "app" / "src" / "main" / "AndroidManifest.xml").read_text()
    assert "MainActivity" in manifest
    res = scaffold.verify(sc, str(tmp_path))
    assert res["status"] == "skipped" and "gradlew" in res["build_cmd"]


def test_full_build_python_runs_pytest(tmp_path):
    sc = scaffold.build_scaffold("python", "tool")
    scaffold.write(sc, str(tmp_path))
    captured = {}
    def runner(argv, cwd):
        captured["argv"] = argv
        class P:
            returncode, stdout, stderr = 0, "1 passed", ""
        return P()
    res = scaffold.full_build(sc, str(tmp_path), runner=runner)
    assert res["status"] == "success" and "pytest" in " ".join(captured["argv"])
