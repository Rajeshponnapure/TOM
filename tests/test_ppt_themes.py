"""Presentation themes: named styles (gaming / gradient / floral / bright ...)
resolve to real palettes, an explicitly-requested theme is extracted from the
command, and a deck actually renders with the chosen theme without crashing.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools.document_creator import _resolve_style, _detect_theme, _THEME_PRESETS


# ── style resolution ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("word,expected", [
    ("gaming", "gaming"),
    ("gradient", "gradient"),
    ("floral", "floral"),
    ("flowers", "floral"),
    ("bright", "vibrant"),
    ("colourful", "vibrant"),
    ("neon", "gaming"),
    ("luxury", "elegant"),
    ("gaming theme", "gaming"),       # substring
    ("", ""),
    ("zzzz", ""),
])
def test_resolve_style(word, expected):
    assert _resolve_style(word) == expected


def test_named_theme_changes_the_palette():
    minimal = _detect_theme("x", {"style": "minimal"})
    gaming = _detect_theme("x", {"style": "gaming"})
    assert gaming["primary"] != minimal["primary"]
    assert gaming == _THEME_PRESETS["gaming"]


def test_detect_theme_accepts_a_plain_string():
    assert _detect_theme("x", "floral")["primary"] == _THEME_PRESETS["floral"]["primary"]


def test_custom_colours_override_the_preset():
    t = _detect_theme("x", {"style": "gaming", "accent": "#123456"})
    assert t["accent"] == "#123456"
    assert t["primary"] == _THEME_PRESETS["gaming"]["primary"]


# ── extraction from a natural-language command ───────────────────────────────

def test_agent_extracts_requested_theme():
    import agent
    f = agent.TomAgent._extract_requested_theme
    assert f("make a ppt on AI in a gaming theme") == "gaming"
    assert f("build a 10 slide deck with bright colours") == "bright"
    assert f("gradient theme deck on fintech") == "gradient"
    assert f("a floral presentation for a wedding") == "floral"
    assert f("presentation about climate change") == ""


# ── end-to-end render ────────────────────────────────────────────────────────

def test_deck_renders_with_a_named_theme(tmp_path):
    pytest.importorskip("pptx")
    from tools.document_creator import create_presentation
    fpath = str(tmp_path / "deck.pptx")
    res = create_presentation(
        title="Neon Night",
        slides_content=[{"title": "Intro", "content": ["One", "Two"]}],
        filename=fpath,
        theme={"style": "gaming"},
    )
    assert res["status"] == "success", res
    assert os.path.isfile(fpath)
