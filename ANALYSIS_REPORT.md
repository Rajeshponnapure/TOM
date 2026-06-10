# TOM Autonomous Agent - Analysis Report

**Generated:** May 14, 2026  
**Scope:** Full codebase analysis (30+ source files)  
**Severity Legend:** 🔴 Critical | 🟠 High | 🟡 Medium | 🔵 Low

---

## 🔴 CRITICAL - Will Cause Agent Crash or Malfunction

### 1. `OSTools.__init__()` Defined Twice — `app_paths` Never Initialized

- **File:** `tools/os_tools.py`, lines 9 and 160
- **Problem:** The class has TWO `__init__` methods. Python's second `__init__` completely **overrides** the first, so `self.app_paths`, `self.config_dir`, and the `os.makedirs()` call from line 10–11 are **never executed**.
- **Verified:** `hasattr(OSTools(), 'app_paths')` returns `False`.
- **Impact:** Any call to `OSTools.open_application()` raises `AttributeError: 'OSTools' object has no attribute 'app_paths'`. Opening any application (Chrome, Word, Excel) will crash the agent.
- **Fix:** Remove the duplicate `__init__` at line 160 (lines 160–162, which only contains `pass`).

---

### 2. "Event Loop is Closed" Runtime Crash

- **File:** `tom_desktop_app.py`, line 856
- **Problem:** `_process_message()` calls `asyncio.run(self.agent.execute_task(text))` from a background thread. `asyncio.run()` always creates a **new** event loop. When the thread exits, that event loop is destroyed. On subsequent async calls (e.g., during feedback, rewards, or next command), the agent finds a closed loop and crashes with `"Event loop is closed"`.
- **Evidence in logs:**
  - `safety_log.txt` line 126: `ERROR: [FAILURE] | Target: can u open chrome | Note: Event loop is closed`
  - `lifetime_chat.json` line 56, 85, 105: Multiple occurrences
- **Impact:** The desktop UI will randomly crash after the first task completes. Reward/penalty feedback, scheduled tasks, and any follow-up command all fail.
- **Fix:** Use a shared event loop in the main thread, or use `asyncio.run_coroutine_threadsafe()` to schedule coroutines on a persistent event loop instead of creating new ones.

---

### 3. Agent Builder F-String Broken — `{name}` Not Interpolated

- **File:** `tools/agent_builder.py`, line 18
- **Problem:** The string `f"""""""""# Auto-generated agent: {name}` contains 9 consecutive double quotes after `f`. Python parses this as `f"""` (open f-string) + `"""` (close empty f-string) + `"""` (open regular string). The `{name}` is inside the regular triple-quoted string, NOT inside the f-string, so it is rendered literally as `{name}`.
- **Verified:** Scaffolded agent `main.py` contained literal text `# Auto-generated agent: {name}` instead of the actual name.
- **Impact:** Every agent created via `build_agent` command will have broken `main.py` files with un-interpolated template variables.
- **Fix:** Change to a properly constructed f-string: `f'''# Auto-generated agent: {name}\n...'''` or use `.format()`.

---

### 4. `search()` Method Passes Non-Existent Parameter

- **File:** `tools/browser_tools.py`, line 274
- **Problem:** `await self.click_element("textarea[jsaction='click']", timeout=3000)` passes `timeout=3000` as a keyword argument to `click_element()`.
- **Root Cause:** The `click_element()` method at line 189 has signature `async def click_element(self, selector: str)` — it only accepts `selector`, not `timeout`.
- **Impact:** Calling `search()` will raise `TypeError: click_element() got an unexpected keyword argument 'timeout'`.
- **Fix:** Remove the `timeout` argument, or add it to the `click_element()` method signature.

---

### 5. Email OAuth — Second `except` Block is Dead Code

- **File:** `tools/email_tools.py`, lines 165–183
- **Problem:** Both `except` clauses catch `Exception`. In Python, when multiple `except` blocks catch the same type, only the **first** one is ever executed. The second `except Exception` at line 179 is unreachable.
- **Impact:** OAuth errors that don't match the "access_denied" / "403" check in the first handler will **not** produce an error response — they'll silently fall through and likely hit an `UnboundLocalError` for `credentials` downstream.
- **Fix:** Merge both `except` blocks into one with proper conditional logic.

---

### 6. Safety Guard `is_action_safe()` is Effectively Useless

- **File:** `agent.py`, line 318 (`safety_check = await self.safety.is_action_safe(command)`)
- **File:** `safety/guards.py`, lines 42–67
- **Problem:** The full user command string (e.g., "delete all files") is passed as `action_name`. The `blocked_actions` dict checks **exact matches** against keys like `"delete_files"`, `"send_emails_without_approval"`, etc. Since `"delete all files" != "delete_files"`, the safety check **always** returns `safe=True`.
- **Impact:** The entire safety system does not work. Harmful commands are never blocked by this check.
- **Fix:** Use keyword detection (e.g., check if any blocked term appears as a substring of the command) rather than exact matching.

---

### 7. `execute_email_send` Route Handler Not Implemented

- **File:** `agent.py`, `execute_task()` method, lines 355–390
- **File:** `tools/command_router.py`, lines 76–83
- **Problem:** The command router routes "send email" / "send the email" to handler `"execute_email_send"`, but `agent.py:execute_task()` has **no branch** for `route.handler == "execute_email_send"`. The request silently falls through to `generate_chat_response()`.
- **Impact:** Sending emails always results in a chat reply instead of actual email dispatch.
- **Fix:** Add a handler branch: `elif route.handler == "execute_email_send": result = await self.execute_email_task(command)`.

---

### 8. `_build_memory_context()` May Return Truncated Content Mid-String

- **File:** `tools/chat_memory.py`, lines 65–88
- **Problem:** Line 87: `context = context[-max_chars:]` truncates from the **end** rather than the beginning when exceeding `max_chars`. This cuts off the **oldest** context, but due to the negative slice, it starts from a character offset that may split a word or sentence.
- **Impact:** The LLM prompt may contain broken/partial text fragments, confusing the model.
- **Fix:** Use `context[:max_chars]` to truncate from the beginning, or `context[-max_chars:]` only if appending newest content at the end is intentional but guaranteed not to split mid-sentence.

---

## 🟠 HIGH — Functional Deficiencies

### 9. Missing Dependencies in `requirements.txt`

| Dependency | Where Used | Status |
|---|---|---|
| `langchain-core` | `agent.py:6` — `from langchain_core.prompts import ChatPromptTemplate` | ❌ MISSING |
| `apscheduler` | `tools/scheduler.py:11` — `from apscheduler.schedulers.background import BackgroundScheduler` | ❌ MISSING |
| `reportlab` | `tools/pdf_tools.py:9` — `from reportlab.lib.pagesizes import letter, A4` | ❌ MISSING |
| `google-auth` | Already present | ✅ OK |
| `google-auth-oauthlib` | Already present | ✅ OK |
| `google-api-python-client` | May be needed for Gmail API | ⚠️ NOT LISTED |

**Impact:** Installing from `requirements.txt` alone will NOT install all required packages. The agent will crash on import with `ModuleNotFoundError`.

---

### 10. `tools/init.py` Named Incorrectly

- **File:** `tools/init.py` (exists) vs `tools/__init__.py` (missing)
- **Problem:** The file is named `init.py` instead of `__init__.py` (with double underscores). While Python 3.3+ supports namespace packages without `__init__.py`, the file content explicitly has imports and `__all__`, indicating it was intended as a proper package init.
- **Impact:** Imports like `from tools import ...` work due to namespace packages, but `from tools import OSTools` using the `__all__` list will **not** work because `__init__.py` is not the standard name.
- **Fix:** Rename `tools/init.py` to `tools/__init__.py`.

---

### 11. `create_html_file()` Has a Logic Bug

- **File:** `tools/file_tools.py`, line 22
- **Code:** `filename if not filename.endswith(".html") else filename`
- **Problem:** Both branches of the conditional return `filename` unchanged. The `.html` extension is never appended regardless of input.
- **Impact:** Files created without `.html` extension may not open correctly in browsers.
- **Fix:** `filename if filename.endswith(".html") else filename + ".html"`

---

### 12. `execute_website_creation()` Always Creates "bakery_store"

- **File:** `agent.py`, line 522
- **Code:** `result = await self.file_tools.create_website({"name": "bakery_store"})`
- **Problem:** The website name is **hardcoded** to `"bakery_store"` regardless of what the user requested. If the user asks "create a website for my photography business", the output is still `src/bakery_site/`.
- **Impact:** Creates confusing output where directory name doesn't match user request.
- **Fix:** Use the command text (or the route metadata) to infer the actual project name.

---

### 13. `execute_file_command()` Regex Has Format Issues

- **File:** `agent.py`, lines 778–782
- **Problem:** The regex patterns have formatting quirks:
  - Line 778: `r'(?:create\s+|write\s+|make\s+)file?\s+for?\s+...'` — the `?` after `file` and `for` means the `e` is optional, unintentionally matching "fil" or "fo".
  - Only `.py`, `.html`, `.css` are handled — `.js`, `.tsx`, `.json`, `.md`, and other common file types are silently rejected.
- **Fix:** Fix the regex quantifiers and extend supported file extensions.

---

### 14. Desktop App Voice Mode Activates Synchronous Setup in UI Thread

- **File:** `tom_desktop_app.py`, lines 627–628
- **Problem:** `self.voice._setup_input()` and `self.voice._setup_output()` are called directly in the Tkinter main thread. These methods may block (especially `pyttsx3.init()` which scans system audio drivers).
- **Impact:** UI freezes for several seconds when enabling voice mode.
- **Fix:** Offload setup to a background thread.

---

### 15. `tom_desktop_app.spec` Missing Hidden Imports

- **File:** `tom_desktop_app.spec`, line 9
- **Problem:** Only `speech_recognition` is listed in `hiddenimports`. Missing entries:
  - `pytesseract`
  - `PIL` / `Pillow`
  - `pyttsx3`
  - `apscheduler`
  - `reportlab`
  - `langchain_ollama`
  - `playwright`
- **Impact:** PyInstaller builds will silently fail at runtime with `ModuleNotFoundError`.
- **Fix:** Add all missing hidden imports.

---

## 🟡 MEDIUM — Security & Configuration Issues

### 16. Instagram Credentials Exposed in Plain Text

- **File:** `memories/session_experiences.json`, entries with `id: 1777743256375`
- **Problem:** Instagram username `_rajeshponnapureddy_` and password `Rajesh@#2004` are stored in plain text in a JSON file that is part of version control.
- **Impact:** If this repository is pushed to a public remote, credentials are exposed. Any process that can read this file has access to the Instagram account.
- **Fix:** Never store credentials in memory files. Use environment variables or a secrets manager.

---

### 17. Email Password Stored in `.env` File

- **File:** `C:\Users\saimo\tom_autonomous_agent\.env`, line 95
- **Code:** `EMAIL_PASSWORD=lbqyctrwvjerotew`
- **Problem:** While the comments claim this is "deprecated", an apparent Gmail app password is still stored in plaintext in the `.env` file.
- **Impact:** If `.env` is committed or exposed, the email account is compromised.
- **Fix:** Remove the `EMAIL_PASSWORD` line entirely — OAuth2 is used instead.

---

### 18. Hardcoded Path to System Prompt File

- **File:** `agent.py`, line 55
- **Code:** `self.system_prompt_file = os.path.join(os.getcwd(), "config/system_prompt.txt")`
- **Problem:** Uses `os.getcwd()` which depends on the current working directory at runtime. If the app is launched from a different directory (e.g., via shortcut, scheduled task, or from a subfolder), the path will be wrong.
- **Fix:** Use `os.path.dirname(__file__)` or `Path(__file__).parent` to derive the path relative to the script location.

---

### 19. Voice Tools Use Google's Online Speech API with No Fallback

- **File:** `tools/voice_tools.py`, line 154
- **Code:** `text = self._recognizer.recognize_google(audio)`
- **Problem:** Uses Google's free web speech API which requires an active internet connection. There is no fallback to offline recognition (e.g., `recognize_sphinx` for CMU Sphinx or `recognize_whisper` for local Whisper).
- **Impact:** Voice input silently fails when offline.
- **Fix:** Add offline fallback recognition backend.

---

### 20. Memory Files Grow Unboundedly

- **Files:** `memories/lifetime_chat.json`, `memories/session_experiences.json`
- **Problem:** Every chat turn and every experience is appended indefinitely with no cleanup or rotation mechanism.
- **Impact:** Over time, memory files can grow to gigabytes, causing slow loads, high memory usage, and large LLM context windows.
- **Fix:** Implement a maximum file size or entry count with oldest-entry eviction.

---

### 21. Two Separate `SafetyGuards` Classes Exist

- **Files:** `safety/guards.py` and `safety_guards.py` (root level)
- **Problem:** Both files define a class named `SafetyGuards` with different interfaces:
  - `safety/guards.py`: `log_action(self, action, target, status, message)` — used by `agent.py`
  - `safety_guards.py`: `log_action(self, action, status, message)` — legacy, unused
- **Impact:** Import confusion. If someone does `from safety_guards import SafetyGuards` they get the legacy class with a different `log_action` signature.
- **Fix:** Remove the legacy `safety_guards.py` from the root.

---

### 22. Instagram Agent Lacks Login Flow

- **File:** `agents/instagram_ai_news_agent/main.py`, line 89–104
- **Problem:** `open_instagram()` just navigates to `https://www.instagram.com` without handling login. It assumes the Chrome profile is already authenticated.
- **Impact:** If the Chrome profile is not logged into Instagram, the workflow will capture an empty/login page instead of the feed.
- **Fix:** Add login detection and credential-based authentication flow.

---

### 23. Instagram Agent Captures Entire Page as Single Post

- **File:** `agents/instagram_ai_news_agent/main.py`, lines 106–142
- **Problem:** `extract_post_content()` calls `get_page_content()` which returns ALL visible text on the page. On each scroll, this same content is captured again with slight variations due to new content loading. There's no post-level DOM parsing to extract individual posts.
- **Impact:** The "posts" list contains near-duplicates of the same page content, making AI classification unreliable.
- **Fix:** Parse individual `<article>` elements from the DOM to extract separate posts.

---

## 🔵 LOW — Minor Issues

| # | Issue | File | Details |
|---|-------|------|---------|
| 24 | `chromedriver.exe` in root but unused | Root directory | Selenium/ChromeDriver not used — Playwright is used instead. Dead file (~15 MB). |
| 25 | `.env` has unused `OPENAI_API_KEY` placeholder | `.env:163` | `OPENAI_API_KEY=YOUR_API_IF_NEEDED` — placeholder value, not actually used in code. |
| 26 | `dotenv.load_dotenv()` called twice | `main.py:7` and `email_tools.py:18` | Harmless double-load, but `email_tools.py` loads it at module import time which may be too early. |
| 27 | `safe_print` defined in 3 places | `main.py:18`, `agent.py:26`, `email_tools.py:21` | Duplicated utility function — should be in a shared module. |
| 28 | `agent.py:__del__` is empty | `agent.py:1070–1072` | Destructor does nothing — resources may not be cleaned up on garbage collection. |
| 29 | `browser_tools.py:__del__` is empty | `browser_tools.py:308–310` | Same — no cleanup on garbage collection. |
| 30 | Activity counts array index gap | `tom_desktop_app.py:714` | `usable_height = bar_height - ((len(items) - 1) * gap)` — dividing by `len(items)` may produce fractional pixel heights for bars. |

---

## Summary Statistics

| Severity | Count | Key Impact Areas |
|----------|-------|------------------|
| 🔴 Critical | 8 | App crashes, security bypass, broken agent builder, non-functional safety |
| 🟠 High | 6 | Missing deps, file creation bugs, missing features, broken builds |
| 🟡 Medium | 8 | Exposed credentials, infinite growth, no offline fallback, routing gaps |
| 🔵 Low | 7 | Code hygiene, dead files, minor visual glitches |
| **Total** | **29** | |

---

## Fixes Applied (May 14, 2026)

| # | Issue | Status | File Changed |
|---|-------|--------|-------------|
| 1 | `OSTools.__init__()` double definition | ✅ FIXED | `tools/os_tools.py` — removed duplicate `__init__` |
| 2 | Event loop crash ("Event loop is closed") | ✅ FIXED | `tom_desktop_app.py` — persistent event loop via `asyncio.run_coroutine_threadsafe()` |
| 3 | `agent_builder.py` f-string broken | ✅ FIXED | `tools/agent_builder.py` — proper f-string with escaped inner braces |
| 4 | `search()` passes non-existent `timeout` | ✅ FIXED | `tools/browser_tools.py` — removed `timeout=3000` argument |
| 5 | Email OAuth dead code (second except) | ✅ FIXED | `tools/email_tools.py` — merged into single except block |
| 6 | `is_action_safe()` exact match bug | ✅ FIXED | `safety/guards.py` — keyword substring matching with `blocked_keywords` mapping |
| 7 | `execute_email_send` handler missing | ✅ FIXED | `agent.py` — added `execute_email_send_flow()` method and route handler |
| 8 | `_build_memory_context()` truncation | ✅ FIXED | `tools/chat_memory.py` — added newline-aware truncation |
| 9 | `create_html_file()` .html extension bug | ✅ FIXED | `tools/file_tools.py` — fixed inverted logic |
| 10 | Missing deps in `requirements.txt` | ✅ FIXED | `requirements.txt` — added `langchain-core`, `apscheduler`, `reportlab` |
| 11 | `tools/init.py` wrong name | ✅ FIXED | Renamed to `tools/__init__.py` |
| 12 | Website creation hardcoded name | ✅ FIXED | `agent.py` — dynamic project name extraction from command |
| 13 | File command regex issues | ✅ FIXED | `agent.py` — fixed regex, added more file extensions |
| 14 | Hardcoded system prompt path | ✅ FIXED | `agent.py` — uses `__file__`-relative path |
| 15 | Memory file unbounded growth | ✅ FIXED | `tools/chat_memory.py` + `tools/learning.py` — max entries limit (500) |
| 16 | Tkinter tuple padding crash | ✅ FIXED | `tom_desktop_app.py` — changed tuple `pady=(a,b)` to single values |

## Recommended Immediate Fixes (Priority Order)
