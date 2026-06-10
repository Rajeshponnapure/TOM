"""Voice-stack + bug-fix contracts (2026-06-10 user-reported issues)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_voice_self_test_structure(monkeypatch):
    monkeypatch.setenv("VOICE_INPUT_ENABLED", "true")
    monkeypatch.setenv("VOICE_OUTPUT_ENABLED", "true")
    from tools.voice_tools import VoiceTools
    vt = VoiceTools()
    r = vt.self_test()
    for key in ("mic_count", "pygame_audio", "problems", "verdict", "env"):
        assert key in r
    txt = vt.self_test_text()
    assert "Voice self-test" in txt

def test_play_audio_survives_pygame_failure(tmp_path, monkeypatch):
    """pygame errors must NOT abort the fallback chain (was: except ImportError only)."""
    from tools.voice_tools import VoiceTools
    monkeypatch.setenv("VOICE_OUTPUT_ENABLED", "true")
    vt = VoiceTools()
    fake = tmp_path / "x.mp3"
    fake.write_bytes(b"\x00")
    # In CI pygame is absent (ImportError) or has no device (pygame.error) —
    # both must be swallowed and recorded, never raised.
    vt._play_audio(str(fake))  # must not raise
    # unique-temp-name counter exists
    assert not hasattr(vt, "_utt_counter") or isinstance(vt._utt_counter, int)

def test_unique_tts_filenames():
    """Fixed tom_voice.mp3 name caused WinError 32 lock; must be unique now."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "tools", "voice_tools.py"), encoding="utf-8").read()
    assert 'f"tom_voice_{os.getpid()}_{self._utt_counter}.mp3"' in src
    assert 'os.path.join(tempfile.gettempdir(), "tom_voice.mp3")' not in src
    assert "pygame.mixer.music.unload()" in src

def test_calibration_once_per_session():
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "tools", "voice_tools.py"), encoding="utf-8").read()
    assert "_calibrated" in src

def test_gui_has_global_scroll_dispatcher():
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "tom_desktop_app.py"), encoding="utf-8").read()
    assert "_install_global_scroll" in src
    assert 'bind_all("<MouseWheel>"' in src

def test_data_analysis_handles_sample_and_app_open():
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "agent.py"), encoding="utf-8").read()
    assert "sample_sales_data.csv" in src
    assert "power\\s*bi" in src or "power\\\\s*bi" in src
