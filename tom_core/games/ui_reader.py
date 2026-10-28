"""Read a game's interface: the buttons on screen and what they say.

Game menus defeat plain OCR — blocky pixel fonts with drop shadows on textured backgrounds (Tesseract
reads Minecraft's main menu as noise and misses "Play" entirely). Two things fix it:

1. Find the buttons first. A button is a large, near-uniform rectangle (low local variance), so the
   connected flat regions of the frame are the buttons and text fields; the textured world behind them
   is not flat and drops out.
2. Read each button on its own: cut it out, keep only the pixels much lighter (or darker) than its fill —
   the label — and OCR that single line. On Minecraft's menu this reads Play / Settings / Realms at
   64-91 % confidence where whole-screen OCR found nothing.

Labels come back with OCR's slips ("Dressing Foom"), so `find()` matches fuzzily.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np

Box = Tuple[int, int, int, int]


@dataclass
class Item:
    text: str
    conf: float
    box: Box                         # x, y, w, h in frame pixels
    kind: str = "button"             # "button" (a flat panel) | "text" (a free line of text)
    fill: int = 0                    # median grey of the panel (dark panels are usually text fields)

    @property
    def center(self) -> Tuple[int, int]:
        x, y, w, h = self.box
        return x + w // 2, y + h // 2


def _ocr_line(img, psm: int = 7) -> Tuple[str, float]:
    import pytesseract
    from tom_core.screen_control import find_tesseract
    pytesseract.pytesseract.tesseract_cmd = find_tesseract()
    d = pytesseract.image_to_data(img, config=f"--oem 1 --psm {psm}", output_type=pytesseract.Output.DICT)
    words = [(d["text"][i], float(d["conf"][i])) for i in range(len(d["text"]))
             if d["text"][i].strip() and float(d["conf"][i]) >= 0]
    if not words:
        return "", 0.0
    return " ".join(w for w, _ in words), sum(c for _, c in words) / len(words)


def panels(frame_bgr, min_w: float = 0.05, min_h: float = 0.03, max_h: float = 0.18) -> List[Tuple[Box, int]]:
    """Flat rectangles (buttons, fields, tabs) as (box, fill grey), largest first."""
    import cv2
    g = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    gf = g.astype(np.float32)
    mean = cv2.blur(gf, (9, 9))
    var = cv2.blur(gf * gf, (9, 9)) - mean * mean
    flat = (var < 40).astype(np.uint8) * 255
    n, _labels, stats, _c = cv2.connectedComponentsWithStats(flat, connectivity=4)
    H, W = g.shape
    out = []
    for x, y, w, h, area in stats[1:]:
        if w > W * min_w and H * min_h < h < H * max_h and w / max(1, h) > 1.3 and area / float(w * h) > 0.5:
            out.append(((int(x), int(y), int(w), int(h)), int(np.median(g[y:y + h, x:x + w]))))
    return sorted(out, key=lambda p: -p[0][2] * p[0][3])


def read_panel(gray, box: Box, fill: int, ocr: Callable = _ocr_line) -> Tuple[str, float]:
    """The label on one panel: try light-on-dark and dark-on-light, keep the more confident read."""
    import cv2
    x, y, w, h = box
    crop = gray[y:y + h, x:x + w]
    best = ("", 0.0)
    for light in (True, False):
        mask = crop > min(250, fill + 50) if light else crop < max(5, fill - 50)
        if mask.mean() < 0.003:                       # nothing that colour on this panel
            continue
        img = np.where(mask, 0, 255).astype(np.uint8)
        if h > 80:
            img = cv2.resize(img, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        img = cv2.copyMakeBorder(img, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=255)
        text, conf = ocr(img)
        text = re.sub(r"^[^A-Za-z0-9]+|[^A-Za-z0-9!?)]+$", "", text)
        if text and conf > best[1]:
            best = (text, conf)
    return best


def _words(img, scale: float, min_conf: float = 50) -> List[Tuple[str, float, Box]]:
    import pytesseract
    from tom_core.screen_control import find_tesseract
    pytesseract.pytesseract.tesseract_cmd = find_tesseract()
    d = pytesseract.image_to_data(img, config="--oem 1 --psm 11", output_type=pytesseract.Output.DICT)
    out = []
    for i, t in enumerate(d["text"]):
        try:
            conf = float(d["conf"][i])
        except (TypeError, ValueError):
            continue
        if t.strip() and conf >= min_conf:
            out.append((t, conf, (int(d["left"][i] / scale), int(d["top"][i] / scale),
                                  int(d["width"][i] / scale), int(d["height"][i] / scale))))
    return out


def text_lines(frame_bgr, words_fn: Optional[Callable] = None, light: int = 190) -> List[Item]:
    """Plain light text on a flat dark background (side menus, labels: "Cheats", "World name") —
    the pixels brighter than `light` become black-on-white, read as sparse text, grouped into lines."""
    import cv2
    g = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    img = np.where(g > light, 0, 255).astype(np.uint8)
    img = cv2.resize(img, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    words = sorted((words_fn or _words)(img, 0.5), key=lambda w: (w[2][1], w[2][0]))
    lines: List[List[Tuple[str, float, Box]]] = []
    for w in words:
        x, y, ww, hh = w[2]
        for line in lines:
            lx, ly, lw, lh = line[-1][2]
            if abs(ly - y) < max(10, 0.6 * lh) and 0 <= x - (lx + lw) < 2.5 * max(lh, hh):
                line.append(w)
                break
        else:
            lines.append([w])
    items = []
    for line in lines:
        xs = [b[0] for _, _, b in line] + [b[0] + b[2] for _, _, b in line]
        ys = [b[1] for _, _, b in line] + [b[1] + b[3] for _, _, b in line]
        text = " ".join(t for t, _, _ in line)
        conf = sum(c for _, c, _ in line) / len(line)
        items.append(Item(text, conf, (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)), "text"))
    return items


def _inside(inner: Box, outer: Box) -> bool:
    cx, cy = inner[0] + inner[2] / 2, inner[1] + inner[3] / 2
    return outer[0] <= cx <= outer[0] + outer[2] and outer[1] <= cy <= outer[1] + outer[3]


def read(frame_bgr, ocr: Callable = _ocr_line, max_panels: int = 24, lines: bool = True) -> List[Item]:
    """Every readable button/field on screen plus free text lines, top to bottom."""
    import cv2
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    items = []
    for box, fill in panels(frame_bgr)[:max_panels]:
        text, conf = read_panel(gray, box, fill, ocr)
        if text and conf >= 30:
            items.append(Item(text, conf, box, "button", fill))
    if lines:
        try:
            extra = text_lines(frame_bgr)
        except Exception:
            extra = []
        items += [ln for ln in extra if not any(_inside(ln.box, b.box) for b in items)]
    return sorted(items, key=lambda it: (it.box[1], it.box[0]))


def _norm(s: str) -> str:
    s = s.lower()
    for a, b in (("0", "o"), ("1", "l"), ("5", "s"), ("|", "l"), ("f", "r")):   # pixel-font slips: Foom→room
        s = s.replace(a, b)
    return re.sub(r"[^a-z ]+", "", s).strip()


def score(label: str, target: str) -> float:
    a, b = _norm(label), _norm(target)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if b in a.split() or (len(b) > 3 and b in a):
        return 0.92
    return difflib.SequenceMatcher(None, a, b).ratio()


def find(items: Sequence[Item], *targets: str, threshold: float = 0.72) -> Optional[Item]:
    """The item best matching any of `targets` ("Create New", "Create new world" …)."""
    best, best_s = None, threshold
    for it in items:
        for t in targets:
            s = score(it.text, t)
            if s > best_s:
                best, best_s = it, s
    return best


def labels(items: Sequence[Item]) -> List[str]:
    return [it.text for it in items]
