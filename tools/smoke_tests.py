"""Smoke tests for TOM desktop packaging and core flows.

Run:
  python tools/smoke_tests.py

These checks cover:
  - imports
  - voice input/output disabled behavior
  - file creation
  - agent name/capability routing
  - a headless UI chat roundtrip with a fake agent
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _assert(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


def test_imports():
    import tom_desktop_app  # noqa: F401
    from agent import TomAgent  # noqa: F401
    from tools.voice_tools import VoiceTools  # noqa: F401
    from tools.file_tools import FileTools  # noqa: F401
    return True


def test_voice_disabled():
    os.environ["VOICE_INPUT_ENABLED"] = "false"
    os.environ["VOICE_OUTPUT_ENABLED"] = "false"

    from tools.voice_tools import VoiceTools

    voice = VoiceTools()
    status = voice.status()
    _assert(status["voice_input_enabled"] is False, "Voice input should be disabled")
    _assert(status["voice_output_enabled"] is False, "Voice output should be disabled")
    _assert(voice.listen_once()["status"] == "skipped", "listen_once should skip when disabled")
    _assert(voice.speak("hello")["status"] == "skipped", "speak should skip when disabled")
    return True


def test_file_creation():
    from tools.file_tools import FileTools

    with tempfile.TemporaryDirectory() as temp_dir:
        cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            file_tools = FileTools()
            result = asyncio.run(file_tools.write_file("smoke_test.txt", "Hello TOM"))
            _assert(result["status"] == "success", "File creation should succeed")
            _assert(Path("smoke_test.txt").exists(), "Expected file was not created")
        finally:
            os.chdir(cwd)
    return True


def test_agent_routing():
    from agent import TomAgent

    agent = TomAgent.__new__(TomAgent)
    agent.action_keywords = ["create file", "build agent", "send email"]
    agent.chat_memory = type("Memory", (), {"build_context": lambda self, query, recent_n=14, relevant_n=10, max_chars=5000: ""})()

    _assert(agent._is_build_agent_request("build agent for instagram"), "build-agent detection failed")
    _assert(agent._infer_agent_name("build agent for instagram and email") == "instagram_news_to_email_agent", "agent name inference failed")
    caps = agent._infer_capabilities("build agent for instagram and email tech news")
    _assert("open_instagram" in caps, "instagram capability missing")
    _assert("send_email_message" in caps, "email capability missing")
    _assert("classify_tech_news" in caps, "news capability missing")
    return True


def test_ui_chat_roundtrip():
    import tom_desktop_app

    class FakeAgent:
        async def execute_task(self, text):
            return {"message": f"Echo: {text}", "experience_id": 123}

        async def give_reward(self, experience_id, reward):
            return {"message": f"reward={reward} for {experience_id}"}

        async def revise_response_with_feedback(self, user_command, previous_response, feedback):
            return {"message": f"Revised: {user_command} | {feedback}"}

    def fake_startup(self):
        self._enqueue(self._set_status, "Ready")
        self.agent = FakeAgent()
        self.agent_ready = True
        self._enqueue(self._append_chat, "assistant", "Hi, I am TOM. What should we build or automate today?")

    original_startup = tom_desktop_app.TomDesktopApp._startup
    tom_desktop_app.TomDesktopApp._startup = fake_startup

    root = None
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        app = tom_desktop_app.TomDesktopApp(root)

        deadline = time.time() + 5
        while not app.agent_ready and time.time() < deadline:
            root.update()
            time.sleep(0.05)

        _assert(app.agent_ready, "App should be ready in smoke test")
        app.input_var.set("hello TOM")
        if hasattr(app, "_input_has_placeholder"):
            app._input_has_placeholder = False
        app.send_message()

        deadline = time.time() + 5
        while app.processing and time.time() < deadline:
            root.update()
            time.sleep(0.05)

        root.update()
        _assert("Echo:" in app.last_response_message and "hello TOM" in app.last_response_message,
                "UI chat roundtrip failed")
        return True
    finally:
        tom_desktop_app.TomDesktopApp._startup = original_startup
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass


def main():
    checks = [
        ("imports", test_imports),
        ("voice_disabled", test_voice_disabled),
        ("file_creation", test_file_creation),
        ("agent_routing", test_agent_routing),
        ("ui_chat_roundtrip", test_ui_chat_roundtrip),
    ]

    for name, check in checks:
        print(f"[TOM smoke] running {name}...")
        check()
        print(f"[TOM smoke] {name}: ok")

    print("[TOM smoke] all checks passed")


if __name__ == "__main__":
    main()
