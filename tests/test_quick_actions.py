"""Quick actions: every action switches TOM into a skill mode handled by the agent (no window needed).

They used to open "Enter URL:"-style dialogs and call handlers directly, bypassing the agent
(owner report 2026-10-21). Now each one only selects a tom_core.skill_modes mode.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

pytest.importorskip("tkinter")
tom_desktop_app = pytest.importorskip("tom_desktop_app")

from tom_core import skill_modes  # noqa: E402


class _Var:
    def __init__(self):
        self.value = ""

    def set(self, value):
        self.value = value


class _Entry:
    def focus_set(self):
        pass

    def icursor(self, _):
        pass


def _app_with_quick_actions():
    """A TomDesktopApp with only what _quick_action touches (no Tk root)."""
    # __init__ builds the real list; recover it without creating any widgets.
    import inspect, ast, textwrap
    src = textwrap.dedent(inspect.getsource(tom_desktop_app.TomDesktopApp.__init__))
    start = src.index("self.quick_actions = [")
    end = src.index("]\n", start) + 1
    expr = src[start + len("self.quick_actions = "):end]
    colors = {k: k for k in ("blue", "emerald", "orange", "red", "cyan", "purple",
                             "amber", "pink", "indigo")}
    app = tom_desktop_app.TomDesktopApp.__new__(tom_desktop_app.TomDesktopApp)
    app.quick_actions = eval(compile(ast.parse(expr, mode="eval"), "qa", "eval"), {"C": colors})
    app.entered = []
    app._enter_skill_mode = lambda key: app.entered.append(key)
    app._prompt_and_run = lambda *a: pytest.fail("quick actions must not open input dialogs any more")
    app._show_view = lambda view: None
    app.input_var = _Var()
    app.input_entry = _Entry()
    return app


def test_all_28_quick_actions_are_defined():
    assert len(_app_with_quick_actions().quick_actions) == 28        # 2026-10-27: + Website


def test_every_quick_action_enters_its_mode():
    app = _app_with_quick_actions()
    for qa in app.quick_actions:
        app.entered.clear()
        app._quick_action(qa["cmd"])
        assert app.entered == [skill_modes.BY_LABEL[qa["label"]]], qa["label"]


def test_mode_text_carries_the_mode_and_the_chosen_file():
    app = tom_desktop_app.TomDesktopApp.__new__(tom_desktop_app.TomDesktopApp)
    app._skill_mode, app._mode_file = skill_modes.MODES["media"], r"C:\clips\a.mp4"
    text, mode = skill_modes.split(app._mode_text("trim the first 5 seconds"))
    assert mode.key == "media" and text == 'trim the first 5 seconds "C:\\clips\\a.mp4"'
    app._skill_mode = None
    assert app._mode_text("hello") == "hello"


