# TOM — Current-State Architecture (R0 audit)

> Audit date: 2026-10-20 · Baseline commit: `4dd8da7` · Branch: `refactor/r0-r1-audit-and-characterization`
> Scope: PRD v1.1 Refactoring Supplement §S2 / §S7. This describes TOM **as it is**, not as the PRD wants it.
> Every claim below was checked against the source at the commit above; line numbers refer to that commit.

## 1. Size and shape

| Area | Files | Lines (approx.) |
|---|---|---|
| `agent.py` — `TomAgent`, the whole brain | 1 | 3,698 |
| `tom_desktop_app.py` — Tkinter GUI + voice UI | 1 | 5,580 |
| `main.py` — CLI REPL | 1 | 220 |
| `tools/` — capability modules | 72 | ~37,000 |
| `safety/guards.py` — keyword safety gate + audit log | 1 | 674 |
| `agents/` — email + Instagram background daemons | 7 | — |
| `tests/` — pytest suite | 40 | 453 pass / 15 skip, 10 min wall-clock |

## 2. Entry points (interfaces)

| Interface | File | How it reaches the brain |
|---|---|---|
| CLI | `main.py:163` | `await tom_agent.execute_task(user_input)` wrapped in `asyncio.wait_for(TASK_TIMEOUT_SECONDS)` |
| CLI voice mode | `main.py:96` | `voice_tools.start_conversation_mode(process_fn=tom_agent.generate_voice_response)` |
| Desktop chat | `tom_desktop_app.py:3630` | `run_coroutine_threadsafe(agent.execute_task(text), self._loop)` on a worker thread |
| Desktop voice window | `tom_desktop_app.py:1149` | `agent.execute_task(heard)` |
| Desktop voice conversation | `tom_desktop_app.py:3458` | `agent.generate_voice_response` |
| Desktop engine buttons | `tom_desktop_app.py:3850–4760` | **Direct calls** to ~16 engines (`HardwareControl`, `MLEngine`, `VLSIEngine`, `IoTEngine`, `NewsAgent`, `BlenderControl`, `MediaEngine`, …) — ~90 call sites, **not** through `execute_task` |
| Desktop file analysis | `tom_desktop_app.py:3683` | `agent.analyze_file(...)` directly |
| Demo / sandbox | `demo/run_demo.py`, `tools/sandbox_functional_tests.py` | `execute_task` |
| Autonomous / orchestrator | `tools/autonomous_agent.py:190–220`, `tools/agent_orchestrator.py` | Re-enter `execute_task` recursively with synthesized commands |
| Background daemons | `agents/email_agent`, `agents/instagram_*` | Separate processes started by `*_agent_controller.py` via `subprocess` |

## 3. The shared execution path — `TomAgent.execute_task()` (`agent.py:763–1304`)

One ~540-line coroutine. In order:

1. **Keyword safety gate** — `SafetyGuards.is_action_safe(command)` matches the *raw command text* against keyword lists (`delete `, `send email`, `pip install`, `system32`, crypto+verb, offensive-security patterns). Returns `safe` / `requires_approval`. Some intents (`email send`, `delete`, `tool acquisition`) defer approval to their own handler to avoid double prompts.
2. **Approval** — `ApprovalManager.request_approval()` (`tools/approval.py`): GUI provider callback if set, otherwise console `input()`, otherwise **deny** (no console under `pythonw`).
3. RAG store of the user message (fire-and-forget, executor thread).
4. **Deterministic meta commands** (`what can you do`, `status`, `show logs`, `voice check`, …).
5. **Hindsight memory** commands / preference capture; `arecall()` starts in parallel with NLP parsing.
6. `understand_command()` → `CommandParser.parse_with_llm()` (LLM call).
7. **Routing cascade** — ~45 `if/elif` branches combining: `EngineRouter.detect()`, `CommandRouter.route()` (keyword → handler name + `needs_approval`), `SkillManager.route_task()`, and the parser's `intent`. Final fallback: universal plan/execute attempt (`task_heuristics.should_attempt_universal`) or `generate_chat_response()`.
8. Post-processing: "Remembering from earlier" annotation, `_retain_outcome()` to Hindsight, skill telemetry, `safety.log_action("COMPLETED", SUCCESS|FAILURE)`, `Learner.log_experience`, chat memory, RAG, `SelfEvolution.record_success`.
9. On exception: error dict, all of the above best-effort.

**Return contract (de facto):** `Dict[str, Any]` with `status ∈ {success, error, cancelled, unsupported, unhandled, blocked…}`, `message`, optional `response_type`, `memories_used`, `experience_id`, `plan`, `content`, `screen_summary`. There is no typed schema.

### Call graph (simplified)

```text
main.py ─┐                         ┌─ SafetyGuards.is_action_safe (keyword)
GUI chat ┼─► TomAgent.execute_task ┼─ ApprovalManager (GUI cb | console | deny)
GUI voice┘        │                ├─ HindsightMemory.arecall / retain  (cloud by default)
                  │                ├─ CommandParser.parse_with_llm ─► llm_factory ─► Ollama | Groq
                  │                ├─ CommandRouter / SkillManager / EngineRouter (routing)
                  │                └─ handler ─► tools/* (subprocess, files, SMTP, Playwright, pyautogui …)
GUI engine buttons ───────────────────────────► tools/* directly   (bypass: no gate, no audit)
AutonomousAgent / AgentOrchestrator ─► execute_task (recursive)
```

## 4. Hidden / global state

- `agent._progress_callback` module global (`set_progress_callback`).
- `TomAgent._last_command / _last_response / _last_exp_id / _last_result / _recalled` — per-agent mutable fields shared by all concurrent tasks. Two concurrent `execute_task` calls overwrite each other's `_recalled`.
- Singletons: `get_memory()`, `get_rag()`, `get_evolution()`, `get_scheduler()`, `get_mcp_manager()`, `knowledge_engine.get_engine()`.
- `SafetyGuards.log_file` is `os.path.join(os.getcwd(), "tom_logs", …)` — **depends on the process CWD**, not the project root.
- `.env` is loaded by `main.py` and the GUI; `llm_factory.persist_provider()` rewrites `.env` at runtime.

## 5. Task state

- **No task ID, no task object, no persisted task state.** A task exists only as a coroutine. A restart loses in-flight work with no record of it.
- Cancellation: GUI cancels the `concurrent.futures.Future` (`_cancel_active_work`) → `CancelledError` inside the coroutine. Subprocesses already started are not tracked or killed. The CLI has only the timeout.
- `TaskScheduler` (`tools/scheduler.py`) — APScheduler with an in-process fallback; not a durable task store.
- Persistence that does exist: Hindsight journal + offline queue (`tom_brain/hindsight/*.jsonl`), `Learner` experiences, `ChatMemory`, ChromaDB RAG, skill telemetry JSON. No SQLite anywhere in first-party code paths (only `mcp_manager` / `dependency_manager` touch `sqlite3`, for the MCP database connector).

## 6. Policy / safety boundary

- Policy is **keyword matching on the raw user sentence** before routing, plus `CommandRouter.needs_approval`. There is no per-tool-call validation, no argument schema, no workspace allowlist enforced centrally.
- Some handlers carry their own checks: `SafetyGuards.check_file_path_safe`, `is_protected_from_deletion` (used by delete), `tool_acquirer` approval, `email send` approval on the exact message, `file_ops` dry-run plan + approval.
- Bypasses: GUI engine buttons (incl. `HardwareControl.click/type_text/press_key`), `generate_voice_response` chat branch (LLM only, no side effects, but no gate/audit), recursive `AutonomousAgent` calls (re-gated by keyword on synthesized text).
- `BlenderControl.execute_script` runs `exec(script)` **in-process** when `bpy` is importable (`tools/blender_control.py:526`).
- Audit log `tom_logs/safety_log.txt` stores the **raw command text** — no redaction at write time (masking only happens when displayed via `show logs`, `agent.py:3435`).

## 7. Model / inference layer

- `tools/llm_factory.py` — provider = `TOM_LLM_PROVIDER` (`ollama` | `groq`); if unset, **Groq is chosen automatically whenever `GROQ_API_KEY` exists** (cloud by default when a key is present).
- Four model slots (`primary`, `fast`, `code`, `embed`) resolved against installed Ollama models with fallback.
- No resource admission, no VRAM estimate, no unload policy. `auto_scaler.py` reads `nvidia-smi` for reporting only and is not wired into inference.
- Model calls are time-boxed (`OLLAMA_TIMEOUT_SECONDS`, default 120 s).

## 8. Memory

| Store | Module | Location | Leaves machine? |
|---|---|---|---|
| Long-term (preferences, corrections, outcomes) | `hindsight_memory.py` | Hindsight Cloud (default) or self-hosted; local journal `tom_brain/hindsight/journal.jsonl`; offline queue `pending.jsonl` | **Yes** when `HINDSIGHT_API_KEY` is set (Cloud default URL) |
| Semantic conversation | `rag_memory.py` | ChromaDB under `tom_brain/` | No |
| Chat transcript | `chat_memory.py` | local JSON | No |
| Experiences / rewards | `learning.py`, `self_evolution.py` | local JSON | No |

Hindsight failure isolation is already good: calls are time-boxed on a single dedicated thread, failures degrade to "no memory", retains queue to disk offline (`hindsight_memory.py` header, lines 13–24).

## 9. Voice

- `tools/voice_tools.py` (SpeechRecognition + pyttsx3/edge-tts, pygame→ffplay→PowerShell playback chain) and `tools/voice_enhanced.py` (2,007 lines).
- ASR engine from `VOICE_RECOGNITION_ENGINE` — currently `google` in `.env` (**cloud ASR; audio leaves the machine**).
- No push-to-talk-first policy, no adapter interface separating capture / VAD / ASR / TTS.

## 10. Known defects found during the audit

| # | Location | Defect |
|---|---|---|
| D1 | `tom_desktop_app.py:5534` | `_on_web_link_analyze_callback` guards on `hasattr(self.agent, "process_message")`; `TomAgent` has no such method, so the forward is a silent no-op. |
| D2 | `.env` | `TOM_LLM_PROVIDER` is defined twice (`ollama`, then `groq`); the later value wins, so the effective route is cloud. |
| D3 | `.env` | `OLLAMA_MODEL / FAST / CODE = llama3.2:3b`, which is **not installed**; every start relies on fallback resolution. |
| D4 | `safety/guards.py:91` | Raw commands (may contain secrets) are written to the audit log unredacted. |
| D5 | `safety/guards.py:58` | Log path depends on `os.getcwd()`; launching from another directory scatters logs. |
| D6 | `agent.py` | Per-instance `_recalled` / `_last_*` fields race under concurrent tasks. |
| D8 | `tests/test_e2e_agent.py` | The fixture did not isolate `TOM_WORKSPACE_DIR` or stub `FileTools.open_file`. The "draft a note…" case wrote `document.docx` into the user's real `Desktop\TOM Workspace` and launched Word via `os.startfile`. Word then held the pytest temp dir open and broke the next run (161 errors). **Fixed in R1** (test-only change). The case still takes ~46 s and needs a follow-up. |
| D7 | `requirements.txt` | `psutil` is neither pinned nor installed in `.venv311`, so `auto_scaler` resource readings silently degrade (`_HAS_PSUTIL = False`). |
