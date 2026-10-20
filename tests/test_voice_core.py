"""tom_core.voice — local-first ASR/TTS adapters, worker processes, GPU admission."""
import os
import sys
import textwrap

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tom_core.resources.gpu import GpuMemory, admit_gpu_job  # noqa: E402
from tom_core.voice import config as vconfig  # noqa: E402
from tom_core.voice.asr import ASRError, LocalWhisperASR, clean_transcript, find_cuda_runtime_dir  # noqa: E402
from tom_core.voice.tts import SpeechClip, TTSError, choose_voice, speech_text  # noqa: E402
from tom_core.voice.workers import WorkerError, WorkerProcess  # noqa: E402

_VOICE_ENV = ("TOM_ASR_ENGINE", "VOICE_RECOGNITION_ENGINE", "TOM_ASR_LANGUAGE", "TOM_ASR_MODEL",
              "TOM_ASR_MODEL_DIR", "TOM_TTS_ENGINE", "TOM_TTS_VOICE", "TOM_VOICE", "TOM_EDGE_VOICE")


@pytest.fixture
def clean_env(monkeypatch):
    for k in _VOICE_ENV:
        monkeypatch.delenv(k, raising=False)
    return monkeypatch


# ── configuration: local unless a cloud engine is chosen explicitly ──────

def test_defaults_are_local(clean_env):
    cfg = vconfig.load_config()
    assert cfg.asr_engine == "local" and not cfg.asr_is_cloud
    assert cfg.tts_engine == "local" and not cfg.tts_is_cloud
    assert cfg.asr_language == "en"
    assert cfg.tts_voice_preference[0] == "en-IN"          # Indian English voice first
    assert cfg.edge_voice == "en-IN-PrabhatNeural"


def test_cloud_engines_need_an_explicit_choice(clean_env):
    clean_env.setenv("VOICE_RECOGNITION_ENGINE", "google")
    clean_env.setenv("TOM_TTS_ENGINE", "edge")
    cfg = vconfig.load_config()
    assert cfg.asr_is_cloud and cfg.tts_is_cloud


def test_new_variable_wins_and_unknown_values_stay_local(clean_env):
    clean_env.setenv("VOICE_RECOGNITION_ENGINE", "google")
    clean_env.setenv("TOM_ASR_ENGINE", "whisper")
    assert vconfig.load_config().asr_engine == "local"
    clean_env.setenv("TOM_ASR_ENGINE", "some-cloud-thing")
    clean_env.setenv("TOM_TTS_ENGINE", "nonsense")
    cfg = vconfig.load_config()
    assert cfg.asr_engine == "local" and cfg.tts_engine == "local"


def test_language_auto_and_voice_preferences(clean_env):
    clean_env.setenv("TOM_ASR_LANGUAGE", "auto")
    clean_env.setenv("TOM_TTS_VOICE", "Heera, Ravi")
    clean_env.setenv("TOM_VOICE", "en-IN-NeerjaNeural")     # legacy edge voice setting still honoured
    cfg = vconfig.load_config()
    assert cfg.asr_language is None
    assert cfg.tts_voice_preference[:3] == ["Heera", "Ravi", "en-IN"]
    assert cfg.edge_voice == "en-IN-NeerjaNeural"


def test_model_dir_only_counts_complete_downloads(clean_env, tmp_path):
    snap = tmp_path / "models--mobiuslabsgmbh--faster-whisper-large-v3-turbo" / "snapshots" / "abc"
    snap.mkdir(parents=True)
    (snap / "config.json").write_text("{}")
    clean_env.setattr(vconfig, "DEFAULT_MODEL_DIRS", ())      # ignore this machine's real caches
    clean_env.setenv("TOM_ASR_MODEL_DIR", str(tmp_path))
    assert vconfig.load_config().model_dir() is None          # no model.bin → not usable
    (snap / "model.bin").write_bytes(b"x")
    assert vconfig.load_config().model_dir() == str(tmp_path)


def test_repo_table_matches_faster_whisper():
    utils = pytest.importorskip("faster_whisper.utils")
    assert vconfig.FASTER_WHISPER_REPOS == utils._MODELS


def test_missing_model_is_reported_never_downloaded(clean_env, tmp_path):
    clean_env.setenv("TOM_ASR_MODEL_DIR", str(tmp_path))
    clean_env.setenv("TOM_ASR_MODEL", "no-such-model-xyz")
    asr = LocalWhisperASR(vconfig.load_config())
    with pytest.raises(ASRError, match="does not download"):
        asr.transcribe_wav(b"RIFF")


# ── TTS helpers ──────────────────────────────────────────────────────────

VOICES = [("Microsoft David", "en-US"), ("Microsoft Zira", "en-US"), ("Microsoft Mark", "en-US")]


def test_indian_english_voice_wins_when_installed():
    assert choose_voice(VOICES, ["en-IN", "Mark"]) == 2                  # not installed → Mark
    with_heera = VOICES + [("Microsoft Heera", "en-IN")]
    assert choose_voice(with_heera, ["en-IN", "Mark"]) == 3
    assert choose_voice([("Microsoft Hortense", "fr-FR"), ("Microsoft Zira", "en-US")], ["xx"]) == 1
    assert choose_voice([], ["en-IN"]) is None


def test_speech_text_reads_like_a_person_talking():
    out = speech_text("**Done!** See `report.docx`:\n\n- [the dashboard](http://x.io/a)\n"
                      "```python\nprint(1)\n```\nMore at https://example.com/page")
    assert "*" not in out and "`" not in out and "print(1)" not in out and "http" not in out
    assert "report.docx" in out and "the dashboard" in out and "the link" in out


# ── ASR helpers ──────────────────────────────────────────────────────────

def test_whisper_hallucinations_and_silence_are_dropped():
    assert clean_transcript([{"text": " Thank you.", "no_speech_prob": 0.1, "avg_logprob": -0.2}]) == ""
    assert clean_transcript([{"text": "Open Chrome", "no_speech_prob": 0.9, "avg_logprob": -1.4}]) == ""
    kept = clean_transcript([{"text": " Open Chrome", "no_speech_prob": 0.05, "avg_logprob": -0.2},
                             {"text": " and search the news.", "no_speech_prob": 0.1, "avg_logprob": -0.3}])
    assert kept == "Open Chrome and search the news."


def test_cuda_runtime_dir_discovery(tmp_path, monkeypatch):
    dll = "cublas64_12.dll" if os.name == "nt" else "libcublas.so.12"
    monkeypatch.setenv("PATH", "")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "nowhere"))
    assert find_cuda_runtime_dir() == ""
    (tmp_path / dll).write_bytes(b"x")
    assert find_cuda_runtime_dir(str(tmp_path)) == str(tmp_path)


# ── GPU admission (PRD RRM-003 / RRM-012) ────────────────────────────────

@pytest.mark.parametrize("free,requested,cuda_ok,device", [
    (7900, "auto", True, "cuda"),
    (2000, "auto", True, "cpu"),          # not enough after the reserve
    (7900, "cpu", True, "cpu"),
    (7900, "auto", False, "cpu"),         # no CUDA runtime
    (2000, "cuda", True, "cpu"),          # explicit cuda is still refused when it would not fit
])
def test_gpu_admission(free, requested, cuda_ok, device):
    gpu = GpuMemory(total_mb=8151, used_mb=8151 - free, free_mb=free)
    assert admit_gpu_job(1200, 1536, requested=requested, gpu=gpu, cuda_available=cuda_ok).device == device


def test_unmeasurable_gpu_means_cpu():
    assert admit_gpu_job(1200, 1536, gpu=None).device == "cpu"


# ── worker process protocol ──────────────────────────────────────────────

FAKE_WORKER = textwrap.dedent("""
    import os, sys
    from tom_core.voice.workers import fail_startup, protocol_stdout, serve
    protocol_stdout()
    print("library noise on stdout must not break the protocol")
    if os.environ.get("FAKE_FAIL_START"):
        fail_startup("model missing")
    def handle(op, args):
        if op == "echo":
            return {"echo": args["value"]}
        if op == "boom":
            raise ValueError("bad input")
        if op == "die":
            os._exit(3)
    serve(handle, {"device": "fake"})
""")


@pytest.fixture
def fake_worker(tmp_path):
    script = tmp_path / "fake_worker.py"
    script.write_text(FAKE_WORKER)
    workers = []

    def make(**env):
        w = WorkerProcess("fake", env=env, start_timeout=30, command=[sys.executable, "-u", str(script)])
        workers.append(w)
        return w
    yield make
    for w in workers:
        w.stop()


def test_worker_round_trip_and_error_reply(fake_worker):
    w = fake_worker()
    assert w.start()["device"] == "fake"
    assert w.request("echo", value="नमस्ते TOM")["echo"] == "नमस्ते TOM"
    with pytest.raises(WorkerError, match="bad input"):
        w.request("boom")
    assert w.request("echo", value=2)["echo"] == 2          # still serving after an error reply


def test_worker_is_restarted_once_after_a_crash(fake_worker):
    w = fake_worker()
    w.start()
    first_pid = w._proc.pid
    with pytest.raises(WorkerError):
        w.request("die")                                    # dies again on the retry too
    assert w.request("echo", value="back")["echo"] == "back"
    assert w._proc.pid != first_pid


def test_worker_startup_failure_is_reported(fake_worker):
    w = fake_worker(FAKE_FAIL_START="1")
    with pytest.raises(WorkerError, match="model missing"):
        w.start()


# ── VoiceTools uses the adapters and never goes silent ───────────────────

class _FailingTTS:
    name = "windows"
    voice = ""

    def synthesize(self, text):
        raise TTSError("worker gone")


class _OkTTS:
    name = "windows"
    voice = "Microsoft Mark"

    def __init__(self, path):
        self.path = path
        self.texts = []

    def synthesize(self, text):
        self.texts.append(text)
        return SpeechClip(path=str(self.path), engine="windows", voice=self.voice)


@pytest.fixture
def voice(clean_env):
    clean_env.setenv("VOICE_INPUT_ENABLED", "false")
    clean_env.setenv("VOICE_OUTPUT_ENABLED", "false")
    from tools.voice_tools import VoiceTools
    vt = VoiceTools()
    vt.output_enabled = True
    vt.played = []
    vt._play_audio = vt.played.append
    return vt


def test_speech_goes_through_the_adapter_with_markdown_removed(voice, tmp_path):
    clip = tmp_path / "u.wav"
    clip.write_bytes(b"RIFF")
    voice._tts_adapter = _OkTTS(clip)
    result = voice.speak("**Report ready.** Saved as `q3.xlsx`.")
    assert result["status"] == "success" and result["voice"] == "Microsoft Mark"
    assert voice._tts_adapter.texts == ["Report ready. Saved as q3.xlsx."]
    assert voice.played == [str(clip)] and not clip.exists()      # temp clip cleaned up


def test_a_failing_voice_falls_back_to_sapi(voice):
    spoken = []
    voice._tts_adapter = _FailingTTS()
    voice._tts_engine = type("Sapi", (), {"say": lambda s, t: spoken.append(t), "runAndWait": lambda s: None,
                                          "stop": lambda s: None})()
    result = voice.speak("Hello there.")
    assert result["status"] == "success" and spoken == ["Hello there."]
    assert "worker gone" in voice._output_error


# ── real engines (only where the models and Windows voices exist) ────────

def _real_voice_available():
    if os.name != "nt":
        return False
    try:
        import faster_whisper  # noqa: F401
        import winrt.windows.media.speechsynthesis  # noqa: F401  (import only in this probe)
    except Exception:
        return False
    return vconfig.load_config().model_dir() is not None


@pytest.mark.skipif(os.environ.get("TOM_SKIP_REAL_VOICE") == "1", reason="real voice test disabled")
def test_local_voice_round_trip_is_accurate(clean_env):
    """Windows voice speaks a command; the local Whisper worker must hear it back word for word."""
    import subprocess
    probe = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, %r); "
                            "from tests.test_voice_core import _real_voice_available as f; "
                            "sys.exit(0 if f() else 1)" % os.path.dirname(os.path.dirname(__file__))],
                           capture_output=True, timeout=60)
    if probe.returncode != 0:
        pytest.skip("local speech model / Windows voices not available on this machine")
    from tom_core.voice.tts import LocalWindowsTTS
    cfg = vconfig.load_config()
    tts, asr = LocalWindowsTTS(cfg), LocalWhisperASR(cfg)
    try:
        clip = tts.synthesize("Please open Chrome and search for the weather in Hyderabad.")
        with open(clip.path, "rb") as fh:
            heard = asr.transcribe_wav(fh.read())
    finally:
        tts.close()
        asr.close()
    words = heard.text.lower().replace(".", "").replace(",", "")
    assert "open chrome" in words and "weather in hyderabad" in words, heard.text
