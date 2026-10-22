# R9 feature security & privacy review (2026-10-22)

Every R9 capability is off by default (`tom_core/features.py`); the acceptance suite is
`tests/test_advanced_features.py`.

| Feature | Flag | What it can do | Risks considered | Controls |
|---|---|---|---|---|
| Watchers (C11) | `TOM_WATCHERS=1` | Read disk free, RAM use, blocked tasks every 5 min; add a notice | Noise; acting on its own (killing processes) | Notify on appear/clear only; observe-only, never kills or deletes (RRM-008); broken watcher stays silent. Thresholds `TOM_WATCH_DISK_FREE_GB`, `TOM_WATCH_RAM_PCT` |
| Workflow learning (C12) | `TOM_WORKFLOWS=1` | Save the last plan as a workflow, run it later with new inputs | Replaying an action the user never reviewed; injected steps | Saved as **draft**; runs only after "approve workflow X" (the user sees every step and argument first); runs through the normal executor, so policy, approvals, taint rule and checkpoints all apply; unknown inputs refused |
| Cloud escalation (RRM-007) | `TOM_CLOUD_ESCALATION=1` + `GROQ_API_KEY` + `TOM_CLOUD_DATA_POLICY` + `TOM_CLOUD_DAILY_LIMIT` | Send one request to the cloud model when local inference failed after its one retry | Personal data leaving the PC; cost | All four settings required; `no-personal-data` keeps requests mentioning files, email, contacts, memories, paths local; daily request cap counted in `tom_brain/cloud_usage.json` |
| Remote access | — | **Not implemented** | Unauthenticated control of the PC | TOM opens no listening socket; `test_tom_opens_no_network_listener` fails the build if one appears. Adding it needs authenticated, encrypted transport and its own review |

Specialist agents (C10) are reviewed in `tool-permissions.md` §4 (tool grants per role).
