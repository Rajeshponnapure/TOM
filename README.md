# TOM Desktop

TOM is a Windows-first local automation assistant with a Tkinter UI, Ollama-backed reasoning, voice input/output, browser automation, and a growing plugin architecture for real desktop workflows.

Start here
- [Architecture guide](ARCHITECTURE.md)
- [Setup and deployment](SETUP.md)

What you need to provide
- For the default assistant experience, you only need a working Windows account, Python environment, Ollama, and a logged-in Chrome profile.
- For Gmail analysis or sending mail, provide Gmail OAuth credentials and the Google account email address.
- For custom Chrome startup, provide the Chrome profile name or a `CHROME_PROFILE_PATH` override.
- For browser-only workflows like Instagram and YouTube, no API key is required if you are already signed into those sites in Chrome.
- For OCR or screen-reading workflows, you will later need Tesseract installed locally.

Email delivery
- TOM uses Gmail or SMTP/IMAP for generated report delivery.
- If you want TOM to send reports automatically, provide Gmail OAuth credentials and the sender email address.
- The Instagram report workflow now ends with email delivery.

Where to get the Chrome profile path
- On Windows, the Chrome user data folder is usually `C:\Users\<your-user>\AppData\Local\Google\Chrome\User Data`.
- The profile folder inside it is usually `Default`, `Profile 1`, `Profile 2`, and so on.
- TOM can discover these profiles automatically, or you can provide the base path in `CHROME_PROFILE_PATH`.

Screen reading
- TOM can now inspect visible screen text with OCR when you ask it to read or analyze the screen.
- This works best after installing Tesseract locally and ensuring the target app is visible on the desktop.

What you do not need to hard-code
- Do not hard-code website passwords into the project.
- Do not add external messaging configuration for the current workflow; report delivery is email-only.
- Do not add API keys for Chrome, Instagram, YouTube, or Word automation; those flows use local desktop or browser sessions.

Current runtime
- UI: [tom_desktop_app.py](tom_desktop_app.py)
- Agent core: [agent.py](agent.py)
- Voice helpers: [tools/voice_tools.py](tools/voice_tools.py)
- Command routing: [tools/command_router.py](tools/command_router.py)
- Approval flow: [tools/approval.py](tools/approval.py)
- Chrome profile discovery: [tools/chrome_profiles.py](tools/chrome_profiles.py)
- Plugin discovery: [tools/plugin_manager.py](tools/plugin_manager.py)
- Memory and learning: [tools/learning.py](tools/learning.py)

Development run

1. Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Start Ollama:

```powershell
ollama serve
```

4. Launch TOM:

```powershell
python tom_desktop_app.py
```

What TOM now covers
- Voice and text interaction
- Chrome profile detection and profile-aware launch paths
- Email drafting and approval-first sending
- Local experience logging with truthful outcome normalization
- Plugin discovery under `agents/`
- Basic OCR screen-reading support for visible text on the desktop

Configuration reference

Required for the core app
- `OLLAMA_BASE_URL` — local Ollama endpoint, usually `http://localhost:11434`
- `OLLAMA_MODEL` — local model name, for example `llama3.2:latest`

Recommended for smoother use
- `TASK_TIMEOUT_SECONDS` — keeps long tasks from blocking the UI too long
- `OLLAMA_TIMEOUT_SECONDS` — stops model calls from hanging indefinitely
- `VOICE_INPUT_ENABLED` and `VOICE_OUTPUT_ENABLED` — turn voice features on or off
- `VOICE_SPEAK_TIMEOUT_SECONDS` — prevents TTS from locking the loop
- `FEEDBACK_MAX_LOOPS` — limits the reward/penalty feedback cycle

Only if you want email workflows
- `EMAIL_ADDRESS` — the Gmail address used for OAuth and sending
- `GMAIL_CREDENTIALS_FILE` — Google OAuth client file path
- `GMAIL_TOKEN_FILE` — token cache file path
- `SMTP_SERVER` and `SMTP_PORT` — optional if you use SMTP directly
- `IMAP_HOST` and `IMAP_PORT` — optional if you want mail reading through IMAP

Only if you want custom browser startup
- `CHROME_PROFILE_PATH` — custom Chrome user data directory
- `CHROME_EXECUTABLE` — optional override if Chrome is installed somewhere unusual

Only for future OCR / screen understanding work
- `TESSERACT_CMD` — path to the Tesseract executable if it is not on PATH

Packaging
- PyInstaller and Inno Setup instructions are in [SETUP.md](SETUP.md).

Troubleshooting
- If voice input shows a missing package error, install `SpeechRecognition` and `pyaudio`.
- If Chrome profile launch fails, confirm that Chrome is installed and that the desired profile exists under your Windows Chrome user data directory.
- If Ollama is unavailable, the UI still starts, but LLM-backed responses and planning will be limited.
