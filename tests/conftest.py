"""Shared fakes: an in-process SMTP server and IMAP server (no network, no real mail)."""
import base64
import os
import socketserver
import sys
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Never let a test read or write the user's real state. A leak check on 2026-10-21 (snapshot →
# full suite → diff) found tests writing the owner's chat history, learning files, RAG store,
# audit log, file-move undo journal and .env (it set OLLAMA_MODEL to a model that isn't
# installed). Every runtime-state folder (memories/, tom_brain/, tom_logs/, data/ — see
# tools/project_paths.STATE_DIRS) and the .env TOM writes settings to now point at a throwaway
# location for the whole session. Must run before any TOM module is imported.
if not os.environ.get("TOM_STATE_ROOT"):
    import tempfile as _tempfile
    os.environ["TOM_STATE_ROOT"] = _tempfile.mkdtemp(prefix="tom_test_state_")
if not os.environ.get("TOM_ENV_FILE"):
    os.environ["TOM_ENV_FILE"] = os.path.join(os.environ["TOM_STATE_ROOT"], ".env")
# Deliverables a test creates must not land in the owner's Desktop "TOM Workspace" either.
if not os.environ.get("TOM_WORKSPACE_DIR"):
    os.environ["TOM_WORKSPACE_DIR"] = os.path.join(os.environ["TOM_STATE_ROOT"], "workspace")
# Tests must never reach into the owner's real apps (WhatsApp Desktop is read through UI
# Automation since 2026-10-21); a test that needs it injects a fake instead.
os.environ["TOM_DISABLE_UI_AUTOMATION"] = "1"
os.environ["TOM_NO_AUTO_OPEN"] = "1"          # created documents never pop up on the owner's screen
# Long-term memory is local by default (ADR-005). Never let a test read or write the user's real
# store in tom_brain/hindsight — every test session gets a throwaway one unless a test sets its own.
if not os.environ.get("TOM_MEMORY_STATE_DIR"):
    import tempfile as _tempfile
    os.environ["TOM_MEMORY_STATE_DIR"] = _tempfile.mkdtemp(prefix="tom_test_memory_")
# Same for the durable task store (tom_brain/tasks.sqlite3).
if not os.environ.get("TOM_TASK_DB"):
    import tempfile as _tempfile
    os.environ["TOM_TASK_DB"] = os.path.join(_tempfile.mkdtemp(prefix="tom_test_tasks_"), "tasks.sqlite3")

from tools.email_tools import EmailTools  # noqa: E402


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




# ── fake IMAP server ────────────────────────────────────────────────────────
IMAP_MAIL = {  # uid -> (headers, body, seen)
    1: ("From: Boss <boss@corp.com>\r\nTo: tom@example.com\r\nSubject: Urgent: contract deadline\r\n"
        "Date: Mon, 1 Jan 2026 10:00:00 +0000\r\n\r\n", "Please confirm by today?", True),
    2: ("From: Shop <noreply@shop.com>\r\nTo: tom@example.com\r\nSubject: Weekly newsletter\r\n"
        "Date: Tue, 2 Jan 2026 10:00:00 +0000\r\n\r\n", "Unsubscribe here", True),
    3: ("From: Sam <sam@friend.org>\r\nTo: tom@example.com\r\nSubject: Lunch?\r\n"
        "Date: Wed, 3 Jan 2026 10:00:00 +0000\r\n\r\n", "Can you join us for lunch?", False),
}


class _ImapHandler(socketserver.StreamRequestHandler):
    def _line(self, text):
        self.wfile.write(text.encode() + b"\r\n")

    def handle(self):
        srv = self.server
        self._line("* OK IMAP4rev1 fake ready")
        while True:
            raw = self.rfile.readline()
            if not raw:
                return
            tag, _, rest = raw.decode().strip().partition(" ")
            cmd = rest.upper()
            srv.commands.append(rest)
            if cmd.startswith("CAPABILITY"):
                self._line("* CAPABILITY IMAP4rev1")
                self._line(f"{tag} OK done")
            elif cmd.startswith("LOGIN"):
                self._line(f"{tag} OK logged in")
            elif cmd.startswith("SELECT"):
                self._line(f"* {len(IMAP_MAIL)} EXISTS")
                self._line(f"{tag} OK [READ-WRITE] selected")
            elif cmd.startswith("UID SEARCH"):
                unseen = "UNSEEN" in cmd
                uids = [u for u, (_, _, seen) in IMAP_MAIL.items() if not (unseen and seen)]
                self._line("* SEARCH " + " ".join(map(str, uids)))
                self._line(f"{tag} OK search done")
            elif cmd.startswith("UID FETCH"):
                uid = int(rest.split()[2])
                headers, body, _ = IMAP_MAIL[uid]
                hb, bb = headers.encode(), body.encode()
                self.wfile.write(
                    f"* {uid} FETCH (UID {uid} RFC822.SIZE {len(hb) + len(bb)} "
                    f"BODY[HEADER.FIELDS (DATE FROM SUBJECT TO)] {{{len(hb)}}}\r\n".encode() + hb +
                    f" BODY[TEXT]<0> {{{len(bb)}}}\r\n".encode() + bb + b")\r\n")
                self._line(f"{tag} OK fetch done")
            elif cmd.startswith("LOGOUT"):
                self._line("* BYE")
                self._line(f"{tag} OK bye")
                return
            else:
                self._line(f"{tag} OK")


@pytest.fixture
def imap_server():
    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True
    srv = Server(("127.0.0.1", 0), _ImapHandler)
    srv.commands = []
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv
    srv.shutdown()
    srv.server_close()


@pytest.fixture
def inbox_tools(imap_server, monkeypatch):
    for key in ("GMAIL_CREDENTIALS_FILE", "GMAIL_TOKEN_FILE"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("EMAIL_ADDRESS", "tom@example.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "app-pass")
    monkeypatch.setenv("IMAP_HOST", "127.0.0.1")
    monkeypatch.setenv("IMAP_PORT", str(imap_server.server_address[1]))
    monkeypatch.setenv("IMAP_SSL", "false")
    return EmailTools()
