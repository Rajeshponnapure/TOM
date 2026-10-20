# TOM — Target-State Architecture

> Source: PRD v1.1 §12 + Refactoring Supplement §S3/§S4, adapted to what the R0 audit found
> (see `current-state.md`). Decisions that deviate from the PRD's *suggested* implementation are recorded in
> `docs/migration/decisions.md`.

## 1. Principle

Strangler migration. A new core package grows **beside** `agent.py`; `TomAgent.execute_task()` becomes a
compatibility facade that delegates into it. Existing handlers in `agent.py` and `tools/*` keep working and are
moved behind typed tool adapters one at a time (R7). Nothing is rewritten clean-room.

## 2. Components and contracts

The new code lives in a neutral package, `tom_core/` (the product name is undecided, see ADR-002).

```text
interfaces (main.py CLI · tom_desktop_app.py GUI · voice)          ← unchanged launchers
        │  submit_task / get_task / pause_task / cancel_task / approve_action
        ▼
tom_core.tasks.TaskService ──► tom_core.tasks.TaskStore (SQLite, WAL)       source of truth for status
        │                       tom_core.tasks.state (state machine, PRD §13)
        ├─► Planner            (structured plan; no side effects)
        ├─► Executor ──► tom_core.tools.ToolRegistry (Pydantic arg schemas, timeouts, evidence)
        │                    │
        │                    └─► tom_core.policy.PolicyEngine  (deterministic; risk class; workspace rules)
        │                            └─► tom_core.policy.ApprovalService (payload-hash bound, expiring)
        ├─► Verifier           (success only with evidence, FR-008)
        ├─► tom_core.memory.MemoryPort ──► HindsightAdapter (wraps tools/hindsight_memory.py)
        └─► tom_core.models.ModelGateway ──► OllamaAdapter | GroqAdapter (wrap tools/llm_factory.py)
                                   └─► tom_core.resources.Admission (VRAM/RAM measured budget)
tom_core.observability.redact   applied to every log / audit / export write
```

| Boundary | Contract | Phase |
|---|---|---|
| Interface → TaskService | `submit_task(text, interface) -> TaskRecord`, `get_task(id)`, `pause_task`, `cancel_task`, `approve_action(approval_id, decision)` | R2 |
| TaskService → TaskStore | append-only events + current state row; `recover()` on start marks `RUNNING`/`AWAITING_APPROVAL` as `BLOCKED(needs_reconciliation)` | R4 |
| Executor → ToolRegistry | `ToolRequest{tool, args, task_id}` → `ToolResult{status, evidence, error_class, duration}` | R3 |
| ToolRegistry → PolicyEngine | `evaluate(request) -> Decision{allow \| require_approval \| deny, risk, reason}`; the LLM can never call `approve` | R3 |
| TaskService → Memory | `recall(query, scope)`, `retain(record)`; failures return empty and are logged, never raised | R5 |
| ModelGateway → Providers | `generate`, `health`, `load`, `unload`; provider code stays in adapters | R6 |
| ResourceManager → Runtime | `admit(profile) -> Admit \| Defer(reason) \| Fallback(profile)` using *measured* free VRAM minus reserve | R6 |

## 3. Risk classes (PRD §11.3, FR-014)

`OBSERVE` → `REVERSIBLE` → `WORKSPACE_WRITE` → `MATERIAL_CHANGE` → `DESTRUCTIVE_OR_EXTERNAL` → `PRIVILEGED` → `BLOCKED`.
Each tool declares a class; the policy engine may only *raise* it based on arguments (e.g. a write outside the
workspace → `BLOCKED` unless separately authorized). See `docs/security/tool-permissions.md`.

## 4. Trust boundaries

1. **User ↔ interfaces** — the only place approvals originate (GUI dialog / CLI prompt). Never from model output.
2. **Core ↔ model** — model output is untrusted data. It may *propose* tool calls; the registry validates them.
3. **Core ↔ content** — web pages, files, repo content, tool output are untrusted (FR-017); they cannot change policy.
4. **Machine ↔ cloud** — Groq inference, Hindsight Cloud, Google ASR. Each route must be disclosed and opt-in (RRM-007, §7).
5. **Policy files** — `config/policies.yaml` is read at start-up only; no tool can write to it (§11.2 "Policy integrity").

## 5. Interface strategy

- Keep Tkinter (ADR-003). The GUI's ~90 direct engine calls migrate to `TaskService.submit_task(..., tool=...)`
  in R7 so they get policy + audit; until then they are listed as known bypasses (TOM-MIG-010 tracked).
- CLI gains `tom task submit|status|cancel|approve|logs` subcommands (FR-001, §14) beside the existing REPL.

## 6. Feature flags (rollback seam, §S4)

| Flag | Default | Effect when `0` |
|---|---|---|
| `TOM_TASK_SERVICE` | `1` after R2 lands | `execute_task` runs the legacy body directly (no task record) |
| `TOM_POLICY_ENGINE` | `1` after R3 lands | Tool calls skip the new engine; legacy keyword gate only |
| `TOM_TASK_STORE` | `1` after R4 lands | In-memory task store; nothing persisted |
| `TOM_RESOURCE_ADMISSION` | `1` after R6 lands | Model loads are not admission-checked |

The legacy keyword gate (`SafetyGuards.is_action_safe`) stays **in addition to** the new engine until R10, so
turning a flag off never makes TOM less safe than it is today.
