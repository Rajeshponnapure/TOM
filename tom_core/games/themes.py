"""Colour themes for the games TOM makes.

Every role has its own clearly different colour (checked in tests), for two reasons: the player can tell
things apart at a glance, and TOM's autopilot finds the player, the target and the hazards on screen by
colour when it plays the game.
"""
from __future__ import annotations

import re
from typing import Dict, Tuple

RGB = Tuple[int, int, int]
ROLES = ("background", "player", "player_accent", "target", "hazard", "ground", "accent", "text")

THEMES: Dict[str, Dict[str, RGB]] = {
    "classic": {"background": (20, 20, 28), "player": (70, 200, 255), "player_accent": (30, 110, 150),
                "target": (255, 214, 60), "hazard": (235, 64, 64), "ground": (80, 175, 90),
                "accent": (160, 100, 235), "text": (240, 240, 240)},
    "neon": {"background": (10, 6, 22), "player": (0, 255, 190), "player_accent": (0, 130, 105),
             "target": (255, 245, 0), "hazard": (255, 30, 140), "ground": (110, 70, 255),
             "accent": (0, 150, 255), "text": (245, 245, 255)},
    "space": {"background": (6, 8, 26), "player": (130, 225, 255), "player_accent": (60, 120, 170),
              "target": (255, 190, 70), "hazard": (250, 80, 50), "ground": (120, 125, 140),
              "accent": (190, 90, 255), "text": (235, 235, 245)},
    "forest": {"background": (16, 34, 22), "player": (250, 160, 60), "player_accent": (150, 90, 30),
               "target": (255, 240, 110), "hazard": (200, 40, 60), "ground": (110, 170, 70),
               "accent": (80, 120, 200), "text": (240, 245, 235)},
    "ocean": {"background": (8, 30, 56), "player": (255, 255, 120), "player_accent": (170, 160, 40),
              "target": (255, 120, 170), "hazard": (240, 70, 40), "ground": (40, 160, 170),
              "accent": (120, 200, 255), "text": (235, 245, 255)},
    "candy": {"background": (40, 18, 46), "player": (120, 255, 220), "player_accent": (40, 150, 120),
              "target": (255, 230, 90), "hazard": (255, 70, 110), "ground": (250, 150, 230),
              "accent": (130, 120, 255), "text": (255, 245, 250)},
}

_WORDS = {
    "neon": r"neon|cyber|synth|retro ?wave|glow",
    "space": r"space|galaxy|star|alien|asteroid|planet|rocket|cosmic",
    "forest": r"forest|jungle|nature|wood|garden|tree",
    "ocean": r"ocean|sea|underwater|fish|beach|water|shark",
    "candy": r"candy|sweet|cute|pastel|pink|kawaii",
}


def pick(request: str, default: str = "classic") -> str:
    r = (request or "").lower()
    for name, rx in _WORDS.items():
        if re.search(rf"\b(?:{rx})", r):
            return name
    return default


def colors(theme: str) -> Dict[str, list]:
    return {role: list(rgb) for role, rgb in THEMES.get(theme, THEMES["classic"]).items()}
