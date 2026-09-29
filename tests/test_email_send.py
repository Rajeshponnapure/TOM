"""Email sending end to end against a tiny in-process SMTP server (no network)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import base64
import socket
import socketserver
import threading

import pytest

from tools.email_tools import EmailTools, is_valid_address


class _Handler(socketserver.StreamRequestHandler):
    def _send(self, line):
        self.wfile.write((line + "\r\n").encode())

    def handle(self):
        srv = self.server
        srv.connections += 1
        self._send("220 fake ESMTP")
        while True:
            raw = self.rfile.readline()
            if not raw:
                return
            line = raw.decode("utf-8", "replace").strip()
            cmd = line.upper()
            if cmd.startswith("EHLO"):
                self.wfile.write(b"250-fake\r\n250 AUTH PLAIN\r\n")
            elif cmd.startswith("AUTH PLAIN"):
                token = line.split(None, 2)[2]
                _, user, pwd = base64.b64decode(token).decode().split("\x00")
                srv.logins.append((user, pwd))
                self._send("235 ok" if pwd == srv.password else "535 bad credentials")
            elif cmd.startswith(("MAIL FROM", "RCPT TO")):
                self._send("250 ok")
            elif cmd == "DATA":
                self._send("354 go")
                body = []
                while True:
                    row = self.rfile.readline().decode("utf-8", "replace")
                    if row.strip() == ".":
                        break
                    body.append(row)
                srv.messages.append("".join(body))
                self._send("250 queued")
            elif cmd == "QUIT":
                self._send("221 bye")
                return
            else:
                self._send("250 ok")


@pytest.fixture
def smtp_server():
    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True
    srv = Server(("127.0.0.1", 0), _Handler)
    srv.messages, srv.logins, srv.connections, srv.password = [], [], 0, "app-pass"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv
    srv.shutdown()
    srv.server_close()


@pytest.fixture
def tools(smtp_server, monkeypatch):
    for key in ("GMAIL_CREDENTIALS_FILE", "GMAIL_TOKEN_FILE"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("EMAIL_ADDRESS", "tom@example.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "app-pass")
    monkeypatch.setenv("SMTP_SERVER", "127.0.0.1")
    monkeypatch.setenv("SMTP_PORT", str(smtp_server.server_address[1]))
    monkeypatch.setenv("SMTP_STARTTLS", "false")
    return EmailTools()


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
