# Architecture Decision Records — TOM refactor

Status values: **Proposed** (awaiting owner approval at the R0 gate) · **Accepted** · **Superseded**.

---

## ADR-001 — Brownfield strangler migration, not a rewrite
**Status:** Accepted (mandated by PRD §S1/§S8)
**Context:** 54 k lines of working code and 453 passing tests. The PRD's §12.3 layout (`src/jarvis/...`) is a greenfield suggestion.
**Decision:** New core code grows beside `agent.py`. `execute_task()` stays as a compatibility facade until every caller is migrated (TOM-MIG-002).
**Consequence:** For several phases there are two layers: legacy handlers wrapped by new contracts.

## ADR-002 — New core package is `tom_core/`, not `src/jarvis/`
**Status:** Proposed
**Context:** §S8 says the product name is undecided and JARVIS is only a codename. The repo uses flat top-level packages (`tools/`, `safety/`, `agents/`), and PyInstaller's spec and tests import them from the repo root.
**Decision:** Use a top-level `tom_core/` package (no `src/` layout) so existing imports, `tests/conftest.py` path setup and the PyInstaller spec keep working. Branding stays in config. A rename is an R10 task.
**Alternative rejected:** a `src/` layout. It would change every import path and the frozen-exe build for no functional gain at this stage.

## ADR-003 — Keep the Tkinter desktop UI; do not port to PySide6 now
**Status:** Proposed
**Context:** PRD §12.4 *suggests* PySide6. `tom_desktop_app.py` is 5,580 lines of working Tkinter with voice window, approvals provider, dashboards and crash hooks. A port is a rewrite of the largest file, with no PRD requirement that Tkinter cannot meet (FR-018 progress, §14 approvals and emergency stop are all feasible in Tk).
**Decision:** Keep Tkinter. Add the PRD §14 elements (task list, approval panel, emergency stop) to it in R2/R8. Revisit only if a concrete requirement cannot be met.

## ADR-004 — SQLite (stdlib `sqlite3`, WAL mode) for task state
**Status:** Proposed (PRD §9.2 and §12.4 already recommend it)
**Decision:** One file at `tom_brain/tasks.sqlite3` (runtime dir, already git-ignored), stdlib `sqlite3`, no ORM. Schema migrations are numbered SQL files with a pre-migration backup copy (§S4, §20).

## ADR-005 — Cloud routes become explicit opt-in, decided by the owner
**Status:** Proposed — **needs owner decision**
**Context (baseline §6):** Inference (Groq), memory (Hindsight Cloud) and ASR (Google) currently all send data off-machine by default. RRM-007 / NFR-006 require cloud to be disabled unless configured with a data-sharing policy.
**Options:** (a) keep current behaviour but disclose each route in the UI; (b) default every route to local and require an explicit `TOM_CLOUD_*` opt-in per route; (c) (b) plus per-task disclosure.
**Recommendation:** (c). The refactor will **not** change these defaults until the owner chooses, because flipping them silently would break the owner's current setup.

## ADR-006 — Policy engine is additive to the legacy keyword gate
**Status:** Proposed
**Decision:** The new deterministic `PolicyEngine` evaluates every tool call. `SafetyGuards.is_action_safe` keeps running on the raw sentence until R10. Either one can block; neither can override the other's block. This keeps the feature flag (`TOM_POLICY_ENGINE=0`) from ever making TOM less safe than the baseline.

## ADR-007 — Characterization tests use the existing stubbed-LLM pattern
**Status:** Accepted
**Decision:** `tests/characterization/` builds a real `TomAgent` with `HINDSIGHT_ENABLED=0`, `TOM_LLM_PROVIDER=ollama`, `understand_command` replaced by the regex parser, `_invoke_llm` stubbed, and an injected approval provider. This is the same pattern as `tests/test_e2e_agent.py`. No network, no model, deterministic.
