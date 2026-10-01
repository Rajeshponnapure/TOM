# Changelog

All notable changes to TOM. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **Network & device diagnostics engine (`tools/network_tools.py`, routed via `engine_router` as the
  `network` key).** The legitimate realization of "show me the devices on my wifi / my network info":
  `list_devices` (ARP table of the local subnet), `wifi_status` + `wifi_profiles` (own machine, via
  `netsh`), `network_overview` (hostname/IPs), and `scan_ports` — a TCP connect scan **restricted to
  loopback/private-LAN targets** (`_is_private_host`), refusing arbitrary public hosts. No attack
  tooling (no WiFi-password cracking, deauth, or device takeover — those can't be runtime-constrained
  to systems the user owns). Subprocess calls use arg lists (never `shell=True`), time out, and decode
  UTF-8 with `errors="replace"` so `netsh`'s non-cp1252 bytes never crash the reader thread. Registered
  in `capability_registry` (`network`), tests in `tests/test_network_tools.py`.
- **Tool acquisition (`tools/tool_acquirer.py`; `agent.execute_tool_acquisition`).** Acquire a
  capability TOM lacks: `install_package` (`pip install` into the venv, strict name validation so no
  shell metacharacters reach pip, approval-gated), `clone_repo` (shallow-clone + read-only inspect of a
  public repo from an allowlisted host — github/gitlab/bitbucket/codeberg/sr.ht over https; the repo is
  never run or installed), and `save_tool` (write an LLM-scaffolded module into the workspace for
  review, not imported/executed). Routed via `_is_acquire_tool_request`/`_extract_package`/
  `_scaffold_tool`, approval-gated for install/clone. Deliberately does not download-and-run untrusted
  code. Registered in `capability_registry` (`tool_acquire`), tests in `tests/test_tool_acquirer.py`.
- **Workspace isolation — TOM now builds user deliverables *outside* its own repo.** Websites, code
  scaffolds, documents, decks and reports were being written into the TOM install (`output/`, or the
  current working dir for `--- FILE: … ---` scaffolds), polluting the app folder. Added workspace
  routing in `tools/project_paths.py` (`workspace_root()` → `<Desktop>/TOM Workspace`, overridable via
  `TOM_WORKSPACE_DIR`; `resolve_deliverable_dir`/`resolve_deliverable_path`; honours an explicit
  absolute path named in the request). `FileTools.output_dir` and `document_creator.OUTPUT_DIR` now
  point at the workspace; `create_website` takes a `target_root`; `agent.py` resolves every
  `--- FILE: … ---` entry under a per-project workspace sub-folder (`_deliverable_target`/`_place_in`)
  and extracts an explicit target path from the command (`_extract_target_dir`). Tests in
  `tests/test_workspace_and_delete.py`.
- **Guarded delete (`FileTools.delete_path` + `SafetyGuards.is_protected_from_deletion`).** TOM can
  delete a file or folder, but only after showing a warning with exactly what will be removed (type,
  size/file-count) and getting explicit approval; it deletes to the Recycle Bin when `send2trash` is
  available. It refuses — approval or not — to delete the TOM install or anything inside it (stops
  "delete agent.py" self-destructing the app), OS system trees, drive roots, and top-level personal
  folders. Routed in `agent.py` (`_is_delete_request`/`_extract_delete_target`/`execute_delete`), with
  the generic approval gate deferring to the delete executor's richer prompt. Tests included.
- **Presentation themes by name.** Added `gaming`, `gradient`, `floral`, `vibrant`, `dark`, `elegant`,
  `ocean`, `sunset`, `pastel`, `royal` presets (plus alias cues like "bright"→vibrant) to
  `tools/document_creator.py`, with `_resolve_style` + alias map; `_detect_theme` now accepts a plain
  style string. `agent._extract_requested_theme` pulls an explicitly-requested theme from the command
  and overrides the LLM's guess. Tests in `tests/test_ppt_themes.py`.
- **Knowledge acquisition — "learn about X".** `agent.acquire_knowledge` researches a topic on the web
  (reusing `_research_topic`), saves a curated note to `knowledge/acquired_*.md`, and hot-reloads the
  knowledge engine so it is usable immediately; also indexed into RAG. Routed via `_is_learn_request`/
  `_learn_topic`. It writes notes only — it does not download or execute code from the internet. Tests
  in `tests/test_knowledge_acquisition.py`.
- **Defensive security gate (`SafetyGuards.assess_security_request`, wired into `is_action_safe`).**
  Security help is scoped to systems the user owns or is authorised to test. Requests targeting third
  parties, or describing harm/credential theft/detection-evasion, are blocked; own-system/CTF/lab and
  educational-defence requests are allowed but require an authorisation confirmation. Tests in
  `tests/test_security_gate.py`.
- **Real video/photo editing engine (`tools/media_engine.py`) — TOM had zero actual capability here before.**
  `skills/39-media-production-skills.md` is pure reference text about Premiere Pro/DaVinci Resolve/Photoshop,
  but `SkillManager._classify()` had labeled it `tool_backed` against `blender_control` + `os_tools` — neither
  of which can touch a video or photo file. Root cause: naive keyword matching hit "windows" inside "power
  windows" (a DaVinci color-grading term, nothing to do with the Windows OS) and "3d" inside a section
  heading. Built a real engine instead: video editing (trim, concat, format conversion, text/caption overlay,
  audio extraction, resize, color adjustment, volume) via ffmpeg, photo editing (resize, crop, 10 filters
  including sepia/grayscale/blur/sharpen, watermark, format conversion, rotate) via Pillow. Wired into
  `tools/engine_router.py` (new `media` engine key, natural-language detection, `_run_media`) and
  `tools/capability_registry.py` (53/53 capabilities verified, 0 orphans); added a `media_engine` term to
  `SkillManager.TOOL_BACKED_TERMS` so the skill now correctly reflects real backing. Every operation waits for
  completion, checks the exit code, and verifies the declared output file actually exists on disk before
  reporting success — every photo operation was physically run and pixel-checked (dimensions, grayscale
  channel equality, watermark region actually changed); ffmpeg isn't installed on this dev machine, so video
  operations were verified against a faked subprocess covering success, a silent no-op that exits 0 but
  produces nothing, a nonzero exit, and a timeout. Added `tests/test_media_engine.py` (18 cases) and extended
  `tests/test_engine_router_detection.py`. Registered in `tools/preflight.py` (`media` capability: Pillow
  required, ffmpeg optional with a precise install fix message) and documented in `docs/SETUP.md`.
- **`tools/auto_scaler.py` (parallel execution, CPU/RAM-aware worker scaling, load balancing, work sharding —
  22 methods, ~1300 lines) was instantiated at GUI startup with a chat line claiming "Auto Scaler: resource
  management, parallel exec" was active, but not one of its methods was ever called anywhere in the codebase.**
  Wired it into `tools/engine_router.py` (the same natural-language-routing pattern already used for
  ML/IoT/VLSI/hardware/etc.) with a new `scaler` engine key: `detect_resources`, `get_status`,
  `performance_report`, `optimize_workers`, and `simulate_load` are now reachable via chat/CLI (e.g. "auto
  scaler status", "system resources", "simulate load with 20 tasks", "optimal workers for io-bound tasks"),
  registered as a real capability in `tools/capability_registry.py` (52/52 verified, 0 orphans). Wiring it in
  for real immediately surfaced a genuine pre-existing bug that had never been exercised: `simulate_load()`
  appended the bare `_synthetic_task` function (which `parallel_execute` calls with zero arguments) for half
  its synthetic tasks, even though that function requires `(duration, idx)` — every one of those tasks raised
  `TypeError: missing 2 required positional arguments`, invisible until now because nothing ever called this
  method. Fixed to pass matching args like the other half already did. Added
  `test_scaler_still_required_not_orphaned` and `test_scaler_simulate_load_all_tasks_complete` to
  `tests/test_engine_router_detection.py`.

### Fixed
- **Enabling `TOM_INCLUDE_EXTERNAL_SKILLS=1` with no `awesome-claude-skills/` directory silently loaded 0 of
  the advertised "+864 opt-in" skills, with no indication why.** `tools/skill_manager.py::_load_all()` already
  no-opped safely when that directory was missing (no crash), but gave zero feedback either way. Investigated
  the directory itself: it does not exist anywhere in this repo, `.gitignore` documents it only as a
  "vendored third-party repo (has its own .git; not tracked here)", and no commit in this repo's history nor
  any setup doc records which external repository was actually vendored there — a web search turned up at
  least 5 unrelated GitHub projects all named "awesome-claude-skills" with different skill counts, so
  guessing one would be presenting an assumption as fact. Added a clear warning log
  (`[SkillManager] TOM_INCLUDE_EXTERNAL_SKILLS is on but ... does not exist`) when the flag is enabled but the
  directory is absent or empty, so the gap is honest instead of silent, and documented the situation plus the
  manual vendoring steps in `docs/SETUP.md` (new "6b) Optional: external opt-in skills" section). The feature
  defaults off and the 47 bundled local skills are unaffected either way.

### Fixed
- **4 of 26 knowledge base files silently contributed zero content, with nothing anywhere indicating it.**
  `tools/knowledge_engine.py::_load_all()` opened every file with plain `encoding="utf-8"` and swallowed every
  failure with a bare `except: pass`. Two files (`game_dev/core_programming.json`,
  `game_dev/rendering_graphics.json`) carry a UTF-8 BOM that rejects under plain `utf-8`; two others had genuine
  JSON syntax errors — a trailing comma after the last property of an object in
  `cybersecurity/linux_windows_mobile.json`, and a doubled backslash in `game_dev/game_engines.json` that closed
  a string early (`\\"coins\"` instead of `\"coins\"`). `linux_windows_mobile.json` is explicitly what the
  cybersecurity skill tells TOM to load for "deeper domain coverage" on mobile security testing — that coverage
  never actually existed. Switched to `encoding="utf-8-sig"` (handles both BOM and non-BOM files), fixed both
  JSON files, and now logs a warning instead of silently discarding a parse failure. Total loaded sections:
  83 → 97. Added `test_every_knowledge_json_file_on_disk_actually_parses` so a future malformed file fails CI
  instead of silently vanishing.

### Changed
- **Removed needless `chr()`-concatenation obfuscation in `tools/iot_engine.py`.** Five spots spelled out
  ordinary identifiers character-by-character (`arch[chr(100)+chr(101)+...]` for `arch["description"]`, and
  similarly for `"protocol"`, `"backend"`, the `RC522_RST` / `DFPlayer_RX` / `DFPlayer_TX` pin names, and a
  `"result"` dict key) instead of just writing the string. Decoded and confirmed each one is functionally
  identical to the literal — no hidden behavior — but this pattern is a known code-smell that static/malware
  scanners flag, and it serves no purpose in an otherwise plainly-written file. Replaced with the literal
  strings; verified the architecture and pinout generators still produce identical output.

### Fixed
- **"Explain how to send an email" would actually send one; "what is the weather in Paris" would explain TOM's
  own features instead of the weather.** `tools/command_router.py::_is_explanation_request()` (the recently
  added self-explanation feature) had two opposite bugs from one flat pattern list: (1) it excluded ANY
  sentence containing an action verb anywhere, so genuine explanation requests about an action ("explain how
  to send an email", "explain how to create a word document") fell through to actually *performing* that
  action; (2) its generic patterns ("what is", "how do") matched any everyday question, hijacking unrelated
  ones ("what is the weather in Paris", "how do I get to the airport", "what are the ingredients for pasta")
  into TOM explaining itself. Split into unambiguous lead-ins ("explain how ...") that always win regardless
  of action words, and generic phrasings that now require the topic to actually name a TOM feature (memory,
  skill, agent, hindsight, etc.) before triggering. Added `tests/test_command_router_explanation.py` (14 cases)
  and verified the full routing suite still passes unchanged.
- **Queued Hindsight memories could get stuck offline forever, even once Hindsight was reachable again.**
  `tools/hindsight_memory.py::flush_pending()` reads the offline-queue file and deletes it in one step; if that
  hit a momentary Windows file lock (`WinError 32`, "used by another process" — reproduced consistently: a
  real-client test failed 1 run in 3, always on the same `unlink()` line, right after `_queue_pending()` had
  just written that exact file, almost certainly Windows Defender/indexer briefly touching it), the function
  caught the `OSError` and silently gave up for good — this is the *only* place anything re-sends the offline
  queue, so a momentary lock permanently stranded the memory until the next full process restart. Added a
  bounded retry (up to 15 × 0.1s) around the read+unlink; verified with a 25-iteration and then a 15-iteration
  stress test of the exact failure scenario (0 failures in both, versus roughly 1-in-3 before).
- **Multi-agent escalation could hand a failed task to a completely unrelated specialist.**
  `tools/agent_orchestrator.py::_escalate_task()` re-routed a failed task to `other_agents[0]` — whichever
  sub-agent happened to be idle first in dict iteration order — with no regard for whether it fit the task at
  all. Physically reproduced: a coding task's Tech Lead failure escalated to the Marketing Lead, who then
  "successfully" handled a Python bug fix. Escalation now re-scores the remaining idle agents with the same
  keyword relevance used for primary routing and picks the best fit (falling back to the first idle agent only
  when none scores above zero). Added `tests/test_agent_orchestrator.py`.
- **A generated slide could render one bullet per letter instead of one per sentence.**
  `tools/document_creator.py::create_presentation()` is prompted (in `agent.py`) to have the LLM return each
  slide's `content` as a JSON array of bullet strings, but nothing validated the shape before
  `_add_bullet_box()` did `for bullet in bullets[:8]`. When a slide's content came back as a plain string — an
  ordinary LLM deviation, e.g. a paragraph instead of a bullet list — Python iterated it character by character
  ("Welcome" → 7 one-letter bullets). Slide content is now normalized to a list before rendering, and a
  non-dict slide entry no longer crashes the whole deck. Added `tests/test_document_creator.py`.
- **Skill routing was biased toward whichever matching skill sorted first alphabetically.**
  `tools/skill_manager.py`'s `DOMAIN_MAP` gave every keyword match a flat +4.0 regardless of how many skills
  that keyword maps to, so a generic word like "design" (5 UI-ish skills) scored identically to a specific one
  like "database" (1 skill) — any tie fell to the alphabetically/numerically first skill name. "design a
  database schema" and "design a REST API" both routed to `01-ui-ux-design` instead of `06-database-skills` /
  a backend skill. Each keyword's bonus is now split across its own target list (inverse-frequency weighting),
  so a keyword shared across many skills carries proportionally less weight per skill than one that uniquely
  identifies it. Verified a genuinely UI-flavored "design" query still correctly routes to `01-ui-ux-design`.
- **No chart ever displayed in a data-analysis report.** `tools/data_analysis.py::generate_report()` wrote every
  `<img src>` as a path relative to the project root instead of relative to the report's own directory, where
  every chart is actually saved as a sibling file. The reference never resolved in a browser — every HTML report
  TOM has ever generated has had broken chart images. Now uses the bare filename.
- **`generate_report()` could crash outright on an ordinary dataset.** `auto_visualize()` classified `datetime64`
  columns as "categorical" and tried to bar-chart `value_counts()` of raw timestamps, which pandas/matplotlib
  reject with `ValueError: Must supply freq for datetime value` — an unhandled crash for any DataFrame with a
  real (non-string) date column, e.g. anything not freshly round-tripped through CSV text. Datetime columns are
  now excluded from that classification (they already get their own time-series chart), and the chart loop is
  wrapped in the same failure-isolation the rest of the file uses. Added `tests/test_data_analysis.py` — this
  module had zero test coverage, which is how both bugs went unnoticed.
- **Most generated Verilog wouldn't compile.** `tools/vlsi_engine.py`'s header builder never declared `reg` on
  outputs written from inside an `always` block, defaulting them to `wire` — a hard type error on every standard
  toolchain (Icarus, Verilator, Vivado). Affected 11 of 15 default module types (`generate_hdl`, including the
  README's own `create a verilog counter` example) and 16 of 36 RTL library designs (`generate_rtl`). Both
  generators now mark the specific ports that are actually procedurally driven.
- `generate_rtl(..., "cordic")` always raised: a duplicated `elif dt == "cordic":` branch shadowed the real
  implementation, so the function fell through and returned `None`.
- `generate_rtl(..., "booth_multiplier")` always raised: the branch built the Verilog text but never returned it,
  falling through to the next `elif` and returning `None`. Also fixed a missing brace in its reset assignment.
- `generate_rtl(..., "single_port_ram")` generated an unrelated, internally-broken Wallace-tree-multiplier body
  (copy/paste leftover, with mismatched `generate`/`endgenerate`) instead of RAM logic. Replaced with a correct
  single-port RAM.
- **The autonomous agent (`execute autonomous task: ...`) never actually used the LLM.** All five call sites in
  `tools/autonomous_agent.py` (plan, research, execute, verify, reflect) called `self.llm.agenerate([prompt])` —
  the legacy completion-LLM API — against a chat model (`ChatOllama`/`ChatGroq`), which always raised
  `AttributeError: 'str' object has no attribute 'content'`. Caught by a bare `except Exception`, so planning
  silently fell back to one generic subtask, verification silently reported "skipped", and reflection was never
  real — on every single autonomous run. Switched to `llm.ainvoke(prompt)`; verified end-to-end with a mocked LLM.
- `tools/mcp_manager.py`'s SMTP send path opened two unused, unauthenticated `SMTP_SSL` connections to Gmail (and
  never closed either) before the real send logic ran, on every call.
- **~30s added to every TOM startup when Ollama is offline.** `tools/llm_factory.py`'s `ollama_installed_models()`
  only cached a *successful* probe; a failed one was retried on every call. `TomAgent.__init__` calls it up to 8
  times (4 model slots, resolved then instantiated), each paying the full connection timeout. Failed probes are
  now throttled too (10s), cutting a cold, Ollama-offline `TomAgent()` construction from ~36s to ~12s.
- **pytest was writing real data to the configured Hindsight Cloud account.** `tests/test_e2e_agent.py` (31 tests)
  constructed a full `TomAgent()` without disabling or faking long-term memory — the only test file with that gap.
  Every mocked "send email" / "post to Slack" / etc. task ran `HindsightMemory.retain()` for real. Now sets
  `HINDSIGHT_ENABLED=0`, matching every other test file that builds a real agent.
- `tools/sandbox_functional_tests.py`'s fake email tools double was missing `draft_email`, which `agent.py`'s real
  write-email path calls; the diagnostic script's own functional check for that flow was failing.
- Two test helpers compared file paths with `str(Path.relative_to(...))`, which renders with backslashes on
  Windows against hardcoded forward-slash expected values — failing 5 tests on Windows only (silently masked on
  the Linux CI runner). Now uses `.as_posix()`.
- **Emailing a Gmail address failed with "Unknown tool: gmail_info".** Connector keywords were matched anywhere in the
  request, including inside the address, so `name@gmail.com` looked like "use the Gmail connector" (and
  `@slack.com` / `@github.com` addresses reached the Slack / GitHub paths). Routers now ignore email addresses and
  URLs. The connector fallback no longer calls a tool that does not exist; Gmail requests use the email workflows.
  Everyday words such as "issue", "commit", "forecast" and "rain" no longer start GitHub or weather lookups.
- **File requests worked in the wrong folder.** Pointing TOM at an explicit path that merely ended in `Downloads`
  (for example the demo sandbox `...\\sandbox\\Downloads`) organized the user's *real* Downloads folder: the path was
  matched by its last word. Explicit paths are now used exactly as given; only bare names such as "downloads" or
  "my desktop" mean the profile folders. A path or folder that does not exist is reported, never replaced by a
  default, and a request that names no folder now asks instead of assuming Downloads.
- **Nothing was being saved to Hindsight.** The Hindsight client binds its HTTP session to the thread that first used it,
  and TOM called it from several threads, so background saves failed with "Timeout context manager should be used
  inside a task" and piled up in the offline queue (the Memory screen showed "0 stored"). All Hindsight calls now run
  on one dedicated thread, and queued memories are sent automatically on the next start.
- TOM said "Saved to long-term memory" whenever memory was merely configured. It now says so only after Hindsight
  accepted the memory; otherwise it says it is *not* saved yet and why. The Memory screen and status line show the
  number of waiting memories, failed saves and a readable reason (for example `HTTP 401 ... check HINDSIGHT_API_KEY`).
- "Revert what you just did" reverts the most recent organization wherever it happened (it used to assume Downloads).

### Added
- **`filesystem` and `database` MCP connectors** (`tools/mcp_manager.py`). Both were documented in this file's own
  module docstring and in the README's "Built-in MCP connectors" list, but neither was ever implemented — calling
  either always failed with "No connector 'filesystem'/'database'". `filesystem` provides `read_file`/`write_file`/
  `list_directory`, routed through the same protected-system-path guard (`safety/guards.py`) the rest of the app
  uses. `database` provides a parameterized `query` tool for SQLite (stdlib) and PostgreSQL (`psycopg2`, optional)
  via a connection string. Neither has natural-language routing yet, matching the existing `notion`/`instagram`
  connectors (callable via `mcp.call(...)`; chat gets the "not wired to plain language yet" info message) —
  registered in `MCPManager.with_defaults()` so `mcp status` now truthfully lists all 11 documented connectors.

### Changed
- File requests are read as whole sentences (`tools/file_intent.py`): keyword rules always run, and when the agent has a
  model it also reads the sentence to fill in the folder, file types and destination. The model's answer is validated
  against the user's own words (a folder must be quoted from the request or be a well-known name), it can never turn a
  find/undo/zip/convert into moves, and a path the user typed always wins. Model failures fall back to the rules.

### Added
- **Slack, Discord and Telegram messaging** through their official APIs (`tools/chat_apps.py`): the exact target and
  text are approved first, and "sent" is reported only when the service returns a message id.
- **WhatsApp safety checks:** Desktop automation types only while WhatsApp is the foreground window and clicks only
  inside it; a known phone number (`WHATSAPP_CONTACTS`) opens the exact chat; Web mode refuses ambiguous names,
  checks the opened chat's header and reads the sent message back. Desktop results are reported as `unconfirmed`.
- **Email:** app-password SMTP sending (`EMAIL_PASSWORD`), `SMTP_STARTTLS` / `IMAP_SSL` switches, reconnect on a stale
  connection, unread-only inbox triage, and working opt-in auto-reply (once per message and sender, never to bots).
- `tools/generate_gmail_token.py` creates the Gmail OAuth token, with a paste-the-URL fallback when the browser
  cannot reach the local listener.
- Linux and macOS support for app discovery and launch; protected-path guard for `/etc`, `/usr`, `/System`, ...
- File requests such as "move the pdfs in downloads into a folder called Invoices".
- Whole-agent end-to-end tests against in-process fake SMTP / IMAP / chat-app servers; `ruff` correctness gate in CI;
  `pyproject.toml`, `CONTRIBUTING.md`, `SECURITY.md`, issue and PR templates, Dependabot.

### Changed
- "send an email/mail to ..." now sends (with approval) instead of drafting, and is no longer mistaken for an
  inbox request; the approval shows the real recipient, subject and body, and appears once.
- Email/Instagram agents use the same LLM provider selection as the main app (Groq by default when configured).
- Documentation moved under `docs/`; Windows launchers stay at the repository root.

### Fixed
- Email drafts could contain the internal prompt (with memory context) when the model ignored the requested format.
- WhatsApp commands like "send Madhu a message on WhatsApp saying hello" parsed the wrong contact.
- "message X on Telegram/Discord/Slack" opened the app and reported success without sending anything; Slack posts
  used to default to `#general` without asking.
- Folder detection picked `Documents` for "organize my pdf documents in downloads" and `/year` for "type/year".
- File organizing did not consult the protected-path guard.
- `tools/ml_engine.py`: the ARIMA forecast referenced `StatsARIMA` before importing it, so statsmodels was never used
  and the request silently fell back to the scratch implementation.

### Removed
- Stale internal audit/plan/readiness reports, `docs/archive/`, the deprecated `legacy/` tools, `.bak` backups,
  duplicate logo copies in the repository root, an unused Chrome-profile helper with a hard-coded personal name, and
  personal paths and email addresses from the documentation. All remain available in git history.

## [1.0.0]

- Hindsight long-term memory: retain / recall / reflect, offline queue, visible "Remembering" card, Memory screen.
- Hosted Groq as the default LLM when `GROQ_API_KEY` is set; local Ollama on opt-in; chat sessions.
- Verified file operations with plan → approval → execute → undo.
- Desktop app (Tkinter), CLI, capability registry with health checks, skills and knowledge routing,
  voice, document/spreadsheet/presentation creation, browser and Instagram agents, PyInstaller build and installer.
