"""Email through Gmail in the owner's Chrome profile (tools.gmail_web) — all fakes, no real Chrome or mail.

Owner request 2026-10-27: open the default Chrome profile, open Gmail, find the person, fill in the
message, ask before sending, send it. "Sent" is claimed only when the message is in the Sent folder.
"""
import asyncio
import json
from datetime import date
from urllib.parse import parse_qs, urlparse

import pytest

from tools import gmail_web
from tools.gmail_web import GmailWeb, compose_url

CHROME = "Chrome_WidgetWin_1"


class Profiles:
    def __init__(self, user_data_dir="", ok=True):
        self.user_data_dir = user_data_dir
        self.chrome_executable = "chrome.exe"
        self.launched = []
        self.ok = ok

    def launch_profile(self, profile, url):
        self.launched.append((profile, url))
        return {"status": "success"} if self.ok else {"status": "error", "message": "no chrome"}


class Hardware:
    def __init__(self):
        self.keys = []

    def hotkey(self, *keys):
        self.keys.append(keys)
        return {"status": "success"}


class Windows:
    """A scripted sequence of window lists; the last one repeats."""

    def __init__(self, *frames):
        self.frames = list(frames)

    def __call__(self):
        return self.frames.pop(0) if len(self.frames) > 1 else self.frames[0]


def _gw(windows=None, foreground="Ravi meeting - me@gmail.com - Gmail - Google Chrome", profiles=None, mail=None):
    focused = []
    gw = GmailWeb(email_tools=mail, profiles=profiles or Profiles(), hardware=Hardware(),
                  windows=windows or Windows([(1, CHROME, "Ravi meeting - me@gmail.com - Gmail - Google Chrome")]),
                  foreground=lambda: foreground, focus=focused.append, poll=0.001)
    gw.focused = focused
    return gw


def test_compose_link_carries_recipient_subject_and_body_encoded():
    url = compose_url("ravi@example.com", "Meeting at 4 pm & agenda", "Hi Ravi,\nSee you at 4.", "me@gmail.com")
    q = parse_qs(urlparse(url).query)
    assert url.startswith("https://mail.google.com/mail/u/me%40gmail.com/?view=cm&fs=1")
    assert q["to"] == ["ravi@example.com"] and q["su"] == ["Meeting at 4 pm & agenda"]
    assert q["body"] == ["Hi Ravi,\nSee you at 4."]


def test_the_last_used_chrome_profile_is_the_default(tmp_path):
    (tmp_path / "Local State").write_text(json.dumps({"profile": {"last_used": "Profile 2"}}), encoding="utf-8")
    assert GmailWeb(profiles=Profiles(str(tmp_path))).last_used_profile() == "Profile 2"
    assert GmailWeb(profiles=Profiles(str(tmp_path / "missing"))).last_used_profile() == "Default"


def test_opening_the_draft_launches_that_profile_with_the_compose_link(tmp_path):
    (tmp_path / "Local State").write_text(json.dumps({"profile": {"last_used": "Profile 1"}}), encoding="utf-8")
    profiles = Profiles(str(tmp_path))
    gw = _gw(profiles=profiles)
    res = asyncio.run(gw.open_compose("ravi@example.com", "Hi", "Body"))
    assert res["status"] == "success" and profiles.launched[0][0] == "Profile 1"
    assert "to=ravi%40example.com" in profiles.launched[0][1]


def test_a_too_long_message_is_not_opened_as_a_link():
    profiles = Profiles()
    res = asyncio.run(_gw(profiles=profiles).open_compose("a@b.co", "Hi", "x" * 9000))
    assert res["status"] == "too_long" and profiles.launched == []


def test_an_inbox_already_open_is_not_mistaken_for_the_draft():
    inbox = (5, CHROME, "Inbox (3) - me@gmail.com - Gmail - Google Chrome")
    draft = (5, CHROME, "Ravi meeting - me@gmail.com - Gmail - Google Chrome")
    gw = _gw(windows=Windows([inbox], [inbox], [draft]))
    res = asyncio.run(gw.wait_for_compose("Ravi meeting", before={(5, inbox[2])}))
    assert res["status"] == "ready" and res["title"] == draft[2]


def test_a_sign_in_page_is_reported_not_typed_into():
    gw = _gw(windows=Windows([(2, CHROME, "Sign in - Google Accounts - Google Chrome")]))
    res = asyncio.run(gw.wait_for_compose("Hi", timeout=0.05))
    assert res["status"] == "signin" and "sign in" in res["message"].lower()


def test_no_gmail_window_times_out():
    gw = _gw(windows=Windows([(3, "Notepad", "notes.txt - Notepad")]))
    assert asyncio.run(gw.wait_for_compose("Hi", timeout=0.02))["status"] == "timeout"


def test_send_presses_gmail_send_only_after_approval_and_focus_check():
    gw = _gw()
    res = asyncio.run(gw.send_open_draft("ravi@example.com", "Ravi meeting", hwnd=1))
    assert res["status"] == "pressed" and gw._hardware.keys == [("ctrl", "enter")] and gw.focused == [1]


def test_send_is_refused_without_approval(monkeypatch):
    from tom_core.tools import guard
    monkeypatch.setattr(guard, "_approval_manager", type("No", (), {"request_approval": lambda s, r, p=None: False})())
    gw = _gw()
    res = asyncio.run(gw.send_open_draft("ravi@example.com", "Ravi meeting", hwnd=1))
    assert res["status"] != "pressed" and gw._hardware.keys == []


def test_send_stops_if_another_window_is_in_front():
    gw = _gw(foreground="Untitled - Notepad")
    res = asyncio.run(gw.send_open_draft("ravi@example.com", "Ravi meeting", hwnd=1))
    assert res["status"] == "blocked" and res["sent"] is False and gw._hardware.keys == []
    assert "still open" in res["message"]


def test_emergency_stop_blocks_the_send():
    from tom_core.policy import get_policy
    gw = _gw()
    get_policy().halt("test")
    try:
        res = asyncio.run(gw.send_open_draft("ravi@example.com", "Ravi meeting", hwnd=1))
    finally:
        get_policy().resume()
    assert res["status"] == "blocked" and gw._hardware.keys == []


def test_tests_never_reach_the_real_chrome():
    assert GmailWeb(profiles=Profiles()).available() is False      # TOM_DISABLE_UI_AUTOMATION=1 (conftest)


# ── the owner's mailbox ────────────────────────────────────────────────

class FakeImap:
    def __init__(self, folders):
        self.folders = folders          # name -> list of header texts
        self.current = None

    def list_folders(self):
        return [((b"\\HasNoChildren",), b"/", "INBOX"), ((b"\\HasNoChildren", b"\\Sent"), b"/", "[Gmail]/Sent Mail")]

    def select_folder(self, name, readonly=False):
        self.current = name

    def search(self, criteria):
        msgs = self.folders.get(self.current, [])
        if criteria[0] == "OR":
            token = criteria[2].lower()
            return [i for i, h in enumerate(msgs, 1) if token in h.lower()]
        if criteria[0] == "SINCE":
            assert isinstance(criteria[1], date)
            to = criteria[3].lower()
            return [i for i, h in enumerate(msgs, 1) if to in h.lower()]
        return []

    def fetch(self, ids, parts):
        msgs = self.folders.get(self.current, [])
        key = b"BODY[HEADER.FIELDS (FROM TO CC)]" if "FROM" in parts[0] else b"BODY[HEADER.FIELDS (SUBJECT)]"
        out = {}
        for i in ids:
            h = msgs[i - 1]
            if key.endswith(b"(SUBJECT)]"):
                h = next((line for line in h.split("\r\n") if line.lower().startswith("subject:")), "")
            out[i] = {key: h.encode()}
        return out


class Mail:
    def __init__(self, imap):
        self.imap = imap

    async def _get_active_mail_connection(self):
        return self.imap


INBOX = ["From: Ravi Kumar <ravi.kumar@acme.com>\r\nTo: me@gmail.com\r\nSubject: Plan",
         "From: Ravi Kumar <ravi.kumar@acme.com>\r\nTo: me@gmail.com\r\nSubject: Again",
         "From: Ravi Teja <raviteja@gmail.com>\r\nTo: me@gmail.com\r\nSubject: Hello",
         "From: Ravi Alerts <noreply@ravi-shop.com>\r\nTo: me@gmail.com\r\nSubject: Sale"]
SENT = ["From: me@gmail.com\r\nTo: Ravi Kumar <ravi.kumar@acme.com>\r\nSubject: Ravi meeting"]


def test_people_are_found_in_the_owners_mail_most_frequent_first(monkeypatch):
    monkeypatch.setenv("EMAIL_ADDRESS", "me@gmail.com")
    gw = _gw(mail=Mail(FakeImap({"INBOX": INBOX, "[Gmail]/Sent Mail": SENT})))
    found = asyncio.run(gw.find_contacts("Ravi"))
    assert [c["address"] for c in found] == ["ravi.kumar@acme.com", "raviteja@gmail.com"]   # no noreply, not me
    assert found[0]["name"] == "Ravi Kumar" and found[0]["count"] == 3
    assert [c["address"] for c in asyncio.run(gw.find_contacts("Ravi Teja"))] == ["raviteja@gmail.com"]


def test_no_mailbox_means_unknown_not_empty():
    assert asyncio.run(_gw(mail=None).find_contacts("Ravi")) is None


def test_sent_is_confirmed_from_the_sent_folder():
    gw = _gw(mail=Mail(FakeImap({"[Gmail]/Sent Mail": SENT})))
    assert asyncio.run(gw.verify_sent("ravi.kumar@acme.com", "Ravi meeting", since=0, timeout=0)) is True
    assert asyncio.run(gw.verify_sent("ravi.kumar@acme.com", "Other subject", since=0, timeout=0)) is False
    assert asyncio.run(_gw(mail=None).verify_sent("a@b.co", "x", since=0)) is None


def test_a_revoked_oauth_token_falls_back_to_the_app_password(monkeypatch):
    """2026-10-27: 'invalid_grant' on the OAuth token disabled every mail read although the app password worked."""
    from tools.email_tools import EmailTools
    et = EmailTools()
    et.gmail_credentials_file, et.email_address, et.email_password = "client.json", "me@gmail.com", "app-pass"

    async def oauth():
        return {"status": "error", "message": "OAuth2 error: invalid_grant"}

    async def password(provider):
        et.connection_pool["imap"] = "conn"
        return {"status": "success", "message": "Connected to gmail IMAP"}
    monkeypatch.setattr(et, "_connect_gmail_oauth", oauth)
    monkeypatch.setattr(et, "_connect_imap_generic", password)
    res = asyncio.run(et.connect_email_service("gmail"))
    assert res["status"] == "success" and "invalid_grant" in res["message"]
    assert asyncio.run(et._get_active_mail_connection()) == "conn"


# ── reading the screen (fake OCR — tests never photograph or click the desktop) ─────────

class FakeScreen:
    """Lines of text "on screen"; clicks are recorded. Each line is (text, y)."""

    def __init__(self, lines, after_click=None):
        from tom_core.screen_control import ScreenControl
        self.lines, self.after_click, self.clicks = lines, after_click, []

        def ocr(_img):
            out = []
            for n, (text, y) in enumerate(self.lines):
                x = 100
                for w in text.split():
                    out.append((w, 95.0, (x, y, 10 * len(w), 20), n))
                    x += 10 * len(w) + 8
            return out
        hw = type("H", (), {"click": lambda s, x, y: self.clicks.append((x, y)) or self._clicked() or {"status": "success"},
                            "double_click": lambda s, x, y: {"status": "success"}})()
        self.sc = ScreenControl(hardware=hw, grab=lambda region: None, ocr=ocr)

    def _clicked(self):
        if self.after_click is not None:
            self.lines = self.after_click

    def __getattr__(self, name):
        return getattr(self.sc, name)


def test_only_the_send_button_is_clicked_not_the_word_send_in_the_body():
    screen = FakeScreen([("TOM live test 23:47", 100), ("This is a test: TOM clicked Send itself", 300),
                         ("Send", 900)], after_click=[("Message sent", 950)])
    gw = _gw()
    gw._screen_tool = screen
    res = asyncio.run(gw.send_open_draft("ravi@example.com", "Ravi meeting", hwnd=1))
    assert res["method"] == "button" and screen.clicks and screen.clicks[0][1] == 910      # the button row
    assert gw._hardware.keys == [] and "Message sent" in res["screen"]


def test_a_missed_click_falls_back_to_the_shortcut_once():
    screen = FakeScreen([("Send", 900)])                                   # still there after the click
    gw = _gw()
    gw._screen_tool = screen
    res = asyncio.run(gw.send_open_draft("ravi@example.com", "Ravi meeting", hwnd=1))
    assert res["method"] == "keyboard" and gw._hardware.keys == [("ctrl", "enter")]


def test_an_older_draft_never_passes_for_this_one():
    gw = _gw()
    gw._screen_tool = FakeScreen([("ravi@example.com", 80), ("TOM live test 21:30", 120)])
    res = asyncio.run(gw.inspect_draft("ravi@example.com", "TOM live test 21:38", hwnd=1, timeout=0))
    assert res["ok"] is False and res["missing"] == ["subject"]
    gw._screen_tool = FakeScreen([("ravi@example.com", 80), ("TOM live test 21:38", 120)])
    assert asyncio.run(gw.inspect_draft("ravi@example.com", "TOM live test 21:38", hwnd=1, timeout=0))["ok"] is True


def test_drafted_emails_never_greet_an_address_or_claim_they_were_sent():
    from agent import TomAgent
    body = ("Dear ravi.kumar@acme.com,\n\nPlease find the report attached. It appears to have sent successfully.\n\n"
            "Best regards,\nRajesh")
    out = TomAgent._tidy_email_body(body)
    assert out.startswith("Hello,") and "sent successfully" not in out and "report attached" in out


# ── the agent ──────────────────────────────────────────────────────────

class FakeGmail:
    def __init__(self, contacts=None, confirmed=True, window="ready"):
        self.contacts, self.confirmed, self.window = contacts, confirmed, window
        self.calls = []

    def available(self):
        return True

    async def find_contacts(self, name):
        self.calls.append(("find", name))
        return self.contacts

    async def open_compose(self, to, subject, body):
        self.calls.append(("open", to, subject))
        return {"status": "success", "windows_before": set()}

    async def wait_for_compose(self, subject, before=None):
        return {"status": self.window, "hwnd": 7, "message": "Gmail in Chrome is asking you to sign in."}

    async def send_open_draft(self, to, subject, hwnd):
        self.calls.append(("send", to, subject, hwnd))
        return {"status": "pressed"}

    async def verify_sent(self, to, subject, since):
        return self.confirmed


def _agent(gmail, approve=True):
    from agent import TomAgent
    from tools.approval import ApprovalManager
    a = TomAgent.__new__(TomAgent)
    a._gmail_web_tool = gmail
    a.email_tools = object()
    a.safety = type("S", (), {"log_action": lambda self, *x, **k: None})()
    mgr = ApprovalManager()
    a.seen = []
    mgr.provider = lambda req: a.seen.append(req.summary) or approve
    a.approval_manager = mgr
    return a


BODY = "Hi Ravi, can we move tomorrow's meeting to 4 pm? Thanks, Rajesh"
PARSED = {"subject": "Moving tomorrow's meeting", "message_body": BODY}


def test_the_email_is_shown_in_gmail_then_sent_after_yes_and_confirmed():
    g = FakeGmail(confirmed=True)
    a = _agent(g)
    res = asyncio.run(a.execute_email_send_flow("send an email to ravi@acme.com", dict(PARSED)))
    assert [c[0] for c in g.calls] == ["open", "send"]
    assert res["status"] == "success" and res["verified"] is True and "Sent folder" in res["message"]
    assert "open in Chrome" in a.seen[0] and BODY in a.seen[0]


def test_no_means_nothing_is_sent_and_the_draft_stays():
    g = FakeGmail()
    res = asyncio.run(_agent(g, approve=False).execute_email_send_flow("send an email to ravi@acme.com", dict(PARSED)))
    assert res["status"] == "cancelled" and res["sent"] is False and "still open" in res["message"]
    assert [c[0] for c in g.calls] == ["open"]


def test_send_that_cannot_be_confirmed_is_reported_as_unverified():
    res = asyncio.run(_agent(FakeGmail(confirmed=False)).execute_email_send_flow(
        "send an email to ravi@acme.com", dict(PARSED)))
    assert res["status"] == "unverified" and res["sent"] is None and "check Gmail" in res["message"]


def test_sign_in_page_stops_before_asking():
    a = _agent(FakeGmail(window="signin"))
    res = asyncio.run(a.execute_email_send_flow("send an email to ravi@acme.com", dict(PARSED)))
    assert res["status"] == "needs_input" and a.seen == []


def test_a_name_is_looked_up_in_the_mail():
    g = FakeGmail(contacts=[{"name": "Ravi Kumar", "address": "ravi.kumar@acme.com", "count": 3}])
    res = asyncio.run(_agent(g).execute_email_send_flow("send an email to Ravi", dict(PARSED, recipient_name="Ravi")))
    assert ("open", "ravi.kumar@acme.com", PARSED["subject"]) in g.calls
    assert res["status"] == "success" and "Found Ravi in your mail" in res["message"]


def test_several_matches_ask_which_one_and_the_answer_continues():
    g = FakeGmail(contacts=[{"name": "Ravi Kumar", "address": "ravi.kumar@acme.com", "count": 3},
                            {"name": "Ravi Teja", "address": "raviteja@gmail.com", "count": 1}])
    a = _agent(g)
    ask = asyncio.run(a.execute_email_send_flow("send an email to Ravi", dict(PARSED, recipient_name="Ravi")))
    assert ask["status"] == "needs_input" and "Ravi Teja <raviteja@gmail.com>" in ask["message"]
    done = asyncio.run(a._answer_pending_choice("2"))
    assert done["status"] == "success" and ("send", "raviteja@gmail.com", PARSED["subject"], 7) in g.calls


def test_nobody_found_asks_for_the_address():
    res = asyncio.run(_agent(FakeGmail(contacts=[])).execute_email_send_flow(
        "send an email to Ravi", dict(PARSED, recipient_name="Ravi")))
    assert res["status"] == "error" and "couldn't find them in your mail" in res["message"]


@pytest.mark.parametrize("command,via_chrome", [
    ("send an email to ravi@acme.com", True), ("send an email to ravi@acme.com via smtp", False),
    ("send an email to ravi@acme.com in the background", False)])
def test_the_route_can_be_chosen(command, via_chrome, monkeypatch):
    monkeypatch.delenv("TOM_EMAIL_VIA", raising=False)
    assert _agent(FakeGmail())._email_via_chrome(command) is via_chrome
    monkeypatch.setenv("TOM_EMAIL_VIA", "smtp")
    assert _agent(FakeGmail())._email_via_chrome("send an email to ravi@acme.com") is False
