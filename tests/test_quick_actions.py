"""Quick-action dispatch: every action reaches its intended handler (no window needed)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

pytest.importorskip("tkinter")
tom_desktop_app = pytest.importorskip("tom_desktop_app")

# Actions that open a dedicated input prompt, by label -> handler name.
PROMPTED = {
    "Web Auto": "_handle_web_automation", "Multi-Agent": "_handle_multi_agent",
    "Security": "_handle_security_check", "File Anal": "_handle_file_analysis",
    "Data Anal": "_handle_data_analysis", "Autonomous": "_handle_autonomous",
    "Hardware": "_handle_hardware", "Skill": "_handle_skill_query", "ML": "_handle_ml",
    "IoT": "_handle_iot", "VLSI": "_handle_vlsi", "Env Setup": "_handle_env",
    "News": "_handle_news", "Voice+": "_handle_voice_enhanced", "Game Dev": "_handle_game_dev",
    "Blender 3D": "_handle_blender", "Media Edit": "_handle_media", "Auto Scaler": "_handle_scaler",
    "Auto-Update": "_handle_auto_update",
}


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
    app.prompted = []
    app._prompt_and_run = lambda prompt, handler: app.prompted.append(handler.__name__)
    app._show_view = lambda view: None
    app.input_var = _Var()
    app.input_entry = _Entry()
    return app


def test_all_27_quick_actions_are_defined():
    assert len(_app_with_quick_actions().quick_actions) == 27


def test_each_quick_action_reaches_its_handler():
    app = _app_with_quick_actions()
    for qa in app.quick_actions:
        app.prompted.clear()
        app.input_var.value = ""
        app._quick_action(qa["cmd"])
        if qa["label"] in PROMPTED:
            # e.g. "Security"'s command is "Check website safety: " — dispatch
            # must go by label, not by searching the command text.
            assert app.prompted == [PROMPTED[qa["label"]]], qa["label"]
        else:
            assert app.prompted == [], qa["label"]
            assert app.input_var.value == qa["cmd"], qa["label"]


def test_hardware_commands_parse_coordinates_and_keep_case():
    calls = []

    class HW:
        def is_available(self):
            return True

        def __getattr__(self, name):
            return lambda *a, **k: calls.append((name, a)) or {"status": "success"}

    app = tom_desktop_app.TomDesktopApp.__new__(tom_desktop_app.TomDesktopApp)
    app.hardware = HW()
    app._append_chat = lambda role, text: None
    app._enqueue = lambda fn, *a: None
    cases = {
        "move mouse to 500 500": ("move_mouse", (500, 500)),   # the dialog's own example
        "click at 10, 20": ("click", (10, 20)),
        "type Hello World": ("type_text", ("Hello World",)),   # case preserved
        "scroll 5": ("scroll", (5,)),
    }
    for command, expected in cases.items():
        calls.clear()
        app._handle_hardware(command)
        assert calls[0] == expected, command
