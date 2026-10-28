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
| C05 Browser agent | Partial | Playwright web automation and research; external side effects need approval. Authenticated sessions aren't managed, but TOM now acts in the owner's **own signed-in Chrome profile** by sight for Gmail (`gmail_web`) and Instagram/LinkedIn DMs (`social_web`), gated send with on-screen confirmation |
| C06 Memory | Done | provenance, confidence, retention, correct/forget (chat + both apps) — AT-015 |
| C07 Resource manager | Done (see RRM-005/010) | |
| C08 Planner/executor | Done | typed plans, deps, retries, timeouts, cancel, pause, checkpoints, verification, honest report |
| C09 Diagnostics | Done | processes, resources, services, event log, DNS, ports, runtimes |
| C10 Specialists | Done | role tool grants (`ROLE_TOOLS`) |
| C11 Watchers | Done | opt-in, change-only notices |
| C12 Workflow learning | Done | draft/approve/run |
| C13 Business productivity | Done | professional Word/PDF/PowerPoint/Excel (`tom_core/documents`), email drafts, sends need approval |
| C14 Cloud & infrastructure | Partial | git, Docker/WSL detection; no deployment tooling |
| C15 IoT | Done | firmware/code generation **plus live device control** (`tools/iot_live.py`): detect boards on COM ports (USB VID:PID), I2C-scan what's wired (MicroPython REPL or a flashed scanner), compile+flash with PlatformIO, read back over serial. Flashing is gated (DESTRUCTIVE_OR_EXTERNAL). `test_iot_live.py` (13) |
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

## Owner capability pass (2026-10-27)

Owner request: every option should do professional-grade work — e.g. a bakery website built after
asking what it needs, email sent from Gmail in the owner's Chrome profile after asking, control of the
PC, starting games.

| Area | Before | Now | Evidence |
|---|---|---|---|
| Website (C13) | only the literal words "create website" routed; one model call returned the whole site as JSON (broke on bad JSON, generic page, invented details) | `tom_core/website`: 16 business blueprints, one round of questions for owner-only facts (never invented), section-by-section writing with retry + fallback, multi-file site (SEO, schema.org, map, tel/WhatsApp, form, mobile nav, a11y), verification before success; Website quick action | `test_website_builder.py` (33); live: llama3.2:3b bakery site in 17 s warm, all checks pass, 0 JS errors, no overflow at 390 px |
| Email (C05/C13) | SMTP only; a bare name failed ("I need Ravi's address") | `tools/gmail_web.py`: name looked up in the owner's mail; draft opened pre-filled in Gmail in Chrome's last-used profile; approval shows the exact message; focus check; Ctrl+Enter; **sent only when found in Sent** | `test_gmail_web.py` (26). Live: Chrome + profile found, IMAP + Sent folder read. **Not live-tested: an actual send** (needs the owner's go-ahead) |
| Mail reading | revoked OAuth token (`invalid_grant`) disabled all IMAP reads | falls back to the app password | live: IMAP connects |
| Computer control (C01) | mouse/keyboard/volume/screenshot only | `tools/system_control.py`: lock, sleep*, restart*/shut down* (60 s, cancellable), brightness (read back), show desktop, switch to / close* an app (checked), Settings pages. *needs approval | `test_games_and_system_control.py`; live: brightness read via WMI |
| Games | "play Green Hell" fell through to chat | `tools/game_library.py`: Steam (all libraries) + Epic games; "play/start/launch <game>" starts it; TOM says plainly it can't play real-time games for the owner | live index: Spider-Man 2, Green Hell, over the hill |

### Live feature audit (2026-10-27, second pass)

Every quick action and the main chat features were run through the real `TomAgent` with the local model
(llama3.2:3b) and isolated state; every approval refused unless named, so nothing was sent. Outputs were
opened and read, not just their status. Defects found and fixed:

| Feature | Found | Fixed |
|---|---|---|
| Blender 3D | "low-poly house with lights" answered with Pygame code: the owner's `blender_mcp` add-on crashed Blender at exit, the failure was hidden behind a skill answer, and "light" picked a lighting demo on a cube | `--factory-startup`; a saved scene counts; subject beats modifier; real house (gable roof, door, windows, chimney, path, trees), lights, camera framing; failures reported |
| Multi-Agent | invented product specs | research pieces search the web first and cite; no figures without results |
| Analyze | two generic sentences | structured analysis (summary, factors, pros/cons or comparison table, risks, recommendation), web-grounded when facts matter |
| News | stale SEO pages, feed URL as every link, duplicates | Google News briefings: last 2 days, real links, de-duplicated |
| Diagnostics | "why is my RAM high?" → "I don't have that information" | measured report, per-app process totals, GPU holders, loaded models, tips; closes nothing |
| Env Setup | "Has conflicts: yes" + "No conflicts detected" | verdict from `pip check` exit code |
| Auto-Update | "Count: 0" | behind/ahead of upstream, incoming commits, local changes |
| ML | ignored "predict for 5" | predictions + fitted line |
| Website safety | example.com "no https" (scored the typed text) | one verified HTTPS request; certificate errors flagged |
| PowerPoint | "5 slides" → 9 | the number is the deck length |
| Word | "one-page proposal" → cover + contents + 1,749 words | compact layout, 3 sections, word budget (361 words live) |
| Excel | budget with no formulas, "$" for rupees | numeric columns inferred from values; currency from the data |
| Autonomous | poems saved with literal `\n` | double-escaped text unescaped |
| Fix failing tests | worked, but rewrote the file's blank lines | minimal change merged onto the original |
| Website (agent) | every section fell back to standard text | Ollama JSON mode for website writing |

Verified working as-is: documents/letters, email draft, web search, website, Web Auto, file and data
analysis, system info/brightness, skills, IoT/VLSI code, game scaffold, media resize, scaler, status,
task report, self-evaluation. Full suite after the fixes: 923 passed, 15 skipped.

### Third pass (2026-10-27/28): models per task, screen control, live email

* **Automatic model per task** — `tom_core/resources/model_router.py`; benchmark and choices in
  `docs/benchmarks/model-routing.md`. Live: code fix, documents, website, analysis, plans → qwen3:8b; chat
  reuses the loaded model. Full 40-feature audit rerun with routing: 38 succeeded, 2 sends correctly
  refused; one regression (Autonomous: the 8B model mangled the long workspace path) fixed with
  `<workspace>`-style folder tokens and a named-folder repair — live: `poems/` with three real poems.
* **Screen control by sight** — Tesseract 5.4 installed (UB-Mannheim, winget); `tom_core/screen_control.py`
  reads, finds, clicks, types (Unicode via a fixed clipboard) and re-reads to confirm. Commands: "click X",
  "double-click X", "type X", "read my screen" (which used to be answered by chat without looking).
* **Live email to the owner** — written by TOM, opened in Gmail in Chrome's default profile, draft checked
  on screen (recipient + exact subject), Send button clicked by sight, Gmail's "Message sent" seen, email
  found in the recipient's inbox (26.7 s). TOM never clicks Send unless this exact draft is on screen.

Known limits: Gmail's Ctrl+Enter send is not documented by Google for accounts with keyboard shortcuts
off — the Sent-folder check is what decides success. Sleep via `SetSuspendState` may be refused on
Modern Standby laptops (reported as such). TOM plays real-time games only by the two routes described
below (its own games by sight; any installed game by the state-aware loop, which reads the screen and
retries after deaths but is not an expert player of a 3D action game).

### Owner "do everything" capability pass (2026-10-28)

Owner asked to fill every remaining gap, warning on risky actions but proceeding on confirmation
(the malware / attack-a-third-party blocks in `safety/guards.py` were kept — they already warn-and-
allow only for the owner's own systems). Built this session (branch
`refactor/r0-r1-audit-and-characterization`):

| Area | What shipped | Evidence |
|---|---|---|
| agent.py type safety | Fixed all 31 Pylance `severity 8` errors the owner reported; `pyright` 0 errors for agent.py | pyright |
| Live IoT (C15) | `tools/iot_live.py` — port/board detection, I2C scan, PlatformIO flash (gated), serial read-back; wired into the engine router | `test_iot_live.py` (13) |
| API keys | `tom_core/secrets.py` — TOM asks for a key when a feature needs one, saves to `.env`, reuses it; redactor masks the value everywhere | `test_secrets.py` (11) |
| Instagram/LinkedIn (C05) | `tools/social_web.py` — DM in the owner's own Chrome profile by sight, gated send, on-screen confirmation | `test_social_web.py` (14) |
| Dev builds | `tom_core/coding/scaffold.py` — real buildable scaffolds (static/node/react/python/android/flutter) + `verify()` that runs the toolchain (`node --check`, `py_compile`); `_execute_code_project` now builds and reports evidence | `test_scaffold.py` (14) |
| 3D + assets | `tools/asset_fetch.py` (CC0 Poly Haven: models/HDRIs/textures) + `blender_control.assemble_scene`; verified live (barrel + sunset HDRI imported into Blender 5.2, .blend + preview rendered) | `test_asset_fetch.py` (8, incl. live), `test_asset_task.py` (9) |
| Game autopilot | `tools/game_autopilot.py` — vision model → DirectInput scan codes, bounded loop, kill switch; **experimental**, warns about anti-cheat/ban and reflex limits, gated on the exact game | `test_game_autopilot.py` (9) |

Design kept throughout: observation is free; anything that writes to a device, sends a message, or
drives a game passes the policy engine once on the exact payload, with the warning shown first.

### Game development and playing (2026-10-28, second pass)

| Area | What shipped | Evidence |
|---|---|---|
| Making games (C17) | `tom_core/games/`: one shared Pygame runtime (`tomgame.py`) and eight genres (snake, breakout, flappy, shooter, runner, pong, racer, platformer). `studio.py` reads genre/theme/difficulty/title from the request, writes the game, then **runs it headless** and reports the real traceback back to the model to repair; a manifest, README and `run.bat` are written next to it. An unknown genre asks which one instead of inventing a game | `test_game_studio_and_play.py` — all 8 genres built and self-tested |
| Godot / Unity | `godot.py` writes a Godot 4 project and verifies it by running it headless in the real engine; `unity.py` writes a complete C# project + build script. A missing licence or editor is reported as the actual reason, not as success | tests (Godot skipped when the engine is absent); live: 4.7.2 builds and runs |
| Playing its own games | `strategies.py` reads the screen state and returns key holds/mouse moves per genre, scoring measurably above random play (e.g. platformer 15-22 coins/min vs 0) | `test_game_studio_and_play.py`; live window runs |
| Autopilot input | Fixed the `SendInput` struct size that made every key silently do nothing; window-aware loop that only types into the game's window and pauses when anything else comes to the front; `stop playing` releases every key | regression test in `test_game_studio_and_play.py` |
| Tasks inside games | `tools/game_tasks.py`: Minecraft Bedrock by its own chat commands (`/fill`, `/setblock`, `/locate`, `/tp`, `/give`, time/weather/gamemode). TOM opens chat, types, reads the game's reply by OCR, stops at the first refusal and explains that cheats are off, then offers to play toward the goal instead; any other game becomes the vision explorer's goal | `test_game_studio_and_play.py` |
| Game discovery | `tools/game_library.py` reads desktop/Start-menu `.lnk` files, so a game started through BlueStacks (or a Steam/Epic link) is found like a Steam title; emulator window titles are used when they differ from the game's name | `test_game_studio_and_play.py` |
| Routing | "make a game" → game dev (not chat), "play my snake game" → launch, "play it for me" → autopilot, "build a house in minecraft" → in-game task, "stop playing" → stop | `test_routing_for_making_playing_and_tasks` |

### Playing any installed game, with understanding (2026-10-28, third pass)

Owner asked that TOM be able to play *any* game installed on the laptop — not just Minecraft — learning
the game's controls, adapting to what is on screen, and retrying until the goal is met. Before this pass
"playing" an installed game meant: launch it, then hold whichever single key a small vision model picked,
once a second, with no idea what the screen showed. It pressed W at main menus, at loading screens and at
death screens alike, kept no memory between sessions, and had no notion of success or failure.

| Area | What shipped | Evidence |
|---|---|---|
| Reading the game's state | `tom_core/games/perceive.py` — every frame is classified `loading / menu / paused / gameplay / dead / static` from the game's own words (OCR) first and pixel motion second, with a rolling average so one still frame is not mistaken for a freeze | `test_game_play_loop.py` (perception cases) |
| Learning the controls | `tom_core/games/discover.py` — on the first session with an unfamiliar game, TOM presses each candidate key once, measures how much of the screen changed, and records only what answered. ESC/TAB/ENTER are never probed (they open menus and consoles). A game that answered nothing is not marked as learned, so the next session tries again | live: Viper — `W A S D SPACE` all measured 0.012-0.019; only keys within a quarter of the best became roles |
| Remembering each game | `tom_core/games/profile.py` — a per-game JSON profile in `TOM Workspace/game_profiles/`: discovered controls, screen states seen, sessions, deaths, goals met, best session, notes. Built-in metadata per installed game says only its window title and *kind* (action / survival / driving / turnbased / command) — the bindings are measured, never assumed | `test_game_play_loop.py`; live file written for Viper |
| Playing with a goal and retries | `tom_core/games/play_loop.py` — `parse_goal` turns "survive 5 minutes" / "get to level 3" / "win a round" into a checkable goal; the loop dispatches by state (click the menu button or press Enter; tap the board; press Enter/Escape to respawn), counts one death per death screen, retries up to `max_attempts`, checks win/target words on screen, and reports what it saw | live: Viper — died at 3.0 s and 5.7 s, came back into play both times via Enter, game's own `rounds` went 2 → 4 |
| Per-game behaviour | turn-based games (Ludo King) are tapped by their button words with the middle of the board as a fallback and never press keys; driving games keep the throttle down; a still screen in a 3D game is treated as normal play (not a menu) so Enter is never pressed at a standing camera | `test_game_play_loop.py` |
| Wiring | `tools/game_play.py` — `WindowBackend` captures the game's client area, reads its words, and sends keys/mouse **only while that window is in front**; `play_installed_game` now delegates to it and the agent's approval prompt states the new behaviour | `test_game_play_loop.py` (48 tests); live end-to-end via `play_live("Viper")` |

Defects found by running it on a real window rather than in tests, and fixed:

* a single death screen was counted as one death **per look** — three looks of "Game over" became "died 3
  times, gave up"; deaths are now counted on entering the dead state;
* clicking "play again" on a PC game's death overlay succeeds (the text is found) and does nothing — 17
  clicks, still dead; keyed games now answer the death screen with Enter, falling back to Escape;
* `roles_from` used a fixed 0.02 cutoff and found **no** controls in a real (small) window where every
  working key measured 0.012; it now compares against the best key, with a small absolute floor;
* clicks are now real actions that are counted, instead of being issued outside the input path.

Honest limits of this pass: a 3D action game (Spider-Man 2, Green Hell) is driven by a small local vision
model plus motion heuristics, so TOM can follow what is on screen and stop dying to menus, but it will not
fight or platform like a person; Ludo King is the one installed game whose board it can genuinely read and
tap; Minecraft still uses its own chat commands for tasks (exact and checked), with the loop as the
fallback when cheats are off. Anti-cheat is never evaded — the warning and the account-ban risk are shown
before anything runs, and only the owner's own single-player games are expected to be used this way.

### The strategy path vs the general path, and latency (2026-10-28, fourth pass)

Owner reported that earlier work played a game "with exceptional skill", while later runs died on the
first attempt. Both were true, of two different code paths, and the numbers explain it:

| Player on the same snake game (Viper) | Best | Mean | Rounds survived |
|---|---|---|---|
| `strategies.SnakeStrategy` — reads the board's own colours, plans a path | **33** | 33.0 | **1 (never died)** |
| Random keys (`evaluate(player="random")`) | 2 | 0.40 | 5 |

and live in a real window: **score 26 / best 26 / one round** over 40 s at 35.5 fps, later 34.2 fps.

The mistake this pass fixes: `play_live` (the installed-game path) did not recognise a game TOM had made,
so asking it to play Viper ran the **general** explorer instead of the strategy — three deaths in six
seconds on the same game the strategy survived for a full round. `play_live` now checks
`studio.find_made_game()` first and hands a made game to `play_made_game`, so that can never happen again.

Latency, measured rather than claimed (1200×900 window):

| Cost | Before | Now |
|---|---|---|
| Strategy decision | 0.73 ms median, 0.94 ms p95 | already this — it was never the problem |
| One screen read (OCR) | 366 ms | **244 ms** (mss grabs the region; pyautogui grabbed the whole screen and cropped; and a large window is no longer upscaled 2× before OCR) |
| General loop rate | 8.9 looks/s (OCR inline, fixed sleep on top of the work) | **29.2 looks/s** at a 30 fps target (OCR on a background thread; the loop sleeps only the remainder of its tick) |
| Made-game play rate | 35.5 fps | unchanged |

Also fixed: in a grid or arcade game the discovered "forward" key is really a *direction*, so holding it
forever drove into a wall — the run that died in three seconds. Those games now move in 0.6 s bursts and
change direction; 3D kinds (action, survival, driving, command) still hold forward, which is how those
games are played.

What this does **not** mean: an arbitrary 3D game is still not played at a professional level. The
professional-level path is the strategy players for games TOM builds (colour perception + planning +
DirectInput at 30-60 fps). For an installed 3D game the general loop reads the screen, works menus,
recovers from deaths and retries — it does not fight or platform like a person, and saying otherwise
would be the exact overclaim this project has avoided elsewhere.
