# SETUP — Install & run TOM

This guide takes a fresh Windows machine to a working TOM install (development run or
packaged `.exe`). Follow the sections in order. For the design/architecture context, see
[ARCHITECTURE.md](ARCHITECTURE.md); for the feature overview, see [README.md](README.md).

Setup values fall into three buckets:
- **Required** — needed for TOM to start and use local reasoning.
- **Optional** — only for a specific feature (email, custom Chrome profile, OCR, voice).
- **Not needed** — browser automation that reuses your signed-in Chrome session needs
  no extra API keys.

---

## 0) TL;DR (the fast path)

```powershell
# From the repo root:
setup_python311_env.bat        # creates .venv311 and installs requirements.txt

# In another terminal:
ollama serve
ollama pull gemma4:latest
ollama pull qwen2.5-coder:7b-instruct
ollama pull nomic-embed-text:latest

# Optional config:
copy .env.example .env         # then edit values you actually need

# Run:
launch_tom_ui.bat
```

If anything fails, read the matching section below.

---

## 1) System prerequisites

- **Windows 10 / 11 (x64).**
- **Python 3.11.x — required.** TOM does **not** support 3.10 or 3.12. The launchers and
  `requirements.txt` enforce this. Install official Python 3.11 from python.org and tick
  *"Add Python to PATH"*.
- **8+ GB RAM** for small local models; more for larger models.
- **[Ollama](https://ollama.com)** installed and on PATH (runs the local LLM).
- **Google Chrome** installed (for browser-automation features).
- *(Optional)* **Tesseract OCR** for screen reading.
- *(Optional)* **Node.js** if you want TOM to run/verify `.js` projects.

Verify Python:

```powershell
py -3.11 --version
# or
python --version      # must print 3.11.x
```

---

## 2) Create the Python 3.11 environment

**Recommended — use the provided script.** It creates `.venv311` with the correct
interpreter and installs everything:

```powershell
cd C:\path\to\tom_autonomous_agent
setup_python311_env.bat
```

**Manual alternative:**

```powershell
py -3.11 -m venv .venv311
.\.venv311\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> The launchers look for the interpreter in this order: `.venv311\` → `venv\` →
> `py -3.11` → a system Python 3.11 install → `python` (only if it is 3.11). Keeping the
> env in `.venv311` is the smoothest path.

**PyAudio note (voice input):** if `pip install -r requirements.txt` can't build
`pyaudio` on Windows, install a prebuilt wheel:

```powershell
pip install pipwin
pipwin install pyaudio
# or download a matching cp311 wheel and: pip install path\to\PyAudio-<ver>-cp311-...whl
```

Voice still works without PyAudio for output (TTS); PyAudio is only needed for
microphone input.

---

## 3) Install and start Ollama + pull models

Install Ollama, then start the server and pull the default models:

```powershell
ollama serve
# in another terminal:
ollama pull gemma4:latest                 # primary reasoning model
ollama pull qwen2.5-coder:7b-instruct     # fast + code model
ollama pull nomic-embed-text:latest       # embeddings for RAG memory

# verify the server is up:
curl http://localhost:11434/api/tags
```

You can substitute any Ollama model by setting `OLLAMA_MODEL`, `OLLAMA_FAST_MODEL`,
`OLLAMA_CODE_MODEL`, or `OLLAMA_EMBED_MODEL` in `.env`. If Ollama is offline, TOM's UI
still launches but LLM reasoning, planning, and RAG memory are limited.

---

## 4) Configure `.env`

Copy the annotated template and edit only what you need:

```powershell
copy .env.example .env
```

Every value has a working default, so an empty `.env` is fine to start. The full
annotated reference is in [.env.example](.env.example) and
[ENVIRONMENT_SETUP_GUIDE.md](ENVIRONMENT_SETUP_GUIDE.md).

### Required for the core app
- `OLLAMA_BASE_URL` — usually `http://localhost:11434`
- `OLLAMA_MODEL` — default `gemma4:latest`

### Recommended for stability
- `OLLAMA_TIMEOUT_SECONDS` — LLM call timeout (default 120)
- `TASK_TIMEOUT_SECONDS` — per-task timeout (default 180)
- `OLLAMA_FAST_MODEL`, `OLLAMA_CODE_MODEL`, `OLLAMA_EMBED_MODEL` — model slots

### Only for Gmail / email features
- `EMAIL_ADDRESS` — the Gmail address you sign in with
- `EMAIL_PASSWORD` — a Gmail **App Password** (if using SMTP/IMAP directly)
- `GMAIL_CREDENTIALS_FILE` — path to the Google OAuth client JSON
- `GMAIL_TOKEN_FILE` — path to the cached OAuth token
- `IMAP_HOST` / `IMAP_PORT` / `SMTP_SERVER` / `SMTP_PORT` — only if you override defaults

See [GMAIL_OAUTH_SETUP.md](GMAIL_OAUTH_SETUP.md) for the OAuth walkthrough.

### Only for the Instagram agent
- `INSTAGRAM_CHROME_PROFILE`, `INSTAGRAM_POSTS_PER_RUN`,
  `INSTAGRAM_CHECK_INTERVAL_SECONDS`, `INSTAGRAM_AUTO_SEND_REPORT_EMAIL`, and the other
  `INSTAGRAM_*` tuning values in `.env.example`.

### Only for custom Chrome startup
- `CHROME_PROFILE_PATH` — custom Chrome user-data directory
- `CHROME_EXECUTABLE` — override if Chrome is installed somewhere unusual

### Only for OCR / screen reading
- `TESSERACT_CMD` — path to `tesseract.exe` if it is not on PATH

### Only for voice
- `VOICE_INPUT_ENABLED` / `VOICE_OUTPUT_ENABLED` — turn voice on/off
- `TOM_VOICE`, `TOM_VOICE_RATE`, `VOICE_RECOGNITION_ENGINE`, and threshold tuning values

> **No API key needed** for Chrome automation, Instagram/YouTube browsing in the
> browser, WhatsApp-via-browser, or local Microsoft Office automation. Those use your
> signed-in browser session and local apps.

---

## 5) Where to find your Chrome profile path

- Paste `%LOCALAPPDATA%\Google\Chrome\User Data` into File Explorer's address bar.
- The profile folder is usually `Default`, or `Profile 1`, `Profile 2`, …
- TOM can auto-discover profiles; only set `CHROME_PROFILE_PATH` if you want to force a
  specific user-data directory.

---

## 6) Optional: Tesseract OCR (screen reading)

- Install the Tesseract Windows binary.
- Add it to PATH, **or** set `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe`
  in `.env`.
- `pytesseract` and `opencv-python` are already in `requirements.txt`.

---

## 7) Run TOM (development)

```powershell
launch_tom_ui.bat
```

The launcher finds Python 3.11, checks that core dependencies import, then starts
`tom_desktop_app.py`.

**Other launchers:**
- `launch_tom_safe.bat` — voice disabled + console visible. Use this first if the app
  crashes or behaves oddly.
- `launch_tom_debug.bat` — console visible for full tracebacks.
- `launch_tom_ui.vbs` — runs via `pythonw` with no console window (development).

**CLI mode:** `python main.py` runs the agent without the GUI.

---

## 8) Verify the install

```powershell
# Diagnostic self-check — imports, capabilities, optional libraries
.venv311\Scripts\python.exe tools\verify_tom_system.py

# Full test suite (pytest.ini already pins --basetemp to .pytest_tmp)
.venv311\Scripts\python.exe -m pytest
```

> **Windows temp note:** the default pytest temp dir under `pytest-of-<user>` can have
> broken ACLs on some machines. `pytest.ini` already redirects `--basetemp` to
> `.pytest_tmp` to avoid this — don't override it.

---

## 9) Build the desktop `.exe` (optional)

The build uses the committed spec `tom_desktop_app.spec`:

```powershell
build.bat
# Output: dist\tom_desktop_app.exe  +  dist\SHA256SUMS.txt
```

Or do environment-setup → build → Desktop shortcut in one shot:

```powershell
SETUP_TOM.bat
```

Notes:
- The binary is **unsigned**, so Windows SmartScreen may warn on first run.
- **Rebuild after every code change** — the frozen EXE does not auto-pick-up edits.
- The frozen EXE **does not read `.env`**. Env-gated features fall back to their
  bootstrap defaults inside the EXE (voice defaults to ON in the bundle). If you depend
  on `.env` values, run from source instead, or bake them into the build environment.

### Manual PyInstaller (if you prefer)

```powershell
pip install pyinstaller
pyinstaller --noconsole --onefile --add-data "resources;resources" `
  --icon=resources\tom_icon.ico tom_desktop_app.py
```

---

## 10) Build a Windows installer (optional, for distribution)

An Inno Setup script lives at `installer\tom_installer.iss`:

```powershell
# Install Inno Setup first, then:
iscc installer\tom_installer.iss
# Output: TOM-Installer.exe
```

---

## 11) Icon assets

Put artwork in `resources\`:
- `tom_icon.png` — square PNG used in the UI
- `tom_icon.ico` — Windows icon for the EXE and shortcuts

Generate the `.ico` from a PNG (needs Pillow, already in requirements):

```powershell
python tools\make_icon.py resources\tom_icon.png
# -> resources\tom_icon.ico
```

---

## 12) Background agents (optional)

TOM ships two long-running agents you can start as daemons:

```powershell
start_email_agent_daemon.bat        # inbox monitoring / triage
start_instagram_agent_daemon.bat    # Instagram AI-news extraction + report
```

You can also control them by chatting with TOM: `start email agent`,
`stop instagram agent`, `email agent status`. Both honor the approval gate before
sending anything.

---

## 13) Moving to a new machine — checklist

- [ ] Install official **Python 3.11** (Add to PATH).
- [ ] Run `setup_python311_env.bat` (creates `.venv311`, installs requirements).
- [ ] Install Ollama; `ollama serve`; pull the three default models.
- [ ] Install Chrome; sign in to the sites you'll automate.
- [ ] *(Optional)* install Tesseract; set `TESSERACT_CMD`.
- [ ] *(Optional)* `copy .env.example .env` and fill feature-specific values.
- [ ] *(Optional)* drop `tom_icon.png` / `tom_icon.ico` into `resources\`.
- [ ] Run `.venv311\Scripts\python.exe tools\verify_tom_system.py`.
- [ ] Launch with `launch_tom_ui.bat` (or `launch_tom_safe.bat` if it crashes).
- [ ] *(Optional)* `build.bat` for the EXE + Desktop shortcut.

---

## 14) Troubleshooting

| Symptom | Fix |
|---|---|
| "TOM requires Python 3.11.x" | Install official Python 3.11, then `setup_python311_env.bat`. |
| "TOM dependencies are missing" | Re-run `setup_python311_env.bat`. |
| `pip install pyaudio` fails | Use `pipwin install pyaudio` or a `cp311` PyAudio wheel. |
| LLM replies empty/limited | `ollama serve` running? Models pulled? Check `curl http://localhost:11434/api/tags`. |
| App crashes on launch | Run `launch_tom_safe.bat` (voice off, console visible) to see the error. |
| Mic not detected | Check drivers; ensure no other app holds the mic; or `VOICE_INPUT_ENABLED=false`. |
| Chrome profile launch fails | Confirm Chrome installed and the profile exists; optionally set `CHROME_PROFILE_PATH`. |
| `read my screen` does nothing | Install Tesseract; set `TESSERACT_CMD`; keep the target window visible. |
| EXE ignores `.env` / code changes | Run from source for `.env`; rebuild with `build.bat` after edits. |
| pytest permission errors in temp | Don't override `--basetemp`; it's pinned to `.pytest_tmp` in `pytest.ini`. |

---

## 15) `.env` starter template

```env
# Core (LLM)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:latest
OLLAMA_FAST_MODEL=qwen2.5-coder:7b-instruct
OLLAMA_CODE_MODEL=qwen2.5-coder:7b-instruct
OLLAMA_EMBED_MODEL=nomic-embed-text:latest
OLLAMA_TIMEOUT_SECONDS=120
TASK_TIMEOUT_SECONDS=180

# Voice (optional)
VOICE_INPUT_ENABLED=false
VOICE_OUTPUT_ENABLED=false

# Email (optional — Gmail/inbox features)
# EMAIL_ADDRESS=you@gmail.com
# EMAIL_PASSWORD=your_app_password
# GMAIL_CREDENTIALS_FILE=google-credentials.json
# GMAIL_TOKEN_FILE=google-credentials_token.json
# IMAP_HOST=imap.gmail.com
# IMAP_PORT=993
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587

# Browser (optional — custom Chrome startup)
# CHROME_EXECUTABLE=C:/Program Files/Google/Chrome/Application/chrome.exe
# CHROME_PROFILE_PATH=%LOCALAPPDATA%/Google/Chrome/User Data

# OCR (optional — screen reading)
# TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```
