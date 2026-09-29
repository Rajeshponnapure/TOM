"""Whole-agent runs through TomAgent.execute_task against fake SMTP/IMAP servers.

The LLM is stubbed; everything else (routing, safety gate, approval, mail I/O)
is the real code path a user's request takes.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from types import SimpleNamespace

import pytest


@pytest.fixture
def agent(tmp_path, monkeypatch, smtp_server, imap_server):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOM_LLM_PROVIDER", "ollama")
    monkeypatch.delenv("GMAIL_CREDENTIALS_FILE", raising=False)
    monkeypatch.setenv("EMAIL_ADDRESS", "tom@example.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "app-pass")
    monkeypatch.setenv("SMTP_SERVER", "127.0.0.1")
    monkeypatch.setenv("SMTP_PORT", str(smtp_server.server_address[1]))
    monkeypatch.setenv("SMTP_STARTTLS", "false")
    monkeypatch.setenv("IMAP_HOST", "127.0.0.1")
    monkeypatch.setenv("IMAP_PORT", str(imap_server.server_address[1]))
    monkeypatch.setenv("IMAP_SSL", "false")
    monkeypatch.setenv("EMAIL_AGENT_STATE_DIR", str(tmp_path / "state"))
    from agent import TomAgent
    tom = TomAgent()

    async def fake_llm(self, chain, payload, task_name, llm=None):
        return SimpleNamespace(content="SUBJECT: Quarterly report\nBODY:\nHello John, the quarterly report is "
                                      "attached and ready for your review. Kind regards, Rajesh")
    monkeypatch.setattr(TomAgent, "_invoke_llm", fake_llm)

    async def no_parse_llm(command):          # regex parse only; no network
        return tom.nlp_parser.parse(command)
    monkeypatch.setattr(tom, "understand_command", no_parse_llm)

    tom.asked = []
    tom.answer = True
    tom.approval_manager.provider = lambda req: tom.asked.append(req) or tom.answer
    return tom


def run(agent, command):
    return asyncio.run(agent.execute_task(command))


def test_send_email_asks_once_shows_the_message_and_delivers(agent, smtp_server):
    result = run(agent, "send an email to john@example.com about the quarterly report")
    assert result["status"] == "success", result
    assert len(agent.asked) == 1, [r.summary for r in agent.asked]        # not twice
    assert "john@example.com" in agent.asked[0].summary
    assert "Quarterly report" in agent.asked[0].summary and "Hello John" in agent.asked[0].summary
    assert len(smtp_server.messages) == 1 and "Subject: Quarterly report" in smtp_server.messages[0]


def test_declining_the_email_sends_nothing(agent, smtp_server):
    agent.answer = False
    result = run(agent, "send email to john@example.com saying the numbers are final and approved")
    assert result["status"] == "cancelled"
    assert smtp_server.messages == [] and smtp_server.connections == 0


def test_writing_an_email_never_sends(agent, smtp_server):
    result = run(agent, "write an email to john@example.com about the quarterly report")
    assert smtp_server.messages == [] and agent.asked == []
    assert result["status"] == "success"


def test_unread_request_returns_only_unread_mail(agent):
    result = run(agent, "check my unread emails")
    assert result["status"] == "success", result
    assert result["emails_reviewed"] == 1 and "Lunch?" in result["message"]


def test_plain_inbox_request_reviews_recent_mail(agent):
    result = run(agent, "summarize my inbox")
    assert result["emails_reviewed"] == 3
    assert result["important_count"] >= 1 and "Urgent: contract deadline" in result["message"]


def test_auto_reply_is_off_by_default_and_drafts_instead(agent, smtp_server, monkeypatch):
    monkeypatch.delenv("EMAIL_AUTO_REPLY_ENABLED", raising=False)
    result = run(agent, "summarize my inbox")
    assert result["auto_replied_count"] == 0 and smtp_server.messages == []
    assert result["draft_reply_count"] >= 1


def test_auto_reply_when_enabled_answers_people_once_and_never_bots(agent, smtp_server, monkeypatch):
    monkeypatch.setenv("EMAIL_AUTO_REPLY_ENABLED", "true")
    first = run(agent, "summarize my inbox")
    recipients = sorted(m.split("To: ")[1].split("\r\n")[0] for m in smtp_server.messages)
    assert recipients == ["boss@corp.com", "sam@friend.org"], recipients      # never noreply@shop.com
    assert first["auto_replied_count"] == 2
    assert all("Sent automatically by TOM" in m for m in smtp_server.messages)
    second = run(agent, "summarize my inbox")                                 # same mail again
    assert second["auto_replied_count"] == 0 and len(smtp_server.messages) == 2


def test_daemon_service_auto_replies_and_dedupes(agent, smtp_server, monkeypatch, tmp_path):
    monkeypatch.setenv("EMAIL_AUTO_REPLY_ENABLED", "true")
    monkeypatch.setenv("EMAIL_IMPORTANT_OPEN_IN_CLIENT", "false")
    from agents.email_agent.service import EmailAgentService
    service = EmailAgentService()
    service.llm = None                                   # canned reply text; no model needed
    first = asyncio.run(service.run_once())
    assert first["auto_replied_count"] == 2 and len(smtp_server.messages) == 2
    again = asyncio.run(service.run_once())
    assert again["auto_replied_count"] == 0 and len(smtp_server.messages) == 2


def test_automated_senders_are_recognised():
    from tools.email_tools import is_automated_sender
    for bot in ("noreply@shop.com", "no-reply@x.io", "mailer-daemon@mail.com", "notifications@github.com",
                "bounce+abc@lists.org", ""):
        assert is_automated_sender(bot), bot
    for person in ("boss@corp.com", "sam@friend.org", "reply.to.me@example.com"):
        assert not is_automated_sender(person), person


def test_draft_never_contains_the_internal_prompt(agent, smtp_server, monkeypatch):
    """A model that ignores the SUBJECT/BODY format must not leak the prompt (or memory) into the draft."""
    from agent import TomAgent

    async def chatty(self, chain, payload, task_name, llm=None):
        return SimpleNamespace(content="Sure! Here is a friendly note thanking John for the quarterly numbers.")
    monkeypatch.setattr(TomAgent, "_invoke_llm", chatty)
    result = run(agent, "write an email to john@example.com about the quarterly report")
    assert result["status"] == "success"
    assert result["body"].startswith("Sure! Here is a friendly note")
    assert "Memory:" not in result["body"] and "Request from the user" not in result["body"]
    assert smtp_server.messages == []


# ── chat apps, end to end through execute_task ──────────────────────────────
from test_chat_apps import api  # noqa: E402,F401  (fake Slack/Discord/Telegram HTTP API)


@pytest.fixture
def chat(agent, api, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_CHATS", '{"Ravi": 555}')
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-good")
    opened = []

    async def fake_open(name, profile_id=None):
        opened.append(name)
        return {"status": "success", "message": f"Opened {name}"}
    monkeypatch.setattr(agent.os_tools, "open_application", fake_open)
    agent.opened = opened
    agent.api = api
    return agent


def test_telegram_message_is_approved_on_the_exact_text_then_sent(chat):
    result = run(chat, "send hi there to Ravi on telegram")
    assert result["status"] == "success" and result["id"] == 42, result
    assert len(chat.asked) == 1
    assert "Ravi" in chat.asked[0].summary and "hi there" in chat.asked[0].summary and "Telegram" in chat.asked[0].summary
    assert chat.api.requests[-1][2] == {"chat_id": 555, "text": "hi there"}


def test_declined_chat_message_is_never_sent(chat):
    chat.answer = False
    result = run(chat, "message Ravi on telegram: secret plan")
    assert result["status"] == "cancelled" and chat.api.requests == []


def test_slack_post_now_needs_approval_and_goes_where_you_said(chat):
    result = run(chat, "post to slack #dev: deploy done")
    assert result["status"] == "success", result
    assert len(chat.asked) == 1 and "#dev" in chat.asked[0].summary
    assert chat.api.requests[-1][2] == {"channel": "#dev", "text": "deploy done"}


def test_vague_slack_request_posts_nothing(chat):
    result = run(chat, "send a message on slack")
    assert result["status"] == "error" and "Nothing was posted" in result["message"]
    assert chat.api.requests == [] and chat.asked == []


def test_unconfigured_chat_app_opens_it_and_explains(chat, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN")
    result = run(chat, "send hi to Ravi on telegram")
    assert result["status"] == "unsupported" and "nothing was sent" in result["message"]
    assert "TELEGRAM_BOT_TOKEN" in result["message"] and chat.opened == ["telegram"]
    assert chat.asked == [] and chat.api.requests == []


def test_whatsapp_request_shows_recipient_and_text_in_the_approval(chat, monkeypatch):
    calls = []

    async def fake_send(contact, message):
        calls.append((contact, message))
        return {"status": "unconfirmed", "sent": True, "message": "sent, unconfirmed"}
    monkeypatch.setattr(chat.whatsapp_tools, "send_message", fake_send)
    result = run(chat, "send Madhu a message on WhatsApp saying hello")
    assert calls == [("Madhu", "hello")]
    assert len(chat.asked) == 1 and "Madhu" in chat.asked[0].summary and "hello" in chat.asked[0].summary
    assert result["status"] == "unconfirmed"

    chat.asked.clear()
    chat.answer = False
    calls.clear()
    assert run(chat, "send Madhu a message on WhatsApp saying hello")["status"] == "cancelled" and calls == []
