# Environment Setup Guide

This is the single canonical guide for all environment variables used across the TOM project.

Use this document to fill in each `.env` or `config.example.env` file in the project.

## 1. What to fill in first

Start with the root project `.env` file. This is the main runtime configuration for TOM.

Then fill in the agent-specific example env files only if you are using those sub-agents:
- `agents/instagram_ai_news_agent/config.example.env`
- `agents/instagram_agent/config.example.env`
- `agents/test_agent2/config.example.env`

The obsolete WhatsApp scaffold folder has been removed and should not be used.

## 2. Root `.env` file

Create or update this file in the project root:
- `c:\Users\saimo\tom_autonomous_agent\.env`

### Required values

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest
```

### Recommended values

```env
OLLAMA_TIMEOUT_SECONDS=45
TASK_TIMEOUT_SECONDS=75
VOICE_INPUT_ENABLED=true
VOICE_OUTPUT_ENABLED=true
VOICE_SPEAK_TIMEOUT_SECONDS=8
FEEDBACK_MAX_LOOPS=5
```

### Optional values for email sending

```env
EMAIL_ADDRESS=your-email@gmail.com
GMAIL_CREDENTIALS_FILE=C:\path\to\client_secret.json
GMAIL_TOKEN_FILE=C:\path\to\gmail_token.json
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
EMAIL_PASSWORD=
```

### Optional values for Chrome profile selection

```env
CHROME_PROFILE_PATH=C:\Users\you\AppData\Local\Google\Chrome\User Data
CHROME_EXECUTABLE=C:\Program Files\Google\Chrome\Application\chrome.exe
```

### Optional values for OCR / screen reading

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

## 3. Instagram AI News agent env file

File:
- `c:\Users\saimo\tom_autonomous_agent\agents\instagram_ai_news_agent\config.example.env`

Copy it to `.env` in the same folder if you want a dedicated agent config.

### Values to set

```env
INSTAGRAM_CHROME_PROFILE=Default
EMAIL_ADDRESS=your-email@gmail.com
GMAIL_CREDENTIALS_FILE=path/to/client_secret.json
GMAIL_TOKEN_FILE=path/to/gmail_token.json
INSTAGRAM_POSTS_PER_RUN=50
INSTAGRAM_SCROLL_PAUSE_TIME=2.0
INSTAGRAM_MAX_SCROLL_ATTEMPTS=100
```

### Where to get these values

- `INSTAGRAM_CHROME_PROFILE`: from Chrome profile names under `%LOCALAPPDATA%\Google\Chrome\User Data`
- `EMAIL_ADDRESS`: the inbox that should receive the report
- `GMAIL_CREDENTIALS_FILE`: Google Cloud OAuth Desktop client JSON download
- `GMAIL_TOKEN_FILE`: local token cache file created after first OAuth sign-in
- `INSTAGRAM_POSTS_PER_RUN`: number of posts to inspect each run
- `INSTAGRAM_SCROLL_PAUSE_TIME`: delay between feed scrolls in seconds
- `INSTAGRAM_MAX_SCROLL_ATTEMPTS`: safety limit to stop infinite scrolling

## 4. Legacy or other agent env files

These folders still have example env files:
- `agents/instagram_agent/config.example.env`
- `agents/test_agent2/config.example.env`

Use them only if you are actively working on those older scaffolds. They are not required for the Instagram-to-email workflow.

## 5. How to get the real values

### OLLAMA settings
- Install Ollama locally.
- Start it with `ollama serve`.
- Confirm it is reachable at `http://localhost:11434`.
- Keep the model name as `llama3.2:latest` unless you intentionally use another model.

### Gmail OAuth settings
- Go to Google Cloud Console.
- Create or select a project.
- Enable the Gmail API.
- Create an OAuth Desktop client.
- Download the JSON credentials file.
- Save it somewhere on your machine and point `GMAIL_CREDENTIALS_FILE` to it.
- The first run creates the token file at `GMAIL_TOKEN_FILE` after login.

### Chrome profile settings
- Open File Explorer.
- Paste `%LOCALAPPDATA%\Google\Chrome\User Data` into the address bar.
- The profile folder is usually `Default` or `Profile 1`.
- Use that exact folder name in `INSTAGRAM_CHROME_PROFILE`.

### Tesseract settings
- Install Tesseract OCR for Windows.
- Add it to your PATH, or set `TESSERACT_CMD` directly.
- Only needed if you want screen reading/OCR features.

## 6. What no longer belongs in env files

Do not add WhatsApp-specific settings for the current project workflow.
The Instagram-to-email flow now uses:
- Instagram through your browser session
- Gmail / SMTP / IMAP for email delivery
- PDF report generation with ReportLab

## 7. Quick checklist

- Create the root `.env` file.
- Fill `OLLAMA_BASE_URL` and `OLLAMA_MODEL` first.
- Add Gmail settings if you want report delivery.
- Add Chrome profile settings if you want Instagram automation.
- Add OCR settings only if you need screen-reading support.
- Ignore the removed WhatsApp scaffold folder.

## 8. Related files

- `SETUP.md` for the main machine setup guide
- `README.md` for the project overview
- `agents/instagram_ai_news_agent/README.md` for the Instagram workflow details
