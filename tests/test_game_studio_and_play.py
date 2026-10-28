"""Game development and game playing, checked by running things, not by reading them:

* every genre TOM makes is written, then run headless with a random bot (the self-test TOM itself uses);
* TOM's by-sight strategies play those games measurably better than random key-mashing;
* the input layer sends what games read (the SendInput struct-size bug that silently dropped every key);
* in-game tasks (Minecraft commands), their fallbacks, and the routing of all of it.
No real window, keyboard or game is touched here.
"""
import ctypes
import itertools
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tom_core.games import godot, strategies, studio, themes, unity
from tools import game_autopilot as ga
from tools import game_library, game_tasks


# ── making games ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("genre", list(studio.GENRES))
def test_every_genre_is_made_and_passes_its_self_test(tmp_path, genre):
    res = studio.GameStudio(output_dir=str(tmp_path)).create(f"make a {genre} game", frames=300)
    assert res["status"] == "success", res["message"]
    assert res["verified"] and res["self_test"]["stats"]["frames"] >= 300
    for name in ("main.py", "tomgame.py", "config.json", "tom_game.json", "README.md", "run.bat"):
        assert os.path.isfile(os.path.join(res["path"], name)), name
    assert studio.read_manifest(res["path"])["genre"] == genre


def test_a_broken_game_is_reported_as_broken(tmp_path):
    res = studio.GameStudio(output_dir=str(tmp_path)).create("make a snake game", frames=100)
    with open(os.path.join(res["path"], "main.py"), "a", encoding="utf-8") as fh:
        fh.write("\nraise RuntimeError('boom')\n")
    test = studio.self_test(res["path"], frames=100)
    assert test["ok"] is False and "boom" in test["error"]


def test_request_details_pick_genre_theme_title_and_difficulty():
    spec = studio.plan("make a hard neon space shooter called Star Guard")
    assert spec == {"genre": "shooter", "theme": "neon", "difficulty": "hard", "title": "Star Guard"}
    assert studio.plan("build me a game where a ship shoots asteroids")["genre"] == "shooter"
    assert studio.plan("an easy flappy bird game")["difficulty"] == "easy"
    assert studio.plan("make a game")["genre"] is None
    hard, easy = studio.game_settings("runner", "hard"), studio.game_settings("runner", "easy")
    assert hard["speed"] > easy["speed"]


def test_unknown_genre_without_a_model_asks_instead_of_inventing(tmp_path):
    res = studio.GameStudio(output_dir=str(tmp_path)).create("make a chess game", frames=50)
    assert res["status"] == "needs_input" and "snake" in res["message"]


def test_model_written_game_is_repaired_with_the_real_traceback(tmp_path):
    good = open(os.path.join(studio.TEMPLATES, "runner.py"), encoding="utf-8").read()
    prompts = []

    def write_code(prompt):
        prompts.append(prompt)
        return "```python\nraise ValueError('first try')\n```" if len(prompts) == 1 else f"```python\n{good}```"

    res = studio.GameStudio(output_dir=str(tmp_path), write_code=write_code).create("make a chess game", frames=100)
    assert res["status"] == "success" and res["repairs"] == 1
    assert "first try" in prompts[1]


def test_theme_colours_are_distinct_so_players_and_tom_can_tell_things_apart():
    for name, palette in themes.THEMES.items():
        for (ra, a), (rb, b) in itertools.combinations(palette.items(), 2):
            gap = sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5
            assert gap >= 60, (name, ra, rb, gap)


def test_finding_a_made_game_by_title_genre_or_the_newest(tmp_path):
    st = studio.GameStudio(output_dir=str(tmp_path))
    st.create("make a snake game called Viper", frames=30)
    st.create("make a runner game", frames=30)
    assert studio.find_made_game("viper", str(tmp_path))["title"] == "Viper"
    assert studio.find_made_game("my snake game", str(tmp_path))["title"] == "Viper"
    assert studio.find_made_game("the game you made", str(tmp_path)) is not None
    assert studio.find_made_game("chess", str(tmp_path)) is None


@pytest.mark.skipif(not godot.find_godot(), reason="Godot isn't installed")
def test_godot_game_runs_in_the_real_engine(tmp_path):
    res = godot.create("make a snake game in godot", output_dir=str(tmp_path), frames=200)
    assert res["status"] == "success", res["message"]
    assert os.path.isfile(os.path.join(res["path"], "project.godot"))


def test_godot_and_unity_say_which_genres_they_support():
    assert godot.create("make a pong game in godot")["status"] == "needs_input"
    assert unity.write_project("make a racing game in unity")["status"] == "needs_input"


def test_unity_project_is_complete_and_licence_problems_are_explained(tmp_path, monkeypatch):
    w = unity.write_project("make a runner game in unity", output_dir=str(tmp_path))
    for rel in ("Assets/Scripts/TomGame.cs", "Assets/Scripts/Genres.cs", "Assets/Editor/TomBuild.cs",
                "Assets/StreamingAssets/config.json", "Packages/manifest.json", "tom_game.json"):
        assert os.path.isfile(os.path.join(w["path"], rel)), rel
    monkeypatch.setattr(unity, "find_unity", lambda: "unity.exe")

    def fake_run(argv, **kw):
        with open(argv[argv.index("-logFile") + 1], "w", encoding="utf-8") as fh:
            fh.write("[Licensing::Module] Error: Access token is unavailable; failed to update\n")
        return type("P", (), {"returncode": 198, "stdout": "", "stderr": ""})()
    monkeypatch.setattr(unity.subprocess, "run", fake_run)
    b = unity.build(w["path"])
    assert b["ok"] is False and b.get("licence") and "Unity Hub" in b["error"]


# ── playing them by sight ─────────────────────────────────────────────────
@pytest.fixture(scope="module")
def made(tmp_path_factory):
    root = tmp_path_factory.mktemp("made")
    st = studio.GameStudio(output_dir=str(root))
    return {g: st.create(f"make a {g} game", frames=30)["path"] for g in studio.GENRES}


@pytest.mark.parametrize("genre", list(studio.GENRES))
def test_tom_plays_its_games_better_than_random(made, genre):
    bot = strategies.evaluate(made[genre], frames=1500, player="strategy", seed=3)
    rnd = strategies.evaluate(made[genre], frames=1500, player="random", seed=3)
    if genre == "pong":                   # beating the computer takes long rallies; it must not lose a point
        assert bot["rounds"] == 1 and bot["best"] >= rnd["best"]
    else:
        assert bot["best"] > rnd["best"], (bot, rnd)


def test_strategy_works_on_a_scaled_window_frame(made):
    import numpy as np
    import cv2
    s = strategies.for_manifest(dict(studio.read_manifest(made["breakout"])))
    frame = np.zeros((600, 800, 3), np.uint8)
    frame[:] = s.bgr["background"].astype(np.uint8)
    frame[554:568, 300:410] = s.bgr["player"].astype(np.uint8)       # paddle, centre x 355
    frame[300:312, 600:612] = s.bgr["target"].astype(np.uint8)       # ball to the right
    big = cv2.resize(frame, (1200, 900), interpolation=cv2.INTER_NEAREST)   # 150% DPI scaling
    assert s.act(big, now=0.0).hold == {"right"}


# ── the input layer ───────────────────────────────────────────────────────
@pytest.mark.skipif(os.name != "nt", reason="Windows input")
def test_sendinput_struct_has_the_size_windows_requires():
    t = ga._input_types()
    assert ctypes.sizeof(t["INPUT"]) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)


def test_arrow_keys_use_hardware_scan_codes_not_directinput_numbers():
    assert ga.SCAN["UP"] == 0x48 and ga.SCAN["LEFT"] == 0x4B and ga.EXTENDED >= {"UP", "DOWN", "LEFT", "RIGHT"}


def test_keystate_presses_releases_and_taps_exactly():
    log = []
    ks = ga.KeyState(send=lambda k, down: log.append((k, down)) or True)
    ks.apply({"left"})
    ks.apply({"left", "action"})
    ks.apply({"action"}, tap={"restart"})
    ks.release_all()
    assert log == [("LEFT", True), ("SPACE", True), ("LEFT", False), ("ENTER", True), ("ENTER", False),
                   ("SPACE", False)]
    assert ks.down == set()


def test_play_window_never_types_while_another_window_is_in_front(monkeypatch):
    sent = []
    monkeypatch.setattr(ga, "_window_alive", lambda h: True)
    monkeypatch.setattr(ga, "is_foreground", lambda h: False)
    monkeypatch.setattr(ga, "focus_window", lambda h: False)
    monkeypatch.setattr(ga, "set_dpi_aware", lambda: None)
    player = type("P", (), {"act": lambda self, f: strategies.Move(hold={"left"})})()
    run = ga.play_window(1, player, 1.0, ga.KeyState(send=lambda k, d: sent.append((k, d)) or True))
    assert sent == [] and run["frames"] == 0 and run["paused_s"] > 0.5


# ── tasks inside games ────────────────────────────────────────────────────
def test_task_requests_are_parsed():
    assert game_tasks.parse("build a house in minecraft") == ("minecraft", "build a house")
    assert game_tasks.parse("in Green Hell, find water") == ("Green Hell", "find water")
    assert game_tasks.parse("find a village in my minecraft game") == ("minecraft", "find a village")
    assert game_tasks.parse("lock my pc") is None


def test_minecraft_plans_are_real_bedrock_commands():
    house = game_tasks.minecraft_plan("build a big brick house")
    assert house and all(c.startswith(("/fill", "/setblock")) for c in house.commands)
    assert any("brick_block hollow" in c for c in house.commands)
    v = game_tasks.minecraft_plan("take me to the nearest village")
    assert v.commands == ["/locate structure village"] and v.expect == "locate:go"
    assert game_tasks.minecraft_plan("give me 10 diamonds").commands == ["/give @s diamond 10"]
    assert game_tasks.minecraft_plan("make it day").commands == ["/time set day"]
    assert game_tasks.minecraft_plan("write me a poem") is None


def test_reading_minecraft_replies():
    r = game_tasks.read_reply("The nearest village is at [-232, (y?), 568] (412 blocks away)")
    assert r["kind"] == "located" and (r["x"], r["z"]) == (-232, 568)
    assert game_tasks.read_reply("You do not have permission to use this slash command")["kind"] == "denied"
    assert game_tasks.read_reply("23 blocks filled")["kind"] == "done"


class FakeDriver:
    def __init__(self, replies):
        self.replies, self.ran = list(replies), []

    def run(self, cmd):
        self.ran.append(cmd)
        return dict(self.replies.pop(0), command=cmd)


def test_locate_then_teleport_when_asked_to_go_there():
    plan = game_tasks.minecraft_plan("go to a village")
    d = FakeDriver([{"ok": True, "kind": "located", "what": "village", "x": 10, "y": None, "z": -40},
                    {"ok": True, "kind": "done"}])
    res = game_tasks.run_minecraft(plan, d)
    assert res["status"] == "success" and d.ran[-1] == "/tp @s 10 ~ -40" and "x 10, z -40" in res["message"]


def test_cheats_off_is_explained_and_offers_the_other_way():
    plan = game_tasks.minecraft_plan("build a house")
    d = FakeDriver([{"ok": False, "kind": "denied", "said": "do not have permission"}])
    res = game_tasks.run_minecraft(plan, d)
    assert res["status"] == "error" and res["fallback"] == "play" and "Activate Cheats" in res["message"]
    assert len(d.ran) == 1                                         # stopped at the first refusal


def test_chat_opener_falls_back_from_t_to_slash():
    typed, pressed = [], []
    screens = iter(["", "Minecraft world", "/fill ~2 ...", "23 blocks filled"])
    drv = game_tasks.MinecraftDriver(1, ocr=lambda: next(screens, ""), typer=typed.append,
                                     press=lambda k: pressed.append(k) or True, foreground=lambda: True)
    r = drv.run("/fill ~2 ~ ~2 ~4 ~2 ~4 stone", settle=0)
    assert typed[0] == "t" and typed[2] == "/" and typed[3] == "fill ~2 ~ ~2 ~4 ~2 ~4 stone"
    assert pressed == ["ESC", "ENTER"] and r["kind"] == "done"


def test_driver_refuses_to_type_when_the_game_is_not_in_front():
    drv = game_tasks.MinecraftDriver(1, ocr=lambda: "", typer=lambda t: pytest.fail("typed"),
                                     press=lambda k: pytest.fail("pressed"), foreground=lambda: False)
    assert drv.run("/time set day")["kind"] == "not_focused"


# ── finding games on this PC ──────────────────────────────────────────────
def test_bluestacks_and_store_link_shortcuts_count_as_games(tmp_path):
    for name in ("Minecraft", "Ludo King", "Notepad", "Hollow Knight"):
        (tmp_path / f"{name}.lnk").write_text("x")
    targets = {"Minecraft": (r"C:\Program Files\BlueStacks_nxt\HD-Player.exe",
                             '--instance Pie64 --cmd launchApp --package "com.mojang.minecraftpe"'),
               "Ludo King": (r"C:\Program Files\BlueStacks_nxt\HD-Player.exe", "--cmd launchApp --package x"),
               "Notepad": (r"C:\Windows\notepad.exe", ""),
               "Hollow Knight": ("steam://rungameid/367520", "")}
    games = game_library.shortcut_games([str(tmp_path)], read=lambda p: targets[os.path.splitext(os.path.basename(p))[0]])
    by = {g.name: g for g in games}
    assert set(by) == {"Minecraft", "Ludo King", "Hollow Knight"}
    assert by["Minecraft"].launcher == "BlueStacks" and by["Minecraft"].window == "BlueStacks App Player"


# ── routing ───────────────────────────────────────────────────────────────
def test_routing_for_making_playing_and_tasks(tmp_path, monkeypatch):
    from tools.command_router import CommandRouter
    from tools.engine_router import EngineRouter
    studio.GameStudio(output_dir=str(tmp_path)).create("make a snake game called Viper", frames=30)
    monkeypatch.setattr(studio, "made_games", lambda root=None, _r=str(tmp_path): studio.__dict__["_made"](_r)
                        if False else _list(str(tmp_path)))
    monkeypatch.setattr(game_library, "installed_games",
                        lambda refresh=False: [game_library.Game("Minecraft", "BlueStacks", "x.lnk", "BlueStacks App Player")])
    r, e = CommandRouter(), EngineRouter()
    assert r.route("build a house in minecraft").handler == "execute_game_task"
    assert r.route("build a website in react").handler != "execute_game_task"
    assert r.route("play viper for me").metadata.get("made")
    assert r.route("play my snake game").handler == "execute_game_launch"
    assert r.route("open the game you made").handler == "execute_game_launch"
    assert r.route("stop playing").handler == "execute_stop_game"
    assert r.route("play minecraft for me").handler == "execute_game_autopilot"
    assert e.detect("make a snake game") == "gamedev"
    assert e.detect("build me a game where a ship shoots asteroids") == "gamedev"
    assert e.detect("play a game") is None


def _list(root):
    found = []
    for name in os.listdir(root):
        m = studio.read_manifest(os.path.join(root, name))
        if m:
            found.append(dict(m, path=os.path.join(root, name), mtime=os.path.getmtime(os.path.join(root, name))))
    return sorted(found, key=lambda m: m["mtime"], reverse=True)
