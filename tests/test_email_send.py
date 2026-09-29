"""Email sending end to end against a tiny in-process SMTP server (no network)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import socket

import pytest

from tools.email_tools import EmailTools, is_valid_address


def test_address_validation():
    assert is_valid_address("john@example.com")
    assert not is_valid_address("john")
    assert not is_valid_address("")
    assert not is_valid_address("john@example.com\nBcc: x@y.com")


def test_send_with_app_password_reaches_the_server(tools, smtp_server):
    result = asyncio.run(tools.send_email_direct("john@example.com", "Hello", "Body text"))
    assert result["status"] == "success", result
    assert smtp_server.logins == [("tom@example.com", "app-pass")]
    assert "Subject: Hello" in smtp_server.messages[0]
    assert "To: john@example.com" in smtp_server.messages[0]


def test_send_email_requires_approval(tools, smtp_server):
    async def deny(*_):
        return False
    result = asyncio.run(tools.send_email("john@example.com", "Hi", "Body", approval_callback=deny))
    assert result["status"] == "cancelled" and not smtp_server.messages
    no_callback = asyncio.run(tools.send_email("john@example.com", "Hi", "Body"))
    assert no_callback["status"] == "cancelled" and not smtp_server.messages


def test_a_name_is_not_an_address(tools, smtp_server):
    result = asyncio.run(tools.send_email_direct("Ravi", "Hi", "Body"))
    assert result["status"] == "error" and "email address" in result["message"]
    assert smtp_server.connections == 0


def test_header_injection_is_neutralised(tools, smtp_server):
    asyncio.run(tools.send_email_direct("john@example.com", "Hi\r\nBcc: evil@example.com", "Body"))
    headers = smtp_server.messages[0].split("\r\n\r\n", 1)[0]
    assert "\nBcc:" not in headers


def test_wrong_password_is_reported_not_swallowed(tools, monkeypatch):
    monkeypatch.setenv("EMAIL_PASSWORD", "nope")
    result = asyncio.run(EmailTools().send_email_direct("john@example.com", "Hi", "Body"))
    assert result["status"] == "error" and "535" in result["message"]


def test_stale_connection_is_reopened_once(tools, smtp_server):
    assert asyncio.run(tools.send_email_direct("a@example.com", "One", "x"))["status"] == "success"
    tools.connection_pool["smtp"].sock.shutdown(socket.SHUT_RDWR)   # the link dropped
    assert asyncio.run(tools.send_email_direct("b@example.com", "Two", "y"))["status"] == "success"
    assert len(smtp_server.messages) == 2 and smtp_server.connections == 2


def test_unconfigured_email_says_what_to_set(monkeypatch):
    for key in ("GMAIL_CREDENTIALS_FILE", "EMAIL_ADDRESS", "EMAIL_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    result = asyncio.run(EmailTools().send_email_direct("john@example.com", "Hi", "x"))
    assert result["status"] == "error" and "EMAIL_PASSWORD" in result["message"]


# ── inbox: real IMAP conversation against the fake server ───────────────────
def test_fetch_returns_parsed_headers_and_body(inbox_tools):
    result = asyncio.run(inbox_tools.fetch_imap_emails("inbox", max_count=10))
    assert result["status"] == "success" and result["emails_count"] == 3, result
    first = result["emails"][0]
    assert first["subject"] == "Urgent: contract deadline"
    assert "boss@corp.com" in first["from"]
    assert first["body_preview"].startswith("Please confirm")


def test_unread_only_asks_the_server_for_unseen_mail(inbox_tools, imap_server):
    result = asyncio.run(inbox_tools.fetch_imap_emails("inbox", max_count=10, unread_only=True))
    assert [e["subject"] for e in result["emails"]] == ["Lunch?"]
    assert any("UNSEEN" in c.upper() for c in imap_server.commands)


def test_fetch_never_marks_mail_as_read(inbox_tools, imap_server):
    asyncio.run(inbox_tools.fetch_imap_emails("inbox"))
    fetches = [c for c in imap_server.commands if c.upper().startswith("UID FETCH")]
    assert fetches and all("BODY.PEEK[" in c.upper() for c in fetches)
    assert not any("BODY[TEXT]" in c.upper().replace("BODY.PEEK", "") for c in fetches)


def test_inbox_triage_classifies_real_fetched_mail(inbox_tools):
    from tools.email_tools import classify_email_item
    emails = asyncio.run(inbox_tools.fetch_imap_emails("inbox"))["emails"]
    priority = {e["subject"]: classify_email_item(e)["priority"] for e in emails}
    assert priority["Urgent: contract deadline"] == "important"
    assert priority["Weekly newsletter"] == "low"
