# SETUP — Move TOM to a new Windows machine

This file describes the steps to prepare a fresh Windows system to run TOM (development or packaged exe). Follow the sections in order.

For the full production target, also review [ARCHITECTURE.md](ARCHITECTURE.md).

This guide now distinguishes between three kinds of setup values:
- Required: needed for TOM to start and use local reasoning.
- Optional: only needed for a feature such as email, custom Chrome profiles, or OCR.
- Not needed: browser automation that uses your already signed-in Chrome session does not require extra API keys.

1) System prerequisites
- Windows 10 / 11 (x64)
- Python 3.10+ (3.11 recommended)
- 8+ GB RAM for small models; more if you plan to run large local models
- Ollama installed and available on the PATH (if you plan to run models locally)

2) Prepare Python environment (developer mode)

Open PowerShell and run:

```powershell
cd \path\to\tom_autonomous_agent
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Notes:
- If you cannot install `pyaudio` via pip on Windows, download a matching PyAudio wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio and install it with `pip install path\to\PyAudio‑<ver>.whl`.

3) Configure environment variables

Copy or create a `.env` file in the repo root (an example is in the project). Important items:

For the full, consolidated list of environment variables, see [ENVIRONMENT_SETUP_GUIDE.md](ENVIRONMENT_SETUP_GUIDE.md).

Required for the core app:

- `OLLAMA_BASE_URL` — usually `http://localhost:11434`
- `OLLAMA_MODEL` — defaults to `llama3.2:latest`

Recommended for stability:

- `OLLAMA_TIMEOUT_SECONDS` — timeout for LLM calls
- `TASK_TIMEOUT_SECONDS` — timeout for a single user task
- `VOICE_INPUT_ENABLED=true` and `VOICE_OUTPUT_ENABLED=true` to enable voice
- `VOICE_SPEAK_TIMEOUT_SECONDS` — protects the TTS thread from blocking
- `FEEDBACK_MAX_LOOPS=5` — limits the response feedback loop

Only if you want Gmail analysis or email sending:

- `EMAIL_ADDRESS` — the Gmail address you will sign in with
- `GMAIL_CREDENTIALS_FILE` — path to the Google OAuth client JSON file
- `GMAIL_TOKEN_FILE` — path to the cached OAuth token file
- `SMTP_SERVER` and `SMTP_PORT` — only if you use direct SMTP
- `IMAP_HOST` and `IMAP_PORT` — only if you want IMAP mail reading

Only if you want custom Chrome startup or profile selection:

- `CHROME_PROFILE_PATH` — optional override for a custom Chrome profile directory
- `CHROME_EXECUTABLE` — optional override if Chrome is installed in a non-standard location

Only for future OCR / screen understanding features:

- `TESSERACT_CMD` — path to the Tesseract executable if it is not on PATH

Recommended additional variables for the production architecture:

- `VOICE_RATE=`
- `VOICE_VOLUME=`

What you do not need to add for the current browser-based workflows:

- No Chrome API key is needed.
- No Instagram API key is needed if you are using browser automation with your logged-in session.
- No messaging API key or messaging developer account is needed because the project now uses email-only report delivery.
- No YouTube API key is needed for opening, browsing, or reading content in the browser.
- No Microsoft Office API key is needed for local Office automation on your machine.

Email delivery setup:

- Use your Gmail account or another SMTP/IMAP-compatible email account.
- Create a Google Cloud OAuth client if you want Gmail reading/sending with OAuth.
- Set `EMAIL_ADDRESS`, `GMAIL_CREDENTIALS_FILE`, and `GMAIL_TOKEN_FILE` in `.env`.
- If you use non-Gmail mail, set `SMTP_SERVER`, `SMTP_PORT`, `IMAP_HOST`, and `IMAP_PORT` instead.

Where to find the Chrome profile path:

- Open File Explorer and paste `%LOCALAPPDATA%\Google\Chrome\User Data` into the address bar.
- The profile folder is usually `Default` or `Profile 1`, `Profile 2`, etc.
- If TOM needs a fixed override, set `CHROME_PROFILE_PATH` to that user data folder.

If you want TOM to read what is currently on the screen:

- Install Tesseract OCR on Windows.
- Add the Tesseract binary to PATH or set `TESSERACT_CMD` in `.env`.
- Install the extra packages listed below if they are not already installed.

4) Install and start Ollama (local LLM)

Install Ollama following official docs. Then start it:

```powershell
ollama serve
# verify
curl http://localhost:11434/api/tags
```

5) Resources and icon

Create a `resources/` folder at the repo root and put your TOM artwork there. Recommended filenames:

- `tom_icon.png` — square PNG used in UI and for icon generation
- `tom_icon.ico` — Windows icon file used for the exe and shortcuts

To create `tom_icon.ico` from a PNG (requires Pillow):

```powershell
pip install pillow
python tools\make_icon.py resources\tom_icon.png
# result: resources\tom_icon.ico
```

6) Build a single-file executable (optional)

Install PyInstaller and build:

```powershell
pip install pyinstaller
pyinstaller --noconsole --onefile --add-data "resources;resources" --icon=resources\tom_icon.ico tom_desktop_app.py

# Output: dist\tom_desktop_app.exe
```

Notes:
- `--add-data "resources;resources"` bundles the `resources/` folder into the exe and ensures the app can find assets at runtime.
- Keep `tom_icon.ico` available to set the shortcut icon.

7) Create a Windows installer (recommended for distribution)

We provide an Inno Setup script at `installer/tom_installer.iss`.
Install Inno Setup, then run:

```powershell
iscc installer\tom_installer.iss
# Output: TOM-Installer.exe
```

8) Launching without a console

- The built single-file exe is built with `--noconsole` so it will not show a console.
- A `launch_tom_ui.vbs` helper is included to run the script via `pythonw` without a console during development.

9) Voice troubleshooting

- If you see: "Missing package: install 'SpeechRecognition' and 'pyaudio'", run:

```powershell
pip install SpeechRecognition
# if pip install pyaudio fails, use a wheel from the Gohlke site and install it
```

- If microphone is not detected, ensure drivers are installed and no other application is holding the mic.
- Use `VOICE_INPUT_ENABLED=false` in `.env` to disable voice if issues persist.

10) After moving to a new machine — quick checklist

- Install Python and create venv
- Install requirements
- Put `resources/tom_icon.png` and `tom_icon.ico` into `resources/`
- Start Ollama or point `OLLAMA_BASE_URL` to a reachable model endpoint
- (Optional) Build exe with PyInstaller and use the installer script

11) Support and next steps

If you want, I can:
- Produce the compiled installer artifact on a machine with Inno Setup installed.
- Expand smoke tests into a CI script.
- Start Phase 3 features (guarded engineer capabilities) after you confirm deployment is successful on the target machine.

12) Recommended production extras

If you plan to extend TOM into the full assistant described in `ARCHITECTURE.md`, install the optional libraries below as needed:

```powershell
pip install fastapi uvicorn pydantic pyautogui pywinauto opencv-python pytesseract python-pptx reportlab pywin32 apscheduler
```

For OCR, also install the Tesseract Windows binary and add it to PATH.

13) Suggested `.env` template

Use this as a starting point, then only fill in the feature-specific values you actually need:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest
OLLAMA_TIMEOUT_SECONDS=45
TASK_TIMEOUT_SECONDS=75
VOICE_INPUT_ENABLED=true
VOICE_OUTPUT_ENABLED=true
VOICE_SPEAK_TIMEOUT_SECONDS=8
FEEDBACK_MAX_LOOPS=5

# Only for Gmail / email features
# EMAIL_ADDRESS=you@gmail.com
# GMAIL_CREDENTIALS_FILE=C:\path\to\client_secret.json
# GMAIL_TOKEN_FILE=C:\path\to\gmail_token.json
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# IMAP_HOST=imap.gmail.com
# IMAP_PORT=993

# Only for custom Chrome startup
# CHROME_PROFILE_PATH=C:\Users\you\AppData\Local\Google\Chrome\User Data
# CHROME_EXECUTABLE=C:\Program Files\Google\Chrome\Application\chrome.exe

# Only for OCR / screen reading
# TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

