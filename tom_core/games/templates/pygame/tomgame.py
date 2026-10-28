"""Runtime shared by every pygame game TOM makes: config, window, input, game-over/restart and stats.

Copied next to main.py in each generated project, so the project runs on its own (`python main.py`).

Self-test: with TOM_GAME_SELFTEST=<frames> the game runs headless (SDL dummy video/audio) for that many
frames with a random bot at the controls, then prints one line `TOM_SELFTEST {json}` and exits 0. TOM
uses it to prove a generated game really runs before it says the game is ready.

Stats: the score, best score and number of rounds are written to stats.json every couple of seconds and
on exit, so anyone (including TOM's autopilot) can read how a run went.
"""
import json
import os
import random
import sys
import time

SELFTEST_FRAMES = int(os.environ.get("TOM_GAME_SELFTEST", "0") or 0)
if SELFTEST_FRAMES:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402  (the SDL environment above must be set first)

HERE = os.path.dirname(os.path.abspath(__file__))
ACTIONS = ("up", "down", "left", "right", "action", "restart")
KEYS = {
    "up": (pygame.K_UP, pygame.K_w),
    "down": (pygame.K_DOWN, pygame.K_s),
    "left": (pygame.K_LEFT, pygame.K_a),
    "right": (pygame.K_RIGHT, pygame.K_d),
    "action": (pygame.K_SPACE,),
    "restart": (pygame.K_r, pygame.K_RETURN),
    "quit": (pygame.K_ESCAPE,),
}


def load_config():
    with open(os.path.join(HERE, "config.json"), encoding="utf-8") as fh:
        return json.load(fh)


def color(cfg, role):
    return tuple(cfg["colors"][role])


class Controls:
    """What the player is pressing this frame: held actions plus the ones newly pressed (taps).

    A tap shorter than one frame still counts, because KEYDOWN events are read as well as key state.
    `override` lets a script or test drive the game without a keyboard: a callable returning the set
    of held actions for this frame.
    """

    def __init__(self, seed=0, override=None):
        self.held_now = set()
        self._prev = set()
        self._down = set()
        self.override = override
        self._bot = random.Random(seed) if (SELFTEST_FRAMES and override is None) else None
        self._bot_held = set()
        self._bot_left = 0

    def poll(self, events, game_over=False):
        self._prev = self.held_now
        self._down = set()
        for event in events:
            if event.type == pygame.KEYDOWN:
                for name, keys in KEYS.items():
                    if event.key in keys:
                        self._down.add(name)
        if self.override is not None:
            self.held_now = set(self.override())
        elif self._bot is not None:
            self.held_now = self._bot_step(game_over)
        else:
            pressed = pygame.key.get_pressed()
            self.held_now = {name for name, keys in KEYS.items() if any(pressed[k] for k in keys)}

    def _bot_step(self, game_over):
        if self._bot_left <= 0:
            self._bot_left = self._bot.randint(4, 18)
            if game_over:
                self._bot_held = {"restart"}
            else:
                self._bot_held = set(self._bot.sample(("up", "down", "left", "right", "action"),
                                                      self._bot.randint(0, 2)))
        self._bot_left -= 1
        return self._bot_held

    def held(self, name):
        return name in self.held_now

    def tapped(self, name):
        return name in self._down or (name in self.held_now and name not in self._prev)


class BaseGame:
    """One game: reset() sets up a round, step(controls) plays one frame, draw(screen) renders it.
    Calling end() finishes the round; restart (R / Enter / Space) starts a new one."""

    def __init__(self, cfg, rng=None):
        self.cfg = cfg
        self.w, self.h = cfg["width"], cfg["height"]
        self.rng = rng or random.Random(cfg.get("seed"))
        self.score = 0
        self.best = 0
        self.rounds = 1
        self.over = False
        self.frame = 0
        self.reset()

    def reset(self):
        raise NotImplementedError

    def step(self, controls):
        raise NotImplementedError

    def draw(self, screen):
        raise NotImplementedError

    def end(self):
        self.over = True
        self.best = max(self.best, self.score)

    def update(self, controls):
        self.frame += 1
        if self.over:
            if controls.tapped("restart") or controls.tapped("action"):
                self.rounds += 1
                self.score = 0
                self.over = False
                self.reset()
            return
        self.step(controls)
        self.best = max(self.best, self.score)

    def stats(self):
        return {"score": self.score, "best": self.best, "rounds": self.rounds, "over": self.over,
                "frames": self.frame}


_FONTS = {}


def text(screen, cfg, message, size, center=None, topleft=None):
    font = _FONTS.get(size)
    if font is None:
        font = _FONTS[size] = pygame.font.Font(None, size)
    surf = font.render(str(message), True, color(cfg, "text"))
    rect = surf.get_rect()
    if center is not None:
        rect.center = center
    else:
        rect.topleft = topleft or (10, 8)
    screen.blit(surf, rect)


def draw_hud(screen, game):
    text(screen, game.cfg, f"Score {game.score}   Best {game.best}", 30, topleft=(12, 8))
    if game.over:
        text(screen, game.cfg, "Game over", 64, center=(game.w // 2, game.h // 2 - 24))
        text(screen, game.cfg, "Press R, Enter or Space to play again", 30, center=(game.w // 2, game.h // 2 + 24))


def write_stats(game, path=None):
    path = path or os.path.join(HERE, "stats.json")
    data = dict(game.stats(), title=game.cfg.get("title", ""), updated=time.time())
    try:
        with open(path + ".tmp", "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        os.replace(path + ".tmp", path)
    except OSError:
        pass
    return data


def run(game_class):
    """Open the window and play until the window closes, Esc, or the self-test frame budget runs out."""
    cfg = load_config()
    pygame.init()
    screen = pygame.display.set_mode((cfg["width"], cfg["height"]))
    pygame.display.set_caption(cfg["title"])
    clock = pygame.time.Clock()
    game = game_class(cfg)
    controls = Controls(seed=cfg.get("seed") or 0)
    last_save = time.monotonic()
    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
        controls.poll(events, game.over)
        if controls.tapped("quit"):
            running = False
        was_over = game.over
        game.update(controls)
        game.draw(screen)
        draw_hud(screen, game)
        pygame.display.flip()
        if (game.over and not was_over) or time.monotonic() - last_save > 2.0:
            write_stats(game)
            last_save = time.monotonic()
        if SELFTEST_FRAMES and game.frame >= SELFTEST_FRAMES:
            running = False
        clock.tick(0 if SELFTEST_FRAMES else cfg.get("fps", 60))
    stats = write_stats(game)
    pygame.quit()
    if SELFTEST_FRAMES:
        print("TOM_SELFTEST " + json.dumps(stats))
        sys.stdout.flush()
    return stats
