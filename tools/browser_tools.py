from playwright.async_api import async_playwright
from typing import Optional, Dict, Any, List
import asyncio
import os
import shutil
import tempfile
from io import BytesIO

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import pytesseract
except Exception:
    pytesseract = None

class BrowserTools:
    """Handles browser automation with Playwright"""
    
    def __init__(self):
        self.playwright = None
        self.chromium = None
        self.browser = None
        self.context = None
        self.page = None
        self.chrome_profile = None

    async def init_browser(self, headless: bool = False, profile: Optional[str] = None) -> Dict[str, Any]:
        """Initialize Playwright browser for automation with optional Chrome profile"""
        try:
            result = {
                "status": "success",
                "message": "Browser initialized successfully"
            }

            self.playwright = await async_playwright().start()
            chrome_settings = self._get_chrome_settings(profile)

            if chrome_settings["user_data_dir"]:
                try:
                    self.context = await self.playwright.chromium.launch_persistent_context(
                        user_data_dir=chrome_settings["user_data_dir"],
                        headless=headless,
                        executable_path=chrome_settings["executable_path"],
                        args=chrome_settings["args"],
                        viewport={"width": 1920, "height": 1080},
                    )
                except Exception:
                    fallback_user_data_dir = self._prepare_profile_copy(chrome_settings["user_data_dir"])
                    self.context = await self.playwright.chromium.launch_persistent_context(
                        user_data_dir=fallback_user_data_dir,
                        headless=headless,
                        executable_path=chrome_settings["executable_path"],
                        args=chrome_settings["args"],
                        viewport={"width": 1920, "height": 1080},
                    )

                self.browser = self.context
                self.page = self.context.pages[-1] if self.context.pages else await self.context.new_page()
            else:
                self.chromium = await self.playwright.chromium.launch(
                    headless=headless,
                    executable_path=chrome_settings["executable_path"],
                    args=chrome_settings["args"],
                )
                self.context = await self.chromium.new_context(
                    viewport={"width": 1920, "height": 1080}
                )
                self.browser = self.context
                self.page = await self.context.new_page()

            self.chrome_profile = chrome_settings["profile_directory"] or "Default"
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to initialize browser: {str(e)}"
            }

    def _get_chrome_settings(self, profile: Optional[str] = None) -> Dict[str, Any]:
        """Resolve Chrome executable, user data directory, and profile directory."""
        profile_directory = profile or os.getenv("INSTAGRAM_CHROME_PROFILE", "Default")
        user_data_dir = os.getenv("CHROME_PROFILE_PATH") or os.path.join(
            os.getenv("LOCALAPPDATA", ""),
            "Google",
            "Chrome",
            "User Data",
        )
        executable_path = os.getenv("CHROME_EXECUTABLE") or None
        if executable_path and not os.path.exists(executable_path):
            executable_path = None

        args = []
        if profile_directory and profile_directory != "Default":
            args.append(f"--profile-directory={profile_directory}")

        return {
            "profile_directory": profile_directory,
            "user_data_dir": user_data_dir if os.path.exists(user_data_dir) else None,
            "executable_path": executable_path,
            "args": args,
        }

    def _prepare_profile_copy(self, source_user_data_dir: str) -> str:
        """Create a temporary copy of the Chrome user data directory to avoid profile locks."""
        target_user_data_dir = os.path.join(tempfile.gettempdir(), "tom_chrome_user_data_copy")
        os.makedirs(target_user_data_dir, exist_ok=True)

        for entry_name in os.listdir(source_user_data_dir):
            if entry_name.startswith("Singleton") or entry_name == "lockfile":
                continue

            source_entry = os.path.join(source_user_data_dir, entry_name)
            target_entry = os.path.join(target_user_data_dir, entry_name)

            try:
                if os.path.isdir(source_entry):
                    shutil.copytree(source_entry, target_entry, dirs_exist_ok=True)
                else:
                    shutil.copy2(source_entry, target_entry)
            except Exception:
                continue

        return target_user_data_dir

    async def _get_active_page(self):
        """Return the current live page, recreating one if needed."""
        if self.page is not None:
            return self.page
        if self.context and getattr(self.context, "pages", None) and self.context.pages:
            self.page = self.context.pages[-1]
            return self.page
        if self.context:
            self.page = await self.context.new_page()
            return self.page
        return None

    async def open_url(self, url: str) -> Dict[str, Any]:
        """Opens a URL in the browser"""
        from safety.guards import SafetyGuards
        safety = SafetyGuards()
        
        if not safety.validate_url(url):
            return {
                "status": "error",
                "message": "Invalid URL format"
            }

        try:
            page = await self._get_active_page()
            if not page:
                raise Exception("No active browser page available")
            await page.goto(url)
            return {
                "status": "success",
                "message": f"Opened URL: {url}",
                "title": await page.title()
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to open URL: {str(e)}"
            }

    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Types text into an input field"""
        try:
            page = await self._get_active_page()
            if not page:
                raise Exception("No active browser page available")
            await page.fill(selector, text)
            return {
                "status": "success",
                "message": f"Typed '{text}' into {selector}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to type: {str(e)}"
            }

    async def click_element(self, selector: str) -> Dict[str, Any]:
        """Clicks on a web element"""
        try:
            page = await self._get_active_page()
            if not page:
                raise Exception("No active browser page available")
            await page.click(selector)
            return {
                "status": "success",
                "message": f"Clicked element matching: {selector}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to click: {str(e)}"
            }

    async def get_page_content(self, selector: str = None) -> str:
        """Gets visible content from page
        
        Returns:
            String of page content or selected element text
        """
        try:
            page = await self._get_active_page()
            if not page:
                return "Error getting page content: No active browser page available"
            if selector:
                content = await page.inner_text(selector)
            else:
                # Prefer OCR from the visible viewport so the caller gets text rendered in images/video frames.
                content = (await self.capture_visible_text()).strip()
                if not content:
                    content = await page.locator("body").inner_text(timeout=5000)
                content = content[:4000]
            
            return content if isinstance(content, str) else str(content)
        except Exception as e:
            return f"Error getting page content: {str(e)}"

    async def capture_visible_text(self) -> str:
        """OCR the visible viewport to extract text drawn inside posts, images, and video frames."""
        page = await self._get_active_page()
        if not page or Image is None or pytesseract is None:
            return ""

        try:
            screenshot_bytes = await page.screenshot(full_page=False)
            image = Image.open(BytesIO(screenshot_bytes))
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception:
            return ""

    async def get_current_url(self) -> str:
        """Gets the current page URL"""
        try:
            page = await self._get_active_page()
            return page.url if page else ""
        except Exception as e:
            return ""

    async def execute_script(self, script: str) -> Any:
        """Executes JavaScript in the page context
        
        Args:
            script: JavaScript code to execute
            
        Returns:
            Result of JavaScript execution
        """
        try:
            page = await self._get_active_page()
            if not page:
                raise Exception("No active browser page available")
            result = await page.evaluate(script)
            return result
        except Exception as e:
            raise Exception(f"Failed to execute script: {str(e)}")

    async def search(self, query: str, url: str = "https://www.google.com") -> Dict[str, Any]:
        """Performs a Google search"""
        try:
            page = await self._get_active_page()
            if not page:
                raise Exception("No active browser page available")
            await page.goto(url)
            # Click search box and type
            await self.click_element("textarea[jsaction='click']")
            await self.type_text("textarea", query)

            # Submit search
            await self.click_element("button[type='submit']")

            return {
                "status": "success",
                "message": f"Searched for: {query}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Search failed: {str(e)}"
            }

    async def close_browser(self):
        """Closes browser cleanly"""
        try:
            if self.context is not None:
                await self.context.close()
                self.context = None
                self.browser = None
                self.page = None
            if self.chromium is not None:
                await self.chromium.close()
                self.chromium = None
            if self.playwright is not None:
                await self.playwright.stop()
                self.playwright = None
            return {"status": "success", "message": "Browser closed"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def __del__(self):
        pass

    # ── Web Automation Suite Integration ────────────────────────────────

    async def get_automation(self):
        """Lazy-load and return WebAutomationSuite instance."""
        if not hasattr(self, '_automation') or self._automation is None:
            from tools.web_automation import WebAutomationSuite
            self._automation = WebAutomationSuite(self)
        return self._automation

    async def verify_page(self) -> Dict[str, Any]:
        """Verify current page functionality: check errors, test interactivity."""
        auto = await self.get_automation()
        await auto.start_listeners()
        return await auto.verify_page_functionality()

    async def click_all_interactive(self) -> Dict[str, Any]:
        """Click every interactive element on the page."""
        auto = await self.get_automation()
        return await auto.click_all_buttons()

    async def get_all_errors(self) -> Dict[str, Any]:
        """Capture console + network + page errors."""
        auto = await self.get_automation()
        await auto.start_listeners()
        return await auto.capture_all_errors()

    async def auto_debug(self, url: str, max_iterations: int = 5, llm_callback=None, fix_callback=None) -> Dict[str, Any]:
        """Full auto-debug loop: detect -> analyze -> fix -> retest."""
        auto = await self.get_automation()
        return await auto.auto_debug_loop(url, max_iterations, llm_callback, fix_callback)

    async def fill_form(self, data: Dict[str, str]) -> Dict[str, Any]:
        """Fill form fields intelligently."""
        auto = await self.get_automation()
        return await auto.fill_form_fields(data)

    async def fill_form_with_profile(self, fields: List[str] = None) -> Dict[str, Any]:
        """Auto-fill form using stored user profile data."""
        auto = await self.get_automation()
        return await auto.fill_form_with_user_data(fields)

    async def click_text(self, text: str) -> Dict[str, Any]:
        """Click element by visible text."""
        auto = await self.get_automation()
        return await auto.click_element_by_text(text)

    async def wait_and_verify(self, url: str, expected_text: str = None) -> Dict[str, Any]:
        """Open URL, wait, verify expected text appears, check errors."""
        auto = await self.get_automation()
        return await auto.wait_and_verify(url, expected_text)

    async def check_localhost_servers(self, port: int = None) -> Dict[str, Any]:
        """Check running localhost servers."""
        auto = await self.get_automation()
        return await auto.check_localhost(port)

    async def build_and_verify_app(self, project_path: str, build_command: str = "npm run build",
                                    dev_command: str = "npm run dev", port: int = 5173,
                                    expected_text: str = None) -> Dict[str, Any]:
        """Build, start dev server, open browser, verify functionality."""
        auto = await self.get_automation()
        return await auto.build_and_verify_webapp(project_path, build_command, dev_command, port, expected_text)
