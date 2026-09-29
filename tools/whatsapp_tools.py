"""
WhatsApp automation for TOM.

Two transports:
1. WhatsApp Desktop (Windows) - keyboard automation with hard safety checks.
2. WhatsApp Web - Playwright, with fallback selectors and a read-back check.

Safety rules that both share:
  * A recipient is an exact phone number when one is known (a number in the command,
    or a name in WHATSAPP_CONTACTS / data/whatsapp_contacts.json). A number opens the
    exact chat, so nothing is "searched" and the wrong person can't be picked.
  * Desktop automation never types unless WhatsApp is the foreground window, and any
    click stays inside that window (the old code clicked a fixed screen position).
  * Web automation refuses an ambiguous name, checks the opened chat's header, and
    reads the outgoing bubble back before it says "sent".
  * Desktop cannot read the screen, so its result is "unconfirmed", never "success".
  * Once keys have been sent the other transport is never tried (no double sends).
"""
import asyncio
import json
import logging
import os
import re
import urllib.parse
import webbrowser
from typing import Any, Dict, List, Optional

from tools.project_paths import project_path_str

logger = logging.getLogger(__name__)

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.3
    _PYAUTOGUI_OK = True
except Exception:          # ImportError, or no display (headless Linux raises other errors)
    pyautogui = None
    _PYAUTOGUI_OK = False

try:
    import pyperclip
    _PYPERCLIP_OK = True
except Exception:
    pyperclip = None
    _PYPERCLIP_OK = False


def _css_quote(text: str) -> str:
    """Escape a value for use inside a double-quoted CSS attribute selector."""
    return str(text).replace("\\", "\\\\").replace('"', '\\"')


# ── Recipient resolution ─────────────────────────────────────────────────────

_PHONE_RE = re.compile(r"^\+?[\d(][\d\s().-]{6,}$")


def normalize_number(text: str) -> Optional[str]:
    """'+91 98765-43210' -> '919876543210' (international format, digits only)."""
    text = (text or "").strip()
    if not _PHONE_RE.match(text):
        return None
    digits = re.sub(r"\D", "", text)
    return digits if 8 <= len(digits) <= 15 else None


def load_contacts() -> Dict[str, str]:
    """name (lower-case) -> digits, from data/whatsapp_contacts.json and WHATSAPP_CONTACTS (JSON)."""
    merged: Dict[str, str] = {}
    sources: List[Any] = []
    try:
        with open(project_path_str("data", "whatsapp_contacts.json"), "r", encoding="utf-8") as handle:
            sources.append(json.load(handle))
    except (OSError, ValueError):
        pass
    raw = os.environ.get("WHATSAPP_CONTACTS", "").strip()
    if raw:
        try:
            sources.append(json.loads(raw))
        except ValueError:
            logger.warning("WHATSAPP_CONTACTS is not valid JSON; ignoring it.")
    for source in sources:                       # the environment (later) wins over the file
        if isinstance(source, dict):
            for name, number in source.items():
                digits = normalize_number(str(number))
                if digits:
                    merged[str(name).strip().lower()] = digits
    return merged


def resolve_number(contact: str) -> Optional[str]:
    """A phone number for this recipient if one is known, else None (=> search by name)."""
    direct = normalize_number(contact)
    if direct:
        return direct
    return load_contacts().get((contact or "").strip().lower())


# ── WhatsApp Web selectors (several generations; the first one present wins) ──

SEARCH_BOX = [
    'div[contenteditable="true"][data-tab="3"]',
    'div[role="textbox"][contenteditable="true"][aria-label*="Search" i]',
    '#side div[contenteditable="true"]',
]
COMPOSER = [
    'footer div[contenteditable="true"][data-tab="10"]',
    'div[contenteditable="true"][data-tab="10"]',
    'footer div[role="textbox"][contenteditable="true"]',
    '#main footer div[contenteditable="true"]',
    'div[contenteditable="true"][aria-label*="Type a message" i]',
]
CHAT_HEADER = ['#main header span[title]', 'header span[dir="auto"][title]']
RESULT_TITLES = ['#pane-side span[title]', 'span[title]']
OUTGOING_TEXT = 'div.message-out span.selectable-text'


class WhatsAppError(Exception):
    """A step failed *before anything was sent*."""


class WhatsAppTools:
    def __init__(self, browser_tools=None):
        self.browser_tools = browser_tools
        self.whatsapp_url = "https://web.whatsapp.com"
        self._app_family = "5319275A.WhatsAppDesktop_cv1g1gvanyjgm"

    # ══════════════════════════════════════════════════════════════════════════
    # Desktop (Windows)
    # ══════════════════════════════════════════════════════════════════════════

    # Hooks (replaced in tests; the real ones use Win32 through ctypes).
    @staticmethod
    def _is_windows() -> bool:
        return os.name == "nt"

    def _foreground_title(self) -> str:
        if os.name != "nt":
            return ""
        import ctypes
        user32 = ctypes.windll.user32
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(user32.GetForegroundWindow(), buf, 512)
        return buf.value

    def _foreground_rect(self) -> Optional[tuple]:
        """(left, top, right, bottom) of the foreground window, or None."""
        if os.name != "nt":
            return None
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        rect = wintypes.RECT()
        if not user32.GetWindowRect(user32.GetForegroundWindow(), ctypes.byref(rect)):
            return None
        return rect.left, rect.top, rect.right, rect.bottom

    def _launch_desktop(self, uri: str) -> None:
        if os.name == "nt":
            os.startfile(uri)
        else:
            raise OSError("WhatsApp Desktop automation is Windows-only")

    async def _wait_foreground(self, timeout: float = 12.0) -> bool:
        waited = 0.0
        while waited <= timeout:
            if "whatsapp" in self._foreground_title().lower():
                return True
            await asyncio.sleep(0.5)
            waited += 0.5
        return False

    def _require_foreground(self, step: str) -> None:
        title = self._foreground_title()
        if "whatsapp" not in title.lower():
            raise WhatsAppError(
                f"WhatsApp was not the active window when I was about to {step} "
                f"(active: '{title or 'unknown'}'). I stopped so nothing lands in another app.")

    def _type_text(self, text: str) -> None:
        if _PYPERCLIP_OK:
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
        elif text.isascii():
            pyautogui.write(text, interval=0.02)
        else:
            raise WhatsAppError("This text has non-ASCII characters and 'pyperclip' is not installed "
                                "(pip install pyperclip), so I can't type it safely.")

    async def send_message_native(self, contact_name: str, message: str) -> Dict[str, Any]:
        """Send through WhatsApp Desktop. The status is 'unconfirmed', never 'success': the
        desktop app cannot be read back. `sent` says whether any keys were actually sent."""
        if not _PYAUTOGUI_OK:
            return {"status": "error", "sent": False,
                    "message": "pyautogui is not available (pip install pyautogui; it needs a desktop session)."}
        if not _PYPERCLIP_OK and not (message.isascii() and contact_name.isascii()):
            return {"status": "error", "sent": False,
                    "message": "This text has non-ASCII characters; install pyperclip (pip install pyperclip)."}

        number = resolve_number(contact_name)
        sent = False
        try:
            # A number opens the exact chat with the text pre-filled: no search, no wrong contact.
            uri = f"whatsapp://send?phone={number}&text={urllib.parse.quote(message)}" if number else "whatsapp:"
            await asyncio.to_thread(self._launch_desktop, uri)
            if not await self._wait_foreground():
                raise WhatsAppError("WhatsApp did not come to the front, so I did not type anything.")
            await asyncio.sleep(0.8)

            if number:
                self._require_foreground("send the pre-filled message")
                sent = True                      # from here on keys may reach the chat
                pyautogui.press("enter")
            else:
                self._require_foreground("open the new-chat search")
                pyautogui.hotkey("ctrl", "n")
                await asyncio.sleep(0.8)
                self._require_foreground("type the contact name")
                pyautogui.hotkey("ctrl", "a")
                self._type_text(contact_name)
                await asyncio.sleep(2.0)
                self._require_foreground("select the contact")
                pyautogui.press("enter")           # the first match: see the note in the result
                await asyncio.sleep(1.5)
                self._require_foreground("focus the message box")
                rect = self._foreground_rect()
                if rect:                           # inside the WhatsApp window, near its bottom edge
                    left, top, right, bottom = rect
                    pyautogui.click(x=(left + right) // 2, y=max(top + 1, bottom - 60))
                    await asyncio.sleep(0.4)
                self._require_foreground("type the message")
                sent = True
                self._type_text(message)
                await asyncio.sleep(0.5)
                self._require_foreground("press send")
                pyautogui.press("enter")
            await asyncio.sleep(1)
        except WhatsAppError as exc:
            return {"status": "error", "sent": sent, "message": str(exc)}
        except Exception as exc:
            logger.error("WhatsApp native send failed: %s", exc)
            return {"status": "error", "sent": sent,
                    "message": f"WhatsApp automation failed: {exc}. WhatsApp may be open; check it before retrying."}

        how = ("to the exact number on file" if number
               else "to the first search match for that name (add the person to WHATSAPP_CONTACTS to target an exact number)")
        return {"status": "unconfirmed", "sent": True, "via": "desktop",
                "message": (f"I sent \"{message[:80]}{'...' if len(message) > 80 else ''}\" to {contact_name} in "
                            f"WhatsApp Desktop {how}. The desktop app can't be read back, so I can't confirm "
                            f"delivery - please glance at the chat.")}

    # ══════════════════════════════════════════════════════════════════════════
    # Web
    # ══════════════════════════════════════════════════════════════════════════

    async def _ensure_browser(self):
        if not self.browser_tools:
            from tools.browser_tools import BrowserTools
            self.browser_tools = BrowserTools()

        if not self.browser_tools.browser:
            chrome_path = os.environ.get(
                "CHROME_EXECUTABLE",
                "C:/Program Files/Google/Chrome/Application/chrome.exe",
            )
            profile_path = os.environ.get(
                "CHROME_PROFILE_PATH",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data"),
            )
            await self.browser_tools.init_browser(
                executable_path=chrome_path,
                user_data_dir=profile_path,
                headless=False,
            )

        page = await self.browser_tools._get_active_page()
        if not page:
            page = await self.browser_tools.context.new_page()
        return page

    @staticmethod
    async def _first_present(page, selectors: List[str], timeout_ms: int):
        """The first element any selector finds (all are polled together until the timeout)."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_ms / 1000
        while True:
            for selector in selectors:
                handle = await page.query_selector(selector)
                if handle:
                    return handle
            if loop.time() >= deadline:
                return None
            await asyncio.sleep(0.25)

    async def _chat_titles(self, page) -> List[str]:
        for selector in RESULT_TITLES:
            titles = await page.eval_on_selector_all(
                selector, "els => els.map(e => e.getAttribute('title')).filter(Boolean)")
            if titles:
                return list(dict.fromkeys(titles))
        return []

    @staticmethod
    def pick_chat(contact: str, titles: List[str]) -> str:
        """Exact (case-insensitive) match, else a unique partial match; refuse anything ambiguous."""
        wanted = contact.strip().lower()
        exact = [t for t in titles if t.strip().lower() == wanted]
        if exact:
            return exact[0]
        partial = [t for t in titles if wanted and wanted in t.lower()]
        if len(partial) == 1:
            return partial[0]
        if not partial:
            raise WhatsAppError(f"I couldn't find '{contact}' in WhatsApp.")
        raise WhatsAppError(f"'{contact}' matches several chats ({', '.join(partial[:5])}). "
                            f"Tell me the full name, or give me the phone number.")

    async def _open_chat_by_name(self, page, contact: str) -> str:
        search = await self._first_present(page, SEARCH_BOX, 15000)
        if not search:
            raise WhatsAppError("I couldn't find WhatsApp Web's search box (its page layout may have changed).")
        await search.click()
        await asyncio.sleep(0.3)
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await search.type(contact, delay=50)
        await asyncio.sleep(1.5)
        title = self.pick_chat(contact, await self._chat_titles(page))
        await page.locator(f'span[title="{_css_quote(title)}"]').first.click()
        await asyncio.sleep(0.8)
        header = await self._first_present(page, CHAT_HEADER, 5000)
        opened = (await header.get_attribute("title")) if header else ""
        if not opened or opened.strip().lower() != title.strip().lower():
            raise WhatsAppError(f"The chat that opened is '{opened or 'unknown'}', not '{title}'. "
                                f"I stopped before typing anything.")
        return opened

    async def _wait_logged_in(self, page) -> bool:
        return bool(await self._first_present(page, SEARCH_BOX, 60000))

    async def _goto_web(self, page, url: str) -> None:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

    async def _read_back(self, page, message: str, timeout: float = 10.0) -> bool:
        want = " ".join(message.split())
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            texts = await page.eval_on_selector_all(OUTGOING_TEXT, "els => els.map(e => e.innerText)")
            if texts and want in " ".join(texts[-1].split()):
                return True
            await asyncio.sleep(0.4)
        return False

    async def send_message_web(self, contact_name: str, message: str) -> Dict[str, Any]:
        """Send through WhatsApp Web; 'success' is only reported after the message shows up in the chat."""
        number = resolve_number(contact_name)
        try:
            page = await self._ensure_browser()
            if number:
                await self._goto_web(page, f"{self.whatsapp_url}/send?phone={number}"
                                           f"&text={urllib.parse.quote(message)}")
            elif "web.whatsapp.com" not in (page.url or ""):
                await self._goto_web(page, self.whatsapp_url)
            if not await self._wait_logged_in(page):
                return {"status": "waiting", "sent": False,
                        "message": "WhatsApp Web opened. Scan the QR code with your phone, then try again."}

            if number:
                target = f"+{number}"
                composer = await self._first_present(page, COMPOSER, 20000)
                if not composer:
                    raise WhatsAppError(f"The chat for {target} didn't open (is it a WhatsApp number?).")
            else:
                target = await self._open_chat_by_name(page, contact_name)
                composer = await self._first_present(page, COMPOSER, 8000)
                if not composer:
                    raise WhatsAppError("I couldn't find WhatsApp Web's message box (its layout may have changed).")
                await composer.click()
                await composer.type(message, delay=20)
                await asyncio.sleep(0.3)
            await composer.press("Enter")
        except WhatsAppError as exc:
            return {"status": "error", "sent": False, "message": str(exc)}
        except Exception as exc:
            logger.error("WhatsApp Web send failed: %s", exc)
            return {"status": "error", "sent": False, "message": f"Failed to send via WhatsApp Web: {exc}"}

        preview = f"\"{message[:80]}{'...' if len(message) > 80 else ''}\""
        if await self._read_back(page, message):
            return {"status": "success", "sent": True, "via": "web", "verified": True,
                    "message": f"Sent {preview} to {target} on WhatsApp Web (seen in the chat)."}
        return {"status": "unconfirmed", "sent": True, "via": "web", "verified": False,
                "message": f"I pressed send for {preview} to {target}, but couldn't see it appear in the chat. "
                           f"Please check WhatsApp Web."}

    # ══════════════════════════════════════════════════════════════════════════
    # Unified entry points
    # ══════════════════════════════════════════════════════════════════════════

    async def send_message(self, contact_name: str, message: str) -> Dict[str, Any]:
        """Send a WhatsApp message.

        WHATSAPP_MODE=auto (default): Desktop first on Windows, then Web.
                       web: Web only (verified). desktop: Desktop only.
        Web is only tried if the desktop attempt failed before sending anything.
        """
        mode = os.environ.get("WHATSAPP_MODE", "auto").strip().lower()
        native_result: Optional[Dict[str, Any]] = None
        if self._is_windows() and mode in ("auto", "desktop"):
            native_result = await self.send_message_native(contact_name, message)
            if native_result.get("sent") or mode == "desktop":
                return native_result
            logger.info("WhatsApp Desktop did not send (%s); trying WhatsApp Web.", native_result.get("message"))
        try:
            web_result = await self.send_message_web(contact_name, message)
        except Exception as exc:
            web_result = {"status": "error", "sent": False, "message": str(exc)}
        if native_result and web_result.get("status") == "error":
            web_result["message"] = (f"Both WhatsApp Desktop and Web failed. Desktop: {native_result.get('message')} "
                                     f"Web: {web_result.get('message')}")
        return web_result

    async def open_whatsapp(self) -> Dict[str, Any]:
        """Open WhatsApp Desktop if installed, otherwise WhatsApp Web (any OS)."""
        if self._is_windows():
            try:
                await asyncio.to_thread(self._launch_desktop, "whatsapp:")
                return {"status": "success", "message": "WhatsApp desktop app opened."}
            except Exception:
                pass

        try:
            from tools.os_tools import OSTools
            result = await OSTools().open_application("whatsapp")
            if result.get("status") == "success":
                return {"status": "success", "message": result.get("message", "WhatsApp opened.")}
        except Exception:
            pass

        try:
            if webbrowser.open(self.whatsapp_url):
                return {"status": "success",
                        "message": "Opened WhatsApp Web in the browser (desktop app not found)."}
        except Exception:
            pass
        return {"status": "error", "message": "Could not open WhatsApp by any method."}

    async def read_recent_messages(self, contact_name: str, count: int = 5) -> Dict[str, Any]:
        """Read recent messages from a contact via WhatsApp Web."""
        try:
            page = await self._ensure_browser()
            if "web.whatsapp.com" not in (page.url or ""):
                await self._goto_web(page, self.whatsapp_url)
            if not await self._wait_logged_in(page):
                return {"status": "waiting", "message": "WhatsApp Web needs QR login."}
            await self._open_chat_by_name(page, contact_name)
            await asyncio.sleep(0.5)
            messages = await page.evaluate("""([count, who]) => {
                const msgs = document.querySelectorAll('div.message-in, div.message-out');
                const result = [];
                for (const m of Array.from(msgs).slice(-count)) {
                    const text = m.querySelector('span.selectable-text');
                    const isOut = m.classList.contains('message-out');
                    if (text) result.push({ from: isOut ? 'You' : who, text: text.innerText });
                }
                return result;
            }""", [int(count), contact_name])
            return {
                "status": "success",
                "messages": messages,
                "message": f"Last {len(messages)} messages with {contact_name}:\n"
                    + "\n".join(f"  {m['from']}: {m['text'][:100]}" for m in messages),
            }
        except WhatsAppError as exc:
            return {"status": "error", "message": str(exc)}
        except Exception as exc:
            return {"status": "error", "message": f"Failed to read messages: {exc}"}
