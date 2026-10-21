# Refactor Status (PRD v1.1 supplement §S5)

Last updated 2026-10-21.

| Phase | State | Evidence |
|---|---|---|
| R0 Repository audit | **Done — approved by owner 2026-10-21** | `docs/architecture/*`, `docs/migration/*`, `docs/security/tool-permissions.md`, `docs/runbooks/rollback.md` |
| R1 Characterization tests | **Done** | `tests/characterization/` — 21 offline tests (~9 s) |
| R2 Shared task facade | **Done** | `tom_core/tasks/` — `TomAgent.execute_task()` is a facade over `TaskService.submit_task()`; CLI, Tk chat, Tk voice, voice mode, scheduler and the PySide6 UI all go through it with an `interface` label. Rollback: `TOM_TASK_SERVICE=0` |
| R3 Policy + typed tools | **Started** — secret redaction only | `tom_core/observability/redact.py`, applied to the audit log and the task store. Policy engine / typed tool registry not started |
| R4 Durable task state | **Partly done** | SQLite store (`tom_brain/tasks.sqlite3`), restart reconciliation (orphaned tasks → `BLOCKED`, never replayed), cross-process cancel, emergency stop. Not yet: checkpoints, retry ceilings, pause/resume |
| R5 Memory adapter | **Partly done** | Local SQLite memory behind the Hindsight client surface (ADR-010); cloud opt-in. Not yet: provenance/confidence fields, retention policy, memory editing UI |
| R6 Resource manager | **Started** | Measured-VRAM admission for the ASR model (ADR-009), CPU/RAM/VRAM panel. Not yet: LLM admission, `num_ctx` profiles, benchmark harness |
| R8 Voice and interfaces | **Largely done** | Local ASR/TTS adapters in worker processes, female Indian-English voice preference (`TOM_TTS_GENDER`), one push-to-talk module (`tom_core/voice/push_to_talk.py`) used by both the PySide6 and the Tkinter app, professional voice persona; PySide6 desktop UI |
| R7, R9, R10 | Not started | — |

## Owner decisions recorded (2026-10-21)

ADR-002 `tom_core/` ✔ · ADR-003 keep Tkinter **and** add PySide6 ✔ · ADR-005 cloud routes opt-in, local default ✔ ·
`.env` cleaned (duplicate keys removed, installed models only) ✔.

## Acceptance tests

| PRD test | Status | Where |
|---|---|---|
| AT-001 Task lifecycle | Partial — id, persisted state, events, final outcome; no plan/steps yet | `test_task_service.py` |
| AT-003 Approval gate | Characterized (delete, email); Qt dialog shows exact target | `characterization/`, `test_qt_app.py` |
| AT-005 Cancellation | **Pass** | `test_cancel_requested_from_another_interface_stops_the_task` |
| AT-006 Recovery | **Pass** (no blind replay) | `test_restart_marks_orphaned_tasks_blocked_and_never_replays` |
| AT-007 Verification | **Pass** for state labelling (`UNVERIFIED`) | `test_success_is_only_claimed_with_evidence` |
| AT-010 Secret redaction | **Pass** (audit log + task store) | `test_secrets_never_reach_the_audit_log`, redaction tests |
| AT-012 Cross-interface state | **Pass** (shared store + remote cancel) | `test_task_service.py`, `test_qt_app.py` |
| AT-014 Voice interruption | Partial — stop flag + playback stop tested; barge-in during listening not yet | `test_voice_core.py` |
| TOM-MIG-002 execute_task compatibility | **Pass** | full suite |
| TOM-MIG-003 Memory continuity | Partial — journal seeding tested; see open item 1 | `test_local_memory.py` |
| TOM-MIG-007 Rollback | **Pass** for `TOM_TASK_SERVICE=0` | `test_rollback_flag_runs_the_legacy_path` |
| TOM-MIG-009 Secret handling | **Pass** for logs/tasks | — |
| TOM-MIG-010 No direct execution bypass | **Open** — Tk engine buttons still call tools directly (R7). Closed for Tk voice: the old sidebar voice mode (`generate_voice_response`, which skipped TaskService for most requests) was replaced by push-to-talk on 2026-10-21; the CLI voice mode in `main.py` still uses it | `current-state.md` §2, `test_push_to_talk.py` |

## R0 defects

| # | Status |
|---|---|
| D1 dead `process_message` forward | open |
| D2 duplicate `TOM_LLM_PROVIDER` | **fixed** (`.env`) |
| D3 configured model not installed | **fixed** (`qwen3:8b` / `nomic-embed-text`) |
| D4 secrets in audit log | **fixed** (redaction) |
| D5 CWD-relative log path | open |
| D6 shared `_recalled` / `_last_*` races | open |
| D7 psutil missing | **fixed** (pinned + installed) |
| D8 e2e test wrote to real workspace | **fixed** |
| D9 tests wrote to the real memory journal (retain journals even with `HINDSIGHT_ENABLED=0`) | **fixed for future runs** (`conftest.py` isolates memory + task stores); existing entries: open item 1 |
| D10 voice input dead: PyAudio never installed | **fixed** (pinned + installed) |

## Open items needing the owner

1. **Test entries in the real memory journal.** ≥358 of 815 `journal.jsonl` entries and ≥200 of 401 `pending.jsonl` entries match test-suite commands (all 206 entries dated 2026-10-20 are test runs). Backups: `tom_brain/backups/hindsight-*-20261021-003731.jsonl`. They will be imported into the new local store on TOM's next start unless removed first.
2. ~~Indian-English offline voice~~ **Done 2026-10-21:** `Language.TextToSpeech~~~en-IN` installed (adds Microsoft Heera, female, and Ravi, male). Later the same day the owner switched TOM to **US English**: the default is now **Zira** (female, en-US) at rate 1.15; Heera stays available with `TOM_TTS_VOICE=en-IN`. Verified through `LocalWindowsTTS` and `test_local_voice_round_trip_is_accurate`.
3. **Rotate the Hindsight API key** — it was printed in a session log on 2026-10-21.

## Owner-reported fixes (2026-10-21)

- **Speech capture rewritten** (owner: "it isn't taking all my voice") — `tom_core/voice/capture.py` replaces speech_recognition's 0.8 s-pause / 15 s endpointing: a request ends after 2.5 s of quiet, at 60 s, or when Talk is pressed again. Measured with synthesized speech + noise (`tests/test_voice_capture.py` and a Whisper round trip): mid-sentence pauses, speaking at the press, a noisy room and quiet speech all keep the full request.
- **Voice:** US English female (Zira), 15 % faster; voice-mode replies phrased in US English.
