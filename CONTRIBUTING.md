# Contributing to TOM

Thanks for helping. TOM acts on people's real files, email and messages, so the bar is
**verified behaviour, not plausible-looking code**.

## Setup

TOM supports **Python 3.11 only**.

```powershell
setup_python311_env.bat            # Windows: creates .venv311 and installs requirements.txt
copy .env.example .env             # every value has a default; add keys only for what you use
```

On any OS, the minimal test environment is:

```bash
python3.11 -m venv .venv311 && source .venv311/bin/activate
pip install -r requirements-ci.txt ruff
```

## Before you open a pull request

```bash
ruff check .                       # syntax errors and undefined names (the CI gate)
pytest                             # whole suite; pyproject.toml pins --basetemp to .pytest_tmp
python tools/verify_tom_system.py  # diagnostic self-check (optional but useful)
```

CI runs the same steps on every pull request. A change is done when they pass **and** you have
seen the behaviour work - see below.

## What "tested" means here

* **Fix a bug → first write a test that fails on the old code**, then fix it.
  Tests that only pass because the fake is too forgiving don't count.
* Prefer tests that run the real path: `TomAgent.execute_task` against the in-process fake
  SMTP / IMAP / Slack / Discord / Telegram servers (`tests/conftest.py`, `tests/test_chat_apps.py`),
  rather than mocks of our own functions.
* Anything that talks to a service we can't run in CI (Gmail OAuth, WhatsApp Desktop, real Hindsight
  Cloud) must say so in the pull request: what was tested against a fake, what was not tested.

## Rules for code that acts on the user's behalf

1. **Approval first.** Anything that sends, posts, moves, renames or deletes goes through
   `ApprovalManager` and shows the *real* target and content, not just the command text.
2. **Never claim success you didn't observe.** Use the service's confirmation (message id, read-back
   from the page, files found on disk). If it can't be confirmed, return `unconfirmed`, not `success`.
3. **Fail closed.** Unknown recipient, ambiguous name, protected path, missing config: stop and
   say why. Never fall back to a guess (no default channel, no "first match").
4. **No secrets or personal data in the repo.** `.env`, `*credentials*.json` and `*token*.json` are
   git-ignored; keep it that way. Use `you@example.com`, not a real address.
5. **Degrade gracefully.** Optional dependencies are imported lazily; a missing package must produce a
   clear message, not a crash at startup.

## Adding a capability

Add a real executor **and** register it in `tools/capability_registry.py`. A test rejects fake
capabilities and orphan tools. Route it from `tools/command_router.py` / `tools/engine_router.py` and add
routing tests for the phrasings you expect *and* a few that must not match.

## Style

* Match the surrounding code; keep functions small and typed where the file already is.
* `ruff` enforces correctness only (`pyproject.toml`); new style rules need their own pull request.
* Commit messages: an imperative summary line, then *why* the change was needed.

## Reporting problems

Bugs and feature requests: open an issue using the templates. **Security issues: do not open a
public issue** - see [SECURITY.md](SECURITY.md).
