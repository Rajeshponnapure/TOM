"""
Voice I/O for TOM.
Input:  speech_recognition (Google/Whisper) + pyaudio
Output: edge-tts (Microsoft Neural) with pyttsx3 fallback
Mode:   Continuous voice conversation with NLP context
"""
import asyncio
import json
import math
import os
import subprocess
import tempfile
import threading
import time
from typing import Any, Callable, Dict, Optional


class VoiceTools:
    def __init__(self):
        self.input_enabled = os.environ.get("VOICE_INPUT_ENABLED", "false").lower() == "true"
        self.output_enabled = os.environ.get("VOICE_OUTPUT_ENABLED", "false").lower() == "true"
        self.energy_threshold = int(os.environ.get("VOICE_ENERGY_THRESHOLD", "800"))
        self.pause_threshold = float(os.environ.get("VOICE_PAUSE_THRESHOLD", "0.8"))
        self.listen_timeout = int(os.environ.get("VOICE_LISTEN_TIMEOUT", "7"))
        self.phrase_time_limit = int(os.environ.get("VOICE_PHRASE_TIME_LIMIT", "15"))
        self.calibration_duration = float(os.environ.get("VOICE_CALIBRATION_DURATION", "0.5"))

        self.voice_name = os.environ.get("TOM_VOICE", "en-US-GuyNeural")
        self.voice_rate = os.environ.get("TOM_VOICE_RATE", "+0%")
        self.recognition_engine = os.environ.get("VOICE_RECOGNITION_ENGINE", "google")

        self._recognizer = None
        self._tts_engine = None
        self._edge_tts_ok = False
        self._input_error = ""
        self._output_error = ""

        # Conversation mode state
        self._conv_active = False
        self._conv_thread: Optional[threading.Thread] = None
        self._conv_stop = threading.Event()
        self._speaking = False

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
            recognizer = sr.Recognizer()
            recognizer.energy_threshold = self.energy_threshold
            recognizer.dynamic_energy_threshold = True
            recognizer.pause_threshold = self.pause_threshold
            recognizer.non_speaking_duration = 0.4
            recognizer.dynamic_energy_adjustment_damping = 0.15
            recognizer.dynamic_energy_ratio = 1.5
            self._recognizer = recognizer
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
        try:
            import edge_tts
            self._edge_tts_ok = True
        except ImportError:
            self._edge_tts_ok = False

        if not self._edge_tts_ok:
            try:
                import pyttsx3
                self._tts_engine = pyttsx3.init()
                rate = int(os.environ.get("VOICE_RATE", "175"))
                volume = float(os.environ.get("VOICE_VOLUME", "1.0"))
                self._tts_engine.setProperty("rate", rate)
                self._tts_engine.setProperty("volume", volume)
            except Exception as exc:
                self.output_enabled = False
                self._output_error = str(exc)

    # ── Status ───────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        return {
            "voice_input_enabled": self.input_enabled,
            "voice_output_enabled": self.output_enabled,
            "voice_engine": "edge-tts" if self._edge_tts_ok else ("pyttsx3" if self._tts_engine else "none"),
            "voice_name": self.voice_name if self._edge_tts_ok else "system",
            "recognition_engine": self.recognition_engine,
            "voice_input_error": self._input_error,
            "voice_output_error": self._output_error,
            "conversation_active": self._conv_active,
        }

    # ── Speak ────────────────────────────────────────────────────────────

    def speak(self, text: str, timeout_seconds: int = 30) -> Dict[str, Any]:
        if not self.output_enabled:
            return {"status": "skipped", "message": "Voice output disabled"}
        self._speaking = True
        try:
            if self._edge_tts_ok:
                return self._speak_edge_tts(text, timeout_seconds)
            return self._speak_pyttsx3(text, timeout_seconds)
        finally:
            self._speaking = False

    def _speak_edge_tts(self, text: str, timeout_seconds: int) -> Dict[str, Any]:
        result = {"status": "success", "message": "Spoken (edge-tts)"}

        def _run():
            tmp = ""
            try:
                import edge_tts
                # FIX: unique file per utterance — a fixed name gets locked by
                # the player and every later save fails on Windows.
                self._utt_counter = getattr(self, "_utt_counter", 0) + 1
                tmp = os.path.join(tempfile.gettempdir(),
                                   f"tom_voice_{os.getpid()}_{self._utt_counter}.mp3")
                loop = asyncio.new_event_loop()
                communicate = edge_tts.Communicate(text[:2000], self.voice_name, rate=self.voice_rate)
                loop.run_until_complete(communicate.save(tmp))
                loop.close()
                self._play_audio(tmp)
            except Exception as exc:
                result["status"] = "error"
                result["message"] = f"edge-tts failed: {exc}"
            finally:
                # best-effort cleanup of this and older utterance files
                try:
                    if tmp and os.path.isfile(tmp):
                        os.remove(tmp)
                except OSError:
                    pass

        worker = threading.Thread(target=_run, daemon=True)
        worker.start()
        worker.join(timeout=max(5, timeout_seconds))
        if worker.is_alive():
            return {"status": "error", "message": f"Voice output timed out after {timeout_seconds}s"}
        return result

    def speak_async(self, text: str, timeout_seconds: int = 30) -> threading.Thread:
        result = {}
        def _run():
            r = self.speak(text, timeout_seconds)
            result.update(r)
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t

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
            while pygame.mixer.music.get_busy():
                pygame.time.wait(50)
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
                        timeout=30, capture_output=True)
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
                timeout=30, capture_output=True)
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

        try:
            import speech_recognition as sr

            mic_kwargs = {}
            mic_index = os.environ.get("VOICE_MIC_INDEX", "").strip()
            if mic_index.isdigit():
                mic_kwargs["device_index"] = int(mic_index)
            with sr.Microphone(**mic_kwargs) as source:
                # FIX: calibrate ONCE per conversation. Re-calibrating on every
                # listen (with dynamic adjustment on top) ratcheted the energy
                # threshold up until real speech was treated as background noise.
                if not getattr(self, "_calibrated", False):
                    self._recognizer.adjust_for_ambient_noise(
                        source, duration=max(0.3, self.calibration_duration))
                    self._calibrated = True
                if self.on_state_change:
                    self.on_state_change("listening", "")
                if self.on_audio_level:
                    self.on_audio_level(0.3)

                audio = self._recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=self.phrase_time_limit)

            # Compute audio levels from captured data for the UI meter
            if self.on_audio_level:
                try:
                    raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
                    chunk_size = 3200
                    for i in range(0, min(len(raw), chunk_size * 20), chunk_size):
                        level = self._compute_rms(raw[i:i + chunk_size])
                        self.on_audio_level(level)
                except Exception:
                    pass
                self.on_audio_level(0.0)

            if self.recognition_engine == "google":
                text = self._recognizer.recognize_google(audio)
            else:
                text = self._recognizer.recognize_whisper(audio)

            return {"status": "success", "message": "Voice recognized", "text": text.strip()}

        except Exception as exc:
            if self.on_audio_level:
                self.on_audio_level(0.0)
            import speech_recognition as sr
            if isinstance(exc, sr.WaitTimeoutError):
                return {"status": "timeout", "message": "No speech detected.", "text": ""}
            if isinstance(exc, sr.UnknownValueError):
                return {"status": "error", "message": "Could not understand audio.", "text": ""}
            if isinstance(exc, sr.RequestError):
                return {"status": "error", "message": f"Speech service error: {exc}", "text": ""}
            err = str(exc)
            if "PortAudio" in err or "Pa_" in err or "No Default" in err:
                return {"status": "error", "message": "Microphone not available.", "text": ""}
            return {"status": "error", "message": f"Voice input failed: {err}", "text": ""}

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
        self._calibrated = False  # fresh ambient calibration per session

        def _notify(state, text=""):
            if on_status:
                try:
                    on_status(state, text)
                except Exception:
                    pass

        def _loop():
            import speech_recognition as sr

            _notify("ready", "Voice mode active. I'm listening...")
            greeting = "Hey! I'm here. What's up?"
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
                        farewell = "Alright, talk to you later!"
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

        self._conv_thread = threading.Thread(target=_loop, daemon=True, name="tom-voice-conv")
        self._conv_thread.start()

        if blocking:
            self._conv_thread.join()

        return {"status": "started", "message": "Voice conversation mode active. Say 'stop' or 'bye' to end."}

    def stop_conversation_mode(self) -> Dict[str, Any]:
        if not self._conv_active:
            return {"status": "not_active", "message": "Conversation mode is not running."}
        self._conv_stop.set()
        if self._conv_thread and self._conv_thread.is_alive():
            self._conv_thread.join(timeout=5)
        self._conv_active = False
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
        # network for STT (google) and TTS (edge)
        for label, host in (("google_stt_reachable", "speech.googleapis.com"),
                            ("edge_tts_reachable", "speech.platform.bing.com")):
            try:
                socket.create_connection((host, 443), timeout=3).close()
                report[label] = True
            except OSError:
                report[label] = False
        report["input_error"] = self._input_error
        report["output_error"] = self._output_error
        # verdicts
        problems = []
        if report["mic_count"] == 0:
            problems.append("No microphone detected — check Windows Settings > Privacy "
                            "& security > Microphone (allow desktop apps), and that a mic is plugged in/enabled.")
        if not report.get("google_stt_reachable"):
            problems.append("Google speech service unreachable — voice RECOGNITION needs internet; "
                            "check connection/firewall, or set VOICE_RECOGNITION_ENGINE=whisper (offline, needs openai-whisper).")
        if not report.get("edge_tts_reachable"):
            problems.append("Edge-TTS service unreachable — TOM's neural VOICE needs internet; "
                            "pyttsx3 offline fallback will be used if installed.")
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
                 f"  Google STT reachable: {r.get('google_stt_reachable')}",
                 f"  Edge-TTS reachable: {r.get('edge_tts_reachable')}",
                 f"  Env: input={r['env']['VOICE_INPUT_ENABLED']} output={r['env']['VOICE_OUTPUT_ENABLED']} "
                 f"engine={r['env']['engine']} threshold={r['env']['energy_threshold']}"]
        if r.get("mic_error"):
            lines.append(f"  Mic error: {r['mic_error']}")
        for p in r["problems"]:
            lines.append(f"  FIX: {p}")
        return "\n".join(lines)
