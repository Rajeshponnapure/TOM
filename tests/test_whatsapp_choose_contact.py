"""Owner report 2026-10-21: "open whatsapp and text mounish as hi if there are multiple people with the
same name or with any prefix or suffix ask me by showing the names which one you should send the
text to" — TOM sent the whole sentence to the first search match. Now: message "hi", the matching
chats are listed, and the user's answer picks the exact chat."""
import asyncio
import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import whatsapp_tools as wt  # noqa: E402
from tools.nlp_parser import CommandParser  # noqa: E402
from tools.whatsapp_uia import Candidate, UIAError, candidates_from_rows, choose, clean_label  # noqa: E402

OWNER_COMMAND = ("open whatsapp and text mounish as hi if there are multiple people with the same name or "
                 "with with any prefix or suffix ask me by showing the names which one you should send the text to")

# Rows exactly as WhatsApp Desktop 2.2640 exposed them through UI Automation for "mounish".
ROWS = [
    ("Mounish Sai 12:55 https://s.team/p/dmjm-fcrc/gdmcdhmc", "Mounish Sai 12:55"),
    ("Koteswara Rao Mounish Vp Available", "Koteswara Rao Mounish Vp"),
    ("Mounish Sai 21/06/2026 mounish college fee 2nd year.pdf · 2 pages", "Mounish Sai 21/06/2026"),
    ("College Group 10:02 mounish: see you", "College Group 10:02"),        # a message hit in a group
]


def test_owner_command_is_understood():
    details = CommandParser.__new__(CommandParser)._extract_whatsapp_details(OWNER_COMMAND)
    assert details == {"contact": "mounish", "message": "hi", "confirm_contact": "1"}


def test_result_rows_become_distinct_people():
    assert clean_label("Mounish Sai 12:55") == "Mounish Sai"
    assert clean_label("Mounish Sai 21/06/2026") == "Mounish Sai"
    assert clean_label("Ravi Yesterday") == "Ravi"
    assert [c.label for c in candidates_from_rows(ROWS, "mounish")] == ["Mounish Sai", "Koteswara Rao Mounish Vp"]


def test_choose_never_guesses():
    two = candidates_from_rows(ROWS, "mounish")
    assert choose(two, "mounish") is None                         # ambiguous → ask
    assert choose(two, "Mounish Sai").label == "Mounish Sai"      # exact name → that chat
    assert choose([Candidate("Ravi K", "")], "ravi").label == "Ravi K"   # the only match


# ── WhatsApp Desktop with a fake UI Automation layer and a fake keyboard ──

class FakeUIA:
    def __init__(self, rows=ROWS, fail=False):
        self.rows, self.fail, self.opened = rows, fail, []

    def candidates(self, query):
        if self.fail:
            raise UIAError("not available")
        return candidates_from_rows(self.rows, query)

    def open_chat(self, label, query=None):
        self.opened.append(label)


class Keys:
    def __init__(self):
        self.events = []

    def hotkey(self, *k):
        self.events.append(("hotkey", k))

    def press(self, k):
        self.events.append(("press", k))

    def write(self, t, interval=0):
        self.events.append(("write", t))

    def click(self, x, y):
        self.events.append(("click", (x, y)))


class Desktop(wt.WhatsAppTools):
    def __init__(self, uia):
        super().__init__(uia_factory=lambda: uia)
        self.launched = []

    @staticmethod
    def _is_windows():
        return True

    def _foreground_title(self):
        return "WhatsApp"

    def _foreground_rect(self):
        return (0, 0, 1000, 800)

    def _launch_desktop(self, uri):
        self.launched.append(uri)


async def _no_sleep(_):
    return None


@pytest.fixture
def keys(monkeypatch):
    k = Keys()
    monkeypatch.setattr(wt, "pyautogui", k)
    monkeypatch.setattr(wt, "_PYAUTOGUI_OK", True)
    monkeypatch.setattr(wt, "_PYPERCLIP_OK", False)
    monkeypatch.setattr(wt.asyncio, "sleep", _no_sleep)
    monkeypatch.setenv("WHATSAPP_CONTACTS", json.dumps({}))
    return k


def test_several_matches_ask_and_type_nothing(keys):
    uia = FakeUIA()
    result = asyncio.run(Desktop(uia).send_message_native("mounish", "hi", confirm=True))
    assert result["status"] == "needs_input" and result["sent"] is False
    assert result["options"] == ["Mounish Sai", "Koteswara Rao Mounish Vp"]
    assert "1. Mounish Sai" in result["message"] and "Nothing has been sent" in result["message"]
    assert keys.events == [] and uia.opened == []


def test_the_chosen_chat_is_opened_exactly_then_the_message_typed(keys):
    uia = FakeUIA()
    result = asyncio.run(Desktop(uia).send_message_native("Mounish Sai", "hi"))
    assert uia.opened == ["Mounish Sai"]
    assert ("write", "hi") in keys.events
    assert ("hotkey", ("ctrl", "n")) not in keys.events          # no keyboard search, no first-match Enter
    assert result["sent"] is True and "the only match" in result["message"]


def test_without_ui_automation_a_requested_confirmation_refuses_to_guess(keys):
    result = asyncio.run(Desktop(FakeUIA(fail=True)).send_message_native("mounish", "hi", confirm=True))
    assert result["status"] == "error" and result["sent"] is False and keys.events == []
    assert "can't check" in result["message"]


def test_needs_input_is_returned_not_retried_on_whatsapp_web(keys, monkeypatch):
    tools = Desktop(FakeUIA())
    called = []

    async def web(*a, **k):
        called.append(a)
        return {"status": "success", "sent": True}
    monkeypatch.setattr(tools, "send_message_web", web)
    monkeypatch.setenv("WHATSAPP_MODE", "auto")
    assert asyncio.run(tools.send_message("mounish", "hi"))["status"] == "needs_input" and called == []


def test_web_lists_the_matches_too():
    with pytest.raises(wt.WhatsAppAmbiguous) as err:
        wt.WhatsAppTools.pick_chat("mounish", ["Mounish Sai", "Koteswara Rao Mounish Vp", "Ravi"])
    assert err.value.options == ["Mounish Sai", "Koteswara Rao Mounish Vp"]


# ── the agent remembers the question and understands the answer ─────────

def _agent_with(sends, approve=True):
    from agent import TomAgent
    a = TomAgent.__new__(TomAgent)
    a.approval_manager = type("A", (), {"request_approval": lambda self, req: approve})()
    a.safety = type("S", (), {"log_action": lambda self, *x, **k: None})()

    class Tools:
        async def send_message(self, contact, message, confirm=False):
            sends.append((contact, message, confirm))
            if contact == "mounish":
                return wt.needs_choice("mounish", ["Mounish Sai", "Koteswara Rao Mounish Vp"], message)
            return {"status": "unconfirmed", "sent": True, "message": f"sent to {contact}"}
    a.whatsapp_tools = Tools()
    return a


@pytest.mark.parametrize("reply,expected", [
    ("2", "Koteswara Rao Mounish Vp"), ("the second one", "Koteswara Rao Mounish Vp"),
    ("Mounish Sai", "Mounish Sai"), ("1", "Mounish Sai"), ("koteswara", "Koteswara Rao Mounish Vp"),
])
def test_the_answer_picks_the_chat(reply, expected):
    sends = []
    a = _agent_with(sends)
    first = asyncio.run(a._send_whatsapp("mounish", "hi", confirm=True))
    assert first["status"] == "needs_input"
    done = asyncio.run(a._answer_pending_choice(reply))
    assert done["sent"] is True and sends[-1] == (expected, "hi", True)


def test_cancel_and_unrelated_messages():
    sends = []
    a = _agent_with(sends)
    asyncio.run(a._send_whatsapp("mounish", "hi"))
    assert asyncio.run(a._answer_pending_choice("cancel"))["status"] == "cancelled"
    asyncio.run(a._send_whatsapp("mounish", "hi"))
    assert asyncio.run(a._answer_pending_choice("what's the weather in Hyderabad?")) is None
    assert a._pending_choice is None and len(sends) == 2          # nothing else was sent


def test_a_stale_question_is_not_answered():
    sends = []
    a = _agent_with(sends)
    asyncio.run(a._send_whatsapp("mounish", "hi"))
    a._pending_choice["at"] = time.time() - 3600
    assert asyncio.run(a._answer_pending_choice("2")) is None and len(sends) == 1


def test_declined_approval_sends_nothing():
    sends = []
    a = _agent_with(sends, approve=False)
    asyncio.run(a._send_whatsapp("mounish", "hi"))
    assert asyncio.run(a._answer_pending_choice("1"))["status"] == "cancelled" and len(sends) == 1
