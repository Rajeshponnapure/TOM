# Changelog

All notable changes to TOM. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **Slack, Discord and Telegram messaging** through their official APIs (`tools/chat_apps.py`): the exact target and
  text are approved first, and "sent" is reported only when the service returns a message id.
- **WhatsApp safety checks:** Desktop automation types only while WhatsApp is the foreground window and clicks only
  inside it; a known phone number (`WHATSAPP_CONTACTS`) opens the exact chat; Web mode refuses ambiguous names,
  checks the opened chat's header and reads the sent message back. Desktop results are reported as `unconfirmed`.
- **Email:** app-password SMTP sending (`EMAIL_PASSWORD`), `SMTP_STARTTLS` / `IMAP_SSL` switches, reconnect on a stale
  connection, unread-only inbox triage, and working opt-in auto-reply (once per message and sender, never to bots).
- `tools/generate_gmail_token.py` creates the Gmail OAuth token, with a paste-the-URL fallback when the browser
  cannot reach the local listener.
- Linux and macOS support for app discovery and launch; protected-path guard for `/etc`, `/usr`, `/System`, ...
- File requests such as "move the pdfs in downloads into a folder called Invoices".
- Whole-agent end-to-end tests against in-process fake SMTP / IMAP / chat-app servers; `ruff` correctness gate in CI;
  `pyproject.toml`, `CONTRIBUTING.md`, `SECURITY.md`, issue and PR templates, Dependabot.

### Changed
- "send an email/mail to ..." now sends (with approval) instead of drafting, and is no longer mistaken for an
  inbox request; the approval shows the real recipient, subject and body, and appears once.
- Email/Instagram agents use the same LLM provider selection as the main app (Groq by default when configured).
- Documentation moved under `docs/`; Windows launchers stay at the repository root.

### Fixed
- Email drafts could contain the internal prompt (with memory context) when the model ignored the requested format.
- WhatsApp commands like "send Madhu a message on WhatsApp saying hello" parsed the wrong contact.
- "message X on Telegram/Discord/Slack" opened the app and reported success without sending anything; Slack posts
  used to default to `#general` without asking.
- Folder detection picked `Documents` for "organize my pdf documents in downloads" and `/year` for "type/year".
- File organizing did not consult the protected-path guard.
- `tools/ml_engine.py`: the ARIMA forecast referenced `StatsARIMA` before importing it, so statsmodels was never used
  and the request silently fell back to the scratch implementation.

### Removed
- Stale internal audit/plan/readiness reports, `docs/archive/`, the deprecated `legacy/` tools, `.bak` backups,
  duplicate logo copies in the repository root, an unused Chrome-profile helper with a hard-coded personal name, and
  personal paths and email addresses from the documentation. All remain available in git history.

## [1.0.0]

- Hindsight long-term memory: retain / recall / reflect, offline queue, visible "Remembering" card, Memory screen.
- Hosted Groq as the default LLM when `GROQ_API_KEY` is set; local Ollama on opt-in; chat sessions.
- Verified file operations with plan → approval → execute → undo.
- Desktop app (Tkinter), CLI, capability registry with health checks, skills and knowledge routing,
  voice, document/spreadsheet/presentation creation, browser and Instagram agents, PyInstaller build and installer.
