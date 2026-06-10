# TOM Autonomous Agent — Capabilities & Functionality Report

**Generated:** May 14, 2026  
**Version:** Full codebase analysis

---

## Overview

TOM is an autonomous desktop assistant that runs locally using Ollama (offline LLM) with a Tkinter-based desktop UI. It can automate applications, manage email, browse the web, create files/websites, scaffold sub-agents, and run scheduled Instagram monitoring workflows.

---

## 1. Core Capabilities

### 1.1 Conversational AI Chat
- **How it works:** Uses `Ollama` (local LLM) via `langchain-ollama`. User input is routed through `ChatOllama` with a system prompt loaded from `config/system_prompt.txt`.
- **Files:** `agent.py` → `generate_chat_response()`, `agent.py` → `plan_task()`
- **Memory:** Persistent chat history stored in `memories/lifetime_chat.json`. Context window built from recent + keyword-relevant messages.
- **Commands:** Any non-action text (greetings, questions, chit-chat)

### 1.2 Open Applications
- **How it works:** Matches keywords ("open chrome", "launch word") and runs the Windows executable via `subprocess.Popen()`.
- **Supported Apps:**
  - Google Chrome (including profile-specific launching)
  - Microsoft Word
  - Microsoft Excel
  - Microsoft PowerPoint
  - Microsoft Edge
  - Notepad
  - Any Windows app via system `start` command fallback
- **Chrome Profiles:** Detects Chrome profiles from `Local State`, launches with `--profile-directory` flag.
- **Files:** `agent.py:467` → `execute_open_command()`, `tools/os_tools.py`, `tools/chrome_profiles.py`

### 1.3 File Operations
- **Create files:** Write `.py`, `.html`, `.css`, `.js`, `.json`, `.md`, `.txt` files with appropriate templates
- **Read files:** Read any text file and display content
- **Create websites:** Generate multi-page website structure (HTML + CSS) with preview capability
- **Safety:** Path validation prevents writing to system folders (`C:\Windows\`, `/sys/`, etc.)
- **Files:** `agent.py:770` → `execute_file_command()`, `agent.py:824` → `execute_read_file_command()`, `tools/file_tools.py`

### 1.4 Email Management
- **Gmail OAuth2:** Connects via OAuth2 credentials file (`google-credentials.json`). Auto-refreshes tokens and saves to `google-credentials_token.json`.
- **IMAP/SMTP Fallback:** Supports generic IMAP for other providers (Outlook, etc.)
- **Operations:**
  - Draft emails for review (never sends without approval)
  - Send emails with user confirmation
  - Auto-reply to low-priority emails (configurable via `EMAIL_AUTO_REPLY_ENABLED`)
  - Inbox triage: classify emails as important/low-priority, flag urgent items
  - Fetch and summarize inbox messages
- **Files:** `tools/email_tools.py`, `agent.py:543` → `execute_email_task()`, `agent.py:662` → `execute_email_inbox_workflow()`

### 1.5 Browser Automation (Playwright)
- **How it works:** Uses Playwright to automate Chromium browser with persistent Chrome profiles.
- **Operations:**
  - Open URLs
  - Type text into fields
  - Click elements by CSS selector
  - Extract page content and visible text
  - Execute JavaScript in page context
  - Screenshot + OCR (Tesseract) for text extraction from images/video frames
  - Google search
- **Files:** `tools/browser_tools.py`

### 1.6 Screen Reading (OCR)
- **How it works:** Captures the current desktop screen using `pyautogui`, extracts text via `pytesseract` (Tesseract OCR engine).
- **Output:** Text blocks with confidence scores and bounding box coordinates.
- **Files:** `tools/screen_tools.py`

### 1.7 Voice Input/Output
- **Input:** `SpeechRecognition` + `pyaudio` — listens via microphone, transcribes using Google's free speech API.
- **Output:** `pyttsx3` — text-to-speech with configurable rate (50-300 wpm) and volume.
- **Controls:** Runtime toggle commands: "voice on/off", "speak on/off"
- **Files:** `tools/voice_tools.py`

### 1.8 Code Fixing & Debugging
- **How it works:** Routes "fix code", "debug code", "repair code" commands to an LLM prompt focused on debugging.
- **Files:** `agent.py:227` → `execute_code_help()`

### 1.9 Agent Building (Scaffolding)
- **How it works:** Creates sub-agent directory structure under `agents/<name>/` with:
  - `main.py` — entrypoint with `run()` function
  - `README.md` — permissions and setup instructions
  - `requirements.txt` — dependencies
  - `config.example.env` + `.env` — configuration template
- **Inferred capabilities:** Detects Instagram, email, tech news, and general task capabilities from command text.
- **Files:** `agent.py:453` → `build_agent()`, `tools/agent_builder.py`

### 1.10 Learning & Feedback
- **Experience tracking:** Every action is logged as an "experience" with outcome (success/failure/incomplete) in `memories/session_experiences.json`.
- **Reward/Penalty:** Users can reward (positive) or penalize (negative) experiences. Penalties trigger automatic response revision.
- **Skill summary:** Aggregates experience data into a skills report with usage counts and weighted scores.
- **Files:** `tools/learning.py`, `agent.py:436` → `give_reward()`

### 1.11 Scheduling
- **How it works:** Uses `APScheduler` (or lightweight fallback) to run recurring tasks.
- **Current use:** Schedule Instagram AI news report generation every N hours.
- **Files:** `tools/scheduler.py`

---

## 2. Agent-Specific Workflows

### 2.1 Instagram AI News Agent (`agents/instagram_ai_news_agent/`)
- **Purpose:** Automated Instagram feed monitoring for AI/tech news
- **Workflow:**
  1. Initialize Playwright browser with Chrome profile
  2. Open Instagram and scroll the feed
  3. Extract post content (text, visual text, author, URL)
  4. Filter posts for AI-related keywords (40+ keywords including OpenAI, Claude, Gemini, etc.)
  5. Classify importance (1-5 scale based on keyword density)
  6. Generate a professional PDF report with `reportlab`
  7. Email the PDF report via Gmail OAuth2
  8. Supports scheduling every N hours
- **Keywords tracked:** AI, machine learning, OpenAI, GPT, Claude, Anthropic, Meta AI, Gemini, Mistral, Stable Diffusion, etc.
- **Files:** `agents/instagram_ai_news_agent/main.py`, `tools/pdf_tools.py`

### 2.2 Email Agent (`agents/email_agent/`)
- **Purpose:** Email triage and automated reply management
- **Files:** `agents/email_agent/main.py`

---

## 3. Desktop Application (Tkinter UI)

- **File:** `tom_desktop_app.py`
- **Features:**
  - Dashboard view with activity metrics (messages, voice, email, Instagram counts)
  - Chart view with live usage bar charts
  - Chat view with scrollable conversation, voice input button, and terminal
  - Agent selector (Core TOM, Email Agent, Instagram Agent) with context-aware prefix prompts
  - Quick-action buttons for voice mode and agent execution
  - Activity feed and recent events tracking
  - Feedback system: Reward (+1) and Penalty (-1) + Revise buttons
  - Auto-start: Checks/launches Ollama server on startup
  - Voice mode toggle with auto-transcribe and send
- **Entry points:**
  - `launch_tom_ui.bat` — Console launcher (uses `python.exe`)
  - `launch_tom_ui.vbs` — Silent launcher (uses `pythonw.exe`, no console window)
  - `tom_desktop_app.spec` — PyInstaller build spec for standalone `.exe`

---

## 4. Safety & Security System

- **File:** `safety/guards.py`
- **Features:**
  - Keyword-based action blocking (delete, remove, send email without approval, install software, cryptocurrency access)
  - File path validation — prevents writing to system directories
  - Email validation — regex-based format checking
  - URL validation — basic URL format verification
  - Action logging to `tom_logs/safety_log.txt` with timestamps
  - User confirmation prompts for sensitive actions

---

## 5. Plugin System

- **File:** `tools/plugin_manager.py`
- **Discovery:** Scans `agents/` and `plugins/` directories for subdirectories with `main.py`, `plugin.json`, or `README.md`
- **Loading:** Dynamic module loading via `importlib`

---

## 6. Environment Configuration (`.env`)

| Variable | Purpose | Default |
|---|---|---|
| `OLLAMA_BASE_URL` | Ollama API endpoint | `http://localhost:11434` |
| `OLLAMA_MODEL` | LLM model name | `llama3.2:latest` |
| `OLLAMA_TIMEOUT_SECONDS` | LLM request timeout | `45` |
| `TASK_TIMEOUT_SECONDS` | Max task duration | `75` |
| `VOICE_INPUT_ENABLED` | Enable microphone input | `true` |
| `VOICE_OUTPUT_ENABLED` | Enable TTS output | `true` |
| `GMAIL_CREDENTIALS_FILE` | Path to OAuth JSON | `google-credentials.json` |
| `EMAIL_ADDRESS` | Sender email address | — |
| `INSTAGRAM_CHROME_PROFILE` | Chrome profile for Instagram | `Profile 7` |
| `ALLOW_EMAIL_READ` | Permission flag | `true` |
| `ALLOW_CODE_EXECUTION` | Permission flag | `true` |

---

## 7. Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                   User Interface                     │
│  ┌─────────────────┐  ┌──────────────────────────┐   │
│  │  CLI (main.py)   │  │  Desktop UI (tkinter)    │   │
│  │  terminal-based  │  │  Dashboard/Charts/Chat   │   │
│  └────────┬─────────┘  └───────────┬──────────────┘   │
└───────────┼─────────────────────────┼──────────────────┘
            │                         │
            ▼                         ▼
┌─────────────────────────────────────────────────────┐
│               TomAgent (agent.py)                    │
│  ┌──────────┐ ┌──────────┐ ┌───────────────────┐   │
│  │ Command  │ │ Safety   │ │ Chat Memory       │   │
│  │ Router   │ │ Guards   │ │ (lifetime_chat)   │   │
│  └────┬─────┘ └────┬─────┘ └─────────┬─────────┘   │
│       │            │                 │              │
│       ▼            ▼                 ▼              │
│  ┌─────────────────────────────────────────────┐    │
│  │           Tool Layer (tools/)                │    │
│  │  OSTools │ BrowserTools │ FileTools         │    │
│  │  EmailTools │ VoiceTools │ ScreenTools      │    │
│  │  Scheduler │ Learning │ PDFTools │ Plugin   │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────┐
│              External Services                       │
│  Ollama (local LLM) │ Playwright (Browser)          │
│  Gmail OAuth2       │ Tesseract OCR                 │
│  Google Speech API  │ Instagram (via Chrome)        │
└─────────────────────────────────────────────────────┘
```

---

## 8. Supported User Commands

| Category | Example Commands |
|---|---|
| **Application Launch** | "Open Chrome", "Open Chrome Rajesh profile", "Launch Word", "Open Excel" |
| **Website Creation** | "Create website for my bakery store", "Make website for photography portfolio" |
| **Email** | "Write email to boss@example.com", "Draft email to client", "Send email to user@example.com", "Check inbox", "Summarize emails", "Review my inbox", "Triage emails" |
| **File Operations** | "Write code for login.py", "Create file index.html", "Read file path/to/file.txt", "Show me config/settings.json" |
| **Code Help** | "Fix my code", "Debug this", "Help me fix the error" |
| **Screen Reading** | "Read screen", "Analyze screen", "What's on screen", "Scan screen" |
| **Instagram** | "Run Instagram workflow", "Instagram scroll report", "Check Instagram AI news" |
| **Agent Building** | "Build agent that does X", "Create agent for Instagram and email", "Make agent called my_agent" |
| **Voice Control** | "Voice on", "Voice off", "Speak on", "Speak off" |
| **Scheduling** | Via code: schedule Instagram reports every 3 hours |
| **Chat** | "Hello", "What can you do?", "Tell me a joke" |
| **Feedback** | "reward 1.5", "penalty 0.5" (CLI only), UI Reward/Penalty buttons |
| **System** | "help", "exit", "quit" |

---

## 9. Limitations

1. **Ollama Required**: Agent won't function without Ollama running locally with the specified model.
2. **Windows-Only App Paths**: `os_tools.py` hardcodes Windows paths for Office and Chrome.
3. **Internet Dependency**: Voice input uses Google's online speech API; email needs IMAP/SMTP connectivity.
4. **Instagram Login**: Assumes Chrome profile is already logged into Instagram — no credential-based login.
5. **No Google Drive Integration**: The Instagram agent can save PDFs locally but the planned Google Drive upload is not implemented.
6. **Single-User**: No multi-user or session isolation.
7. **No API/Web Interface**: Only CLI and Tkinter desktop UI.

---

## 10. File Inventory

| File | Purpose |
|---|---|
| `main.py` | CLI entry point — terminal-based interaction loop |
| `agent.py` | Core agent — `TomAgent` class with all task executors |
| `tom_desktop_app.py` | Tkinter desktop UI — dashboard, charts, chat |
| `safety/guards.py` | Safety system — action blocking, logging, validation |
| `tools/os_tools.py` | Open applications, read/write files, directory listing |
| `tools/browser_tools.py` | Playwright browser automation |
| `tools/file_tools.py` | File creation, website scaffolding |
| `tools/email_tools.py` | Gmail OAuth2, IMAP/SMTP email operations |
| `tools/voice_tools.py` | Speech recognition and text-to-speech |
| `tools/screen_tools.py` | Screen capture and OCR text extraction |
| `tools/command_router.py` | Heuristic command classification and routing |
| `tools/approval.py` | User approval gate for sensitive actions |
| `tools/chrome_profiles.py` | Chrome profile discovery and launch |
| `tools/chat_memory.py` | Persistent chat history with context builder |
| `tools/learning.py` | Experience tracking with reward/penalty system |
| `tools/scheduler.py` | Background task scheduling (APScheduler) |
| `tools/plugin_manager.py` | Plugin discovery and loading |
| `tools/agent_builder.py` | Sub-agent scaffolding |
| `tools/pdf_tools.py` | PDF report generation (reportlab) |
| `config/system_prompt.txt` | LLM system prompt instructions |
| `.env` | Environment configuration |
| `requirements.txt` | Python package dependencies |
| `tom_desktop_app.spec` | PyInstaller build configuration |
| `launch_tom_ui.bat` | Console launcher |
| `launch_tom_ui.vbs` | Silent launcher (no console) |
