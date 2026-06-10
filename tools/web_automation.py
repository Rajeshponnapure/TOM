"""
Web Automation Suite for TOM.
Full browser DevTools integration: console, network, elements, auto-debug.

Capabilities:
- Open DevTools and capture console logs/errors
- Capture network requests and failed responses
- Execute JS in page context
- Click elements by text or selector
- Fill forms with user data
- Full page verification workflow
- Auto-debug loop: detect errors -> analyze -> fix -> retest
"""
import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from tools.project_paths import project_path_str

logger = logging.getLogger(__name__)


@dataclass
class ConsoleEntry:
    level: str
    text: str
    source: str = ""
    line: int = 0
    timestamp: float = 0.0


@dataclass
class NetworkEntry:
    url: str
    method: str
    status: int
    status_text: str
    content_type: str = ""
    request_headers: Dict = field(default_factory=dict)
    response_headers: Dict = field(default_factory=dict)
    body: str = ""
    error: str = ""
    duration_ms: float = 0.0
    timestamp: float = 0.0


@dataclass
class PageError:
    type: str
    message: str
    source: str = ""
    line: int = 0
    column: int = 0
    stack: str = ""


class WebAutomationError(Exception):
    pass


class WebAutomationSuite:
    """Full browser automation with DevTools, console, network inspection."""

    def __init__(self, browser_tools=None):
        self.browser_tools = browser_tools
        self._console_logs: List[ConsoleEntry] = []
        self._network_logs: List[NetworkEntry] = []
        self._page_errors: List[PageError] = []
        self._listener_active = False
        self.user_profile = self._load_user_profile()

    def _load_user_profile(self) -> Dict[str, Any]:
        profile_path = project_path_str("tom_brain", "user_profile.json")
        try:
            if os.path.exists(profile_path):
                with open(profile_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {"name": "Rajesh", "email": "", "phone": ""}

    async def _get_page(self):
        if not self.browser_tools:
            raise WebAutomationError("BrowserTools not available")
        page = await self.browser_tools._get_active_page()
        if not page:
            raise WebAutomationError("No active browser page")
        return page

    async def start_listeners(self):
        """Start capturing console and network events."""
        page = await self._get_page()
        if self._listener_active:
            return

        self._console_logs = []
        self._network_logs = []
        self._page_errors = []

        page.on("console", self._on_console)
        page.on("response", self._on_response)
        page.on("pageerror", self._on_page_error)
        page.on("requestfailed", self._on_request_failed)

        self._listener_active = True

    async def stop_listeners(self):
        """Stop capturing events."""
        page = await self._get_page()
        if not self._listener_active:
            return
        try:
            page.remove_listener("console", self._on_console)
            page.remove_listener("response", self._on_response)
            page.remove_listener("pageerror", self._on_page_error)
            page.remove_listener("requestfailed", self._on_request_failed)
        except Exception:
            pass
        self._listener_active = False

    def _on_console(self, msg):
        entry = ConsoleEntry(
            level=msg.type,
            text=msg.text,
            source=msg.location.url if msg.location else "",
            line=msg.location.line_number if msg.location else 0,
        )
        self._console_logs.append(entry)

    async def _on_response(self, response):
        status = response.status
        url = response.url
        entry = NetworkEntry(
            url=url,
            method=response.request.method,
            status=status,
            status_text="OK" if status < 400 else "ERROR",
            content_type=response.headers.get("content-type", ""),
        )
        if status >= 400:
            try:
                entry.body = await response.text()
            except Exception:
                entry.body = ""
        self._network_logs.append(entry)

    def _on_page_error(self, error):
        entry = PageError(
            type="page_error",
            message=str(error),
        )
        self._page_errors.append(entry)

    def _on_request_failed(self, request):
        entry = NetworkEntry(
            url=request.url,
            method=request.method,
            status=0,
            status_text="FAILED",
            error=request.failure.error_text if request.failure else "Unknown",
        )
        self._network_logs.append(entry)

    async def capture_console_logs(self) -> Dict[str, Any]:
        """Get all console messages captured so far."""
        logs = []
        for entry in self._console_logs:
            logs.append({
                "level": entry.level,
                "text": entry.text[:500],
                "source": entry.source,
                "line": entry.line,
            })
        return {"status": "success", "console_logs": logs, "count": len(logs)}

    async def capture_console_errors(self) -> Dict[str, Any]:
        """Get only error-level console messages."""
        errors = [e for e in self._console_logs if e.level in ("error", "assert")]
        return {
            "status": "success",
            "console_errors": [{"text": e.text[:500], "source": e.source, "line": e.line} for e in errors],
            "count": len(errors),
        }

    async def capture_network_errors(self) -> Dict[str, Any]:
        """Get failed network requests (4xx, 5xx, or connection failures)."""
        errors = [
            e for e in self._network_logs
            if e.status >= 400 or e.status == 0
        ]
        return {
            "status": "success",
            "network_errors": [
                {"url": e.url[:200], "method": e.method, "status": e.status, "error": e.error}
                for e in errors
            ],
            "count": len(errors),
        }

    async def capture_all_errors(self) -> Dict[str, Any]:
        """Get console errors + network errors + page errors together."""
        console_errs = await self.capture_console_errors()
        network_errs = await self.capture_network_errors()
        page_errs = [
            {"type": e.type, "message": e.message[:500]} for e in self._page_errors
        ]
        all_errors = (
            console_errs.get("console_errors", [])
            + network_errs.get("network_errors", [])
            + page_errs
        )
        return {
            "status": "success",
            "all_errors": all_errors,
            "total_count": len(all_errors),
            "console_count": console_errs.get("count", 0),
            "network_count": network_errs.get("count", 0),
            "page_error_count": len(page_errs),
        }

    async def execute_script(self, script: str) -> Any:
        """Execute JavaScript in page context."""
        page = await self._get_page()
        try:
            result = await page.evaluate(script)
            return result
        except Exception as e:
            raise WebAutomationError(f"Script execution failed: {e}")

    async def get_page_html(self) -> str:
        """Get full page HTML."""
        return await self.execute_script("document.documentElement.outerHTML")

    async def click_element_by_text(self, text: str, partial: bool = True) -> Dict[str, Any]:
        """Click an element by its visible text content."""
        page = await self._get_page()
        try:
            if partial:
                selector = f"text=/{text}/i"
            else:
                selector = f"text={text}"
            await page.click(selector, timeout=5000)
            return {"status": "success", "message": f"Clicked element with text: {text}"}
        except Exception as e:
            return {"status": "error", "message": f"Could not click '{text}': {e}"}

    async def click_elements_by_selector(self, selector: str) -> Dict[str, Any]:
        """Click all elements matching a selector."""
        page = await self._get_page()
        try:
            elements = await page.query_selector_all(selector)
            clicked = 0
            for el in elements:
                try:
                    await el.click(timeout=2000)
                    clicked += 1
                    await asyncio.sleep(0.3)
                except Exception:
                    continue
            return {"status": "success", "message": f"Clicked {clicked} elements matching '{selector}'"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def click_all_buttons(self) -> Dict[str, Any]:
        """Click every interactive element on the page and report results."""
        page = await self._get_page()
        results = []
        selectors = [
            "button",
            "a[href]",
            "input[type='submit']",
            "input[type='button']",
            "[role='button']",
            ".btn",
        ]
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                for el in elements:
                    try:
                        tag = await el.get_attribute("outerHTML") or ""
                        text = await el.inner_text() or ""
                        tag_name = await el.evaluate("el => el.tagName.toLowerCase()")
                        href = await el.get_attribute("href") or ""

                        result = {
                            "tag": tag_name,
                            "text": text[:60],
                            "href": href[:100] if href else "",
                        }

                        try:
                            box = await el.bounding_box()
                            result["visible"] = box is not None
                            if box:
                                await el.click(timeout=2000)
                                result["clicked"] = True
                                await asyncio.sleep(0.2)
                            else:
                                result["clicked"] = False
                                result["reason"] = "not visible"
                        except Exception as ex:
                            result["clicked"] = False
                            result["reason"] = str(ex)[:100]

                        results.append(result)
                    except Exception:
                        continue
            except Exception:
                continue

        successful = sum(1 for r in results if r.get("clicked"))
        failed = sum(1 for r in results if not r.get("clicked"))
        return {
            "status": "success",
            "total_elements": len(results),
            "clicked_successfully": successful,
            "click_failed": failed,
            "elements": results,
        }

    async def fill_form_fields(self, data: Dict[str, str]) -> Dict[str, Any]:
        """Fill form fields intelligently by matching labels/names/placeholders to data keys."""
        page = await self._get_page()
        filled = []
        not_found = []

        field_map = {
            "name": ["name", "full name", "your name", "username"],
            "email": ["email", "e-mail", "email address", "your email"],
            "phone": ["phone", "telephone", "mobile", "phone number", "contact"],
            "password": ["password", "pass", "pwd"],
            "address": ["address", "street", "location"],
            "city": ["city", "town"],
            "state": ["state", "province", "region"],
            "zip": ["zip", "zip code", "postal", "postcode", "pincode", "pin code"],
            "country": ["country", "nation"],
            "message": ["message", "comments", "description", "content", "body"],
            "subject": ["subject", "topic"],
            "search": ["search", "query", "q"],
        }

        for key, value in data.items():
            if not value:
                continue
            key_lower = key.lower()
            possible_labels = field_map.get(key_lower, [key_lower])
            found = False

            for label in possible_labels:
                selectors = [
                    f"input[type='text'][name='{label}']",
                    f"input[type='email'][name='{label}']",
                    f"input[type='tel'][name='{label}']",
                    f"input[name='{label}']",
                    f"textarea[name='{label}']",
                    f"input[placeholder*='{label}' i]",
                    f"textarea[placeholder*='{label}' i]",
                    f"input[id*='{label}' i]",
                    f"textarea[id*='{label}' i]",
                    f"label:has-text('{label}') + input",
                    f"label:has-text('{label}') + textarea",
                ]
                for sel in selectors:
                    try:
                        el = await page.query_selector(sel)
                        if el:
                            await el.fill(value)
                            filled.append({"field": key, "selector": sel})
                            found = True
                            break
                    except Exception:
                        continue
                if found:
                    break

            if not found:
                not_found.append(key)

        return {
            "status": "success" if filled else "error",
            "filled": filled,
            "not_found": not_found,
            "filled_count": len(filled),
        }

    async def fill_form_with_user_data(self, fields: List[str] = None) -> Dict[str, Any]:
        """Auto-fill form using stored user profile data."""
        data = {}
        if not fields:
            fields = ["name", "email", "phone", "address"]

        profile = self.user_profile
        field_data = {
            "name": profile.get("name", ""),
            "email": profile.get("email", ""),
            "phone": profile.get("phone", ""),
            "address": profile.get("address", ""),
            "city": profile.get("city", ""),
            "state": profile.get("state", ""),
            "zip": profile.get("zip", ""),
            "country": profile.get("country", ""),
        }

        for f in fields:
            if f in field_data and field_data[f]:
                data[f] = field_data[f]

        if not data:
            return {"status": "error", "message": "No user data available for these fields"}

        return await self.fill_form_fields(data)

    async def verify_page_functionality(self) -> Dict[str, Any]:
        """Run comprehensive page verification: check for errors, test interactivity."""
        page = await self._get_page()
        results = {
            "page_loaded": False,
            "title": "",
            "console_errors": [],
            "network_errors": [],
            "broken_links": [],
            "interactive_elements": 0,
            "forms_found": 0,
            "status": "unknown",
        }

        try:
            results["title"] = await page.title()
            results["page_loaded"] = True
        except Exception:
            results["page_loaded"] = False
            return results

        errors = await self.capture_all_errors()
        results["console_errors"] = errors.get("all_errors", [])
        results["total_errors"] = errors.get("total_count", 0)

        try:
            links = await page.query_selector_all("a[href]")
            broken = []
            for link in links:
                try:
                    href = await link.get_attribute("href")
                    if href and href.startswith(("http", "//")):
                        broken.append({"href": href[:200], "status": "checking"})
                except Exception:
                    continue
            results["total_links"] = len(links)
            results["broken_links"] = broken
        except Exception:
            pass

        try:
            buttons = await page.query_selector_all("button, input[type='submit'], input[type='button'], [role='button']")
            results["interactive_elements"] = len(buttons)
        except Exception:
            pass

        try:
            forms = await page.query_selector_all("form")
            results["forms_found"] = len(forms)
        except Exception:
            pass

        results["status"] = "pass" if results.get("total_errors", 0) == 0 else "has_errors"
        return results

    async def auto_debug_loop(
        self,
        url: str,
        max_iterations: int = 5,
        llm_callback=None,
        fix_callback=None,
    ) -> Dict[str, Any]:
        """Full auto-debug cycle:
        1. Open URL
        2. Capture console + network errors
        3. Analyze errors with LLM
        4. Generate fix
        5. Apply fix
        6. Reload and retest
        7. Repeat until clean or max iterations
        """
        page = await self._get_page()
        iteration_results = []

        for iteration in range(1, max_iterations + 1):
            logger.info(f"[AUTO-DEBUG] Iteration {iteration}/{max_iterations}")

            await self.start_listeners()

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(1)
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to load page: {e}",
                    "iteration": iteration,
                    "url": url,
                }

            verification = await self.verify_page_functionality()
            errors = verification.get("console_errors", [])
            error_count = verification.get("total_errors", 0)

            iteration_result = {
                "iteration": iteration,
                "url": url,
                "error_count": error_count,
                "errors": errors[:20],
                "verification": verification,
            }

            if error_count == 0:
                iteration_result["status"] = "clean"
                iteration_results.append(iteration_result)
                return {
                    "status": "success",
                    "message": f"Page clean after {iteration} iteration(s)",
                    "iterations": iteration_results,
                    "total_iterations": iteration,
                }

            if llm_callback and errors:
                error_text = json.dumps(errors[:10], indent=2)
                analysis = await llm_callback(
                    f"Analyze these web page errors and suggest fixes:\n{error_text}\n\n"
                    f"URL: {url}\nPage title: {verification.get('title', '')}"
                )
                iteration_result["analysis"] = analysis

            if fix_callback and errors:
                try:
                    fix_result = await fix_callback(errors, iteration)
                    iteration_result["fix_applied"] = fix_result
                except Exception as e:
                    iteration_result["fix_error"] = str(e)

            iteration_results.append(iteration_result)

            if iteration < max_iterations:
                await asyncio.sleep(0.5)

        return {
            "status": "max_iterations_reached",
            "message": f"Reached max {max_iterations} iterations with {error_count} errors remaining",
            "iterations": iteration_results,
            "total_iterations": max_iterations,
            "final_error_count": error_count,
        }

    async def open_devtools(self) -> Dict[str, Any]:
        """Open Chrome DevTools via keyboard shortcut."""
        page = await self._get_page()
        try:
            await page.keyboard.press("F12")
            await asyncio.sleep(0.5)
            return {"status": "success", "message": "DevTools opened"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_console_history(self) -> List[ConsoleEntry]:
        """Get console history by injecting script."""
        page = await self._get_page()
        try:
            result = await page.evaluate("""() => {
                if (window.__tomConsoleHistory) {
                    return window.__tomConsoleHistory;
                }
                window.__tomConsoleHistory = [];
                const orig = console.log;
                console.log = function() {
                    window.__tomConsoleHistory.push({
                        level: 'log',
                        text: Array.from(arguments).map(a => String(a)).join(' '),
                        timestamp: Date.now()
                    });
                    orig.apply(console, arguments);
                };
                return window.__tomConsoleHistory;
            }""")
            return result
        except Exception:
            return []

    async def inject_console_capture(self) -> Dict[str, Any]:
        """Inject JS to capture all console output going forward."""
        page = await self._get_page()
        script = """
        (function() {
            if (window.__tomConsoleInjected) return;
            window.__tomConsoleInjected = true;
            window.__tomConsoleLogs = [];

            ['log', 'warn', 'error', 'info', 'debug'].forEach(function(level) {
                var orig = console[level];
                console[level] = function() {
                    window.__tomConsoleLogs.push({
                        level: level,
                        text: Array.from(arguments).map(function(a) {
                            try { return JSON.stringify(a); }
                            catch(e) { return String(a); }
                        }).join(' '),
                        timestamp: Date.now()
                    });
                    return orig.apply(console, arguments);
                };
            });

            window.addEventListener('error', function(e) {
                window.__tomConsoleLogs.push({
                    level: 'unhandled_error',
                    text: e.message + ' at ' + e.filename + ':' + e.lineno,
                    timestamp: Date.now()
                });
            });

            window.addEventListener('unhandledrejection', function(e) {
                window.__tomConsoleLogs.push({
                    level: 'unhandled_promise',
                    text: String(e.reason),
                    timestamp: Date.now()
                });
            });
        })();
        """
        try:
            await page.evaluate(script)
            return {"status": "success", "message": "Console capture injected"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_injected_console_logs(self) -> Dict[str, Any]:
        """Get console logs captured via injected script."""
        page = await self._get_page()
        try:
            logs = await page.evaluate("window.__tomConsoleLogs || []")
            return {"status": "success", "count": len(logs), "logs": logs[-100:]}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def check_localhost(self, port: int = None) -> Dict[str, Any]:
        """Check if a localhost server is running on specified port(s)."""
        import socket

        if port:
            ports_to_check = [port]
        else:
            ports_to_check = [3000, 3001, 5000, 5173, 8080, 8000, 4200, 3002, 5001, 5002]

        results = []
        for p in ports_to_check:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            try:
                result = sock.connect_ex(("127.0.0.1", p))
                if result == 0:
                    results.append({"port": p, "status": "open", "url": f"http://localhost:{p}"})
            except Exception:
                pass
            finally:
                sock.close()

        return {
            "status": "success" if results else "no_servers",
            "servers_found": len(results),
            "servers": results,
        }

    async def open_url_and_wait(self, url: str, wait_for_selector: str = None, timeout: int = 15000) -> Dict[str, Any]:
        """Open URL and wait for specific element or network idle."""
        page = await self._get_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=timeout)
            if wait_for_selector:
                await page.wait_for_selector(wait_for_selector, timeout=timeout)
            return {
                "status": "success",
                "message": f"Opened {url}",
                "title": await page.title(),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def screenshot_page(self, full_page: bool = False) -> bytes:
        """Take a screenshot of the current page."""
        page = await self._get_page()
        return await page.screenshot(full_page=full_page)

    async def wait_and_verify(self, url: str, expected_text: str = None, timeout: int = 15000) -> Dict[str, Any]:
        """Open URL, wait, and verify expected text appears."""
        page = await self._get_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=timeout)
            await asyncio.sleep(1)

            result = {
                "status": "success",
                "url": url,
                "title": await page.title(),
            }

            if expected_text:
                try:
                    content = await page.inner_text("body")
                    found = expected_text.lower() in content.lower()
                    result["text_found"] = found
                    result["expected_text"] = expected_text
                    result["text_check"] = "pass" if found else "fail"
                except Exception as e:
                    result["text_check"] = "error"
                    result["text_error"] = str(e)

            errors = await self.capture_all_errors()
            result["errors"] = errors.get("all_errors", [])
            result["error_count"] = errors.get("total_count", 0)

            return result
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def build_and_verify_webapp(
        self,
        project_path: str,
        build_command: str = "npm run build",
        dev_command: str = "npm run dev",
        port: int = 5173,
        expected_text: str = None,
    ) -> Dict[str, Any]:
        """Build a web app, start dev server, open browser, verify functionality."""
        import subprocess

        results = {
            "build_status": "unknown",
            "server_status": "unknown",
            "browser_status": "unknown",
            "verification": None,
        }

        if not os.path.exists(project_path):
            return {"status": "error", "message": f"Project path not found: {project_path}"}

        build_proc = subprocess.run(
            build_command.split(),
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if build_proc.returncode == 0:
            results["build_status"] = "success"
            results["build_output"] = build_proc.stdout[-500:]
        else:
            results["build_status"] = "failed"
            results["build_output"] = build_proc.stdout[-300:] + build_proc.stderr[-300:]
            return {"status": "error", "message": "Build failed", "results": results}

        server_proc = subprocess.Popen(
            dev_command.split(),
            cwd=project_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        await asyncio.sleep(3)
        results["server_status"] = "started"
        results["server_pid"] = server_proc.pid

        try:
            check = await self.check_localhost(port)
            results["server_check"] = check

            vb = await self.wait_and_verify(
                f"http://localhost:{port}",
                expected_text=expected_text,
            )
            results["browser_status"] = "success" if vb.get("status") == "success" else "failed"
            results["verification"] = vb
        except Exception as e:
            results["browser_status"] = "failed"
            results["verification_error"] = str(e)

        results["status"] = "success" if results["browser_status"] == "success" else "partial"
        return results
