from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import MethodType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent import TomAgent
from tools.capability_resolver import CapabilityResolver
from tools.command_router import CommandRouter
from tools.nlp_parser import CommandParser
from tools.skill_manager import SkillManager


class FakeSafety:
    async def is_action_safe(self, command: str):
        return {"safe": True}

    def log_action(self, *args, **kwargs):
        return None


class FakeApproval:
    def request_approval(self, request):
        return True


class FakeMemory:
    def append(self, *args, **kwargs):
        return None

    def build_context(self, *args, **kwargs):
        return ""


class FakeLearner:
    def log_experience(self, *args, **kwargs):
        return None


class FakePluginManager:
    def match_plugin(self, command):
        return None


class FakeFileTools:
    def __init__(self):
        self.calls = []

    async def create_word_document(self, file_name, **kwargs):
        self.calls.append(("word", file_name, kwargs))
        return {"status": "success", "message": "word ok", "path": f"sandbox/{file_name}"}

    async def create_excel_workbook(self, file_name, **kwargs):
        self.calls.append(("excel", file_name, kwargs))
        return {"status": "success", "message": "excel ok", "path": f"sandbox/{file_name}"}

    async def create_powerpoint(self, file_name, **kwargs):
        self.calls.append(("powerpoint", file_name, kwargs))
        return {"status": "success", "message": "powerpoint ok", "path": f"sandbox/{file_name}"}

    async def create_website(self, project_name, index_content=None, css_content=None):
        self.calls.append(("website", project_name, {"index": index_content, "css": css_content}))
        return {"status": "success", "message": "website ok", "path": f"sandbox/{project_name}"}

    async def write_file(self, filepath, content):
        self.calls.append(("write_file", filepath, content))
        return {"status": "success", "message": f"wrote {filepath}", "bytes_written": len(content)}

    def open_file(self, filepath):
        self.calls.append(("open_file", filepath, {}))


class FakeEmailTools:
    def __init__(self):
        self.calls = []

    async def draft_email_with_llm(self, recipient, prompt, llm):
        self.calls.append(("draft", recipient, prompt))
        return {"status": "success", "message": f"drafted {recipient}", "recipient": recipient}

    async def send_email(self, recipient, subject, body, approval_callback=None):
        if approval_callback:
            approved = await approval_callback(recipient, subject, body)
            if not approved:
                return {"status": "cancelled", "message": "cancelled"}
        self.calls.append(("send", recipient, subject, body))
        return {"status": "success", "message": f"sent {recipient}", "recipient": recipient}


class FakeOSTools:
    def __init__(self):
        self.calls = []

    async def open_application(self, app_name):
        self.calls.append(("open", app_name))
        return {"status": "success", "message": f"opened {app_name}", "app": app_name}


class FakeWhatsAppTools:
    async def send_message(self, contact_name, message):
        return {"status": "success", "message": f"sent whatsapp to {contact_name}"}

    async def open_whatsapp(self):
        return {"status": "success", "message": "opened whatsapp"}


async def fake_invoke_llm(self, chain, payload, task_name, llm=None):
    payload = payload or {}
    if task_name == "word_doc":
        content = json.dumps({
            "title": "Sandbox Letter",
            "sections": [{"type": "paragraph", "text": "Sandbox body"}],
        })
    elif task_name == "excel":
        content = json.dumps({
            "sheets": [{"name": "Budget", "headers": ["Item", "Cost"], "data": [["Hosting", 10]]}],
        })
    elif task_name == "presentation":
        content = json.dumps({
            "title": "Sandbox Deck",
            "slides": [{"title": "Overview", "content": ["One", "Two", "Three"]}],
        })
    elif task_name == "website":
        content = json.dumps({
            "index_html": "<!doctype html><html><body><h1>Sandbox</h1></body></html>",
            "style_css": "body{font-family:Arial}",
        })
    elif task_name == "code_project":
        content = "--- FILE: sandbox_app/README.md ---\n# Sandbox App\n\n--- FILE: sandbox_app/server.py ---\nprint('ok')\n"
    elif task_name == "data_analysis":
        content = "--- FILE: sandbox_analysis.py ---\nprint('analysis ok')\n"
    elif task_name == "email_draft_for_send":
        content = "SUBJECT: Sandbox\nBODY:\nHello from sandbox."
    elif task_name == "skill_route":
        content = "Sandbox skill response."
    else:
        content = "Sandbox response."
    return SimpleNamespace(content=content)


def build_agent() -> TomAgent:
    agent = TomAgent.__new__(TomAgent)
    agent.safety = FakeSafety()
    agent.approval_manager = FakeApproval()
    agent.chat_memory = FakeMemory()
    agent.learner = FakeLearner()
    agent.rag = SimpleNamespace(available=False)
    agent.evolution = None
    agent.nlp_parser = CommandParser()
    agent.command_router = CommandRouter()
    agent.skill_manager = SkillManager()
    agent.capability_resolver = CapabilityResolver()
    agent.plugin_manager = FakePluginManager()
    agent.file_tools = FakeFileTools()
    agent.email_tools = FakeEmailTools()
    agent.os_tools = FakeOSTools()
    agent.whatsapp_tools = FakeWhatsAppTools()
    agent.chrome_profiles = SimpleNamespace(launch_profile=lambda query: {"status": "success", "message": query})
    agent.browser_tools = None
    agent.mcp = None
    agent.llm = object()
    agent.fast_llm = object()
    agent.code_llm = object()
    agent.engine_router = None
    agent.model_timeout_seconds = 5
    agent.task_timeout_seconds = 30
    agent._last_command = ""
    agent._last_response = ""
    agent._last_result = None
    agent._last_exp_id = None
    agent._invoke_llm = MethodType(fake_invoke_llm, agent)
    return agent


async def main() -> int:
    agent = build_agent()
    cases = [
        ("create a word document about leave letter", "word"),
        ("create an excel budget tracker", "excel"),
        ("create a powerpoint presentation about AI", "powerpoint"),
        ("write email to john@example.com about meeting", "draft"),
        ("send email to john@example.com saying hello", "send"),
        ("open vs code", "open"),
        ("create website called demo website", "website"),
        ("build a full stack web app with login and API routes", "write_file"),
        ("analyze excel sales.xlsx", "write_file"),
        ("ethical hacking checklist for web app", "skill_route"),
    ]
    results = {}
    for command, expected in cases:
        before_file = len(agent.file_tools.calls)
        before_email = len(agent.email_tools.calls)
        before_os = len(agent.os_tools.calls)
        result = await agent.execute_task(command)
        if result.get("status") != "success":
            raise AssertionError(f"{command}: expected success, got {result}")
        results[command] = result.get("response_type") or result.get("message", "")

        calls = (
            agent.file_tools.calls[before_file:]
            + agent.email_tools.calls[before_email:]
            + agent.os_tools.calls[before_os:]
        )
        if expected == "skill_route":
            if result.get("response_type") != "skill_route":
                raise AssertionError(f"{command}: expected skill_route, got {result}")
        elif not any(call[0] == expected for call in calls):
            raise AssertionError(f"{command}: expected call {expected}, calls={calls}")

    print("sandbox functional tests passed")
    print(json.dumps({"cases": len(cases)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
