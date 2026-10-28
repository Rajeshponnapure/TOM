"""Unity games: write a real Unity project, build a Windows .exe with Unity in batch mode, run the .exe
headless to prove it works.

Same games, colours and 800x600 layout as the pygame/Godot versions (IMGUI drawing), so TOM's autopilot
can play the built game too. The build is slow (several minutes for a new project) and needs the Unity
licence signed in through Unity Hub; if Unity refuses, TOM reports Unity's own error.
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
from typing import Any, Dict, Optional

from tom_core.games import studio, themes

TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "unity")
GENRES = ("snake", "runner")
_PACKAGES = {"dependencies": {"com.unity.modules.imgui": "1.0.0", "com.unity.modules.jsonserialize": "1.0.0"}}


def find_unity() -> str:
    """The newest Unity editor installed through Unity Hub ('' if none)."""
    roots = [os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Unity", "Hub", "Editor"),
             os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Unity")]
    hits = []
    for root in roots:
        hits += glob.glob(os.path.join(root, "*", "Editor", "Unity.exe")) + glob.glob(os.path.join(root, "Editor", "Unity.exe"))
    return sorted(hits)[-1] if hits else ""


def write_project(request: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
    spec = studio.plan(request)
    genre = spec["genre"]
    if genre not in GENRES:
        return {"status": "needs_input", "engine": "unity", "message": (
            f"In Unity I can build and verify: {', '.join(GENRES)}. Pick one of those for Unity, or I can make "
            f"{'a ' + genre if genre else 'that'} game in pygame.")}
    if output_dir is None:
        from tools.project_paths import workspace_path
        output_dir = str(workspace_path("games"))
    os.makedirs(output_dir, exist_ok=True)
    path = studio._unique_dir(output_dir, studio.slug(spec["title"]) + "_unity")
    for sub in ("Assets/Scripts", "Assets/Editor", "Assets/StreamingAssets", "Packages"):
        os.makedirs(os.path.join(path, sub))
    shutil.copyfile(os.path.join(TEMPLATES, "TomGame.cs"), os.path.join(path, "Assets", "Scripts", "TomGame.cs"))
    shutil.copyfile(os.path.join(TEMPLATES, "Genres.cs"), os.path.join(path, "Assets", "Scripts", "Genres.cs"))
    shutil.copyfile(os.path.join(TEMPLATES, "TomBuild.cs"), os.path.join(path, "Assets", "Editor", "TomBuild.cs"))
    settings = studio.game_settings(genre, spec["difficulty"])
    cfg = {"title": spec["title"], "genre": genre, "width": 800, "height": 600, "fps": 60,
           "colors": themes.colors(spec["theme"]), "game": settings}
    exe = "_".join(re.split(r'[<>:"/\\|?*]', spec["title"])).replace(" ", "_")
    files = {
        os.path.join("Assets", "StreamingAssets", "config.json"): json.dumps(cfg, indent=2),
        os.path.join("Packages", "manifest.json"): json.dumps(_PACKAGES, indent=2),
        "tom_game.json": json.dumps({"engine": "unity", "genre": genre, "title": spec["title"],
                                     "window_title": spec["title"], "width": 800, "height": 600,
                                     "colors": cfg["colors"], "game": settings,
                                     "controls": studio.GENRES[genre].controls,
                                     "entry": os.path.join("Build", exe + ".exe"), "made_by": "TOM"}, indent=2),
        "README.md": (f"# {spec['title']}\n\n{studio.GENRES[genre].blurb}\n\nA Unity game made by TOM. Open this "
                      "folder in Unity Hub (Add → this folder), or play Build/" + exe + ".exe.\n"),
    }
    for name, content in files.items():
        with open(os.path.join(path, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
    return {"status": "written", "path": path, "spec": spec, "exe": os.path.join(path, "Build", exe + ".exe")}


def build(path: str, timeout: int = 1800) -> Dict[str, Any]:
    unity = find_unity()
    if not unity:
        return {"ok": False, "error": "Unity isn't installed (Unity Hub → Installs)."}
    log = os.path.join(path, "build.log")
    # no -nographics: in Unity 6 that asks for the paid "headless" entitlement; plain batch mode doesn't
    argv = [unity, "-batchmode", "-quit", "-projectPath", path,
            "-executeMethod", "TomBuild.Build", "-logFile", log]
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Unity did not finish building in {timeout // 60} minutes."}
    try:
        text = open(log, encoding="utf-8", errors="replace").read()
    except OSError:
        text = ""
    errors = [ln.strip() for ln in text.splitlines()
              if re.search(r"error CS\d+|Build Failed|No valid Unity Editor license|licens\w* (?:error|not)|"
                           r"Scripts have compiler errors|Aborting batchmode", ln, re.IGNORECASE)]
    if re.search(r"Access token is unavailable|No valid Unity Editor license|com\.unity\.editor\.headless' was not found",
                 text) and "TOM_BUILD" not in text:
        return {"ok": False, "returncode": proc.returncode, "log": log, "unity": unity, "licence": True,
                "error": ("Unity wouldn't start a build because it has no active licence on this PC. Open Unity Hub, "
                          "sign in, then Preferences → Licenses → Add → \"Get a free personal license\", and ask me "
                          "to build it again — the project is already written.")}
    built = re.search(r"TOM_BUILD Succeeded", text) is not None
    ok = proc.returncode == 0 and built
    return {"ok": ok, "returncode": proc.returncode, "log": log, "unity": unity,
            "error": "" if ok else ("\n".join(dict.fromkeys(errors))[:1200] or text.strip()[-1200:] or "no log")}


def self_test(exe: str, frames: int = 600, timeout: int = 180) -> Dict[str, Any]:
    if not os.path.isfile(exe):
        return {"ok": False, "error": f"no built game at {exe}"}
    argv = [exe, "-batchmode", "-nographics", "-logFile", "-", f"--selftest={frames}"]
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"the built game did not finish its self-test in {timeout}s"}
    line = next((ln[ln.index("TOM_SELFTEST "):] for ln in (proc.stdout or "").splitlines() if "TOM_SELFTEST " in ln), "")
    if not line:
        return {"ok": False, "error": (proc.stdout or proc.stderr or "no output").strip()[-800:]}
    stats = json.loads(line[len("TOM_SELFTEST "):])
    ok = int(stats.get("frames", 0)) >= frames
    return {"ok": ok, "stats": stats, "error": "" if ok else f"stopped after {stats.get('frames')} frames"}


def create(request: str, output_dir: Optional[str] = None, frames: int = 600) -> Dict[str, Any]:
    written = write_project(request, output_dir)
    if written["status"] != "written":
        return written
    path, spec = written["path"], written["spec"]
    result: Dict[str, Any] = {"engine": "unity", "path": path, "title": spec["title"], "genre": spec["genre"],
                              "exe": written["exe"]}
    b = build(path)
    result["build"] = b
    if not b["ok"]:
        result.update(status="error", verified=False, message=(
            f"I wrote the Unity project in {path}, but Unity's build failed, so there's no playable game yet: "
            f"{b['error'][-700:]}"))
        return result
    test = self_test(written["exe"], frames)
    result.update(self_test=test, verified=test["ok"])
    if test["ok"]:
        s = test["stats"]
        result.update(status="success", message=(
            f"Built the Unity game \"{spec['title']}\" ({written['exe']}). The .exe ran headless for {s['frames']} "
            f"frames ({s['rounds']} round(s) by a random bot) without an error. Open the folder in Unity Hub to edit it."))
    else:
        result.update(status="error", message=f"Unity built {written['exe']}, but it failed its run: {test['error'][-600:]}")
    return result


def launch(path: str) -> Dict[str, Any]:
    manifest = studio.read_manifest(path) or {}
    exe = os.path.join(path, manifest.get("entry", ""))
    if not os.path.isfile(exe):
        return {"status": "error", "message": "That Unity game hasn't been built yet."}
    proc = subprocess.Popen([exe, "-screen-fullscreen", "0", "-screen-width", "800", "-screen-height", "600"], cwd=os.path.dirname(exe))
    return {"status": "success", "pid": proc.pid, "title": manifest.get("window_title", ""),
            "message": f"Started {manifest.get('title', 'the game')}."}
