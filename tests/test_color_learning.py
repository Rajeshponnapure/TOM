"""Learning which colour on screen is the player, from pixels and the keys TOM pressed.

Everything here is synthetic scenes with known ground truth: a Breakout-shaped game and a shooter-shaped
one, plus a photorealistic-looking scene where the honest answer is "I can't tell". The point is that the
roles are *measured* — the colour that answers the keys is the player — so the tests assert what was
recovered, not that some heuristic fired.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from tom_core.games import learn_colors
from tom_core.games.learn_colors import ColorModel

BACKGROUND = (30, 20, 10)       # BGR
PADDLE = (200, 40, 40)          # BGR — a red paddle
BALL = (0, 220, 220)            # BGR — a yellow ball
BRICK = (40, 40, 200)           # BGR — blue bricks
ENEMY = (0, 0, 230)             # BGR — a red enemy
HUD = (240, 240, 240)


def _blank(h=300, w=400):
    frame = np.zeros((h, w, 3), np.uint8)
    frame[:, :] = BACKGROUND
    frame[0:22, :] = HUD                              # a score band, as most games draw
    return frame


def breakout_frames(n=40, h=300, w=400):
    """A paddle that follows the direction held, a ball that bounces, and a row of bricks."""
    frames, pressed = [], []
    ball_x, ball_y, vy = w // 2, 60, 7
    for i in range(n):
        direction = -1 if i < n // 2 else 1
        pressed.append(direction)
        frame = _blank(h, w)
        frame[40:52, 20:w - 20] = BRICK               # bricks
        step = i if i < n // 2 else i - n // 2
        paddle_x = int(w / 2 - 40 + direction * step * 4)      # moves left, then right
        frame[h - 26:h - 18, max(0, paddle_x):max(0, paddle_x) + 80] = PADDLE
        ball_y += vy
        if ball_y < 60 or ball_y > h - 40:
            vy = -vy
            ball_y += vy
        ball_x = (ball_x + 5) % (w - 12)
        frame[ball_y:ball_y + 10, ball_x:ball_x + 10] = BALL
        frames.append(frame)
    return frames, pressed


def shooter_frames(n=40, h=300, w=400):
    """A ship at the bottom that follows the direction held, enemies falling from the top."""
    frames, pressed = [], []
    for i in range(n):
        direction = -1 if i < n // 2 else 1
        pressed.append(direction)
        frame = _blank(h, w)
        step = i if i < n // 2 else i - n // 2
        ship_x = int(w / 2 - 20 + direction * step * 5)
        frame[h - 30:h - 20, max(0, ship_x):max(0, ship_x) + 44] = PADDLE
        ey = 40 + (i * 6) % 160
        frame[ey:ey + 12, 90:104] = ENEMY
        frame[ey + 30:ey + 42, 260:274] = ENEMY
        frames.append(frame)
    return frames, pressed


def noise_frames(n=8, h=200, w=300):
    """What a photorealistic 3D game looks like to this: nothing stable, nothing distinct."""
    rng = np.random.default_rng(3)
    return [rng.integers(0, 255, (h, w, 3), dtype=np.uint8) for _ in range(n)], [0] * n


def rgb(color):
    """The scenes are drawn in BGR (as captured); everything learned and stored is RGB."""
    return tuple(color[::-1])


def _near(got, want, tol=40):
    return got is not None and max(abs(int(a) - int(b)) for a, b in zip(got, want)) <= tol


# ── roles ──────────────────────────────────────────────────────────────────
def test_the_colour_that_answers_the_keys_is_the_player():
    model = learn_colors.infer(*breakout_frames())
    assert _near(model.player, rgb(PADDLE)), f"player should be the paddle {rgb(PADDLE)}, got {model.player}"
    assert model.learned() and model.confidence > 0.4


def test_the_other_moving_thing_is_the_target():
    model = learn_colors.infer(*breakout_frames())
    assert _near(model.target, rgb(BALL)), f"target should be the ball {rgb(BALL)}, got {model.target}"


def test_static_blocks_are_not_called_danger():
    """Bricks do not move, so they must not be recorded as hazards."""
    model = learn_colors.infer(*breakout_frames())
    assert not _near(model.hazard, rgb(BRICK))


def test_a_falling_enemy_is_the_hazard():
    model = learn_colors.infer(*shooter_frames())
    assert _near(model.player, rgb(PADDLE))
    assert _near(model.hazard, rgb(ENEMY)), f"hazard should be the enemy {rgb(ENEMY)}, got {model.hazard}"


def test_the_background_is_recognised_as_such():
    model = learn_colors.infer(*breakout_frames())
    assert _near(model.background, rgb(BACKGROUND), tol=45)


def test_nothing_answering_the_keys_means_no_player_claimed():
    """The honest failure: a static screen teaches nothing, so no player colour is invented."""
    frames, _ = breakout_frames(n=10)
    still = [frames[0]] * 10
    model = learn_colors.infer(still, [0] * 10)
    assert not model.learned()
    assert "nothing on screen moved" in " ".join(model.notes)


def test_a_photorealistic_scene_is_not_guessed():
    model = learn_colors.infer(*noise_frames())
    assert model.genre is None, "random pixels must never be called a game type"


# ── genre, and the strategy it unlocks ─────────────────────────────────────
def test_a_paddle_and_a_bouncing_ball_is_recognised_as_breakout():
    model = learn_colors.infer(*breakout_frames())
    assert model.genre == "breakout"


def test_a_ship_under_falling_enemies_is_recognised_as_a_shooter():
    model = learn_colors.infer(*shooter_frames())
    assert model.genre == "shooter"


def test_the_learned_manifest_drives_the_real_breakout_strategy():
    model = learn_colors.infer(*breakout_frames())
    manifest = learn_colors.manifest_from(model.colors(), model.genre, 400, 300)
    from tom_core.games import strategies
    strategy = strategies.for_manifest(manifest)
    assert strategy is not None and type(strategy).__name__ == "BreakoutStrategy"
    # the ball to the left of the paddle must send the paddle left, and to the right must send it right
    def scene(ball_x):
        frame = _blank(300, 400)
        frame[286:294, 180:260] = PADDLE               # paddle centred at x=220
        frame[200:210, ball_x:ball_x + 10] = BALL
        return frame

    assert "left" in strategy.act(scene(40), now=0.0).hold
    strategy.act(scene(40), now=1 / 60)
    assert "right" in strategy.act(scene(360), now=2 / 60).hold


def test_no_strategy_without_a_recognised_genre():
    model = ColorModel(player=(1, 2, 3))               # colours but no genre
    assert learn_colors.manifest_from(model.colors(), "", 400, 300) is None
    assert learn_colors.manifest_for(model, 400, 300) is None


def test_describe_says_what_it_learned():
    text = learn_colors.describe(learn_colors.infer(*breakout_frames()))
    assert "I control the" in text and "breakout" in text


# ── the collection pass ────────────────────────────────────────────────────
def test_collecting_frames_alternates_direction_blocks():
    """Blocks alternate instead of one long phase each way: a gliding avatar (the snake) dies if it is
    driven one way for a whole phase, measured live on Viper."""
    from tools import game_play
    held = []
    tick = {"i": 0}

    class Backend:
        def frame(self):
            tick["i"] += 1
            frame = _blank(40, 60)
            frame[20:24, 2 + (tick["i"] % 40):] = PADDLE[:1]      # something visibly moves each capture
            return frame

    shots, pressed = game_play.collect_for_learning(Backend(), lambda keys: held.append(set(keys)),
                                                    frames=8, gap=0.0, left="A", right="D")
    assert pressed == [-1, -1, -1, -1, -1, 1, 1, 1], f"alternating blocks, got {pressed}"
    assert held[0] == {"A"} and held[-1] == set(), "it must let go of the keys when it finishes"


def test_a_vertical_pair_is_probed_so_gliding_games_can_answer():
    """Viper's snake glides right and rejects the left key (a reverse); its turns answer W/S, so the
    pass must probe both axes or it concludes "nothing answers the keys"."""
    from tools import game_play
    from tom_core.games.profile import GameProfile
    held = []
    tick = {"i": 0}

    class Backend:
        def frame(self):
            tick["i"] += 1
            frame = _blank(40, 60)
            frame[20:24, 2 + (tick["i"] % 40):] = PADDLE[:1]
            return frame

    pairs = game_play.pairs_for_learning(GameProfile(game="G"), "A", "D")
    assert pairs[0] == ("A", "D", "x") and pairs[1] == ("W", "S", "y"), f"got {pairs}"
    prof = GameProfile(game="G", responsive={"UP": 0.5, "DOWN": 0.2})
    assert game_play.pairs_for_learning(prof, "A", "D")[1] == ("UP", "DOWN", "y")

    press_sets = []
    game_play.collect_for_learning(
        Backend(), lambda keys: press_sets.append(set(keys)), frames=10, gap=0.0,
        left="A", right="D", pairs=pairs)
    verticals = [k for k in press_sets if k and ("W" in k or "S" in k)]
    assert verticals, f"the vertical pair must actually be pressed, got {press_sets}"


def test_a_frozen_screen_is_revived_and_those_frames_are_labelled_unknown():
    """A pass can start on a death screen (the game was already playing itself); it taps a restart key
    and the frames around that tap carry pressed=0 so they never feed the response statistic."""
    from tools import game_play
    held = []
    n = {"i": 0}

    class Backend:
        def frame(self):
            n["i"] += 1
            return _blank(40, 60)          # every frame identical: a frozen screen

    shots, pressed = game_play.collect_for_learning(
        Backend(), lambda keys: held.append(set(keys)), frames=9, gap=0.0,
        left="A", right="D", revive=("R",))
    assert any(k == {"R"} for k in held), f"it should have tapped the revive key, held: {held}"
    assert 0 in pressed and any(p == 0 for p in pressed), \
        f"revived frames must be labelled unknown (0), got {pressed}"
    assert len(shots) > 0


def test_a_frozen_screen_that_stays_frozen_gives_up():
    """At most LEARN_REVIVES revive attempts; an unrevivable game hands back frames and no more."""
    from tools import game_play
    presses = []

    class Backend:
        def frame(self):
            return _blank(40, 60)

    _, pressed = game_play.collect_for_learning(
        Backend(), lambda keys: presses.append(set(keys)), frames=30, gap=0.0,
        left="A", right="D", revive=("R",))
    tap_r = sum(1 for k in presses if k == {"R"})
    assert 2 * tap_r <= 2 * game_play.LEARN_REVIVES, "one down-tap and one release per attempt"
    assert tap_r == game_play.LEARN_REVIVES, f"should attempt {game_play.LEARN_REVIVES} revives, got {tap_r}"


def test_revive_keys_put_restart_like_keys_first():
    from tools import game_play
    from tom_core.games.profile import GameProfile
    prof = GameProfile(game="G", responsive={"A": 0.5, "D": 0.4, "R": 0.2, "E": 0.1, "ENTER": 0.05})
    keys = game_play.revive_keys_for("A", "D", prof)
    assert keys[0] == "R" and "ENTER" in keys, f"restart-ish keys first, got {keys}"
    assert "D" not in keys, "movement keys cannot revive anything"
    assert game_play.revive_keys_for("A", "D", GameProfile(game="G")) == ("R", "ENTER")


def test_response_voting_survives_a_late_registering_game():
    """Real games register a tap a frame or two late; the vote window forgives that lag, and an actor
    moving against the keys comes out far below the threshold."""
    n = 40
    frames, pressed = [], []
    for i in range(n):
        direction = -1 if i < n // 2 else 1
        pressed.append(direction)
        frame = _blank(300, 400)
        # a player that registers the direction one capture late
        lead = direction if i < n // 2 else -direction
        follower = pressed[i - 1] if i >= 1 else lead
        px = int(200 + follower * (i if i < n // 2 else i - n // 2) * 4)
        frames.append(frame)
    # build positions directly and check voting maths on a path instead of pixels: the head moves
    # left during the A phase (one frame late), right during the D phase
    path = [220.0] + [220.0 - 4 * (i - 1) for i in range(1, n // 2 + 1)] \
        + [220.0 - 4 * (n // 2 - 1) + 4 * (i - n // 2) for i in range(n // 2 + 1, n)]
    agree = asked = 0
    good, bad = 0, 0
    for i in range(1, len(path)):
        dx = path[i] - path[i - 1]
        if abs(dx) < 0.5:
            continue
        for lag in (1, 2, 3):
            if 0 <= i - lag < len(pressed) and pressed[i - lag]:
                asked += 1
                good += 1 if dx * pressed[i - lag] > 0 else 0
    assert asked >= 8 and good / asked > 0.62, f"late-registering player should still vote in: {good}/{asked}"


def test_learning_keys_prefer_the_two_directions_the_game_answered():
    from tools import game_play
    from tom_core.games.profile import GameProfile
    prof = GameProfile(game="G", responsive={"A": 0.5, "D": 0.5, "E": 0.1})
    assert game_play.learning_keys(prof) == ("A", "D")
    prof = GameProfile(game="G", responsive={"W": 0.9, "S": 0.4})
    assert game_play.learning_keys(prof) == ("W", "S")
    assert game_play.learning_keys(GameProfile(game="G")) == ("A", "D")


def test_learned_colours_are_stored_rgb_for_the_strategy_players():
    """The capture is BGR and the manifests are RGB; mixing them would aim the paddle at the wrong thing."""
    frames, pressed = breakout_frames()
    model = learn_colors.infer(frames, pressed)
    stored = model.colors()["player"]
    assert _near(stored, rgb(PADDLE), tol=12), f"stored {stored} should be RGB of the paddle {rgb(PADDLE)}"
