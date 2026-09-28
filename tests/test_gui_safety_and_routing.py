"""Approval gate, agent-mode plugin routing and web-automation console capture."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import builtins
from types import SimpleNamespace

from tools.approval import ApprovalManager, ApprovalRequest

REQ = ApprovalRequest(action="send_email", summary="Send email to john@example.com")


def test_approval_uses_gui_provider_when_set():
    seen = []
    mgr = ApprovalManager()
    mgr.provider = lambda req: seen.append(req.action) or True
    assert mgr.request_approval(REQ) is True
    assert seen == ["send_email"]


def test_approval_denies_instead_of_crashing_without_console(monkeypatch):
    # pythonw / the frozen exe have no stdin: input() raises EOFError.
    def no_console(_prompt=""):
        raise EOFError("EOF when reading a line")
    monkeypatch.setattr(builtins, "input", no_console)
    assert ApprovalManager().request_approval(REQ) is False


def test_approval_provider_error_denies():
    mgr = ApprovalManager()
    mgr.provider = lambda req: 1 / 0
    assert mgr.request_approval(REQ) is False


def test_explicit_prompt_fn_still_wins():
    mgr = ApprovalManager()
    mgr.provider = lambda req: False
    assert mgr.request_approval(REQ, prompt_fn=lambda _p: "yes") is True


def _agent_with_plugins():
    from agent import TomAgent
    from tools.plugin_manager import PluginManager
    agent = TomAgent.__new__(TomAgent)
    agent.plugin_manager = PluginManager(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return agent


def test_agent_mode_preamble_does_not_trigger_plugins():
    agent = _agent_with_plugins()
    for mode in ("Email Agent", "Instagram Agent"):
        routed = (f"You are {mode} mode. Use the workflow.\n\n"
                  "User request: Create a professional Word document about remote work")
        assert agent._user_request_text(routed) == "Create a professional Word document about remote work"
        assert not agent._should_use_plugin_route(routed.lower()), mode


def test_explicit_plugin_request_still_routes():
    agent = _agent_with_plugins()
    routed = "You are Email Agent mode.\n\nUser request: run the email agent once"
    assert agent._should_use_plugin_route(routed.lower())
    assert agent._should_use_plugin_route("run the email agent once")


def test_console_capture_reads_playwright_location_dict():
    from tools.web_automation import WebAutomationSuite
    suite = WebAutomationSuite(browser_tools=None)
    msg = SimpleNamespace(type="error", text="boom",
                          location={"url": "http://localhost/app.js", "lineNumber": 7, "columnNumber": 1})
    suite._on_console(msg)
    entry = suite._console_logs[-1]
    assert (entry.source, entry.line, entry.text) == ("http://localhost/app.js", 7, "boom")
