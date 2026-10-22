"""Push-to-talk shared by the Tk and PySide6 apps, and the female-voice preference (owner, 2026-10-21)."""
import os
import queue
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tom_core.voice import config as vconfig  # noqa: E402
from tom_core.voice import push_to_talk  # noqa: E402
from tom_core.voice.tts import choose_voice  # noqa: E402


class FakeVoice:
    """The slice of VoiceTools push-to-talk uses; records what happened."""

    def __init__(self, result=None, speaking=False, mic_ok=True):
        self.result = result if result is not None else {"status": "success", "text": " open chrome ",
                                                         "asr_seconds": 0.31}
        self._speaking = speaking
        self._mic_ok = mic_ok
        self.input_enabled = False
        self.output_enabled = False
        self._recognizer = None
        self._tts_adapter = None
        self._tts_engine = None
        self._input_error = ""
        self.config = vconfig.VoiceConfig()
        self.calls = []
        self.spoken = []

    def _setup_input(self):
        self.calls.append("setup_input")
        if self._mic_ok:
            self._recognizer = object()
        else:
            self.input_enabled = False
            self._input_error = "No microphone devices detected."

    def _setup_output(self):
        self.calls.append("setup_output")
        self._tts_adapter = object()

    def stop_speaking(self):
        self.calls.append("stop_speaking")
        self._speaking = False

    def listen_neural(self, timeout=7):
        self.calls.append(("listen", timeout))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    def speak(self, text):
        self.spoken.append(text)


# ── tom_core.voice.push_to_talk ──────────────────────────────────────────

def test_capture_returns_the_words_and_says_where_they_were_recognised():
    v = FakeVoice()
    heard = push_to_talk.capture(v)
    assert heard.text == "open chrome"
    assert "recognised locally in 0.31s" in heard.message
    assert ("listen", push_to_talk.LISTEN_TIMEOUT_S) in v.calls


def test_capture_names_the_cloud_when_google_asr_was_opted_into():
    v = FakeVoice()
    v.config = vconfig.VoiceConfig(asr_engine="google")
    assert "by Google (cloud)" in push_to_talk.capture(v).message


def test_pressing_while_tom_speaks_cuts_the_reply_off_first():
    v = FakeVoice(speaking=True)
    push_to_talk.capture(v)
    assert v.calls.index("stop_speaking") < v.calls.index(("listen", push_to_talk.LISTEN_TIMEOUT_S))


@pytest.mark.parametrize("result,expected", [
    ({"status": "timeout", "message": "No speech detected.", "text": ""}, "No speech detected."),
    ({"status": "success", "text": "   "}, "Didn't catch that."),
    (RuntimeError("mic unplugged"), "Voice error: mic unplugged"),
])
def test_nothing_usable_heard_gives_a_reason_and_no_text(result, expected):
    heard = push_to_talk.capture(FakeVoice(result=result))
    assert heard.text == "" and heard.message == expected


def test_prepare_turns_on_the_mic_and_can_leave_mute_alone():
    v = FakeVoice()
    assert push_to_talk.prepare(v, speak=False) == ""
    assert v.input_enabled and not v.output_enabled and "setup_output" not in v.calls
    assert push_to_talk.prepare(v) == ""
    assert v.output_enabled and v.calls.count("setup_input") == 1      # set up once, reused


def test_prepare_reports_a_missing_microphone():
    assert push_to_talk.prepare(FakeVoice(mic_ok=False)) == "No microphone devices detected."


# ── female voice preference ──────────────────────────────────────────────

US = [("Microsoft David", "en-US", "male"), ("Microsoft Zira", "en-US", "female"),
      ("Microsoft Mark", "en-US", "male")]
IN = [("Microsoft Ravi", "en-IN", "male"), ("Microsoft Heera", "en-IN", "female")]
PREF = list(vconfig.DEFAULT_LOCAL_VOICE_PREFERENCE)          # en-US, Zira, Mark, David, en-IN


def test_default_is_the_female_us_english_voice_even_with_indian_voices_installed():
    voices = US + IN                                          # this machine since 2026-10-21
    assert voices[choose_voice(voices, PREF, "female")][0] == "Microsoft Zira"


def test_an_indian_english_preference_still_picks_the_female_voice():
    voices = US + IN
    assert voices[choose_voice(voices, ["en-IN"] + PREF, "female")][0] == "Microsoft Heera"


def test_female_beats_a_better_ranked_male_voice():
    assert US[choose_voice(US, ["Mark", "Zira"], "female")][0] == "Microsoft Zira"
    assert (IN + US)[choose_voice(IN + US, ["en-IN"], "female")][0] == "Microsoft Heera"


def test_a_female_voice_that_cannot_speak_english_is_not_chosen():
    voices = [("Microsoft Hortense", "fr-FR", "female"), ("Microsoft David", "en-US", "male")]
    assert choose_voice(voices, PREF, "female") == 1


def test_no_gender_keeps_the_preference_order():
    assert US[choose_voice(US, ["Mark", "Zira"])][0] == "Microsoft Mark"
    assert US[choose_voice(US, PREF, "male")][0] == "Microsoft David"        # first male en-US


@pytest.mark.parametrize("value,gender,edge", [
    (None, "female", "en-US-JennyNeural"),
    ("male", "male", "en-US-GuyNeural"),
    ("any", None, "en-US-JennyNeural"),
])
def test_gender_setting(monkeypatch, value, gender, edge):
    for k in ("TOM_TTS_GENDER", "TOM_EDGE_VOICE", "TOM_VOICE"):
        monkeypatch.delenv(k, raising=False)
    if value:
        monkeypatch.setenv("TOM_TTS_GENDER", value)
    cfg = vconfig.load_config()
    assert cfg.tts_gender == gender and cfg.edge_voice == edge


# ── Tkinter app: same flow as the PySide6 window ─────────────────────────

class _Widget:
    def __init__(self):
        self.config = {}

    def configure(self, **kw):
        self.config.update(kw)


@pytest.fixture
def tk_app():
    pytest.importorskip("tkinter")
    tom_desktop_app = pytest.importorskip("tom_desktop_app")
    app = tom_desktop_app.TomDesktopApp.__new__(tom_desktop_app.TomDesktopApp)
    app.voice = FakeVoice()
    app.agent_ready = True
    app.processing = False
    app.voice_mode_enabled = False
    app._voice_ui_window = None
    app.voice_btn, app.mic_btn = _Widget(), _Widget()
    app.activity_counts = {"voice": 0}
    app.recent_events = []
    app.chat, app.sent = [], []
    app.ui = queue.Queue()
    app._enqueue = lambda fn, *a: app.ui.put((fn, a))
    app._append_chat = lambda role, text: app.chat.append((role, text))
    app._show_view = app._set_status = app._refresh_dashboard = lambda *a: None
    app.send_message = lambda text=None, interface="desktop": app.sent.append((text, interface))
    return app


def _drain(app, timeout=5.0):
    fn, args = app.ui.get(timeout=timeout)          # the listening thread hands back one result
    fn(*args)


def test_tk_push_to_talk_sends_the_words_as_a_voice_task(tk_app):
    tk_app._push_to_talk()
    assert tk_app.voice_mode_enabled and "Done" in tk_app.mic_btn.config["text"]
    _drain(tk_app)
    assert tk_app.sent == [("open chrome", "voice")]
    assert not tk_app.voice_mode_enabled and "Talk" in tk_app.mic_btn.config["text"]
    assert tk_app.activity_counts["voice"] == 1
    assert not tk_app.voice.output_enabled          # Tk's Mute setting is left as it was


def test_tk_pressing_talk_again_while_listening_means_done(tk_app):
    finished = []
    tk_app.voice.finish_listening = lambda: finished.append(True)
    tk_app.voice_mode_enabled = True                 # a press is already listening
    tk_app._push_to_talk()
    assert finished == [True] and tk_app.ui.empty()


def test_tk_push_to_talk_does_not_send_while_tom_is_busy(tk_app):
    tk_app._push_to_talk()
    tk_app.processing = True                         # a typed message went out meanwhile
    _drain(tk_app)
    assert tk_app.sent == [] and any("Not sent" in t for _, t in tk_app.chat)


def test_tk_push_to_talk_explains_why_it_cannot_listen(tk_app):
    tk_app.agent_ready = False
    tk_app._push_to_talk()
    tk_app.agent_ready, tk_app.voice = True, None
    tk_app._push_to_talk()
    assert tk_app.ui.empty() and not tk_app.voice_mode_enabled
    assert "initializing" in tk_app.chat[0][1] and "not available" in tk_app.chat[1][1]


def test_tk_send_message_routes_spoken_text_with_the_voice_label(monkeypatch):
    pytest.importorskip("tkinter")
    tom_desktop_app = pytest.importorskip("tom_desktop_app")
    app = tom_desktop_app.TomDesktopApp.__new__(tom_desktop_app.TomDesktopApp)
    app.processing, app.agent_ready = False, True
    app._attachments, app._clear_attachments = [], lambda: None
    app.agent_profiles = {"general": {"prefix": "", "label": "TOM"}}
    app.active_agent_key = "general"
    app.activity_counts = {"messages": 0}
    app.recent_events = []
    app._refresh_dashboard = app._append_chat = lambda *a: None
    app.send_btn, app.stop_btn, app.orb = _Widget(), _Widget(), type("Orb", (), {})()
    app.input_var = type("Var", (), {"get": lambda s: "typed text", "set": lambda s, v: None})()
    routed = []
    app._process_message = lambda text, interface="desktop": routed.append((text, interface))
    tom_desktop_app.TomDesktopApp.send_message(app, text="what time is it", interface="voice")
    end = time.time() + 5
    while not routed and time.time() < end:
        time.sleep(0.01)
    assert routed == [("what time is it", "voice")]


# ── PySide6 app uses the same module ─────────────────────────────────────

def test_qt_push_to_talk_round_trip(monkeypatch, tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from test_qt_app import FakeAgent, _wait
    from tom_core.interfaces import qt_app

    app = QApplication.instance() or QApplication([])
    voice = FakeVoice()
    w = qt_app.TomWindow(lambda: FakeAgent(str(tmp_path / "tasks.sqlite3")), start_sampler=False,
                         voice_factory=lambda: voice)
    try:
        _wait(app, lambda: w.talk_btn.isEnabled(), "agent ready")
        w.talk_btn.setChecked(True)
        _wait(app, lambda: "You said: open chrome" in w.chat.toPlainText(), "voice reply")
        _wait(app, lambda: voice.spoken, "reply read aloud")
        assert "recognised locally" in w.voice_lbl.text()
        w.refresh_tasks()
        assert w.task_table.item(0, 2).text() == "voice"
    finally:
        w.close()


def test_at014_interrupting_tom_stops_playback_and_sends_the_next_request_once(tk_app):
    """AT-014: press Talk while TOM is speaking → the reply stops, the new request runs exactly once,
    and a second press during that same listen only ends it (no second submission)."""
    tk_app.voice = FakeVoice(speaking=True)
    finished = []
    tk_app.voice.finish_listening = lambda: finished.append(True)
    tk_app._push_to_talk()
    tk_app._push_to_talk()                            # impatient second press while still listening
    _drain(tk_app)
    assert "stop_speaking" in tk_app.voice.calls
    assert tk_app.voice.calls.index("stop_speaking") < tk_app.voice.calls.index(("listen", push_to_talk.LISTEN_TIMEOUT_S))
    assert tk_app.sent == [("open chrome", "voice")]  # exactly one task
    assert finished == [True] and tk_app.ui.empty()
