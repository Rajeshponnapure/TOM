"""Routing + flow for "send an email", "inbox", WhatsApp and other chat apps."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from types import SimpleNamespace

import pytest

from tools.approval import ApprovalManager
from tools.command_router import CommandRouter
from tools.nlp_parser import CommandParser

ROUTER = CommandRouter()


@pytest.mark.parametrize("command", [
    "send an email to john@example.com saying the report is ready",
    "send email to john@example.com saying hi",
    "send mail to john@example.com about the meeting",
    "send the email to john@example.com",
    "send an email to john about the review",     # "review" must not mean "review my inbox"
    "Please send a mail to HR about leave",
])
def test_send_requests_are_sent_with_approval(command):
    route = ROUTER.route(command)
    assert route.handler == "execute_email_send" and route.needs_approval
    assert CommandParser()._detect_intent(command) == "send_email"


@pytest.mark.parametrize("command", [
    "check my emails", "summarize my inbox", "review my emails",
    "send me an email summary of my inbox",
])
def test_inbox_requests_never_send(command):
    route = ROUTER.route(command)
    assert route.handler == "execute_email_inbox_workflow" and not route.needs_approval


@pytest.mark.parametrize("command", [
    "write an email to john@example.com about the budget",
    "draft an email to my manager about leave",
])
def test_writing_an_email_only_drafts(command):
    route = ROUTER.route(command)
    assert route.handler == "execute_email_task" and not route.needs_approval


class _Tools:
    def __init__(self):
        self.sent = []

    async def send_email(self, recipient, subject, body, attachments=None, approval_callback=None):
        if not await approval_callback(recipient, subject, body):
            return {"status": "cancelled", "message": "Email sending cancelled by user."}
        self.sent.append((recipient, subject, body))
        return {"status": "success", "message": "Email sent successfully!"}


def _agent(approve):
    from agent import TomAgent
    agent = TomAgent.__new__(TomAgent)
    agent.email_tools = _Tools()
    mgr = ApprovalManager()
    mgr.provider = approve
    agent.approval_manager = mgr
    return agent


BODY = "Hello John, the quarterly report is attached and ready for your review."


def test_approval_prompt_shows_the_real_subject_and_body():
    seen = []
    agent = _agent(lambda req: seen.append(req.summary) or True)
    parsed = {"email_address": "john@example.com", "subject": "Report", "message_body": BODY}
    result = asyncio.run(agent.execute_email_send_flow("send email to john@example.com", parsed))
    assert result["status"] == "success"
    assert "john@example.com" in seen[0] and "Report" in seen[0] and BODY in seen[0]
    assert agent.email_tools.sent == [("john@example.com", "Report", BODY)]


def test_declined_email_is_not_sent():
    agent = _agent(lambda req: False)
    parsed = {"email_address": "john@example.com", "subject": "Report", "message_body": BODY}
    result = asyncio.run(agent.execute_email_send_flow("send email to john@example.com", parsed))
    assert result["status"] == "cancelled" and agent.email_tools.sent == []


def test_a_bare_name_asks_for_the_address_instead_of_hitting_smtp():
    agent = _agent(lambda req: True)
    parsed = {"recipient_name": "Ravi", "message_body": BODY}
    result = asyncio.run(agent.execute_email_send_flow("send an email to Ravi", parsed))
    assert result["status"] == "error" and "Ravi" in result["message"] and "address" in result["message"]
    assert agent.email_tools.sent == []


def test_address_in_the_command_is_found_even_if_the_parser_missed_it():
    agent = _agent(lambda req: True)
    result = asyncio.run(agent.execute_email_send_flow(
        "send an email to john@example.com", {"message_body": BODY, "subject": "Hi"}))
    assert result["status"] == "success"
    assert agent.email_tools.sent[0][0] == "john@example.com"


# ── WhatsApp parsing ─────────────────────────────────────────────────────
@pytest.mark.parametrize("command,contact,message", [
    ("send Madhu a message on WhatsApp saying hello", "Madhu", "hello"),
    ("message Madhu on whatsapp: happy birthday", "Madhu", "happy birthday"),
    ("send hello to Madhu on WhatsApp", "Madhu", "hello"),
    ("send happy birthday to Madhu Sri on whatsapp", "Madhu Sri", "happy birthday"),
    ("send hi, how are you to Madhu on whatsapp", "Madhu", "hi, how are you"),
    ("open whatsapp and text Madhu hello there", "Madhu", "hello there"),
    ("text Madhu on whatsapp saying I'm outside", "Madhu", "I'm outside"),
    ("tell Madhu on whatsapp that the meeting moved", "Madhu", "the meeting moved"),
    ("whatsapp Madhu saying I am late", "Madhu", "I am late"),
])
def test_whatsapp_contact_and_message_are_split_correctly(command, contact, message):
    assert CommandParser()._extract_whatsapp_details(command) == {"contact": contact, "message": message}


def test_whatsapp_web_selector_quotes_are_escaped():
    from tools.whatsapp_tools import _css_quote
    assert _css_quote('O"Brien') == 'O\\"Brien'
    assert _css_quote("a\\b") == "a\\\\b"


# ── chat apps TOM cannot drive ───────────────────────────────────────────
class _OS:
    def __init__(self):
        self.opened = []

    async def open_application(self, name, profile_id=None):
        self.opened.append(name)
        return {"status": "success", "message": f"Opened {name}"}


@pytest.mark.parametrize("command,app", [
    ("open telegram and message Ravi hello", "telegram"),
    ("send hi to Ravi on telegram", "telegram"),
    ("open discord and text Sam hey", "discord"),
    ("open teams and message Bob", "teams"),
])
def test_chat_in_an_unsupported_app_opens_it_but_never_claims_success(command, app):
    from agent import TomAgent
    agent = TomAgent.__new__(TomAgent)
    agent.os_tools = _OS()
    result = asyncio.run(agent.execute_open_command(command))
    assert agent.os_tools.opened == [app]
    assert result["status"] == "unsupported"
    assert "nothing was sent" in result["message"] and "WhatsApp" in result["message"]


@pytest.mark.parametrize("command", ["open telegram", "launch slack", "open notepad and type hello"])
def test_plain_open_still_just_opens(command):
    from agent import TomAgent
    agent = TomAgent.__new__(TomAgent)
    agent.os_tools = _OS()
    result = asyncio.run(agent.execute_open_command(command))
    assert result["status"] == "success"
