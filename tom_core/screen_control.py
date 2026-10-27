"""Screen control the way a person does it: look at the screen, read it (Tesseract OCR), find what to click,
click or type, then look again to check it worked. No app APIs.

    sc = ScreenControl()
    sc.read()                      -> lines of text on screen with their boxes
    sc.find("Send")                -> where "Send" is (best match), or None
    sc.click_text("Send")          -> click it (policy-gated, like every mouse action)
    sc.type_text("hello ₹ world")  -> types it (Unicode through the clipboard)
    sc.wait_for("Message sent")    -> poll until it appears, or time out

Every click and keypress goes through tools.hardware_control, whose methods pass the policy engine
(emergency stop, audit log). Coordinates are physical pixels: pyautogui makes the process DPI-aware, so a
screenshot and the mouse agree (measured 2560x1600 on the owner's laptop, 2026-10-27).
"""
from __future__ import annotations

import difflib
import os
import re
import shutil
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

Box = Tuple[int, int, int, int]                      # left, top, width, height (screen pixels)


def _dpi_aware() -> None:
    """Physical pixels everywhere. Without this, a window rectangle read before pyautogui was imported came
    back in scaled coordinates, so TOM read the wrong part of the screen and missed Gmail's Send button
    (live check 2026-10-27)."""
    if os.name != "nt":
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)          # per-monitor aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


_dpi_aware()


def find_tesseract() -> str:
    """The tesseract executable: TESSERACT_CMD, PATH, or the standard install folders; "" if none."""
    for cand in (os.environ.get("TESSERACT_CMD", "").strip().strip('"'), shutil.which("tesseract") or "",
                 r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                 r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Tesseract-OCR", "tesseract.exe")):
        if cand and os.path.isfile(cand):
            return cand
    return ""


@dataclass
class Word:
    text: str
    conf: float
    box: Box


@dataclass
class Line:
    words: List[Word] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def box(self) -> Box:
        return _union([w.box for w in self.words])


@dataclass
class Match:
    text: str
    box: Box
    score: float
    line: str

    @property
    def center(self) -> Tuple[int, int]:
        x, y, w, h = self.box
        return x + w // 2, y + h // 2


def _union(boxes: List[Box]) -> Box:
    x1 = min(b[0] for b in boxes)
    y1 = min(b[1] for b in boxes)
    x2 = max(b[0] + b[2] for b in boxes)
    y2 = max(b[1] + b[3] for b in boxes)
    return x1, y1, x2 - x1, y2 - y1


def _norm(s: str) -> str:
    return re.sub(r"[^\w@.+-]+", " ", (s or "").lower()).strip()


class ScreenControl:
    def __init__(self, hardware=None, grab: Optional[Callable] = None, ocr: Optional[Callable] = None,
                 scale: float = 2.0):
        self._hardware = hardware
        self._grab = grab                       # tests inject a fake screenshot / OCR
        self._ocr = ocr
        self.scale = scale                      # UI text is small: upscaling 2x roughly halves OCR misses
        self.cmd = find_tesseract()

    # ── seeing ────────────────────────────────────────────────────────────
    def available(self) -> Tuple[bool, str]:
        if self._ocr is not None:
            return True, ""
        try:
            import pytesseract  # noqa: F401
        except ImportError:
            return False, "pytesseract is not installed (pip install pytesseract)"
        if not self.cmd:
            return False, ("Tesseract OCR is not installed — install it (winget install UB-Mannheim.TesseractOCR) "
                           "or set TESSERACT_CMD to tesseract.exe")
        return True, ""

    def screenshot(self, region: Optional[Box] = None):
        if self._grab is not None:
            return self._grab(region)
        import pyautogui
        return pyautogui.screenshot(region=region) if region else pyautogui.screenshot()

    def read(self, region: Optional[Box] = None) -> List[Line]:
        """Text lines on screen (or in `region`) with screen-pixel boxes."""
        img = self.screenshot(region)
        ox, oy = (region[0], region[1]) if region else (0, 0)
        if self._ocr is not None:
            words = self._ocr(img)                                  # [(text, conf, (x, y, w, h), line_key)]
        else:
            words = self._tesseract(img)
        lines: dict = {}
        for text, conf, (x, y, w, h), key in words:
            if text.strip() and conf >= 30:
                lines.setdefault(key, Line()).words.append(Word(text, conf, (x + ox, y + oy, w, h)))
        return sorted(lines.values(), key=lambda ln: (ln.box[1], ln.box[0]))

    def _tesseract(self, img) -> list:
        import pytesseract
        from PIL import ImageOps
        pytesseract.pytesseract.tesseract_cmd = self.cmd
        g = ImageOps.grayscale(img)
        if self.scale != 1:
            g = g.resize((int(g.width * self.scale), int(g.height * self.scale)))
        d = pytesseract.image_to_data(g, config="--oem 1 --psm 11", output_type=pytesseract.Output.DICT)
        s, out = self.scale, []
        for i, text in enumerate(d["text"]):
            try:
                conf = float(d["conf"][i])
            except (TypeError, ValueError):
                conf = -1
            box = (int(d["left"][i] / s), int(d["top"][i] / s), int(d["width"][i] / s), int(d["height"][i] / s))
            # psm 11 (sparse text) numbers every fragment as its own block — group words by row instead
            out.append((text, conf, box, None))
        return _rows(out)

    def text(self, region: Optional[Box] = None) -> str:
        return "\n".join(ln.text for ln in self.read(region))

    def find(self, target: str, region: Optional[Box] = None, lines: Optional[List[Line]] = None,
             min_score: float = 0.8) -> Optional[Match]:
        """Best on-screen match for `target` (a word or phrase). Exact phrase first, then fuzzy."""
        want = _norm(target).split()
        if not want:
            return None
        best: Optional[Match] = None
        for ln in (lines if lines is not None else self.read(region)):
            ws = [_norm(w.text) for w in ln.words]
            n = len(want)
            for i in range(0, max(1, len(ws) - n + 1)):
                got = ws[i:i + n]
                if not got:
                    continue
                score = difflib.SequenceMatcher(None, " ".join(want), " ".join(got)).ratio()
                if score >= min_score and (best is None or score > best.score):
                    best = Match(" ".join(w.text for w in ln.words[i:i + n]),
                                 _union([w.box for w in ln.words[i:i + n]]), score, ln.text)
        return best

    def find_all(self, target: str, region: Optional[Box] = None, min_score: float = 0.8) -> List[Match]:
        """Every place `target` appears (one best match per line), top to bottom."""
        out = []
        for ln in self.read(region):
            m = self.find(target, lines=[ln], min_score=min_score)
            if m:
                out.append(m)
        return out

    def wait_for(self, target: str, timeout: float = 10.0, region: Optional[Box] = None,
                 interval: float = 0.7) -> Optional[Match]:
        end = time.monotonic() + timeout
        while True:
            m = self.find(target, region)
            if m or time.monotonic() >= end:
                return m
            time.sleep(interval)

    # ── acting (policy-gated through tools.hardware_control) ─────────────────
    def _hw(self):
        if self._hardware is None:
            from tools.hardware_control import HardwareControl
            self._hardware = HardwareControl()
        return self._hardware

    def click_text(self, target: str, region: Optional[Box] = None, double: bool = False,
                   prefer: str = "best") -> dict:
        """Click `target`. prefer="lowest" picks the match nearest the bottom; prefer="button" only accepts a
        short standalone label (a button), never the same word inside a sentence — Gmail's body text said
        "clicked Send itself" and that word was clicked instead of the Send button (live check 2026-10-27)."""
        if prefer in ("lowest", "button"):
            found = self.find_all(target, region)
            if prefer == "button":
                found = [x for x in found if len(x.line.split()) <= 4]
            m = max(found, key=lambda x: x.box[1]) if found else None
        else:
            m = self.find(target, region)
        if m is None:
            return {"status": "error", "found": False, "message": f"I couldn't see '{target}' on the screen."}
        x, y = m.center
        hw = self._hw()
        r = hw.double_click(x, y) if double else hw.click(x, y)
        ok = r.get("status") == "success"
        return {"status": "success" if ok else r.get("status", "error"), "found": True, "at": (x, y),
                "matched": m.text, "score": round(m.score, 2),
                "message": f"Clicked '{m.text}' at {x},{y}." if ok else r.get("message", "Click refused.")}

    def type_text(self, text: str) -> dict:
        """Type `text` into the focused field. Anything beyond plain ASCII is pasted via the clipboard,
        because simulated keystrokes can't produce ₹, é, emoji or Indic scripts."""
        hw = self._hw()
        if text.isascii() and "\n" not in text:
            return hw.type_text(text, interval=0.01)
        r = hw.copy_to_clipboard(text)
        if r.get("status") != "success":
            return r
        return hw.hotkey("ctrl", "v")

    def press(self, *keys: str) -> dict:
        hw = self._hw()
        return hw.hotkey(*keys) if len(keys) > 1 else hw.press_key(keys[0])


def window_box(hwnd: int) -> Optional[Box]:
    """The window's rectangle on screen (physical pixels), or None."""
    if os.name != "nt" or not hwnd:
        return None
    import ctypes
    from ctypes import wintypes
    rect = wintypes.RECT()
    if not ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    x, y = max(rect.left, 0), max(rect.top, 0)
    return x, y, max(rect.right - x, 1), max(rect.bottom - y, 1)


def _rows(words: list) -> list:
    """Assign each OCR word to a text row: words whose vertical centres are within half a line height and
    that are horizontally close (< 3 character widths apart) belong to the same row segment."""
    items = sorted((w for w in words if w[0].strip()), key=lambda w: w[2][1] + w[2][3] / 2)
    bands: List[list] = []                                   # words on the same horizontal band
    for w in items:
        cy, h = w[2][1] + w[2][3] / 2, max(w[2][3], 1)
        if bands:
            ref = bands[-1]
            rcy = sum(x[2][1] + x[2][3] / 2 for x in ref) / len(ref)
            rh = max(max(x[2][3] for x in ref), 1)
            if abs(cy - rcy) <= max(h, rh) * 0.5:
                ref.append(w)
                continue
        bands.append([w])
    out, n = [], 0
    for band in bands:                                       # split a band where words are far apart
        band.sort(key=lambda w: w[2][0])
        seg = [band[0]]
        for w in band[1:]:
            prev = seg[-1]
            h = max(w[2][3], prev[2][3], 1)
            if w[2][0] - (prev[2][0] + prev[2][2]) > 3 * h:
                out += [(t, c, b, n) for (t, c, b, _k) in seg]
                n, seg = n + 1, []
            seg.append(w)
        out += [(t, c, b, n) for (t, c, b, _k) in seg]
        n += 1
    return out
