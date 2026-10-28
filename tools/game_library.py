"""The games installed on this PC (Steam and Epic), so "play Green Hell" starts Green Hell.

Steam: every library in steamapps/libraryfolders.vdf, one appmanifest_<id>.acf per installed app →
steam://rungameid/<id>. Epic: Manifests/*.item with the "games" category → the launch link Epic writes
into its own desktop shortcuts. Store games (Solitaire …) are found by tools.os_tools instead.

TOM can start a game and bring it to the front. It can also attempt to play one by looking at the screen
(tom_core/games/play_loop), but it never claims expert play of a real-time game — it reports what it
actually saw and did.
"""
from __future__ import annotations

import difflib
import glob
import json
import os
import re
import time
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import quote

_NOT_GAMES = re.compile(r"redistributable|steamworks common|\bsdk\b|dedicated server|proton|steam linux runtime|"
                        r"soundtrack|\bdemo\b server|benchmark tool", re.IGNORECASE)
_CACHE: dict = {"at": 0.0, "games": []}
TTL = 300.0


@dataclass(frozen=True)
class Game:
    name: str
    launcher: str          # "Steam" | "Epic Games" | "BlueStacks" | "Shortcut"
    launch: str            # URI or shortcut handed to the shell
    window: str = ""       # title of the window it plays in, when that isn't the game's name (emulators)
    package: str = ""      # Android package for an emulator game (BlueStacks "--package …"), used over ADB


def _steam_root() -> str:
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
                path = winreg.QueryValueEx(key, "SteamPath")[0]
                if path and os.path.isdir(path):
                    return os.path.normpath(path)
        except OSError:
            pass
    default = os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Steam")
    return default if os.path.isdir(default) else ""


def _vdf_values(text: str, key: str) -> List[str]:
    return re.findall(rf'"{key}"\s+"([^"]*)"', text)


def steam_games(root: Optional[str] = None) -> List[Game]:
    root = root if root is not None else _steam_root()
    if not root:
        return []
    def norm(p: str) -> str:                           # the main library appears as both C:/… and c:\…
        return os.path.normcase(os.path.normpath(p))

    libraries = {norm(os.path.join(root, "steamapps"))}
    try:
        with open(os.path.join(root, "steamapps", "libraryfolders.vdf"), encoding="utf-8", errors="replace") as fh:
            for path in _vdf_values(fh.read(), "path"):
                libraries.add(norm(os.path.join(path.replace("\\\\", "\\"), "steamapps")))
    except OSError:
        pass
    games: List[Game] = []
    for lib in libraries:
        for manifest in glob.glob(os.path.join(lib, "appmanifest_*.acf")):
            try:
                with open(manifest, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            appid, name = (_vdf_values(text, "appid") or [""])[0], (_vdf_values(text, "name") or [""])[0]
            if appid and name and not _NOT_GAMES.search(name):
                games.append(Game(name, "Steam", f"steam://rungameid/{appid}"))
    return list({g.launch: g for g in games}.values())


def epic_games(manifests: Optional[str] = None) -> List[Game]:
    folder = manifests or os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), "Epic",
                                       "EpicGamesLauncher", "Data", "Manifests")
    games = []
    for item in glob.glob(os.path.join(folder, "*.item")):
        try:
            with open(item, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        if "games" not in [str(c).lower() for c in data.get("AppCategories", [])]:
            continue                                   # Unreal Engine, plugins, tools
        name, app = data.get("DisplayName", ""), data.get("AppName", "")
        ns, cid = data.get("CatalogNamespace", ""), data.get("CatalogItemId", "")
        if name and app:
            ident = quote(f"{ns}:{cid}:{app}", safe="") if ns and cid else quote(app, safe="")
            games.append(Game(name, "Epic Games", f"com.epicgames.launcher://apps/{ident}?action=launch&silent=true"))
    return games


def _shortcut_target(lnk: str) -> tuple:
    """(target, arguments) of a Windows .lnk, read with the shell's own COM object."""
    if os.name != "nt":
        return "", ""
    try:
        import pythoncom  # noqa: F401  (pywin32)
        from win32com.client import Dispatch
        sc = Dispatch("WScript.Shell").CreateShortcut(lnk)
        return str(sc.TargetPath or ""), str(sc.Arguments or "")
    except Exception:
        return "", ""


def shortcut_games(folders: Optional[List[str]] = None, read=None) -> List[Game]:
    """Games started from a desktop / Start-menu shortcut that Steam and Epic don't list — e.g. an
    Android game in BlueStacks ("Minecraft.lnk" → HD-Player.exe --cmd launchApp --package …) or a
    steam:// / Epic link. Only shortcuts that point at a game launcher count, not every app."""
    if folders is None:
        home = os.path.expanduser("~")
        folders = [os.path.join(home, "Desktop"), os.path.join(home, "OneDrive", "Desktop"),
                   os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), "Desktop"),
                   os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs")]
    read = read or _shortcut_target
    games: List[Game] = []
    for folder in folders:
        for lnk in glob.glob(os.path.join(folder, "**", "*.lnk"), recursive=True):
            name = os.path.splitext(os.path.basename(lnk))[0]
            target, args = read(lnk)
            low = f"{target} {args}".lower()
            if "hd-player.exe" in low and "launchapp" in low:
                pkg = re.search(r"--package\s+\"?([A-Za-z0-9_.]+)", args or "")
                games.append(Game(name, "BlueStacks", lnk, window="BlueStacks App Player",
                                  package=pkg.group(1) if pkg else ""))
            elif re.search(r"steam://rungameid|com\.epicgames\.launcher://apps", low):
                games.append(Game(name, "Shortcut", lnk))
    return list({g.name.lower(): g for g in games}.values())


def installed_games(refresh: bool = False) -> List[Game]:
    if refresh or time.monotonic() - _CACHE["at"] > TTL:
        found = steam_games() + epic_games()
        known = {_norm(g.name) for g in found}
        _CACHE["games"] = found + [g for g in shortcut_games() if _norm(g.name) not in known]
        _CACHE["at"] = time.monotonic()
    return list(_CACHE["games"])


def _norm(text: str) -> str:
    text = re.sub(r"[™®©]", "", text or "").lower()
    text = re.sub(r"\b(marvel'?s|tom clancy'?s|sid meier'?s|the)\b", " ", text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def find_game(query: str, games: Optional[List[Game]] = None) -> Optional[Game]:
    q = _norm(query)
    if len(q) < 2:
        return None
    games = installed_games() if games is None else games
    by_norm = {_norm(g.name): g for g in games}
    if q in by_norm:
        return by_norm[q]
    words = q.split()
    # every spoken word is in the name AND they cover most of it ("hell" alone is not "Green Hell")
    contains = [g for n, g in by_norm.items()
                if all(w in n.split() for w in words) and len(words) / len(n.split()) > 0.5]
    if len(contains) == 1:
        return contains[0]
    close = difflib.get_close_matches(q, list(by_norm), n=1, cutoff=0.8)
    return by_norm[close[0]] if close else None


async def launch(game: Game) -> dict:
    """Start the game through its launcher (gated like opening any app — the emergency stop applies)."""
    from tom_core.policy.engine import ActionClass
    from tom_core.tools.guard import aenforce
    gate = await aenforce("app.open", ActionClass.REVERSIBLE, payload={"app": game.name})
    if not gate.allowed:
        return {**gate.refusal(), "game": game.name}
    if os.environ.get("TOM_NO_AUTO_OPEN") == "1":      # tests / headless checks never start a real game
        return {"status": "skipped", "game": game.name, "message": f"Would start {game.name} (auto-open is off)."}
    try:
        os.startfile(game.launch)                      # type: ignore[attr-defined]  (Windows)
    except (OSError, AttributeError) as exc:
        return {"status": "error", "game": game.name, "message": f"Could not start {game.name}: {exc}"}
    return {"status": "success", "game": game.name, "launcher": game.launcher,
            "message": f"Starting {game.name} through {game.launcher}."}
