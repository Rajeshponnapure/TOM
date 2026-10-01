# SETUP — Install & run TOM

This guide takes a fresh Windows machine to a working TOM install (development run or
packaged `.exe`). Follow the sections in order. For the design/architecture context, see
[ARCHITECTURE.md](ARCHITECTURE.md); for the feature overview, see [README.md](../README.md).

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

# Pick ONE way to run the LLM:
#   Path A (hosted, easiest): put GROQ_API_KEY=... in .env  (console.groq.com) — done.
#   Path B (local, no key):   install Ollama and pull the 3 models:
ollama serve                              # in another terminal
ollama pull gemma4:latest
ollama pull qwen2.5-coder:7b-instruct
ollama pull nomic-embed-text:latest       # embeddings — pull this one even on Groq

# Config (copy the template, then set the keys you actually need — see §4):
copy .env.example .env

# Run:
launch_tom_ui.bat

# Or put a double-clickable TOM icon on your Desktop:
create_desktop_shortcut.bat
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
- *(Optional)* **Git** on PATH — only needed if you want TOM to *clone and inspect* a
  GitHub repo via the tool-acquisition feature. Everything else works without it.
- *(Optional)* **ffmpeg** on PATH — only for video editing (photo editing needs none).

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
cd C:\path\to\TOM
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

Every value has a working default, so an empty `.env` is fine to start **if you run
local models**. The full annotated reference is in [`.env.example`](../.env.example).

### The one real decision: which LLM runs TOM

TOM needs a language model to reason. You only need **one** of the paths below to get a
fully working TOM — that single choice is the only genuinely required setup. You can also
set up **both** and switch between them live (see the note under the table).

| Path | What to set | Where to get it | Notes |
|------|-------------|-----------------|-------|
| **A — Groq (hosted, easiest)** | `GROQ_API_KEY=gsk_…` | Your Groq account's API-keys page (**console.groq.com**) | Becomes the **default** the moment the key is present. No local models to pull. Needs internet. |
| **B — Ollama (fully local, no key)** | nothing, or `TOM_LLM_PROVIDER=ollama` | Install Ollama + `ollama pull` the 3 models (§3) | No API key, runs offline, needs ~8 GB+ RAM. |
| **C — Both (switch live)** | the key from A **and** the models from B | both of the above | The header dropdown flips Groq ↔ Ollama with no restart; each remembers its own model. |

**About "both" (Path C):** having both configured does **not** blend them — exactly one
provider is active per request. The desktop header dropdown just lets you choose per task
(Groq for hosted speed/quality, Ollama for fully-offline local), switching instantly with
no restart. Use it when you want that flexibility; otherwise one provider is all you need.

**Embeddings always run locally via Ollama** (`nomic-embed-text`) even on Groq — Groq has
no embeddings endpoint — so pulling that one model helps the local RAG memory either way.

### Recommended: long-term memory (Hindsight)

TOM remembers your corrections and preferences across sessions via Hindsight. Without
it the app still runs, but memory is limited to the current session.

- `HINDSIGHT_API_KEY` — from **ui.hindsight.vectorize.io** (cloud), **or**
- `HINDSIGHT_BASE_URL=http://localhost:8888` — if you self-host the Hindsight server.
- `HINDSIGHT_ENABLED=0` turns long-term memory off entirely.

### Core local-model knobs (only if using Ollama / tuning)

- `OLLAMA_BASE_URL` — usually `http://localhost:11434`
- `OLLAMA_MODEL` — default `gemma4:latest`

If a configured model is not pulled, TOM falls back to an installed model of the
right kind (another tag of the same model first, then any chat model; embedding
models are never used for chat) and logs the `ollama pull <name>` fix. Choosing a
model from the desktop dropdown is saved to `.env` so it survives restarts.

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

### Only for chat apps (Slack / Discord / Telegram / WhatsApp)

Each is independent — set only the ones you use. Messages always go through the
approval gate before sending.

- `SLACK_BOT_TOKEN` — a Slack bot token with `chat:write` (+ `users:read` to message
  people by name). From your Slack app's **OAuth & Permissions** page (`xoxb-…`).
- `DISCORD_WEBHOOK_URL` / `DISCORD_WEBHOOKS` — channel webhook URLs
  (Discord → Channel Settings → Integrations → Webhooks). Webhooks post to a channel;
  they cannot DM.
- `TELEGRAM_BOT_TOKEN` — from **@BotFather**; plus `TELEGRAM_CHATS` mapping names to
  chat ids (the chat must have messaged the bot first).
- `WHATSAPP_CONTACTS` — a name→number map (international format). **No key** — WhatsApp
  goes through your signed-in browser/desktop session.

### Only for Groq image analysis (vision)

- `GROQ_VISION_MODEL` — set to a multimodal model id your Groq account can use, e.g.
  `meta-llama/llama-4-scout-17b-16e-instruct`. Without it, image questions fall back to
  local OCR (and TOM says so). Not needed on the Ollama path (local vision is used).

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

### Only to change where TOM builds things

- `TOM_WORKSPACE_DIR` — where TOM writes deliverables (websites, code projects,
  documents, decks). Default: `<your Desktop>/TOM Workspace`. Naming an explicit path in
  a request (e.g. "build it in `D:\Projects\Foo`") always wins. TOM never builds inside
  its own install folder.

> **No API key needed** for: Chrome automation, Instagram/YouTube browsing, WhatsApp
> (browser), local Microsoft Office automation, **network diagnostics** (devices on your
> wifi / port scan of your own hosts), **guarded delete**, **document/website/deck
> building**, and **tool acquisition** (installing a library uses `pip`; *cloning* a repo
> just needs **Git** on PATH — see §1). These use your local machine, signed-in browser
> session, and local apps — no cloud credentials.

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

## 6a) Optional: ffmpeg (video editing)

- Photo editing (`tools/media_engine.py`) works out of the box — Pillow is already in
  `requirements.txt`.
- Video editing (trim/concat/format-convert/text-overlay/color/volume) needs **ffmpeg**,
  which is a system binary, not a pip package:
  - Download from [ffmpeg.org/download.html](https://ffmpeg.org/download.html) and add
    `ffmpeg.exe` to PATH, **or** place it at `C:\ffmpeg\bin\ffmpeg.exe`.
  - Run `python tools/preflight.py` (or ask TOM "system status") to confirm it's found.
- Without ffmpeg, video-editing requests return a clear "ffmpeg is not installed" error
  instead of failing silently; photo editing is unaffected.

---

## 6b) Optional: external opt-in skills ("+864 auto-routed")

The 47 skills in `skills/` ship with TOM and load by default. The README's "+864 opt-in"
figure refers to a **separate, manually vendored** directory that is **not bundled with
this repo and not downloaded by any setup script here**:

- `tools/skill_manager.py` looks for `SKILL.md` files under `./awesome-claude-skills/`
  (project root) only when `TOM_INCLUDE_EXTERNAL_SKILLS=1` is set in `.env`.
- `.gitignore` excludes `awesome-claude-skills/` as a "vendored third-party repo (has its
  own .git; not tracked here)" — but no commit in this repo's history records which
  external repository was originally vendored there, and there are several unrelated
  GitHub projects that share the name "awesome-claude-skills" with different skill
  counts. **Pick the source yourself and verify its skill count before relying on the
  "+864" figure** — do not assume any particular one is correct.
- If you enable the flag without that directory present, TOM now logs a clear warning
  (`[SkillManager] TOM_INCLUDE_EXTERNAL_SKILLS is on but ... does not exist`) and simply
  runs with the 47 local skills — it will not crash or silently under-report.
- To use it: clone/copy your chosen skills collection into `./awesome-claude-skills/`
  such that each skill is `awesome-claude-skills/<skill-name>/SKILL.md`, then set
  `TOM_INCLUDE_EXTERNAL_SKILLS=1` in `.env`.

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
- `create_desktop_shortcut.bat` — creates/refreshes the **TOM** shortcut on your
  Desktop. It opens `dist\tom_desktop_app.exe` when that build exists, otherwise it
  runs `launch_tom_ui.vbs` so the source app starts with no console window. Re-run it
  any time; it overwrites the existing shortcut.

**CLI mode:** `python main.py` runs the agent without the GUI.

### Which model is TOM using?

`TOM_LLM_PROVIDER` in `.env` decides:

- **Groq (hosted)** — the default whenever `GROQ_API_KEY` is set. All chat slots run on
  `GROQ_MODEL` (default `openai/gpt-oss-120b`).
- **Ollama (local)** — only when you ask for it explicitly with
  `TOM_LLM_PROVIDER=ollama` (also accepts `local`). TOM never drifts back to a local
  model by itself.

Two deliberate exceptions, both reported in the chat window:

- **Embeddings** (RAG memory indexing) always run locally — Groq has no embeddings
  endpoint. This encoder does not answer prompts.
- **Image analysis** needs a vision model. If your Groq account has none, set
  `GROQ_VISION_MODEL` to a multimodal model, or run with `TOM_LLM_PROVIDER=ollama` for
  local vision. Otherwise TOM uses local OCR and says so.

A variable already exported in your shell wins over `.env` (standard dotenv behaviour, and what
headless scripts rely on). If a stale `TOM_LLM_PROVIDER` is left in an old terminal, TOM prints
a heads-up in the chat window rather than switching providers quietly — clear it with
`Remove-Item Env:TOM_LLM_PROVIDER` (PowerShell) and relaunch.

---

## 8) Verify the install

```powershell
# Diagnostic self-check — imports, capabilities, optional libraries
.venv311\Scripts\python.exe tools\verify_tom_system.py

# Full test suite (pyproject.toml already pins --basetemp to .pytest_tmp)
.venv311\Scripts\python.exe -m pytest
```

> **Windows temp note:** the default pytest temp dir under `pytest-of-<user>` can have
> broken ACLs on some machines. `pyproject.toml` already redirects `--basetemp` to
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
- [ ] **Choose your LLM:** either put `GROQ_API_KEY` in `.env` (hosted), **or** install
      Ollama, `ollama serve`, and pull the three default models (local).
- [ ] *(Recommended)* set `HINDSIGHT_API_KEY` (or `HINDSIGHT_BASE_URL`) for cross-session memory.
- [ ] Install Chrome; sign in to the sites you'll automate.
- [ ] *(Optional)* install **Git** (only for repo cloning) and **ffmpeg** (only for video editing).
- [ ] *(Optional)* install Tesseract; set `TESSERACT_CMD`.
- [ ] *(Optional)* `copy .env.example .env` and fill feature-specific values (chat-app tokens, email, …).
- [ ] *(Optional)* drop `tom_icon.png` / `tom_icon.ico` into `resources\`.
- [ ] Run `.venv311\Scripts\python.exe tools\verify_tom_system.py`.
- [ ] Launch with `launch_tom_ui.bat` (or `launch_tom_safe.bat` if it crashes).
- [ ] *(Optional)* `create_desktop_shortcut.bat` for the **TOM** Desktop shortcut.
- [ ] *(Optional)* `build.bat` for the EXE build.

---

## 14) Troubleshooting

| Symptom | Fix |
| --- | --- |
| "TOM requires Python 3.11.x" | Install official Python 3.11, then `setup_python311_env.bat`. |
| "TOM dependencies are missing" | Re-run `setup_python311_env.bat`. |
| `pip install pyaudio` fails | Use `pipwin install pyaudio` or a `cp311` PyAudio wheel. |
| LLM replies empty/limited | `ollama serve` running? Models pulled? Check `curl http://localhost:11434/api/tags`. |
| App crashes on launch | Run `launch_tom_safe.bat` (voice off, console visible) to see the error. |
| Mic not detected | Check drivers; ensure no other app holds the mic; or `VOICE_INPUT_ENABLED=false`. |
| Chrome profile launch fails | Confirm Chrome installed and the profile exists; optionally set `CHROME_PROFILE_PATH`. |
| `read my screen` does nothing | Install Tesseract; set `TESSERACT_CMD`; keep the target window visible. |
| EXE ignores `.env` / code changes | Run from source for `.env`; rebuild with `build.bat` after edits. |
| pytest permission errors in temp | Don't override `--basetemp`; it's pinned to `.pytest_tmp` in `pyproject.toml`. |

---

## 15) `.env` starter template

```env
# ── LLM: pick ONE path ────────────────────────────────────────────
# Path A — Groq (hosted, easiest): uncomment and paste your key.
# GROQ_API_KEY=gsk_your_key_here
# GROQ_MODEL=openai/gpt-oss-120b
#
# Path B — Ollama (local, no key): the defaults below. Pull the models first (§3).
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:latest
OLLAMA_FAST_MODEL=qwen2.5-coder:7b-instruct
OLLAMA_CODE_MODEL=qwen2.5-coder:7b-instruct
OLLAMA_EMBED_MODEL=nomic-embed-text:latest
OLLAMA_TIMEOUT_SECONDS=120
TASK_TIMEOUT_SECONDS=180

# ── Long-term memory (recommended) ────────────────────────────────
# HINDSIGHT_API_KEY=                     # from ui.hindsight.vectorize.io
# HINDSIGHT_BASE_URL=http://localhost:8888   # or self-host instead

# ── Where TOM builds things (optional) ────────────────────────────
# TOM_WORKSPACE_DIR=C:\Users\you\Desktop\TOM Workspace

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
