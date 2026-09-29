# Security Policy

## Supported versions

Only the latest commit on `main` receives security fixes.

## Reporting a vulnerability

Please **do not open a public issue**. Report it privately through GitHub:
<https://github.com/Rajeshponnapure/TOM/security/advisories/new>

Include what you found, how to reproduce it, and the impact you expect. You should get a first
response within a few days. Please give us reasonable time to fix the problem before disclosing it.

## What TOM protects, and how

TOM runs on your own computer and can act on your files, email and messages. The safeguards below are
covered by tests in `tests/`.

* **Approval gate.** Sending email, WhatsApp / Slack / Discord / Telegram messages, and moving or renaming
  files ask first, showing the real recipient, text and file counts. Declining sends or changes nothing.
* **Protected locations.** File organizing and file writes refuse system folders
  (`C:\Windows`, `C:\Program Files`, `/etc`, `/usr`, `/System`, ...). Undo is available for the last organization.
* **No guessing.** Ambiguous recipients, unknown Slack users and unknown Discord webhooks are rejected instead of
  defaulting to a channel or the first match.
* **Auto-reply is opt-in** (`EMAIL_AUTO_REPLY_ENABLED`), never answers bots or no-reply senders, answers each
  message once, and is rate-limited.
* **Secrets stay local.** `.env`, `*credentials*.json`, `*token*.json`, `*.pem` and `*.key` are git-ignored,
  and the migration packager skips them.
* **Audit log.** Actions are recorded in `tom_logs/safety_log.txt` (rotated at about 2 MB).

## Handling your own credentials

* Treat `google-credentials_token.json` and `.env` like passwords. If one leaks, delete the token and revoke
  access at <https://myaccount.google.com/permissions>, and rotate any app password or API key it contained.
* If your TOM folder is inside OneDrive/Dropbox, set `GMAIL_TOKEN_FILE` to a path outside it.
* Before pushing to a remote, check nothing sensitive is tracked:
  `git ls-files | findstr /i "env credential token"` (Windows) or
  `git ls-files | grep -i -E "env|credential|token"` - only `.env.example` and source files should appear.

## Known limitations

* The Windows executable is **unsigned**, so SmartScreen may warn on first run. `build.bat` writes a SHA-256
  checksum to `dist\SHA256SUMS.txt` - publish it next to any download.
* WhatsApp Desktop automation cannot read the app back, so it reports "unconfirmed" rather than "sent".
