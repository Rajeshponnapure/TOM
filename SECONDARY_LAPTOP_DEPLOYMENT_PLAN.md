# Secondary Laptop Deployment Plan

This plan is the operational handoff for moving TOM, the email agent, and the Instagram agent to a second Windows laptop so the workflows can run 24x7 without consuming the primary machine.

If you want the fast path, run [setup_secondary_laptop.ps1](setup_secondary_laptop.ps1) from the repo root. It prints the checklist, verifies tools, and gives the exact commands to bring the machine online.

## 1) What must move

Copy the entire repository folder, including:
- `AGENTS.md`
- `CLAUDE.md`
- `skills/`
- `config/`
- `tools/`
- `agents/`
- `.env` or a fresh `.env` created from the same values
- `google-credentials.json`
- `google-credentials_token.json`
- `reports/` only if you want old PDFs preserved
- `tom_logs/` only if you want prior state preserved

## 2) What must be installed on the secondary laptop

- Python 3.11
- Google Chrome
- Ollama if you want local LLM summaries
- `ffmpeg` on PATH for video-audio transcription
- Tesseract OCR on PATH if you want image text extraction fallback

## 3) Required configuration

Set these environment variables on the new machine:

- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `EMAIL_ADDRESS`
- `GMAIL_CREDENTIALS_FILE`
- `GMAIL_TOKEN_FILE`
- `CHROME_PROFILE_PATH` or `INSTAGRAM_CHROME_PROFILE`
- `EMAIL_PROVIDER=gmail`
- `EMAIL_INBOX_MAX_COUNT`
- `EMAIL_AUTO_REPLY_ENABLED`
- `EMAIL_CHECK_INTERVAL_SECONDS`
- `INSTAGRAM_POSTS_PER_RUN`
- `INSTAGRAM_CHECK_INTERVAL_SECONDS`
- `INSTAGRAM_MAX_CAROUSEL_PAGES`
- `INSTAGRAM_VIDEO_AUDIO_CAPTURE_ENABLED`

## 4) Install and verify

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Test the core pieces:

```powershell
.\venv\Scripts\python.exe agents\instagram_ai_news_agent\main.py --once
.\venv\Scripts\python.exe -c "from tools.email_agent_controller import EmailAgentController; print(EmailAgentController().status())"
```

Or run the one-command helper:

```powershell
.\setup_secondary_laptop.ps1 -Bootstrap
```

## 5) Start scripts

Use these launcher files from the repository root:

- `start_email_agent_daemon.bat`
- `start_instagram_agent_daemon.bat`

Both scripts call the controller layer so they avoid duplicate daemon starts.

## 6) 24x7 scheduling

Create two Windows Task Scheduler entries for each agent:

- `KeepAlive` task every 5 minutes
- `OnLogon` task at startup/login

If you want an admin-level task, create a SYSTEM task from an elevated PowerShell session. Example:

```powershell
$action = New-ScheduledTaskAction -Execute 'C:\Path\To\Repo\start_instagram_agent_daemon.bat'
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName 'TomInstagramAgent-SYSTEM' -Action $action -Trigger $trigger -RunLevel Highest -User 'SYSTEM'
```

## 7) How the strict instruction system works

The agents now load the following runtime instruction stack before producing replies or generated content:

- `CLAUDE.md`
- `AGENTS.md`
- `config/system_prompt.txt`
- `skills/SKILL.md`
- `skills/design-systems.md`
- `skills/uniqueness-engine.md`
- `skills/platform-specs.md`
- `skills/ui-patterns.md`

For visible outputs like PDFs or reports, the UI skill stack is applied automatically so generated artifacts use a deliberate visual system instead of a template-looking layout.

Instagram report emails now use the same polished presentation logic so the email itself reads like a curated digest instead of a plain log dump.

## 8) Operational checklist

- Confirm Chrome is logged into the correct Instagram profile.
- Confirm Gmail OAuth works on the secondary laptop.
- Confirm Ollama is reachable.
- Run each agent once manually before scheduling it.
- Only after a successful manual run, enable the scheduled tasks.

## 9) Recovery steps

If an agent stops:

1. Check the matching `tom_logs/*_agent_state.json` file.
2. Check the matching PID file.
3. Kill the stale process if needed.
4. Rerun the matching launcher `.bat` file.
5. Recheck the PDF/report output under `reports/`.
