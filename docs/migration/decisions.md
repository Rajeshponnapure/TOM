# Architecture Decision Records — TOM refactor

Status values: **Proposed** (awaiting owner approval at the R0 gate) · **Accepted** · **Superseded**.

---

## ADR-001 — Brownfield strangler migration, not a rewrite
**Status:** Accepted (mandated by PRD §S1/§S8)
**Context:** 54 k lines of working code and 453 passing tests. The PRD's §12.3 layout (`src/jarvis/...`) is a greenfield suggestion.
**Decision:** New core code grows beside `agent.py`. `execute_task()` stays as a compatibility facade until every caller is migrated (TOM-MIG-002).
**Consequence:** For several phases there are two layers: legacy handlers wrapped by new contracts.

## ADR-002 — New core package is `tom_core/`, not `src/jarvis/`
**Status:** Accepted (owner, 2026-10-21)
**Context:** §S8 says the product name is undecided and JARVIS is only a codename. The repo uses flat top-level packages (`tools/`, `safety/`, `agents/`), and PyInstaller's spec and tests import them from the repo root.
**Decision:** Use a top-level `tom_core/` package (no `src/` layout) so existing imports, `tests/conftest.py` path setup and the PyInstaller spec keep working. Branding stays in config. A rename is an R10 task.
**Alternative rejected:** a `src/` layout. It would change every import path and the frozen-exe build for no functional gain at this stage.

## ADR-003 — Keep the Tkinter desktop UI, and add a PySide6 UI beside it
**Status:** Accepted (owner, 2026-10-21: "keep my UI and also create a PySide6 too")
**Context:** PRD §12.4 *suggests* PySide6. `tom_desktop_app.py` is 5,580 lines of working Tkinter; a port would be a rewrite of the largest file.
**Decision:** Keep the Tkinter app unchanged as an interface. Build a second desktop interface in PySide6 (`tom_core/interfaces/qt_app.py`, launched by `tom_qt_app.py` / `launch_tom_qt.bat`) as a pure TaskService client: task list across all interfaces, timeline, approvals dialog, resource panel, privacy panel, push-to-talk, emergency stop (PRD §14). Neither UI has its own agent logic (§12.2).
**Amendment (owner, 2026-10-21):** the Tkinter voice mode now uses the same push-to-talk as the PySide6 app (`tom_core/voice/push_to_talk.py`): the sidebar button, the chat 🎤 button, `Ctrl+Space` and the Voice window each take one request per press and run it as a `voice` task. The Voice window keeps the continuous loop as "Hands-free". The old sidebar voice mode (`VoiceTools.start_conversation_mode` + `generate_voice_response`, which skipped TaskService for most requests) is no longer reachable from the UI. `Ctrl+V` no longer toggles voice; it fired on every paste.

## ADR-004 — SQLite (stdlib `sqlite3`, WAL mode) for task state
**Status:** Proposed (PRD §9.2 and §12.4 already recommend it)
**Decision:** One file at `tom_brain/tasks.sqlite3` (runtime dir, already git-ignored), stdlib `sqlite3`, no ORM. Schema migrations are numbered SQL files with a pre-migration backup copy (§S4, §20).

## ADR-005 — Every cloud route is explicit opt-in; local is the default
**Status:** Accepted (owner, 2026-10-21: "use opt in if that means using local ones")
**Context (baseline §6):** Inference (Groq), memory (Hindsight Cloud), ASR (Google) and TTS (edge-tts) all sent data off-machine by default. RRM-007 / NFR-006 require cloud to be disabled unless configured.
**Decision — per route, the opt-in is choosing the cloud engine explicitly; a credential alone never opts in:**

| Route | Default (local) | Opt-in |
|---|---|---|
| LLM | Ollama, installed models only (`qwen3:8b` for every chat slot) | `TOM_LLM_PROVIDER=groq` (GUI toggle sets it) |
| Memory | SQLite store `tom_brain/hindsight/memory.sqlite3`, seeded from the journal | `HINDSIGHT_BASE_URL=https://api.hindsight.vectorize.io` |
| Speech-to-text | faster-whisper `large-v3-turbo` from `C:\voice-agent-data\cache\huggingface\hub` | `VOICE_RECOGNITION_ENGINE=google` (uses `en-IN`) |
| Text-to-speech | Windows voices; female US English (owner, 2026-10-21): Zira, rate 1.15 | `TOM_TTS_ENGINE=edge` (`en-US-JennyNeural`, +15%) |

`tom_core/privacy.py` reports the live routing; it is shown in "system status" and the PySide6 privacy panel.
**Supersedes:** the earlier llm_factory rule "Groq whenever GROQ_API_KEY is set" (tests updated accordingly).

## ADR-006 — Policy engine is additive to the legacy keyword gate
**Status:** Proposed
**Decision:** The new deterministic `PolicyEngine` evaluates every tool call. `SafetyGuards.is_action_safe` keeps running on the raw sentence until R10. Either one can block; neither can override the other's block. This keeps the feature flag (`TOM_POLICY_ENGINE=0`) from ever making TOM less safe than the baseline.

## ADR-007 — Characterization tests use the existing stubbed-LLM pattern
**Status:** Accepted
**Decision:** `tests/characterization/` builds a real `TomAgent` with `HINDSIGHT_ENABLED=0`, `TOM_LLM_PROVIDER=ollama`, `understand_command` replaced by the regex parser, `_invoke_llm` stubbed, and an injected approval provider. This is the same pattern as `tests/test_e2e_agent.py`. No network, no model, deterministic.

## ADR-008 — `UNVERIFIED` terminal task state
**Status:** Accepted
**Context:** FR-008 forbids marking a task successful without verified success criteria, but the legacy handlers report `status: success` without evidence.
**Decision:** TaskService maps legacy success to `SUCCEEDED` only when the result carries `verified: True` or is a pure observation (chat answer, status report, memory recall — delivering the answer *is* the criterion). Every other success becomes `UNVERIFIED`, shown distinctly in the UI (PRD §14 "unverified steps"). Handlers graduate to `SUCCEEDED` as R7 adds verification to each tool adapter.

## ADR-009 — Speech engines run in worker processes
**Status:** Accepted
**Context (measured 2026-10-21):** importing WinRT speech before onnxruntime, torch or CTranslate2 crashes the process with an access violation; TomAgent itself crashes that way. A Whisper model takes ~4 s to load and should stay warm.
**Decision:** ASR (faster-whisper) and TTS (WinRT) each run in a JSON-lines worker process (`tom_core/voice/workers.py`): crash isolation, one warm model, restart-once on failure, `HF_HUB_OFFLINE=1` so a worker can never download a model. GPU use for ASR is admitted from *measured* free VRAM minus a 1.5 GB reserve; otherwise CPU; a failed CUDA load falls back to CPU once (PRD §6.3). The speech model is released when a voice session ends (RRM-006). CUDA 12 cuBLAS is borrowed from Ollama's install unless `TOM_CUDA_LIB_DIR` says otherwise — fragile across Ollama updates; the CPU fallback covers that case.

## ADR-010 — Local memory implements the Hindsight client surface
**Status:** Accepted
**Decision:** `tom_core/memory/local_store.py` implements `create_bank / retain / recall / reflect / list_memories` over SQLite FTS5 (porter stemming), so `tools/hindsight_memory.py` (journal, offline queue, time-boxing, rules) is unchanged. It is seeded once from `journal.jsonl`; seeding never edits the journal. `reflect` has no LLM: it returns stored preferences/corrections newest-first and no structured output — callers already fall back to deterministic rule parsing.
