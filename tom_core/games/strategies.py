"""Play the games TOM made from the pixels on screen — the same way a person does, by looking.

Each strategy gets one BGR frame of the game's window (any size: Windows may scale the window, so
everything is measured relative to the size in the game's manifest) and returns what to press:
`Move(hold={...}, tap={...})` with actions up/down/left/right/action/restart. The autopilot turns that
into real key presses; `evaluate()` feeds it straight into the game, headless, so tests can measure how
well it plays (its score against a random player) without a window or a keyboard.

Nothing here reads the game's memory or code — only colours on screen, which the manifest names
(tom_game.json: player, target, hazard, ground …). That is what makes the same approach usable on a
real window captured with mss.
"""
from __future__ import annotations

import importlib.util
import json
import os
import random
import sys
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np

HUD = 44
Box = Tuple[float, float, float, float]          # x, y, w, h in game coordinates


@dataclass
class Move:
    hold: Set[str] = field(default_factory=set)
    tap: Set[str] = field(default_factory=set)
    look: Optional[Tuple[int, int]] = None              # relative mouse move (3D games), if any


class Strategy:
    """Base: colour masks and blobs in game coordinates."""

    tolerance = 38

    def __init__(self, manifest: Dict[str, Any]):
        self.m = manifest
        self.gw, self.gh = manifest.get("width", 800), manifest.get("height", 600)
        self.g = manifest.get("game", {})
        self.bgr = {role: np.array(rgb[::-1], dtype=np.int16) for role, rgb in manifest["colors"].items()}
        self._range = {role: (np.clip(c - self.tolerance, 0, 255).astype(np.uint8),
                              np.clip(c + self.tolerance, 0, 255).astype(np.uint8)) for role, c in self.bgr.items()}
        self.scale = 1.0
        self.frames = 0
        self.fps = float(manifest.get("fps", 60))
        self.now = 0.0
        self.elapsed = 1.0                     # game frames since the previous look (live capture is slower)

    def mask(self, frame, role: str):
        """uint8 mask (255 where the pixel is this role's colour, within the tolerance)."""
        import cv2
        lo, hi = self._range[role]
        return cv2.inRange(np.ascontiguousarray(frame), lo, hi)

    def blobs(self, frame, role: str, min_area: float = 20.0) -> List[Box]:
        import cv2
        mask = self.mask(frame, role)
        top = int(HUD * self.scale)
        mask[:top, :] = 0                                         # score / lives row
        n, _labels, stats, _cent = cv2.connectedComponentsWithStats(mask, connectivity=4)
        s = self.scale
        out = []
        for i in range(1, n):
            x, y, w, h, area = stats[i]
            if area >= min_area * s * s:
                out.append((x / s, y / s, w / s, h / s))
        return out

    def largest(self, frame, role: str, min_area: float = 20.0) -> Optional[Box]:
        boxes = self.blobs(frame, role, min_area)
        return max(boxes, key=lambda b: b[2] * b[3]) if boxes else None

    def game_over(self, frame) -> bool:
        """The runtime writes "Game over" in the text colour across the middle of the screen; during play
        text only appears in the score row at the top."""
        s = self.scale
        band = frame[int((self.gh / 2 - 60) * s):int((self.gh / 2 + 45) * s), :]
        return int(np.count_nonzero(self.mask(band, "text"))) > 400 * s * s

    def act(self, frame, now: Optional[float] = None) -> Move:
        """`now` is the time in seconds (evaluate() passes game time; live play uses the clock), so
        speeds are measured per game frame even when the capture runs slower than the game."""
        import time
        self.frames += 1
        now = time.monotonic() if now is None else now
        if self.frames > 1:
            self.elapsed = min(10.0, max(0.25, (now - self.now) * self.fps))
        self.now = now
        if frame.shape[1] != self.gw or frame.shape[0] != self.gh:
            import cv2                         # a DPI-scaled window: work in the game's own pixels
            frame = cv2.resize(frame, (self.gw, self.gh), interpolation=cv2.INTER_NEAREST)
        self.scale = 1.0
        if self.game_over(frame):
            self.reset_memory()
            return Move(tap={"restart"}) if self.frames % 6 == 0 else Move()
        return self.decide(frame)

    def reset_memory(self) -> None:
        """Forget frame-to-frame state (previous ball position …) between rounds."""
        for name in ("prev_ball", "prev_y", "prev_x", "prev", "last_head", "prev_front"):
            if hasattr(self, name):
                setattr(self, name, None)

    def decide(self, frame) -> Move:
        raise NotImplementedError


def _center(b: Box) -> Tuple[float, float]:
    return b[0] + b[2] / 2, b[1] + b[3] / 2


def _toward(cur: float, goal: float, dead: float, less: str, more: str) -> Set[str]:
    if goal < cur - dead:
        return {less}
    if goal > cur + dead:
        return {more}
    return set()


# ── snake ────────────────────────────────────────────────────────────────
class SnakeStrategy(Strategy):
    DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}

    def __init__(self, manifest):
        super().__init__(manifest)
        self.cols, self.rows = self.g.get("cols", 24), self.g.get("rows", 17)
        self.cell = min(self.gw // self.cols, (self.gh - HUD) // self.rows)
        self.x0 = (self.gw - self.cell * self.cols) // 2
        self.y0 = HUD + (self.gh - HUD - self.cell * self.rows) // 2
        self.last_head = None
        self.heading = (1, 0)
        self.choice: Set[str] = set()

    def _grid(self, frame):
        s = self.scale
        xs = ((self.x0 + (np.arange(self.cols) + 0.5) * self.cell) * s).astype(int)
        ys = ((self.y0 + (np.arange(self.rows) + 0.5) * self.cell) * s).astype(int)
        xs = np.clip(xs, 0, frame.shape[1] - 1)
        ys = np.clip(ys, 0, frame.shape[0] - 1)
        samples = frame[np.ix_(ys, xs)].astype(np.int16)          # rows x cols x 3

        def near(role):
            return np.all(np.abs(samples - self.bgr[role]) <= self.tolerance, axis=2)
        return near("player"), near("player_accent"), near("target")

    def decide(self, frame):
        head_m, body_m, food_m = self._grid(frame)
        heads = np.argwhere(head_m)
        if not len(heads):
            return Move(tap={"restart"}) if self.frames % 30 == 0 else Move()
        head = (int(heads[0][1]), int(heads[0][0]))
        if head == self.last_head:
            return Move(hold=self.choice)
        if self.last_head is not None:
            d = (head[0] - self.last_head[0], head[1] - self.last_head[1])
            if d in self.DIRS.values():
                self.heading = d
        self.last_head = head
        blocked = {(int(c), int(r)) for r, c in np.argwhere(body_m)}
        foods = [(int(c), int(r)) for r, c in np.argwhere(food_m)]
        step = self._plan(head, blocked, foods[0] if foods else None)
        self.choice = {step} if step else set()
        return Move(hold=self.choice)

    def _free(self, cell, blocked):
        return 0 <= cell[0] < self.cols and 0 <= cell[1] < self.rows and cell not in blocked

    def _area(self, start, blocked, limit):
        seen, todo = {start}, deque([start])
        while todo and len(seen) < limit:
            x, y = todo.popleft()
            for dx, dy in self.DIRS.values():
                n = (x + dx, y + dy)
                if n not in seen and self._free(n, blocked):
                    seen.add(n)
                    todo.append(n)
        return len(seen)

    def _plan(self, head, blocked, food) -> Optional[str]:
        reverse = (-self.heading[0], -self.heading[1])
        options = {name: (head[0] + d[0], head[1] + d[1]) for name, d in self.DIRS.items() if d != reverse}
        options = {k: v for k, v in options.items() if self._free(v, blocked)}
        if not options:
            return None
        need = len(blocked) + 2
        if food is not None:                                       # shortest path that leaves room to live
            prev = {head: None}
            todo = deque([head])
            while todo:
                cur = todo.popleft()
                if cur == food:
                    break
                for d in self.DIRS.values():
                    n = (cur[0] + d[0], cur[1] + d[1])
                    if n not in prev and self._free(n, blocked):
                        prev[n] = cur
                        todo.append(n)
            if food in prev:
                cur = food
                while prev[cur] != head:
                    cur = prev[cur]
                first = next((k for k, v in options.items() if v == cur), None)
                if first and self._area(cur, blocked | {head}, need) >= need:
                    return first
        return max(options, key=lambda k: self._area(options[k], blocked | {head}, 10_000))


# ── breakout ─────────────────────────────────────────────────────────────
class BreakoutStrategy(Strategy):
    def __init__(self, manifest):
        super().__init__(manifest)
        self.prev_ball = None

    def decide(self, frame):
        paddle = self.largest(frame, "player", 300)
        ball = self.largest(frame, "target", 40)
        if paddle is None:
            return Move(tap={"restart"}) if self.frames % 30 == 0 else Move()
        px = _center(paddle)[0]
        if ball is None:
            self.prev_ball = None
            return Move(hold=_toward(px, self.gw / 2, 12, "left", "right"))
        bx, by = _center(ball)
        goal = bx
        if self.prev_ball is not None:
            vx, vy = bx - self.prev_ball[0], by - self.prev_ball[1]
            if abs(vx) + abs(vy) < 0.5:                             # stuck on the paddle: launch it
                self.prev_ball = (bx, by)
                return Move(tap={"action"})
            if vy > 0:                                              # falling: where will it reach the paddle?
                goal = _bounce(bx, vx / vy * (paddle[1] - by), 0, self.gw)
        self.prev_ball = (bx, by)
        return Move(hold=_toward(px, goal, 10, "left", "right"))


def _bounce(x: float, dx: float, lo: float, hi: float) -> float:
    span = hi - lo
    if span <= 0:
        return x
    p = (x - lo + dx) % (2 * span)
    return lo + (p if p <= span else 2 * span - p)


# ── flappy ───────────────────────────────────────────────────────────────
class FlappyStrategy(Strategy):
    def __init__(self, manifest):
        super().__init__(manifest)
        self.prev_y = None
        self.gap = self.g.get("gap", 175)

    def decide(self, frame):
        bird = self.largest(frame, "player", 120)
        if bird is None:
            return Move(tap={"restart"}) if self.frames % 30 == 0 else Move()
        bx, by = _center(bird)
        vy = 0.0 if self.prev_y is None else by - self.prev_y
        self.prev_y = by
        pipes = [p for p in self.blobs(frame, "hazard", 200) if p[0] + p[2] > bird[0] - 4]
        target = self.gh / 2
        if pipes:
            nearest = min(p[0] for p in pipes)
            column = [p for p in pipes if abs(p[0] - nearest) < 8]
            tops = [p for p in column if p[1] <= HUD + 2]
            bottoms = [p for p in column if p[1] > HUD + 2]
            gap_top = max((p[1] + p[3] for p in tops), default=HUD)
            gap_bottom = min((p[1] for p in bottoms), default=gap_top + self.gap)
            target = (gap_top + gap_bottom) / 2 + 18
            if bird[1] < gap_top + 12:
                return Move()
        if by > target and vy >= 0:
            return Move(tap={"action"})
        return Move()


# ── shooter ──────────────────────────────────────────────────────────────
class ShooterStrategy(Strategy):
    def decide(self, frame):
        ship = self.largest(frame, "player", 300)
        if ship is None:
            return Move(tap={"restart"}) if self.frames % 30 == 0 else Move()
        sx = _center(ship)[0]
        enemies = self.blobs(frame, "hazard", 200)
        if not enemies:
            return Move(hold={"action"} | _toward(sx, self.gw / 2, 20, "left", "right"))
        target = max(enemies, key=lambda e: e[1] - abs(_center(e)[0] - sx) * 0.35)
        return Move(hold={"action"} | _toward(sx, _center(target)[0], 6, "left", "right"))


# ── runner ───────────────────────────────────────────────────────────────
class RunnerStrategy(Strategy):
    def __init__(self, manifest):
        super().__init__(manifest)
        self.prev_x = None
        self.speed = float(self.g.get("speed", 6.0))
        jump, grav = abs(self.g.get("jump", -15.5)), self.g.get("gravity", 0.8)
        self.apex = jump / grav                                     # frames to the top of a jump

    def decide(self, frame):
        me = self.largest(frame, "player", 300)
        if me is None:
            return Move(tap={"restart"}) if self.frames % 30 == 0 else Move()
        ahead = [o for o in self.blobs(frame, "hazard", 150) if o[0] + o[2] > me[0]]
        if not ahead:
            self.prev_x = None
            return Move()
        ob = min(ahead, key=lambda o: o[0])
        step = (self.prev_x - ob[0]) / self.elapsed if self.prev_x is not None else 0.0
        if 0 < step < 30:
            self.speed = 0.7 * self.speed + 0.3 * step
        self.prev_x = ob[0]
        distance = ob[0] - (me[0] + me[2])
        window = self.apex * self.speed - (ob[2] + me[2]) / 2 - 8
        return Move(hold={"action"}) if 0 <= distance <= window else Move()


# ── pong ─────────────────────────────────────────────────────────────────
class PongStrategy(Strategy):
    def __init__(self, manifest):
        super().__init__(manifest)
        self.prev = None

    def decide(self, frame):
        boxes = [b for b in self.blobs(frame, "player", 300) if b[0] < self.gw / 2]
        if not boxes:
            return Move(tap={"restart"}) if self.frames % 30 == 0 else Move()
        paddle = max(boxes, key=lambda b: b[3])
        py = _center(paddle)[1]
        ball = self.largest(frame, "target", 60)
        if ball is None:
            return Move(hold=_toward(py, self.gh / 2, 10, "up", "down"))
        bx, by = _center(ball)
        goal = by
        if self.prev is not None:
            vx, vy = bx - self.prev[0], by - self.prev[1]
            if vx < -0.5:
                my_x = paddle[0] + paddle[2]
                landing = _bounce(by, vy / vx * (my_x - bx), HUD + 7, self.gh - 7)
                # meet the ball off-centre so it leaves steeply, toward wherever the computer can't reach
                cpu = [b for b in self.blobs(frame, "hazard", 300) if b[0] > self.gw / 2]
                cpu_x, cpu_y = _center(cpu[0]) if cpu else (self.gw - 30, self.gh / 2)
                speed = min(13.0, abs(vx) / self.elapsed + 0.35)
                best_aim, best_gap = 40, -1.0
                for aim in (40, -40):
                    out_vy = speed * 0.75 * (aim / 50)
                    arrive = _bounce(landing, out_vy / speed * (cpu_x - my_x), HUD + 7, self.gh - 7)
                    if abs(arrive - cpu_y) > best_gap:
                        best_aim, best_gap = aim, abs(arrive - cpu_y)
                goal = landing - best_aim
            else:
                goal = (by + self.gh / 2) / 2
        self.prev = (bx, by)
        return Move(hold=_toward(py, goal, 8, "up", "down"))


# ── racer ────────────────────────────────────────────────────────────────
class RacerStrategy(Strategy):
    def __init__(self, manifest):
        super().__init__(manifest)
        self.lanes = max(3, int(self.g.get("lanes", 3)))
        self.left = self.gw // 2 - self.lanes * 60
        self.cooldown_until = 0.0
        self.speed = float(self.g.get("speed", 5.0))
        self.prev_front = None

    def lane_of(self, x: float) -> int:
        return int(max(0, min(self.lanes - 1, (x - self.left) // 120)))

    def decide(self, frame):
        car = self.largest(frame, "player", 400)
        if car is None:
            return Move(tap={"restart"}) if self.frames % 30 == 0 else Move()
        cx = _center(car)[0]
        lane = self.lane_of(cx)
        settled = abs(cx - (self.left + 60 + lane * 120)) < 6
        traffic = self.blobs(frame, "hazard", 400)
        front = max((t[1] for t in traffic if t[1] < car[1]), default=None)
        if front is not None and self.prev_front is not None:
            step = (front - self.prev_front) / self.elapsed
            if 0 < step < 30:
                self.speed = 0.7 * self.speed + 0.3 * step
        self.prev_front = front
        danger = max(160.0, self.speed * 30)                         # ~half a second of travel
        clear = {}
        for ln in range(self.lanes):
            ahead = [t[1] + t[3] for t in traffic if self.lane_of(_center(t)[0]) == ln and t[1] < car[1] + car[3]]
            clear[ln] = car[1] - max(ahead) if ahead else 10_000.0
        side = {ln: all(not (self.lane_of(_center(t)[0]) == ln and t[1] < car[1] + car[3] + 10
                             and t[1] + t[3] > car[1] - 30) for t in traffic) for ln in range(self.lanes)}
        if not settled or self.now < self.cooldown_until or clear[lane] > danger:
            return Move()
        options = [ln for ln in (lane - 1, lane + 1) if 0 <= ln < self.lanes and side[ln]]
        if not options:
            return Move()
        best = max(options, key=lambda ln: clear[ln])
        if clear[best] <= clear[lane]:
            return Move()
        self.cooldown_until = self.now + 0.1
        return Move(tap={"left" if best < lane else "right"})


# ── platformer ───────────────────────────────────────────────────────────
class PlatformerStrategy(Strategy):
    REACH = 125
    LEDGE_ENEMY = 45          # don't jump onto a ledge with an enemy this close (px; tuned headless)
    FLEE = 0                  # back away from an enemy above this close (px; 0 = never, measured best)

    def decide(self, frame):
        me = self.largest(frame, "player", 300)
        if me is None:
            return Move(tap={"restart"}) if self.frames % 30 == 0 else Move()
        mx, feet = _center(me)[0], me[1] + me[3]
        coins = self.blobs(frame, "target", 60)
        plats = self.blobs(frame, "ground", 200)
        enemies = self.blobs(frame, "hazard", 120)
        hold: Set[str] = set()
        standing = any(abs(p[1] - feet) < 3 and p[0] - 2 <= me[0] + me[2] and me[0] <= p[0] + p[2] + 2 for p in plats)
        no_jump, flee = False, None
        for e in enemies:
            ex, rise = _center(e)[0], feet - (e[1] + e[3])        # rise > 0: the enemy stands above our feet
            if abs(rise) < 24 and abs(ex - mx) < 70:
                if standing:
                    hold |= {"action"}                             # level with us: hop over it
                else:
                    flee = "left" if ex > mx else "right"          # mid-air next to it: drift away
            elif 0 < rise < self.REACH + 20 and abs(ex - mx) < self.LEDGE_ENEMY:
                no_jump = True                                     # it's on the ledge we'd jump onto
                if abs(ex - mx) < self.FLEE:
                    flee = "left" if ex > mx else "right"
        if not coins:
            return Move(hold=hold)
        coin = min(coins, key=lambda c: abs(_center(c)[0] - mx) + 2.2 * max(0.0, feet - (c[1] + c[3])))
        cx, cy = _center(coin)
        goal_x = cx
        under = [p for p in plats if p[0] - 4 <= cx <= p[0] + p[2] + 4 and p[1] > cy]
        stand = min(under, key=lambda p: p[1]) if under else None
        if stand is not None and stand[1] < feet - 8:              # the coin sits on a higher platform
            if stand[1] < feet - self.REACH:                       # too high: go via a stepping platform
                steps = [p for p in plats if feet - self.REACH <= p[1] < feet - 8]
                if steps:
                    stand = min(steps, key=lambda p: abs(_center(p)[0] - cx))
                    goal_x = min(max(cx, stand[0] + 20), stand[0] + stand[2] - 20)
            near_edge = stand[0] - 40 <= mx <= stand[0] + stand[2] + 40
            if near_edge:
                hold |= {"action"}
        on = [p for p in plats if abs(p[1] - feet) < 6 and p[0] - 2 <= me[0] + me[2] and me[0] <= p[0] + p[2] + 2]
        if on and on[0][2] < self.gw * 0.9:
            lo, hi = min(p[0] for p in on), max(p[0] + p[2] for p in on)
            grew = True
            while grew:                                            # ledges with a gap too narrow to drop through
                grew = False
                for p in plats:
                    if abs(p[1] - feet) < 6 and p[0] < self.gw * 0.9 and (lo - me[2] - 4 < p[0] + p[2] < lo or
                                                                          hi < p[0] < hi + me[2] + 4):
                        lo, hi, grew = min(lo, p[0]), max(hi, p[0] + p[2]), True
            if cy > feet and lo - 10 <= cx <= hi + 10:
                # the coin is below this ledge: walk off the nearer end instead of standing over it
                goal_x = lo - 24 if mx - lo < hi - mx else hi + 24
                self.drop = (goal_x, feet)
        drop = getattr(self, "drop", None)
        if drop is not None:                                       # keep walking until we actually fall
            if abs(feet - drop[1]) < 3 and abs(mx - drop[0]) > 4:
                goal_x = drop[0]
            else:
                self.drop = None
        steer = _toward(mx, goal_x, 6, "left", "right")
        if on and steer and on[0][2] < self.gw * 0.9:              # about to run off a ledge: leap instead
            edge = on[0][0] if steer == {"left"} else on[0][0] + on[0][2]
            if abs(mx - edge) < 26 and cy < feet + 40:
                hold |= {"action"}
        if no_jump:
            hold.discard("action")
        if flee:
            steer = {flee}
        return Move(hold=hold | steer)


STRATEGIES: Dict[str, Callable[[Dict[str, Any]], Strategy]] = {
    "snake": SnakeStrategy, "breakout": BreakoutStrategy, "flappy": FlappyStrategy, "shooter": ShooterStrategy,
    "runner": RunnerStrategy, "pong": PongStrategy, "racer": RacerStrategy, "platformer": PlatformerStrategy,
}


def for_manifest(manifest: Optional[Dict[str, Any]]) -> Optional[Strategy]:
    if not manifest or manifest.get("genre") not in STRATEGIES or "colors" not in manifest:
        return None
    return STRATEGIES[manifest["genre"]](manifest)


# ── headless evaluation ──────────────────────────────────────────────────
class _Scripted:
    def __init__(self):
        self.held_now: Set[str] = set()
        self._prev: Set[str] = set()
        self._taps: Set[str] = set()

    def set(self, move: Move):
        self._prev, self.held_now, self._taps = self.held_now, set(move.hold), set(move.tap)

    def held(self, name):
        return name in self.held_now or name in self._taps

    def tapped(self, name):
        return name in self._taps or (name in self.held_now and name not in self._prev)


def _load_game(path: str):
    sys.modules.pop("tomgame", None)
    sys.path.insert(0, path)
    try:
        spec = importlib.util.spec_from_file_location(f"tom_made_game_{abs(hash(path))}", os.path.join(path, "main.py"))
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, sys.modules["tomgame"]
    finally:
        sys.path.remove(path)


def evaluate(path: str, frames: int = 3600, player: str = "strategy", seed: int = 7) -> Dict[str, Any]:
    """Play a made game headless for `frames` frames. player='strategy' plays by sight; 'random'
    mashes keys. Returns score stats — the measurable answer to "can TOM play it?"."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    with open(os.path.join(path, "tom_game.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    with open(os.path.join(path, "config.json"), encoding="utf-8") as fh:
        cfg = json.load(fh)
    cfg["seed"] = seed
    module, runtime = _load_game(path)
    import pygame
    pygame.font.init()
    screen = pygame.Surface((cfg["width"], cfg["height"]))
    game = module.Game(cfg, random.Random(seed))
    controls = _Scripted()
    strategy = for_manifest(manifest) if player == "strategy" else None
    rng = random.Random(seed)
    scores: List[int] = []
    was_over = False
    for _ in range(frames):
        game.draw(screen)
        runtime.draw_hud(screen, game)
        if strategy is not None:
            rgb = pygame.surfarray.pixels3d(screen)
            frame = np.ascontiguousarray(np.transpose(rgb, (1, 0, 2))[:, :, ::-1])
            del rgb
            move = strategy.act(frame, now=game.frame / 60.0)
        else:
            move = Move(hold=set(rng.sample(("up", "down", "left", "right", "action"), rng.randint(0, 2))),
                        tap={"restart"} if game.over else set())
        controls.set(move)
        game.update(controls)
        if game.over and not was_over:
            scores.append(game.score)
        was_over = game.over
    if not game.over:
        scores.append(game.score)
    return {"player": player, "frames": frames, "best": max(scores) if scores else 0,
            "mean": round(sum(scores) / len(scores), 2) if scores else 0.0, "rounds": len(scores), "scores": scores}
