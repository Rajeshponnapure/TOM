"""
Voice I/O for TOM.
Input:  pyaudio microphone capture (tom_core.voice.capture: records until the user stops talking
        or presses Talk again) → ASR adapter (local faster-whisper by default; Google only when
        chosen explicitly)
Output: TTS adapter (local Windows voices by default, female US English preferred;
        edge-tts online neural voices only when chosen explicitly) → pyttsx3 fallback
Mode:   Continuous voice conversation with NLP context
Engines live in tom_core.voice; see docs/migration/decisions.md ADR-005 for the cloud opt-in rule.
"""
import asyncio
import json
import math
import os
import subprocess
import tempfile
import threading
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional


def _wav_16k(pcm: bytes, sample_rate: int, sample_width: int) -> bytes:
    """Microphone PCM → the 16 kHz 16-bit mono WAV every ASR adapter takes."""
    import speech_recognition as sr
    return sr.AudioData(pcm, sample_rate, sample_width).get_wav_data(convert_rate=16000, convert_width=2)


class VoiceTools:
    def __init__(self):
        self.input_enabled = os.environ.get("VOICE_INPUT_ENABLED", "false").lower() == "true"
        self.output_enabled = os.environ.get("VOICE_OUTPUT_ENABLED", "false").lower() == "true"
        self.energy_threshold = int(os.environ.get("VOICE_ENERGY_THRESHOLD", "800"))
        self.listen_timeout = int(os.environ.get("VOICE_LISTEN_TIMEOUT", "7"))

        from tom_core.voice import load_config
        self.config = load_config()
        # How a request ends is set by tom_core.voice.capture (TOM_VOICE_END_SILENCE /
        # TOM_VOICE_MAX_SECONDS); the old 0.8 s pause / 15 s limit cut people off mid-sentence.
        self._noise_floor: Optional[float] = None     # room noise, carried between presses
        self._listen_stop = threading.Event()          # Talk pressed again / Stop pressed
        self._listen_cancelled = False                 # Stop: throw the audio away
        self.voice_name = self.config.edge_voice
        self.voice_rate = self.config.edge_rate
        self.recognition_engine = self.config.asr_engine      # "local" | "google"

        self._recognizer = None
        self._asr = None              # tom_core.voice.asr.ASREngine, created on first use
        self._tts_engine = None       # pyttsx3 (SAPI) — local last-resort voice
        self._tts_adapter = None      # tom_core.voice.tts.TTSEngine (Windows voices / edge)
        self._edge_tts_ok = False
        self._input_error = ""
        self._output_error = ""

        # Conversation mode state
        self._conv_active = False
        self._conv_thread: Optional[threading.Thread] = None
        self._conv_stop = threading.Event()
        self._speaking = False
        self._speech_stop = threading.Event()

        # Audio level callback (for UI visualization)
        self.on_audio_level: Optional[Callable] = None
        self.on_state_change: Optional[Callable] = None

        self._setup_input()
        self._setup_output()

    # ── Input setup ──────────────────────────────────────────────────────

    def _setup_input(self):
        if not self.input_enabled:
            return
        try:
            import speech_recognition as sr
            try:
                mic_names = sr.Microphone.list_microphone_names()
            except Exception:
                mic_names = []
            if not mic_names:
                self.input_enabled = False
                self._input_error = "No microphone devices detected."
                return
            # Marks input as ready; listening itself is done by tom_core.voice.capture.
            self._recognizer = sr.Recognizer()
        except Exception as exc:
            self.input_enabled = False
            msg = str(exc)
            if isinstance(exc, ModuleNotFoundError):
                self._input_error = "Missing: pip install SpeechRecognition pyaudio"
            elif "PortAudio" in msg or "Pa_" in msg or "No Default" in msg:
                self._input_error = "Microphone/PortAudio issue. Check audio drivers."
            else:
                self._input_error = msg

    # ── Output setup ─────────────────────────────────────────────────────

    def _setup_output(self):
        if not self.output_enabled:
            return
        from tom_core.voice.tts import make_tts
        self._tts_adapter = make_tts(self.config)
        self._edge_tts_ok = bool(self._tts_adapter and self._tts_adapter.name == "edge")
        if self._tts_adapter is None:
            self._ensure_sapi()

    def _ensure_sapi(self) -> bool:
        """pyttsx3/SAPI: the local voice of last resort, so a TTS failure is never silence."""
        if self._tts_engine is not None:
            return True
        try:
            import pyttsx3
            self._tts_engine = pyttsx3.init()
            # SAPI words per minute; 200 ≈ the Windows voice's TOM_TTS_RATE 1.15 (SAPI's own default is ~175)
            rate = int(os.environ.get("VOICE_RATE", "200"))
            volume = float(os.environ.get("VOICE_VOLUME", "1.0"))
            self._tts_engine.setProperty("rate", rate)
            self._tts_engine.setProperty("volume", volume)
            self._choose_sapi_voice()
            return True
        except Exception as exc:
            if self._tts_adapter is None:
                self.output_enabled = False
            self._output_error = str(exc)
            return False

    def _choose_sapi_voice(self) -> None:
        """Same voice rules as the Windows adapter (gender, then US English), instead of SAPI's default."""
        try:
            from tom_core.voice.tts import choose_voice
            voices = list(self._tts_engine.getProperty("voices") or [])
            idx = choose_voice([(v.name, str((v.languages or [""])[0]), v.gender or "") for v in voices],
                               self.config.tts_voice_preference, self.config.tts_gender)
            if idx is not None:
                self._tts_engine.setProperty("voice", voices[idx].id)
        except Exception:
            pass  # keep SAPI's default voice rather than no voice

    def _asr_engine(self):
        if self._asr is None:
            from tom_core.voice.asr import make_asr
            self._asr = make_asr(self.config)
        return self._asr

    def warm_up_recognizer(self) -> None:
        """Load the speech model in the background so the first utterance isn't slowed by it."""
        asr = self._asr_engine()
        if hasattr(asr, "warm_up"):
            def _run():
                try:
                    asr.warm_up()
                except Exception as exc:
                    self._input_error = str(exc)
            threading.Thread(target=_run, name="tom-asr-warmup", daemon=True).start()

    def release_recognizer(self) -> None:
        """Unload the speech model (frees its VRAM/RAM, PRD RRM-006); it reloads on next use."""
        asr, self._asr = self._asr, None
        if asr is not None:
            try:
                asr.close()
            except Exception:
                pass

    # ── Status ───────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        adapter = self._tts_adapter
        voice_engine = adapter.name if adapter else ("pyttsx3" if self._tts_engine else "none")
        voice_name = (getattr(adapter, "voice", "") or ("auto (US English preferred)" if voice_engine == "windows" else "")
                      ) if adapter else "system"
        return {
            "voice_input_enabled": self.input_enabled,
            "voice_output_enabled": self.output_enabled,
            "voice_engine": voice_engine,
            "voice_name": voice_name,
            "recognition_engine": self.recognition_engine,
            "asr_cloud": self.config.asr_is_cloud,
            "tts_cloud": self.config.tts_is_cloud,
            "voice_input_error": self._input_error,
            "voice_output_error": self._output_error,
            "conversation_active": self._conv_active,
        }

    # ── Speak ────────────────────────────────────────────────────────────

    def speak(self, text: str, timeout_seconds: int = 30) -> Dict[str, Any]:
        if not self.output_enabled:
            return {"status": "skipped", "message": "Voice output disabled"}
        from tom_core.voice.tts import speech_text
        text = speech_text(text)
        if not text:
            return {"status": "skipped", "message": "Nothing to say"}
        self._speech_stop.clear()
        self._speaking = True
        try:
            if self._tts_adapter is not None:
                result = self._speak_adapter(text, timeout_seconds)
                if result["status"] != "error":
                    return result
                # The preferred engine failed: fall back to the local SAPI voice, never silence.
                self._output_error = result["message"]
                if not self._ensure_sapi():
                    return result
            return self._speak_pyttsx3(text, timeout_seconds)
        finally:
            self._speaking = False

    def _speak_adapter(self, text: str, timeout_seconds: int) -> Dict[str, Any]:
        adapter = self._tts_adapter
        result = {"status": "success", "message": f"Spoken ({adapter.name})"}

        def _run():
            clip = None
            try:
                clip = adapter.synthesize(text[:2000])
                result["voice"] = clip.voice
                if self._speech_stop.is_set():
                    result.update({"status": "stopped", "message": "Voice playback stopped."})
                    return
                self._play_audio(clip.path)
                if self._speech_stop.is_set():
                    result.update({"status": "stopped", "message": "Voice playback stopped."})
            except Exception as exc:
                result["status"] = "error"
                result["message"] = f"{adapter.name} voice failed: {exc}"
            finally:
                try:
                    if clip and os.path.isfile(clip.path):
                        os.remove(clip.path)
                except OSError:
                    pass

        worker = threading.Thread(target=_run, daemon=True)
        worker.start()
        worker.join(timeout=max(5, timeout_seconds))
        if worker.is_alive():
            # Not "error": the clip may still be playing, so no SAPI fallback (no double speech).
            self.stop_speaking()
            return {"status": "timeout", "message": f"Voice output timed out after {timeout_seconds}s"}
        return result

    def speak_async(self, text: str, timeout_seconds: int = 30) -> threading.Thread:
        result = {}
        def _run():
            r = self.speak(text, timeout_seconds)
            result.update(r)
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t

    def stop_speaking(self) -> Dict[str, Any]:
        """Interrupt playback without disabling voice for a future response."""
        self._speech_stop.set()
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                try:
                    pygame.mixer.music.unload()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if self._tts_engine:
                self._tts_engine.stop()
        except Exception:
            pass
        return {"status": "stopped", "message": "Voice playback stopped."}

    def _play_audio(self, filepath: str):
        # Try pygame first.
        # FIX: catch EVERY pygame failure (pygame.error from mixer.init when the
        # audio device is busy/missing, etc.) — previously only ImportError was
        # caught, so one pygame hiccup skipped ALL fallback players and TOM went
        # silent. Also unload() afterwards: pygame keeps the mp3 LOCKED on
        # Windows, which made the next edge-tts save fail with WinError 32.
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy() and not self._speech_stop.is_set():
                pygame.time.wait(50)
            if self._speech_stop.is_set():
                pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()  # release file lock (pygame >= 2.0)
            except Exception:
                pass
            return
        except Exception as _pg_err:
            self._output_error = f"pygame playback unavailable ({_pg_err}); using fallback player."

        # Fallback: use ffplay (from ffmpeg) — handles mp3 natively
        try:
            for cmd in ["ffplay", r"C:\ffmpeg\bin\ffplay.exe"]:
                try:
                    subprocess.run(
                        [cmd, "-nodisp", "-autoexit", "-loglevel", "quiet", filepath],
                        timeout=30, capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                    return
                except FileNotFoundError:
                    continue
        except Exception:
            pass

        # Fallback: use Windows Media Player COM via PowerShell
        try:
            ps_script = (
                f"Add-Type -AssemblyName presentationCore; "
                f"$p = New-Object System.Windows.Media.MediaPlayer; "
                f"$p.Open([Uri]'{filepath}'); "
                f"Start-Sleep -Milliseconds 300; "
                f"$p.Play(); "
                f"while($p.Position -lt $p.NaturalDuration.TimeSpan) {{ Start-Sleep -Milliseconds 200 }}; "
                f"$p.Close()"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                timeout=30, capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            return
        except Exception:
            pass

        # Last resort: open with default player
        try:
            os.startfile(filepath)
            time.sleep(3)
        except Exception:
            pass

    def _speak_pyttsx3(self, text: str, timeout_seconds: int) -> Dict[str, Any]:
        if not self._tts_engine:
            return {"status": "error", "message": "No TTS engine available"}
        result = {"status": "success", "message": "Spoken (pyttsx3)"}
        def _run():
            try:
                self._tts_engine.say(text)
                self._tts_engine.runAndWait()
            except Exception as exc:
                result["status"] = "error"
                result["message"] = f"pyttsx3 failed: {exc}"
        worker = threading.Thread(target=_run, daemon=True)
        worker.start()
        worker.join(timeout=max(3, timeout_seconds))
        if worker.is_alive():
            try:
                self._tts_engine.stop()
            except Exception:
                pass
            return {"status": "error", "message": f"Voice timed out after {timeout_seconds}s"}
        return result

    # ── Listen ───────────────────────────────────────────────────────────

    @staticmethod
    def _compute_rms(raw_data: bytes) -> float:
        """Compute RMS energy level (0.0-1.0) from raw 16-bit PCM audio."""
        import struct
        count = len(raw_data) // 2
        if count == 0:
            return 0.0
        shorts = struct.unpack(f"<{count}h", raw_data[:count * 2])
        sq_sum = sum(s * s for s in shorts)
        return min(1.0, math.sqrt(sq_sum / count) / 16000.0)

    def listen_neural(self, timeout: int = 7) -> Dict[str, Any]:
        if not self.input_enabled or not self._recognizer:
            return {"status": "skipped", "message": "Voice input disabled", "text": ""}
        if self._speaking:
            time.sleep(0.3)
            return {"status": "skipped", "message": "Waiting for speech to finish", "text": ""}

        self._listen_stop.clear()
        self._listen_cancelled = False
        try:
            from tom_core.voice.capture import CaptureSettings, record

            settings = CaptureSettings(start_timeout=float(timeout),
                                       end_silence=self.config.listen_end_silence,
                                       max_seconds=self.config.listen_max_seconds)
            with self._microphone() as (read, rate, width):
                if self.on_state_change:
                    self.on_state_change("listening", "")
                rec = record(read, rate, sample_width=width, settings=settings, stop=self._listen_stop,
                             on_level=self.on_audio_level, noise_floor=self._noise_floor)
            self._noise_floor = rec.noise_floor
            if self.on_audio_level:
                self.on_audio_level(0.0)
            if self._listen_cancelled:
                return {"status": "cancelled", "message": "Listening cancelled.", "text": ""}
            if not rec.pcm:
                return {"status": "timeout", "message": "No speech detected.", "text": ""}

            if self.on_state_change:
                self.on_state_change("transcribing", "")
            heard = self._asr_engine().transcribe_wav(_wav_16k(rec.pcm, rec.sample_rate, rec.sample_width))
            if not heard.text:
                return {"status": "error", "message": "Could not understand audio.", "text": ""}
            return {"status": "success", "message": "Voice recognized", "text": heard.text,
                    "engine": heard.engine, "asr_seconds": heard.seconds,
                    "audio_seconds": round(rec.seconds, 2), "ended_by": rec.reason}

        except Exception as exc:
            if self.on_audio_level:
                self.on_audio_level(0.0)
            from tom_core.voice.asr import ASRError
            if isinstance(exc, ASRError):
                return {"status": "error", "message": str(exc), "text": ""}
            err = str(exc)
            if "PortAudio" in err or "Pa_" in err or "No Default" in err or "Invalid input device" in err:
                return {"status": "error", "message": "Microphone not available.", "text": ""}
            return {"status": "error", "message": f"Voice input failed: {err}", "text": ""}

    @contextmanager
    def _microphone(self):
        """(read, sample_rate, sample_width) of the configured microphone (VOICE_MIC_INDEX or default)."""
        import speech_recognition as sr
        mic_kwargs = {}
        mic_index = os.environ.get("VOICE_MIC_INDEX", "").strip()
        if mic_index.isdigit():
            mic_kwargs["device_index"] = int(mic_index)
        with sr.Microphone(**mic_kwargs) as source:
            yield (lambda: source.stream.read(source.CHUNK)), source.SAMPLE_RATE, source.SAMPLE_WIDTH

    def finish_listening(self) -> None:
        """End the current request now and recognise what was said (Talk pressed again)."""
        self._listen_stop.set()

    def cancel_listening(self) -> None:
        """Stop listening and throw the audio away (Stop pressed)."""
        self._listen_cancelled = True
        self._listen_stop.set()

    def listen_once(self) -> Dict[str, Any]:
        return self.listen_neural(timeout=self.listen_timeout)

    # ── Continuous Voice Conversation Mode ───────────────────────────────

    def start_conversation_mode(
        self,
        process_fn: Callable,
        on_status: Callable = None,
        *,
        blocking: bool = False,
    ):
        if self._conv_active:
            return {"status": "already_active", "message": "Conversation mode is already running."}

        if not self.input_enabled or not self._recognizer:
            self.input_enabled = True
            self._setup_input()
            if not self._recognizer:
                return {"status": "error", "message": f"Cannot start voice mode: {self._input_error}"}

        if not self.output_enabled:
            self.output_enabled = True
            self._setup_output()

        self._conv_stop.clear()
        self._conv_active = True
        self._noise_floor = None  # fresh noise-floor estimate per session
        self.warm_up_recognizer()  # model loads while the greeting plays

        def _notify(state, text=""):
            if on_status:
                try:
                    on_status(state, text)
                except Exception:
                    pass

        def _loop():
            import speech_recognition as sr

            _notify("ready", "Voice mode active. I'm listening...")
            greeting = "Hello, I'm listening. How can I help?"
            _notify("speaking", f"TOM: {greeting}")
            _greet_res = self.speak(greeting, timeout_seconds=10)
            if _greet_res.get("status") not in ("success", "skipped"):
                _notify("error", f"Voice output problem: {_greet_res.get('message')} "
                                 f"(say 'voice check' in chat for a full diagnosis)")

            consecutive_timeouts = 0

            while not self._conv_stop.is_set():
                try:
                    _notify("listening", "Listening...")

                    result = self.listen_neural(timeout=self.listen_timeout)

                    if self._conv_stop.is_set():
                        break

                    if result.get("status") == "timeout":
                        consecutive_timeouts += 1
                        if consecutive_timeouts >= 4:
                            _notify("idle", "Still here if you need me.")
                            consecutive_timeouts = 0
                        continue

                    if result.get("status") != "success" or not result.get("text"):
                        continue

                    consecutive_timeouts = 0
                    heard = result["text"].strip()

                    if not heard:
                        continue

                    lower = heard.lower().strip()

                    # Stop commands
                    if lower in ("stop", "exit", "quit", "stop listening", "end conversation",
                                 "goodbye", "bye", "stop talking", "shut up", "that's all",
                                 "thanks bye", "ok bye", "that's all for now"):
                        farewell = "Okay. I'll be here whenever you need me."
                        _notify("speaking", f"TOM: {farewell}")
                        self.speak(farewell, timeout_seconds=8)
                        _notify("idle", "Voice conversation ended.")
                        break

                    _notify("processing", f"You: \"{heard}\"")

                    # Process the command
                    try:
                        fn_result = process_fn(heard)
                        if asyncio.iscoroutine(fn_result):
                            loop = asyncio.new_event_loop()
                            response = loop.run_until_complete(fn_result)
                            loop.close()
                        else:
                            response = fn_result
                        if isinstance(response, dict):
                            response = response.get("message", str(response))
                        response = str(response).strip()
                    except Exception as e:
                        response = "Sorry, I hit an error on that one."
                        _notify("error", str(e))

                    if not response:
                        response = "Hmm, I didn't have a good answer for that."

                    # Speak response — BLOCKING so we finish before listening again
                    display = f"TOM: \"{response[:120]}...\"" if len(response) > 120 else f"TOM: \"{response}\""
                    _notify("speaking", display)
                    _spk = self.speak(response[:500], timeout_seconds=30)
                    if _spk.get("status") not in ("success", "skipped"):
                        _notify("error", f"Voice output problem: {_spk.get('message')}")

                except KeyboardInterrupt:
                    _notify("idle", "Voice conversation interrupted.")
                    break
                except Exception as e:
                    _notify("error", f"Voice error: {e}")
                    if self._conv_stop.is_set():
                        break
                    time.sleep(0.5)

            self._conv_active = False
            self.release_recognizer()

        self._conv_thread = threading.Thread(target=_loop, daemon=True, name="tom-voice-conv")
        self._conv_thread.start()

        if blocking:
            self._conv_thread.join()

        return {"status": "started", "message": "Voice conversation mode active. Say 'stop' or 'bye' to end."}

    def stop_conversation_mode(self) -> Dict[str, Any]:
        self.stop_speaking()
        self.cancel_listening()
        if not self._conv_active:
            return {"status": "not_active", "message": "Conversation mode is not running."}
        self._conv_stop.set()
        if self._conv_thread and self._conv_thread.is_alive():
            self._conv_thread.join(timeout=5)
        self._conv_active = False
        self.release_recognizer()
        return {"status": "stopped", "message": "Conversation mode stopped."}

    @property
    def conversation_active(self) -> bool:
        return self._conv_active

    # ── Audio Level Monitor (for UI) ─────────────────────────────────────

    class AudioLevelMonitor:
        def __init__(self):
            self.current_level = 0.0
            self.peak_level = 0.0
            self._lock = threading.Lock()

        def update(self, level: float):
            with self._lock:
                self.current_level = level
                self.peak_level = max(self.peak_level, level)

        def get_level(self) -> float:
            with self._lock:
                return self.current_level

        def reset_peak(self):
            with self._lock:
                self.peak_level = 0.0

    # ── Self-test: one command tells you exactly what is broken ──────────
    def self_test(self) -> Dict[str, Any]:
        """Diagnose the whole voice stack without needing a conversation."""
        import socket
        report: Dict[str, Any] = {"env": {
            "VOICE_INPUT_ENABLED": os.environ.get("VOICE_INPUT_ENABLED", "(unset → false)"),
            "VOICE_OUTPUT_ENABLED": os.environ.get("VOICE_OUTPUT_ENABLED", "(unset → false)"),
            "engine": self.recognition_engine,
            "energy_threshold": self.energy_threshold,
        }}
        # microphones
        try:
            import speech_recognition as sr
            names = sr.Microphone.list_microphone_names()
            report["microphones"] = names[:10]
            report["mic_count"] = len(names)
        except Exception as exc:
            report["microphones"] = []
            report["mic_count"] = 0
            report["mic_error"] = str(exc)
        # playback
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            report["pygame_audio"] = "OK"
            pygame.mixer.quit()
        except Exception as exc:
            report["pygame_audio"] = f"FAILED: {exc} (fallback players will be used)"
        # network — only for the cloud engines actually selected (ADR-005: they are opt-in)
        cloud_checks = []
        if self.config.asr_is_cloud:
            cloud_checks.append(("google_stt_reachable", "speech.googleapis.com"))
        if self.config.tts_is_cloud:
            cloud_checks.append(("edge_tts_reachable", "speech.platform.bing.com"))
        for label, host in cloud_checks:
            try:
                socket.create_connection((host, 443), timeout=3).close()
                report[label] = True
            except OSError:
                report[label] = False
        # local engines
        report["asr_engine"] = self.config.asr_engine
        report["tts_engine"] = self.config.tts_engine
        if not self.config.asr_is_cloud:
            report["asr_model"] = self.config.asr_model
            report["asr_model_found"] = bool(os.path.isdir(self.config.asr_model) or self.config.model_dir())
        if self._tts_adapter is not None and self._tts_adapter.name == "windows":
            try:
                voices = self._tts_adapter.voices()
                report["windows_voices"] = [f"{v['name']} ({v['language']})" for v in voices]
                report["us_english_female_voice"] = any(
                    v["language"].lower() == "en-us" and v.get("gender") == "female" for v in voices)
            except Exception as exc:
                report["windows_voices"] = []
                report["windows_voice_error"] = str(exc)
        report["input_error"] = self._input_error
        report["output_error"] = self._output_error
        # verdicts
        problems = []
        if report["mic_count"] == 0:
            problems.append("No microphone detected — check Windows Settings > Privacy "
                            "& security > Microphone (allow desktop apps), and that a mic is plugged in/enabled.")
        if report.get("asr_model_found") is False:
            problems.append(f"Local speech model '{self.config.asr_model}' not found in "
                            f"{', '.join(self.config.asr_model_dirs)} — set TOM_ASR_MODEL_DIR to a faster-whisper "
                            "cache that has it (TOM never downloads models).")
        if report.get("google_stt_reachable") is False:
            problems.append("Google speech service unreachable (cloud ASR is selected) — check the connection, "
                            "or switch back to local recognition: VOICE_RECOGNITION_ENGINE=local.")
        if report.get("edge_tts_reachable") is False:
            problems.append("Edge-TTS unreachable (cloud voice is selected) — the local Windows voice will be used.")
        if report.get("windows_voice_error"):
            problems.append(f"Windows voices unavailable: {report['windows_voice_error']}")
        if report.get("us_english_female_voice") is False:
            report["tip"] = ("No female US English voice found: Settings > Time & language > Speech > "
                             "Manage voices > Add voices > English (United States). TOM picks it up automatically.")
        if str(report.get("pygame_audio", "")).startswith("FAILED"):
            problems.append("Audio playback device issue — check output device / drivers; "
                            "fallback players (ffplay/PowerShell) will be tried automatically.")
        report["problems"] = problems
        report["verdict"] = "ALL CLEAR — voice should work." if not problems else             f"{len(problems)} problem(s) found."
        return report

    def self_test_text(self) -> str:
        r = self.self_test()
        lines = [f"Voice self-test: {r['verdict']}",
                 f"  Mics detected: {r['mic_count']}"
                 + (f" (first: {r['microphones'][0]})" if r.get("microphones") else ""),
                 f"  Playback (pygame): {r['pygame_audio']}",
                 f"  Speech recognition: {r['asr_engine']}"
                 + (f" (model {r.get('asr_model')}, found: {r.get('asr_model_found')})" if 'asr_model' in r else
                    f" (cloud, reachable: {r.get('google_stt_reachable')})"),
                 f"  Voice: {r['tts_engine']}"
                 + (f" — installed: {', '.join(r['windows_voices'])}" if r.get("windows_voices") else "")
                 + (f" (cloud, reachable: {r.get('edge_tts_reachable')})" if 'edge_tts_reachable' in r else ""),
                 f"  Env: input={r['env']['VOICE_INPUT_ENABLED']} output={r['env']['VOICE_OUTPUT_ENABLED']} "
                 f"engine={r['env']['engine']} threshold={r['env']['energy_threshold']}"]
        if r.get("mic_error"):
            lines.append(f"  Mic error: {r['mic_error']}")
        for p in r["problems"]:
            lines.append(f"  FIX: {p}")
        if r.get("tip"):
            lines.append(f"  TIP: {r['tip']}")
        return "\n".join(lines)
