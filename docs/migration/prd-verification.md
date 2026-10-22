# PRD v1.1 verification (2026-10-22)

Every requirement in `TOM_Refactoring_PRD_v1.1.docx`, checked against the code on branch
`refactor/r0-r1-audit-and-characterization`. **Done** = implemented and covered by a test or a measured
live check; **Partial** = the core exists and what is missing is named; **Not built** = deliberately
left out, with the reason.

## Functional requirements

| ID | Status | Evidence / what is missing |
|---|---|---|
| FR-001 Text requests (desktop + CLI) | Done | Tk app, PySide6 app, `main.py`; all through `TaskService` |
| FR-002 Push-to-talk, spoken replies, opt-in wake word | Done | `tom_core/voice/push_to_talk.py`; `TOM_WAKE_WORD` (off by default) — `test_push_to_talk.py` |
| FR-003 Task id, time, state, plan, tool history, outcome | Done | task store + events; planned tasks store their plan and each step (`plan_plan`/`plan_step` events); tool calls in `tom_logs/audit.jsonl` |
| FR-004 Typed steps: deps, expected output, risk, timeout, verification | Done | `Step` (+ `annotate`) — `test_prd_gaps.py`. Preconditions are expressed as dependencies |
| FR-005 Validate schema, permissions, workspace, policy before each call | Done | `ToolRegistry.call` → pydantic → grants → `enforce` |
| FR-006 Pause, cancel, bounded retry | Done | Pause/Resume buttons (both apps) hold every action at the policy gate; cancel + emergency stop; retry ceiling — `test_prd_gaps.py`, `test_durable_execution.py` |
| FR-007 Record tool inputs/outputs, redacted | Done | `guard.audit` / `record_outcome` with `redact` — AT-010 |
| FR-008 Success only when verified | Done | `UNVERIFIED` state, executor marks unverified writes, documents re-opened before success |
| FR-009 Approval for destructive / privileged / material / external | Done | `PolicyEngine` classes + `ApprovalLedger` — `test_no_direct_execution.py`. (TOM has no purchase or credential-change tools; any such command would be a material shell action needing approval.) |
| FR-010 LLM cannot approve itself or change policy | Done | deterministic engine; policy code and config are protected paths |
| FR-011 Workspace allowlist | Done | workspace roots + `TOM_WORKSPACE_ROOTS`; outside needs approval |
| FR-012 Recovery point before high-impact changes | Partial | overwritten files backed up, deletions to Recycle Bin, organize undo journal, git checkpoint before code fixes. Not every tool creates one (e.g. hardware input is classed reversible) |
| FR-013 Durable state, restart reconciliation | Done | SQLite store; orphans → `BLOCKED`; resume never redoes a half-done step — AT-006 |
| FR-014 Observation / reversible / external / privileged | Done | `ActionClass` |
| FR-015 Show plan and confirm when ambiguous or risky | Done | plan preview + one confirmation before multi-change plans; missing details are asked for (WhatsApp text, understanding `missing`) |
| FR-016 Project profiles | Partial | `tom_core/projects.py`: root, language, test/build commands, notes, tool list; "fix the failing tests in <project>" uses them. The stored tool list is not yet enforced as a grant |
| FR-017 Prompt-injection defence | Done | executor taint rule + untrusted-data prompts — AT-011 |
| FR-018 Progress, step, evidence, elapsed, blockers in UI | Done | Qt: progress line, "Working… Ns — step", task timeline with events, blocked tasks listed (and opt-in watcher notices) |
| FR-019 Export task report, redacted | Done | "export task report" → Markdown in the workspace — `test_prd_gaps.py` |
| FR-020 Reusable workflows from approved demonstrations | Done | `tom_core/workflows.py` (draft → approve → run), behind `TOM_WORKFLOWS` |

## Resource rules

| ID | Status | Evidence / what is missing |
|---|---|---|
| RRM-001 Sampling | Done | Qt resource panel every 2 s (CPU, RAM, VRAM) |
| RRM-002 Estimate load cost | Done | `llm_admission.need_mb` (weights + KV + overhead); ASR admission (ADR-009) |
| RRM-003 VRAM reserve | Done | `TOM_VRAM_RESERVE_MB` — AT-008 |
| RRM-004 One GPU-heavy workload | Done | idle models Ollama will swap count as reclaimable; Ollama serialises requests |
| RRM-005 Queue/defer with explanation | Partial | TOM falls back (smaller context/model, stated CPU split) and prints why; it does not hold a task in a queue |
| RRM-006 Unload, idle timeout, fallback | Done | Ollama keep-alive (`TOM_OLLAMA_KEEP_ALIVE`), fallback model, cloud gate |
| RRM-007 Cloud off unless key + policy + limit | Done | `tom_core/resources/cloud.py` — `test_advanced_features.py` |
| RRM-008 No automatic process killing | Done | watchers observe only; no auto-kill code path |
| RRM-009 Latency, tok/s, load, memory, quality | Done | `tests/manual/benchmark_llm.py` → `docs/benchmarks/llm-profiles.md` |
| RRM-010 Per-task resource budget | Partial | time budget per plan (600 s) and per tool timeouts; no CPU/RAM/disk budget per task |
| RRM-011 Core works when inference fails | Done | task store, policy and scheduler run without a model (the test suite runs with no model) |
| RRM-012 Measured capacity | Done | admission uses measured free VRAM |

## Capabilities

| ID | Status | Evidence / what is missing |
|---|---|---|
| C01 Computer control | Done | apps, UI Automation (WhatsApp), keyboard/mouse (gated), screenshots |
| C02 Voice | Partial | push-to-talk, interruptible TTS, opt-in wake word, female US-English voice. ASR is not streaming (recognised after you stop); only English has been measured |
| C03 Software engineering | Done | git tools, read-only shell, test-fixing workflow with checkpoint, diff and rollback — AT-013 |
| C04 File intelligence | Done | file analysis, organize with undo, duplicate finder (content hash) |
| C05 Browser agent | Partial | Playwright web automation and research; external side effects need approval. Authenticated sessions are not managed |
| C06 Memory | Done | provenance, confidence, retention, correct/forget (chat + both apps) — AT-015 |
| C07 Resource manager | Done (see RRM-005/010) | |
| C08 Planner/executor | Done | typed plans, deps, retries, timeouts, cancel, pause, checkpoints, verification, honest report |
| C09 Diagnostics | Done | processes, resources, services, event log, DNS, ports, runtimes |
| C10 Specialists | Done | role tool grants (`ROLE_TOOLS`) |
| C11 Watchers | Done | opt-in, change-only notices |
| C12 Workflow learning | Done | draft/approve/run |
| C13 Business productivity | Done | professional Word/PDF/PowerPoint/Excel (`tom_core/documents`), email drafts, sends need approval |
| C14 Cloud & infrastructure | Partial | git, Docker/WSL detection; no deployment tooling |
| C15 IoT | Partial | firmware/code generation (ESP32, Arduino, MQTT); no live device control |
| C16 Multi-device access | Not built | security: TOM opens no network port (`test_tom_opens_no_network_listener`); needs authenticated, encrypted transport and its own review first |
| C17 Preflight/simulation | Done | plan preview with affected paths and rollback; code fixes roll back on failure |
| C18 Self-evaluation | Done | "self evaluation": success rate, failure categories, proposals |

## Non-functional requirements

| ID | Status | Evidence |
|---|---|---|
| NFR-001 Availability | Done | core runs without a model; RRM-011 |
| NFR-002 Responsiveness | Done | agent on its own thread; UI never blocks on models or `nvidia-smi` |
| NFR-003 Latency | Measured | understanding 8–13 ms for clear requests; 3B model 105 tok/s; deck 15–30 s, report 25–40 s |
| NFR-004 Reliability | Done | durable task store, bounded retries, resume-safe reconciliation |
| NFR-005 Security | Done | least privilege, approvals, audit, protected paths, no listener |
| NFR-006 Privacy | Done | local-first; cloud strictly opt-in |
| NFR-007 Resource safety | Done | VRAM admission, OOM fallback |
| NFR-008 Maintainability | Done | `tom_core/` packages per concern |
| NFR-009 Testability | Done | full suite (see `status.md`) |
| NFR-010 Observability | Done | audit log, task timelines, task reports |
| NFR-011 Portability | Partial | Windows-first by design (UI Automation, SAPI/WinRT voices) |
| NFR-012 Accessibility | Partial | keyboard shortcuts (Ctrl+Space talk, Ctrl+. stop, Enter send); no screen-reader audit yet |

## Acceptance tests

All PRD acceptance tests AT-001 … AT-015 pass — see `status.md`.
