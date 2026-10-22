# Release checklist (PRD R10)

Name stays **TOM** (owner decision 2026-10-21) — no rename step.

## Before merging the refactor branch

- [ ] Close every TOM window (a running TOM rewrites `memories/lifetime_chat.json`).
- [ ] Back up the state folders: `memories/`, `tom_brain/`, `tom_logs/`, `data/`, and `.env`
      (see `docs/runbooks/rollback.md`).
- [ ] Full suite: `$env:TOM_SKIP_REAL_VOICE="1"; .venv311\Scripts\python.exe -m pytest -q` — must be green.
- [ ] Leak check: the suite writes nothing under the real `memories/`, `tom_brain/`, `tom_logs/`, `data/`
      (tests run under `TOM_STATE_ROOT`; compare folder timestamps before/after).
- [ ] Model benchmark refreshed if models changed: `tests\manual\benchmark_llm.py <models>` →
      `docs/benchmarks/llm-profiles.md`.
- [ ] Manual smoke test, both UIs (`launch_tom_ui.bat`, `launch_tom_qt.bat`):
  - [ ] Push-to-talk: speak a full sentence; it is heard whole; reply in the female US-English voice.
  - [ ] Press Talk while TOM is speaking: the reply stops; the new request runs once.
  - [ ] "Hey" → a greeting with no invented system or inbox status.
  - [ ] A WhatsApp request to an ambiguous name lists the matches and sends nothing until you choose.
  - [ ] Delete a test file → an approval prompt naming that exact file; it goes to the Recycle Bin.
  - [ ] Stop button during a task → the task ends; the next request works.
  - [ ] Autonomous: "autonomous task: list the 3 largest files in <folder>" → real file list.
  - [ ] "show my memories" / "forget memory N" work.
- [ ] `docs/migration/status.md` reflects the release; the PRD .docx is **not** committed.

## Rollback

`TOM_TASK_SERVICE=0` restores the pre-R2 execution path; `TOM_LLM_ADMISSION=0` disables the VRAM
check; every R9 feature is off unless its flag is set. A full rollback is `git checkout main` plus
restoring the state backup (`docs/runbooks/rollback.md`).
