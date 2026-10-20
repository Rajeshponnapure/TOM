# Refactor Status (PRD v1.1 supplement §S5)

| Phase | State | Evidence |
|---|---|---|
| R0 Repository audit | **Done — awaiting owner approval** | `docs/architecture/current-state.md`, `target-state.md`, `module-matrix.csv`, `baseline.md`, `decisions.md`, `docs/security/tool-permissions.md`, `docs/runbooks/rollback.md` |
| R1 Characterization tests | **Done** | `tests/characterization/` — 18 pass + 3 strict-xfail gap trackers, ~9 s, offline. Full suite after R1: 471 pass / 15 skip / 3 xfail, 0 fail (227.9 s). Fixed e2e isolation leak D8 |
| R2 Shared task facade | Not started (blocked on R0 approval) | — |
| R3 Policy + typed tools | Not started | — |
| R4 Durable task state | Not started | — |
| R5–R10 | Not started | — |

## R0 exit gate: decisions the owner must make

1. **ADR-005 cloud routes:** keep Groq / Hindsight Cloud / Google ASR as defaults, or make each opt-in? (Recommendation: opt-in + per-task disclosure.)
2. **ADR-002** `tom_core/` package name and flat layout.
3. **ADR-003** keep Tkinter instead of porting to PySide6.
4. **Module matrix:** confirm the REPLACE/DEFER rows (`auto_scaler`, `auto_update`, `self_evolution`, `rag_memory`, `agent_orchestrator`, `iot_engine`).
5. **`.env` cleanup** (D2/D3): remove the duplicate `TOM_LLM_PROVIDER` line; set `OLLAMA_*_MODEL` to an installed model.

## Gap trackers (strict xfail — they flip when delivered)

| Test | Requirement | Closing phase |
|---|---|---|
| `test_every_result_carries_a_task_id` | FR-003 | R2 |
| `test_blocked_results_carry_a_status` | result contract | R2 |
| `test_secrets_never_reach_the_audit_log` | TOM-MIG-009 / AT-010 | R3 |

## Acceptance-test coverage today

| PRD test | Status |
|---|---|
| AT-003 Approval gate | Characterized for delete (declined → untouched, asked once); also `tests/test_e2e_agent.py` for email |
| AT-010 Secret redaction | **Failing** (gap tracker above) |
| TOM-MIG-001 Interface parity | Seam characterized (CLI, desktop chat, desktop voice all reach `execute_task`); GUI engine buttons are a known bypass |
| TOM-MIG-008 No regression | Full suite baseline 453 pass / 15 skip |
| All others | Not yet implementable (need R2–R6) |
