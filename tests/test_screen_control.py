"""Screen control by sight (tom_core.screen_control) and the commands that use it — fake OCR and fake
mouse/keyboard; tests never photograph or click the owner's desktop."""
import asyncio

import pytest

from tom_core import screen_control as scm
from tom_core.screen_control import ScreenControl, _rows
from tools.command_router import CommandRouter


class Hw:
    def __init__(self):
        self.calls = []

    def click(self, x, y):
        self.calls.append(("click", x, y))
        return {"status": "success"}

    def double_click(self, x, y):
        self.calls.append(("double", x, y))
        return {"status": "success"}

    def type_text(self, text, interval=0.0):
        self.calls.append(("type", text))
        return {"status": "success"}

    def copy_to_clipboard(self, text):
        self.calls.append(("clip", text))
        return {"status": "success"}

    def hotkey(self, *keys):
        self.calls.append(("keys",) + keys)
        return {"status": "success"}

    def press_key(self, key):
        self.calls.append(("key", key))
        return {"status": "success"}


def screen(lines, hw=None):
    """lines: [(text, x, y)] → a ScreenControl that 'sees' them."""
    def ocr(_img):
        out = []
        for n, (text, x, y) in enumerate(lines):
            for w in text.split():
                out.append((w, 92.0, (x, y, 11 * len(w), 22), n))
                x += 11 * len(w) + 8
        return out
    return ScreenControl(hardware=hw or Hw(), grab=lambda region: None, ocr=ocr)


def test_words_are_grouped_into_lines_left_to_right():
    words = [("Order", 90, (160, 101, 50, 20), None), ("Confirm", 90, (100, 100, 55, 22), None),
             ("Cancel", 90, (600, 100, 55, 22), None), ("Total:", 90, (100, 160, 50, 20), None)]
    rows = _rows(words)
    by_line = {}
    for text, _c, _b, key in rows:
        by_line.setdefault(key, []).append(text)
    assert sorted(by_line.values()) == [["Cancel"], ["Confirm", "Order"], ["Total:"]]   # far-apart words split


def test_find_matches_a_phrase_and_tolerates_small_ocr_errors():
    sc = screen([("Customer name:", 100, 50), ("Confirm 0rder", 100, 300)])
    m = sc.find("Confirm Order")
    assert m and m.text == "Confirm 0rder" and m.score >= 0.8
    assert sc.find("Delete account") is None


def test_click_text_clicks_the_centre_of_what_it_sees():
    hw = Hw()
    sc = screen([("Confirm Order", 100, 300)], hw)
    r = sc.click_text("Confirm Order")
    assert r["status"] == "success" and hw.calls[0][0] == "click"
    x, y = hw.calls[0][1:]
    assert 100 < x < 260 and 300 <= y <= 322
    assert screen([("Nothing here", 0, 0)]).click_text("Send")["found"] is False


def test_button_preference_ignores_the_word_inside_a_sentence():
    hw = Hw()
    sc = screen([("TOM clicked Send itself in the body text", 100, 200), ("Send", 100, 900)], hw)
    sc.click_text("Send", prefer="button")
    assert hw.calls[0][2] > 800
    hw2 = Hw()
    screen([("TOM clicked Send itself in the body text", 100, 200)], hw2).click_text("Send", prefer="button")
    assert hw2.calls == []                                     # no button: nothing clicked


def test_unicode_is_pasted_and_ascii_is_typed():
    hw = Hw()
    sc = screen([], hw)
    sc.type_text("hello")
    sc.type_text("Rajesh ₹500 తెలుగు")
    assert hw.calls[0] == ("type", "hello")
    assert hw.calls[1] == ("clip", "Rajesh ₹500 తెలుగు") and hw.calls[2] == ("keys", "ctrl", "v")


def test_tesseract_is_found_in_its_install_folder(monkeypatch, tmp_path):
    exe = tmp_path / "tesseract.exe"
    exe.write_text("")
    monkeypatch.setenv("TESSERACT_CMD", str(exe))
    assert scm.find_tesseract() == str(exe)


@pytest.mark.parametrize("text,action,target", [
    ("click Send", "click", "Send"), ("click on the File menu", "click", "File"),
    ("double-click Recycle Bin", "double_click", "Recycle Bin"), ("type Hello Ravi", "type", "Hello Ravi"),
    ("type text hello", "type", "hello")])
def test_screen_commands_route(text, action, target):
    d = CommandRouter().route(text)
    assert d.handler == "execute_screen_action" and d.metadata == {"action": action, "target": target}


@pytest.mark.parametrize("text", ["read my screen", "what is on my screen?", "what do you see", "summarize my screen"])
def test_screen_questions_read_the_screen_not_chat(text):
    assert CommandRouter().route(text).handler == "execute_screen_read"


def test_coordinate_clicks_stay_with_the_hardware_engine():
    assert CommandRouter().route("click at 100, 200").handler != "execute_screen_action"


def test_the_agent_types_then_confirms_on_screen():
    from agent import TomAgent
    hw = Hw()
    lines = [("Customer name:", 100, 50)]
    sc = screen(lines, hw)

    def after_type(*_a, **_k):
        lines.append(("Rajesh cake order", 100, 120))
        return {"status": "success"}
    hw.type_text = after_type
    a = TomAgent.__new__(TomAgent)
    a._screen_control = sc
    r = asyncio.run(a.execute_screen_action("type", "Rajesh cake order"))
    assert r["status"] == "success" and r["verified"] is True


def test_reading_the_screen_answers_from_the_ocr_text_only():
    from agent import TomAgent
    seen = {}

    class Resp:
        content = "Gmail is open with a draft to Ravi."

    async def invoke(prompt, payload, label, llm=None):
        seen.update(payload)
        return Resp()
    a = TomAgent.__new__(TomAgent)
    a._screen_control = screen([("Compose Mail - Gmail", 0, 0), ("To ravi@example.com", 0, 40)])
    a._invoke_llm, a.llm = invoke, None
    r = asyncio.run(a.execute_screen_read("read my screen"))
    assert r["status"] == "success" and "ravi@example.com" in seen["t"] and "OCR" in r["message"]


def test_without_tesseract_the_screen_is_not_claimed(monkeypatch):
    from agent import TomAgent
    a = TomAgent.__new__(TomAgent)
    sc = ScreenControl()
    sc.cmd = ""
    a._screen_control = sc
    r = asyncio.run(a.execute_screen_read("read my screen"))
    assert r["status"] == "error" and "Tesseract" in r["message"]
