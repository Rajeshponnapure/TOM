"""Games on this PC and everyday Windows control (owner request 2026-10-27: "control my system",
"play the games inside my system"). Fakes only — nothing is locked, restarted or launched for real.
"""
import asyncio
import json

import pytest

from tools import game_library as gl
from tools import system_control as sc
from tools.command_router import CommandRouter

GAMES = [gl.Game("Marvel's Spider-Man 2", "Steam", "steam://rungameid/2651280"),
         gl.Game("Green Hell", "Steam", "steam://rungameid/815370"),
         gl.Game("over the hill", "Steam", "steam://rungameid/2929250")]


@pytest.fixture
def games(monkeypatch):
    monkeypatch.setattr(gl, "_CACHE", {"at": 1e18, "games": list(GAMES)})
    return GAMES


# ── game library ───────────────────────────────────────────────────────

def test_steam_manifests_in_every_library_are_read_once(tmp_path):
    main, extra = tmp_path / "Steam", tmp_path / "Lib2"
    (main / "steamapps").mkdir(parents=True)
    (extra / "steamapps").mkdir(parents=True)
    vdf = '"libraryfolders"\n{\n "0" { "path" "%s" }\n "1" { "path" "%s" }\n}' % (
        str(main).replace("\\", "\\\\"), str(extra).replace("\\", "\\\\"))
    (main / "steamapps" / "libraryfolders.vdf").write_text(vdf, encoding="utf-8")
    (main / "steamapps" / "appmanifest_815370.acf").write_text('"AppState"\n{\n "appid" "815370"\n "name" "Green Hell"\n}')
    (main / "steamapps" / "appmanifest_228980.acf").write_text(
        '"AppState"\n{\n "appid" "228980"\n "name" "Steamworks Common Redistributables"\n}')
    (extra / "steamapps" / "appmanifest_2651280.acf").write_text(
        '"AppState"\n{\n "appid" "2651280"\n "name" "Marvel\'s Spider-Man 2"\n}')
    found = sorted(gl.steam_games(str(main)), key=lambda g: g.name)
    assert [(g.name, g.launch) for g in found] == [("Green Hell", "steam://rungameid/815370"),
                                                  ("Marvel's Spider-Man 2", "steam://rungameid/2651280")]


def test_epic_lists_games_not_engines(tmp_path):
    (tmp_path / "a.item").write_text(json.dumps({"DisplayName": "Fortnite", "AppName": "Fortnite",
                                                 "CatalogNamespace": "fn", "CatalogItemId": "4fe",
                                                 "AppCategories": ["public", "games", "applications"]}))
    (tmp_path / "b.item").write_text(json.dumps({"DisplayName": "Unreal Engine", "AppName": "UE_5.4",
                                                 "AppCategories": ["public", "engines"]}))
    found = gl.epic_games(str(tmp_path))
    assert [g.name for g in found] == ["Fortnite"]
    assert found[0].launch == "com.epicgames.launcher://apps/fn%3A4fe%3AFortnite?action=launch&silent=true"


@pytest.mark.parametrize("query,name", [
    ("green hell", "Green Hell"), ("spider-man 2", "Marvel's Spider-Man 2"), ("spiderman 2", "Marvel's Spider-Man 2"),
    ("Spider Man 2", "Marvel's Spider-Man 2"), ("over the hill", "over the hill"), ("green hel", "Green Hell"),
])
def test_games_are_found_by_how_people_say_them(query, name):
    assert gl.find_game(query, GAMES).name == name


@pytest.mark.parametrize("query", ["some music", "lofi on youtube", "chess", "hell"])
def test_unrelated_names_are_not_games(query):
    assert gl.find_game(query, GAMES) is None


def test_launch_is_gated_by_the_emergency_stop(monkeypatch):
    from tom_core.policy import get_policy
    monkeypatch.delenv("TOM_NO_AUTO_OPEN", raising=False)
    started = []
    monkeypatch.setattr(gl.os, "startfile", started.append, raising=False)
    get_policy().halt("test")
    try:
        res = asyncio.run(gl.launch(GAMES[1]))
    finally:
        get_policy().resume()
    assert res["status"] == "blocked" and started == []
    res = asyncio.run(gl.launch(GAMES[1]))
    assert res["status"] == "success" and started == ["steam://rungameid/815370"]


@pytest.mark.parametrize("text,game", [
    ("play green hell", "Green Hell"), ("play spider-man 2", "Marvel's Spider-Man 2"),
    ("start the game over the hill", "over the hill"),
    ("launch green hell on steam", "Green Hell")])
def test_play_requests_route_to_the_game(text, game, games):
    d = CommandRouter().route(text)
    assert d.handler == "execute_game_launch" and d.metadata["game"] == game


def test_play_for_me_routes_to_the_experimental_autopilot(games):
    # Owner (2026-10-28) redefined "play X for me" as the experimental autopilot; plain "play/launch
    # X" still just starts the game.
    d = CommandRouter().route("can you play green hell for me")
    assert d.handler == "execute_game_autopilot" and d.metadata["game"] == "Green Hell"


@pytest.mark.parametrize("text", ["play some music", "play lofi on youtube", "open notepad"])
def test_other_play_and_open_requests_do_not(text, games):
    assert CommandRouter().route(text).handler != "execute_game_launch"


def test_the_agent_starts_the_game_and_is_honest_about_playing(games, monkeypatch):
    from agent import TomAgent
    monkeypatch.delenv("TOM_NO_AUTO_OPEN", raising=False)
    started = []
    monkeypatch.setattr(gl.os, "startfile", started.append, raising=False)
    a = TomAgent.__new__(TomAgent)
    a.command_router = CommandRouter()
    res = asyncio.run(a.execute_game_launch("can you play green hell for me"))
    assert res["status"] == "success" and started == ["steam://rungameid/815370"]
    # Started, then says what it can do next — it never claims to have played it.
    assert 'say "play it for me"' in res["message"].lower() and "i played" not in res["message"].lower()
    assert "can't play" not in asyncio.run(a.execute_game_launch("play green hell"))["message"]


# ── system control ─────────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("lock my pc", ("lock", "")), ("lock the screen", ("lock", "")), ("put my laptop to sleep", ("sleep", "")),
    ("restart my pc", ("restart", "")), ("reboot the computer", ("restart", "")),
    ("shut down the computer", ("shutdown", "")), ("turn off my laptop", ("shutdown", "")),
    ("cancel the shutdown", ("cancel_shutdown", "")), ("stop the restart", ("cancel_shutdown", "")),
    ("set brightness to 60", ("brightness", "60")), ("brightness 40%", ("brightness", "40")),
    ("increase brightness by 20", ("brightness", "+20")), ("increase brightness", ("brightness", "+10")),
    ("dim the screen", ("brightness", "-10")), ("what is the brightness", ("brightness", "?")),
    ("show desktop", ("show_desktop", "")), ("minimize all windows", ("show_desktop", "")),
    ("switch to chrome", ("switch", "chrome")), ("close notepad", ("close", "notepad")),
    ("open bluetooth settings", ("settings", "bluetooth")), ("open wifi settings", ("settings", "wifi")),
    ("close the deal with ravi", None), ("close my account", None), ("open notepad", None),
    ("what is a lock", None), ("restart the download", None),
])
def test_parse(text, expected):
    assert sc.parse(text) == expected


class OS:
    def __init__(self, brightness=50, windows=None, front=""):
        self.calls, self.brightness, self.front = [], brightness, front
        self.wins = windows if windows is not None else [(11, "Untitled - Notepad"), (12, "Inbox - Gmail - Google Chrome")]

    def __call__(self, op, *args):
        self.calls.append((op, *args))
        if op == "get_brightness":
            return self.brightness
        if op == "set_brightness":
            self.brightness = args[0]
            return True
        if op == "close_window":
            self.wins = [w for w in self.wins if w[0] != args[0]]
            return True
        if op == "foreground":
            return self.front
        return True


def _tool(os_fake, hardware=None):
    return sc.SystemControl(windows=lambda: os_fake.wins, run=os_fake, hardware=hardware)


def test_lock_runs_without_asking(monkeypatch):
    asked = []
    from tom_core.tools import guard
    monkeypatch.setattr(guard, "_approval_manager",
                        type("A", (), {"request_approval": lambda s, r, p=None: asked.append(r) or True})())
    os_fake = OS()
    assert asyncio.run(_tool(os_fake).run("lock"))["status"] == "success"
    assert ("lock",) in os_fake.calls and asked == []


@pytest.mark.parametrize("action", ["sleep", "restart", "shutdown"])
def test_power_actions_need_approval_and_a_no_does_nothing(action, monkeypatch):
    from tom_core.tools import guard
    asked = []
    monkeypatch.setattr(guard, "_approval_manager",
                        type("A", (), {"request_approval": lambda s, r, p=None: asked.append(r) or False})())
    os_fake = OS()
    res = asyncio.run(_tool(os_fake).run(action))
    assert res["status"] != "success" and os_fake.calls == [] and len(asked) == 1


def test_restart_gives_a_cancel_window_and_cancel_works():
    os_fake = OS()
    res = asyncio.run(_tool(os_fake).run("restart"))
    assert res["status"] == "success" and "60 seconds" in res["message"] and ("shutdown", "restart") in os_fake.calls
    assert asyncio.run(_tool(os_fake).run("cancel_shutdown"))["status"] == "success"


def test_brightness_is_set_and_read_back():
    os_fake = OS(brightness=56)
    res = asyncio.run(_tool(os_fake).run("brightness", "+10"))
    assert res["status"] == "success" and res["level"] == 66 and res["verified"] is True
    assert asyncio.run(_tool(os_fake).run("brightness", "100"))["level"] == 100
    assert asyncio.run(_tool(os_fake).run("brightness", "+10"))["level"] == 100          # clamped
    assert asyncio.run(_tool(OS(brightness=None)).run("brightness", "50"))["status"] == "error"


def test_close_reports_whether_the_window_really_closed():
    os_fake = OS()
    res = asyncio.run(_tool(os_fake).run("close", "notepad"))
    assert res["status"] == "success" and ("close_window", 11) in os_fake.calls
    res = asyncio.run(_tool(OS()).run("close", "photoshop"))
    assert res["status"] == "error" and "nothing was closed" in res["message"]


def test_switch_checks_the_window_in_front():
    ok = asyncio.run(_tool(OS(front="Inbox - Gmail - Google Chrome")).run("switch", "chrome"))
    assert ok["status"] == "success" and ok["verified"]
    blocked = asyncio.run(_tool(OS(front="Untitled - Notepad")).run("switch", "chrome"))
    assert blocked["status"] == "unverified"


def test_show_desktop_uses_the_gated_keyboard():
    keys = []
    hw = type("H", (), {"hotkey": lambda s, *k: keys.append(k) or {"status": "success"}})()
    assert asyncio.run(_tool(OS(), hw).run("show_desktop"))["status"] == "success" and keys == [("win", "d")]


def test_settings_pages_open_by_uri():
    os_fake = OS()
    asyncio.run(_tool(os_fake).run("settings", "bluetooth"))
    assert ("open_uri", "ms-settings:bluetooth") in os_fake.calls


def test_emergency_stop_blocks_system_control():
    from tom_core.policy import get_policy
    os_fake = OS()
    get_policy().halt("test")
    try:
        res = asyncio.run(_tool(os_fake).run("lock"))
    finally:
        get_policy().resume()
    assert res["status"] == "blocked" and os_fake.calls == []


def test_test_runs_never_start_a_real_game(monkeypatch):
    started = []
    monkeypatch.setattr(gl.os, "startfile", started.append, raising=False)
    monkeypatch.setenv("TOM_NO_AUTO_OPEN", "1")
    assert asyncio.run(gl.launch(GAMES[1]))["status"] == "skipped" and started == []
