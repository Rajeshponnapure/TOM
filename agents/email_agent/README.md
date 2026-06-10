# Email Agent

This agent now has its own backend and can run as a standalone daemon.

It can:

- connect to your email provider
- fetch recent inbox messages
- classify important vs low-priority mail
- draft replies for messages that need attention
- auto-send low-priority replies when `EMAIL_AUTO_REPLY_ENABLED=true`
- keep running in the background on a check interval
- persist its last run, summary, and important-email queue for TOM to inspect

## Run

From the repository root:

```bash
python agents/email_agent/main.py
```

To keep it running continuously:

```bash
python agents/email_agent/main.py --daemon
```

To run a single triage pass:

```bash
python agents/email_agent/main.py --once
```

TOM can also control the daemon with commands like:

- `Start email agent`
- `Stop email agent`
- `Email agent status`
- `Email agent summary`

## Environment

Use the same email variables as the main TOM app:

- `EMAIL_ADDRESS`
- `EMAIL_PASSWORD` or Gmail OAuth credentials
- `GMAIL_CREDENTIALS_FILE`
- `GMAIL_TOKEN_FILE`
- `IMAP_HOST`
- `IMAP_PORT`
- `SMTP_SERVER`
- `SMTP_PORT`
- `EMAIL_PROVIDER`
- `EMAIL_INBOX_MAX_COUNT`
- `EMAIL_AUTO_REPLY_ENABLED`
- `EMAIL_CHECK_INTERVAL_SECONDS`
- `EMAIL_AGENT_STATE_DIR`

## Notes

The email agent stores runtime state in `tom_logs/email_agent_state.json` and process info in `tom_logs/email_agent.pid`. TOM reads those files to start, stop, and summarize the daemon without depending on TOM for the actual email loop.