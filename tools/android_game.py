"""Android games (BlueStacks or any emulator/phone with ADB) as the game brain's eyes and hands.

Why ADB rather than clicking the BlueStacks window: a tap through ADB lands at an exact point on the
Android screen, needs no keyboard focus, and can never type into another Windows app. The screenshot comes
from Android itself (`screencap`), so it is the game's real pixels, not whatever window is on top.

Setup the owner does once: BlueStacks → Settings → Advanced → turn on "Android Debug Bridge" → Save.
BlueStacks ships its own adb (HD-Adb.exe, next to HD-Player.exe). The port differs per instance and can
change between starts, so TOM looks for it in this order: BLUESTACKS_ADB (e.g. 127.0.0.1:5555), devices
adb already knows, the port in bluestacks.conf, then the common defaults.

Everything that runs a command goes through `run`, so tests replace it and need no device.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from tom_core.games import brain

Runner = Callable[[Sequence[str], float, bool], Tuple[int, bytes]]

ADB_CANDIDATES = (
    r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe",
    r"C:\Program Files\BlueStacks\HD-Adb.exe",
    r"C:\Program Files (x86)\BlueStacks\HD-Adb.exe",
)
CONF_CANDIDATES = (
    r"C:\ProgramData\BlueStacks_nxt\bluestacks.conf",
    r"C:\ProgramData\BlueStacks\bluestacks.conf",
)
DEFAULT_PORTS = (5555, 5565, 5575, 5585, 5595)
KNOWN_PACKAGES = {
    "minecraft": "com.mojang.minecraftpe",
}
KEYCODES = {"ENTER": 66, "BACK": 4, "ESC": 4, "SPACE": 62, "TAB": 61, "UP": 19, "DOWN": 20, "LEFT": 21,
            "RIGHT": 22, "BACKSPACE": 67, "HOME": 3}
# Characters `adb shell input text` can carry after escaping for the device shell. '%' is excluded: the
# tool reads "%s" as a space, so a literal percent can't be typed unambiguously.
_TEXT_OK = re.compile(r"^[A-Za-z0-9 _\-.,:/@+=!?#~'\"()\[\]{}*&;<>|$^]*$")


def _default_run(cmd: Sequence[str], timeout: float = 15.0, binary: bool = False) -> Tuple[int, bytes]:
    kwargs: Dict[str, Any] = {}
    if os.name == "nt":
        kwargs["creationflags"] = 0x08000000            # CREATE_NO_WINDOW: no console flashes
    try:
        p = subprocess.run(list(cmd), capture_output=True, timeout=timeout, **kwargs)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc).encode()
    return p.returncode, p.stdout if p.returncode == 0 or binary else (p.stdout + p.stderr)


def find_adb(env: Optional[Dict[str, str]] = None, exists: Callable[[str], bool] = os.path.exists) -> str:
    env = os.environ if env is None else env
    for key in ("TOM_ADB", "ADB_PATH"):
        if env.get(key) and exists(env[key]):
            return env[key]
    found = shutil.which("adb")
    if found:
        return found
    return next((p for p in ADB_CANDIDATES if exists(p)), "")


def conf_ports(text: str) -> List[int]:
    """ADB ports named in bluestacks.conf. ⚠️ VERIFY: the exact key isn't documented by BlueStacks;
    this accepts any `...adb_port="NNNN"` line, which is the form reported by users."""
    ports = []
    for m in re.finditer(r"adb_port\s*=\s*\"?(\d{2,5})\"?", text or ""):
        port = int(m.group(1))
        if 1024 < port < 65536 and port not in ports:
            ports.append(port)
    return ports


def text_arg(text: str) -> Optional[str]:
    """`text` escaped for `adb shell input text`, or None when it can't be typed safely."""
    if not text or not _TEXT_OK.match(text):
        return None
    out = []
    for ch in text:
        if ch == " ":
            out.append("%s")
        elif ch.isalnum() or ch in "_-.,:/@+=":
            out.append(ch)
        else:
            out.append("\\" + ch)                       # shell metacharacter on the device: escape it
    return "".join(out)


def package_from_args(args: str) -> str:
    """The Android package in a BlueStacks shortcut's arguments ("--cmd launchApp --package com.x.y")."""
    m = re.search(r"--package\s+\"?([A-Za-z0-9_.]+)", args or "")
    return m.group(1) if m else ""


class Adb:
    def __init__(self, adb: str = "", serial: str = "", run: Optional[Runner] = None):
        self.adb = adb or find_adb()
        self.serial = serial
        self.run = run or _default_run

    def _cmd(self, *args: str) -> List[str]:
        base = [self.adb] + (["-s", self.serial] if self.serial else [])
        return base + list(args)

    def devices(self) -> List[str]:
        code, out = self.run([self.adb, "devices"], 10.0, False)
        if code != 0:
            return []
        found = []
        for line in out.decode(errors="replace").splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                found.append(parts[0])
        return found

    def connect(self, env: Optional[Dict[str, str]] = None,
                read_conf: Optional[Callable[[], str]] = None) -> Tuple[bool, str]:
        """Find and select a device. (ok, message)."""
        if not self.adb:
            return False, ("I couldn't find adb. Turn on BlueStacks → Settings → Advanced → Android Debug Bridge, "
                           "or set TOM_ADB to adb.exe.")
        env = os.environ if env is None else env
        wanted = env.get("BLUESTACKS_ADB", "").strip()
        tried: List[str] = []
        if wanted:
            tried.append(wanted)
        else:
            known = self.devices()
            if known:
                self.serial = known[0]
                return True, f"Using Android device {self.serial}."
            conf = (read_conf or _read_conf)()
            tried += [f"127.0.0.1:{p}" for p in conf_ports(conf)]
            tried += [f"127.0.0.1:{p}" for p in DEFAULT_PORTS if f"127.0.0.1:{p}" not in tried]
        for target in tried:
            self.run([self.adb, "connect", target], 8.0, False)
            if target in self.devices():
                self.serial = target
                return True, f"Connected to {target}."
        return False, ("BlueStacks didn't answer over ADB (tried " + ", ".join(tried[:4]) + "). Turn on "
                       "Settings → Advanced → Android Debug Bridge in BlueStacks, or set BLUESTACKS_ADB to the "
                       "address it shows (e.g. 127.0.0.1:5555).")

    def screencap(self):
        """The Android screen as a BGR array, or None."""
        code, png = self.run(self._cmd("exec-out", "screencap", "-p"), 15.0, True)
        if code != 0 or not png.startswith(b"\x89PNG"):
            return None
        try:
            import cv2
            import numpy as np
            return cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
        except Exception:
            return None

    def shell(self, *args: str, timeout: float = 15.0) -> bool:
        code, _ = self.run(self._cmd("shell", *args), timeout, False)
        return code == 0

    def tap(self, x: int, y: int) -> bool:
        return self.shell("input", "tap", str(int(x)), str(int(y)))

    def swipe(self, x1: int, y1: int, x2: int, y2: int, ms: int) -> bool:
        return self.shell("input", "swipe", str(int(x1)), str(int(y1)), str(int(x2)), str(int(y2)), str(int(ms)),
                          timeout=15.0 + ms / 1000.0)

    def text(self, text: str) -> bool:
        arg = text_arg(text)
        return arg is not None and self.shell("input", "text", arg)

    def key(self, name: str) -> bool:
        code = KEYCODES.get(name.upper())
        return code is not None and self.shell("input", "keyevent", str(code))

    def launch(self, package: str) -> bool:
        return self.shell("monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1")

    def foreground_package(self) -> str:
        code, out = self.run(self._cmd("shell", "dumpsys", "window"), 10.0, False)
        if code != 0:
            return ""
        m = re.search(r"mCurrentFocus=.*?\s([A-Za-z0-9_.]+)/", out.decode(errors="replace"))
        return m.group(1) if m else ""


def _read_conf() -> str:
    for path in CONF_CANDIDATES:
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                return fh.read()
        except OSError:
            continue
    return ""


class AdbBackend(brain.BrainBackend):
    """An Android screen as the brain's backend. Input never touches Windows' keyboard or mouse."""

    platform = "touch"

    def __init__(self, adb: Adb, package: str = "", read_lines=None):
        self.adb = adb
        self.package = package
        self.read_lines = read_lines if read_lines is not None else brain.ocr_reader()
        self._prev = None
        self.lost = 0

    def ready(self) -> bool:
        if not self.package:
            return True
        current = self.adb.foreground_package()
        if current and current != self.package:
            # the game went to the background (an ad, a dialog app, home): bring it back, never act elsewhere
            self.adb.launch(self.package)
            time.sleep(1.5)
            current = self.adb.foreground_package()
        return not current or current == self.package

    def observe(self) -> Optional[brain.Screen]:
        frame = self.adb.screencap()
        if frame is None:
            self.lost += 1
            return None
        screen = brain.screen_from_frame(frame, self.read_lines, self._prev)
        self._prev = frame
        return screen

    def _px(self, screen: brain.Screen, x: float, y: float) -> Tuple[int, int]:
        return int(x * screen.width), int(y * screen.height)

    def act(self, action: Dict[str, Any], screen: brain.Screen) -> Tuple[bool, str]:
        t = action["type"]
        if t in ("click", "aim"):
            return self.adb.tap(*self._px(screen, action["x"], action["y"])), ""
        if t == "double_click":
            x, y = self._px(screen, action["x"], action["y"])
            ok = self.adb.tap(x, y)
            time.sleep(0.08)
            return ok and self.adb.tap(x, y), ""
        if t == "hold":
            x, y = self._px(screen, action["x"], action["y"])
            return self.adb.swipe(x, y, x, y, int(action["seconds"] * 1000)), ""
        if t == "swipe":
            x1, y1 = self._px(screen, action["x"], action["y"])
            x2, y2 = self._px(screen, action["x2"], action["y2"])
            return self.adb.swipe(x1, y1, x2, y2, int(action["seconds"] * 1000)), ""
        if t == "type":
            if text_arg(action["text"]) is None:
                return False, "that text has characters adb can't type (e.g. %, emoji)"
            return self.adb.text(action["text"]), ""
        if t == "key":
            return self.adb.key(action["key"]), ""
        return False, f"{t} isn't available on a touch screen"


def connect_backend(game_name: str = "", package: str = "", env: Optional[Dict[str, str]] = None,
                    adb: Optional[Adb] = None) -> Tuple[Optional[AdbBackend], str]:
    """(backend, message) for an Android game, launching its package when known."""
    adb = adb or Adb()
    ok, msg = adb.connect(env)
    if not ok:
        return None, msg
    pkg = package or next((p for k, p in KNOWN_PACKAGES.items() if k in (game_name or "").lower()), "")
    if pkg and adb.foreground_package() != pkg:
        adb.launch(pkg)
        time.sleep(4.0)
    return AdbBackend(adb, pkg), msg
