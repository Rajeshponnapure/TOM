# TOM Production Architecture

This document defines the production target for TOM as a local, Windows-first personal automation platform that combines voice, text, browser automation, desktop control, OCR, document generation, approvals, memory, logging, and plugins.

## 1. System Architecture

### Layers

1. Voice Interface Module
   - Speech-to-text for wake word and conversational input.
   - Text-to-speech for spoken responses.
   - Fail-safe behavior: auto-disable voice features on hardware or dependency errors.

2. Text Chat Interface
   - Tkinter desktop UI for local use.
   - Optional FastAPI service for remote or future web UI integration.

3. Command Router
   - Routes natural language into browser, desktop, file, email, spreadsheet, presentation, and plugin actions.
   - Sends sensitive actions to approval.

4. Task Planner
   - Converts a request into an execution plan.
   - Used only when a command is ambiguous or multi-step.

5. Browser Automation Engine
  - Playwright for Chrome, Gmail, YouTube, Instagram, and web apps.
   - Profile-aware Chrome startup.

6. Desktop Automation Engine
   - PyAutoGUI and pywinauto for Windows application control.
   - Office automation via COM when available.

7. OCR and Screen Understanding Module
   - Tesseract OCR and OpenCV for screen capture, text extraction, and UI recognition.

8. LLM Reasoning Module
   - Ollama-backed local model for planning, extraction, summarization, and drafting.
   - Must always run with timeouts and fallback behavior.

9. File Generation Module
   - Word, Excel, PowerPoint, PDF, and report generation.

10. Notification and Approval Module
    - Human-in-the-loop confirmations for sending, publishing, deleting, and other sensitive actions.

11. Memory and Preferences Module
    - Persistent user preferences, session experiences, and action history.

12. Logging and Audit Module
    - Structured audit trail for approvals, success, partial success, failures, and retries.

13. Plugin System
    - New automations live in `agents/<name>/` or `plugins/<name>/`.
    - TOM discovers plugins, reads metadata, and can load them later.

## 2. Recommended Folder Structure

```text
tom_autonomous_agent/
  agent.py
  main.py
  tom_desktop_app.py
  ARCHITECTURE.md
  README.md
  SETUP.md
  requirements.txt
  config/
    system_prompt.txt
  memories/
    lifetime_chat.json
    session_experiences.json
  safety/
    guards.py
  tools/
    approval.py
    browser_tools.py
    chrome_profiles.py
    command_router.py
    email_tools.py
    file_tools.py
    learning.py
    os_tools.py
    plugin_manager.py
    voice_tools.py
  agents/
    <generated plugins>/
  plugins/
    <optional packaged plugins>/
  resources/
    icons, screenshots, templates
  tom_logs/
    safety_log.txt
```

## 3. Dependency List

### Core

- Python 3.11
- `python-dotenv`
- `ollama`
- `langchain-ollama`
- `chromadb`
- `sentence-transformers`
- `playwright`
- `pyttsx3`
- `SpeechRecognition`
- `pyaudio`
- `google-auth`
- `google-auth-oauthlib`
- `imapclient`
- `openpyxl`
- `pandas`
- `Pillow`

### Recommended production extras

- `fastapi`
- `uvicorn`
- `pydantic`
- `pyautogui`
- `pywinauto`
- `opencv-python`
- `pytesseract`
- `python-pptx`
- `reportlab`
- `pywin32`
- `apscheduler`
- `webrtcvad` or wake-word library of choice

## 4. Environment Configuration

Suggested `.env` values:

- `OLLAMA_BASE_URL=http://localhost:11434`
- `OLLAMA_MODEL=llama3.2:latest`
- `OLLAMA_TIMEOUT_SECONDS=45`
- `TASK_TIMEOUT_SECONDS=75`
- `VOICE_INPUT_ENABLED=true|false`
- `VOICE_OUTPUT_ENABLED=true|false`
- `VOICE_SPEAK_TIMEOUT_SECONDS=8`
- `FEEDBACK_MAX_LOOPS=5`
- `CHROME_PROFILE_PATH=` optional override
- `EMAIL_ADDRESS=` for Gmail OAuth2 or SMTP
- `GMAIL_CREDENTIALS_FILE=` path to OAuth client file
- `GMAIL_TOKEN_FILE=` token cache path
- `IMAP_HOST=` optional custom IMAP host
- `SMTP_SERVER=` optional custom SMTP host

## 5. Database Schema

SQLite is sufficient for a single-user laptop deployment.

```sql
CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  mode TEXT NOT NULL,
  device_name TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  command TEXT NOT NULL,
  route TEXT,
  status TEXT NOT NULL,
  outcome TEXT,
  error TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT,
  FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS approvals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER,
  action TEXT NOT NULL,
  approved INTEGER NOT NULL,
  approved_by TEXT,
  approved_at TEXT,
  details TEXT,
  FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  namespace TEXT NOT NULL,
  key TEXT NOT NULL,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(namespace, key)
);
```

## 6. Core Python Modules

- `agent.py`: high-level orchestration, safety checks, planning, execution, logging.
- `tools/voice_tools.py`: voice I/O with bounded timeouts.
- `tools/command_router.py`: intent classification and metadata extraction.
- `tools/approval.py`: human confirmation gate.
- `tools/browser_tools.py`: Playwright lifecycle and browser actions.
- `tools/chrome_profiles.py`: Chrome profile discovery and launch.
- `tools/plugin_manager.py`: plugin discovery and loading.
- `tools/learning.py`: experience store and score tracking.
- `tools/email_tools.py`: Gmail/IMAP draft/send paths.
- `tools/file_tools.py`: local file creation and reading.
- `safety/guards.py`: allow/deny rules and audit logging.

## 7. Plugin Architecture

Plugins should expose metadata and an async entrypoint.

Example layout:

```text
agents/
  instagram_news_to_email_agent/
    main.py
    README.md
    config.example.env
    plugin.json
```

Recommended `plugin.json`:

```json
{
  "name": "instagram_news_to_email_agent",
  "version": "1.0.0",
  "description": "Collect AI news from Instagram and prepare a report",
  "entrypoint": "main.py",
  "capabilities": ["browser", "ocr", "pdf", "email"]
}
```

## 8. GUI and Chat Design

- Desktop-first Tkinter shell for reliability on Windows.
- Left-to-right workflow: input, status, response, approval, history.
- Approval modal should always stay on top and require explicit confirmation for sensitive actions.
- A future FastAPI backend can expose the same router, memory, and task APIs.

## 9. Voice Pipeline

1. Wake word or push-to-talk.
2. Capture microphone audio.
3. Whisper or SpeechRecognition transcription.
4. Route command.
5. Plan or execute.
6. Render text response.
7. Speak response with TTS.

Guardrails:

- Disable voice input if the microphone or driver is missing.
- Time out TTS if speech generation hangs.
- Keep text mode always available.

## 10. Example Workflows

### Chrome profile launch

1. User says: "Open Chrome profile Rajesh and go to Gmail."
2. Router extracts `profile_query=Rajesh`.
3. Chrome profile manager finds the matching profile.
4. Browser launches with that profile and opens Gmail.

### Gmail triage

1. User asks TOM to read today’s mail.
2. Browser or IMAP layer fetches messages.
3. LLM classifies messages into important, reply-needed, informational, spam.
4. TOM drafts replies and waits for approval before sending.

### Instagram AI news report

1. Open Instagram in Chrome.
2. Scroll feed and capture candidate posts.
3. OCR and vision heuristics extract AI-related items.
4. Summarize, rank, and export to PDF.
5. Open email and send only after confirmation.

## 11. Testing Strategy

- Smoke tests for imports, UI startup, voice disabled mode, file creation, and routing.
- Unit tests for command routing, approval prompts, profile discovery, and memory normalization.
- Integration tests for browser automation and Office workflows using mock or test profiles.
- Manual acceptance tests for Chrome, Gmail, Instagram, and email delivery flows.

## 12. Packaging and Deployment

- Development mode: run from `venv`.
- Desktop app: PyInstaller `--noconsole --onefile` build.
- Distribution: Inno Setup installer for Windows users.
- Keep resource files in `resources/` and bundled with the exe.

## 13. Security and Privacy

- Require explicit approval before sending email, sending messages, deleting files, or publishing content.
- Never store raw passwords in code or logs.
- Prefer OAuth or browser sessions over hard-coded credentials.
- Log all sensitive actions with timestamps.
- Treat browser profile access as privileged local access.

## 14. Roadmap

1. Finish task router and approval UI integration.
2. Add OCR-based screen understanding for desktop apps.
3. Add Excel, PowerPoint, and PDF generation pipelines.
4. Add Power BI automation hooks.
5. Build a persistent SQLite backend for memory and audit logs.
6. Add plugin metadata and install/update flows.
7. Add FastAPI service for remote control and monitoring.
8. Add regression tests for each supported app path.
