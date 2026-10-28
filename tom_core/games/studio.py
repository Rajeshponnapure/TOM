"""Make a real, playable game from a request — and prove it runs before saying it's ready.

"make a neon snake game called Viper" → a pygame project in the workspace (main.py + the shared
tomgame.py runtime + config.json + tom_game.json manifest + README + run.bat), then a headless self-test
that plays it for several hundred frames with a random bot. TOM reports success only when that run ends
cleanly and prints its stats line — the same "evidence, not assertion" rule as the dev builds (AT-007).

The eight genres are hand-written, tested games; the request picks the genre, theme, title and
difficulty. A request no genre fits can be written by a model (`write_code`) and goes through the same
self-test, with up to two repair rounds fed the real traceback; if it still fails, TOM says so.

The manifest (tom_game.json) records the genre, colours and controls, which is what lets TOM's
autopilot play the games it made (tools.game_autopilot).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from tom_core.games import themes

TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "pygame")


@dataclass(frozen=True)
class Genre:
    key: str
    words: str                       # regex of request words that pick it
    blurb: str
    controls: Dict[str, str]
    defaults: Dict[str, Any]


GENRES: Dict[str, Genre] = {g.key: g for g in (
    Genre("snake", r"snake|nibbler|worm", "Eat the food, grow longer, don't hit the walls or yourself.",
          {"Arrows / WASD": "steer"}, {"cols": 24, "rows": 17, "move_every": 7}),
    Genre("breakout", r"breakout|brick|arkanoid|paddle and ball|block breaker",
          "Bounce the ball off your paddle and clear the wall of bricks.",
          {"Left/Right": "move paddle", "Space": "launch"}, {"lives": 3, "paddle_speed": 9, "ball_speed": 6.0}),
    Genre("flappy", r"flappy|flap|bird|helicopter|fly(?:ing)? through|gaps?",
          "Flap through the gaps between the pillars.", {"Space / Up": "flap"},
          {"gravity": 0.42, "flap": -7.4, "gap": 175, "speed": 3.2, "spacing": 270}),
    Genre("shooter", r"shoot(?:er|ing)?|space invaders?|invaders?|asteroids?|galaga|blast|laser",
          "Move and fire to stop the invaders before they reach you.",
          {"Left/Right": "move", "Space (hold)": "fire"}, {"lives": 3, "ship_speed": 7, "enemy_speed": 1.6, "spawn_every": 55}),
    Genre("runner", r"runner|endless run|dino|jump over|parkour|running",
          "Run forever and jump over the obstacles as the speed climbs.", {"Space / Up": "jump"},
          {"speed": 6.0, "jump": -15.5, "gravity": 0.8}),
    Genre("pong", r"pong|table tennis|ping ?pong|air hockey",
          "Beat the computer paddle; miss three and it's over.", {"Up/Down": "move paddle"},
          {"lives": 3, "ball_speed": 6.0, "ai_speed": 5.0}),
    Genre("racer", r"rac(?:e|er|ing)|car|traffic|highway|driving|lane",
          "Switch lanes to dodge the traffic as it speeds up.", {"Left/Right": "change lane"},
          {"lanes": 3, "speed": 5.0}),
    Genre("platformer", r"platform(?:er)?|mario|jump and run|coins?|side[- ]?scroll",
          "Run and jump across platforms collecting coins while avoiding enemies.",
          {"Left/Right": "run", "Space / Up": "jump"}, {"run_speed": 5, "jump": -14.0, "gravity": 0.7, "enemies": 2}),
)}

# Speed-like settings scaled by difficulty (bigger = harder unless listed in _EASIER_WHEN_BIGGER).
_SPEEDS = {"speed", "ball_speed", "enemy_speed", "ai_speed"}
_EASIER_WHEN_BIGGER = {"gap", "spawn_every", "move_every", "lives"}


def detect_genre(request: str) -> Optional[str]:
    r = (request or "").lower()
    best, at = None, len(r) + 1
    for key, genre in GENRES.items():            # the genre named earliest in the sentence wins
        m = re.search(rf"\b(?:{genre.words})", r)
        if m and m.start() < at:
            best, at = key, m.start()
    return best


def detect_difficulty(request: str) -> str:
    r = (request or "").lower()
    if re.search(r"\b(easy|simple|kids?|beginner|relaxing|casual)\b", r):
        return "easy"
    if re.search(r"\b(hard|difficult|challenging|insane|expert|fast)\b", r):
        return "hard"
    return "normal"


def detect_title(request: str, genre: str, theme: str) -> str:
    m = re.search(r"\b(?:called|named|titled)\s+[\"']?([A-Za-z0-9][\w' -]{0,40}?)[\"']?(?=$|[.,!?]|\s+(?:with|in|that|where|using|for)\b)",
                  request or "", re.IGNORECASE)
    if m:
        return m.group(1).strip()
    pretty = {"flappy": "Flapper", "runner": "Runner", "racer": "Racer", "platformer": "Platformer"}
    prefix = "" if theme == "classic" else theme.title() + " "
    return f"{prefix}{pretty.get(genre, genre.title())}"


def slug(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", text or "game").strip("_").lower()
    return s or "game"


def game_settings(genre: str, difficulty: str) -> Dict[str, Any]:
    settings = dict(GENRES[genre].defaults)
    factor = {"easy": 0.8, "normal": 1.0, "hard": 1.3}[difficulty]
    for key, value in list(settings.items()):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        if key in _SPEEDS:
            settings[key] = round(value * factor, 2)
        elif key in _EASIER_WHEN_BIGGER and difficulty != "normal":
            adjusted = value / factor if key != "lives" else value + (1 if difficulty == "easy" else -1)
            settings[key] = max(1, int(round(adjusted))) if isinstance(value, int) else round(adjusted, 2)
    return settings


def plan(request: str) -> Dict[str, Any]:
    """What TOM will build for this request (no files yet)."""
    genre = detect_genre(request)
    theme = themes.pick(request)
    difficulty = detect_difficulty(request)
    title = detect_title(request, genre or "game", theme)
    return {"genre": genre, "theme": theme, "difficulty": difficulty, "title": title}


def _python() -> str:
    return sys.executable or "python"


def self_test(path: str, frames: int = 600, timeout: int = 90, entry: str = "main.py") -> Dict[str, Any]:
    """Run the game headless with a random bot and read its TOM_SELFTEST line. Evidence, not assertion."""
    env = dict(os.environ, TOM_GAME_SELFTEST=str(frames), SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy",
               PYGAME_HIDE_SUPPORT_PROMPT="1")
    try:
        proc = subprocess.run([_python(), entry], cwd=path, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"the self-test did not finish in {timeout}s (the game may never end a frame)"}
    except OSError as exc:
        return {"ok": False, "error": f"could not start Python: {exc}"}
    line = next((ln for ln in proc.stdout.splitlines() if ln.startswith("TOM_SELFTEST ")), "")
    if proc.returncode != 0 or not line:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-12:]
        return {"ok": False, "returncode": proc.returncode, "error": "\n".join(tail) or "no output"}
    try:
        stats = json.loads(line[len("TOM_SELFTEST "):])
    except ValueError:
        return {"ok": False, "error": "the self-test line was not valid JSON"}
    ok = stats.get("frames", 0) >= frames
    return {"ok": ok, "stats": stats, "error": "" if ok else f"stopped after {stats.get('frames')} frames"}


def _write(path: str, name: str, content: str) -> None:
    with open(os.path.join(path, name), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def _readme(title: str, blurb: str, controls: Dict[str, str], genre: str) -> str:
    keys = "\n".join(f"- **{k}** — {v}" for k, v in controls.items())
    return (f"# {title}\n\n{blurb}\n\nA {genre} game made by TOM with pygame.\n\n## Play\n\n"
            f"Double-click `run.bat`, or:\n\n```\npip install -r requirements.txt\npython main.py\n```\n\n"
            f"## Controls\n\n{keys}\n- **R / Enter / Space** — play again after a game over\n- **Esc** — quit\n\n"
            f"Settings (speeds, lives, colours, window size) are in `config.json`.\n")


def _unique_dir(root: str, name: str) -> str:
    path, n = os.path.join(root, name), 2
    while os.path.exists(path):
        path, n = os.path.join(root, f"{name}_{n}"), n + 1
    return path


class GameStudio:
    def __init__(self, output_dir: Optional[str] = None,
                 write_code: Optional[Callable[[str], str]] = None):
        if output_dir is None:
            from tools.project_paths import workspace_path
            output_dir = str(workspace_path("games"))
        self.output_dir = output_dir
        self.write_code = write_code            # model hook for genres we have no hand-written game for

    # ── pygame ───────────────────────────────────────────────────────────
    def create(self, request: str, frames: int = 600) -> Dict[str, Any]:
        spec = plan(request)
        if spec["genre"] is None:
            return self._create_from_model(request, spec, frames)
        genre = GENRES[spec["genre"]]
        os.makedirs(self.output_dir, exist_ok=True)
        path = _unique_dir(self.output_dir, slug(spec["title"]))
        os.makedirs(path)
        shutil.copyfile(os.path.join(TEMPLATES, "tomgame.py"), os.path.join(path, "tomgame.py"))
        shutil.copyfile(os.path.join(TEMPLATES, f"{genre.key}.py"), os.path.join(path, "main.py"))
        cfg = {"title": spec["title"], "width": 800, "height": 600, "fps": 60, "seed": None,
               "theme": spec["theme"], "difficulty": spec["difficulty"], "colors": themes.colors(spec["theme"]),
               "game": game_settings(genre.key, spec["difficulty"])}
        _write(path, "config.json", json.dumps(cfg, indent=2))
        manifest = {"engine": "pygame", "genre": genre.key, "title": spec["title"], "window_title": spec["title"],
                    "width": cfg["width"], "height": cfg["height"], "colors": cfg["colors"], "game": cfg["game"],
                    "controls": genre.controls, "entry": "main.py", "made_by": "TOM"}
        _write(path, "tom_game.json", json.dumps(manifest, indent=2))
        _write(path, "requirements.txt", "pygame>=2.5\n")
        _write(path, "README.md", _readme(spec["title"], genre.blurb, genre.controls, genre.key))
        _write(path, "run.bat", "@echo off\ncd /d \"%~dp0\"\npython main.py || py main.py\n")
        return self._finish(path, spec, genre.blurb, genre.controls, frames)

    def _finish(self, path: str, spec: Dict[str, Any], blurb: str, controls: Dict[str, str],
                frames: int, repairs: int = 0) -> Dict[str, Any]:
        test = self_test(path, frames=frames)
        result = {"engine": "pygame", "path": path, "entry": os.path.join(path, "main.py"), "title": spec["title"],
                  "genre": spec["genre"] or "custom", "theme": spec["theme"], "difficulty": spec["difficulty"],
                  "controls": controls, "verified": test["ok"], "self_test": test, "repairs": repairs}
        if test["ok"]:
            s = test["stats"]
            result.update(status="success", message=(
                f"Made \"{spec['title']}\" — {blurb} It ran {s['frames']} frames in a headless self-test "
                f"({s['rounds']} round(s) played by a random bot) without an error. Saved in {path}."))
        else:
            result.update(status="error", message=(
                f"I wrote \"{spec['title']}\" in {path}, but it failed its self-test, so it isn't ready: "
                f"{test['error'][-600:]}"))
        return result

    def _create_from_model(self, request: str, spec: Dict[str, Any], frames: int) -> Dict[str, Any]:
        options = ", ".join(GENRES)
        if self.write_code is None:
            return {"status": "needs_input", "engine": "pygame", "message": (
                f"I can build these games and prove they run: {options}. Which one is closest to what you "
                "want? (Or tell me the genre — e.g. \"make a space shooter called Star Guard\".)")}
        spec = dict(spec, title=detect_title(request, "game", spec["theme"]))
        os.makedirs(self.output_dir, exist_ok=True)
        path = _unique_dir(self.output_dir, slug(spec["title"]))
        os.makedirs(path)
        shutil.copyfile(os.path.join(TEMPLATES, "tomgame.py"), os.path.join(path, "tomgame.py"))
        cfg = {"title": spec["title"], "width": 800, "height": 600, "fps": 60, "seed": None,
               "theme": spec["theme"], "colors": themes.colors(spec["theme"]), "game": {}}
        _write(path, "config.json", json.dumps(cfg, indent=2))
        _write(path, "requirements.txt", "pygame>=2.5\n")
        _write(path, "run.bat", "@echo off\ncd /d \"%~dp0\"\npython main.py || py main.py\n")
        example = open(os.path.join(TEMPLATES, "runner.py"), encoding="utf-8").read()
        prompt = (f"Write main.py for this pygame game: {request}\n\nIt MUST use the provided runtime exactly like "
                  f"this example (subclass BaseGame with reset/step/draw, read input only via controls.held/"
                  f"controls.tapped with actions up/down/left/right/action, colours only via color(cfg, role) "
                  f"with roles background/player/player_accent/target/hazard/ground/accent, call self.end() on "
                  f"game over, add to self.score, finish with `if __name__ == \"__main__\": run(Game)`).\n\n"
                  f"Example:\n```python\n{example}\n```\nReply with only the Python code.")
        error, repairs = "", 0
        for attempt in range(3):
            code = self.write_code(prompt if not error else
                                   f"{prompt}\n\nYour previous main.py failed its test run with:\n{error}\nFix it.")
            code = _code_block(code)
            _write(path, "main.py", code)
            test = self_test(path, frames=frames)
            if test["ok"]:
                break
            error, repairs = test["error"][-1500:], attempt + 1
        controls = {"Arrows / WASD": "move", "Space": "action"}
        _write(path, "tom_game.json", json.dumps({"engine": "pygame", "genre": "custom", "title": spec["title"],
                                                  "window_title": spec["title"], "colors": cfg["colors"],
                                                  "entry": "main.py", "made_by": "TOM"}, indent=2))
        _write(path, "README.md", _readme(spec["title"], request.strip(), controls, "custom"))
        return self._finish(path, dict(spec, genre=None), request.strip().rstrip(".") + ".", controls, frames,
                            repairs=min(repairs, 2))

    # ── running a made game ──────────────────────────────────────────────
    @staticmethod
    def launch(path: str) -> Dict[str, Any]:
        """Start a made game in its own window (not during tests)."""
        manifest = read_manifest(path)
        if manifest is None:
            return {"status": "error", "message": f"{path} is not a game TOM made (no tom_game.json)."}
        if os.environ.get("TOM_NO_AUTO_OPEN") == "1":
            return {"status": "skipped", "message": f"Would start {manifest['title']} (auto-open is off)."}
        if manifest.get("engine") == "godot":
            from tom_core.games import godot
            return godot.launch(path)
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.Popen([_python(), manifest.get("entry", "main.py")], cwd=path, creationflags=flags)
        return {"status": "success", "pid": proc.pid, "title": manifest["window_title"],
                "message": f"Started {manifest['title']}."}


def _code_block(text: str) -> str:
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text or "", re.DOTALL)
    return (m.group(1) if m else (text or "")).strip() + "\n"


def read_manifest(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(os.path.join(path, "tom_game.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def made_games(root: Optional[str] = None) -> List[Dict[str, Any]]:
    """Every game TOM made in the workspace, newest first, each with its manifest and folder."""
    if root is None:
        from tools.project_paths import workspace_path
        root = str(workspace_path("games"))
    found = []
    try:
        names = os.listdir(root)
    except OSError:
        return []
    for name in names:
        path = os.path.join(root, name)
        manifest = read_manifest(path)
        if manifest:
            found.append(dict(manifest, path=path, mtime=os.path.getmtime(path)))
    return sorted(found, key=lambda m: m["mtime"], reverse=True)


def find_made_game(query: str, root: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """A made game by title or genre ("my snake game", "Viper"), newest first."""
    q = re.sub(r"\b(?:my|the|a|game|that you made|you made|you built|tom'?s|last|latest|new|one)\b", " ",
               (query or "").lower())
    words = [w for w in re.split(r"[^a-z0-9]+", q) if w]
    games = made_games(root)
    if not words:                                     # "the game you made", "my last game" → the newest
        made = re.search(r"you made|you built|my (?:last |latest |new )?game|last game|latest game", (query or "").lower())
        return games[0] if made and games else None
    for game in games:                                # title first: "Viper"
        title = [w for w in re.split(r"[^a-z0-9]+", game["title"].lower()) if w]
        if all(w in title for w in words):
            return game
    for game in games:                                # then genre: "snake"
        if any(w == game.get("genre") or GENRES.get(game.get("genre", "")) and
               re.fullmatch(GENRES[game["genre"]].words, w) for w in words):
            return game
    return None
