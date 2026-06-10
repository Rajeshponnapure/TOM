import asyncio
import json
import math
import os
import queue
import random
import subprocess
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from urllib.error import URLError
from urllib.request import Request, urlopen

try:
    import requests as http_requests
except ImportError:
    http_requests = None

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    from PIL import Image, ImageTk, ImageDraw
except Exception:
    Image = None
    ImageTk = None
    ImageDraw = None

_SET_APPID = None
if os.name == "nt":
    try:
        import ctypes
        def _set_app_user_model_id(appid: str):
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)
            except Exception:
                pass
        _SET_APPID = _set_app_user_model_id
    except Exception:
        _SET_APPID = None

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
from dotenv import load_dotenv
load_dotenv()

# ── New v3 tool imports ───────────────────────────────────────────────
try:
    from tools.data_analysis import DataAnalysisEngine
    _HAS_DATA_ANALYSIS = True
except ImportError:
    DataAnalysisEngine = None
    _HAS_DATA_ANALYSIS = False

try:
    from tools.file_analyzer import FileAnalyzer
    _HAS_FILE_ANALYZER = True
except ImportError:
    FileAnalyzer = None
    _HAS_FILE_ANALYZER = False

try:
    from tools.autonomous_agent import AutonomousAgent
    _HAS_AUTONOMOUS = True
except ImportError:
    AutonomousAgent = None
    _HAS_AUTONOMOUS = False

try:
    from tools.rag_memory import RAGMemory
    _HAS_RAG = True
except ImportError:
    _HAS_RAG = False

try:
    from tools.skill_manager import SkillManager
    _HAS_SKILLS = True
except ImportError:
    SkillManager = None
    _HAS_SKILLS = False

try:
    from tools.hardware_control import HardwareControl
    _HAS_HARDWARE = True
except ImportError:
    HardwareControl = None
    _HAS_HARDWARE = False

try:
    from tools.ml_engine import MLEngine
    _HAS_ML = True
except ImportError:
    MLEngine = None
    _HAS_ML = False

try:
    from tools.iot_engine import IoTEngine
    _HAS_IOT = True
except ImportError:
    IoTEngine = None
    _HAS_IOT = False

try:
    from tools.vlsi_engine import VLSIEngine
    _HAS_VLSI = True
except ImportError:
    VLSIEngine = None
    _HAS_VLSI = False

try:
    from tools.dependency_manager import DependencyManager
    _HAS_DEPS = True
except ImportError:
    DependencyManager = None
    _HAS_DEPS = False

try:
    from tools.news_agent import NewsAgent
    _HAS_NEWS = True
except ImportError:
    NewsAgent = None
    _HAS_NEWS = False

try:
    from tools.auto_scaler import AutoScaler
    _HAS_SCALER = True
except ImportError:
    AutoScaler = None
    _HAS_SCALER = False

try:
    from tools.voice_enhanced import VoiceEnhanced
    _HAS_VOICE_ENH = True
except ImportError:
    VoiceEnhanced = None
    _HAS_VOICE_ENH = False

try:
    from tools.game_dev import GameDevEngine
    _HAS_GAME_DEV = True
except ImportError:
    GameDevEngine = None
    _HAS_GAME_DEV = False

try:
    from tools.blender_control import BlenderControl
    _HAS_BLENDER = True
except ImportError:
    BlenderControl = None
    _HAS_BLENDER = False

try:
    from tools.auto_update import AutoUpdate
    _HAS_AUTO_UPDATE = True
except ImportError:
    AutoUpdate = None
    _HAS_AUTO_UPDATE = False

C = {
    "bg":       "#090b10",
    "surface":  "#11151d",
    "surface2": "#191f2a",
    "border":   "#293241",
    "border2":  "#354156",
    "text":     "#f4f7fb",
    "text2":    "#b5c0cf",
    "muted":    "#788597",
    "blue":     "#4f8cff",
    "cyan":     "#2cc8d8",
    "purple":   "#9b7cff",
    "emerald":  "#2ebd85",
    "amber":    "#e6a23a",
    "pink":     "#e96ba8",
    "red":      "#f05252",
    "indigo":   "#6f7cff",
    "orange":   "#f28c45",
}

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r, g, b):
    return "#{:02x}{:02x}{:02x}".format(max(0, min(255, int(r))), max(0, min(255, int(g))), max(0, min(255, int(b))))

def tint(color, factor):
    r, g, b = hex_to_rgb(color)
    return rgb_to_hex(r * factor, g * factor, b * factor)

def blend(c1, c2, t):
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    return rgb_to_hex(r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t)


# ── Futuristic Holographic Dashboard ──────────────────────────────────────────

class TomHoloDashboard:
    """
    Full-canvas animated holographic dashboard for TOM.

    Features:
    • Animated hexagonal grid background (scanline / hologram effect)
    • 6 glowing neural-network stat nodes in a ring with pulsing connections
    • Live animated stat counters (smooth number interpolation)
    • 3D-perspective bar chart with neon bars
    • Particle field streaming between nodes
    • Scrolling activity log with neon text
    • All at ~33ms / 30 fps via after()
    """

    NODE_LABELS = ["Messages", "Voice", "Docs", "Analysis", "Email", "Files"]
    NODE_COLORS = [C["blue"], C["cyan"], C["emerald"], C["amber"], C["orange"], C["purple"]]

    def __init__(self, canvas: tk.Canvas):
        self.cv   = canvas
        self.t    = 0.0
        self.w    = 1
        self.h    = 1

        # Stat values (display-smoothed)
        self._targets = [0.0] * 6
        self._current = [0.0] * 6

        # Node positions (computed on first draw)
        self._node_pos = []

        # Particles
        self._particles = []
        self._MAX_PART  = 60

        # Activity log lines
        self._log_lines: list = []
        self._log_scroll = 0.0

        # HEX grid cache
        self._hex_pts: list = []

        # Status string
        self.status_text  = "Initialising..."
        self.model_text   = ""
        self.memory_count = 0

        # Bar values for chart (separate from node values)
        self._bar_targets = [0.0] * 6
        self._bar_current = [0.0] * 6

        canvas.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        self.w = max(event.width,  300)
        self.h = max(event.height, 300)
        self._hex_pts = []        # invalidate hex cache
        self._node_pos = []

    # ── Public API ──────────────────────────────────────────────────────

    def push_stats(self, values: list, bar_values: list = None):
        """Update target stat values (list of 6 ints)."""
        for i, v in enumerate(values[:6]):
            self._targets[i] = float(v)
        if bar_values:
            for i, v in enumerate(bar_values[:6]):
                self._bar_targets[i] = float(v)
        else:
            self._bar_targets = list(self._targets)

    def push_log(self, line: str):
        self._log_lines.append(line)
        if len(self._log_lines) > 80:
            self._log_lines.pop(0)

    def set_status(self, text: str, model: str = "", memory: int = 0):
        self.status_text  = text
        self.model_text   = model
        self.memory_count = memory

    # ── Draw ────────────────────────────────────────────────────────────

    def draw(self):
        cv = self.cv
        cv.delete("all")
        w, h = self.w, self.h
        t = self.t

        # Smooth stat values
        for i in range(6):
            self._current[i] += (self._targets[i] - self._current[i]) * 0.06
            self._bar_current[i] += (self._bar_targets[i] - self._bar_current[i]) * 0.08

        # ── Background ─────────────────────────────────────────────────
        cv.create_rectangle(0, 0, w, h, fill=C["bg"], outline="")

        # Hex grid
        self._draw_hex_grid(cv, w, h, t)

        # Scanline sweep
        sweep_y = (h * 0.5 * (1 + math.sin(t * 0.4))) % h
        self._draw_scanline(cv, w, sweep_y)

        # ── Stat nodes ring ─────────────────────────────────────────────
        cx, cy = w * 0.28, h * 0.46
        ring_r  = min(w * 0.18, h * 0.28)
        self._draw_node_ring(cv, cx, cy, ring_r, t)

        # ── Central orb glow ────────────────────────────────────────────
        self._draw_central_glow(cv, cx, cy, t)

        # ── Particles ───────────────────────────────────────────────────
        self._update_particles(cx, cy, ring_r)
        self._draw_particles(cv)

        # ── Status + model bar (top right) ──────────────────────────────
        self._draw_status_bar(cv, w, h, t)

        # ── 3D bar chart (right half) ────────────────────────────────────
        self._draw_bar_chart(cv, w * 0.56, h * 0.08, w * 0.40, h * 0.52, t)

        # ── Activity log (bottom right) ──────────────────────────────────
        self._draw_activity_log(cv, w * 0.56, h * 0.63, w * 0.42, h * 0.34)

        # ── Legend below nodes ───────────────────────────────────────────
        self._draw_legend(cv, cx, cy + ring_r + 24)

        self.t += 0.033

    # ── Hex Grid ────────────────────────────────────────────────────────

    def _draw_hex_grid(self, cv, w, h, t):
        SIZE = 28
        color_base = "#0d1526"
        color_glow = "#112244"

        if not self._hex_pts:
            pts = []
            dx = SIZE * 1.732
            dy = SIZE * 1.5
            cols = int(w / dx) + 2
            rows = int(h / dy) + 2
            for row in range(-1, rows + 1):
                for col in range(-1, cols + 1):
                    x = col * dx + (SIZE * 0.866 if row % 2 else 0)
                    y = row * dy
                    pts.append((x, y))
            self._hex_pts = pts

        pulse = math.sin(t * 0.7) * 0.3 + 0.7
        for (hx, hy) in self._hex_pts:
            d = math.hypot(hx - w * 0.28, hy - h * 0.46)
            intensity = max(0.0, 1.0 - d / (h * 0.55)) * pulse
            if intensity < 0.04:
                col = color_base
            else:
                col = blend(color_base, color_glow, intensity * 0.8)
            hex_pts = []
            for angle_deg in range(0, 360, 60):
                a = math.radians(angle_deg)
                hex_pts.extend([hx + SIZE * 0.85 * math.cos(a),
                                 hy + SIZE * 0.85 * math.sin(a)])
            cv.create_polygon(hex_pts, outline=col, fill="", width=1)

    def _draw_scanline(self, cv, w, y):
        for i in range(4):
            alpha = 0.08 - i * 0.02
            if alpha <= 0:
                continue
            yy = y + i * 3
            col = blend(C["bg"], C["cyan"], alpha)
            cv.create_line(0, yy, w, yy, fill=col, width=1)

    # ── Node Ring ───────────────────────────────────────────────────────

    def _draw_node_ring(self, cv, cx, cy, r, t):
        n   = 6
        pos = []
        for i in range(n):
            angle = math.pi * 2 * i / n - math.pi / 2 + t * 0.05
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            pos.append((x, y))
        self._node_pos = pos

        # Connection lines
        for i in range(n):
            for j in range(i + 1, n):
                x1, y1 = pos[i]
                x2, y2 = pos[j]
                pulse   = (math.sin(t * 1.5 + i * 0.8 + j * 0.5) + 1) / 2
                alpha   = 0.06 + pulse * 0.18
                col     = blend(C["bg"], C["blue"], alpha)
                cv.create_line(x1, y1, x2, y2, fill=col, width=1)

        # Node circles
        for i, ((x, y), label, color) in enumerate(zip(pos, self.NODE_LABELS, self.NODE_COLORS)):
            val   = int(self._current[i])
            pulse = (math.sin(t * 2.0 + i * 1.05) + 1) / 2
            R     = 22 + pulse * 5

            # Outer glow rings
            for ring in range(3, 0, -1):
                gr   = R + ring * 6
                alph = 0.12 - ring * 0.03
                gcol = blend(C["bg"], color, alph)
                cv.create_oval(x - gr, y - gr, x + gr, y + gr, outline=gcol, fill="", width=1)

            # Main circle
            cv.create_oval(x - R, y - R, x + R, y + R, outline=color, fill="#080c14", width=2)

            # Value text inside
            cv.create_text(x, y - 3, text=str(val), fill=color,
                           font=("Segoe UI", 9, "bold"), anchor="center")
            cv.create_text(x, y + 9, text=label[:4], fill=C["muted"],
                           font=("Segoe UI", 6), anchor="center")

    def _draw_central_glow(self, cv, cx, cy, t):
        pulse = (math.sin(t * 1.8) + 1) / 2
        for ring in range(5, 0, -1):
            r    = 8 + ring * 4 + pulse * 4
            alph = 0.25 - ring * 0.04
            col  = blend(C["bg"], C["cyan"], alph)
            cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill=col, outline="")
        cv.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill=C["cyan"], outline="")
        cv.create_text(cx, cy + 22, text="TOM", fill=C["cyan"],
                       font=("Segoe UI", 8, "bold"), anchor="center")

    def _draw_legend(self, cv, cx, bottom_y):
        for i, (label, color) in enumerate(zip(self.NODE_LABELS, self.NODE_COLORS)):
            row = i // 3
            col = i % 3
            x   = cx - 70 + col * 52
            y   = bottom_y + row * 16
            cv.create_rectangle(x - 4, y - 4, x + 4, y + 4, fill=color, outline="")
            cv.create_text(x + 8, y, text=label[:3], fill=C["text2"],
                           font=("Segoe UI", 7), anchor="w")

    # ── Particles ───────────────────────────────────────────────────────

    def _update_particles(self, cx, cy, ring_r):
        if len(self._particles) < self._MAX_PART and random.random() < 0.4:
            src = random.choice(self._node_pos) if self._node_pos else (cx, cy)
            dst = random.choice(self._node_pos) if self._node_pos else (cx, cy)
            self._particles.append({
                "x": src[0], "y": src[1],
                "tx": dst[0], "ty": dst[1],
                "color": random.choice(self.NODE_COLORS),
                "life": random.uniform(0.4, 1.0),
                "age":  0.0,
                "speed": random.uniform(0.015, 0.04),
            })
        alive = []
        for p in self._particles:
            p["age"] += p["speed"]
            frac = min(p["age"] / p["life"], 1.0)
            p["x"] = p["x"] + (p["tx"] - p["x"]) * p["speed"] * 1.5
            p["y"] = p["y"] + (p["ty"] - p["y"]) * p["speed"] * 1.5
            if p["age"] < p["life"]:
                alive.append(p)
        self._particles = alive

    def _draw_particles(self, cv):
        for p in self._particles:
            alpha = 1.0 - p["age"] / p["life"]
            col   = blend(C["bg"], p["color"], alpha * 0.9)
            r     = 2.5 * alpha
            x, y  = p["x"], p["y"]
            cv.create_oval(x - r, y - r, x + r, y + r, fill=col, outline="")

    # ── Status Bar ──────────────────────────────────────────────────────

    def _draw_status_bar(self, cv, w, h, t):
        bx, by, bw, bh = w * 0.56, h * 0.01, w * 0.42, h * 0.06
        # Panel background
        cv.create_rectangle(bx, by, bx + bw, by + bh,
                             fill=C["surface"], outline=C["border"], width=1)
        pulse = (math.sin(t * 3.0) + 1) / 2
        dot_col = blend(C["emerald"], C["cyan"], pulse)
        cv.create_oval(bx + 10, by + bh/2 - 4, bx + 18, by + bh/2 + 4, fill=dot_col, outline="")

        cv.create_text(bx + 26, by + bh * 0.35, text=self.status_text,
                       fill=C["text"], font=("Segoe UI", 9, "bold"), anchor="w")
        model_str = self.model_text[:28] if self.model_text else ""
        mem_str   = f"  ▸  🧠 {self.memory_count:,} memories" if self.memory_count else ""
        cv.create_text(bx + 26, by + bh * 0.72, text=model_str + mem_str,
                       fill=C["muted"], font=("Segoe UI", 7), anchor="w")

    # ── 3D Bar Chart ─────────────────────────────────────────────────────

    def _draw_bar_chart(self, cv, left, top, width, height, t):
        # Panel
        cv.create_rectangle(left, top, left + width, top + height,
                             fill=C["surface"], outline=C["border"], width=1)
        cv.create_text(left + 12, top + 14, text="▶  LIVE STATS",
                       fill=C["cyan"], font=("Segoe UI", 8, "bold"), anchor="w")

        n   = 6
        pad = 18
        chart_left  = left + pad
        chart_right = left + width - pad
        chart_top   = top + 36
        chart_bot   = top + height - pad
        chart_h     = chart_bot - chart_top
        chart_w     = chart_right - chart_left

        max_val = max(1.0, max(self._bar_current))
        bar_w   = chart_w / n

        # Horizontal grid lines
        for step in range(5):
            gy = chart_bot - chart_h * step / 4
            cv.create_line(chart_left, gy, chart_right, gy,
                           fill=C["border"], dash=(3, 6))
            if step > 0:
                cv.create_text(chart_left - 4, gy,
                               text=str(int(max_val * step / 4)),
                               fill=C["muted"], font=("Segoe UI", 6), anchor="e")

        DEPTH = 6  # 3D depth offset

        for i, (val, label, color) in enumerate(
            zip(self._bar_current, self.NODE_LABELS, self.NODE_COLORS)
        ):
            bar_frac = val / max_val if max_val > 0 else 0
            pulse     = (math.sin(t * 2.0 + i * 1.1) + 1) / 2
            bar_h_px  = max(2, chart_h * bar_frac)

            bx = chart_left + i * bar_w + bar_w * 0.15
            bw = bar_w * 0.7
            by = chart_bot - bar_h_px

            # 3D top face
            cv.create_polygon(
                bx, by, bx + bw, by,
                bx + bw + DEPTH, by - DEPTH, bx + DEPTH, by - DEPTH,
                fill=blend(color, "#ffffff", 0.3), outline=""
            )
            # 3D right face
            cv.create_polygon(
                bx + bw, by, bx + bw, chart_bot,
                bx + bw + DEPTH, chart_bot - DEPTH, bx + bw + DEPTH, by - DEPTH,
                fill=blend(color, "#000000", 0.4), outline=""
            )
            # Front face (with glow pulse)
            fill_col = blend(color, "#ffffff", pulse * 0.15)
            cv.create_rectangle(bx, by, bx + bw, chart_bot,
                                fill=fill_col, outline=color, width=1)

            # Value label on top
            if val > 0:
                cv.create_text(bx + bw / 2, by - DEPTH - 6,
                               text=str(int(val)), fill=color,
                               font=("Segoe UI", 7, "bold"), anchor="center")

            # Label below x-axis
            cv.create_text(bx + bw / 2, chart_bot + 8, text=label[:3],
                           fill=C["text2"], font=("Segoe UI", 6), anchor="center")

    # ── Activity Log ─────────────────────────────────────────────────────

    def _draw_activity_log(self, cv, left, top, width, height):
        cv.create_rectangle(left, top, left + width, top + height,
                            fill=C["surface"], outline=C["border"], width=1)
        cv.create_text(left + 12, top + 14, text="◈  RECENT ACTIVITY",
                       fill=C["purple"], font=("Segoe UI", 8, "bold"), anchor="w")

        clip_top  = top + 28
        clip_bot  = top + height - 8
        log_to_show = self._log_lines[-16:]
        line_h    = 13
        y         = clip_bot - line_h

        for line in reversed(log_to_show):
            if y < clip_top:
                break
            col = C["cyan"] if line.startswith("►") else C["text2"]
            cv.create_text(left + 10, y, text=line[:52], fill=col,
                           font=("Segoe UI", 7), anchor="w")
            y -= line_h


# ── TomOrb ─────────────────────────────────────────────────────────────────────

class TomOrb:
    RING_DEFS = [
        {"r": 115, "tilt": math.radians(70), "color": C["blue"],   "speed":  0.030, "dots": 3, "phase": 0.00},
        {"r": 135, "tilt": math.radians(40), "color": C["purple"], "speed": -0.020, "dots": 2, "phase": 2.09},
        {"r": 150, "tilt": math.radians(20), "color": C["cyan"],   "speed":  0.025, "dots": 3, "phase": 4.19},
    ]
    N_PARTICLES = 40

    def __init__(self, canvas, cx, cy, tom_image=None):
        self.canvas = canvas
        self.cx = cx
        self.cy = cy
        self.base_R = 72
        self.t = 0.0
        self.pulse_t = 0.0
        self.status = "ready"
        self.arc_angle = 0.0
        self.arc_target = 270.0
        self.tom_image = tom_image
        self.ring_angles = [rd["phase"] for rd in self.RING_DEFS]
        self.particles = []
        for _ in range(self.N_PARTICLES):
            self.particles.append(self._new_particle(born=True))

    def _new_particle(self, born=False):
        angle = random.uniform(0, 2 * math.pi)
        dist  = random.uniform(self.base_R + 20, self.base_R + 110)
        color = random.choice([C["blue"], C["purple"], C["cyan"], C["emerald"]])
        life  = random.uniform(0.3, 1.0)
        age   = random.uniform(0, life) if born else 0.0
        speed = random.uniform(0.005, 0.018) * random.choice([-1, 1])
        size  = random.uniform(1.5, 3.5)
        return {"angle": angle, "dist": dist, "color": color, "life": life, "age": age, "speed": speed, "size": size}

    def draw(self):
        cv = self.canvas
        cv.delete("orb_anim")
        cx, cy = self.cx, self.cy
        R = self.base_R * (1.0 + 0.04 * math.sin(self.pulse_t))
        for i, (extra, alpha) in enumerate([(130, 0.06), (105, 0.09), (88, 0.14), (70, 0.20)]):
            r_h = R + extra - i * 10
            shade = blend(C["bg"], C["blue"], alpha)
            cv.create_oval(cx - r_h, cy - r_h, cx + r_h, cy + r_h, fill=shade, outline="", tags="orb_anim")
        for p in self.particles:
            p["age"] += 0.016
            p["angle"] += p["speed"]
            if p["age"] >= p["life"]:
                p.update(self._new_particle())
                continue
            alpha_p = 1.0 - (p["age"] / p["life"])
            px = cx + p["dist"] * math.cos(p["angle"])
            py = cy + p["dist"] * math.sin(p["angle"]) * 0.45
            r_p = p["size"] * alpha_p
            col = blend(p["color"], C["bg"], 1.0 - alpha_p * 0.8)
            if r_p > 0.5:
                cv.create_oval(px - r_p, py - r_p, px + r_p, py + r_p, fill=col, outline="", tags="orb_anim")
        ring_data = []
        for idx, rd in enumerate(self.RING_DEFS):
            self.ring_angles[idx] += rd["speed"]
            theta0 = self.ring_angles[idx]
            tilt = rd["tilt"]
            rx = rd["r"]
            ry = rd["r"] * abs(math.sin(tilt))
            dots = []
            for d in range(rd["dots"]):
                theta = theta0 + d * (2 * math.pi / rd["dots"])
                for trail_i, trail_offset in enumerate([0, -0.12, -0.24, -0.36]):
                    tt = theta + trail_offset
                    dx = cx + rx * math.cos(tt)
                    dy = cy + ry * math.sin(tt)
                    z  = math.sin(tt) * math.sin(tilt)
                    dot_r = (3.5 if trail_i == 0 else 2.5 - trail_i * 0.5) * (0.6 + 0.8 * abs(z))
                    bright = 0.4 + 0.6 * (0.5 + 0.5 * z)
                    bright_trail = bright * (1.0 - trail_i * 0.22)
                    col_dot = tint(rd["color"], bright_trail)
                    dots.append({"x": dx, "y": dy, "z": z, "r": dot_r, "color": col_dot, "trail": trail_i})
            ring_data.append({"rx": rx, "ry": ry, "color": rd["color"], "dots": dots})
        for rg in ring_data:
            rx, ry = rg["rx"], rg["ry"]
            ring_col = tint(rg["color"], 0.35)
            cv.create_oval(cx - rx, cy - ry, cx + rx, cy + ry, outline=ring_col, fill="", width=1, dash=(4, 6), tags="orb_anim")
        for rg in ring_data:
            for dot in rg["dots"]:
                if dot["z"] < 0:
                    r_d = dot["r"]
                    cv.create_oval(dot["x"] - r_d, dot["y"] - r_d, dot["x"] + r_d, dot["y"] + r_d, fill=dot["color"], outline="", tags="orb_anim")
        layers = [
            (R * 1.30, blend(C["bg"], "#0a1628", 0.5)),
            (R * 1.10, blend(C["bg"], "#0d1e38", 0.6)),
            (R * 0.95, "#0d1e3a"),
            (R * 0.80, "#112244"),
            (R * 0.65, "#153070"),
            (R * 0.48, "#1e40af"),
        ]
        for (lr, lc) in layers:
            cv.create_oval(cx - lr, cy - lr, cx + lr, cy + lr, fill=lc, outline="", tags="orb_anim")
        if self.tom_image is not None:
            cv.create_image(cx, cy, image=self.tom_image, tags="orb_anim")
        else:
            glow_col = blend(C["blue"], C["cyan"], 0.5 + 0.5 * math.sin(self.pulse_t * 0.7))
            cv.create_text(cx + 2, cy + 2, text="TOM", font=("Segoe UI", 22, "bold"), fill=tint(glow_col, 0.3), tags="orb_anim")
            cv.create_text(cx, cy, text="TOM", font=("Segoe UI", 22, "bold"), fill=glow_col, tags="orb_anim")
        rim_col = blend(C["blue"], C["cyan"], 0.4)
        cv.create_oval(cx - R, cy - R, cx + R, cy + R, outline=rim_col, fill="", width=1, tags="orb_anim")
        for rg in ring_data:
            for dot in rg["dots"]:
                if dot["z"] >= 0:
                    r_d = dot["r"]
                    cv.create_oval(dot["x"] - r_d, dot["y"] - r_d, dot["x"] + r_d, dot["y"] + r_d, fill=dot["color"], outline="", tags="orb_anim")
        hx = cx - R * 0.30
        hy = cy - R * 0.30
        cv.create_oval(hx - 12, hy - 8, hx + 12, hy + 8, fill="#ffffff", outline="", tags="orb_anim", stipple="gray25")
        cv.create_oval(hx - 6, hy - 4, hx + 6, hy + 4, fill="#ffffff", outline="", tags="orb_anim")
        arc_r = R + 22
        if self.status == "ready":
            arc_col = C["emerald"]
            self.arc_target = 270.0
        else:
            arc_col = C["amber"]
            self.arc_target = 180.0 + 90.0 * abs(math.sin(self.t * 0.04))
        self.arc_angle += (self.arc_target - self.arc_angle) * 0.06
        if self.arc_angle > 1.0:
            cv.create_arc(cx - arc_r, cy - arc_r, cx + arc_r, cy + arc_r, start=90, extent=-self.arc_angle, outline=arc_col, fill="", width=2, style="arc", tags="orb_anim")
            arc_end_rad = math.radians(90 - self.arc_angle)
            ax = cx + arc_r * math.cos(arc_end_rad)
            ay = cy - arc_r * math.sin(arc_end_rad)
            cv.create_oval(ax - 3, ay - 3, ax + 3, ay + 3, fill=arc_col, outline="", tags="orb_anim")
        self.t += 1
        self.pulse_t += 0.06


# ── Voice UI Window ───────────────────────────────────────────────────────────

class VoiceUIWindow:
    """
    Dedicated voice conversation window with 3D animated orb.
    Opens when user clicks the Voice button.
    Shows Tom's logo with reactive animations for listening/speaking/thinking states.
    """

    def __init__(self, parent: tk.Tk, desktop_app):
        self.parent = parent
        self.app = desktop_app
        self.window = tk.Toplevel(parent)
        self.window.title("TOM — Voice Conversation")
        self.window.geometry("520x700")
        self.window.minsize(400, 600)
        self.window.configure(bg=C["bg"])

        if _SET_APPID:
            try:
                _SET_APPID("com.tom.voice")
            except Exception:
                pass

        self.window.transient(parent)
        self.window.grab_set()

        self._state = "idle"  # idle, listening, processing, speaking
        self._audio_level = 0.0
        self._running = True
        self._conversation_active = False

        self._particles = []
        self._pulse = 0.0
        self._wave_offset = 0.0
        self._orb_glow = 0.0

        self._build_ui()
        self._bind_shortcuts()

        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        self.window.after(50, self._animate)

    def _build_ui(self):
        w = self.window

        # Main canvas for 3D orb animation
        self.canvas = tk.Canvas(w, width=520, height=420, bg=C["bg"],
                                highlightthickness=0, bd=0)
        self.canvas.pack(fill="x", padx=0, pady=(20, 0))

        # Load Tom image for center of orb
        self._tom_image = None
        tom_path = self.app._find_resource(
            ("tom without bng.png", "tom with bng.png", "tom_icon.png")
        )
        if tom_path:
            try:
                from PIL import Image, ImageTk
                pil = Image.open(tom_path).convert("RGBA")
                pil = pil.resize((100, 100), Image.LANCZOS)
                mask = Image.new("L", (100, 100), 0)
                from PIL import ImageDraw
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, 100, 100), fill=255)
                pil.putalpha(mask)
                self._tom_image = ImageTk.PhotoImage(pil)
            except Exception:
                pass

        # Status label
        self.status_var = tk.StringVar(value="Press the button to start")
        self.status_label = tk.Label(w, textvariable=self.status_var,
                                     bg=C["bg"], fg=C["cyan"],
                                     font=("Segoe UI", 13, "bold"))
        self.status_label.pack(pady=(8, 0))

        # Sub-status
        self.sub_status_var = tk.StringVar(value="Voice conversation with TOM")
        tk.Label(w, textvariable=self.sub_status_var,
                 bg=C["bg"], fg=C["text2"], font=("Segoe UI", 9)).pack(pady=(2, 0))

        # Audio level meter
        level_frame = tk.Frame(w, bg=C["bg"])
        level_frame.pack(pady=(12, 0))
        tk.Label(level_frame, text="Audio Level", bg=C["bg"], fg=C["muted"],
                 font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.level_canvas = tk.Canvas(level_frame, width=300, height=16,
                                      bg=C["surface"], highlightthickness=0)
        self.level_canvas.pack()
        self._level_bar = self.level_canvas.create_rectangle(
            2, 2, 2, 14, fill=C["cyan"], outline=""
        )

        # Control buttons
        btn_frame = tk.Frame(w, bg=C["bg"])
        btn_frame.pack(pady=(20, 0))

        self.start_btn = tk.Button(btn_frame, text="\u25b6  Start Conversation",
                                   command=self._start_conversation,
                                   bg=C["blue"], fg="#ffffff",
                                   activebackground="#2563eb",
                                   activeforeground="#ffffff",
                                   relief="flat", bd=0,
                                   padx=24, pady=10,
                                   font=("Segoe UI", 11, "bold"), cursor="hand2")
        self.start_btn.pack(side="left", padx=(0, 10))

        self.stop_btn = tk.Button(btn_frame, text="\u25a0  Stop",
                                  command=self._stop_conversation,
                                  bg=C["surface2"], fg=C["red"],
                                  activebackground=C["border2"],
                                  activeforeground=C["red"],
                                  relief="flat", bd=0,
                                  padx=20, pady=10,
                                  font=("Segoe UI", 11, "bold"),
                                  cursor="hand2", state="disabled")
        self.stop_btn.pack(side="left")

        # Close button
        tk.Button(w, text="Close Window", command=self._on_close,
                  bg=C["surface2"], fg=C["text2"],
                  activebackground=C["border2"], activeforeground=C["text"],
                  relief="flat", bd=0, padx=16, pady=8,
                  font=("Segoe UI", 9), cursor="hand2").pack(pady=(14, 0))

        # Conversation transcript area
        tk.Label(w, text="Conversation", bg=C["bg"], fg=C["muted"],
                 font=("Segoe UI", 7, "bold")).pack(anchor="w", padx=30, pady=(14, 0))

        transcript_frame = tk.Frame(w, bg=C["surface"], padx=12, pady=12)
        transcript_frame.pack(fill="both", expand=True, padx=30, pady=(4, 20))

        self.transcript_text = tk.Text(transcript_frame, bg=C["surface2"],
                                       fg=C["text2"], insertbackground=C["text"],
                                       relief="flat", bd=0,
                                       font=("Segoe UI", 9),
                                       wrap="word", state="disabled",
                                       height=6)
        self.transcript_text.pack(fill="both", expand=True)

        scroll = tk.Scrollbar(transcript_frame, orient="vertical",
                              command=self.transcript_text.yview)
        scroll.pack(side="right", fill="y")
        self.transcript_text.configure(yscrollcommand=scroll.set)

    def _bind_shortcuts(self):
        self.window.bind("<Escape>", lambda e: self._on_close())
        self.window.bind("<Return>", lambda e: self._start_conversation()
                         if not self._conversation_active else None)

    def _animate(self):
        if not self._running:
            return
        cv = self.canvas
        cv.delete("all")
        w = cv.winfo_width() or 520
        h = cv.winfo_height() or 420
        cx, cy = w // 2, h // 2
        self._pulse += 0.05
        self._wave_offset += 0.03

        # Background scanlines
        for i in range(0, h, 6):
            alpha = 0.02 + 0.02 * math.sin(i * 0.1 + self._pulse)
            col = blend(C["bg"], C["blue"], alpha)
            cv.create_line(0, i, w, i, fill=col, width=1)

        # Outer glow rings (expand based on state)
        base_r = 80
        if self._state == "listening":
            glow_size = 8 + 4 * math.sin(self._pulse * 2)
            ring_count = 8
        elif self._state == "speaking":
            glow_size = 12 + 8 * math.sin(self._pulse * 3)
            ring_count = 10
        elif self._state == "processing":
            glow_size = 5 + 3 * math.sin(self._pulse * 1.5)
            ring_count = 6
        else:
            glow_size = 4 + 2 * math.sin(self._pulse * 0.5)
            ring_count = 4

        for ring in range(ring_count, 0, -1):
            r = base_r + ring * 8 + glow_size * math.sin(self._pulse + ring * 0.5)
            alpha = 0.25 - ring * 0.02
            col = blend(C["bg"], self._state_color(), alpha)
            cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill=col, outline="")

        # Particles orbiting (density varies by state)
        particle_count = {
            "idle": 25, "listening": 50, "processing": 35, "speaking": 45
        }.get(self._state, 25)

        for _ in range(len(self._particles), particle_count):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(base_r + 10, base_r + 80)
            self._particles.append({
                "angle": angle, "dist": dist,
                "speed": random.uniform(0.005, 0.02) * random.choice([-1, 1]),
                "size": random.uniform(1.5, 4.0),
                "life": random.uniform(0.5, 1.5),
                "age": random.uniform(0, 0.5),
                "color": random.choice([C["blue"], C["cyan"], C["purple"], C["emerald"]]),
            })

        self._particles = [p for p in self._particles if p["age"] < p["life"]]
        for p in self._particles:
            p["age"] += 0.02
            p["angle"] += p["speed"]
            alpha = 1.0 - (p["age"] / p["life"])
            px = cx + p["dist"] * math.cos(p["angle"])
            py = cy + p["dist"] * math.sin(p["angle"]) * 0.5
            pr = p["size"] * alpha
            col = blend(p["color"], C["bg"], 1.0 - alpha * 0.7)
            if pr > 0.5:
                cv.create_oval(px - pr, py - pr, px + pr, py + pr, fill=col, outline="")

        # Central orb layers
        orb_r = base_r + 6 * math.sin(self._pulse * 0.7)
        layers = [
            (orb_r * 1.5, blend(C["bg"], "#0a1628", 0.3)),
            (orb_r * 1.3, blend(C["bg"], "#0d1e38", 0.4)),
            (orb_r * 1.1, "#0d1e3a"),
            (orb_r * 0.9, "#112244"),
            (orb_r * 0.7, "#153070"),
            (orb_r * 0.5, "#1e40af"),
        ]
        for lr, lc in layers:
            cv.create_oval(cx - lr, cy - lr, cx + lr, cy + lr, fill=lc, outline="")

        # Tom image at center
        if self._tom_image is not None:
            cv.create_image(cx, cy, image=self._tom_image)
        else:
            glow_col = blend(C["blue"], C["cyan"],
                             0.5 + 0.5 * math.sin(self._pulse * 0.7))
            cv.create_text(cx, cy, text="TOM", fill=glow_col,
                           font=("Segoe UI", 20, "bold"))

        # Orb rim glow
        rim_col = blend(self._state_color(), C["cyan"], 0.3)
        cv.create_oval(cx - orb_r, cy - orb_r, cx + orb_r, cy + orb_r,
                       outline=rim_col, fill="", width=2)

        # Wave animation when speaking
        if self._state in ("speaking", "listening"):
            wave_amp = 20 if self._state == "speaking" else 10
            wave_y = cy + orb_r + 30
            points = []
            for x in range(0, w, 4):
                y = wave_y + wave_amp * math.sin(x * 0.05 + self._wave_offset * 3)
                points.extend([x, y])
            if len(points) >= 4:
                cv.create_line(*points, fill=C["cyan"], width=2, smooth=True)

        # Update audio level bar
        self._update_level_bar()

        self.window.after(33, self._animate)

    def _state_color(self) -> str:
        return {
            "idle": C["blue"],
            "listening": C["cyan"],
            "processing": C["amber"],
            "speaking": C["emerald"],
        }.get(self._state, C["blue"])

    def _update_level_bar(self):
        w = self.level_canvas.winfo_width() or 300
        bar_w = max(2, w - 4)
        fill_w = max(2, bar_w * min(1.0, self._audio_level * 3))
        try:
            color = C["emerald"] if self._audio_level < 0.3 else (
                C["amber"] if self._audio_level < 0.6 else C["red"]
            )
            self.level_canvas.coords(self._level_bar, 2, 2, 2 + fill_w, 14)
            self.level_canvas.itemconfig(self._level_bar, fill=color)
        except Exception:
            pass

    def _start_conversation(self):
        if self._conversation_active:
            return
        if not self.app.voice:
            self._append_transcript("System", "Voice tools not available.")
            return
        if not self.app.agent_ready:
            self._append_transcript("System", "TOM is still initializing...")
            return

        self._conversation_active = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._set_state("listening")

        def _voice_loop():
            try:
                voice = self.app.voice
                voice.on_audio_level = self._on_audio_level
                voice.on_state_change = self._on_voice_state

                greeting = "Hey! I'm TOM. What can I help you with?"
                self._enqueue(lambda: self._append_transcript("TOM", greeting))
                self._enqueue(lambda: self._set_state("speaking"))
                voice.speak(greeting)
                self._enqueue(lambda: self._set_state("listening"))

                consecutive_timeouts = 0

                while self._conversation_active:
                    try:
                        result = voice.listen_neural(timeout=7)
                    except Exception as e:
                        err_msg = f"Listen error: {e}"
                        self._enqueue(lambda m=err_msg: self._append_transcript(
                            "System", m))
                        time.sleep(0.5)
                        continue

                    if result.get("status") == "timeout":
                        consecutive_timeouts += 1
                        if consecutive_timeouts >= 4:
                            self._enqueue(lambda: self._set_state("idle"))
                            consecutive_timeouts = 0
                        continue

                    if result.get("status") != "success" or not result.get("text"):
                        continue

                    consecutive_timeouts = 0
                    heard = result["text"].strip()
                    if not heard:
                        continue

                    self._enqueue(lambda t=heard: self._append_transcript("You", t))

                    lower = heard.lower().strip()
                    if lower in ("stop", "exit", "quit", "goodbye", "bye",
                                 "stop listening", "thanks bye", "that's all"):
                        farewell = "Alright, talk to you later!"
                        self._enqueue(lambda: self._append_transcript("TOM", farewell))
                        self._enqueue(lambda: self._set_state("speaking"))
                        voice.speak(farewell)
                        break

                    self._enqueue(lambda: self._set_state("processing"))

                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            self.app.agent.execute_task(heard), self.app._loop)
                        response = future.result(timeout=120)
                        if isinstance(response, dict):
                            response = response.get("message", str(response))
                        response = str(response).strip()
                    except Exception as e:
                        response = f"Sorry, I hit an error: {e}"

                    if not response:
                        response = "I didn't have a good answer for that."

                    self._enqueue(lambda r=response: self._append_transcript("TOM", r))
                    self._enqueue(lambda: self._set_state("speaking"))
                    voice.speak(response[:500])
                    self._enqueue(lambda: self._set_state("listening"))

            except Exception as e:
                err_msg = f"Error: {e}"
                self._enqueue(lambda m=err_msg: self._append_transcript("System", m))
            finally:
                self._enqueue(self._on_conversation_end)

        threading.Thread(target=_voice_loop, daemon=True).start()

    def _stop_conversation(self):
        self._conversation_active = False
        if self.app.voice:
            self.app.voice.stop_conversation_mode()
        self._set_state("idle")

    def _on_conversation_end(self):
        self._conversation_active = False
        self._set_state("idle")
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_var.set("Conversation ended")
        self.sub_status_var.set("Press Start to begin again")

    def _set_state(self, state: str):
        self._state = state
        labels = {
            "idle": "Ready",
            "listening": "Listening...",
            "processing": "Thinking...",
            "speaking": "Speaking...",
        }
        self.status_var.set(labels.get(state, state))
        if state == "listening":
            self.sub_status_var.set("I'm all ears — speak naturally")
        elif state == "processing":
            self.sub_status_var.set("Processing your request...")
        elif state == "speaking":
            self.sub_status_var.set("TOM is responding...")
        else:
            self.sub_status_var.set("Voice conversation with TOM")

    def _on_audio_level(self, level: float):
        self._audio_level = level

    def _on_voice_state(self, state: str, text: str):
        state_map = {"listening": "listening", "processing": "processing",
                     "speaking": "speaking", "idle": "idle", "error": "idle",
                     "ready": "listening"}
        new_state = state_map.get(state, "idle")
        self._enqueue(lambda s=new_state: self._set_state(s))
        if text:
            self._enqueue(lambda t=text: self._append_transcript("System", t))

    def _append_transcript(self, role: str, text: str):
        self.transcript_text.configure(state="normal")
        tag = role.lower()
        if tag == "tom":
            prefix = "\u25cf TOM: "
            fg = C["blue"]
        elif tag == "you":
            prefix = "\u25b6 You: "
            fg = C["cyan"]
        else:
            prefix = "\u2501 System: "
            fg = C["muted"]
        self.transcript_text.insert("end", prefix, "role")
        self.transcript_text.insert("end", text + "\n", "text")
        self.transcript_text.tag_config("role", foreground=fg,
                                        font=("Segoe UI", 9, "bold"))
        self.transcript_text.tag_config("text", foreground=C["text2"],
                                        font=("Segoe UI", 9))
        self.transcript_text.see("end")
        self.transcript_text.configure(state="disabled")

    def _enqueue(self, fn):
        self.parent.after_idle(fn)

    def _on_close(self):
        self._running = False
        self._conversation_active = False
        if self.app.voice:
            try:
                self.app.voice.stop_conversation_mode()
            except Exception:
                pass
        try:
            self.window.destroy()
        except Exception:
            pass


class TomDesktopApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("TOM — Professional AI Assistant")
        self.root.geometry("1420x880")
        self.root.minsize(1100, 720)
        self.root.configure(bg=C["bg"])

        if _SET_APPID:
            try:
                _SET_APPID("com.tom.desktop")
            except Exception:
                pass

        self._configure_window_icon()

        self.ui_queue = queue.Queue()
        self.agent = None
        self.agent_ready = False
        self.processing = False

        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._loop_thread.start()

        self.active_view = "dashboard"
        self.active_agent_key = "core"
        self.sidebar_visible = True
        self.voice_mode_enabled = False

        self.activity_counts = {"messages": 0, "voice": 0, "email": 0, "instagram": 0, "documents": 0, "analysis": 0}
        self.recent_events = []
        self.view_buttons = {}
        self.metric_vars = {}
        self._chart_bars_current = [0, 0, 0, 0, 0, 0, 0]

        self.last_user_message = ""
        self.last_response_message = ""
        self.last_experience_id = None
        self.last_agent_result = None
        self._seen_email_approval_keys = set()
        self._email_state_file = str(PROJECT_ROOT / "tom_logs" / "email_agent_state.json")

        self._status_phrases = ["Ready", "Thinking...", "Listening...", "Processing...", "Analyzing...", "Creating..."]
        self._status_idx = 0
        self._status_char_idx = 0
        self._status_direction = 1

        self.agent_profiles = {
            "core": {
                "label": "Core TOM",
                "dot": C["blue"],
                "description": "Full AI assistant: docs, analysis, email, voice, game dev, 3D/CGI, cybersecurity.",
                "prefix": "",
                "suggestion": "Ask me to do anything — create documents, analyze data, open apps, send emails, build games, create 3D models, or run security audits.",
            },
            "email": {
                "label": "Email Agent",
                "dot": C["cyan"],
                "description": "Summarize, rank, and draft replies for your inbox.",
                "prefix": "You are Email Agent mode. Summarize inbox messages, identify what matters, flag urgent items.",
                "suggestion": "Review my inbox, summarize the important emails, and draft replies.",
            },
            "instagram": {
                "label": "Instagram Agent",
                "dot": C["pink"],
                "description": "Run Instagram extraction, reporting, and AI-news workflows.",
                "prefix": "You are Instagram Agent mode. Use the Instagram workflow to inspect posts.",
                "suggestion": "Run the Instagram workflow and summarize any AI-related posts.",
            },
        }

        self.quick_actions = [
            {"icon": "\u270f", "label": "Word Doc",    "cmd": "Create a professional Word document about ",    "color": C["blue"]},
            {"icon": "\u229e", "label": "Excel",       "cmd": "Create an Excel spreadsheet for ",              "color": C["emerald"]},
            {"icon": "\u25ad", "label": "PowerPoint",  "cmd": "Create a professional PowerPoint about ",       "color": C["orange"]},
            {"icon": "\u22a0", "label": "PDF Report",  "cmd": "Create a professional PDF report about ",       "color": C["red"]},
            {"icon": "\u2709", "label": "Email",       "cmd": "Write an email to ",                            "color": C["cyan"]},
            {"icon": "\u2295", "label": "Web Search",  "cmd": "Search the web for ",                           "color": C["purple"]},
            {"icon": "\u25b3", "label": "Analyze",     "cmd": "Analyze data: ",                                "color": C["amber"]},
            {"icon": "\u2706", "label": "WhatsApp",    "cmd": "Send a WhatsApp message to ",                   "color": C["emerald"]},
            {"icon": "\u2699", "label": "Web Auto",    "cmd": "Open browser and verify web app on localhost: ","color": C["cyan"]},
            {"icon": "\u2605", "label": "Multi-Agent", "cmd": "Deploy multi-agent task: ",                     "color": C["purple"]},
            {"icon": "\u2691", "label": "Security",    "cmd": "Check website safety: ",                        "color": C["red"]},
            {"icon": "\u22a1", "label": "File Anal",   "cmd": "Analyze file: ",                                "color": C["emerald"]},
            {"icon": "\u25c8", "label": "Data Anal",   "cmd": "Run data analysis on: ",                        "color": C["pink"]},
            {"icon": "\u269b", "label": "Autonomous",  "cmd": "Execute autonomous task: ",                     "color": C["indigo"]},
            {"icon": "\u2328", "label": "Hardware",    "cmd": "Hardware control: ",                             "color": C["blue"]},
            {"icon": "\u25ce", "label": "Skill",       "cmd": "Load skill: ",                                   "color": C["amber"]},
            {"icon": "\u22b9", "label": "ML",          "cmd": "ML task (algorithm, X, y): ",                   "color": C["purple"]},
            {"icon": "\u25e6", "label": "IoT",         "cmd": "IoT task (board, components): ",                "color": C["cyan"]},
            {"icon": "\u22a3", "label": "VLSI",        "cmd": "VLSI task (design type, width): ",              "color": C["pink"]},
            {"icon": "\u2693", "label": "Env Setup",   "cmd": "Environment (venv, packages, 3.11): ",          "color": C["emerald"]},
            {"icon": "\u25ce", "label": "News",        "cmd": "News (daily briefing, tech, world): ",          "color": C["amber"]},
            {"icon": "\u266b", "label": "Voice+",      "cmd": "Voice+ (emotion, conversation): ",              "color": C["purple"]},
            {"icon": "\u25b6", "label": "Game Dev",    "cmd": "Game dev (pygame, unity, script): ",            "color": C["pink"]},
            {"icon": "\u25c7", "label": "Blender 3D",  "cmd": "Blender 3D (cube, sphere, terrain): ",          "color": C["orange"]},
            {"icon": "\u21bb", "label": "Auto-Update", "cmd": "Auto-update (check, pull, pip, full): ",        "color": C["emerald"]},
        ]

        self.voice = None
        self._voice_ui_window = None
        self.web_automation = None
        self.orchestrator = None
        self.data_analysis = None
        self.file_analyzer = None
        self.autonomous = None
        self.skills = None
        self.hardware = None
        self.ml_engine = None
        self.iot_engine = None
        self.vlsi_engine = None
        self.dep_manager = None
        self.news_agent = None
        self.scaler = None
        self.voice_enhanced = None
        self.game_dev = None
        self.blender = None
        self.auto_update = None

        self._build_layout()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(120, self._drain_ui_queue)
        self.root.after(3000, self._poll_email_agent_state)
        self.root.after(100, self._animate_orb)
        self.root.after(800, self._animate_header_status)
        self.root.after(1000, self._tick_clock)

        self._bind_keyboard_shortcuts()

        threading.Thread(target=self._startup, daemon=True).start()

    def _resource_dir(self):
        if getattr(sys, "frozen", False):
            return os.path.join(sys._MEIPASS, "resources")
        return os.path.join(os.path.dirname(__file__), "resources")

    def _find_resource(self, filenames):
        rdir = self._resource_dir()
        for fn in filenames:
            p = os.path.join(rdir, fn)
            if os.path.exists(p):
                return p
        for fn in filenames:
            p = str(PROJECT_ROOT / fn)
            if os.path.exists(p):
                return p
        return None

    def _load_tk_image(self, path, target_size):
        try:
            tw, th = target_size
            if Image and ImageTk:
                pil = Image.open(path).convert("RGBA")
                pil.thumbnail((tw, th), Image.LANCZOS)
                return ImageTk.PhotoImage(pil)
            return tk.PhotoImage(file=path)
        except Exception:
            return None

    def _make_circle_image(self, path, size):
        if not (Image and ImageTk and ImageDraw):
            return None
        try:
            img = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
            mask = Image.new("L", (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size, size), fill=255)
            img.putalpha(mask)
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    def _configure_window_icon(self):
        icon_png = self._find_resource(("tom_icon.png", "tom with bng.png", "tom without bng.png"))
        icon_ico = self._find_resource(("tom_icon.ico",))
        # On Windows use .ico first (native format, handles all sizes correctly)
        if os.name == "nt" and icon_ico:
            try:
                self.root.iconbitmap(default=icon_ico)
            except Exception:
                pass
        # Override with crisp PNG via PIL for the taskbar small icon
        if icon_png and Image and ImageTk:
            try:
                pil_img = Image.open(icon_png).convert("RGBA")
                # Resize to 64x64 for clean taskbar rendering
                pil_img = pil_img.resize((64, 64), Image.LANCZOS)
                img = ImageTk.PhotoImage(pil_img)
                self.root.iconphoto(True, img)
                self._window_icon = img
            except Exception:
                pass

    def _build_layout(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=0)
        self._build_header()
        self.body = tk.Frame(self.root, bg=C["bg"])
        self.body.grid(row=1, column=0, sticky="nswe")
        self.body.columnconfigure(1, weight=0)
        self.body.columnconfigure(2, weight=1)
        self.body.rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_orb_panel()
        self._build_content_area()
        self._build_statusbar()
        self._show_view("dashboard")
        self._refresh_dashboard()
        self._append_chat("meta", "TOM v2.0 — Gemma 4 engine. Initializing...")

    def _build_header(self):
        self.header = tk.Frame(self.root, bg="#0a0e1a", height=50)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_propagate(False)
        self.header.columnconfigure(1, weight=1)

        left = tk.Frame(self.header, bg="#0a0e1a")
        left.grid(row=0, column=0, sticky="w", padx=(8, 0))

        self.toggle_btn = tk.Button(left, text="\u2261", command=self._toggle_sidebar,
            bg="#0a0e1a", fg=C["text2"], activebackground=C["surface"],
            activeforeground=C["text"], relief="flat", font=("Segoe UI", 18),
            bd=0, padx=10, pady=0, cursor="hand2")
        self.toggle_btn.pack(side="left")

        tk.Label(left, text="TOM", bg="#0a0e1a", fg=C["text"],
            font=("Segoe UI", 13, "bold")).pack(side="left", padx=(4, 0))
        tk.Label(left, text="PROFESSIONAL", bg="#0a0e1a", fg=C["muted"],
            font=("Segoe UI", 8)).pack(side="left", padx=(8, 0))

        tk.Frame(left, bg=C["border"], width=1, height=24).pack(side="left", padx=12)

        center = tk.Frame(self.header, bg="#0a0e1a")
        center.grid(row=0, column=1, sticky="")
        self.header_typing_var = tk.StringVar(value="Ready")
        self.header_typing_label = tk.Label(center, textvariable=self.header_typing_var,
            bg="#0a0e1a", fg=C["blue"], font=("Segoe UI", 10))
        self.header_typing_label.pack()

        right = tk.Frame(self.header, bg="#0a0e1a")
        right.grid(row=0, column=2, sticky="e", padx=(0, 16))

        self.clock_var = tk.StringVar(value="00:00:00")
        tk.Label(right, textvariable=self.clock_var, bg="#0a0e1a", fg=C["text2"],
            font=("Consolas", 11)).pack(side="left", padx=(0, 12))

        # Model toggle dropdown — populated from Ollama /api/tags in _startup
        self._model_names = [os.environ.get("OLLAMA_MODEL", "gemma4:latest")]
        self.model_var = tk.StringVar(value=self._model_names[0])
        self.model_menu = tk.OptionMenu(right, self.model_var, *self._model_names,
                                        command=self._on_model_change)
        self.model_menu.config(
            bg="#0a0e1a", fg=C["muted"], activebackground=C["surface"],
            activeforeground=C["text"], relief="flat", bd=0,
            highlightthickness=0, font=("Segoe UI", 9), cursor="hand2",
            padx=6, pady=0)
        self.model_menu["menu"].config(
            bg=C["surface"], fg=C["text"],
            activebackground=C["blue"], activeforeground="#ffffff",
            font=("Segoe UI", 9))
        self.model_menu.pack(side="left", padx=(0, 10))

        self.status_dot_canvas = tk.Canvas(right, width=10, height=10, bg="#0a0e1a", highlightthickness=0)
        self.status_dot_canvas.pack(side="left", padx=(0, 4))
        self.status_dot = self.status_dot_canvas.create_oval(1, 1, 9, 9, fill=C["amber"], outline="")
        self.status_text_var = tk.StringVar(value="Starting")
        tk.Label(right, textvariable=self.status_text_var, bg="#0a0e1a", fg=C["text2"],
            font=("Segoe UI", 9)).pack(side="left")

        # Bottom accent line under header
        accent_bar = tk.Frame(self.root, bg=C["border"], height=1)
        accent_bar.grid(row=0, column=0, sticky="sew", pady=(49, 0))
        # Thin blue gradient accent on top of the border line
        tk.Frame(self.root, bg="#1a3a6b", height=1).grid(row=0, column=0, sticky="sew", pady=(48, 0))

    def _build_sidebar(self):
        self.sidebar_frame = tk.Frame(self.body, bg=C["bg"], width=236)
        self.sidebar_frame.grid(row=0, column=0, sticky="nswe")
        self.sidebar_frame.grid_propagate(False)
        self.sidebar_frame.columnconfigure(0, weight=1)
        self.sidebar_frame.rowconfigure(0, weight=1)
        self.sidebar_frame.rowconfigure(1, weight=0)
        tk.Frame(self.sidebar_frame, bg=C["border"], width=1).place(relx=1.0, rely=0, relheight=1.0, anchor="ne")

        # \u2500\u2500 Scrollable inner canvas \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        _sb_cv = tk.Canvas(self.sidebar_frame, bg=C["bg"], highlightthickness=0, bd=0)
        _sb_cv.grid(row=0, column=0, sticky="nswe")
        _sb_scr = tk.Scrollbar(self.sidebar_frame, orient="vertical", command=_sb_cv.yview,
                                bg=C["surface"], width=4, troughcolor=C["bg"], relief="flat", bd=0)
        _sb_scr.grid(row=0, column=1, sticky="ns")
        _sb_cv.configure(yscrollcommand=_sb_scr.set)

        sb = tk.Frame(_sb_cv, bg=C["bg"])
        _sb_win = _sb_cv.create_window((0, 0), window=sb, anchor="nw")

        def _sb_configure(_e):
            _sb_cv.configure(scrollregion=_sb_cv.bbox("all"))

        def _sb_cv_resize(_e):
            _sb_cv.itemconfig(_sb_win, width=max(1, _e.width - 4))

        sb.bind("<Configure>", _sb_configure)
        _sb_cv.bind("<Configure>", _sb_cv_resize)
        _sb_cv.bind("<MouseWheel>", lambda e: _sb_cv.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        # \u2500\u2500 Logo \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        logo_block = tk.Frame(sb, bg=C["bg"], pady=16, padx=16)
        logo_block.pack(fill="x")
        logo_path = self._find_resource(("tom_icon.png", "tom with bng.png", "tom without bng.png"))
        if logo_path:
            img = self._load_tk_image(logo_path, (44, 44))
            if img:
                self._sidebar_logo = img
                tk.Label(logo_block, image=img, bg=C["bg"]).pack(anchor="w")
        else:
            tk.Label(logo_block, text="\u25ce", bg=C["bg"], fg=C["blue"], font=("Segoe UI", 28)).pack(anchor="w")
        tk.Label(logo_block, text="TOM", bg=C["bg"], fg=C["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(6, 0))
        tk.Label(logo_block, text="Autonomous AI Assistant", bg=C["bg"], fg=C["text2"], font=("Segoe UI", 9)).pack(anchor="w")

        self._sidebar_divider(sb)

        # \u2500\u2500 Navigation \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        nav_wrap = tk.Frame(sb, bg=C["bg"], padx=12, pady=8)
        nav_wrap.pack(fill="x")
        tk.Label(nav_wrap, text="NAVIGATION", bg=C["bg"], fg=C["text2"], font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 6))
        nav_items = [
            ("dashboard", "Dashboard", "\u25a6"),
            ("chat", "Chat", "\u25a4"),
            ("system", "System", "\u25ce"),
            ("charts", "Charts", "\u25a7"),
            ("files", "Files", "\u25a5"),
            ("capabilities", "Capabilities", "\u25c8"),
            ("health", "Health", "\u2695"),
        ]
        for view_key, label, icon in nav_items:
            btn = self._make_nav_button(nav_wrap, icon + "  " + label, lambda k=view_key: self._show_view(k))
            btn.pack(fill="x", pady=2)
            self.view_buttons[view_key] = btn

        self._sidebar_divider(sb)

        # \u2500\u2500 Agents \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        agent_wrap = tk.Frame(sb, bg=C["bg"], padx=12, pady=8)
        agent_wrap.pack(fill="x")
        tk.Label(agent_wrap, text="AGENTS", bg=C["bg"], fg=C["text2"], font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 6))
        for key in ("core", "email", "instagram"):
            profile = self.agent_profiles[key]
            btn = self._make_agent_button(agent_wrap, "\u25cf", profile["dot"], profile["label"], lambda k=key: self._set_active_agent(k))
            btn.pack(fill="x", pady=2)

        self._sidebar_divider(sb)

        # \u2500\u2500 Actions \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        act_wrap = tk.Frame(sb, bg=C["bg"], padx=12, pady=8)
        act_wrap.pack(fill="x")
        tk.Label(act_wrap, text="ACTIONS", bg=C["bg"], fg=C["text2"], font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 6))

        self.voice_btn = tk.Button(act_wrap, text="  \u266a  Voice Mode", command=self._toggle_voice_mode,
            bg=C["surface2"], fg=C["text"], activebackground=C["blue"], activeforeground=C["text"],
            relief="flat", bd=0, padx=12, pady=9, anchor="w", font=("Segoe UI", 9, "bold"), cursor="hand2")
        self.voice_btn.pack(fill="x", pady=(0, 6))

        self.run_btn = tk.Button(act_wrap, text="  \u25b6  Run Agent", command=self._run_active_agent_action,
            bg=C["amber"], fg="#000000", activebackground="#d97706", activeforeground="#000000",
            relief="flat", bd=0, padx=12, pady=9, anchor="w", font=("Segoe UI", 9, "bold"), cursor="hand2")
        self.run_btn.pack(fill="x")

        v2_actions = [
            ("  \u2699  Web Auto",    self._handle_web_automation, C["cyan"]),
            ("  \u25c6  Auto-Debug",  self._handle_auto_debug,     C["orange"]),
            ("  \u2606  Multi-Agent", self._handle_multi_agent,    C["purple"]),
            ("  \u2714  Security",    self._handle_security_check, C["red"]),
            ("  \u25ce  System Check", self._run_system_verification, C["emerald"]),
        ]
        for text, cmd, color in v2_actions:
            btn = tk.Button(act_wrap, text=text, command=cmd,
                bg=C["surface2"], fg=color, activebackground=C["border2"], activeforeground=C["text"],
                relief="flat", bd=0, padx=12, pady=8, anchor="w", font=("Segoe UI", 9, "bold"), cursor="hand2")
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=C["border2"]))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=C["surface2"]))
            btn.pack(fill="x", pady=2)

        self._sidebar_divider(sb)

        # \u2500\u2500 Quick Create \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        quick_wrap = tk.Frame(sb, bg=C["bg"], padx=12, pady=8)
        quick_wrap.pack(fill="x")
        self._sidebar_section_label(quick_wrap, "QUICK CREATE", "⚡")
        for qa in self.quick_actions[:6]:
            col = qa["color"]
            btn = tk.Button(quick_wrap, text=f"  {qa['icon']}  {qa['label']}",
                command=lambda cmd=qa["cmd"]: self._quick_action(cmd),
                bg=C["surface2"], fg=col, activebackground=C["border2"], activeforeground=C["text"],
                relief="flat", bd=0, padx=12, pady=8, anchor="w", font=("Segoe UI", 9, "bold"), cursor="hand2")
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=C["border2"]))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=C["surface2"]))
            btn.pack(fill="x", pady=2)

        tk.Frame(sb, bg=C["bg"], height=8).pack()

        # \u2500\u2500 Pinned status card (outside scroll area) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        self.sidebar_card = tk.Frame(self.sidebar_frame, bg=C["surface"], padx=14, pady=12)
        self.sidebar_card.grid(row=1, column=0, columnspan=2, sticky="ew")
        tk.Frame(self.sidebar_card, bg=C["border"], height=1).pack(fill="x", pady=(0, 8))
        tk.Label(self.sidebar_card, text="ACTIVE", bg=C["surface"], fg=C["muted"], font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.sidebar_agent_var = tk.StringVar(value=self.agent_profiles[self.active_agent_key]["label"])
        tk.Label(self.sidebar_card, textvariable=self.sidebar_agent_var, bg=C["surface"], fg=C["text"],
            font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(3, 0))
        self.sidebar_desc_var = tk.StringVar(value=self.agent_profiles[self.active_agent_key]["description"])
        tk.Label(self.sidebar_card, textvariable=self.sidebar_desc_var, bg=C["surface"], fg=C["text2"],
            font=("Segoe UI", 8), wraplength=186, justify="left").pack(anchor="w", pady=(4, 0))

        self._sync_nav_styles()

    def _build_statusbar(self):
        bar = tk.Frame(self.root, bg="#05080f", height=24)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)
        tk.Frame(bar, bg=C["border"], height=1).pack(fill="x", side="top")

        left = tk.Frame(bar, bg="#05080f")
        left.pack(side="left", fill="y", padx=(10, 0))
        right = tk.Frame(bar, bg="#05080f")
        right.pack(side="right", fill="y", padx=(0, 12))

        self._sb_dot_cv = tk.Canvas(left, width=10, height=10, bg="#05080f", highlightthickness=0)
        self._sb_dot_cv.pack(side="left", pady=7)
        self._sb_dot = self._sb_dot_cv.create_oval(1, 1, 9, 9, fill=C["amber"], outline="")

        self._sb_status_var = tk.StringVar(value="Starting up...")
        tk.Label(left, textvariable=self._sb_status_var, bg="#05080f", fg=C["muted"],
                 font=("Segoe UI", 8)).pack(side="left", padx=(5, 0))

        tk.Label(right, text="TOM v2.0  ·  Autonomous AI", bg="#05080f", fg="#2d3f5c",
                 font=("Segoe UI", 8)).pack(side="right")
        self._sb_model_var = tk.StringVar(value="")
        tk.Label(right, textvariable=self._sb_model_var, bg="#05080f", fg=C["muted"],
                 font=("Segoe UI", 8)).pack(side="right", padx=(0, 10))

    def _update_statusbar(self, status: str, model: str = "", ready: bool = False):
        if hasattr(self, "_sb_status_var"):
            self._sb_status_var.set(status)
        if hasattr(self, "_sb_model_var") and model:
            self._sb_model_var.set(model)
        if hasattr(self, "_sb_dot_cv"):
            col = C["emerald"] if ready else C["amber"]
            self._sb_dot_cv.itemconfig(self._sb_dot, fill=col)

    def _sidebar_section_label(self, parent, text, icon="◆", color=None):
        row = tk.Frame(parent, bg=C["bg"])
        row.pack(fill="x", pady=(0, 6))
        c = color or C["text2"]
        tk.Label(row, text=icon, bg=C["bg"], fg=C["blue"], font=("Segoe UI", 7)).pack(side="left", padx=(0, 4))
        tk.Label(row, text=text, bg=C["bg"], fg=c, font=("Segoe UI", 8, "bold")).pack(side="left")

    def _sidebar_divider(self, parent):
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", padx=12, pady=4)

    def _make_nav_button(self, parent, text, command):
        btn = tk.Button(parent, text=text, command=command, bg=C["bg"], fg=C["text2"],
            activebackground=C["surface2"], activeforeground=C["text"], relief="flat", bd=0,
            padx=10, pady=9, anchor="w", font=("Segoe UI", 9), cursor="hand2")
        btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=C["surface2"], fg=C["text"]))
        btn.bind("<Leave>", lambda e, b=btn: self._restore_nav_btn(b))
        return btn

    def _restore_nav_btn(self, btn):
        is_active = any(b is btn and k == self.active_view for k, b in self.view_buttons.items())
        btn.configure(bg=C["surface2"] if is_active else C["bg"],
                      fg=C["blue"] if is_active else C["text2"])

    def _make_agent_button(self, parent, icon, dot_color, label, command):
        frame = tk.Frame(parent, bg=C["bg"], cursor="hand2")
        dot = tk.Label(frame, text=icon, bg=C["bg"], fg=dot_color, font=("Segoe UI", 8))
        dot.pack(side="left", padx=(10, 4))
        btn = tk.Button(frame, text=label, command=command, bg=C["bg"], fg=C["text2"],
            activebackground=C["surface2"], activeforeground=C["text"], relief="flat", bd=0,
            padx=4, pady=8, anchor="w", font=("Segoe UI", 9), cursor="hand2")
        btn.pack(side="left", fill="x", expand=True)
        frame.command = command
        frame.bind("<Button-1>", lambda e: command())
        frame._dot = dot
        frame._btn = btn
        return frame

    def _build_orb_panel(self):
        self.orb_panel = tk.Frame(self.body, bg=C["bg"], width=290)
        self.orb_panel.grid(row=0, column=1, sticky="ns")
        self.orb_panel.grid_propagate(False)
        self.orb_panel.columnconfigure(0, weight=1)
        tk.Frame(self.orb_panel, bg=C["border"], width=1).place(relx=1.0, rely=0, relheight=1.0, anchor="ne")

        tk.Label(self.orb_panel, text="CORE", bg=C["bg"], fg=C["muted"], font=("Segoe UI", 8, "bold")).pack(pady=(20, 0))
        self.orb_canvas = tk.Canvas(self.orb_panel, width=280, height=300, bg=C["bg"], highlightthickness=0)
        self.orb_canvas.pack(fill="x", pady=(4, 0))

        tom_path = self._find_resource(("tom without bng.png", "tom with bng.png", "tom_icon.png"))
        self._orb_tom_image = None
        if tom_path:
            self._orb_tom_image = self._make_circle_image(tom_path, 100)

        self.orb = TomOrb(canvas=self.orb_canvas, cx=140, cy=150, tom_image=self._orb_tom_image)

        label_frame = tk.Frame(self.orb_panel, bg=C["bg"])
        label_frame.pack(pady=(8, 0))
        tk.Label(label_frame, text="GEMMA 4 ENGINE", bg=C["bg"], fg=C["muted"], font=("Segoe UI", 7, "bold")).pack()

        self._ready_dot_canvas = tk.Canvas(label_frame, width=80, height=18, bg=C["bg"], highlightthickness=0)
        self._ready_dot_canvas.pack()
        self._rdot = self._ready_dot_canvas.create_oval(4, 5, 12, 13, fill=C["amber"], outline="")
        self._ready_text = self._ready_dot_canvas.create_text(18, 9, anchor="w", text="STARTING",
            fill=C["muted"], font=("Segoe UI", 7, "bold"))
        self._rdot_pulse = 0.0
        self.root.after(400, self._pulse_ready_dot)

        cap_frame = tk.Frame(self.orb_panel, bg=C["bg"])
        cap_frame.pack(pady=(12, 0), padx=16, fill="x")
        capabilities = [
            ("\u25cf  Docs", C["blue"]), ("\u25cf  Analysis", C["emerald"]),
            ("\u25cf  Email", C["cyan"]), ("\u25cf  Voice", C["purple"]),
            ("\u25cf  Research", C["amber"]), ("\u25cf  Code", C["orange"]),
            ("\u25cf  Game Dev", C["pink"]), ("\u25cf  Blender 3D", C["orange"]),
            ("\u25cf  Security", C["red"]),
        ]
        row1 = tk.Frame(cap_frame, bg=C["bg"])
        row1.pack(fill="x")
        row2 = tk.Frame(cap_frame, bg=C["bg"])
        row2.pack(fill="x", pady=(4, 0))
        row3 = tk.Frame(cap_frame, bg=C["bg"])
        row3.pack(fill="x", pady=(4, 0))
        for i, (text, color) in enumerate(capabilities):
            parent = row1 if i < 3 else (row2 if i < 6 else row3)
            tk.Label(parent, text=text, bg=C["bg"], fg=color, font=("Segoe UI", 7, "bold")).pack(side="left", padx=(0, 8))

    def _pulse_ready_dot(self):
        self._rdot_pulse += 0.12
        alpha = 0.55 + 0.45 * math.sin(self._rdot_pulse)
        if self.agent_ready:
            col = blend(C["emerald"], C["bg"], 1.0 - alpha)
        else:
            col = blend(C["amber"], C["bg"], 1.0 - alpha)
        try:
            self._ready_dot_canvas.itemconfig(self._rdot, fill=col)
        except Exception:
            pass
        self.root.after(80, self._pulse_ready_dot)

    def _build_content_area(self):
        self.content_frame = tk.Frame(self.body, bg=C["bg"])
        self.content_frame.grid(row=0, column=2, sticky="nswe")
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(0, weight=1)

        self.dashboard_frame = tk.Frame(self.content_frame, bg=C["bg"])
        self.charts_frame = tk.Frame(self.content_frame, bg=C["bg"])
        self.chat_frame = tk.Frame(self.content_frame, bg=C["bg"])
        self.system_frame = tk.Frame(self.content_frame, bg=C["bg"])
        self.files_frame = tk.Frame(self.content_frame, bg=C["bg"])
        self.capabilities_frame = tk.Frame(self.content_frame, bg=C["bg"])
        self.health_frame = tk.Frame(self.content_frame, bg=C["bg"])

        for frm in (self.dashboard_frame, self.chat_frame, self.system_frame, self.charts_frame,
                    self.files_frame, self.capabilities_frame, self.health_frame):
            frm.grid(row=0, column=0, sticky="nswe")

        self._build_dashboard_view(self.dashboard_frame)
        self._build_chat_view(self.chat_frame)
        self._build_system_view(self.system_frame)
        self._build_charts_view(self.charts_frame)
        self._build_files_view(self.files_frame)
        self._build_capabilities_view(self.capabilities_frame)
        self._build_health_view(self.health_frame)

    def _build_dashboard_view(self, parent):
        """Futuristic animated holographic dashboard — full canvas, 30fps."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        # Full-fill canvas — the TomHoloDashboard draws everything onto this
        self._holo_canvas = tk.Canvas(parent, bg=C["bg"], highlightthickness=0, bd=0)
        self._holo_canvas.grid(row=0, column=0, sticky="nswe")

        self._holo = TomHoloDashboard(self._holo_canvas)

        # Seed with current data
        self.metric_vars["messages"] = tk.StringVar(value="0")
        self.metric_vars["voice"]    = tk.StringVar(value="Off")
        self.metric_vars["agent"]    = tk.StringVar(value=self.agent_profiles[self.active_agent_key]["label"])
        self.metric_vars["focus"]    = tk.StringVar(value="Dashboard")
        self.metric_vars["docs"]     = tk.StringVar(value="0")
        self.metric_vars["analysis"] = tk.StringVar(value="0")

        # ── Dashboard text input bar ──────────────────────────────────
        dash_input_outer = tk.Frame(parent, bg=C["bg"])
        dash_input_outer.grid(row=1, column=0, sticky="ew", padx=20, pady=(10, 6))
        parent.rowconfigure(1, weight=0)

        dash_input_border = tk.Frame(dash_input_outer, bg=C["border2"], padx=2, pady=2)
        dash_input_border.pack(fill="x")

        dash_input_inner = tk.Frame(dash_input_border, bg=C["surface2"])
        dash_input_inner.pack(fill="x")
        dash_input_inner.columnconfigure(0, weight=1)

        self._dash_placeholder = "Ask TOM anything..."
        self.dash_input_var = tk.StringVar()
        self.dash_input_entry = tk.Entry(dash_input_inner, textvariable=self.dash_input_var,
            bg=C["surface2"], fg=C["muted"], insertbackground=C["blue"],
            relief="flat", bd=0, font=("Segoe UI", 12))
        self.dash_input_entry.grid(row=0, column=0, sticky="ew", padx=(16, 0), ipady=14)
        self.dash_input_entry.insert(0, self._dash_placeholder)
        self._dash_input_has_placeholder = True

        def _on_dash_focus_in(e):
            dash_input_border.configure(bg=C["blue"])
            if self._dash_input_has_placeholder:
                self.dash_input_entry.delete(0, "end")
                self.dash_input_entry.configure(fg=C["text"])
                self._dash_input_has_placeholder = False
        def _on_dash_focus_out(e):
            dash_input_border.configure(bg=C["border2"])
            if not self.dash_input_var.get().strip():
                self.dash_input_entry.insert(0, self._dash_placeholder)
                self.dash_input_entry.configure(fg=C["muted"])
                self._dash_input_has_placeholder = True

        self.dash_input_entry.bind("<FocusIn>", _on_dash_focus_in)
        self.dash_input_entry.bind("<FocusOut>", _on_dash_focus_out)
        self.dash_input_entry.bind("<Return>", lambda _: self._send_from_dashboard())

        dash_send_btn = tk.Button(dash_input_inner, text="Send  ▶",
            command=self._send_from_dashboard,
            bg=C["blue"], fg="#ffffff", activebackground="#2563eb", activeforeground="#ffffff",
            relief="flat", bd=0, padx=20, pady=12, font=("Segoe UI", 10, "bold"), cursor="hand2")
        dash_send_btn.grid(row=0, column=1, padx=(4, 2))

        dash_voice_btn = tk.Button(dash_input_inner, text="♫  Voice",
            command=self._open_voice_ui,
            bg=C["purple"], fg="#ffffff", activebackground="#7c3aed", activeforeground="#ffffff",
            relief="flat", bd=0, padx=16, pady=12, font=("Segoe UI", 10, "bold"), cursor="hand2")
        dash_voice_btn.grid(row=0, column=2, padx=(0, 2))

        # ── Quick-action buttons — 4-column grid ─────────────────────
        qa_outer = tk.Frame(parent, bg=C["bg"])
        qa_outer.grid(row=2, column=0, sticky="ew", pady=(0, 0))
        parent.rowconfigure(2, weight=0)

        qa_header = tk.Frame(qa_outer, bg=C["bg"])
        qa_header.pack(fill="x", padx=12, pady=(4, 2))
        tk.Frame(qa_header, bg=C["border"], height=1).pack(fill="x", side="top")
        qa_hdr_inner = tk.Frame(qa_header, bg=C["bg"])
        qa_hdr_inner.pack(fill="x", pady=(4, 0))
        tk.Label(qa_hdr_inner, text="⚡  QUICK ACTIONS", bg=C["bg"], fg=C["muted"],
                 font=("Segoe UI", 7, "bold")).pack(side="left")
        tk.Label(qa_hdr_inner, text=f"{len(self.quick_actions)} actions", bg=C["bg"], fg="#2d3f5c",
                 font=("Segoe UI", 7)).pack(side="right")

        qa_strip = tk.Frame(qa_outer, bg=C["bg"])
        qa_strip.pack(fill="x", padx=8, pady=(2, 8))
        _QA_COLS = 4
        for i in range(_QA_COLS):
            qa_strip.columnconfigure(i, weight=1)

        for idx, qa in enumerate(self.quick_actions[:12]):
            col = qa["color"]
            btn = tk.Button(
                qa_strip, text=f"{qa['icon']}  {qa['label']}",
                bg=C["surface"], fg=col,
                activebackground=C["surface2"], activeforeground=col,
                relief="flat", bd=0, padx=6, pady=10,
                font=("Segoe UI", 9, "bold"), cursor="hand2",
                command=lambda cmd=qa["cmd"]: self._quick_action(cmd),
            )
            btn.bind("<Enter>", lambda e, b=btn, c=col: b.configure(bg=C["surface2"]))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=C["surface"]))
            btn.grid(row=idx // _QA_COLS, column=idx % _QA_COLS, sticky="ew", padx=3, pady=3)

        # Start animation loop
        self._holo_anim_running = True
        self._holo_anim_loop()

    def _metric_card(self, parent, col, title, var, accent):
        card = tk.Frame(parent, bg=C["surface"], padx=0, pady=0)
        card.grid(row=0, column=col, sticky="nswe", padx=(0 if col == 0 else 6, 0), pady=(0, 16))
        bar = tk.Frame(card, bg=accent, width=4)
        bar.pack(side="left", fill="y")
        inner = tk.Frame(card, bg=C["surface"], padx=12, pady=12)
        inner.pack(side="left", fill="both", expand=True)
        tk.Label(inner, text=title.upper(), bg=C["surface"], fg=C["muted"], font=("Segoe UI", 7, "bold")).pack(anchor="w")
        tk.Label(inner, textvariable=var, bg=C["surface"], fg=accent, font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(2, 0))

    def _build_charts_view(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        hdr = tk.Frame(parent, bg=C["bg"], padx=24, pady=16)
        hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(hdr, text="Charts & Activity", bg=C["bg"], fg=C["text"],
            font=("Segoe UI", 17, "bold")).pack(anchor="w")
        tk.Label(hdr, text="Usage breakdown across all capabilities.",
            bg=C["bg"], fg=C["text2"], font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))

        body = tk.Frame(parent, bg=C["bg"], padx=24, pady=0)
        body.grid(row=1, column=0, sticky="nswe")
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        chart_card = tk.Frame(body, bg=C["surface"], padx=16, pady=16)
        chart_card.grid(row=0, column=0, sticky="nswe", padx=(0, 8))
        chart_card.columnconfigure(0, weight=1)
        chart_card.rowconfigure(1, weight=1)
        tk.Label(chart_card, text="Usage Breakdown", bg=C["surface"], fg=C["text"],
            font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(chart_card, text="Messages, voice, documents, analysis, email, Instagram.",
            bg=C["surface"], fg=C["text2"], font=("Segoe UI", 8)).grid(row=0, column=0, sticky="sw", pady=(18, 0))

        self.chart_canvas = tk.Canvas(chart_card, bg=C["surface2"], highlightthickness=0)
        self.chart_canvas.grid(row=1, column=0, sticky="nswe", pady=(12, 0))
        self.chart_canvas.bind("<Configure>", lambda e: self._render_chart_canvas())

        legend_card = tk.Frame(body, bg=C["surface"], padx=16, pady=16)
        legend_card.grid(row=0, column=1, sticky="nswe", padx=(8, 0))
        legend_card.columnconfigure(0, weight=1)
        legend_card.rowconfigure(1, weight=1)
        tk.Label(legend_card, text="Stats", bg=C["surface"], fg=C["text"],
            font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w")

        self.chart_notes = tk.Listbox(legend_card, bg=C["surface2"], fg=C["text2"],
            selectbackground=C["border2"], selectforeground=C["text"], relief="flat",
            highlightthickness=0, font=("Segoe UI", 9), bd=0)
        self.chart_notes.grid(row=1, column=0, sticky="nswe", pady=(10, 0))

        refresh_btn = tk.Button(legend_card, text="\u21ba  Refresh", command=self._refresh_dashboard,
            bg=C["surface2"], fg=C["text2"], activebackground=C["border2"], activeforeground=C["text"],
            relief="flat", bd=0, padx=12, pady=8, font=("Segoe UI", 9), cursor="hand2")
        refresh_btn.grid(row=2, column=0, sticky="ew", pady=(10, 0))

    def _build_chat_view(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        hdr = tk.Frame(parent, bg=C["bg"], padx=24, pady=16)
        hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(hdr, text="Chat", bg=C["bg"], fg=C["text"],
            font=("Segoe UI", 17, "bold")).pack(anchor="w")
        self.chat_subtitle_var = tk.StringVar(value="Type or speak to TOM. Say anything.")
        tk.Label(hdr, textvariable=self.chat_subtitle_var, bg=C["bg"], fg=C["text2"],
            font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))

        msg_frame = tk.Frame(parent, bg=C["bg"], padx=24)
        msg_frame.grid(row=1, column=0, sticky="nswe")
        msg_frame.columnconfigure(0, weight=1)
        msg_frame.rowconfigure(0, weight=1)

        self.chat_canvas = tk.Canvas(msg_frame, bg=C["surface"], highlightthickness=0)
        self.chat_canvas.grid(row=0, column=0, sticky="nswe")
        chat_sb = tk.Scrollbar(msg_frame, orient="vertical", command=self.chat_canvas.yview,
            bg=C["surface"], troughcolor=C["surface2"])
        chat_sb.grid(row=0, column=1, sticky="ns")
        self.chat_canvas.configure(yscrollcommand=chat_sb.set)

        self.chat_inner = tk.Frame(self.chat_canvas, bg=C["surface"])
        self.chat_window = self.chat_canvas.create_window((0, 0), window=self.chat_inner, anchor="nw")
        self.chat_inner.bind("<Configure>", self._on_chat_configure)
        self.chat_canvas.bind("<Configure>", self._on_chat_canvas_resize)
        self.chat_canvas.bind("<MouseWheel>", self._on_chat_scroll)

        self._chat_bubbles = []

        # ── Attachment display area ──────────────────────────────────────
        self.attach_frame = tk.Frame(parent, bg=C["bg"])
        self.attach_frame.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 4))
        self.attach_frame.columnconfigure(0, weight=1)

        self._attachments = []
        self.attach_display = tk.Frame(self.attach_frame, bg=C["surface2"], height=40)
        self.attach_display.pack(fill="x")
        self.attach_label = tk.Label(self.attach_display, text="No attachments", bg=C["surface2"],
            fg=C["muted"], font=("Segoe UI", 8), anchor="w")
        self.attach_label.pack(side="left", padx=8, pady=6)
        self.attach_display.pack_forget()

        bottom_bar = tk.Frame(parent, bg=C["bg"], padx=24, pady=12)
        bottom_bar.grid(row=3, column=0, sticky="ew")
        bottom_bar.columnconfigure(0, weight=1)

        # ── Attachment buttons row ──────────────────────────────────────
        attach_row = tk.Frame(bottom_bar, bg=C["surface2"])
        attach_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        attach_row.columnconfigure(0, weight=1)

        self.attach_file_btn = tk.Button(attach_row, text="\U0001F4CE File", command=self._attach_file,
            bg=C["surface2"], fg=C["cyan"], activebackground=C["border2"], activeforeground=C["text"],
            relief="flat", bd=0, padx=10, pady=4, font=("Segoe UI", 8, "bold"), cursor="hand2")
        self.attach_file_btn.pack(side="left", padx=(4, 2))

        self.attach_image_btn = tk.Button(attach_row, text="\U0001F5BC Image", command=self._attach_image,
            bg=C["surface2"], fg=C["emerald"], activebackground=C["border2"], activeforeground=C["text"],
            relief="flat", bd=0, padx=10, pady=4, font=("Segoe UI", 8, "bold"), cursor="hand2")
        self.attach_image_btn.pack(side="left", padx=2)

        self.camera_btn = tk.Button(attach_row, text="\U0001F4F7 Camera", command=self._open_camera,
            bg=C["surface2"], fg=C["amber"], activebackground=C["border2"], activeforeground=C["text"],
            relief="flat", bd=0, padx=10, pady=4, font=("Segoe UI", 8, "bold"), cursor="hand2")
        self.camera_btn.pack(side="left", padx=2)

        self.link_btn = tk.Button(attach_row, text="\U0001F517 Link", command=self._attach_link,
            bg=C["surface2"], fg=C["purple"], activebackground=C["border2"], activeforeground=C["text"],
            relief="flat", bd=0, padx=10, pady=4, font=("Segoe UI", 8, "bold"), cursor="hand2")
        self.link_btn.pack(side="left", padx=(2, 4))

        self.clear_attach_btn = tk.Button(attach_row, text="\u2716 Clear", command=self._clear_attachments,
            bg=C["surface2"], fg=C["red"], activebackground=C["border2"], activeforeground=C["text"],
            relief="flat", bd=0, padx=10, pady=4, font=("Segoe UI", 8, "bold"), cursor="hand2")
        self.clear_attach_btn.pack(side="right", padx=(4, 4))

        # ── Input row ───────────────────────────────────────────────────
        # Bordered input container
        input_border = tk.Frame(bottom_bar, bg=C["border2"], pady=2, padx=2)
        input_border.grid(row=1, column=0, sticky="ew")
        input_border.columnconfigure(0, weight=1)

        input_row = tk.Frame(input_border, bg=C["surface2"])
        input_row.grid(row=0, column=0, sticky="ew")
        input_row.columnconfigure(0, weight=1)

        self._input_placeholder = "Type a message to TOM..."
        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(input_row, textvariable=self.input_var, bg=C["surface2"],
            fg=C["muted"], insertbackground=C["blue"], relief="flat", bd=0, font=("Segoe UI", 12))
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=(14, 0), ipady=14)
        self.input_entry.insert(0, self._input_placeholder)
        self._input_has_placeholder = True

        def _on_input_focus_in(e):
            input_border.configure(bg=C["blue"])
            if self._input_has_placeholder:
                self.input_entry.delete(0, "end")
                self.input_entry.configure(fg=C["text"])
                self._input_has_placeholder = False
        def _on_input_focus_out(e):
            input_border.configure(bg=C["border2"])
            if not self.input_var.get().strip():
                self.input_entry.insert(0, self._input_placeholder)
                self.input_entry.configure(fg=C["muted"])
                self._input_has_placeholder = True
        self.input_entry.bind("<FocusIn>",  _on_input_focus_in)
        self.input_entry.bind("<FocusOut>", _on_input_focus_out)
        self.input_entry.bind("<Return>", lambda _: self.send_message())

        # Voice button - opens dedicated voice conversation UI
        self.voice_ui_btn = tk.Button(input_row, text="\u266b  Voice", command=self._open_voice_ui,
            bg=C["purple"], fg="#ffffff", activebackground="#7c3aed", activeforeground="#ffffff",
            relief="flat", bd=0, padx=14, pady=8, font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.voice_ui_btn.grid(row=0, column=1)

        self.mic_btn = tk.Button(input_row, text="\u266a", command=self._on_mic_click,
            bg=C["surface2"], fg=C["text2"], activebackground=C["surface"], activeforeground=C["blue"],
            relief="flat", bd=0, padx=14, pady=8, font=("Segoe UI", 13), cursor="hand2")
        self.mic_btn.grid(row=0, column=2)

        self.send_btn = tk.Button(input_row, text="Send  \u25b6", command=self.send_message,
            bg=C["blue"], fg="#ffffff", activebackground="#2563eb", activeforeground="#ffffff",
            relief="flat", bd=0, padx=18, pady=8, font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.send_btn.grid(row=0, column=3, padx=(0, 0))

        fb_row = tk.Frame(bottom_bar, bg=C["bg"])
        fb_row.grid(row=2, column=0, sticky="ew", pady=(6, 0))

        tk.Label(fb_row, text="Feedback:", bg=C["bg"], fg=C["muted"], font=("Segoe UI", 8)).pack(side="left", padx=(0, 8))

        self.reward_btn = tk.Button(fb_row, text="\u2713  Reward", command=self.reward_response,
            bg=C["surface2"], fg=C["emerald"], activebackground=C["surface"], relief="flat",
            bd=0, padx=10, pady=4, font=("Segoe UI", 8), cursor="hand2", state="disabled")
        self.reward_btn.pack(side="left", padx=(0, 6))

        self.penalty_btn = tk.Button(fb_row, text="\u2717  Penalty", command=self.penalize_and_revise,
            bg=C["surface2"], fg=C["red"], activebackground=C["surface"], relief="flat",
            bd=0, padx=10, pady=4, font=("Segoe UI", 8), cursor="hand2", state="disabled")
        self.penalty_btn.pack(side="left", padx=(0, 8))

        self.feedback_var = tk.StringVar()
        self.feedback_entry = tk.Entry(fb_row, textvariable=self.feedback_var, bg=C["surface2"],
            fg=C["text2"], insertbackground=C["text"], relief="flat", bd=0, font=("Segoe UI", 8))
        self.feedback_entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 0))
        self.feedback_entry.insert(0, "Tell TOM how to improve...")
        self.feedback_entry.bind("<FocusIn>", lambda e: self.feedback_entry.delete(0, "end") if self.feedback_entry.get() == "Tell TOM how to improve..." else None)

    def _on_chat_configure(self, event):
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))

    def _on_chat_canvas_resize(self, event):
        self.chat_canvas.itemconfig(self.chat_window, width=event.width)

    def _on_chat_scroll(self, event):
        self.chat_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _send_from_dashboard(self):
        text = self.dash_input_var.get().strip()
        if not text or (hasattr(self, '_dash_input_has_placeholder') and self._dash_input_has_placeholder):
            return
        self.dash_input_var.set("")
        self.dash_input_entry.configure(fg=C["muted"])
        self.dash_input_entry.insert(0, self._dash_placeholder)
        self._dash_input_has_placeholder = True
        self.input_var.set(text)
        if hasattr(self, '_input_has_placeholder'):
            self.input_entry.delete(0, "end")
            self.input_entry.insert(0, text)
            self.input_entry.configure(fg=C["text"])
            self._input_has_placeholder = False
        self._show_view("chat")
        self.send_message()

    def _copy_to_clipboard(self, text: str, btn: tk.Button):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
        except Exception:
            return
        original_text = btn.cget("text")
        original_fg = btn.cget("fg")
        btn.configure(text="Copied!", fg=C["emerald"])
        self.root.after(1200, lambda: btn.configure(text=original_text, fg=original_fg))

    def _append_chat_image(self, role: str, image_path: str, caption: str = ""):
        """Render an image thumbnail in the chat, like Claude desktop does."""
        ts = time.strftime("%H:%M")
        bubble = tk.Frame(self.chat_inner, bg=C["surface"])
        bubble.pack(fill="x", padx=16, pady=4, anchor="w")

        wrapper = tk.Frame(bubble, bg=C["surface"])
        wrapper.pack(anchor="e" if role == "user" else "w")
        msg_bg = "#1e3a5f" if role == "user" else C["surface2"]
        msg_frame = tk.Frame(wrapper, bg=msg_bg, padx=10, pady=8)
        msg_frame.pack(anchor="e" if role == "user" else "w")

        # Caption text above image
        if caption:
            tk.Label(msg_frame, text=caption, bg=msg_bg, fg=C["text"],
                     font=("Segoe UI", 11), wraplength=400, justify="left").pack(anchor="w", pady=(0, 6))

        # Image thumbnail
        try:
            from PIL import Image as PILImg, ImageTk as PILImageTk
            pil_img = PILImg.open(image_path).convert("RGB")
            max_w, max_h = 320, 240
            ratio = min(max_w / pil_img.width, max_h / pil_img.height, 1.0)
            new_size = (int(pil_img.width * ratio), int(pil_img.height * ratio))
            pil_img = pil_img.resize(new_size, PILImg.LANCZOS)
            tk_img = PILImageTk.PhotoImage(pil_img)

            img_label = tk.Label(msg_frame, image=tk_img, bg=msg_bg, cursor="hand2")
            img_label.image = tk_img
            img_label.pack(anchor="w", pady=(0, 4))
            img_label.bind("<Button-1>", lambda e, p=image_path: os.startfile(p))
        except Exception:
            tk.Label(msg_frame, text=f"[Image: {os.path.basename(image_path)}]",
                     bg=msg_bg, fg=C["cyan"], font=("Segoe UI", 10)).pack(anchor="w")

        # File name + size label
        try:
            size = os.path.getsize(image_path)
            size_str = f"{size/1024:.1f} KB" if size > 1024 else f"{size} B"
            tk.Label(msg_frame, text=f"{os.path.basename(image_path)}  ({size_str})",
                     bg=msg_bg, fg=C["muted"], font=("Segoe UI", 8)).pack(anchor="w")
        except Exception:
            pass

        # Timestamp
        footer = tk.Frame(wrapper, bg=C["surface"])
        footer.pack(anchor="e" if role == "user" else "w", pady=(2, 0))
        tk.Label(footer, text=ts, bg=C["surface"], fg=C["muted"],
                 font=("Segoe UI", 7)).pack(side="right")

        self._chat_bubbles.append(bubble)
        self.chat_inner.update_idletasks()
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))
        self.chat_canvas.yview_moveto(1.0)

    def _append_chat(self, role: str, text: str):
        ts = time.strftime("%H:%M")
        bubble = tk.Frame(self.chat_inner, bg=C["surface"])
        bubble.pack(fill="x", padx=16, pady=4, anchor="w")

        if role == "user":
            wrapper = tk.Frame(bubble, bg=C["surface"])
            wrapper.pack(anchor="e")
            msg_frame = tk.Frame(wrapper, bg="#1e3a5f", padx=14, pady=10)
            msg_frame.pack(anchor="e")
            tk.Label(msg_frame, text=text, bg="#1e3a5f", fg=C["text"],
                font=("Segoe UI", 12), wraplength=460, justify="left").pack(anchor="w")
            footer = tk.Frame(wrapper, bg=C["surface"])
            footer.pack(anchor="e", pady=(2, 0))
            copy_btn = tk.Button(footer, text="Copy", bg=C["surface"], fg=C["muted"],
                activebackground=C["surface2"], activeforeground=C["text"], relief="flat",
                bd=0, padx=6, pady=0, font=("Segoe UI", 7), cursor="hand2")
            copy_btn.configure(command=lambda t=text, b=copy_btn: self._copy_to_clipboard(t, b))
            copy_btn.pack(side="right")
            tk.Label(footer, text=ts, bg=C["surface"], fg=C["muted"], font=("Segoe UI", 7)).pack(side="right", padx=(0, 6))

        elif role == "assistant":
            wrapper = tk.Frame(bubble, bg=C["surface"])
            wrapper.pack(anchor="w")
            label_row = tk.Frame(wrapper, bg=C["surface"])
            label_row.pack(anchor="w")
            tk.Label(label_row, text="\u25cf  TOM", bg=C["surface"], fg=C["blue"],
                font=("Segoe UI", 8, "bold")).pack(side="left")
            tk.Label(label_row, text=ts, bg=C["surface"], fg=C["muted"], font=("Segoe UI", 7)).pack(side="left", padx=(8, 0))
            msg_frame = tk.Frame(wrapper, bg=C["surface2"], padx=14, pady=10)
            msg_frame.pack(anchor="w", pady=(4, 0))
            tk.Label(msg_frame, text=text, bg=C["surface2"], fg=C["text"],
                font=("Segoe UI", 12), wraplength=540, justify="left").pack(anchor="w")
            footer = tk.Frame(wrapper, bg=C["surface"])
            footer.pack(anchor="w", pady=(2, 0))
            copy_btn = tk.Button(footer, text="Copy", bg=C["surface"], fg=C["muted"],
                activebackground=C["surface2"], activeforeground=C["text"], relief="flat",
                bd=0, padx=6, pady=0, font=("Segoe UI", 7), cursor="hand2")
            copy_btn.configure(command=lambda t=text, b=copy_btn: self._copy_to_clipboard(t, b))
            copy_btn.pack(side="left")

        else:
            wrapper = tk.Frame(bubble, bg=C["surface"])
            wrapper.pack(anchor="center")
            tk.Label(wrapper, text=text, bg=C["surface"], fg=C["muted"],
                font=("Segoe UI", 8, "italic"), wraplength=540, justify="center").pack()

        self._chat_bubbles.append(bubble)
        self.chat_inner.update_idletasks()
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))
        self.chat_canvas.yview_moveto(1.0)

    def _build_files_view(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        hdr = tk.Frame(parent, bg=C["bg"], padx=24, pady=16)
        hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(hdr, text="Generated Files", bg=C["bg"], fg=C["text"],
            font=("Segoe UI", 17, "bold")).pack(anchor="w")
        tk.Label(hdr, text="Documents, spreadsheets, presentations, and reports created by TOM.",
            bg=C["bg"], fg=C["text2"], font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))

        body = tk.Frame(parent, bg=C["bg"], padx=24, pady=16)
        body.grid(row=1, column=0, sticky="nswe")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        list_frame = tk.Frame(body, bg=C["surface"])
        list_frame.grid(row=0, column=0, sticky="nswe")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.files_listbox = tk.Listbox(list_frame, bg=C["surface2"], fg=C["text2"],
            selectbackground=C["border2"], selectforeground=C["text"], relief="flat",
            highlightthickness=0, font=("Segoe UI", 9), bd=0)
        self.files_listbox.grid(row=0, column=0, sticky="nswe")
        sb_files = tk.Scrollbar(list_frame, orient="vertical", command=self.files_listbox.yview,
            bg=C["surface"], troughcolor=C["surface2"])
        sb_files.grid(row=0, column=1, sticky="ns")
        self.files_listbox.configure(yscrollcommand=sb_files.set)

        refresh_btn = tk.Button(parent, text="\u21ba  Refresh", command=self._refresh_files_view,
            bg=C["surface2"], fg=C["text2"], activebackground=C["border2"], activeforeground=C["text"],
            relief="flat", bd=0, padx=12, pady=8, font=("Segoe UI", 9), cursor="hand2")
        refresh_btn.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 16))

        self._refresh_files_view()

    def _build_capabilities_view(self, parent):
        """Capability Center — registry-backed list of everything TOM can do."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        hdr = tk.Frame(parent, bg=C["bg"], padx=24, pady=16)
        hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(hdr, text="Capability Center", bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 17, "bold")).pack(anchor="w")
        tk.Label(hdr, text="Every registered capability, verified against its real executor. "
                           "Type any example in Chat to use it.",
                 bg=C["bg"], fg=C["text2"], font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))
        body = tk.Frame(parent, bg=C["bg"], padx=24, pady=8)
        body.grid(row=1, column=0, sticky="nswe")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        self.capabilities_text = tk.Text(body, bg=C["surface2"], fg=C["text2"], relief="flat",
                                         highlightthickness=0, font=("Consolas", 9), bd=0,
                                         wrap="word", state="disabled")
        self.capabilities_text.grid(row=0, column=0, sticky="nswe")
        cap_sb = tk.Scrollbar(body, orient="vertical", command=self.capabilities_text.yview,
                              bg=C["surface"], troughcolor=C["surface2"])
        cap_sb.grid(row=0, column=1, sticky="ns")
        self.capabilities_text.configure(yscrollcommand=cap_sb.set)
        tk.Button(parent, text="\u21ba  Refresh", command=self._refresh_capabilities_view,
                  bg=C["surface2"], fg=C["text2"], activebackground=C["border2"],
                  activeforeground=C["text"], relief="flat", bd=0, padx=12, pady=8,
                  font=("Segoe UI", 9), cursor="hand2").grid(
                      row=2, column=0, sticky="ew", padx=24, pady=(8, 16))
        self._refresh_capabilities_view()

    def _refresh_capabilities_view(self):
        try:
            from tools.capability_registry import summary_text, validate
            v = validate()
            head = (f"All {v['total']} capabilities verified against real executors.\n\n"
                    if v["ok"] else f"WARNING: broken mappings: {v['missing']}\n\n")
            content = head + summary_text()
        except Exception as exc:
            content = f"Capability registry unavailable: {exc}"
        try:
            self.capabilities_text.configure(state="normal")
            self.capabilities_text.delete("1.0", tk.END)
            self.capabilities_text.insert("1.0", content)
            self.capabilities_text.configure(state="disabled")
        except Exception:
            pass

    def _build_health_view(self, parent):
        """Health Center — live subsystem status (no more silent degradation)."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        hdr = tk.Frame(parent, bg=C["bg"], padx=24, pady=16)
        hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(hdr, text="System Health", bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 17, "bold")).pack(anchor="w")
        tk.Label(hdr, text="Live status of every subsystem. OFFLINE items degrade gracefully "
                           "— the rest of TOM keeps working.",
                 bg=C["bg"], fg=C["text2"], font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))
        body = tk.Frame(parent, bg=C["bg"], padx=24, pady=8)
        body.grid(row=1, column=0, sticky="nswe")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        self.health_text = tk.Text(body, bg=C["surface2"], fg=C["text2"], relief="flat",
                                   highlightthickness=0, font=("Consolas", 9), bd=0,
                                   wrap="word", state="disabled")
        self.health_text.grid(row=0, column=0, sticky="nswe")
        h_sb = tk.Scrollbar(body, orient="vertical", command=self.health_text.yview,
                            bg=C["surface"], troughcolor=C["surface2"])
        h_sb.grid(row=0, column=1, sticky="ns")
        self.health_text.configure(yscrollcommand=h_sb.set)
        tk.Button(parent, text="\u21ba  Refresh", command=self._refresh_health_view,
                  bg=C["surface2"], fg=C["text2"], activebackground=C["border2"],
                  activeforeground=C["text"], relief="flat", bd=0, padx=12, pady=8,
                  font=("Segoe UI", 9), cursor="hand2").grid(
                      row=2, column=0, sticky="ew", padx=24, pady=(8, 16))
        self._refresh_health_view()

    def _refresh_health_view(self):
        if getattr(self, "agent", None) and getattr(self, "agent_ready", False):
            try:
                content = self.agent._health_response().get("message", "Health unavailable.")
            except Exception as exc:
                content = f"Health check failed: {exc}"
        else:
            content = "TOM is still initializing — open this view again in a few seconds."
        try:
            self.health_text.configure(state="normal")
            self.health_text.delete("1.0", tk.END)
            self.health_text.insert("1.0", content)
            self.health_text.configure(state="disabled")
        except Exception:
            pass

    def _build_system_view(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        hdr = tk.Frame(parent, bg=C["bg"], padx=24, pady=16)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.columnconfigure(0, weight=1)
        title = tk.Frame(hdr, bg=C["bg"])
        title.grid(row=0, column=0, sticky="w")
        tk.Label(title, text="System Readiness", bg=C["bg"], fg=C["text"],
            font=("Segoe UI", 17, "bold")).pack(anchor="w")
        tk.Label(title, text="Loaded skills, executable capability paths, dependency limits, and route probes.",
            bg=C["bg"], fg=C["text2"], font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))

        actions = tk.Frame(hdr, bg=C["bg"])
        actions.grid(row=0, column=1, sticky="e")
        tk.Button(actions, text="Refresh", command=self._refresh_system_view,
            bg=C["surface2"], fg=C["text2"], activebackground=C["border2"], activeforeground=C["text"],
            relief="flat", bd=0, padx=14, pady=8, font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(actions, text="Run Check", command=self._run_system_verification,
            bg=C["emerald"], fg="#07100c", activebackground="#25a872", activeforeground="#07100c",
            relief="flat", bd=0, padx=14, pady=8, font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="left")

        body = tk.Frame(parent, bg=C["bg"], padx=24, pady=0)
        body.grid(row=1, column=0, sticky="nswe")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(1, weight=1)

        summary = tk.Frame(body, bg=C["surface"], padx=16, pady=16)
        summary.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 12))
        summary.columnconfigure(0, weight=1)
        summary.columnconfigure(1, weight=1)

        self.system_skill_var = tk.StringVar(value="0")
        self.system_tool_var = tk.StringVar(value="0 / 0")
        self.system_mode_var = tk.StringVar(value="Waiting")
        self.system_limit_var = tk.StringVar(value="0")

        def stat(row, col, label, var, color):
            card = tk.Frame(summary, bg=C["surface2"], padx=12, pady=10)
            card.grid(row=row, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0), pady=(0, 8))
            tk.Label(card, text=label.upper(), bg=C["surface2"], fg=C["muted"],
                font=("Segoe UI", 7, "bold")).pack(anchor="w")
            tk.Label(card, textvariable=var, bg=C["surface2"], fg=color,
                font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(2, 0))

        stat(0, 0, "Skills", self.system_skill_var, C["blue"])
        stat(0, 1, "Tools Ready", self.system_tool_var, C["emerald"])
        stat(1, 0, "Modes", self.system_mode_var, C["cyan"])
        stat(1, 1, "Limits", self.system_limit_var, C["amber"])

        probes = tk.Frame(body, bg=C["surface"], padx=16, pady=16)
        probes.grid(row=0, column=1, rowspan=2, sticky="nswe", padx=(8, 0))
        probes.columnconfigure(0, weight=1)
        probes.rowconfigure(1, weight=1)
        tk.Label(probes, text="Routing and dependency report", bg=C["surface"], fg=C["text"],
            font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w")
        self.system_report_list = tk.Listbox(probes, bg=C["surface2"], fg=C["text2"],
            selectbackground=C["border2"], selectforeground=C["text"], relief="flat",
            highlightthickness=0, font=("Consolas", 9), bd=0)
        self.system_report_list.grid(row=1, column=0, sticky="nswe", pady=(10, 0))
        sb_report = tk.Scrollbar(probes, orient="vertical", command=self.system_report_list.yview,
            bg=C["surface"], troughcolor=C["surface2"])
        sb_report.grid(row=1, column=1, sticky="ns", pady=(10, 0))
        self.system_report_list.configure(yscrollcommand=sb_report.set)

        limits = tk.Frame(body, bg=C["surface"], padx=16, pady=16)
        limits.grid(row=1, column=0, sticky="nswe", padx=(0, 8))
        limits.columnconfigure(0, weight=1)
        limits.rowconfigure(1, weight=1)
        tk.Label(limits, text="Unavailable or external-limited paths", bg=C["surface"], fg=C["text"],
            font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w")
        self.system_limits_list = tk.Listbox(limits, bg=C["surface2"], fg=C["text2"],
            selectbackground=C["border2"], selectforeground=C["text"], relief="flat",
            highlightthickness=0, font=("Segoe UI", 9), bd=0)
        self.system_limits_list.grid(row=1, column=0, sticky="nswe", pady=(10, 0))

        self._refresh_system_view()

    def _collect_system_report(self):
        summary = {
            "skills": "0",
            "tools": "0 / 0",
            "modes": "Unavailable",
            "limits": "0",
        }
        report_lines = []
        limit_lines = []

        manager = self.skills
        if manager is None and SkillManager:
            try:
                manager = SkillManager()
            except Exception as exc:
                manager = None
                limit_lines.append(f"Skill manager unavailable: {exc}")

        if manager:
            try:
                health = manager.health_report()
                modes = health.get("execution_modes", {})
                summary["skills"] = str(health.get("total", manager.count_skills()))
                summary["modes"] = (
                    f"T:{modes.get('tool_backed', 0)} "
                    f"E:{modes.get('external_command', 0)} "
                    f"G:{modes.get('knowledge_only', 0)}"
                )
                summary["limits"] = str(len(health.get("limited", [])))
                report_lines.append(f"skills.total = {summary['skills']}")
                report_lines.append(f"skills.sources = {health.get('sources', {})}")
                report_lines.append(f"skills.execution_modes = {modes}")
            except Exception as exc:
                limit_lines.append(f"Skill health report failed: {exc}")

            probes = [
                "frontend website",
                "react native app",
                "medical diagnosis guide",
                "medical health clinical guide",
                "design a dashboard",
                "create an NLP classifier",
                "predictive analysis",
                "blender 3d model",
            ]
            for probe in probes:
                try:
                    route = manager.route_task(probe)
                    if route.matched:
                        report_lines.append(
                            f"route[{probe}] -> {route.skill_name} "
                            f"mode={route.execution_mode} conf={route.confidence}"
                        )
                        if route.execution_mode != "tool_backed":
                            reason = "; ".join(route.limitations) if route.limitations else route.execution_mode
                            limit_lines.append(f"{route.skill_name}: {reason}")
                    else:
                        report_lines.append(f"route[{probe}] -> unmatched")
                        limit_lines.append(f"Unmatched skill route: {probe}")
                except Exception as exc:
                    report_lines.append(f"route[{probe}] -> error: {exc}")
                    limit_lines.append(f"Route probe failed for '{probe}': {exc}")

        tool_checks = [
            ("Web automation", "web_automation"),
            ("Multi-agent orchestration", "orchestrator"),
            ("Data analysis", "data_analysis"),
            ("File analyzer", "file_analyzer"),
            ("Autonomous agent", "autonomous"),
            ("Hardware control", "hardware"),
            ("ML engine", "ml_engine"),
            ("IoT engine", "iot_engine"),
            ("VLSI engine", "vlsi_engine"),
            ("Dependency manager", "dep_manager"),
            ("News agent", "news_agent"),
            ("Auto scaler", "scaler"),
            ("Voice enhanced", "voice_enhanced"),
            ("Game dev", "game_dev"),
            ("Blender control", "blender"),
            ("Auto update", "auto_update"),
        ]
        ready = 0
        for label, attr in tool_checks:
            if getattr(self, attr, None) is not None:
                ready += 1
                report_lines.append(f"tool[{label}] = ready")
            else:
                report_lines.append(f"tool[{label}] = unavailable")
                limit_lines.append(f"{label}: module, dependency, service, or credential not loaded")
        summary["tools"] = f"{ready} / {len(tool_checks)}"

        try:
            req = Request("http://localhost:11434/api/tags", method="GET")
            with urlopen(req, timeout=1) as resp:
                payload = json.loads(resp.read().decode())
            model_count = len(payload.get("models", []))
            report_lines.append(f"ollama = reachable ({model_count} model(s))")
        except Exception as exc:
            report_lines.append(f"ollama = unreachable ({exc})")
            limit_lines.append("Ollama: local model server is not reachable")

        deduped_limits = []
        seen = set()
        for line in limit_lines:
            if line not in seen:
                seen.add(line)
                deduped_limits.append(line)
        if not deduped_limits:
            deduped_limits.append("No runtime limits detected in loaded components.")

        return summary, report_lines, deduped_limits

    def _apply_system_report(self, summary, report_lines, limit_lines, announce=False):
        if not hasattr(self, "system_report_list"):
            return
        self.system_skill_var.set(summary.get("skills", "0"))
        self.system_tool_var.set(summary.get("tools", "0 / 0"))
        self.system_mode_var.set(summary.get("modes", "Unavailable"))
        self.system_limit_var.set(summary.get("limits", "0"))

        self.system_report_list.delete(0, "end")
        for line in report_lines:
            self.system_report_list.insert("end", f"  {line}")

        self.system_limits_list.delete(0, "end")
        for line in limit_lines[:80]:
            self.system_limits_list.insert("end", f"  {line}")

        if announce:
            self._append_chat(
                "assistant",
                "[System Check]\n"
                f"Skills: {summary.get('skills')}\n"
                f"Tools ready: {summary.get('tools')}\n"
                f"Modes: {summary.get('modes')}\n"
                f"Limits listed: {len(limit_lines)}"
            )

    def _refresh_system_view(self):
        if not hasattr(self, "system_report_list"):
            return
        try:
            summary, report_lines, limit_lines = self._collect_system_report()
            self._apply_system_report(summary, report_lines, limit_lines)
        except Exception as exc:
            self.system_report_list.delete(0, "end")
            self.system_report_list.insert("end", f"  System report failed: {exc}")

    def _run_system_verification(self):
        self._show_view("system")
        if hasattr(self, "system_report_list"):
            self.system_report_list.delete(0, "end")
            self.system_report_list.insert("end", "  Running runtime readiness check...")
        threading.Thread(target=self._run_system_verification_worker, daemon=True).start()

    def _run_system_verification_worker(self):
        try:
            summary, report_lines, limit_lines = self._collect_system_report()
            self._enqueue(self._apply_system_report, summary, report_lines, limit_lines, True)
        except Exception as exc:
            self._enqueue(self._append_chat, "meta", f"[System Check Error] {exc}")

    def _refresh_files_view(self):
        if not hasattr(self, "files_listbox"):
            return
        self.files_listbox.delete(0, "end")
        output_dir = str(PROJECT_ROOT / "output")
        if os.path.exists(output_dir):
            files = []
            for f in os.listdir(output_dir):
                fpath = os.path.join(output_dir, f)
                if os.path.isfile(fpath):
                    files.append((os.path.getmtime(fpath), f, os.path.getsize(fpath)))
            files.sort(key=lambda x: x[0], reverse=True)
            if files:
                for mtime, name, size in files:
                    size_str = f"{size/1024:.1f} KB" if size > 1024 else f"{size} B"
                    date_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))
                    self.files_listbox.insert("end", f"  {name}  ({size_str})  {date_str}")
                return
        self.files_listbox.insert("end", "  No files generated yet.")
        self.files_listbox.insert("end", "  Use Quick Actions or type commands to create documents.")

    def _show_view(self, view_name: str):
        self.active_view = view_name
        frame = {
            "dashboard": self.dashboard_frame,
            "chat": self.chat_frame,
            "system": self.system_frame,
            "charts": self.charts_frame,
            "files": self.files_frame,
            "capabilities": self.capabilities_frame,
            "health": self.health_frame,
        }.get(view_name, self.dashboard_frame)
        frame.tkraise()
        self._sync_nav_styles()
        self.metric_vars.get("focus", tk.StringVar()).set(view_name.title())
        if view_name == "charts":
            self.root.after(100, self._render_chart_canvas)
        elif view_name == "system":
            self.root.after(100, self._refresh_system_view)
        elif view_name == "health":
            self.root.after(100, self._refresh_health_view)
        elif view_name == "capabilities":
            self.root.after(100, self._refresh_capabilities_view)

    def _switch_view(self, view_name: str):
        self._show_view(view_name)
        return "break"

    def _set_active_agent(self, agent_key: str):
        self.active_agent_key = agent_key
        profile = self.agent_profiles[agent_key]
        self.sidebar_agent_var.set(profile["label"])
        self.sidebar_desc_var.set(profile["description"])
        self._sync_nav_styles()
        self._append_chat("meta", f"Switched to {profile['label']}.")
        if self.active_view != "chat":
            self._show_view("chat")

    def _sync_nav_styles(self):
        for key, btn in self.view_buttons.items():
            if key == self.active_view:
                btn.configure(bg=C["surface2"], fg=C["blue"])
            else:
                btn.configure(bg=C["bg"], fg=C["text2"])

    def _toggle_sidebar(self):
        if self.sidebar_visible:
            self.sidebar_frame.grid_forget()
            self.sidebar_visible = False
        else:
            self.sidebar_frame.grid(row=0, column=0, sticky="nswe")
            self.sidebar_visible = True

    def _animate_header_status(self):
        phrases = self._status_phrases
        idx = self._status_idx
        phrase = phrases[idx % len(phrases)]
        if self._status_direction == 1:
            self._status_char_idx += 1
            if self._status_char_idx > len(phrase):
                self._status_direction = -1
                self.root.after(1200, self._animate_header_status)
                return
        else:
            self._status_char_idx -= 1
            if self._status_char_idx < 0:
                self._status_idx = (self._status_idx + 1) % len(phrases)
                self._status_char_idx = 0
                self._status_direction = 1
                self.root.after(300, self._animate_header_status)
                return
        display = phrase[:self._status_char_idx] + ("\u258c" if self._status_direction == 1 else "")
        try:
            self.header_typing_var.set(display)
        except Exception:
            return
        self.root.after(60, self._animate_header_status)

    def _tick_clock(self):
        try:
            self.clock_var.set(time.strftime("%H:%M:%S"))
        except Exception:
            pass
        self.root.after(1000, self._tick_clock)

    def _animate_orb(self):
        try:
            if self.orb_canvas.winfo_exists():
                w = self.orb_canvas.winfo_width()
                h = self.orb_canvas.winfo_height()
                if w > 10 and h > 10:
                    self.orb.cx = w // 2
                    self.orb.cy = h // 2
                self.orb.status = "ready" if self.agent_ready else "loading"
                self.orb.draw()
        except Exception:
            pass
        self.root.after(33, self._animate_orb)

    def _on_agent_progress(self, message: str):
        """Show agent progress in the status bar and update the last thinking bubble."""
        if not self.processing:
            return
        try:
            self._enqueue(self._set_status, message[:80])
            # Update the last "thinking" meta message in chat
            if self._chat_bubbles:
                last = self._chat_bubbles[-1]
                for child in last.winfo_children():
                    for sub in child.winfo_children():
                        if isinstance(sub, tk.Label) and "thinking" in str(sub.cget("text")).lower():
                            self._enqueue(lambda m=message: sub.config(text=m[:100]))
                            return
        except Exception:
            pass

    def _set_status(self, text: str):
        try:
            self.status_text_var.set(text)
            if text.lower() in ("ready",):
                self.status_dot_canvas.itemconfig(self.status_dot, fill=C["emerald"])
                try:
                    self._ready_dot_canvas.itemconfig(self._ready_text, text="READY", fill=C["emerald"])
                except Exception:
                    pass
            elif "error" in text.lower() or "fail" in text.lower():
                self.status_dot_canvas.itemconfig(self.status_dot, fill=C["red"])
            else:
                self.status_dot_canvas.itemconfig(self.status_dot, fill=C["amber"])
        except Exception:
            pass

    def _holo_anim_loop(self):
        """30 fps animation loop driving the holographic dashboard canvas."""
        if not getattr(self, "_holo_anim_running", False):
            return
        if hasattr(self, "_holo") and self.active_view == "dashboard":
            try:
                self._holo.draw()
            except Exception:
                pass
        self.root.after(33, self._holo_anim_loop)

    def _refresh_dashboard(self):
        """Push current stats into the holo dashboard and update legacy metric_vars."""
        # Legacy vars (used by charts view)
        self.metric_vars.get("messages", tk.StringVar()).set(str(self.activity_counts["messages"]))
        self.metric_vars.get("voice",    tk.StringVar()).set("On" if self.voice_mode_enabled else "Off")
        self.metric_vars.get("agent",    tk.StringVar()).set(self.agent_profiles[self.active_agent_key]["label"])
        self.metric_vars.get("focus",    tk.StringVar()).set(self.active_view.title())
        self.metric_vars.get("docs",     tk.StringVar()).set(str(self.activity_counts["documents"]))
        self.metric_vars.get("analysis", tk.StringVar()).set(str(self.activity_counts["analysis"]))

        # Push live stats into holo dashboard
        if hasattr(self, "_holo"):
            node_vals = [
                self.activity_counts["messages"],
                self.activity_counts["voice"],
                self.activity_counts["documents"],
                self.activity_counts["analysis"],
                self.activity_counts["email"],
                self.activity_counts.get("files", 0),
            ]
            self._holo.push_stats(node_vals)

            # Status + model + memory
            model_name = getattr(self, "model_var", None)
            model_str  = model_name.get() if model_name else ""
            mem_count  = 0
            try:
                if hasattr(self, "agent") and self.agent_ready and self.agent.rag and self.agent.rag.available:
                    s = self.agent.rag.stats()
                    mem_count = s.get("conversations", 0) + s.get("knowledge_items", 0) + s.get("document_chunks", 0)
            except Exception:
                pass
            status = getattr(self, "_status_text", "Ready")
            self._holo.set_status(status, model_str, mem_count)

            # Activity log lines
            for ev in self.recent_events[-5:]:
                if ev not in getattr(self, "_holo_last_events", set()):
                    self._holo.push_log(f"► {ev}")
            self._holo_last_events = set(self.recent_events[-20:])

        # Charts view
        if hasattr(self, "chart_notes"):
            self.chart_notes.delete(0, "end")
            items = [
                ("Messages",  self.activity_counts["messages"],  C["blue"]),
                ("Voice",     self.activity_counts["voice"],     C["cyan"]),
                ("Documents", self.activity_counts["documents"], C["emerald"]),
                ("Analysis",  self.activity_counts["analysis"],  C["amber"]),
                ("Email",     self.activity_counts["email"],     C["orange"]),
                ("Instagram", self.activity_counts["instagram"], C["pink"]),
                ("Files",     self.activity_counts.get("files", len(list(self._iter_output_files()))), C["purple"]),
            ]
            for label, val, _ in items:
                self.chart_notes.insert("end", f"  {label}: {val}")
            self.chart_notes.insert("end", "")
            self.chart_notes.insert("end", f"  Agent: {self.agent_profiles[self.active_agent_key]['label']}")

        if hasattr(self, "chart_canvas"):
            self._render_chart_canvas()

    def _iter_output_files(self):
        output_dir = str(PROJECT_ROOT / "output")
        if os.path.exists(output_dir):
            for f in os.listdir(output_dir):
                p = os.path.join(output_dir, f)
                if os.path.isfile(p):
                    yield p

    def _render_chart_canvas(self):
        cv = self.chart_canvas
        cv.delete("all")
        w = max(300, cv.winfo_width() or 300)
        h = max(240, cv.winfo_height() or 240)

        items = [
            ("Messages",  self.activity_counts["messages"],  C["blue"]),
            ("Voice",     self.activity_counts["voice"],     C["cyan"]),
            ("Documents", self.activity_counts["documents"], C["emerald"]),
            ("Analysis",  self.activity_counts["analysis"],  C["amber"]),
            ("Email",     self.activity_counts["email"],     C["orange"]),
            ("Instagram", self.activity_counts["instagram"], C["pink"]),
            ("Files",     self.activity_counts.get("files", len([1 for _ in self._iter_output_files()])), C["purple"]),
        ]
        max_val = max(1, max(v for _, v, _ in items))

        bar_left  = 90
        bar_right = w - 50
        bar_area  = bar_right - bar_left
        top_pad   = 24
        bot_pad   = 24
        usable_h  = h - top_pad - bot_pad
        n         = len(items)
        row_h     = usable_h / n
        bar_h     = row_h * 0.52

        for i in range(5):
            gx = bar_left + bar_area * i / 4
            cv.create_line(gx, top_pad, gx, h - bot_pad, fill=C["border"], dash=(2, 4))

        for idx, (label, val, color) in enumerate(items):
            cy_bar = top_pad + idx * row_h + row_h / 2
            y1 = cy_bar - bar_h / 2
            y2 = cy_bar + bar_h / 2
            target = bar_area * (val / max_val) if max_val > 0 else 0
            current = self._chart_bars_current[idx]
            new = current + (target - current) * 0.18
            self._chart_bars_current[idx] = new
            cv.create_rectangle(bar_left, y1, bar_right, y2, fill=C["surface"], outline="")
            if new > 1:
                cv.create_rectangle(bar_left, y1, bar_left + new, y2, fill=color, outline="")
                cv.create_rectangle(bar_left + new - 2, y1, bar_left + new + 1, y2, fill=blend(color, "#ffffff", 0.4), outline="")
            cv.create_text(bar_left - 8, cy_bar, anchor="e", text=label, fill=C["text2"], font=("Segoe UI", 8))
            cv.create_text(bar_right + 6, cy_bar, anchor="w", text=str(val), fill=color, font=("Segoe UI", 8, "bold"))

        if self.active_view == "charts":
            need_more = any(abs(self._chart_bars_current[i] - (bar_area * (v / max(1, max_val)))) > 0.5 for i, (_, v, _) in enumerate(items))
            if need_more:
                self.root.after(33, self._render_chart_canvas)

    def _quick_action(self, cmd_prefix: str):
        if "Web Auto" in cmd_prefix:
            self._prompt_and_run("Enter URL or localhost port to verify:", self._handle_web_automation)
        elif "Multi-Agent" in cmd_prefix:
            self._prompt_and_run("Describe the multi-agent task:", self._handle_multi_agent)
        elif "Security" in cmd_prefix:
            self._prompt_and_run("Enter URL to check safety:", self._handle_security_check)
        elif "File Anal" in cmd_prefix:
            self._prompt_and_run("Enter file path to analyze:", self._handle_file_analysis)
        elif "Data Anal" in cmd_prefix:
            self._prompt_and_run("Enter file path or description for data analysis:", self._handle_data_analysis)
        elif "Autonomous" in cmd_prefix:
            self._prompt_and_run("Describe the autonomous task to execute:", self._handle_autonomous)
        elif "Hardware" in cmd_prefix:
            self._prompt_and_run("Describe hardware action (e.g., 'move mouse to 500 500', 'click', 'type Hello'):", self._handle_hardware)
        elif "Skill" in cmd_prefix:
            self._prompt_and_run("Enter skill name or question (e.g., 'design', 'data engineering', 'what skills are loaded?'):", self._handle_skill_query)
        elif "ML" in cmd_prefix:
            self._prompt_and_run("ML task (e.g., 'regression linear X=[1,2,3] y=[2,4,6]', 'classify knn', 'auto_ml', 'cluster kmeans', 'ts arima'):", self._handle_ml)
        elif "IoT" in cmd_prefix:
            self._prompt_and_run("IoT task (e.g., 'esp32 dht11 mqtt', 'micropython esp8266', 'protocol mqtt broker', 'sensor bme280'):", self._handle_iot)
        elif "VLSI" in cmd_prefix:
            self._prompt_and_run("VLSI task (e.g., 'verilog counter width=8', 'rtl fsm states=4', 'embedded stm32 gpio', 'freertos tasks=3'):", self._handle_vlsi)
        elif "Env" in cmd_prefix:
            self._prompt_and_run("Env task (e.g., 'create venv', 'install flask', 'update all', 'migrate 3.11', 'check conflicts', 'analyze project'):", self._handle_env)
        elif "News" in cmd_prefix:
            self._prompt_and_run("News task (e.g., 'daily briefing', 'tech roundup', 'world events', 'search AI advances', 'trending'):", self._handle_news)
        elif "Voice+" in cmd_prefix:
            self._prompt_and_run("Voice+ task (e.g., 'analyze emotion text: I feel sad', 'start conversation', 'assess mental state', 'speak Hello world'):", self._handle_voice_enhanced)
        elif "Game Dev" in cmd_prefix:
            self._prompt_and_run("Game dev command (e.g., 'scaffold pygame my_game platformer', 'script unity player movement', 'engines', 'installed'):", self._handle_game_dev)
        elif "Blender" in cmd_prefix:
            self._prompt_and_run("Blender command (e.g., 'cube', 'sphere', 'terrain', 'house', 'lights', 'render', 'animation', 'list'):", self._handle_blender)
        elif "Auto-Update" in cmd_prefix:
            self._prompt_and_run("Auto-update command (e.g., 'check', 'pull', 'pip', 'full', 'research <topic>', 'trending', 'history'):", self._handle_auto_update)
        else:
            self._show_view("chat")
            self.input_var.set(cmd_prefix)
            self.input_entry.focus_set()
            self.input_entry.icursor(tk.END)

    def _prompt_and_run(self, prompt_text: str, handler):
        import tkinter.simpledialog as sd
        result = sd.askstring("TOM", prompt_text, parent=self.root)
        if result:
            handler(result.strip())

    def _toggle_voice_mode(self):
        if not self.voice:
            self._append_chat("meta", "Voice tools are not available in this environment.")
            return
        if not self.voice_mode_enabled:
            self.voice.input_enabled = True
            self.voice.output_enabled = True
            self.voice._setup_input()
            self.voice._setup_output()
            status = self.voice.status()
            if not status["voice_input_enabled"]:
                self._append_chat("meta", f"Voice mode could not start: {status.get('voice_input_error', 'unknown error')}")
                return
            self.voice_mode_enabled = True
            self.voice_btn.configure(text="  \u266a  Voice: ON", bg=C["blue"], fg="#ffffff")

            if self.agent_ready and self.agent:
                self._show_view("chat")

                def _on_voice_status(state, text):
                    self._enqueue(self._append_chat, "meta", f"[{state.upper()}] {text}")
                    if state == "listening":
                        self._enqueue(self._set_status, "Listening...")
                        self._enqueue(setattr, self.orb, "status", "loading")
                    elif state == "processing":
                        self._enqueue(self._set_status, "Processing...")
                        self._enqueue(setattr, self.orb, "status", "loading")
                    elif state == "speaking":
                        self._enqueue(self._set_status, "Speaking...")
                        self._enqueue(setattr, self.orb, "status", "ready")
                    elif state in ("idle", "error"):
                        self._enqueue(self._set_status, "Ready")
                        self._enqueue(self._stop_voice_ui)
                        self._enqueue(setattr, self.orb, "status", "ready")

                self.voice.start_conversation_mode(
                    process_fn=self.agent.generate_voice_response,
                    on_status=_on_voice_status,
                )
                self._append_chat("assistant",
                    "Voice mode activated! I'm listening. Speak naturally \u2014 say 'stop' or 'bye' to end the conversation.")
            else:
                self._append_chat("meta", "Voice mode enabled. TOM is still initializing...")
        else:
            self._stop_voice_ui()
        self._refresh_dashboard()

    def _stop_voice_ui(self):
        self.voice_mode_enabled = False
        if self.voice:
            self.voice.stop_conversation_mode()
            self.voice.input_enabled = False
            self.voice.output_enabled = False
        self.voice_btn.configure(text="  \u266a  Voice Mode", bg=C["surface2"], fg=C["text"])
        self._set_status("Ready")

    def _run_active_agent_action(self):
        if self.processing:
            return
        workflow_commands = {
            "core": "Show me the current dashboard status and what I should prioritize.",
            "email": "Summarize my inbox, triage important emails, and draft safe replies.",
            "instagram": "Run the Instagram AI news workflow and summarize important posts.",
        }
        cmd = workflow_commands.get(self.active_agent_key, "Help me with the current task.")
        self._show_view("chat")
        self.input_var.set(cmd)
        self.send_message()

    def _open_voice_ui(self):
        """Open the dedicated Voice Conversation UI window."""
        if self._voice_ui_window is not None:
            try:
                self._voice_ui_window.window.lift()
                self._voice_ui_window.window.focus_force()
                return
            except Exception:
                self._voice_ui_window = None
        if not self.voice:
            self._append_chat("meta", "Voice tools not available.")
            return
        self._voice_ui_window = VoiceUIWindow(self.root, self)
        self._show_view("chat")

    def _on_mic_click(self):
        if not self.voice:
            self._append_chat("meta", "Voice tools not available.")
            return
        if not getattr(self.voice, "input_enabled", False):
            err = getattr(self.voice, "_input_error", "Voice input disabled.")
            self._append_chat("meta", f"Voice input unavailable: {err}")
            return
        if self.processing:
            return
        self._append_chat("meta", "Listening for your voice...")
        try:
            self.mic_btn.configure(state="disabled")
        except Exception:
            pass

        def listen_and_insert():
            try:
                out = self.voice.listen_once()
                if out.get("status") == "success" and out.get("text"):
                    recognized = out["text"]
                    self.activity_counts["voice"] += 1
                    self.recent_events.append(f"Voice: {recognized}")
                    self._enqueue(self._refresh_dashboard)
                    self._enqueue(self._append_chat, "meta", f"Voice captured: {recognized}")
                    self._enqueue(self.input_var.set, recognized)
                else:
                    self._enqueue(self._append_chat, "meta", f"Voice: {out.get('message')}")
            except Exception as exc:
                self._enqueue(self._append_chat, "meta", f"Voice listen failed: {exc}")
            finally:
                self._enqueue(lambda: self.mic_btn.configure(state="normal"))

        self.input_entry.focus_set()
        threading.Thread(target=listen_and_insert, daemon=True).start()

    _VOICE_TRIGGER_WORDS = (
        "talk", "voice mode", "talk to me", "let's talk", "lets talk",
        "voice chat", "conversation mode", "hey tom let's talk",
        "start voice", "start talking",
    )

    def send_message(self):
        if self.processing:
            return
        if not self.agent_ready:
            self._append_chat("meta", "TOM is still initializing. Please wait.")
            return
        text = self.input_var.get().strip()
        if not text or (hasattr(self, '_input_has_placeholder') and self._input_has_placeholder):
            return

        if text.lower().strip() in self._VOICE_TRIGGER_WORDS:
            self.input_var.set("")
            self._toggle_voice_mode()
            return

        self.input_var.set("")
        self.last_user_message = text

        # Handle attachments — route images/files to analyze_file
        attached_files = list(self._attachments) if self._attachments else []
        self._clear_attachments()

        if attached_files:
            # Show image previews in chat for image attachments
            for atype, apath in attached_files:
                if atype == "image":
                    self._append_chat_image("user", apath, text)

            # Route to analyze_file for image/file attachments
            image_paths = [p for t, p in attached_files if t == "image"]
            file_paths = [p for t, p in attached_files if t == "file"]
            link_paths = [p for t, p in attached_files if t == "link"]

            if image_paths or file_paths:
                analyze_path = (image_paths + file_paths)[0]
                question = text if text else "Analyze this in detail. Describe what you see."
                if not any(ap[0] == "image" for ap in attached_files):
                    self._append_chat("user", text if text else f"Analyze: {os.path.basename(analyze_path)}")
                self._append_chat("meta", f"TOM is analyzing {os.path.basename(analyze_path)}...")
                self.send_btn.configure(state="disabled")
                self.orb.status = "loading"
                self.processing = True
                threading.Thread(target=self._process_file_analysis,
                                 args=(analyze_path, question), daemon=True).start()
                return
            elif link_paths:
                text = f"Analyze this web page: {link_paths[0]}" + (f"\n{text}" if text else "")

        full_text = text
        prefix = self.agent_profiles[self.active_agent_key]["prefix"].strip()
        routed = f"{prefix}\n\nUser request: {full_text}" if prefix else full_text

        self.activity_counts["messages"] += 1
        if self.active_agent_key == "email":
            self.activity_counts["email"] += 1
        elif self.active_agent_key == "instagram":
            self.activity_counts["instagram"] += 1

        self.recent_events.append(f"{self.agent_profiles[self.active_agent_key]['label']}: {text[:60]}")
        self._refresh_dashboard()
        self._append_chat("user", text)
        self._append_chat("meta", f"TOM is thinking...")

        self.send_btn.configure(state="disabled")
        self.orb.status = "loading"
        self.processing = True
        threading.Thread(target=self._process_message, args=(routed,), daemon=True).start()

        # Update header
        self._status_phrases = ["Processing...", "Thinking...", "Analyzing...", "Working..."]
        self._status_idx = 0
        self._status_char_idx = 0
        self._status_direction = 1

    def _process_message(self, text: str):
        try:
            future = asyncio.run_coroutine_threadsafe(self.agent.execute_task(text), self._loop)
            result = future.result(timeout=180)
            message = str(result.get("message", "Done."))
            exp_id = result.get("experience_id")
            self.last_response_message = message
            self.last_experience_id = exp_id
            self.last_agent_result = result

            rtype = result.get("response_type", "")
            if any(t in rtype for t in ("doc", "word", "document")):
                self.activity_counts["documents"] += 1
            elif "analysis" in rtype:
                self.activity_counts["analysis"] += 1

            self._enqueue(self._on_response_ready, message, exp_id, result)
        except Exception as exc:
            self._enqueue(self._on_response_ready, f"Error: {exc}", None, None)

    def _process_file_analysis(self, file_path: str, question: str):
        """Analyze a file/image using the agent's vision + file analysis pipeline."""
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.agent.analyze_file(file_path, question), self._loop)
            result = future.result(timeout=180)
            message = str(result.get("message", "Analysis complete."))
            exp_id = result.get("experience_id")
            self.last_response_message = message
            self.last_experience_id = exp_id
            self.last_agent_result = result
            self.activity_counts["analysis"] += 1
            self._enqueue(self._on_response_ready, message, exp_id, result)
        except Exception as exc:
            self._enqueue(self._on_response_ready, f"Analysis error: {exc}", None, None)

    def _on_response_ready(self, message: str, exp_id, result):
        self._append_chat("assistant", message)
        self.processing = False
        self.orb.status = "ready"
        self.send_btn.configure(state="normal")
        self.input_entry.focus_set()

        state = "normal" if exp_id else "disabled"
        self.reward_btn.configure(state=state)
        self.penalty_btn.configure(state=state)

        if exp_id:
            self._append_chat("meta", f"Experience ID: {exp_id}. Use Reward or Penalty.")

        if isinstance(result, dict):
            attention = result.get("main_screen_items", []) or []
            if attention:
                self._append_chat("meta", f"Email attention: {len(attention)} important email(s).")
                for item in attention[:5]:
                    self._append_chat("assistant",
                        f"Email attention\nFrom: {item.get('sender', 'Unknown')}\nSubject: {item.get('subject', 'No subject')}\n{item.get('summary', '')}")

        self.recent_events.append(f"TOM: {message[:80]}")
        self._refresh_dashboard()

        try:
            if self.voice and getattr(self.voice, "output_enabled", False):
                threading.Thread(target=lambda: self.voice.speak(message[:500]), daemon=True).start()
        except Exception:
            pass

        self._status_phrases = ["Ready", "Thinking...", "Listening...", "Processing...", "Analyzing..."]

    def reward_response(self):
        if not self.last_experience_id or not self.agent:
            self._append_chat("meta", "No response to reward yet.")
            return
        exp_id = int(self.last_experience_id)

        def run():
            try:
                future = asyncio.run_coroutine_threadsafe(self.agent.give_reward(exp_id, 1.0), self._loop)
                out = future.result(timeout=30)
                self._enqueue(self._append_chat, "meta", f"Reward saved: {out.get('message')}")
            except Exception as exc:
                self._enqueue(self._append_chat, "meta", f"Reward failed: {exc}")
        threading.Thread(target=run, daemon=True).start()

    def penalize_and_revise(self):
        if not self.last_experience_id or not self.agent:
            self._append_chat("meta", "No response to penalize yet.")
            return
        correction = self.feedback_var.get().strip()
        if not correction or correction.lower().startswith("tell tom"):
            correction = "Improve response accuracy and align strictly with my request."

        exp_id = int(self.last_experience_id)
        old_resp = self.last_response_message
        user_msg = self.last_user_message
        self._append_chat("meta", "Applying penalty and revising...")

        def run():
            try:
                pen_f = asyncio.run_coroutine_threadsafe(self.agent.give_reward(exp_id, -1.0), self._loop)
                pen_out = pen_f.result(timeout=30)
                rev_f = asyncio.run_coroutine_threadsafe(
                    self.agent.revise_response_with_feedback(user_command=user_msg, previous_response=old_resp, feedback=correction),
                    self._loop,
                )
                revised = rev_f.result(timeout=120)
                revised_msg = revised.get("message", old_resp)
                self.last_response_message = revised_msg
                self._enqueue(self._append_chat, "meta", f"Penalty saved: {pen_out.get('message')}")
                self._enqueue(self._append_chat, "assistant", f"[Revised] {revised_msg}")
            except Exception as exc:
                self._enqueue(self._append_chat, "meta", f"Revise failed: {exc}")
        threading.Thread(target=run, daemon=True).start()

    def _poll_email_agent_state(self):
        try:
            if os.path.exists(self._email_state_file):
                with open(self._email_state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                pending = state.get("pending_approval_replies", []) or []
                new_items = []
                for item in pending:
                    key = (item.get("approval_key") or f"{item.get('to', '')}|{item.get('subject', '')}")
                    if key and key not in self._seen_email_approval_keys:
                        self._seen_email_approval_keys.add(key)
                        new_items.append(item)
                if new_items:
                    self._append_chat("meta", f"Email approval needed: {len(new_items)} draft(s).")
                    for item in new_items[:5]:
                        self._append_chat("assistant",
                            f"Email needs approval\nFrom: {item.get('from', 'Unknown')}\nTo: {item.get('to', 'Unknown')}\nSubject: {item.get('subject', 'No subject')}\nDraft: {item.get('reply_body_preview', '')}")
                    self.activity_counts["email"] += len(new_items)
                    self.recent_events.append(f"Email approvals: {len(new_items)}")
                    self._refresh_dashboard()
                    if self.active_view != "chat":
                        self._show_view("chat")
        except Exception:
            pass
        finally:
            self.root.after(7000, self._poll_email_agent_state)

    def _enqueue(self, fn, *args):
        self.ui_queue.put((fn, args))

    def _drain_ui_queue(self):
        while True:
            try:
                fn, args = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                fn(*args)
            except Exception:
                pass
        self.root.after(120, self._drain_ui_queue)

    # ── New System Initialization ──────────────────────────────────────

    def _init_web_automation(self):
        try:
            from tools.web_automation import WebAutomationSuite
            if self.agent and hasattr(self.agent, 'browser_tools'):
                self.web_automation = WebAutomationSuite(self.agent.browser_tools)
                self._append_chat("meta", "[Web Automation Suite loaded]")
        except Exception as exc:
            self._append_chat("meta", f"[Web Automation unavailable: {exc}]")

    def _init_orchestrator(self):
        try:
            from tools.agent_orchestrator import AgentOrchestrator
            if self.agent:
                self.orchestrator = AgentOrchestrator(tom_agent=self.agent, llm=getattr(self.agent, 'llm', None))
                self._append_chat("meta", "[Multi-Agent Orchestrator loaded]")
        except Exception as exc:
            self._append_chat("meta", f"[Orchestrator unavailable: {exc}]")

    def _init_v3_tools(self):
        """Initialize v3 tools: Data Analysis, File Analyzer, Autonomous Agent."""
        try:
            if DataAnalysisEngine:
                self.data_analysis = DataAnalysisEngine()
                self._append_chat("meta", "[Data Analysis Engine loaded]")
        except Exception as exc:
            self._append_chat("meta", f"[Data Analysis unavailable: {exc}]")

        try:
            if FileAnalyzer:
                self.file_analyzer = FileAnalyzer()
                self._append_chat("meta", "[File Analyzer loaded]")
        except Exception as exc:
            self._append_chat("meta", f"[File Analyzer unavailable: {exc}]")

        try:
            if AutonomousAgent and self.agent:
                self.autonomous = AutonomousAgent(tom_agent=self.agent, llm=getattr(self.agent, 'llm', None))
                self._append_chat("meta", "[Autonomous Agent loaded]")
        except Exception as exc:
            self._append_chat("meta", f"[Autonomous Agent unavailable: {exc}]")

        try:
            if SkillManager:
                self.skills = SkillManager()
                count = self.skills.count_skills()
                self._append_chat("meta", f"[Skill System: {count} domain skills loaded]")
        except Exception as exc:
            self._append_chat("meta", f"[Skill System unavailable: {exc}]")

        try:
            if HardwareControl:
                self.hardware = HardwareControl()
                self._append_chat("meta", f"[Hardware Control: mouse/keyboard/screen]")
        except Exception as exc:
            self._append_chat("meta", f"[Hardware Control unavailable: {exc}]")

        try:
            if MLEngine:
                self.ml_engine = MLEngine()
                self._append_chat("meta", f"[ML Engine: 89 algorithms loaded]")
        except Exception as exc:
            self._append_chat("meta", f"[ML Engine unavailable: {exc}]")

        try:
            if IoTEngine:
                self.iot_engine = IoTEngine()
                self._append_chat("meta", f"[IoT Engine: ESP32/ESP8266, protocols, sensors]")
        except Exception as exc:
            self._append_chat("meta", f"[IoT Engine unavailable: {exc}]")

        try:
            if VLSIEngine:
                self.vlsi_engine = VLSIEngine()
                self._append_chat("meta", f"[VLSI Engine: HDL, embedded C, RTOS, FPGA]")
        except Exception as exc:
            self._append_chat("meta", f"[VLSI Engine unavailable: {exc}]")

        try:
            if DependencyManager:
                self.dep_manager = DependencyManager()
                self._append_chat("meta", f"[Dependency Manager: venv, packages, 3.11 migration]")
        except Exception as exc:
            self._append_chat("meta", f"[Dependency Manager unavailable: {exc}]")

        try:
            if NewsAgent:
                self.news_agent = NewsAgent()
                self._append_chat("meta", f"[News Agent: daily briefing, auto-update]")
        except Exception as exc:
            self._append_chat("meta", f"[News Agent unavailable: {exc}]")

        try:
            if AutoScaler:
                self.scaler = AutoScaler()
                self._append_chat("meta", f"[Auto Scaler: resource management, parallel exec]")
        except Exception as exc:
            self._append_chat("meta", f"[Auto Scaler unavailable: {exc}]")

        try:
            if VoiceEnhanced:
                self.voice_enhanced = VoiceEnhanced()
                self._append_chat("meta", f"[Voice Enhanced: emotion detection, full duplex]")
        except Exception as exc:
            self._append_chat("meta", f"[Voice Enhanced unavailable: {exc}]")
        self._refresh_system_view()

    # ── New Action Handlers ────────────────────────────────────────────

    def _handle_web_automation(self, detail: str):
        if not self.agent or not self.agent_ready:
            self._append_chat("meta", "TOM is still initializing.")
            return
        if not detail:
            self._append_chat("meta", "Provide a URL or localhost port to verify.")
            return
        threading.Thread(target=self._run_web_automation, args=(detail,), daemon=True).start()

    def _run_web_automation(self, detail: str):
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._async_web_automation(detail), self._loop
            )
            result = future.result(timeout=120)
            msg = result.get("message", str(result))[:300]
            self._enqueue(self._append_chat, "assistant", f"[Web Auto] {msg}")
        except Exception as exc:
            self._enqueue(self._append_chat, "meta", f"[Web Auto Error] {exc}")

    async def _async_web_automation(self, detail: str):
        detail = detail.strip()
        if detail.isdigit():
            port = int(detail)
            url = f"http://localhost:{port}"
        elif not detail.startswith("http"):
            url = f"http://{detail}"
        else:
            url = detail
        if self.web_automation:
            return await self.web_automation.wait_and_verify(url)
        if self.agent and hasattr(self.agent, 'browser_tools') and self.agent.browser_tools:
            return await self.agent.browser_tools.wait_and_verify(url)
        return {"status": "error", "message": "Web automation not available"}

    def _handle_multi_agent(self, detail: str):
        if not self.orchestrator:
            self._append_chat("meta", "Multi-agent system not available.")
            return
        if not detail:
            self._append_chat("meta", "Describe the task for the multi-agent system.")
            return
        threading.Thread(target=self._run_multi_agent, args=(detail,), daemon=True).start()

    def _run_multi_agent(self, detail: str):
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.orchestrator.deploy_multi_agent_task(detail), self._loop
            )
            result = future.result(timeout=120)
            msg = result.get("message", str(result))[:300]
            self._enqueue(self._append_chat, "assistant", f"[Multi-Agent] {msg}")
        except Exception as exc:
            self._enqueue(self._append_chat, "meta", f"[Multi-Agent Error] {exc}")

    def _handle_security_check(self, detail: str):
        if not detail:
            self._append_chat("meta", "Provide a URL to check.")
            return
        try:
            from safety.guards import SafetyGuards
            safety = SafetyGuards()
            analysis = safety.analyze_website(detail)
            score = analysis.get("score", 0)
            trust = analysis.get("trust_level", "unknown")
            flags = analysis.get("flags", [])
            rec = analysis.get("recommendation", "unknown")
            msg = (
                f"[Security Check] {detail}\n"
                f"  Trust Level: {trust}\n"
                f"  Safety Score: {score}/100\n"
                f"  Flags: {', '.join(flags) if flags else 'none'}\n"
                f"  Recommendation: {rec}"
            )
            self._enqueue(self._append_chat, "assistant", msg)
        except Exception as exc:
            self._enqueue(self._append_chat, "meta", f"[Security Error] {exc}")

    def _handle_auto_debug(self, detail: str):
        if not detail:
            self._append_chat("meta", "Provide a URL to auto-debug.")
            return
        threading.Thread(target=self._run_auto_debug, args=(detail,), daemon=True).start()

    def _run_auto_debug(self, detail: str):
        try:
            detail = detail.strip()
            if not detail.startswith("http"):
                detail = f"http://{detail}"
            future = asyncio.run_coroutine_threadsafe(
                self._async_auto_debug(detail), self._loop
            )
            result = future.result(timeout=180)
            iterations = result.get("total_iterations", 0)
            msg = f"[Auto-Debug] {detail}: {result.get('message', 'Done')} ({iterations} iterations)"
            self._enqueue(self._append_chat, "assistant", msg)
        except Exception as exc:
            self._enqueue(self._append_chat, "meta", f"[Auto-Debug Error] {exc}")

    async def _async_auto_debug(self, url: str):
        if self.web_automation:
            return await self.web_automation.auto_debug_loop(url, max_iterations=3)
        return {"status": "error", "message": "Web automation not available"}

    # ── v3 Tool Handlers ────────────────────────────────────────────────

    def _handle_file_analysis(self, detail: str):
        if not self.file_analyzer:
            self._append_chat("meta", "File Analyzer not available.")
            return
        if not detail or not os.path.exists(detail):
            self._append_chat("meta", f"File not found: {detail}")
            return
        threading.Thread(target=self._run_file_analysis, args=(detail,), daemon=True).start()

    def _run_file_analysis(self, filepath: str):
        try:
            result = self.file_analyzer.analyze(filepath)
            summary = self.file_analyzer.summarize(filepath)
            self._enqueue(lambda: self._append_chat("assistant", f"[File Analysis]\n{summary}"))
            self._enqueue(lambda: self._append_chat("meta", f"Status: {result.get('status')}"))
        except Exception as exc:
            err_msg = f"[File Analysis Error] {exc}"
            self._enqueue(lambda m=err_msg: self._append_chat("meta", m))

    def _handle_data_analysis(self, detail: str):
        if not self.data_analysis:
            self._append_chat("meta", "Data Analysis Engine not available.")
            return
        threading.Thread(target=self._run_data_analysis, args=(detail,), daemon=True).start()

    def _run_data_analysis(self, detail: str):
        try:
            detail = detail.strip()
            if os.path.exists(detail):
                df = self.data_analysis.load_data(detail)
                df, clean_report = self.data_analysis.auto_clean(df)
                insights = self.data_analysis.generate_insights(df)
                report_path = self.data_analysis.generate_report(df, f"Analysis of {os.path.basename(detail)}")
                overview = insights.get("overview", {})
                msg = (
                    f"[Data Analysis Complete]\n"
                    f"Rows: {overview.get('rows', '?')} | Columns: {overview.get('columns', '?')}\n"
                    f"Cleaning: {len(clean_report.get('operations', []))} ops\n"
                    f"Correlations: {len(insights.get('correlations', []))}\n"
                    f"Anomalies: {len(insights.get('anomalies', []))}\n"
                    f"Recommendations: {len(insights.get('recommendations', []))}\n"
                    f"HTML Report: {report_path}"
                )
                self._enqueue(lambda: self._append_chat("assistant", msg))
            else:
                # Let agent handle text-based analysis request
                self._enqueue(lambda: self.input_var.set(f"Analyze data: {detail}"))
                self._enqueue(lambda: self.send_message())
        except Exception as exc:
            err_msg = f"[Data Analysis Error] {exc}"
            self._enqueue(lambda m=err_msg: self._append_chat("meta", m))

    def _handle_autonomous(self, detail: str):
        if not self.autonomous:
            self._append_chat("meta", "Autonomous Agent not available.")
            return
        if not detail:
            self._append_chat("meta", "Describe the task for the autonomous agent.")
            return
        threading.Thread(target=self._run_autonomous, args=(detail,), daemon=True).start()

    def _run_autonomous(self, detail: str):
        try:
            self._enqueue(lambda: self._append_chat("meta", f"[Autonomous] Starting task: {detail[:80]}..."))
            import asyncio
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(self.autonomous.execute(detail))
            loop.close()
            msg = (
                f"[Autonomous Complete]\n"
                f"Subtasks: {result.get('subtasks_count', 0)}\n"
                f"Completed: {result.get('completed_count', 0)}\n"
                f"Duration: {result.get('duration_seconds', 0)}s\n"
                f"Reflection: {result.get('reflection', '')[:300]}"
            )
            self._enqueue(lambda: self._append_chat("assistant", msg))
        except Exception as exc:
            err_msg = f"[Autonomous Error] {exc}"
            self._enqueue(lambda m=err_msg: self._append_chat("meta", m))

    def _handle_hardware(self, detail: str):
        """Execute a hardware control command."""
        if not self.hardware or not self.hardware.is_available():
            self._append_chat("meta", "[Hardware Control not available - install pyautogui: pip install pyautogui]")
            return
        detail = detail.strip().lower()
        response_msg = ""
        try:
            if detail.startswith("move") or detail.startswith("move mouse"):
                parts = detail.replace("move mouse", "").replace("move", "").strip().split()
                if len(parts) >= 2:
                    x, y = int(parts[0]), int(parts[1])
                    r = self.hardware.move_mouse(x, y)
                    response_msg = f"Moved mouse to ({x}, {y})"
                else:
                    response_msg = "Usage: move mouse <x> <y>"
            elif detail.startswith("click"):
                parts = detail.replace("click", "").strip().split()
                if len(parts) >= 2:
                    r = self.hardware.click(int(parts[0]), int(parts[1]))
                    response_msg = f"Clicked at ({parts[0]}, {parts[1]})"
                else:
                    r = self.hardware.click()
                    pos = self.hardware.get_mouse_position()
                    response_msg = f"Clicked at current position"
            elif detail.startswith("right") or detail.startswith("right click"):
                r = self.hardware.right_click()
                response_msg = "Right clicked"
            elif detail.startswith("double") or detail.startswith("double click"):
                r = self.hardware.double_click()
                response_msg = "Double clicked"
            elif detail.startswith("type"):
                text = detail.replace("type", "", 1).strip().strip("\"'")
                r = self.hardware.type_text(text)
                response_msg = f"Typed {len(text)} characters"
            elif detail.startswith("press"):
                key = detail.replace("press", "", 1).strip()
                r = self.hardware.press_key(key)
                response_msg = f"Pressed key: {key}"
            elif detail.startswith("scroll"):
                parts = detail.replace("scroll", "").strip().split()
                clicks = int(parts[0]) if parts else 3
                r = self.hardware.scroll(clicks)
                response_msg = f"Scrolled {clicks} clicks"
            elif detail.startswith("screenshot") or detail.startswith("ss"):
                r = self.hardware.screenshot()
                response_msg = f"Screenshot saved: {r.get('path', '')}"
            elif detail.startswith("position") or detail.startswith("where"):
                pos = self.hardware.get_mouse_position()
                response_msg = f"Mouse position: ({pos.get('x')}, {pos.get('y')})"
            elif detail.startswith("focus"):
                title = detail.replace("focus", "", 1).strip()
                r = self.hardware.focus_window(title)
                response_msg = f"Focused window: {title}"
            elif detail.startswith("volume"):
                parts = detail.replace("volume", "").strip().split()
                if not parts:
                    v = self.hardware.get_volume()
                    if v.get("status") == "success":
                        response_msg = f"Volume: {v['percent']}% {'(muted)' if v.get('muted') else ''}"
                    else:
                        response_msg = v.get("message", "Volume unknown")
                elif parts[0] == "up":
                    r = self.hardware.volume_up()
                    response_msg = f"Volume up: {r.get('percent', '?')}%"
                elif parts[0] == "down":
                    r = self.hardware.volume_down()
                    response_msg = f"Volume down: {r.get('percent', '?')}%"
                elif parts[0] == "mute":
                    r = self.hardware.mute_audio()
                    response_msg = "Audio muted"
                elif parts[0] == "unmute":
                    r = self.hardware.unmute_audio()
                    response_msg = "Audio unmuted"
                else:
                    try:
                        level = int(parts[0]) / 100.0
                        r = self.hardware.set_volume(level)
                        response_msg = f"Volume set to {parts[0]}%"
                    except ValueError:
                        response_msg = "Usage: volume [up|down|mute|unmute|<percent>]"
            elif detail.startswith("speaker"):
                r = self.hardware.open_speaker_settings()
                response_msg = r.get("message", "Open speaker settings")
            elif detail.startswith("mixer"):
                r = self.hardware.open_volume_mixer()
                response_msg = r.get("message", "Open volume mixer")
            elif detail.startswith("sysinfo") or detail.startswith("system info"):
                r = self.hardware.get_system_info()
                if r.get("status") == "success":
                    info = r["info"]
                    response_msg = "System Info:\n"
                    for k, v in info.items():
                        response_msg += f"  {k}: {v}\n"
                else:
                    response_msg = r.get("message", "System info not available")
            elif detail.startswith("display") or detail.startswith("monitor"):
                r = self.hardware.get_display_info()
                if r.get("status") == "success":
                    response_msg = f"Displays: {r.get('count', 0)}\n"
                    for d in r.get("displays", []):
                        response_msg += f"  {d.get('width')}x{d.get('height')}\n"
                else:
                    response_msg = r.get("message", "Display info not available")
            else:
                response_msg = ("Available commands: move mouse <x> <y>, click [x y], "
                               "right click, double click, type <text>, press <key>, "
                               "scroll <clicks>, screenshot, position, focus <window>, "
                               "volume [up|down|mute|unmute|<percent>], speaker, mixer, "
                               "sysinfo, display")
        except Exception as exc:
            response_msg = f"Hardware error: {exc}"
        self._enqueue(lambda: self._append_chat("assistant", f"[Hardware] {response_msg}"))

    def _handle_skill_query(self, detail: str):
        """Query the skill system for domain knowledge."""
        if not self.skills:
            self._append_chat("meta", "[Skill System not available]")
            return
        detail = detail.strip()
        response_lines = []
        try:
            if "?" in detail or "what" in detail.lower() or "how" in detail.lower():
                skills = self.skills.search_skills(detail)
                if skills:
                    response_lines.append(f"Found relevant skills: {', '.join(skills[:5])}")
                    context = self.skills.get_context_for_task(detail)
                    if context:
                        response_lines.append("Context:\n" + context[:2000])
                else:
                    response_lines.append("No skills matched your query.")
            elif detail.lower() in ("list", "ls", "all", "loaded"):
                skill_list = self.skills.list_skills()
                response_lines.append(f"Loaded skills ({len(skill_list)}):")
                for s in skill_list:
                    response_lines.append(f"  - {s}")
            else:
                content = self.skills.get_skill_by_domain(detail)
                if content:
                    lines = content.split("\n")
                    response_lines.append(f"Skill: {detail}")
                    response_lines.append("\n".join(lines[:80]))
                else:
                    skills = self.skills.search_skills(detail)
                    if skills:
                        response_lines.append(f"Query '{detail}' matched: {', '.join(skills[:5])}")
                    else:
                        response_lines.append(f"No skill found for '{detail}'. Use 'list' to see available skills.")
        except Exception as exc:
            response_lines.append(f"Skill query error: {exc}")
        self._enqueue(lambda: self._append_chat("assistant", "\n".join(response_lines)))

    def _handle_ml(self, detail: str):
        """Handle ML tasks."""
        if not self.ml_engine:
            self._append_chat("meta", "[ML Engine not available]")
            return
        detail = detail.strip()
        response_msg = ""
        try:
            parts = detail.split()
            if not parts:
                response_msg = ("Usage: ML <category> <params>. Categories: regression, classify, cluster, "
                               "dimreduce, deep, timeseries, anomaly, ensemble, feateng, tune, evaluate, "
                               "crossval, automl, list")
            elif parts[0] == "list":
                cats = ["regression (13)", "classification (15)", "clustering (10)",
                        "dim reduction (8)", "ensemble (6)", "deep learning (3)",
                        "time series (7)", "anomaly detection (5)", "feature eng (12)",
                        "hyperparameter tuning (4)", "cross validation (6)"]
                response_msg = "ML Engine: 89 algorithms\n" + "\n".join(f"  - {c}" for c in cats)
            elif parts[0] == "auto" or parts[0] == "automl":
                response_msg = "AutoML: automatic algorithm selection."
                data_match = self._parse_ml_data(" ".join(parts[1:]))
                if data_match:
                    X, y = data_match
                    res = self.ml_engine.auto_ml(X, y)
                    response_msg = f"AutoML: {res.get('best_algorithm', 'N/A')} with CV score {res.get('best_score', 'N/A')}\n"
                    response_msg += res.get("report", "No report generated.")
            elif parts[0] == "regression" or parts[0] == "reg":
                algo = parts[1] if len(parts) > 1 else "linear"
                data = self._parse_ml_data(" ".join(parts[2:]))
                if data:
                    X, y = data
                    res = self.ml_engine.regression(algo, X, y)
                    response_msg = f"Regression ({algo}): {res.get('message', 'OK')}"
                    if "metrics" in res:
                        response_msg += f"\n{res['metrics']}"
                    if "code" in res:
                        response_msg += f"\n{res['code'][:500]}"
                else:
                    res = self.ml_engine.regression(algo, [[1],[2],[3]], [2,4,6])
                    response_msg = f"Regression demo ({algo}): {res.get('message', 'OK')}"
            elif parts[0] == "classify" or parts[0] == "class":
                algo = parts[1] if len(parts) > 1 else "knn"
                data = self._parse_ml_data(" ".join(parts[2:]))
                if data:
                    X, y = data
                    res = self.ml_engine.classify(algo, X, y)
                    response_msg = f"Classification ({algo}): {res.get('message', 'OK')}"
                else:
                    res = self.ml_engine.classify(algo, [[1],[2],[3],[4]], [0,0,1,1])
                    response_msg = f"Classification demo ({algo}): {res.get('message', 'OK')}"
            elif parts[0] == "cluster":
                algo = parts[1] if len(parts) > 1 else "kmeans"
                data = self._parse_ml_data(" ".join(parts[2:]), has_y=False)
                if data:
                    X = data
                    res = self.ml_engine.cluster(algo, X)
                    response_msg = f"Clustering ({algo}): {res.get('message', 'OK')}"
                else:
                    res = self.ml_engine.cluster(algo, [[1,2],[2,3],[8,9],[9,10]])
                    response_msg = f"Clustering demo ({algo}): {res.get('message', 'OK')}"
            elif parts[0] == "ts" or parts[0] == "timeseries":
                algo = parts[1] if len(parts) > 1 else "sma"
                import ast
                data_match = " ".join(parts[2:]).strip()
                response_msg = f"Time Series ({algo}): Use full dataset in tools. Running with sample data."
                res = self.ml_engine.time_series(algo, [10,12,15,14,18,20,22,25])
                response_msg = f"Time Series ({algo}): {res.get('message', 'OK')}"
            elif parts[0] == "anomaly":
                algo = parts[1] if len(parts) > 1 else "isolation_forest"
                res = self.ml_engine.detect_anomalies(algo, [[1],[2],[10],[3],[4],[100]])
                response_msg = f"Anomaly Detection ({algo}): {res.get('message', 'OK')}"
            elif parts[0] == "tune":
                response_msg = "Hyperparameter tuning: use gridsearch/randomsearch with full dataset."
            elif parts[0] == "evaluate":
                response_msg = "Model evaluation: use evaluate(y_true, y_pred, task_type)."
            else:
                response_msg = f"Unknown ML command: {parts[0]}. Use 'list' to see available categories."
        except Exception as exc:
            response_msg = f"ML Error: {exc}"
        self._enqueue(lambda: self._append_chat("assistant", f"[ML] {response_msg}"))

    def _parse_ml_data(self, text, has_y=True):
        """Parse simple inline data like X=[1,2,3] y=[2,4,6]."""
        import ast
        try:
            x_match = text.split("X=")[1].split("]")[0] + "]" if "X=" in text else None
            if x_match:
                X = ast.literal_eval(x_match)
                if has_y:
                    y_match = text.split("y=")[1].split("]")[0] + "]" if "y=" in text else None
                    if y_match:
                        y = ast.literal_eval(y_match)
                        return X, y
                return X
        except Exception:
            pass
        return None

    def _handle_iot(self, detail: str):
        """Handle IoT tasks."""
        if not self.iot_engine:
            self._append_chat("meta", "[IoT Engine not available]")
            return
        detail = detail.strip()
        response_msg = ""
        try:
            parts = detail.lower().split()
            if not parts:
                response_msg = ("Usage: IoT <type> <params>. Types: esp32, esp8266, micropython, "
                               "protocol, sensor, backend, pinout, architecture, config, list")
            elif parts[0] == "list":
                boards = ["esp32", "esp8266", "micropython"]
                protocols = ["mqtt", "http", "websocket", "coap", "ble", "lora", "i2c", "spi", "uart"]
                sensors = ["dht11", "dht22", "bme280", "hc-sr04", "pir", "bh1750", "ssd1306", "gps"]
                response_msg = (f"Boards: {', '.join(boards)}\n"
                               f"Protocols: {', '.join(protocols)}\n"
                               f"Sensors: {', '.join(sensors)}")
            elif parts[0] in ("esp32", "esp8266"):
                comps = [p for p in parts[1:] if p not in ("mqtt", "wifi", "http")]
                has_mqtt = "mqtt" in parts
                res = self.iot_engine.generate_esp_code(parts[0], comps or ["dht11"])
                response_msg = f"IoT Firmware ({parts[0]}):\n{res.get('result', '')[:2000]}"
            elif parts[0] == "micropython":
                comps = [p for p in parts[1:] if p not in ("mqtt", "wifi")]
                res = self.iot_engine.generate_micropython(parts[1] if len(parts) > 1 else "esp32", comps or ["dht11"])
                response_msg = f"MicroPython ({parts[1] if len(parts) > 1 else 'esp32'}):\n{res.get('result', '')[:2000]}"
            elif parts[0] == "protocol":
                proto = parts[1] if len(parts) > 1 else "mqtt"
                res = self.iot_engine.generate_protocol_code(proto, "client")
                response_msg = f"Protocol ({proto}):\n{res.get('result', '')[:2000]}"
            elif parts[0] == "sensor":
                sensor = parts[1] if len(parts) > 1 else "dht11"
                res = self.iot_engine.generate_sensor_code(sensor, "i2c")
                response_msg = f"Sensor ({sensor}):\n{res.get('result', '')[:2000]}"
            elif parts[0] == "backend":
                backend = parts[1] if len(parts) > 1 else "aws"
                res = self.iot_engine.generate_backend_code(backend, "mqtt")
                response_msg = f"Backend ({backend}):\n{res.get('result', '')[:2000]}"
            elif parts[0] == "pinout":
                comps = parts[1:] or ["dht11", "led"]
                res = self.iot_engine.generate_pinout(comps, "esp32")
                response_msg = f"Pinout (ESP32 + {', '.join(comps)}):\n{res.get('result', '')[:2000]}"
            elif parts[0] == "architecture" or parts[0] == "arch":
                use_case = parts[1] if len(parts) > 1 else "smart_home"
                res = self.iot_engine.generate_architecture(use_case, ["dht11", "led"])
                response_msg = f"Architecture ({use_case}):\n{res.get('result', '')[:2000]}"
            elif parts[0] == "config":
                device = parts[1] if len(parts) > 1 else "esp32"
                res = self.iot_engine.generate_config(device)
                response_msg = f"Config ({device}):\n{res.get('result', '')[:2000]}"
            else:
                response_msg = f"Unknown IoT command: {parts[0]}. Use 'list' to see available options."
        except Exception as exc:
            response_msg = f"IoT Error: {exc}"
        self._enqueue(lambda: self._append_chat("assistant", f"[IoT] {response_msg}"))

    def _handle_vlsi(self, detail: str):
        """Handle VLSI and embedded systems tasks."""
        if not self.vlsi_engine:
            self._append_chat("meta", "[VLSI Engine not available]")
            return
        detail = detail.strip()
        response_msg = ""
        try:
            parts = detail.lower().split()
            if not parts:
                response_msg = ("Usage: VLSI <type> <params>. Types: verilog, vhdl, systemverilog, "
                               "rtl, embedded, freertos, zephyr, assembly, testbench, fpga, soc, list")
            elif parts[0] == "list":
                caps = ["HDL: verilog, vhdl, systemverilog",
                        "RTL: adder, multiplier, counter, fsm, alu, ram, rom, fifo, cordic, fir/iir",
                        "Embedded: stm32, avr, pic, riscv, msp430",
                        "RTOS: freertos, zephyr, rtthread",
                        "Assembly: arm, avr, riscv, x86",
                        "Testbench: verilog, vhdl, systemverilog",
                        "FPGA: xilinx, intel, lattice",
                        "SoC: riscv, arm_cortex_m, custom"]
                response_msg = "VLSI Engine capabilities:\n" + "\n".join(f"  - {c}" for c in caps)
            elif parts[0] in ("verilog", "vhdl", "systemverilog", "sv"):
                module = parts[1] if len(parts) > 1 else "counter"
                width = 8
                for p in parts[2:]:
                    if p.startswith("width="):
                        width = int(p.split("=")[1])
                res = self.vlsi_engine.generate_hdl(parts[0], module, width=width)
                response_msg = f"HDL ({parts[0]} - {module}):\n{res.get('result', '')[:2000]}"
            elif parts[0] == "rtl":
                dt = parts[1] if len(parts) > 1 else "adder"
                width = 8
                for p in parts[2:]:
                    if p.startswith("width="):
                        width = int(p.split("=")[1])
                res = self.vlsi_engine.generate_rtl(dt, width=width)
                response_msg = f"RTL ({dt}):\n{res.get('result', '')[:2000]}"
            elif parts[0] == "embedded" or parts[0] == "emb":
                target = parts[1] if len(parts) > 1 else "stm32"
                peri = parts[2] if len(parts) > 2 else "gpio"
                res = self.vlsi_engine.generate_embedded_c(target, peri)
                response_msg = f"Embedded C ({target} - {peri}):\n{res.get('result', '')[:2000]}"
            elif parts[0] in ("freertos", "zephyr", "rtthread", "rtos"):
                rtos = parts[0]
                count = 2
                for p in parts[1:]:
                    if p.startswith("tasks="):
                        count = int(p.split("=")[1])
                task_names = [f"task{i}" for i in range(count)]
                res = self.vlsi_engine.generate_rtos(rtos, task_names)
                response_msg = f"RTOS ({rtos}):\n{res.get('result', '')[:2000]}"
            elif parts[0] in ("asm", "assembly"):
                arch = parts[1] if len(parts) > 1 else "arm"
                routine = parts[2] if len(parts) > 2 else "delay"
                res = self.vlsi_engine.generate_assembly(arch, routine)
                response_msg = f"Assembly ({arch} - {routine}):\n{res.get('result', '')[:2000]}"
            elif parts[0] == "testbench" or parts[0] == "tb":
                lang = parts[1] if len(parts) > 1 else "verilog"
                module = parts[2] if len(parts) > 2 else "counter"
                res = self.vlsi_engine.generate_testbench(lang, module)
                response_msg = f"Testbench ({lang} - {module}):\n{res.get('result', '')[:2000]}"
            elif parts[0] == "fpga":
                vendor = parts[1] if len(parts) > 1 else "xilinx"
                design = parts[2] if len(parts) > 2 else "top"
                res = self.vlsi_engine.generate_fpga_flow(vendor, design)
                response_msg = f"FPGA ({vendor} - {design}):\n{res.get('result', '')[:2000]}"
            elif parts[0] == "soc":
                soc_type = parts[1] if len(parts) > 1 else "riscv"
                comps = [p for p in parts[2:] if not p.startswith("width=")]
                width = 32
                for p in parts[2:]:
                    if p.startswith("width="):
                        width = int(p.split("=")[1])
                res = self.vlsi_engine.generate_soc(soc_type, comps or ["uart", "gpio"], width=width)
                response_msg = f"SoC ({soc_type}):\n{res.get('result', '')[:2000]}"
            elif parts[0] == "timing":
                freq = 100
                for p in parts[1:]:
                    if p.startswith("freq="):
                        freq = int(p.split("=")[1])
                res = self.vlsi_engine.analyze_timing("generic design", freq)
                response_msg = f"Timing Analysis ({freq}MHz):\n{res.get('result', '')[:2000]}"
            else:
                response_msg = f"Unknown VLSI command: {parts[0]}. Use 'list' to see available options."
        except Exception as exc:
            response_msg = f"VLSI Error: {exc}"
        self._enqueue(lambda: self._append_chat("assistant", f"[VLSI] {response_msg}"))

    def _handle_env(self, detail: str):
        if not self.dep_manager:
            self._append_chat("meta", "[Dependency Manager not available]")
            return
        detail = detail.strip().lower()
        response_msg = ""
        try:
            parts = detail.split()
            if not parts:
                response_msg = "Usage: Env <command>. Commands: create venv, install <pkg>, update <pkg>, downgrade <pkg> <ver>, migrate 3.11, check conflicts, analyze, list, ensure"
            elif parts[0] == "create" and "venv" in parts:
                path = parts[2] if len(parts) > 2 else "."
                r = self.dep_manager.create_venv(path)
                response_msg = r.get("message", "VenV created")
            elif parts[0] == "install":
                pkg = parts[1] if len(parts) > 1 else None
                if pkg:
                    ver = parts[2] if len(parts) > 2 and parts[2] not in ("upgrade", "--upgrade") else None
                    upgrade = "upgrade" in parts or "--upgrade" in parts
                    r = self.dep_manager.install_package(pkg, version=ver, upgrade=upgrade)
                    response_msg = r.get("message", f"Installed {pkg}")
                else:
                    response_msg = "Specify a package name"
            elif parts[0] == "update":
                pkg = parts[1] if len(parts) > 1 else None
                if pkg:
                    r = self.dep_manager.update_package(pkg)
                    response_msg = r.get("message", f"Updated {pkg}")
                else:
                    response_msg = "Specify a package name"
            elif parts[0] == "downgrade":
                pkg = parts[1] if len(parts) > 1 else None
                ver = parts[2] if len(parts) > 2 else None
                if pkg and ver:
                    r = self.dep_manager.downgrade_package(pkg, ver)
                    response_msg = r.get("message", f"Downgraded {pkg} to {ver}")
                else:
                    response_msg = "Usage: downgrade <package> <version>"
            elif parts[0] == "migrate" and "3.11" in detail:
                r = self.dep_manager.migrate_to_python311()
                response_msg = r.get("message", "Migration complete")
                if r.get("result"):
                    response_msg += "\n" + str(r["result"])[:500]
            elif "conflict" in parts or parts[0] == "check":
                pkgs = parts[1:] if len(parts) > 1 else None
                r = self.dep_manager.check_conflicts(pkgs)
                response_msg = r.get("message", "Conflict check done")
                if r.get("result"):
                    response_msg += "\n" + str(r["result"])[:500]
            elif parts[0] == "analyze":
                path = parts[1] if len(parts) > 1 else "."
                r = self.dep_manager.analyze_project(path)
                response_msg = r.get("message", "Analysis done")
                if r.get("result"):
                    res = r["result"]
                    response_msg += f"\nFiles: {res.get('total_files', 'N/A')}, LOC: {res.get('total_loc', 'N/A')}, Dependencies: {res.get('dependencies', 'N/A')}"
            elif parts[0] == "list":
                r = self.dep_manager.list_installed()
                if r.get("result"):
                    pkgs = r["result"][:30]
                    response_msg = f"Installed ({len(pkgs)} shown):\n" + "\n".join(f"  {p['name']}=={p['version']}" for p in pkgs)
                else:
                    response_msg = r.get("message", "No packages listed")
            elif parts[0] == "ensure":
                r = self.dep_manager.ensure_tom_dependencies()
                response_msg = r.get("message", "Dependencies verified")
            else:
                response_msg = f"Unknown env command: {parts[0]}. Use 'list' for available commands."
        except Exception as exc:
            response_msg = f"Env Error: {exc}"
        self._enqueue(lambda: self._append_chat("assistant", f"[Env] {response_msg}"))

    def _handle_news(self, detail: str):
        if not self.news_agent:
            self._append_chat("meta", "[News Agent not available]")
            return
        detail = detail.strip().lower()
        response_msg = ""
        try:
            parts = detail.split()
            if not parts:
                response_msg = "Usage: News <command>. Commands: daily briefing, tech roundup, world events, search <query>, trending, update knowledge"
            elif "daily" in detail or "briefing" in detail:
                r = self.news_agent.daily_briefing()
                response_msg = r.get("message", "Daily briefing")
                if r.get("result"):
                    result = r["result"]
                    for category, articles in result.items():
                        if isinstance(articles, list):
                            response_msg += f"\n\n{category.upper()}:"
                            for a in articles[:3]:
                                title = a.get("title", "N/A") if isinstance(a, dict) else str(a)[:80]
                                response_msg += f"\n  - {title}"
            elif "tech" in detail:
                r = self.news_agent.technology_roundup()
                response_msg = r.get("message", "Tech roundup")
                if r.get("result"):
                    for k, v in r["result"].items():
                        if isinstance(v, list):
                            response_msg += f"\n\n{k.upper()}:"
                            for a in v[:3]:
                                response_msg += f"\n  - {a.get('title', str(a)[:80]) if isinstance(a, dict) else str(a)[:80]}"
            elif "world" in detail:
                r = self.news_agent.world_events()
                response_msg = r.get("message", "World events")
                if r.get("result"):
                    for k, v in r["result"].items():
                        if isinstance(v, list):
                            response_msg += f"\n\n{k.upper()}:"
                            for a in v[:3]:
                                response_msg += f"\n  - {a.get('title', str(a)[:80]) if isinstance(a, dict) else str(a)[:80]}"
            elif parts[0] == "search":
                query = " ".join(parts[1:])
                if query:
                    r = self.news_agent.search_news(query)
                    response_msg = r.get("message", f"Search: {query}")
                    if r.get("result"):
                        for a in r["result"][:5]:
                            title = a.get("title", str(a)[:80]) if isinstance(a, dict) else str(a)[:80]
                            response_msg += f"\n  - {title}"
                else:
                    response_msg = "Specify a search query"
            elif "trending" in detail:
                r = self.news_agent.get_trending_topics()
                response_msg = r.get("message", "Trending")
                if r.get("result"):
                    for topic, count in list(r["result"].items())[:10]:
                        response_msg += f"\n  - {topic}"
            elif "update" in detail:
                r = self.news_agent.update_knowledge_base()
                response_msg = r.get("message", "Knowledge base updated")
            else:
                response_msg = f"Unknown news command: {parts[0]}"
        except Exception as exc:
            response_msg = f"News Error: {exc}"
        self._enqueue(lambda: self._append_chat("assistant", f"[News] {response_msg}"))

    def _handle_voice_enhanced(self, detail: str):
        if not self.voice_enhanced:
            self._append_chat("meta", "[Voice Enhanced not available]")
            return
        detail = detail.strip()
        response_msg = ""
        try:
            parts = detail.lower().split()
            if not parts:
                response_msg = "Usage: Voice+ <command>. Commands: analyze emotion text:<text>, start conversation, assess, speak <text>"
            if "analyze" in parts and "emotion" in parts:
                text = detail.split("text:")[1].strip() if "text:" in detail else " ".join(parts[2:])
                if text:
                    r = self.voice_enhanced.detect_emotion(text=text)
                    response_msg = r.get("message", "Emotion analysis")
                    if r.get("result"):
                        emotion = r["result"].get("emotion", "N/A")
                        confidence = r["result"].get("confidence", "N/A")
                        response_msg += f"\nEmotion: {emotion} (confidence: {confidence})"
                else:
                    response_msg = "Provide text to analyze"
            elif "assess" in parts or "psychiatric" in detail:
                text = detail.split(":")[1].strip() if ":" in detail else " ".join(parts[1:])
                if text:
                    r = self.voice_enhanced.psychiatric_assessment([{"text": text, "speaker": "user"}])
                    response_msg = r.get("message", "Assessment")
                    if r.get("result"):
                        for k, v in r["result"].items():
                            response_msg += f"\n{k}: {v}"
                else:
                    response_msg = "Provide conversation text for assessment"
            elif "speak" in parts or "say" in parts:
                text = detail.split("speak")[-1].strip() if "speak" in detail else detail.split("say")[-1].strip()
                if text:
                    r = self.voice_enhanced.speak_text(text)
                    response_msg = r.get("message", f"Speaking: {text[:50]}")
                else:
                    response_msg = "Provide text to speak"
            elif "empathy" in detail or "empathetic" in detail:
                text = detail.split(":")[1].strip() if ":" in detail else detail.split(None, 1)[1] if len(parts) > 1 else ""
                if text:
                    emotion = {"emotion": "sad", "confidence": 0.8}
                    response_text = self.voice_enhanced.generate_empathetic_response(text, emotion)
                    response_msg = f"Empathetic response: {response_text[:500]}"
                else:
                    response_msg = "Provide text for empathetic response"
            elif "start" in detail or "converse" in detail or "conversation" in detail:
                r = self.voice_enhanced.start_conversation_mode()
                response_msg = r.get("message", "Conversation mode started")
            elif "stop" in detail:
                r = self.voice_enhanced.stop_conversation_mode()
                response_msg = r.get("message", "Conversation mode stopped")
                if r.get("result"):
                    response_msg += f"\nSummary: {str(r['result'])[:200]}"
            else:
                response_msg = f"Unknown Voice+ command: {parts[0]}"
        except Exception as exc:
            response_msg = f"Voice+ Error: {exc}"
        self._enqueue(lambda: self._append_chat("assistant", f"[Voice+] {response_msg}"))

    def _init_creative_tools(self):
        """Initialize Game Dev, Blender, Auto-Update tools."""
        try:
            if GameDevEngine:
                self.game_dev = GameDevEngine()
                self._append_chat("meta", "[Game Dev Engine: PyGame, Unity, Godot project scaffolding]")
        except Exception as exc:
            self._append_chat("meta", f"[Game Dev unavailable: {exc}]")

        try:
            if BlenderControl:
                self.blender = BlenderControl()
                avail = "found" if self.blender.is_available() else "not found"
                path = self.blender.get_blender_path()
                self._append_chat("meta", f"[Blender Control: {avail} at {path[:60]}]")
        except Exception as exc:
            self._append_chat("meta", f"[Blender unavailable: {exc}]")

        try:
            if AutoUpdate:
                self.auto_update = AutoUpdate()
                self._append_chat("meta", "[Auto-Update: git, pip, knowledge scraper]")
        except Exception as exc:
            self._append_chat("meta", f"[Auto-Update unavailable: {exc}]")

    # ── Creative Tool Handlers ───────────────────────────────────────────

    def _handle_game_dev(self, detail: str):
        if not self.game_dev:
            self._append_chat("meta", "[Game Dev Engine not available]")
            return
        detail = detail.strip().lower()
        response_msg = ""
        try:
            parts = detail.split()
            if not parts:
                response_msg = ("Usage: Game dev <command>. Commands:\n"
                               "  scaffold pygame <name> [genre] — Create PyGame project\n"
                               "  script <engine> <task> — Generate game script snippet\n"
                               "  unity <name> — Scaffold Unity project structure\n"
                               "  engines — List supported game engines\n"
                               "  installed — Check what's installed on system")
            elif parts[0] == "scaffold" and parts[1] == "pygame":
                name = parts[2] if len(parts) > 2 else "my_game"
                genre = parts[3] if len(parts) > 3 else "platformer"
                r = self.game_dev.scaffold_pygame(name, genre)
                response_msg = r.get("message", "Game scaffolded")
                if r.get("path"):
                    response_msg += f"\nPath: {r['path']}"
                    response_msg += f"\nFiles: {', '.join(r.get('files', []))}"
            elif parts[0] == "script":
                engine = parts[1] if len(parts) > 1 else "pygame"
                task = " ".join(parts[2:]) or "game logic"
                r = self.game_dev.generate_script(engine, task)
                if r.get("status") == "success":
                    response_msg = f"Generated {engine} script:\n{r.get('code', '')[:2000]}"
                else:
                    response_msg = r.get("message", "Script generation failed")
            elif parts[0] == "unity":
                name = parts[1] if len(parts) > 1 else "MyProject"
                r = self.game_dev.build_unity_project(name)
                response_msg = r.get("message", "Unity project created")
                if r.get("path"):
                    response_msg += f"\nPath: {r['path']}"
            elif parts[0] == "engines":
                engines = self.game_dev.list_engines()
                response_msg = "Supported game engines:\n" + "\n".join(f"  - {e} ({l})" for e, l in engines.items())
            elif parts[0] == "installed":
                installed = self.game_dev.detect_installed_engines()
                response_msg = "Detected on system:\n" + "\n".join(f"  - {e}: {s}" for e, s in installed.items())
            else:
                response_msg = f"Unknown game dev command: {parts[0]}. Type 'game dev' for help."
        except Exception as exc:
            response_msg = f"Game Dev Error: {exc}"
        self._enqueue(lambda: self._append_chat("assistant", f"[Game Dev] {response_msg}"))

    def _handle_blender(self, detail: str):
        if not self.blender:
            self._append_chat("meta", "[Blender Control not available]")
            return
        detail = detail.strip().lower()
        response_msg = ""
        try:
            parts = detail.split()
            if not parts:
                caps = self.blender.list_capabilities()
                response_msg = "Blender commands:\n" + "\n".join(f"  {k}: {v}" for k, v in caps.items())
                response_msg += "\n\nOr: run <script text> to execute a custom script"
                response_msg += f"\nBlender path: {self.blender.get_blender_path()}"
                response_msg += f"\nDirect mode: {self.blender.is_available()}"
            elif parts[0] == "run":
                script = detail[len("run "):].strip() if detail.startswith("run ") else ""
                if script:
                    r = self.blender.execute_script(script)
                    response_msg = r.get("message", "Blender script executed")
                else:
                    response_msg = "Provide a Blender Python script to execute"
            elif parts[0] == "list" or parts[0] == "capabilities":
                caps = self.blender.list_capabilities()
                response_msg = "Blender capabilities:\n" + "\n".join(f"  {k}: {v}" for k, v in caps.items())
            else:
                script = self.blender.generate_script(detail)
                r = self.blender.execute_script(script)
                if r.get("status") == "success":
                    response_msg = f"Blender: {r.get('message', 'Done')}"
                    if r.get("script_preview"):
                        response_msg += f"\nScript preview:\n{r['script_preview']}"
                else:
                    script_preview = script[:300]
                    response_msg = f"Generated script (execute in Blender):\n{script_preview}..."
        except Exception as exc:
            response_msg = f"Blender Error: {exc}"
        self._enqueue(lambda: self._append_chat("assistant", f"[Blender] {response_msg}"))

    def _handle_auto_update(self, detail: str):
        if not self.auto_update:
            self._append_chat("meta", "[Auto-Update not available]")
            return
        detail = detail.strip().lower()
        response_msg = ""
        try:
            parts = detail.split()
            if not parts or parts[0] == "help":
                response_msg = ("Auto-Update commands:\n"
                               "  check — Check git for updates\n"
                               "  pull — Pull latest from git\n"
                               "  pip — Update all pip packages\n"
                               "  full — Full update (git + pip + knowledge)\n"
                               "  research <topic> — Scrape web for knowledge\n"
                               "  trending — Fetch trending GitHub repos\n"
                               "  history — Show update history")
            elif parts[0] == "check":
                r = self.auto_update.check_git_updates()
                if r.get("status") == "updates_available":
                    response_msg = f"Updates available: {r.get('count', 0)} changes"
                elif r.get("status") == "up_to_date":
                    response_msg = "Git repo is up to date"
                else:
                    response_msg = r.get("message", "Git check completed")
            elif parts[0] == "pull":
                r = self.auto_update.pull_updates()
                response_msg = r.get("output", r.get("message", "Git pull done"))
                if r.get("error"):
                    response_msg += f"\nErrors: {r['error']}"
            elif parts[0] == "pip":
                r = self.auto_update.update_pip_packages()
                response_msg = r.get("message", "Pip update done")
            elif parts[0] == "full":
                response_msg = "Running full update... (git + pip + knowledge)"
                r = self.auto_update.full_update()
                response_msg = ""
                for k, v in r.items():
                    response_msg += f"\n[{k}] {v.get('message', v.get('status', 'done'))}"
            elif parts[0] == "research":
                topic = " ".join(parts[1:]) if len(parts) > 1 else "Python programming"
                r = self.auto_update.auto_research(topic)
                response_msg = r.get("message", f"Researched '{topic}'")
                if r.get("results"):
                    for res in r["results"][:3]:
                        response_msg += f"\n\nQuery: {res.get('query', '')}"
                        for snip in res.get("snippets", [])[:2]:
                            response_msg += f"\n  - {snip[:200]}"
            elif parts[0] == "trending":
                r = self.auto_update.fetch_trending_repos()
                if r.get("status") == "success":
                    response_msg = "Trending GitHub repos:\n"
                    for repo in r.get("repos", []):
                        response_msg += f"\n  ★ {repo['stars']} {repo['name']}"
                        if repo.get("description"):
                            response_msg += f"\n    {repo['description']}"
                else:
                    response_msg = r.get("message", "Failed to fetch trending")
            elif parts[0] == "history":
                history = self.auto_update.get_update_history()
                if history:
                    response_msg = f"Last {len(history)} updates:\n"
                    for h in history[-5:]:
                        ts = h.get("timestamp", "?")[:19]
                        response_msg += f"\n  [{ts}] {str(h.get('result', {}).get('git', {}).get('status', 'done'))}"
                else:
                    response_msg = "No update history yet"
            else:
                response_msg = f"Unknown auto-update command: {parts[0]}. Type 'auto-update help' for commands."
        except Exception as exc:
            response_msg = f"Auto-Update Error: {exc}"
        self._enqueue(lambda: self._append_chat("assistant", f"[Auto-Update] {response_msg}"))

    def _bind_keyboard_shortcuts(self):
        self.root.bind("<Control-Return>", lambda e: self.send_message())
        self.root.bind("<Control-v>", lambda e: self._toggle_voice_mode())
        self.root.bind("<Control-d>", lambda e: self._switch_view("dashboard"))
        self.root.bind("<Control-c>", lambda e: self._switch_view("chat"))
        self.root.bind("<Control-s>", lambda e: self._switch_view("system"))
        self.root.bind("<Control-f>", lambda e: self._switch_view("files"))
        self.root.bind("<Escape>", lambda e: self.input_entry.focus_set() if hasattr(self, 'input_entry') else None)

    def _startup(self):
        self._enqueue(self._set_status, "Loading modules...")
        try:
            from tools.voice_tools import VoiceTools
            self.voice = VoiceTools()
        except Exception:
            self.voice = None

        try:
            from agent import TomAgent as _TomAgent
            self._TomAgent = _TomAgent
        except Exception as exc:
            self._enqueue(self._set_status, "Import error")
            self._enqueue(self._append_chat, "meta", f"Failed to import TOM agent: {exc}")
            return

        self._enqueue(self._set_status, "Checking Ollama...")
        available = self._ollama_available()
        if not available:
            self._enqueue(self._append_chat, "meta", "Ollama not reachable. Starting ollama serve...")
            self._start_ollama_server()
            for _ in range(20):
                if self._ollama_available():
                    available = True
                    break
                time.sleep(0.5)

        if not available:
            self._enqueue(self._append_chat, "meta", "Could not auto-start Ollama. Start it manually.")
        else:
            self._enqueue(self._append_chat, "meta", "Ollama is ready.")

        self._enqueue(self._set_status, "Initializing TOM with Gemma 4...")
        try:
            # Check required Ollama models exist before initializing
            try:
                model_req = Request("http://localhost:11434/api/tags", method="GET")
                with urlopen(model_req, timeout=5) as resp:
                    tags = json.loads(resp.read().decode())
                    installed = [m["name"] for m in tags.get("models", [])]
                    required = [os.environ.get("OLLAMA_MODEL", "gemma4:latest"),
                                os.environ.get("OLLAMA_FAST_MODEL", "qwen2.5-coder:7b-instruct"),
                                os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")]
                    missing = [m for m in required if m not in installed]
                    if missing:
                        self._enqueue(self._append_chat, "meta",
                            f"Missing Ollama models: {', '.join(missing)}. "
                            f"Run: ollama pull {' '.join(missing)}")
            except Exception:
                pass

            from agent import set_progress_callback
            set_progress_callback(self._on_agent_progress)
            self.agent = self._TomAgent()
            self.agent_ready = True
            self._enqueue(self._init_web_automation)
            self._enqueue(self._init_orchestrator)
            self._enqueue(self._init_v3_tools)
            self._enqueue(self._init_creative_tools)
            self._enqueue(self._set_status, "Ready")
            self._enqueue(self._update_statusbar, "Ready — TOM is online",
                          os.environ.get("OLLAMA_MODEL", "gemma4"), True)
            self._enqueue(self._update_voice_and_dashboard_state)
            self._enqueue(self._fetch_ollama_models)
            self._enqueue(self._append_chat, "assistant",
                "Hi, I am TOM \u2014 powered by Gemma 4. I can create documents, analyze data, send emails, research the web, hold voice conversations, debug web apps, run security checks, and deploy multi-agent tasks. I also have deep expertise in Game Development (Unity/Unreal/Godot/PyGame), 3D & CGI production (Blender/ZBrush/Substance/Houdini), and Cybersecurity (pentesting, reverse engineering, exploit dev, forensics, cloud security). What would you like me to do?")
        except Exception as exc:
            import traceback as _tb
            exc_detail = "".join(_tb.format_exception_only(type(exc), exc)).strip()
            self._enqueue(self._set_status, "Init error")
            self._enqueue(self._append_chat, "meta", f"Failed to initialize TOM: {exc_detail}")

    def _update_voice_and_dashboard_state(self):
        if self.voice:
            status = self.voice.status()
            self.voice_mode_enabled = bool(status.get("voice_input_enabled") or status.get("voice_output_enabled"))
            if self.voice_mode_enabled:
                self.voice_btn.configure(text="  \u266a  Voice: ON", bg=C["blue"], fg="#ffffff")
            else:
                self.voice_btn.configure(text="  \u266a  Voice Mode", bg=C["surface2"], fg=C["text"])
        if hasattr(self, "run_btn"):
            self.run_btn.configure(text=f"  \u25b6  Run {self.agent_profiles[self.active_agent_key]['label']}")
        self._refresh_dashboard()

    def _ollama_available(self) -> bool:
        try:
            req = Request("http://localhost:11434/api/tags", method="GET")
            with urlopen(req, timeout=2):
                return True
        except (URLError, Exception):
            return False

    def _run_async_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _start_ollama_server(self):
        try:
            kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "stdin": subprocess.DEVNULL}
            if os.name == "nt":
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            subprocess.Popen(["ollama", "serve"], **kwargs)
        except Exception as exc:
            self._enqueue(self._append_chat, "meta", f"Unable to start Ollama: {exc}")

    def _fetch_ollama_models(self):
        """Query Ollama API for all installed models and populate the model dropdown."""
        try:
            req = Request("http://localhost:11434/api/tags", method="GET")
            with urlopen(req, timeout=5) as resp:
                tags = json.loads(resp.read().decode())
                models = [m["name"] for m in tags.get("models", [])]
                if not models:
                    return
                current = self.model_var.get()
                # Keep current selection if it's still in the list, else default to first
                if current not in models:
                    current = models[0]
                # Rebuild OptionMenu choices
                self._model_names = models
                menu = self.model_menu["menu"]
                menu.delete(0, "end")
                for name in models:
                    menu.add_command(label=name,
                                     command=lambda v=name: self._on_model_change(v))
                self.model_var.set(current)
        except Exception:
            pass  # Ollama may not be available yet; the dropdown keeps its default

    def _on_model_change(self, model_name: str):
        """Called when the user selects a different model from the dropdown."""
        self.model_var.set(model_name)
        if hasattr(self, "agent") and self.agent_ready:
            try:
                # Update the environment and the agent's LLM in-place
                os.environ["OLLAMA_MODEL"] = model_name
                if hasattr(self.agent, "switch_model"):
                    self.agent.switch_model(model_name)
                    self._append_chat("meta", f"Switched model to {model_name}")
                else:
                    self._append_chat("meta",
                        f"Model preference set to {model_name}. "
                        "Restart TOM to apply if switch_model is not available.")
            except Exception as exc:
                self._append_chat("meta", f"Model switch error: {exc}")
        else:
            # Agent not ready yet — update env so it picks up the selection on init
            os.environ["OLLAMA_MODEL"] = model_name

    # ── Attachment handlers ─────────────────────────────────────────────
    def _attach_file(self):
        path = filedialog.askopenfilename(title="Attach File",
            filetypes=[("All files", "*.*"), ("PDF", "*.pdf"), ("Code", "*.py;*.js;*.ts;*.html"),
                       ("Documents", "*.txt;*.md;*.csv;*.json")])
        if path:
            self._attachments.append(("file", path))
            self._update_attach_display()

    def _attach_image(self):
        path = filedialog.askopenfilename(title="Attach Image",
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp")])
        if path:
            self._attachments.append(("image", path))
            self._update_attach_display()

    def _open_camera(self):
        try:
            import cv2
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not cap.isOpened():
                self._append_chat("system", "Camera not available. Check webcam connection.")
                return
            ret, frame = cap.read()
            cap.release()
            if ret:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"camera_capture_{timestamp}.png"
                filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
                cv2.imwrite(filepath, frame)
                self._attachments.append(("image", filepath))
                self._update_attach_display()
                self._append_chat("system", f"\U0001F4F7 Photo captured from camera")
            else:
                self._append_chat("system", "Failed to capture image from camera.")
        except ImportError:
            self._append_chat("system", "OpenCV not installed. Install with: pip install opencv-python")
        except Exception as e:
            self._append_chat("system", f"Camera error: {e}")

    def _attach_link(self):
        win = tk.Toplevel(self.root)
        win.title("Attach Web Link")
        win.configure(bg=C["bg"])
        win.geometry("520x200")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        frame = tk.Frame(win, bg=C["surface"], padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Enter URL to analyze:", bg=C["surface"], fg=C["text"],
            font=("Segoe UI", 12, "bold")).pack(anchor="w")

        url_var = tk.StringVar()
        entry = tk.Entry(frame, textvariable=url_var, bg=C["surface2"], fg=C["text"],
            insertbackground=C["text"], relief="flat", bd=0, font=("Segoe UI", 11))
        entry.pack(fill="x", ipady=8, pady=(8, 12))
        entry.focus_set()
        entry.bind("<Return>", lambda e: analyze_btn.invoke())

        btn_frame = tk.Frame(frame, bg=C["surface"])
        btn_frame.pack(fill="x")

        def do_analyze():
            url = url_var.get().strip()
            if not url:
                return
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            self._attachments.append(("link", url))
            self._update_attach_display()
            win.destroy()
            # Auto-run web analysis
            self._on_web_link_analyze(url)

        def open_direct():
            url = url_var.get().strip()
            if not url:
                return
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            try:
                import webbrowser
                webbrowser.open(url)
            except Exception:
                pass

        analyze_btn = tk.Button(btn_frame, text="\U0001F50D Analyze Page", command=do_analyze,
            bg=C["blue"], fg="#ffffff", activebackground="#2563eb", activeforeground="#ffffff",
            relief="flat", bd=0, padx=16, pady=8, font=("Segoe UI", 10, "bold"), cursor="hand2")
        analyze_btn.pack(side="left", padx=(0, 8))

        open_btn = tk.Button(btn_frame, text="\U0001F517 Open in Browser", command=open_direct,
            bg=C["surface2"], fg=C["text2"], activebackground=C["border2"], activeforeground=C["text"],
            relief="flat", bd=0, padx=16, pady=8, font=("Segoe UI", 10, "bold"), cursor="hand2")
        open_btn.pack(side="left")

        cancel_btn = tk.Button(btn_frame, text="Cancel", command=win.destroy,
            bg=C["surface2"], fg=C["muted"], activebackground=C["border2"], activeforeground=C["text"],
            relief="flat", bd=0, padx=16, pady=8, font=("Segoe UI", 10), cursor="hand2")
        cancel_btn.pack(side="right")

    def _clear_attachments(self):
        # Remove temp camera captures
        for atype, apath in self._attachments:
            if atype == "image" and "camera_capture" in os.path.basename(apath):
                try:
                    os.remove(apath)
                except Exception:
                    pass
        self._attachments.clear()
        self.attach_display.pack_forget()

    def _update_attach_display(self):
        if not self._attachments:
            self.attach_display.pack_forget()
            return
        self.attach_display.pack(fill="x", pady=(0, 4))
        for w in self.attach_display.winfo_children():
            if w != self.attach_label:
                w.destroy()

        # Show image thumbnails inline in the attachment bar
        thumb_frame = tk.Frame(self.attach_display, bg=C["surface2"])
        thumb_frame.pack(side="left", padx=(8, 0), pady=4)

        labels = []
        for atype, apath in self._attachments:
            name = os.path.basename(apath) if atype != "link" else apath[:40] + ("..." if len(apath) > 40 else "")

            if atype == "image":
                try:
                    from PIL import Image as PILImg, ImageTk as PILImageTk
                    pil = PILImg.open(apath).convert("RGB")
                    pil.thumbnail((48, 48), PILImg.LANCZOS)
                    tk_thumb = PILImageTk.PhotoImage(pil)
                    thumb_lbl = tk.Label(thumb_frame, image=tk_thumb, bg=C["surface2"],
                                         bd=1, relief="solid", cursor="hand2")
                    thumb_lbl.image = tk_thumb
                    thumb_lbl.pack(side="left", padx=2)
                    thumb_lbl.bind("<Button-1>", lambda e, p=apath: os.startfile(p))
                except Exception:
                    pass
                labels.append(f"\U0001F5BC {name}")
            else:
                icon = {"file": "\U0001F4C4", "link": "\U0001F517"}.get(atype, "\U0001F4C4")
                labels.append(f"{icon} {name}")

        total = len(self._attachments)
        self.attach_label.config(
            text=f"\U0001F4CE {total} attachment{'s' if total != 1 else ''}: " + "  |  ".join(labels))

    def _on_web_link_analyze(self, url):
        """Full web page analysis: grab title, text, meta, links, tags, detect technologies."""
        self._append_chat("meta", f"\U0001F50D Analyzing page: {url}")
        self.root.update()
        result_lines = []
        try:
            import requests
            from bs4 import BeautifulSoup
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36"
            }
            resp = requests.get(url, headers=headers, timeout=20)
            resp.encoding = resp.apparent_encoding or "utf-8"
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            result_lines.append(f"**URL:** {url}")
            result_lines.append(f"**Status:** {resp.status_code}")
            result_lines.append(f"**Size:** {len(html):,} chars")
            result_lines.append(f"**Encoding:** {resp.encoding}")

            # Title
            title = soup.title.string.strip() if soup.title and soup.title.string else "N/A"
            result_lines.append(f"\n**Title:** {title}")

            # Meta description
            meta_desc = ""
            meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
            if meta and meta.get("content"):
                meta_desc = meta["content"].strip()
            if meta_desc:
                result_lines.append(f"**Description:** {meta_desc[:200]}")

            # Headings structure
            headings = []
            for tag in ["h1", "h2", "h3"]:
                for h in soup.find_all(tag)[:8]:
                    text = h.get_text(strip=True)
                    if text:
                        headings.append(f"  {tag.upper()}: {text[:100]}")
            if headings:
                result_lines.append(f"\n**Heading Structure:**")
                result_lines.extend(headings[:12])

            # All text (first 2000 chars)
            all_text = soup.get_text(separator=" ", strip=True)
            all_text = " ".join(all_text.split())
            result_lines.append(f"\n**Page Text (first 1500 chars):**")
            result_lines.append(all_text[:1500])

            # Links count
            links = soup.find_all("a", href=True)
            internal = [l for l in links if l["href"].startswith(("/", "#")) or url.split("//")[1].split("/")[0] in l["href"]]
            external = [l for l in links if l not in internal and l["href"].startswith("http")]
            result_lines.append(f"\n**Links:** {len(links)} total, {len(internal)} internal, {len(external)} external")

            # Images
            images = soup.find_all("img")
            img_with_alt = [img for img in images if img.get("alt")]
            result_lines.append(f"**Images:** {len(images)} total, {len(img_with_alt)} with alt text")

            # Scripts / CSS
            scripts = soup.find_all("script", src=True)
            css = soup.find_all("link", rel="stylesheet")
            result_lines.append(f"**Scripts:** {len(scripts)} | **Stylesheets:** {len(css)}")

            # Detect tech stack
            techs = []
            if soup.find("meta", attrs={"name": "generator"}):
                gen = soup.find("meta", attrs={"name": "generator"})
                techs.append(f"Generator: {gen.get('content', 'N/A')}")
            if soup.find_all("script", {"src": lambda v: v and "react" in v.lower()}):
                techs.append("React")
            if soup.find_all("script", {"src": lambda v: v and "angular" in v.lower()}):
                techs.append("Angular")
            if soup.find_all("script", {"src": lambda v: v and "vue" in v.lower()}):
                techs.append("Vue.js")
            if soup.find_all("script", {"src": lambda v: v and "jquery" in v.lower()}):
                techs.append("jQuery")
            if soup.find("meta", attrs={"name": "viewport"}):
                techs.append("Responsive/Mobile-ready")
            if techs:
                result_lines.append(f"\n**Detected Technologies:** {', '.join(techs)}")

            # OG / social tags
            og_tags = soup.find_all("meta", property=lambda v: v and v.startswith("og:"))
            if og_tags:
                result_lines.append(f"\n**Open Graph Tags:** {len(og_tags)} found")
                for og in og_tags[:5]:
                    result_lines.append(f"  {og.get('property', '?')} = {og.get('content', '?')[:80]}")

            # Form detection
            forms = soup.find_all("form")
            if forms:
                result_lines.append(f"\n**Forms:** {len(forms)} detected")

        except ImportError:
            result_lines.append(f"\nTo enable full page analysis, install: pip install requests beautifulsoup4")
            # Fallback: basic fetch
            try:
                import urllib.request
                with urllib.request.urlopen(url, timeout=10) as f:
                    content = f.read().decode("utf-8", errors="replace")
                    result_lines.append(f"\n**Basic Fetch:** {len(content)} chars retrieved (install beautifulsoup4 for full analysis)")
            except Exception as e2:
                result_lines.append(f"\n**Basic fetch failed:** {e2}")
        except Exception as e:
            result_lines.append(f"\n**Analysis error:** {e}")

        result_text = "\n".join(result_lines)
        self._append_chat("assistant", result_text)
        self._on_web_link_analyze_callback(url, result_text)

    def _on_web_link_analyze_callback(self, url, analysis_text):
        """Forward analysis result to the agent for further processing."""
        if hasattr(self, "agent") and self.agent_ready and hasattr(self.agent, "process_message"):
            try:
                summary_prompt = (
                    f"Here's a web page analysis for {url}. Summarize the key points, "
                    f"extract the main content, and identify what this page is about:\n\n{analysis_text[:4000]}"
                )
                asyncio.run_coroutine_threadsafe(
                    self.agent.process_message(summary_prompt), self._loop
                )
            except Exception:
                pass

    def _on_close(self):
        try:
            self._loop.call_soon_threadsafe(self._loop.stop)
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    TomDesktopApp(root)
    # Center the window on the primary screen for a cleaner first launch.
    try:
        root.update_idletasks()
        _w, _h = 1420, 880
        _x = max(0, (root.winfo_screenwidth() - _w) // 2)
        _y = max(0, (root.winfo_screenheight() - _h) // 2)
        root.geometry(f"{_w}x{_h}+{_x}+{_y}")
    except Exception:
        pass
    root.mainloop()

if __name__ == "__main__":
    main()
