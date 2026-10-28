"""Work out which colours on screen are the player, the target and the hazards — from pixels alone.

A strategy player like Breakout's needs to know *which colour is the paddle, which is the ball*. For
games TOM builds, its manifest says so. For a game that was installed, nothing says so, and there is no
honest way to look it up: the answer is in the game's own art.

So TOM measures it, using the one thing it certainly knows: **which keys it just pressed**. During a short
learning pass it holds left for a while, then right, and watches what moves. The colour whose blob moves
left when left is held and right when right is held is the thing the owner controls — the player. That is
a far stronger signal than "biggest blob" or "middle of the screen", and it is verifiable.

The rest follow from statistics:

* **background** — the colour that covers most of the screen;
* **HUD** — colours confined to the top band (excluded from play so score numbers are not read as actors);
* **target** — the other colour that moves a lot but does *not* answer the keys (a ball, food, an item);
* **hazard** — small moving blobs that approach the player, or that are on screen when a death happens;
* **genre** — a guess from geometry and motion (a wide low paddle plus a bouncing ball is Breakout, a low
  ship plus things falling toward it is a shooter). When no genre is recognised, no strategy is used and
  the state loop runs instead — a wrong guess would play worse than the general loop, not better.

Limits, stated plainly: this works on games with flat, distinct actor colours — 2D arcade games, emulated
mobile games, pixel-art titles. A photorealistic 3D game has no "player colour", and it returns None
rather than inventing one.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

Rgb = Tuple[int, int, int]
Box = Tuple[int, int, int, int]


@dataclass
class BlobStats:
    """How one colour behaves across the captured frames."""
    rgb: Rgb
    coverage: float = 0.0          # share of the frame it covers
    present: float = 0.0           # share of frames where it forms a blob
    area: float = 0.0              # mean blob area as a share of the play area
    blobs: float = 1.0             # mean number of separate blobs
    motion: float = 0.0            # mean centroid movement between frames (pixels)
    response: float = 0.0          # best share of agreeing votes over either probe axis (x or y);
                                   # random ≈ 0.5, a real player is far above (see stats_for)
    y: float = 0.5                 # mean vertical position, 0 top .. 1 bottom
    width: float = 0.0             # mean blob width as a share of the frame
    height: float = 0.0            # mean blob height as a share of the frame
    bounces: int = 0               # vertical direction changes (a ball, a falling enemy)
    dy: float = 0.0                # mean vertical movement per frame (+ = travelling down the screen)

    @property
    def aspect(self) -> float:
        return self.width / self.height if self.height > 1e-6 else 0.0

    @property
    def hud(self) -> bool:
        return self.y < 0.14 and self.present > 0.3


@dataclass
class ColorModel:
    """What the learning pass concluded, and how sure it is."""
    player: Optional[Rgb] = None
    target: Optional[Rgb] = None
    hazard: Optional[Rgb] = None
    background: Optional[Rgb] = None
    hud: Optional[Rgb] = None
    playbox: Optional[Box] = None
    genre: Optional[str] = None
    confidence: float = 0.0
    notes: List[str] = field(default_factory=list)

    def colors(self) -> Dict[str, List[int]]:
        out: Dict[str, List[int]] = {}
        for role in ("player", "target", "hazard", "background", "hud"):
            rgb = getattr(self, role)
            if rgb:
                out[role] = [int(c) for c in rgb]
        return out

    def learned(self) -> bool:
        return self.player is not None


# ── colour palette ─────────────────────────────────────────────────────────
def palette(frames: Sequence, k: int = 16, tol: int = 26, step: int = 2) -> List[Tuple[Rgb, float]]:
    """The dominant colours in the frames, merged and sorted by how much of the screen they cover."""
    import numpy as np
    if not frames:
        return []
    picks = list(frames[:: max(1, len(frames) // 8)])
    # step 2, not 4: a small avatar in a big window is a tiny share of the screen and step 4 dropped it
    pixels = np.concatenate([f[::step, ::step].reshape(-1, 3) for f in picks]).astype(np.int16)
    quant = (pixels >> 3)                              # 5 bits a channel is fine for this
    keys, counts = np.unique(quant, axis=0, return_counts=True)
    order = np.argsort(counts)[::-1][:160]
    merged: List[List[Any]] = []
    for i in order:
        rgb = tuple(int(c) for c in (keys[i].astype(np.int32) << 3) + 4)
        n = int(counts[i])
        for m in merged:
            if max(abs(rgb[j] - m[0][j]) for j in range(3)) <= tol:
                m[1] += n
                break
        else:
            merged.append([rgb, n])
    total = max(1, len(pixels))
    return [(rgb, n / total) for rgb, n in merged[:k]]


def moving_colors(frames: Sequence, k: int = 8, threshold: int = 25, tol: int = 26) -> List[Tuple[Rgb, float]]:
    """The colours of pixels that actually changed between frames, biggest share first.

    A coverage-ranked palette cannot see a small avatar: the snake head in a 1200×900 window is 0.08% of
    the screen, so it never reaches the top sixteen colours and the learning pass concluded "nothing here"
    on a live window (measured 2026-10-28). Motion is the better filter — the things that move are the
    only things worth identifying.
    """
    import numpy as np
    changed = []
    for a, b in zip(frames, frames[1:]):
        diff = np.max(np.abs(b.astype(np.int16) - a.astype(np.int16)), axis=2) > threshold
        if diff.any():
            changed.append(b[diff])
    if not changed:
        return []
    pixels = np.concatenate(changed).astype(np.int16)
    quant = pixels >> 3
    keys, counts = np.unique(quant, axis=0, return_counts=True)
    order = np.argsort(counts)[::-1]
    merged: List[List[Any]] = []
    for i in order[:400]:
        rgb = tuple(int(c) for c in (keys[i].astype(np.int32) << 3) + 4)
        n = int(counts[i])
        for m in merged:
            if max(abs(rgb[j] - m[0][j]) for j in range(3)) <= tol:
                m[1] += n
                break
        else:
            merged.append([rgb, n])
        if len(merged) >= k:
            break
    total = max(1, len(pixels))
    return [(rgb, n / total) for rgb, n in merged[:k]]


def _playbox(frames: Sequence) -> Box:
    h, w = frames[0].shape[:2]
    top = int(h * 0.10)                                # score/lives row, never a playing piece
    return (0, top, w, h - top)


def stats_for(frames: Sequence, rgb: Rgb, box: Box, tol: int = 30, min_area: int = 24,
              pressed: Optional[Sequence[Any]] = None) -> BlobStats:
    """Measure one colour across the frames. `pressed` is per-capture probe input: an int (-1, 0, +1)
    meaning a horizontal press of that sign, or a tuple ("y", sign) for a vertical press. 0 = unknown."""
    import cv2
    import numpy as np
    want = np.array(rgb, dtype=np.int16)
    x0, y0, w, h = box
    st = BlobStats(rgb=tuple(int(c) for c in rgb))
    path: List[Tuple[float, float]] = []
    covered = 0
    frames_with_blob = 0
    areas: List[float] = []
    counts: List[int] = []
    widths: List[float] = []
    heights: List[float] = []
    ys: List[float] = []
    for i, frame in enumerate(frames):
        view = frame[y0:y0 + h, x0:x0 + w]
        mask = (np.abs(view.astype(np.int16) - want) <= tol).all(axis=2)
        covered += float(mask.mean())
        n, _labels, blobs, cents = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=4)
        found = [(int(blobs[j][4]), j) for j in range(1, n) if blobs[j][4] >= min_area]
        counts.append(len(found))
        if not found:
            path.append(path[-1] if path else (-1.0, -1.0))
            continue
        frames_with_blob += 1
        area, j = max(found)
        areas.append(area / float(w * h))
        widths.append(int(blobs[j][2]) / float(w))
        heights.append(int(blobs[j][3]) / float(h))
        ys.append(float(cents[j][1]) / max(1.0, float(h)))
        path.append((float(cents[j][0]), float(cents[j][1])))
    n_frames = max(1, len(frames))
    st.coverage = covered / n_frames
    st.present = frames_with_blob / n_frames
    st.area = sum(areas) / len(areas) if areas else 0.0
    st.blobs = sum(counts) / n_frames
    st.width = sum(widths) / len(widths) if widths else 0.0
    st.height = sum(heights) / len(heights) if heights else 0.0
    st.y = sum(ys) / len(ys) if ys else 0.5
    # movement, and whether that movement answers the keys. Votes are tallied per axis and the best
    # axis wins, because measured live (Viper, 2026-10-28) a snake that glides right can never answer
    # the left key — a left input means "reverse", which snakes reject — so its movement answers only
    # the vertical probe pair, and mixing the axes would drown that signal.
    steps: List[float] = []
    agree_v, asked_v = 0, 0
    agree_h, asked_h = 0, 0
    for i in range(1, len(path)):
        if path[i][0] < 0 or path[i - 1][0] < 0:
            continue
        dx = path[i][0] - path[i - 1][0]
        dy = path[i][1] - path[i - 1][1]
        steps.append((dx * dx + dy * dy) ** 0.5)
        if pressed is None or (abs(dx) < 0.5 and abs(dy) < 0.5):
            continue
        # A tap registers a turn a capture or two late (the game reads it on its own tick), and revive
        # frames are 0 (unknown). So ask the last few probes for each move: the player is the colour
        # whose direction agrees with far more probes than not — a non-answerer splits about 50/50.
        for lag in (1, 2, 3):
            if not (0 <= i - lag < len(pressed)):
                continue
            p = pressed[i - lag]
            axis, s = (p if isinstance(p, tuple) else ("x", p))
            if not s:
                continue
            move = dx if axis == "x" else dy
            if abs(move) < 0.5:
                continue
            if axis == "x":
                asked_h += 1
                agree_h += 1 if move * s > 0 else 0
            else:
                asked_v += 1
                agree_v += 1 if move * s > 0 else 0
    st.motion = sum(steps) / len(steps) if steps else 0.0
    st.response = (max((agree_h / asked_h) if asked_h >= 8 else 0.0,
                       (agree_v / asked_v) if asked_v >= 8 else 0.0))
    # vertical behaviour, ignoring teleports: an enemy that respawns at the top jumps by most of the
    # screen in one frame, which is not a bounce and must not be averaged in as movement
    jump = 0.25 * float(h)
    dys = [path[i][1] - path[i - 1][1] for i in range(1, len(path))
           if path[i][1] >= 0 and path[i - 1][1] >= 0]
    dys = [d for d in dys if abs(d) <= jump]
    st.dy = sum(dys) / len(dys) if dys else 0.0
    # bounces: compare each real vertical move with the last one. Two frames at the same height (the
    # ball reached the wall between captures) used to hide the turn entirely, so zero-moves are skipped
    # rather than treated as a direction.
    previous = None
    for d in dys:
        if abs(d) < 0.5:
            continue
        if previous is not None and previous * d < 0:
            st.bounces += 1
        previous = d
    return st


# ── roles ──────────────────────────────────────────────────────────────────
def infer(frames: Sequence, pressed: Optional[Sequence[int]] = None) -> ColorModel:
    """Which colour is what. Returns a model with `player=None` when nothing answered the keys.

    Frames arrive as captured (BGR). Everything here, and every colour stored in a manifest, is RGB.
    """
    model = ColorModel()
    if not frames:
        model.notes.append("no frames captured")
        return model
    frames = [f[:, :, ::-1] for f in frames]              # BGR (capture) → RGB (what we store)
    h, w = frames[0].shape[:2]
    box = _playbox(frames)
    model.playbox = box
    entries = palette(frames)
    movers = moving_colors(frames)
    if not entries and not movers:
        model.notes.append("the screen has no stable colours")
        return model
    # moving colours first (small actors live there), then the palette (background, static pickups)
    candidates: List[Tuple[Rgb, float]] = []
    for rgb, cov in movers + entries:
        if all(max(abs(rgb[j] - got[j]) for j in range(3)) > 26 for got, _ in candidates):
            candidates.append((rgb, cov))
    seen = [stats_for(frames, rgb, box, pressed=pressed) for rgb, _cov in candidates]
    # background: the biggest area, and it must not be a small moving actor
    for st in sorted(seen, key=lambda s: s.coverage, reverse=True):
        if st.coverage > 0.30:
            model.background = st.rgb
            break
    huds = [st for st in seen if st.hud and st is not None and st.coverage < 0.2]
    if huds:
        model.hud = max(huds, key=lambda s: s.coverage).rgb
    actors = [s for s in seen if s.coverage <= 0.30 and s.present >= 0.35 and s.area > 0]
    # the player is the actor whose movement answers the keys: at random it splits about 50/50
    answering = [s for s in actors if s.response > 0.62]
    if answering:
        player = max(answering, key=lambda s: s.response)
        model.player = player.rgb
        model.confidence = min(1.0, 0.35 + 0.65 * max(0.0, (player.response - 0.5) * 2.0))
    else:
        model.notes.append("nothing on screen moved in answer to the keys, so no player colour was found")
        return model
    others = [s for s in actors if s.rgb != model.player]
    movers = [s for s in others if s.motion >= 0.6]
    # A ball bounces (Breakout, Pong). An enemy travels steadily down the screen toward the player
    # (shooter). A pick-up sits still. Telling these apart matters: the same colour must not be both the
    # goal and the danger, or the strategy will chase what kills it.
    # A ball shows up as: some bounce, and no overall downward drift (its vertical travel cancels out).
    # A falling enemy is the opposite: nearly all of its motion is downward. Two seconds is enough to
    # tell those apart; "bounces twice" is not (one bounce in 40 frames is normal and still a ball).
    bouncy, falling = [], []
    for s in movers:
        speed = max(s.motion, 1e-6)
        if s.bounces >= 1 and abs(s.dy) <= 0.5 * speed:
            bouncy.append(s)
        elif s.dy > 0.3 * speed:
            falling.append(s)
    if bouncy:
        model.target = max(bouncy, key=lambda s: (s.bounces, s.motion)).rgb
    if falling:
        model.hazard = max(falling, key=lambda s: (s.dy, s.motion)).rgb
    if model.target is None and movers:
        rest = [s for s in movers if s.rgb != model.hazard]
        if rest:
            model.target = max(rest, key=lambda s: s.motion).rgb
    if model.hazard is None:
        danger = [s for s in others if s.rgb != model.target and s.area <= 0.02 and s.motion > 0.25]
        if danger:
            model.hazard = max(danger, key=lambda s: (s.blobs, s.motion)).rgb
    model.genre = _genre(seen, model, h, w)
    return model


def _genre(seen: List[BlobStats], model: ColorModel, h: int, w: int) -> Optional[str]:
    """A conservative genre guess. None means "use the general loop", which is never worse than a wrong
    guess: a strategy built on the wrong colours plays badly and blames the game."""
    player = next((s for s in seen if s.rgb == model.player), None)
    target = next((s for s in seen if s.rgb == model.target), None)
    hazard = next((s for s in seen if s.rgb == model.hazard), None)
    if player is None:
        return None
    low = player.y > 0.62
    if target is not None and target.bounces >= 1 and player.aspect >= 1.6 and low:
        # a wide, low paddle and a ball that bounces off the top and bottom
        return "breakout" if 0.15 < player.y < 0.95 else None
    if hazard is not None and low and hazard.y < player.y - 0.15 and hazard.motion > 0.3:
        return "shooter"
    return None


# ── a strategy manifest for an installed game ──────────────────────────────
def manifest_for(model: ColorModel, width: int, height: int,
                 fps: int = 60) -> Optional[Dict[str, Any]]:
    """A manifest the existing strategy players understand, from learned colours. None if no genre."""
    if not model.genre or model.player is None:
        return None
    colors = model.colors()
    colors.setdefault("text", [255, 0, 255])          # never matched: death is handled by the play loop
    needed = {"breakout": ("player", "target"), "pong": ("player", "target", "hazard"),
              "shooter": ("player", "hazard")}[model.genre]
    if any(role not in colors for role in needed):
        return None                                    # missing a role the strategy needs
    return {"genre": model.genre, "width": int(width), "height": int(height), "fps": int(fps),
            "colors": colors, "game": {}, "learned_from": "screen"}


def manifest_from(colors: Dict[str, List[int]], genre: str, width: int, height: int,
                  fps: int = 60) -> Optional[Dict[str, Any]]:
    """The same manifest, rebuilt from colours already stored in a profile (no re-learning needed)."""
    if not genre or not colors.get("player"):
        return None
    got = {role: [int(c) for c in rgb] for role, rgb in colors.items()}
    got.setdefault("text", [255, 0, 255])
    needed = {"breakout": ("player", "target"), "pong": ("player", "target", "hazard"),
              "shooter": ("player", "hazard")}.get(genre, ())
    if not needed or not all(role in got for role in needed):
        return None
    return {"genre": genre, "width": int(width), "height": int(height), "fps": int(fps),
            "colors": got, "game": {}, "learned_from": "screen"}


def describe(model: ColorModel) -> str:
    """A checkable sentence about what was learned."""
    if not model.learned():
        return "I couldn't tell which colour I control on that screen: " + (
            "; ".join(model.notes) or "no colour answered the keys")
    bits = [f"I control the {_rgb(model.player)} blob"]
    if model.target:
        bits.append(f"the thing to go for is {_rgb(model.target)}")
    if model.hazard:
        bits.append(f"the danger is {_rgb(model.hazard)}")
    if model.genre:
        bits.append(f"it plays like a {model.genre} game, so I can use that strategy")
    else:
        bits.append("its type isn't one I have a strategy for, so I'll play it by reading the screen")
    return ", ".join(bits) + "."


def _rgb(rgb: Optional[Rgb]) -> str:
    return "#%02X%02X%02X" % tuple(int(c) for c in rgb) if rgb else "unknown"
