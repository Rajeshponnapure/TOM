# TOM Autonomous Agent — Functional Error Report
**Date:** 2026-05-25  
**Scope:** Full codebase audit of `agent.py`, `tools/`, `safety/guards.py`

---

## Summary

10 confirmed functional bugs were found that cause incorrect behaviour, silent failures, or crashes at runtime. They are ordered from most to least critical.

---

## BUG 1 — `approval_gate` handler is never dispatched after user approves (Silent Action Drop)
**File:** `agent.py` → `execute_task()` | **Severity: CRITICAL**

The `CommandRouter` returns `handler="approval_gate"` for sensitive commands such as `"delete file"`, `"share something"`, or `"post to twitter"`. The approval prompt is correctly shown and the user approves — but then the `execute_task` elif chain has **no branch for `"approval_gate"`**, so execution falls through to `elif not self.is_action_request(command)`.

Because `"delete"`, `"share"`, `"post to"` are not in `action_keywords`, `is_action_request()` returns `False` → TOM calls `generate_chat_response()` and just talks back. **The approved action is silently dropped and never executed.**

**Broken code (agent.py ~line 674):**
```python
# No elif for route.handler == "approval_gate" exists anywhere in the chain
elif route.handler in ("execute_data_analysis", ...):
    ...
elif not self.is_action_request(command):     # ← catches approved "delete" commands here
    result = await self.generate_chat_response(command)  # ← just chats instead of acting
```

**Fix:** Add an `approval_gate` branch that inspects the `route.intent` and dispatches the correct executor:
```python
elif route.handler == "approval_gate":
    intent = route.intent
    if intent in ("delete_or_remove",):
        result = await self.execute_file_command(command)
    elif intent == "send_email":
        result = await self.execute_email_send_flow(command)
    else:
        result = await self.generate_chat_response(command)
```

---

## BUG 2 — `execute_email_task` sends an empty, un-generated email body (Email Drafts Are Useless)
**File:** `agent.py` → `execute_email_task()` | **Severity: HIGH**

When a user says `"write email to boss@example.com about the project update"`, TOM calls:
```python
draft = await self.email_tools.draft_email(email_recipient, command[:100], "")
```
- **Subject** is the raw command string truncated to 100 chars (e.g., `"write email to boss@example.com about the pr..."`)
- **Body** is an empty string `""`

The LLM is never invoked to actually write the email. The draft is useless.

**Fix:** Use the LLM to generate a proper subject and body before calling `draft_email`:
```python
# Call LLM to write subject + body from the user's command
prompt = ChatPromptTemplate.from_messages([...])
response = await self._invoke_llm(chain, {"command": command}, "write_email")
# Parse subject and body from response, then call draft_email
```

---

## BUG 3 — `execute_email_send_flow` always sends a generic hardcoded message (Never Uses Actual Content)
**File:** `agent.py` → `execute_email_send_flow()` | **Severity: HIGH**

When the user says `"send email to boss@company.com"`, the function sends:
```python
subject = "Message from TOM"
body = f"Sent via TOM Autonomous Agent per request: {command[:200]}"
```
Every email TOM sends has the same subject and a body that is literally just the user's command pasted in. It never uses any previously drafted content.

**Fix:** Either retrieve the last drafted email from memory/state, or invoke the LLM to compose proper email content from the command before sending.

---

## BUG 4 — `_get_html_template` generates a broken CSS link (Wrong `href` Attribute)
**File:** `agent.py` → `_get_html_template()` | **Severity: HIGH**

```python
<link rel="stylesheet" href="{filename}.css">
```
When `filename` is `"index.html"`, this renders as:
```html
<link rel="stylesheet" href="index.html.css">
```
The `.html` extension is not stripped, so the CSS file is never found by the browser. Every HTML file created by TOM will have no styles applied.

**Fix:**
```python
base_name = filename.replace('.html', '')
# Then use:
<link rel="stylesheet" href="{base_name}.css">
```

---

## BUG 5 — `css_basic` template is invalid CSS (Missing Selector)
**File:** `tools/file_tools.py` → `FileTools.__init__` | **Severity: HIGH**

```python
"css_basic": "{\n  margin: 0;\n  padding: 0;\n  font-family: Arial, sans-serif;\n}"
```
This is a CSS rule block with **no selector**. It is invalid CSS and browsers will ignore it entirely. Every website created using the fallback CSS will have zero styling applied.

**Fix:**
```python
"css_basic": "* {\n  box-sizing: border-box;\n}\n\nbody {\n  margin: 0;\n  padding: 0;\n  font-family: Arial, sans-serif;\n}"
```

---

## BUG 6 — `execute_file_command` only handles `.py` and `.html` — silently errors on all other matched types
**File:** `agent.py` → `execute_file_command()` | **Severity: MEDIUM**

The regex patterns match `.css`, `.js`, `.json`, `.md`, and `.txt` files — but the if/elif only provides templates for `.py` and `.html`. Everything else hits:
```python
else:
    return {"status": "error", "message": f"Unknown file type for {filename}"}
```
So `"create file for style.css"` matches the regex, extracts `"style.css"`, then immediately returns an error. The matched file types are never created.

**Fix:** Add template branches for each supported extension:
```python
elif filename.lower().endswith('.css'):
    content = "/* styles */\nbody {\n  margin: 0;\n  font-family: Arial, sans-serif;\n}"
elif filename.lower().endswith('.js'):
    content = "// JavaScript\nconsole.log('Hello from TOM');"
elif filename.lower().endswith(('.md', '.txt', '.json')):
    content = ""  # empty file or minimal scaffold
```

---

## BUG 7 — `execute_read_file_command` regex won't match natural commands like `"show me login.py"`
**File:** `agent.py` → `execute_read_file_command()` | **Severity: MEDIUM**

The first regex pattern is:
```python
r'(?:read\s+|show me)\s+file?\s+(\.{3}|[a-zA-Z0-9._\-\s]+)'
```
This requires the word `"file"` between `"show me"` and the filename. So `"show me login.py"` does **not** match (no "file" word). `"\.{3}"` matches the literal string `"..."` which is useless as a file path.

The second pattern `r'([a-zA-Z0-9./\-_\.]+\.(py|html|css|txt|js))'` would catch it as a fallback — but only if the filename has no spaces. Commands like `"read file my login script.py"` would fail entirely.

**Fix:** Simplify the primary pattern:
```python
r'(?:read|show\s+me)\s+(?:file\s+)?([a-zA-Z0-9./\\\-_ ]+\.(?:py|html|css|txt|js|json|md))'
```

---

## BUG 8 — `schedule_instagram_reports` uses `asyncio.run()` inside a running event loop (RuntimeError)
**File:** `agent.py` → `schedule_instagram_reports()` / `run_instagram_task()` | **Severity: MEDIUM**

```python
def run_instagram_task():
    try:
        result = asyncio.run(self.execute_instagram_workflow())  # ← CRASH if loop is running
```
`asyncio.run()` raises `RuntimeError: This event loop is already running` when called from within an active asyncio event loop, which is always the case since TOM's main loop is `asyncio.run(main())`. This means scheduled Instagram tasks will **always crash** when triggered from within the app.

**Fix:** Use a separate thread with its own event loop:
```python
def run_instagram_task():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(self.execute_instagram_workflow())
    finally:
        loop.close()
```

---

## BUG 9 — `get_chrome_profiles` in `os_tools.py` has an unexpanded `%USERNAME%` variable (Wrong Path)
**File:** `tools/os_tools.py` → `get_chrome_profiles()` | **Severity: MEDIUM**

```python
chrome_base = r"C:\Users\%USERNAME%\AppData\Local\Google\Chrome\User Data"
```
The `%USERNAME%` environment variable is **never expanded** — the path is passed as a raw string to PowerShell which may or may not expand it depending on context. Additionally, the PowerShell command is split incorrectly into separate list arguments rather than a single command string, which will likely fail.

**Fix:**
```python
chrome_base = os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Local\Google\Chrome\User Data")
```

---

## BUG 10 — `execute_website_creation` may return an unbound `result` on creation failure
**File:** `agent.py` → `execute_website_creation()` | **Severity: LOW**

When `file_tools.create_website()` returns a failure dict (e.g. permissions error), the function reaches this logic:
```python
result = await self.file_tools.create_website(project_name, index_html, style_css)
if result["status"] == "success":
    return { ... }
# Falls through — 'result' is bound but the outer function still reaches:
return result   # Returns raw internal error dict, no user-friendly message
```
The raw dict from `FileTools` is returned with no explanation to the user.

**Fix:** Add a proper else branch:
```python
if result["status"] == "success":
    return {"status": "success", "message": f"Website '{project_name}' created.", "path": result["path"]}
else:
    return {"status": "error", "message": f"Website creation failed: {result.get('message', 'Unknown error')}"}
```

---

## Quick Reference Table

| # | File | Method | Issue | Severity |
|---|------|--------|-------|----------|
| 1 | `agent.py` | `execute_task` | `approval_gate` never dispatched — action silently dropped | **CRITICAL** |
| 2 | `agent.py` | `execute_email_task` | Email draft always has empty body and raw command as subject | **HIGH** |
| 3 | `agent.py` | `execute_email_send_flow` | Always sends hardcoded generic message, never real content | **HIGH** |
| 4 | `agent.py` | `_get_html_template` | CSS link href is `"index.html.css"` instead of `"index.css"` | **HIGH** |
| 5 | `tools/file_tools.py` | `FileTools.__init__` | `css_basic` template has no selector — invalid CSS | **HIGH** |
| 6 | `agent.py` | `execute_file_command` | Only `.py` and `.html` handled; `.css/.js/.json/.md/.txt` error out | **MEDIUM** |
| 7 | `agent.py` | `execute_read_file_command` | Regex requires word "file" in command; `"show me login.py"` fails | **MEDIUM** |
| 8 | `agent.py` | `schedule_instagram_reports` | `asyncio.run()` inside running loop → always crashes | **MEDIUM** |
| 9 | `tools/os_tools.py` | `get_chrome_profiles` | `%USERNAME%` not expanded → wrong Chrome profile path | **MEDIUM** |
| 10 | `agent.py` | `execute_website_creation` | Raw internal error dict returned to user on creation failure | **LOW** |
