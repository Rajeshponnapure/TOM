"""
WhatsApp automation for TOM.

Two modes:
1. Native desktop app (preferred) — uses the WhatsApp Windows app via URL protocol + pyautogui
2. WhatsApp Web fallback — uses Playwright browser automation

The native app approach opens WhatsApp Desktop directly using the whatsapp:// protocol,
then uses keyboard automation to search for contacts and send messages.
"""
import asyncio
import os
import subprocess
import time
import logging
import urllib.parse

logger = logging.getLogger(__name__)

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.3
    _PYAUTOGUI_OK = True
except ImportError:
    _PYAUTOGUI_OK = False


class WhatsAppTools:
    def __init__(self, browser_tools=None):
        self.browser_tools = browser_tools
        self.whatsapp_url = "https://web.whatsapp.com"
        self._app_family = "5319275A.WhatsAppDesktop_cv1g1gvanyjgm"

    # ── Native Desktop App (preferred) ───────────────────────────────────────

    async def send_message_native(self, contact_name: str, message: str):
        """Send a message via the WhatsApp Desktop app using keyboard automation."""

        if not _PYAUTOGUI_OK:
            return {
                "status": "error",
                "message": "pyautogui not installed. Run: pip install pyautogui",
            }

        # Step 1: Open WhatsApp
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "whatsapp:"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            await asyncio.sleep(4)
        except Exception as e:
            return {"status": "error", "message": f"Could not open WhatsApp: {e}"}

        try:
            # Step 2: Focus WhatsApp window and bring to front
            try:
                import ctypes
                import win32gui
                import win32con

                def _find_whatsapp():
                    result = []
                    def cb(hwnd, _):
                        if win32gui.IsWindowVisible(hwnd):
                            title = win32gui.GetWindowText(hwnd).lower()
                            if "whatsapp" in title:
                                result.append(hwnd)
                    win32gui.EnumWindows(cb, None)
                    return result[0] if result else None

                hwnd = _find_whatsapp()
                if hwnd:
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
                    await asyncio.sleep(0.8)
            except ImportError:
                pass

            # Step 3: Click on the search/new-chat area
            # Use Ctrl+N for new chat (works on WhatsApp Desktop UWP)
            # or click the search bar area directly
            await asyncio.sleep(0.5)

            # Try clipboard-based approach for contact search
            try:
                import pyperclip
                _has_pyperclip = True
            except ImportError:
                _has_pyperclip = False

            # Open search — Ctrl+F works on WhatsApp Web-style, for Desktop try clicking search
            pyautogui.hotkey("ctrl", "n")
            await asyncio.sleep(0.8)

            # Clear any existing search text
            pyautogui.hotkey("ctrl", "a")
            await asyncio.sleep(0.2)

            # Type contact name using clipboard (handles all characters)
            if _has_pyperclip:
                pyperclip.copy(contact_name)
                pyautogui.hotkey("ctrl", "v")
            else:
                for char in contact_name:
                    if char.isascii():
                        pyautogui.press(char)
                    else:
                        pyautogui.write(char)
                    await asyncio.sleep(0.05)

            await asyncio.sleep(2.0)

            # Select the first matching contact
            pyautogui.press("enter")
            await asyncio.sleep(1.5)

            # Step 4: Type the message in the message input box
            # The message input should be focused after selecting a contact
            # Click the message input area (bottom of WhatsApp window)
            screen_w, screen_h = pyautogui.size()
            pyautogui.click(x=screen_w // 2, y=screen_h - 80)
            await asyncio.sleep(0.5)

            # Type message using clipboard for reliability
            if _has_pyperclip:
                pyperclip.copy(message)
                pyautogui.hotkey("ctrl", "v")
            else:
                for char in message:
                    if char.isascii():
                        pyautogui.press(char)
                    else:
                        pyautogui.write(char)
                    await asyncio.sleep(0.02)

            await asyncio.sleep(0.5)

            # Step 5: Send with Enter
            pyautogui.press("enter")
            await asyncio.sleep(1)

            logger.info(f"WhatsApp message sent to '{contact_name}'")
            return {
                "status": "success",
                "message": f"Message sent to {contact_name} via WhatsApp: \"{message[:80]}{'...' if len(message) > 80 else ''}\"",
            }

        except Exception as e:
            logger.error(f"WhatsApp native send failed: {e}")
            return {
                "status": "error",
                "message": f"WhatsApp automation failed: {e}. WhatsApp is open — you can send manually.",
            }

    # ── WhatsApp Web Fallback ────────────────────────────────────────────────

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

    async def send_message_web(self, contact_name: str, message: str):
        """Send a message via WhatsApp Web using Playwright browser automation."""
        page = await self._ensure_browser()

        current_url = page.url if page else ""
        if "web.whatsapp.com" not in current_url:
            await page.goto(self.whatsapp_url, wait_until="domcontentloaded", timeout=30000)
            try:
                await page.wait_for_selector(
                    'div[contenteditable="true"][data-tab="3"]',
                    timeout=60000,
                )
            except Exception:
                return {
                    "status": "waiting",
                    "message": "WhatsApp Web opened. Scan the QR code with your phone, then try again.",
                }

        try:
            search_box = await page.wait_for_selector(
                'div[contenteditable="true"][data-tab="3"]',
                timeout=15000,
            )
            await search_box.click()
            await asyncio.sleep(0.3)
            await search_box.fill("")
            await search_box.type(contact_name, delay=50)
            await asyncio.sleep(1.5)

            contact = await page.wait_for_selector(
                f'span[title*="{contact_name}" i]',
                timeout=8000,
            )
            if not contact:
                return {"status": "error", "message": f"Contact '{contact_name}' not found."}
            await contact.click()
            await asyncio.sleep(0.8)

            msg_box = await page.wait_for_selector(
                'div[contenteditable="true"][data-tab="10"]',
                timeout=8000,
            )
            await msg_box.click()
            await msg_box.type(message, delay=20)
            await asyncio.sleep(0.3)
            await msg_box.press("Enter")
            await asyncio.sleep(1)

            logger.info(f"WhatsApp Web message sent to '{contact_name}'")
            return {
                "status": "success",
                "message": f"Message sent to {contact_name} via WhatsApp Web: \"{message[:80]}{'...' if len(message) > 80 else ''}\"",
            }

        except Exception as e:
            logger.error(f"WhatsApp Web send failed: {e}")
            return {"status": "error", "message": f"Failed to send via WhatsApp Web: {e}"}

    # ── Unified send method ──────────────────────────────────────────────────

    async def send_message(self, contact_name: str, message: str):
        """Send a WhatsApp message. Tries native desktop app first, falls back to Web."""
        # Prefer native desktop app
        result = await self.send_message_native(contact_name, message)
        if result.get("status") == "success":
            return result

        # If native failed and we have browser tools, try Web
        logger.info("Native WhatsApp failed, falling back to WhatsApp Web...")
        try:
            return await self.send_message_web(contact_name, message)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Both native and web WhatsApp failed. Native: {result.get('message')}. Web: {e}",
            }

    async def open_whatsapp(self):
        """Open the WhatsApp desktop app, trying multiple discovery methods."""
        # Try 1: URI protocol
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "whatsapp:"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return {"status": "success", "message": "WhatsApp desktop app opened."}
        except Exception:
            pass

        # Try 2: Dynamic app discovery
        try:
            from tools.os_tools import OSTools
            os_tools = OSTools()
            launch_path = os_tools.find_application("whatsapp")
            if launch_path:
                if launch_path.startswith("shell:AppsFolder"):
                    subprocess.Popen(
                        ["cmd", "/c", "start", "", launch_path],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                elif launch_path.lower().endswith(".lnk"):
                    os.startfile(launch_path)
                else:
                    subprocess.Popen([launch_path])
                return {"status": "success", "message": f"WhatsApp opened ({launch_path})."}
        except Exception:
            pass

        # Try 3: Open WhatsApp Web as last resort
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "https://web.whatsapp.com"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return {"status": "success", "message": "Opened WhatsApp Web in browser (desktop app not found)."}
        except Exception as e:
            return {"status": "error", "message": f"Could not open WhatsApp by any method: {e}"}

    async def read_recent_messages(self, contact_name: str, count: int = 5):
        """Read recent messages from a contact via WhatsApp Web."""
        page = await self._ensure_browser()

        current_url = page.url if page else ""
        if "web.whatsapp.com" not in current_url:
            await page.goto(self.whatsapp_url, wait_until="domcontentloaded", timeout=30000)
            try:
                await page.wait_for_selector(
                    'div[contenteditable="true"][data-tab="3"]',
                    timeout=60000,
                )
            except Exception:
                return {"status": "waiting", "message": "WhatsApp Web needs QR login."}

        try:
            search_box = await page.wait_for_selector(
                'div[contenteditable="true"][data-tab="3"]', timeout=10000,
            )
            await search_box.click()
            await search_box.fill("")
            await search_box.type(contact_name, delay=50)
            await asyncio.sleep(1.5)

            contact = await page.wait_for_selector(
                f'span[title*="{contact_name}" i]', timeout=8000,
            )
            await contact.click()
            await asyncio.sleep(1)

            messages = await page.evaluate(f"""() => {{
                const msgs = document.querySelectorAll('div.message-in, div.message-out');
                const result = [];
                const slice = Array.from(msgs).slice(-{count});
                for (const m of slice) {{
                    const text = m.querySelector('span.selectable-text');
                    const isOut = m.classList.contains('message-out');
                    if (text) result.push({{ from: isOut ? 'You' : '{contact_name}', text: text.innerText }});
                }}
                return result;
            }}""")

            return {
                "status": "success",
                "messages": messages,
                "message": f"Last {len(messages)} messages with {contact_name}:\n"
                    + "\n".join(f"  {m['from']}: {m['text'][:100]}" for m in messages),
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to read messages: {e}"}
