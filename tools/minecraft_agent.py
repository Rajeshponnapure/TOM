"""TOM's Minecraft agent: from the main menu to a world, by reading the screen and deciding each step.

"open minecraft, create a creative world called test server 1 and build a modern 3-floor house" —
TOM looks at the game window, reads its buttons (tom_core.games.ui_reader), works out which screen it is
on, and does the next thing toward the goal: Play → Create New → Create New World → name the world →
Creative → cheats on → Create → wait for the world → build (tools.minecraft_build) with chat commands.

Each screen is recognised by the labels on it, not by fixed coordinates, so moved or restyled buttons
still work; an unknown screen with a "Continue"/"OK"-style button is accepted; a screen with nothing
TOM recognises is reported instead of clicked at random. Every frame TOM saw and every action it took is
kept in `trace`, so a run can be checked afterwards.

Input only goes to the Minecraft window (BlueStacks): before every click or key TOM checks the window
is still in front, and stops if it isn't.
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from tom_core.games import ui_reader as ui

ACCEPT = ("Create anyway", "Continue", "OK", "Okay", "Proceed", "Yes", "Got it", "Confirm", "Accept", "Done",
          "Let's Go", "Start", "Play anyway", "Continue anyway")
DISMISS = ("Not now", "No thanks", "Maybe later", "Skip", "Close", "Cancel")


@dataclass
class Step:
    screen: str
    labels: List[str]
    action: str
    detail: str = ""
    frame_path: str = ""


@dataclass
class Goal:
    world: str = "test server 1"
    mode: str = "creative"                    # creative | survival | adventure
    cheats: bool = True
    must_exist: bool = False                  # the owner named an existing world: never create one


class MinecraftAgent:
    def __init__(self, hwnd: int, trace_dir: Optional[str] = None, grab: Optional[Callable] = None,
                 click: Optional[Callable[[int, int], bool]] = None, typer: Optional[Callable[[str], None]] = None,
                 press: Optional[Callable[[str], bool]] = None, foreground: Optional[Callable[[], bool]] = None,
                 reader: Callable = ui.read, sleep: Callable[[float], None] = time.sleep):
        from tools import game_autopilot as ga
        self.hwnd = hwnd
        self.trace_dir = trace_dir
        self.trace: List[Step] = []
        self.reader = reader
        self.sleep = sleep
        self._grab = grab
        self._click = click
        self.typer = typer
        self.press = press or (lambda k: ga.press_action(k, 0.05))
        self.foreground = foreground or (lambda: ga.is_foreground(hwnd))
        self.region: Optional[Tuple[int, int, int, int]] = None
        self.done: Dict[str, bool] = {}

    # ── seeing and acting ──────────────────────────────────────────────────
    def look(self):
        if self._grab is not None:
            frame = self._grab()
        else:
            from tools import game_autopilot as ga
            ga.set_dpi_aware()
            self.region = ga.client_region(self.hwnd)
            cap = ga.FastCapture(region=self.region)
            try:
                frame = cap.grab_bgr().copy()
            finally:
                cap.close()
        # the emulator's own title bar ("BlueStacks App Player") and side toolbar are not the game
        top, right = int(frame.shape[0] * 0.045), int(frame.shape[1] * 0.975)
        items = [it for it in self.reader(frame) if it.box[1] > top and it.box[0] < right]
        return frame, items

    def grab(self):
        """One frame of the game window, no reading (~10 ms)."""
        if self._grab is not None:
            return self._grab()
        from tools import game_autopilot as ga
        self.region = ga.client_region(self.hwnd)
        cap = ga.FastCapture(region=self.region)
        try:
            return cap.grab_bgr().copy()
        finally:
            cap.close()

    def _save(self, frame, n: int) -> str:
        if not self.trace_dir:
            return ""
        import cv2
        os.makedirs(self.trace_dir, exist_ok=True)
        path = os.path.join(self.trace_dir, f"step_{n:02d}.png")
        cv2.imwrite(path, frame)
        return path

    def click(self, item: ui.Item) -> bool:
        if not self.foreground():
            raise RuntimeError("Minecraft is no longer in front; stopped before clicking.")
        x, y = item.center
        if self._click is not None:
            return self._click(x, y)
        from tools import game_autopilot as ga
        ox, oy = (self.region or (0, 0, 0, 0))[:2]
        import ctypes
        ctypes.windll.user32.SetCursorPos(int(ox + x), int(oy + y))
        time.sleep(0.08)
        ga._send_mouse(0x0002)                     # left down: BlueStacks turns it into a tap
        time.sleep(0.07)
        return ga._send_mouse(0x0004)

    def select_by_keys(self, target: str, max_moves: int = 8) -> bool:
        """The other way to press a button when clicks don't reach it (in a world BlueStacks turns the mouse
        into camera/attack input): move the menu focus with the arrow keys until the target is the
        highlighted (green) one, then press Enter."""
        for key in ("DOWN", "UP"):
            for _ in range(max_moves):
                frame, items = self.look()
                item = ui.find(items, target, threshold=0.8)
                if item is not None and self.selected(frame, item):
                    self.press("SPACE")
                    return True
                self.press(key)
                self.sleep(0.35)
        return False

    def scroll(self, x: int, y: int, notches: int) -> None:
        """Scroll the list under (x, y) — for options pushed off screen."""
        if not self.foreground():
            raise RuntimeError("Minecraft is no longer in front; stopped before scrolling.")
        if self._click is not None:                   # tests: record it as a pseudo-click
            self._click(-x, -y)
            return
        from tools import game_autopilot as ga
        import ctypes
        ox, oy = (self.region or (0, 0, 0, 0))[:2]
        ctypes.windll.user32.SetCursorPos(int(ox + x), int(oy + y))
        time.sleep(0.08)
        ga.scroll_wheel(notches)

    def type(self, text: str) -> None:
        if not self.foreground():
            raise RuntimeError("Minecraft is no longer in front; stopped before typing.")
        if self.typer is not None:
            self.typer(text)
        else:
            from tools.game_tasks import type_text
            type_text(text)

    # ── which screen is this, and what to do on it ─────────────────────────
    @staticmethod
    def classify(items: List[ui.Item]) -> str:
        has = lambda *t: ui.find(items, *t) is not None          # noqa: E731
        buttons = [it for it in items if it.kind == "button"]
        # a pop-up sits on top of whatever screen is behind it, so it comes first
        if ui.find(buttons, *ACCEPT, threshold=0.85) is not None and (
                has("Go back", "Cancel", "No", "Not now") or has("can't", "cannot", "warning", "are you sure")):
            return "dialog"
        if has("Create World", "Create") and (has("World Name") or has("Game Mode") or has("Difficulty")
                                               or has("My World") or has("Survival") or has("Creative")
                                               or has("Activate Cheats")):
            return "world_settings"
        if ui.find(buttons, "Play", threshold=0.9) is not None and (has("Settings") or has("Marketplace") or has("Realms")):
            return "main_menu"
        if ui.find(buttons, "Play", threshold=0.9) is not None and has("Edit", "Delete", "Copy World", "Export"):
            return "world_card"
        if has("Create New World", "New World"):
            return "create_menu"
        if has("Create New") and (has("Worlds") or has("Servers") or has("Friends") or has("Import")):
            return "worlds_list"
        if has("Create New"):
            return "worlds_list"
        if has("Generating", "Loading", "Building terrain", "Locating server", "Preparing"):
            return "loading"
        if has("Resume Game", "Save & Quit", "Save and Quit"):
            return "paused"
        if has("Chat and Commands"):
            return "chat"
        if ui.find(items, *ACCEPT):
            return "dialog"
        return "unknown"

    def step(self, goal: Goal) -> Step:
        frame, items = self.look()
        screen = self.classify(items)
        labels = ui.labels(items)
        n = len(self.trace) + 1
        path = self._save(frame, n)

        def act(action: str, detail: str = "") -> Step:
            s = Step(screen, labels, action, detail, path)
            self.trace.append(s)
            return s

        recent = self.trace[-3:]
        if len(recent) == 3 and len({(r.screen, r.action, r.detail) for r in recent}) == 1 and recent[0].action != "wait":
            # the same thing three times and nothing changed: try another way — accept any pop-up, else back out
            target = ui.find([it for it in items if it.kind == "button"], *ACCEPT, threshold=0.75)
            if target is not None:
                self.click(target)
                return act("click", f"{target.text} (unsticking)")
            self.press("ESC")
            return act("key", "ESC (unsticking: the last action changed nothing)")

        if screen == "main_menu":
            self.click(ui.find(items, "Play"))
            return act("click", "Play")
        existing = ui.find([it for it in items if it.box[1] > frame.shape[0] * 0.2], goal.world, threshold=0.85)             if screen in ("worlds_list", "create_menu") and not self.done.get("created") else None
        if existing is not None and ui.score(existing.text, "Create new world") < 0.8:
            self.click(existing)                          # the world already exists: open it, don't make a twin
            self.done.update(name=True, mode=True, cheats=True, created=True, reopened=True)
            return act("click", f"existing world '{existing.text}'")
        if goal.must_exist and screen in ("worlds_list", "create_menu") and not self.done.get("reopened"):
            return act("none", f"the world '{goal.world}' isn't in the list, and you asked me not to create one")
        if screen == "worlds_list":
            self.click(ui.find(items, "Create New"))
            return act("click", "Create New")
        if screen == "create_menu":
            self.click(ui.find(items, "Create New World", "New World"))
            return act("click", "Create New World")
        if screen == "world_settings":
            return self._world_settings(frame, items, goal, act)
        if screen == "paused":                            # mouse clicks resume the game here: use the keys
            ok = self.select_by_keys("Resume Game")
            return act("keys", "Resume Game" if ok else "couldn't reach Resume Game")
        if screen == "chat":                              # chat left open: close it to see the world
            self.press("ESC")
            return act("key", "ESC (close chat)")
        if screen == "world_card":                        # a world's detail card: Play it
            self.click(ui.find([it for it in items if it.kind == "button"], "Play", threshold=0.85))
            return act("click", "Play (world)")
        if screen == "loading":
            self.sleep(2.0)
            return act("wait", "the world is loading")
        if screen == "dialog":
            target = ui.find([it for it in items if it.kind == "button"], *ACCEPT, threshold=0.85) or ui.find(items, *ACCEPT)
            self.click(target)
            return act("click", target.text)
        return act("none", "no screen I recognise")

    @staticmethod
    def selected(frame, item: ui.Item) -> bool:
        """Minecraft marks the chosen option (Survival/Creative, a toggle that is on) in green."""
        x, y, w, h = item.box
        patch = frame[y + h // 4:y + 3 * h // 4, x + w // 4:x + 3 * w // 4]
        if patch.size == 0:
            return False
        b, g, r = [float(c) for c in patch.reshape(-1, 3).mean(axis=0)]
        return g > r + 35 and g > b + 35

    @staticmethod
    def switch_on(frame, box) -> Optional[bool]:
        """A Minecraft on/off switch: the light knob sits on the right when it's on, on the left when off."""
        x, y, w, h = box
        patch = frame[y:y + h, x:x + w]
        if patch.size == 0 or w < 8:
            return None
        px = patch.reshape(-1, 3).astype(int)
        green = ((px[:, 1] > px[:, 2] + 40) & (px[:, 1] > px[:, 0] + 40)).mean()
        if green > 0.12:                                   # the "on" half is drawn green
            return True
        g = patch.mean(axis=2)
        left, right = float(g[:, : w // 2].mean()), float(g[:, w // 2:].mean())
        if abs(left - right) < 20:
            return None
        return right > left

    def _switch_box(self, frame, label: ui.Item):
        """The switch on a setting's row: the far-right end of the row the label starts."""
        H, W = frame.shape[:2]
        if label.kind == "button" and label.box[2] > W * 0.4:          # the whole row is one panel
            x, y, w, h = label.box
            return (int(W * 0.89), y + int(h * 0.15), int(W * 0.065), int(h * 0.7))
        y0 = max(0, label.box[1] - 20)
        return (int(W * 0.89), y0, int(W * 0.065), min(H - y0, label.box[3] + 45))

    def _world_settings(self, frame, items, goal: Goal, act) -> Step:
        """Name → game mode → cheats → Create. One change per look, and each change is checked on the
        next look (the name really reads "test server 1", Creative really turned green) before moving on."""
        W = frame.shape[1]
        tries = self.done.setdefault("tries", {})
        # 1. the world's name
        if not self.done.get("name"):
            field = ui.find([it for it in items if it.kind == "button"], "My World", goal.world, threshold=0.55)
            same_case = field is not None and (field.text.isupper() == goal.world.isupper())
            if field is not None and ui.score(field.text, goal.world) >= 0.8 and same_case:
                self.done["name"] = True
            elif field is not None and tries.get("name", 0) < 3:
                tries["name"] = tries.get("name", 0) + 1
                self.click(field)
                self.sleep(1.0)
                self.press("END")
                for _ in range(max(24, len(field.text) + 6)):
                    self.press("BACKSPACE")
                self.type(goal.world)
                self.sleep(0.4)
                self.press("ENTER")
                return act("type", f"world name '{goal.world}' (was '{field.text}')")
            else:
                return act("none", f"couldn't set the world name (field reads '{field.text if field else 'nothing'}')")
        # 2. the game mode
        if not self.done.get("mode"):
            want = ui.find(items, goal.mode.title(), threshold=0.75)
            if want is not None and self.selected(frame, want):
                self.done["mode"] = True
            elif want is not None and tries.get("mode", 0) < 3:
                tries["mode"] = tries.get("mode", 0) + 1
                self.click(want)
                return act("click", goal.mode.title())
            elif want is None and ui.find(items, "World name") is None:
                tab = ui.find(items, "General", threshold=0.8)        # we're on another tab: go back
                if tab is not None:
                    self.click(tab)
                    return act("click", "General tab")
                return act("none", "can't find the game mode options")
            else:
                return act("none", f"{goal.mode.title()} didn't get selected")
        # 3. cheats (commands: /fill, /setblock … need them)
        if goal.cheats and not self.done.get("cheats"):
            right = [it for it in items if it.box[0] > W * 0.3]
            rows = [it for it in right if re.search(r"\bcheat", it.text, re.I)
                    and ui._norm(it.text) != ui._norm("Cheat Settings")]     # the switch row, not the header
            label = ui.find(items, "Activate Cheats", threshold=0.8) or ui.find(
                [it for it in right if it.kind == "text"], "Cheats", threshold=0.85) or (
                min(rows, key=lambda it: it.box[1]) if rows else None)
            header = ui.find(right, "Cheat Settings", threshold=0.85)
            if label is None and header is not None:            # the switch row sits just above the header
                x, y, w, h = header.box
                label = ui.Item("cheats row", 0, (x, max(0, y - 128), max(w, int(W * 0.45)), 116), "button")
            if label is None:
                tab = ui.find([it for it in items if it.box[0] < W * 0.35], "Cheats", threshold=0.75)
                if tab is not None and tries.get("cheats_tab", 0) < 2:
                    tries["cheats_tab"] = tries.get("cheats_tab", 0) + 1
                    self.click(tab)
                    return act("click", "Cheats tab")
                if tries.get("scroll", 0) < 3:                         # pushed off screen: scroll the menu
                    tries["scroll"] = tries.get("scroll", 0) + 1
                    self.scroll(int(W * 0.15), int(frame.shape[0] * 0.85), -5)
                    return act("scroll", "the left menu, looking for Cheats")
                return act("none", "can't find the Cheats settings")
            box = self._switch_box(frame, label)
            state = self.switch_on(frame, box)
            if state is True:
                self.done["cheats"] = True
            elif tries.get("cheats", 0) < 3:
                tries["cheats"] = tries.get("cheats", 0) + 1
                self.click(ui.Item("switch", 0, box))
                return act("click", f"the Cheats switch (it was {'off' if state is False else 'unreadable'})")
            else:
                return act("none", "the Cheats switch won't turn on")
        # 4. create it
        create = ui.find([it for it in items if it.kind == "button"], "Create", threshold=0.85)
        if create is not None and ui.score(create.text, "Create on Realms") < 0.9:
            self.click(create)
            self.done["created"] = True
            return act("click", "CREATE")
        return act("none", "the world settings screen has no Create button I can read")

    @staticmethod
    def hotbar(frame) -> bool:
        """Minecraft's hotbar: a row of 9 equal squares near the bottom centre — only shown in a world."""
        import cv2
        import numpy as np
        H, W = frame.shape[:2]
        band = frame[int(H * 0.86):H, int(W * 0.25):int(W * 0.75)]
        g = cv2.cvtColor(band, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(g, 30, 100)
        cols = (edges > 0).sum(axis=0)
        peaks = np.where(cols > band.shape[0] * 0.3)[0]
        if len(peaks) < 8:
            return False
        groups = np.split(peaks, np.where(np.diff(peaks) > 12)[0] + 1)    # a slot border is a few lines
        xs = np.array([int(gr.mean()) for gr in groups])
        # the ten slot borders sit on a strict grid (~4 % of the width apart); the world behind the
        # see-through slots adds stray edges, so look for the grid, not for equal gaps
        best = 0
        for start in xs[:6]:
            for period in np.arange(W * 0.038, W * 0.044, 1.0):
                expected = start + period * np.arange(10)
                hits = int(sum(np.min(np.abs(xs - e)) <= 5 for e in expected))
                best = max(best, hits)
        return best >= 8

    def in_world(self, items: List[ui.Item], frame=None) -> bool:
        if frame is not None and self.hotbar(frame):
            return True
        return self.classify(items) == "unknown" and len(items) <= 6

    def enter_world(self, goal: Goal, max_steps: int = 30) -> Dict[str, Any]:
        """Play → … → a freshly created world, then report what was done."""
        for _ in range(max_steps):
            frame, items = self.look()
            if self.in_world(items, frame) and self.hotbar(frame):
                verb = "Opened" if self.done.get("reopened") else "Created and opened" if self.done.get("created") else "Already in"
                return {"status": "success", "trace": self.trace, "message": f"{verb} the world '{goal.world}'."}
            s = self.step(goal)
            if s.action == "none":
                if s.screen == "unknown" and self.done.get("created"):
                    self.sleep(3.0)                       # loading tips / terrain: give it time
                    continue
                return {"status": "error", "trace": self.trace,
                        "message": f"I got stuck on a screen I don't recognise (it shows: {', '.join(s.labels) or 'no readable buttons'})."}
            self.sleep(1.5 if s.action == "click" else 0.5)
        return {"status": "error", "trace": self.trace, "message": f"I didn't reach the world within {max_steps} steps."}


# ── typing commands into the game ──────────────────────────────────────────
class ChatDriver:
    """Opens Minecraft's chat, enters one command, sends it, reads the game's reply.

    Ways in, tried in order: the T key, then the / key (chat opens with the slash typed). Ways to enter
    the text: paste from the clipboard (exact and fast — BlueStacks hands the PC clipboard to Android),
    then slow typing. The input box is read before Enter, so a garbled command is never sent.
    """

    def __init__(self, agent: "MinecraftAgent", paste: Optional[Callable[[str], None]] = None,
                 slow_type: Optional[Callable[[str], None]] = None):
        self.agent = agent
        self._paste = paste
        self._slow = slow_type

    def _frame(self):
        frame, _items = self.agent.look()
        return frame

    def _lines(self, frame, box) -> List[str]:
        H, W = frame.shape[:2]
        x0, y0, x1, y1 = int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H)
        crop = frame[y0:y1, x0:x1]
        if crop.size == 0:
            return []
        try:
            return [it.text for it in ui.read(crop, max_panels=6)]
        except Exception:
            return []

    def _read(self, frame, box) -> str:
        return " ".join(self._lines(frame, box))

    def chat_open(self, frame) -> bool:
        return ui.score(self._read(frame, (0.2, 0.03, 0.8, 0.13)), "Chat and Commands") >= 0.7

    @staticmethod
    def chat_bar(frame) -> bool:
        """Chat is open: its flat light-grey title bar spans the top of the window (a 1 ms pixel check)."""
        H, W = frame.shape[:2]
        band = frame[int(H * 0.055):int(H * 0.1), int(W * 0.05):int(W * 0.35)]
        if band.size == 0:
            return False
        g = band.mean(axis=2)
        return float(g.mean()) > 165 and float(g.std()) < 22

    def fast(self, command: str) -> bool:
        """Enter one command quickly: (re)open chat if needed, click the box, paste, Enter."""
        a = self.agent
        if not a.foreground():
            return False
        frame = a.grab()
        if not self.chat_bar(frame):
            a.press("T")
            for _ in range(6):
                a.sleep(0.25)
                frame = a.grab()
                if self.chat_bar(frame):
                    break
            else:
                return False
        H, W = frame.shape[:2]
        a.click(ui.Item("chat input", 0, (int(W * 0.3), int(H * 0.915), int(W * 0.4), int(H * 0.06))))
        a.sleep(0.1)
        self.paste(command)
        a.sleep(0.12)
        a.press("ENTER")
        a.sleep(0.3)
        return True

    def input_text(self, frame) -> str:
        """The chat input line: light text on the grey bar, read as one line ('' if unreadable)."""
        import cv2
        import numpy as np
        H, W = frame.shape[:2]
        crop = frame[int(H * 0.91):int(H * 0.99), int(W * 0.11):int(W * 0.86)]
        if crop.size == 0:
            return ""
        g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        img = cv2.copyMakeBorder(np.where(g > 200, 0, 255).astype(np.uint8), 12, 12, 12, 12,
                                 cv2.BORDER_CONSTANT, value=255)
        try:
            return ui._ocr_line(img)[0]
        except Exception:
            return ""

    def replies(self, frame) -> List[str]:
        return self._lines(frame, (0.0, 0.1, 0.75, 0.89))

    def reply(self, frame) -> str:
        return " ".join(self.replies(frame))

    def paste(self, text: str) -> None:
        if self._paste is not None:
            return self._paste(text)
        from tools import game_autopilot as ga
        from tools.hardware_control import _set_clipboard_unicode
        _set_clipboard_unicode(text)
        time.sleep(0.15)                               # BlueStacks copies the PC clipboard to Android
        ga.hold_key("CTRL", True)
        ga._send_scancode(0x2F, True)                  # V
        time.sleep(0.04)
        ga._send_scancode(0x2F, False)
        ga.hold_key("CTRL", False)

    def slow_type(self, text: str) -> None:
        if self._slow is not None:
            return self._slow(text)
        from tools.game_tasks import type_text
        type_text(text, gap=0.09)

    def run(self, command: str, settle: float = 0.9, check_input: bool = True) -> Dict[str, Any]:
        from tools.game_tasks import read_reply
        a = self.agent
        if not a.foreground():
            return {"ok": False, "kind": "not_focused", "command": command}
        frame = self._frame()
        opened, text = self.chat_open(frame), command               # chat may still be open from before
        for opener in (() if opened else ("T", "SLASH")):
            a.press(opener)
            for _ in range(4):                                     # it takes a moment to slide in
                a.sleep(0.45)
                frame = self._frame()
                if self.chat_open(frame):
                    opened, text = True, (command if opener == "T" else command.lstrip("/"))
                    break
            if opened:
                break
            a.press("ESC")
            a.sleep(0.4)
        if not opened:
            return {"ok": False, "kind": "chat_failed", "command": command}
        before = set(self.replies(frame))
        probe = command.lstrip("/").split()[0].lower()
        H, W = frame.shape[:2]
        box = ui.Item("chat input", 0, (int(W * 0.3), int(H * 0.915), int(W * 0.4), int(H * 0.06)))
        for enter in (self.paste, self.slow_type):
            if not a.foreground():
                return {"ok": False, "kind": "not_focused", "command": command}
            a.click(box)                                    # give the input box the keyboard first
            a.sleep(0.3)
            enter(text)
            a.sleep(0.35)
            seen = self.input_text(self._frame()).lower() if check_input else ""
            # the pixel font reads "time" as "tine": compare loosely, and an unreadable box is not a failure
            if not check_input or not seen.strip() or ui.score(seen.lstrip("|/ "), text.lstrip("/")) >= 0.6                     or probe[:3] in seen:
                break
            for _ in range(len(text) + 4):                 # clear what went wrong, try the next way
                a.press("BACKSPACE")
        a.press("ENTER")
        a.sleep(settle)
        new_lines = [ln for ln in self.replies(self._frame()) if ln not in before]   # only what this command got
        said = " ".join(new_lines)
        out = read_reply(said)
        out.update(command=command, said=said[:200])
        return out


def build(parts, driver: ChatDriver, progress: Optional[Callable[[int, int, str], None]] = None,
          check_every: int = 1) -> Dict[str, Any]:
    """Type a blueprint, one command at a time. A refused command is recorded and the build goes on
    (one unknown block shouldn't cost the whole house); cheats being off or losing focus stops it."""
    done, failed = 0, []
    for i, part in enumerate(parts, 1):
        r = driver.run(part.command, check_input=(i % max(1, check_every) == 0))
        if progress:
            progress(i, len(parts), part.what)
        if r["kind"] in ("not_focused", "chat_failed"):
            return {"status": "error", "done": done, "failed": failed, "stopped": r["kind"], "at": part.what}
        if r["kind"] == "denied" and re.search(r"permission|cheat", r.get("said", ""), re.I):
            return {"status": "error", "done": done, "failed": failed, "stopped": "cheats_off", "at": part.what}
        if r["kind"] == "denied":
            failed.append({"what": part.what, "command": part.command, "said": r.get("said", "")})
        else:
            done += 1
    return {"status": "success" if not failed else "partial", "done": done, "failed": failed}


# ── one request, start to finish ───────────────────────────────────────────
_NAME = re.compile(r"(?:called|named|name (?:it|the (?:server|world))(?: as)?|with the name)\s+[\"']?"
                   r"([A-Za-z0-9][\w '-]{0,40}?)[\"']?(?=\s*[,.;!?]|\s+(?:and|it|in|with|then|inside|open|launch)\b|$)",
                   re.IGNORECASE)


def parse_session(text: str) -> Optional[Dict[str, Any]]:
    """{'world', 'mode', 'build'} for "open minecraft, create a creative server called test server 1 and
    build a modern 3 floor house"; None when it isn't a Minecraft world/build request."""
    t = text or ""
    low = t.lower()
    if "minecraft" not in low or not re.search(r"\b(world|server|build|construct|house|structure)\b", low):
        return None
    name = _NAME.search(t)
    mode = next((m for m in ("creative", "survival", "adventure") if m in low), "creative")
    build = ""
    m = re.search(r"\b(?:build|construct|create|make)\b(?:(?!\b(?:world|server)\b).)*?\b(house|home|villa|duplex|mansion|"
                  r"building|tower|structure)\b.*", t, re.IGNORECASE | re.DOTALL)
    if m:
        build = m.group(0).strip()
    world = name.group(1).strip() if name else ""
    if not world and not build:
        return None
    existing = bool(re.search(r"\b(existing|already (?:made|created)|that (?:was|you) (?:just )?(?:created|made)|"
                              r"same world|my world)\b", low))
    return {"world": world or "TOM world", "mode": mode, "build": build, "existing": existing}


def wait_for_menu(agent: "MinecraftAgent", timeout: float = 120.0) -> str:
    """After launching: wait until Minecraft shows something TOM can act on (menu or a world)."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        frame, items = agent.look()
        if agent.hotbar(frame):
            return "in_world"
        screen = agent.classify(items)
        if screen != "unknown":
            return screen
        agent.sleep(3.0)
    return "unknown"


def quit_to_menu(agent: "MinecraftAgent", tries: int = 4) -> bool:
    """Leave the current world for the main menu (pause → Save & Quit, by keys)."""
    for _ in range(tries):
        frame, items = agent.look()
        screen = agent.classify(items)
        if screen == "main_menu":
            return True
        if screen == "paused":
            agent.select_by_keys("Save & Quit")
            agent.sleep(6.0)
            continue
        agent.press("ESC")
        agent.sleep(1.5)
    return agent.classify(agent.look()[1]) == "main_menu"


def build_fast(parts, driver: ChatDriver, check_every: int = 12,
               progress: Optional[Callable[[int, int, str], None]] = None) -> Dict[str, Any]:
    """The whole blueprint at ~1 s a command: the first command goes through the careful path (proves
    chat, paste and cheats work), the rest through `fast`, with Minecraft's replies scanned for errors
    every `check_every` commands. Cheats off or lost focus stops the build; other refusals are counted."""
    from tools.game_tasks import _DENIED
    t0 = time.monotonic()
    first = driver.run(parts[0].command)
    if first["kind"] in ("not_focused", "chat_failed"):
        return {"status": "error", "done": 0, "stopped": first["kind"], "errors": [], "seconds": 0}
    if first["kind"] == "denied" and re.search(r"permission|cheat", first.get("said", ""), re.I):
        return {"status": "error", "done": 0, "stopped": "cheats_off", "errors": [first.get("said", "")], "seconds": 0}
    done, errors, seen = 1, [], set()
    for i, part in enumerate(parts[1:], 2):
        if not driver.fast(part.command):
            return {"status": "error", "done": done, "stopped": "not_focused_or_chat", "at": part.what,
                    "errors": errors, "seconds": round(time.monotonic() - t0)}
        done += 1
        if progress:
            progress(i, len(parts), part.what)
        if i % check_every == 0 or i == len(parts):
            for line in driver.replies(driver.agent.grab()):
                if line not in seen and _DENIED.search(line):
                    errors.append(line)
                seen.add(line)
            if any(re.search(r"permission|cheat", e, re.I) for e in errors):
                return {"status": "error", "done": done, "stopped": "cheats_off", "errors": errors,
                        "seconds": round(time.monotonic() - t0)}
    return {"status": "success" if not errors else "partial", "done": done, "errors": errors,
            "seconds": round(time.monotonic() - t0)}
