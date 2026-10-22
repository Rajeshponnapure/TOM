# Tool Risk Categories, Permissions and Approval Requirements

> PRD §11.3 approval matrix applied to TOM's real tools (R0 inventory). "Today" shows current enforcement;
> "Target" shows what the R3 `PolicyEngine` must enforce. Side-effect counts come from a static scan of
> `subprocess`/`os.system`, file deletes/moves, network clients and UI automation calls.

## 1. Risk classes

| Class | Default policy | Approval |
|---|---|---|
| `OBSERVE` | Automatic within allowlisted scope | none |
| `REVERSIBLE` | Automatic, logged | none |
| `WORKSPACE_WRITE` | Automatic only inside a workspace root, with checkpoint where feasible | none inside workspace; outside → `BLOCKED` |
| `MATERIAL_CHANGE` | Approval or project policy | yes |
| `DESTRUCTIVE_OR_EXTERNAL` | Explicit approval bound to the exact payload | yes, every time |
| `PRIVILEGED` | Narrow tool + explicit approval | yes; not available to autonomous loops |
| `BLOCKED` | Never executed; logged | n/a |

## 2. Tool inventory

| Tool / module | Side effects (scan) | Target class | Today | Gap to close |
|---|---|---|---|---|
| `file_analyzer`, `screen_tools`, `network_tools`, `capability_health`, `knowledge_engine` | read-only / subprocess probes | OBSERVE | no gate needed | add timeouts to probes |
| `os_tools.open_app` | 11 subprocess | REVERSIBLE | keyword gate only | allowlist executable resolution |
| `file_tools` create/write | file writes, 4 delete/move | WORKSPACE_WRITE (write) / DESTRUCTIVE (delete) | delete approval + protected-path check | workspace-root enforcement for writes |
| `file_ops` organize/rename/zip | moves | WORKSPACE_WRITE → DESTRUCTIVE when outside workspace | dry-run plan + approval | none beyond workspace roots |
| `document_creator`, `pdf_tools`, `data_analysis`, `media_engine`, `game_dev`, `vlsi_engine`, `ml_engine`, `agent_builder` | write output files; ffmpeg subprocess | WORKSPACE_WRITE | none | output-path workspace check |
| `code_runner` | subprocess + timeout | WORKSPACE_WRITE | none | command policy (§8.3) |
| `email_tools.send`, `whatsapp_tools`, `chat_apps` | SMTP / HTTP / browser send | DESTRUCTIVE_OR_EXTERNAL | approval on exact message | bind approval to payload hash |
| `browser_tools`, `web_automation`, `web_recipes` | Playwright; downloads | OBSERVE (read) / DESTRUCTIVE_OR_EXTERNAL (submit) | partial | pause-before-submit (§8.2); untrusted content |
| `mcp_manager` connectors | 7 network clients | OBSERVE (read) / DESTRUCTIVE_OR_EXTERNAL (post) | keyword gate | per-connector verb classification |
| `tool_acquirer`, `dependency_manager` | pip/git subprocess (9) | MATERIAL_CHANGE | own approval (acquirer only) | dependency_manager has none |
| `hardware_control` click/type/keys | pyautogui (36) | REVERSIBLE (needs post-check) | **none — called directly from GUI buttons** | route through registry; prefer UIA (§8.1) |
| `plugin_manager` | runs plugin subprocesses | BLOCKED pending review unless allowlisted | none | plugin allowlist |
| `blender_control.execute_script` | **in-process `exec()`** when `bpy` importable | BLOCKED (in-process) / WORKSPACE_WRITE (subprocess mode) | none | remove in-process path |
| `auto_update`, `self_evolution` | subprocess + network; prompt self-modification | PRIVILEGED / DEFER | none | feature-flag off by default (§2.2 non-goals) |
| `email_agent_controller`, `instagram_agent_controller` | start/stop daemons | MATERIAL_CHANGE | keyword gate | approval to start |
| Anything touching firewall, credentials, services, `system32` | — | PRIVILEGED / BLOCKED | `system32` hard-block | explicit privileged tool list |

## 3. Non-negotiables (PRD §11.2, FR-010)

1. The LLM cannot approve its own action. Approvals originate only from `ApprovalManager` providers bound to a UI/CLI.
2. An approval is bound to `sha256(tool, normalized_args)` and expires (default 5 min) or when the payload changes (§S3).
3. No tool may write `config/policies.yaml` or anything under `safety/` or `tom_core/policy/`.
4. Secrets (`*_API_KEY`, `*_PASSWORD`, `*_TOKEN`, bearer tokens, `sk-…`, `gsk_…`) are redacted **before** any log, audit, task-store or export write.
5. Paths are normalized (`os.path.realpath`) before workspace checks, which defeats `..` traversal and symlink escape.

## 4. Enforcement (implemented 2026-10-22, R3)

* Every side effect passes `tom_core.tools.guard.enforce()` → `PolicyEngine.decide()`; the decision and a redacted target are appended to `tom_logs/audit.jsonl`.
* Approvals are recorded in `ApprovalLedger`, bound to the exact payload, single-use, valid 300 s.
* Emergency stop (Qt and Tk **Stop**) calls `get_policy().halt()`: every new tool call is refused until the user's next request.
* Background agents with standing permission (email auto-reply, Instagram report) need their opt-in `.env` flag; nothing else is pre-authorized.
* In-process Blender `exec()` is BLOCKED; plugins and code runs need approval for that exact plugin / file / command.
* Specialist agents only see their granted tools (`ROLE_TOOLS` in `tools/agent_orchestrator.py`); the registry refuses anything else.

