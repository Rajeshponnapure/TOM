"""Experimental game autopilot: the decide->send loop, bounds, stop conditions, and the warned gate —
all with fakes, so no game, no real input, no model. The gate runs through the real policy engine."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools import game_autopilot
from tools.game_autopilot import GameAutopilot


def _ap(decide, sent, grab=None):
    return GameAutopilot(decide=decide, send=lambda a: (sent.append(a), True)[1],
                         grab=grab or (lambda: b"frame-bytes"))


def test_loop_sends_decided_actions_and_is_bounded():
    sent = []
    ap = _ap(decide=lambda frame, game: "W", sent=sent)
    run = ap.play("TestGame", seconds=0.4, fps=20)
    assert run.frames > 0 and run.actions and set(run.actions) == {"W"}
    assert run.stopped_reason == "time elapsed"
    assert sent == run.actions


def test_none_action_sends_nothing():
    sent = []
    ap = _ap(decide=lambda f, g: "NONE", sent=sent)
    run = ap.play("G", seconds=0.3, fps=20)
    assert run.frames > 0 and sent == []          # frames read, but no input sent


def test_stop_halts_the_loop():
    sent = []
    ap = _ap(decide=lambda f, g: "SPACE", sent=sent)
    # stop almost immediately from another thread
    import threading
    threading.Timer(0.1, ap.stop).start()
    run = ap.play("G", seconds=5.0, fps=20)
    assert run.stopped_reason == "stopped by request"


def test_emergency_stop_halts_the_loop(monkeypatch):
    from tom_core.policy.engine import get_policy
    get_policy().halt("test halt")
    try:
        ap = _ap(decide=lambda f, g: "W", sent=[])
        run = ap.play("G", seconds=2.0, fps=20)
        assert run.stopped_reason == "emergency stop"
    finally:
        get_policy().resume()


def test_screen_capture_failure_stops_after_max_fail():
    ap = GameAutopilot(decide=lambda f, g: "W", send=lambda a: True, grab=lambda: None)
    run = ap.play("G", seconds=5.0, fps=50, max_fail=3)
    assert run.stopped_reason == "could not capture the screen"


def test_vision_token_parsing(monkeypatch):
    # the ollama call returns junk around the action; only a valid token survives
    class Resp:
        def __init__(self, text): self._t = text
        def read(self): import json; return json.dumps({"response": self._t}).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr(game_autopilot.urllib.request, "urlopen", lambda *a, **k: Resp("  w  \nmove left"))
    assert game_autopilot._ollama_vision(b"img", "Game", "qwen3.5:4b") == "W"
    monkeypatch.setattr(game_autopilot.urllib.request, "urlopen", lambda *a, **k: Resp("banana"))
    assert game_autopilot._ollama_vision(b"img", "Game", "qwen3.5:4b") == "NONE"


# ── the warned gate ────────────────────────────────────────────────────────
def test_start_is_blocked_without_approval(monkeypatch):
    monkeypatch.setenv("TOM_DISABLE_UI_AUTOMATION", "0")
    monkeypatch.setattr(GameAutopilot, "available", lambda self: True)
    import tom_core.tools.guard as guard
    monkeypatch.setattr(guard, "_approval_manager", None)      # no approval channel → blocked
    played = {"ran": False}
    monkeypatch.setattr(GameAutopilot, "play", lambda self, *a, **k: played.__setitem__("ran", True))
    res = GameAutopilot(decide=lambda f, g: "W").start("Minecraft", seconds=1)
    assert res["status"] in ("blocked", "cancelled") and played["ran"] is False


def test_start_runs_after_approval_and_reports_honestly(monkeypatch):
    monkeypatch.setattr(GameAutopilot, "available", lambda self: True)
    import tom_core.tools.guard as guard
    from tools.approval import ApprovalManager
    mgr = ApprovalManager()
    seen = {}
    mgr.provider = lambda req: (seen.update(summary=req.summary), True)[1]
    monkeypatch.setattr(guard, "_approval_manager", mgr)
    ap = GameAutopilot(decide=lambda f, g: "W", send=lambda a: True, grab=lambda: b"x")
    res = ap.start("Minecraft", seconds=0.3, fps=20)
    assert res["status"] == "success" and res["actions_sent"] > 0
    assert "anti-cheat" in seen["summary"].lower() and "ban" in seen["summary"].lower()  # warning shown


# ── routing: "for me"/"autopilot" vs plain launch ──────────────────────────
def test_routing_distinguishes_autopilot_from_launch():
    from tools.command_router import CommandRouter
    r = CommandRouter()
    assert r.route("play Minecraft for me").handler == "execute_game_autopilot"
    assert r.route("autopilot Minecraft").handler == "execute_game_autopilot"
    # a plain launch of a game that isn't installed falls through (not autopilot)
    assert r.route("play some random uninstalled game").handler != "execute_game_autopilot"


# ── upgraded engine: perception, benchmark, hybrid reflex loop, mouse aim ──
import numpy as np
from tools.game_autopilot import Perception, FastCapture, foreground_region


def test_perception_motion_center_finds_the_moving_region():
    a = np.zeros((200, 300, 3), np.uint8)
    b = a.copy()
    b[80:120, 130:170] = 255                       # a bright block appears mid-frame
    c = Perception.motion_center(a, b)
    assert c is not None and 120 < c[0] < 180 and 80 < c[1] < 120

def test_perception_motion_center_none_when_still():
    a = np.full((100, 100, 3), 50, np.uint8)
    assert Perception.motion_center(a, a.copy()) is None

def test_perception_color_mask_center():
    frame = np.zeros((120, 120, 3), np.uint8)
    frame[40:80, 50:90] = (0, 0, 255)              # a red blob (BGR)
    c = Perception.color_mask_center(frame, (0, 120, 120), (10, 255, 255))
    assert c is not None and 50 < c[0] < 90

def test_benchmark_with_injected_capture_reports_fps(monkeypatch):
    # a fake FastCapture that returns instant frames, so fps is measurable without a display
    class FakeCap:
        def grab_bgr(self): return np.zeros((64, 64, 3), np.uint8)
    ap = GameAutopilot(capture=FakeCap())
    b = ap.benchmark(0.4, with_reflex=False)
    assert b["frames"] > 0 and b["fps"] > 0 and b["error"] == ""

def test_hybrid_loop_runs_reflex_every_frame_and_strategy_occasionally():
    frames = iter([np.zeros((32, 32, 3), np.uint8) for _ in range(10_000)])
    sent = []
    reflex_calls = {"n": 0}
    def reflex(bgr, prev):
        reflex_calls["n"] += 1
        return "W"                                  # always strafe forward
    decide_calls = {"n": 0}
    def decide(png, game):
        decide_calls["n"] += 1
        return "SPACE"
    class Cap:
        def grab_bgr(self): return next(frames)
    ap = GameAutopilot(decide=decide, reflex=reflex, capture=Cap(),
                       send=lambda a: (sent.append(a), True)[1])
    run = ap.play("G", seconds=0.5, strategy_every=0.2)
    assert reflex_calls["n"] > run.strategy_calls          # reflex runs far more often than strategy
    assert "W" in sent and run.frames > 0
    assert run.fps > 0 and run.strategy_calls >= 1

def test_foreground_region_shape():
    r = foreground_region()
    assert r is None or (len(r) == 4 and r[2] > 0 and r[3] > 0)

def test_press_action_and_hold_reject_unknown():
    from tools.game_autopilot import press_action, hold_key
    assert press_action("NONE") is True            # explicit no-op is valid
    assert press_action("BANANA") is False
    assert hold_key("ZZZ", True) is False
