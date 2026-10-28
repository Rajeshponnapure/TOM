# Rollback and Data-Recovery Runbook

Applies to every refactor phase (PRD §S4 "preserve a rollback path", TOM-MIG-007).

## 0. Before any phase

```powershell
git switch -c refactor/<phase>-<topic>          # one branch per phase
git tag pre-<phase> HEAD                        # e.g. pre-R2
Copy-Item -Recurse tom_brain "tom_brain.bak-$(Get-Date -f yyyyMMdd-HHmm)"   # runtime state incl. Hindsight journal/queue
.venv311\Scripts\python -m pytest -q tests\characterization   # must be green before and after
```

Hindsight Cloud data is not stored locally. Do not run bulk memory migrations until a `reflect`/export of the bank is
saved (§S4 "Existing Hindsight memory must not be discarded").

## 1. Fast rollback: feature flags (no code change)

| Phase | Flag in `.env` | Restores | Status |
|---|---|---|---|
| R2 | `TOM_TASK_SERVICE=0` | `execute_task` runs the legacy body directly | implemented, tested |
| R4 | `TOM_TASK_STORE=0` | in-memory tasks, no SQLite writes | implemented, tested |
| R3 | `TOM_POLICY_ENGINE=0` | legacy keyword gate only (ADR-006: never weaker than baseline) | not built yet |
| R6 | `TOM_RESOURCE_ADMISSION=0` | model loads not admission-checked | not built yet |

Cloud routes (ADR-005) are restored per route, not by a single flag:
`TOM_LLM_PROVIDER=groq`, `HINDSIGHT_BASE_URL=https://api.hindsight.vectorize.io`,
`VOICE_RECOGNITION_ENGINE=google`, `TOM_TTS_ENGINE=edge`. The pre-change `.env` is in
`tom_brain/backups/env-before-r2-*.bak`, and the pre-change package set in `tom_brain/backups/pip-freeze-before-r2-*.txt`
(`pip install -r` that file to restore it exactly).

Voice: `TOM_ASR_DEVICE=cpu` keeps speech recognition off the GPU; `TOM_TTS_ENGINE=sapi` uses the old pyttsx3 voice.

Restart TOM after changing `.env`.

## 2. Code rollback

```powershell
git switch main                     # or the last good branch
git log --oneline pre-<phase>..     # review what is being dropped
git reset --hard pre-<phase>        # only on the phase branch, never on main
```

## 3. Database rollback (R4 onward)

1. Stop TOM.
2. `tom_brain/tasks.sqlite3` is copied to `tom_brain/backups/tasks-<schema_version>-<timestamp>.sqlite3` automatically before each migration.
3. Restore: copy the backup over `tasks.sqlite3`, set `TOM_TASK_STORE=0` if the code is also being rolled back, then restart.
4. Verify: `python -c "import sqlite3;print(sqlite3.connect('tom_brain/tasks.sqlite3').execute('pragma integrity_check').fetchone())"` prints `('ok',)`.

## 4. Verifying a rollback

- `pytest -q tests/characterization` is green (TOM-MIG-008).
- `python main.py` → `status` returns the health report; `memory status` shows the same bank id as before.
