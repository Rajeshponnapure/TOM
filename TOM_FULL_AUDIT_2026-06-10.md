# TOM Autonomous Agent — Full End-to-End Audit & Remediation Plan

**Audit date:** 2026-06-10
**Auditor role:** Principal architect / Senior QA / Desktop app & AI-agent systems / UI-UX / Automation / Product
**Method:** Static reverse-engineering of the live repository (`tom_autonomous_agent`). Every claim below is grounded in a file/line observed during the audit, or explicitly labelled as an estimate. Per the project's own CLAUDE.md "Zero Hallucination" rule, where I could not execute the frozen Windows `.exe` in this Linux audit sandbox, that limitation is stated rather than guessed.

> **Scope note / what I could NOT do:** The 354 MB Windows `.exe` cannot be executed in this audit environment (no Windows, no Ollama server, no GPU). Runtime claims about the binary (startup time, crash behaviour, live model output) are therefore marked *unverified — requires Windows runtime*. All source-level findings ARE verified.

---

## 1. Executive Summary

TOM is an **ambitious, locally-run autonomous desktop assistant** (~39,000 lines of first-party Python) built on a local Ollama LLM (`gemma4:latest`), a Tkinter desktop UI, a 50-module tool layer, 47 local "skill" docs plus an embedded 864-file external skill library, a 36-file curated knowledge base, three background sub-agents (email, Instagram, news), a multi-agent orchestrator, RAG memory (ChromaDB), and a PyInstaller-packaged executable.

The codebase is **syntactically clean** (all first-party modules compile with zero errors) and the breadth of capability is genuinely large. However, it is **not production-grade**, and there is a sizeable gap between *what the code contains* and *what a user can actually reach and trust*. The dominant problems are architectural and integration-level, not syntax bugs.

**Top findings (verified):**

| # | Severity | Finding | Evidence |
|---|----------|---------|----------|
| 1 | 🔴 Critical | **Secrets sit in the repo with no `.gitignore`.** `.env` (contains `EMAIL_PASSWORD`), `google-credentials.json`, and a live OAuth `..._token.json` are in the project root; there is no `.gitignore` anywhere. Git currently has **0 commits**, so nothing is committed *yet* — but one `git add .` captures all of it. | `ls` root; `grep .gitignore → No such file`; `git ls-files` → none tracked |
| 2 | 🔴 Critical | **Split-brain routing.** Specialized capabilities (ML, IoT, VLSI, Hardware, Blender, Game-Dev, News, Autonomous, Voice+, Auto-Update, Env) are hard-wired **only inside the Tkinter UI** (`tom_desktop_app.py`), bypassing the agent's NLP/skill/knowledge routing. The CLI (`main.py`) cannot reach any of them. | `agent.execute_task` has no handlers for these; `tom_desktop_app.py:2766` `_quick_action` → `_handle_*` |
| 3 | 🟠 High | **Knowledge base is orphaned from reasoning.** `KnowledgeEngine` (`tools/knowledge_engine.py`) and the 36 curated `knowledge/*.md` files are never imported by `agent.py`. Only `news_agent` *writes* to the dir. The agent reasons from RAG conversation memory, not the curated knowledge. | `grep` for `knowledge_engine`/`get_engine()` → no external callers |
| 4 | 🟠 High | **"Power BI report generation" is not real.** No `.pbix`/Power BI executor exists; `data_analysis.py` produces matplotlib PNGs and is literally commented "beats Power BI." A requested capability is silently substituted. | `data_analysis.py:2,48`; no powerbi executor in `tools/` |
| 5 | 🟠 High | **Specialized engines require rigid prefix syntax, not natural language.** e.g. `regression linear X=[1,2,3] y=[2,4,6]`, `verilog counter width=8`, `esp32 dht11 mqtt`. Typing the same intent in plain English in chat misses the engine entirely. | `tom_desktop_app.py` `_run_ml/_run_iot/_run_vlsi` `startswith()` parsers |
| 6 | 🟠 High | **708 MB of duplicated build output.** `dist/tom_desktop_app.exe` and `dist_updated/tom_desktop_app.exe` are **byte-identical** (same MD5), each 354 MB. | `md5sum` match |
| 7 | 🟡 Medium | **`eval()` on external data.** `file_analyzer.py:196` runs `eval()` on ffprobe's `avg_frame_rate` string — code-injection vector from a crafted media file. | `file_analyzer.py:196` |
| 8 | 🟡 Medium | **Startup loads 911 skill files** (47 local + 864 external `SKILL.md`) via glob on every launch, and bundles the whole 18 MB `awesome-claude-skills` repo (including its own `.git`) into the exe. | `skill_manager.py:174-184`; `find … SKILL.md` = 864 |
| 9 | 🟡 Medium | **No dependency pinning.** `requirements.txt` uses only `>=` (0 exact pins) → non-reproducible builds, supply-chain drift. | `grep -c "==" = 0` |
| 10 | 🟡 Medium | **Documentation sprawl / no version control.** 22 root `.md` files (multiple overlapping PLAN_V2/V3/V4, ANALYSIS/CAPABILITIES/FUNCTIONAL reports) and an uninitialised git history make "source of truth" ambiguous. | `ls *.md` = 22; `git log` = no commits |

**Bottom line:** This is a **capable prototype at roughly "advanced internal alpha,"** not a production platform. It needs (a) a security pass, (b) a routing unification so one brain serves both CLI and GUI, (c) genuine knowledge/skill wiring, (d) honest capability labelling, and (e) build/release hygiene. A realistic **Production Readiness Score: 38/100** (detailed scorecard in §15).

---

## 2. Architecture Analysis

### 2.1 High-level component map (verified)

```
                       ┌──────────────────────────────────────────────┐
                       │                ENTRY POINTS                    │
                       │                                                │
                       │   main.py (CLI)        tom_desktop_app.py (GUI)│
                       │      │                       │  4,711 LOC      │
                       │      │                       │  Tkinter        │
                       └──────┼───────────────────────┼─────────────────┘
                              │                       │
                              ▼                       ▼
                   ┌────────────────────┐   ┌──────────────────────────┐
                   │  agent.TomAgent     │   │  GUI-LOCAL DISPATCH       │
                   │  (agent.py 2,053)   │   │  _handle_* / _run_*       │
                   │  execute_task()     │   │  ML/IoT/VLSI/HW/Blender/  │
                   │  = central router   │   │  GameDev/News/Autonomous/ │
                   └─────────┬───────────┘   │  Voice+/AutoUpdate/Env    │
                             │               └───────────┬──────────────┘
        ┌────────────────────┼───────────────┐           │
        ▼                    ▼               ▼            ▼ (engines: ml_engine,
 CommandRouter         SkillManager     CapabilityResolver  iot_engine, vlsi_engine,
 (routes→handler)      (911 SKILL.md)   (skill→tool map)    hardware_control, blender_control,
        │                    │               │             game_dev, news_agent, auto_scaler,
        ▼                    ▼               ▼             voice_enhanced, auto_update,
 ┌─────────────────────────────────────────────────┐      dependency_manager, autonomous_agent)
 │  TOOL LAYER  (tools/*.py — 50 modules)            │
 │  os_tools, browser_tools, file_tools, email_tools │
 │  document_creator, data_analysis, whatsapp_tools, │
 │  screen_tools, pdf_tools, web_automation,         │
 │  mcp_manager, plugin_manager, scheduler,          │
 │  rag_memory, self_evolution, learning, ...        │
 └───────────────────────┬───────────────────────────┘
                         │
   ┌──────────┬──────────┼───────────┬──────────────┬───────────────┐
   ▼          ▼          ▼           ▼              ▼               ▼
 Ollama   ChromaDB   knowledge/   skills/      agents/         safety/
 (LLM)    (RAG)      (36 files,   (47 local +  (email,         guards.py
          tom_brain/ ORPHANED)    864 external)instagram,
                                               news daemons)
```

### 2.2 The central architectural defect — two routers, one brain missing

There are **two independent command routers** that do not share logic:

1. **`agent.execute_task()`** (`agent.py:296-628`) — a 330-line `if/elif` ladder that handles documents (Word/Excel/PPT/PDF), email, WhatsApp, web search, file ops, data analysis, website creation, screen read, MCP connectors, build-agent, and a skill-route fallback. This is what the **CLI** uses and what the **GUI chat box** uses.

2. **`tom_desktop_app._quick_action()` → `_handle_*`/`_run_*`** (`tom_desktop_app.py:2766+`) — a parallel dispatcher that lazy-instantiates the specialized engines (ML, IoT, VLSI, Hardware, Blender, Game-Dev, News, Autonomous, Voice+, Auto-Update, Env) and parses **rigid prefix commands**. This exists **only in the GUI**.

**Consequences (all verified):**
- The CLI (`main.py`) is missing ~11 entire capability families. Two "products" diverge from one repo.
- The specialized engines never see the NLP parser, the skill router, the knowledge base, RAG memory, the safety gate, the learning/evolution loop, or the approval manager — they are reached by a modal `askstring()` dialog and a `startswith()` parser.
- Business logic lives in the **view layer** (Tkinter), which is the classic anti-pattern that blocks testing, headless operation, scheduling, and any future web/mobile front-end.

### 2.3 Subsystem wiring (from `TomAgent.__init__`, `agent.py:57-160`)

Wired into the agent (good): `OSTools, BrowserTools, FileTools, EmailTools, EmailAgentController, InstagramAgentController, SafetyGuards, Learner, ChatMemory, CommandRouter, SkillManager, CapabilityResolver, ApprovalManager, WhatsAppTools, ChromeProfileManager, ScreenTools, FileAnalyzer, PluginManager`, plus optional/try-guarded `rag, evolution, mcp, orchestrator, web_automation`.

Each optional subsystem is initialised in a `try/except` that degrades silently to `None` and prints a `[SUBSYSTEM] Could not initialise` line. This is **resilient** but also **opaque**: a user on a machine where ChromaDB/MCP/orchestrator failed to load gets a silently degraded assistant with no UI surfacing of "RAG is offline."

### 2.4 Dependency posture
- **Heavy runtime coupling:** the whole system assumes a **local Ollama server** at `http://localhost:11434` with `gemma4:latest` (a 26–31B-class model — *Gemma 4 verified real, released April 2026*) plus `qwen2.5-coder:7b` and `nomic-embed-text` pulled. If Ollama isn't running or models aren't pulled, the assistant cannot reason. There is no graceful "LLM unavailable" UX path.
- **`requirements.txt`:** 40+ deps, **all `>=`, zero pins** → non-reproducible.
- **Embedded third-party repo:** `awesome-claude-skills/` (18 MB, includes its own `.git`) is vendored into the tree and bundled into the exe.

---

## 3. Capability Inventory

Format: **Capability → Backend module → UI access → Status**. Status legend: ✅ real & reachable · ⚠️ real but limited/awkward · 🟥 missing/fake/orphaned.

| Capability | Backend implementation | Trigger / UI access path | Status & notes |
|---|---|---|---|
| Open applications | `os_tools.OSTools.open_application` | Chat: "open X"; router `execute_open_command` | ✅ Real (Windows-focused) |
| WhatsApp messaging | `whatsapp_tools.py` (native win32 + web fallback) | Quick action → chat; `_execute_whatsapp` | ✅ Real |
| Word docs | `document_creator` (python-docx) | Quick "Word Doc"; `_create_word_doc` | ✅ Real |
| Excel | `document_creator` (openpyxl) | Quick "Excel"; `_create_excel` | ✅ Real |
| PowerPoint | `document_creator` (python-pptx) | Quick "PowerPoint"; `_execute_presentation` | ✅ Real |
| PDF report | `document_creator` (reportlab) | Quick "PDF Report"; `_create_pdf` | ✅ Real |
| **Power BI report** | — none — (`data_analysis` PNGs) | router keyword only | 🟥 **Fake** — substitutes matplotlib; no Power BI artifact |
| Data clean/analyze/insights | `data_analysis.py` (pandas/matplotlib) | Quick "Data Anal"; `_execute_data_analysis` | ✅ Real (static PNG charts, not interactive) |
| Charts/visualization | `data_analysis.auto_visualize` (matplotlib savefig) | Charts view; data analysis | ⚠️ Real but PNG-only; plotly listed but not the primary path |
| Email write/send/triage | `email_tools` + `email_agent_controller` | Quick "Email"; multiple handlers | ✅ Real (Gmail OAuth + IMAP) |
| Web search | `web_automation`/`browser_tools` + googlesearch | Quick "Web Search"; `_web_search` | ✅ Real |
| Website build | `_execute_website_creation` (LLM codegen) | "create website" | ⚠️ Generates files; no run/deploy/preview pipeline |
| Write code | `file_tools` + code LLM | "write code"; `_execute_code_project` | ✅ Generates files |
| **Run code** | partial (`sandbox_functional_tests`, GUI "run ") | GUI only | ⚠️ Limited/guarded; not a general code runner |
| VS Code / IDE control | `os_tools.open_application` | "open vscode" | ⚠️ Can launch; no in-IDE automation |
| Open WhatsApp/Browser | `whatsapp_tools`, `browser_tools` | quick actions | ✅ Real |
| Screen OCR read | `screen_tools` (pytesseract/opencv) | "read screen"; `execute_screen_read` | ✅ Real (needs Tesseract installed) |
| Hardware control (mouse/kbd/volume) | `hardware_control.py` (pyautogui) | GUI "Hardware" only | ⚠️ GUI-only; prefix syntax |
| ML (regression/classify/cluster/TS) | `ml_engine.py` (sklearn) | GUI "ML" only | ⚠️ GUI-only; prefix syntax; toy default data |
| IoT codegen (ESP/MicroPython) | `iot_engine.py` | GUI "IoT" only | ⚠️ GUI-only; codegen |
| VLSI (Verilog/RTL/embedded) | `vlsi_engine.py` | GUI "VLSI" only | ⚠️ GUI-only; codegen |
| Game dev scaffolding | `game_dev.py` | GUI "Game Dev" only | ⚠️ GUI-only |
| Blender 3D | `blender_control.py` (`exec` of scripts) | GUI "Blender" only | ⚠️ GUI-only; needs Blender; uses `exec()` |
| News briefings | `news_agent.py` | GUI "News" + daemon | ✅ Real (also a scheduled daemon) |
| Multi-agent orchestration | `agent_orchestrator.py` | GUI "Multi-Agent"; not in CLI | ⚠️ GUI-only entry |
| Autonomous multi-step | `autonomous_agent.py` | GUI "Autonomous" only | ⚠️ GUI-only |
| Voice (in/out, conversation) | `voice_tools.py` + `voice_enhanced.py` | CLI "talk"; GUI voice btn | ✅/⚠️ Core voice real; "Voice+" emotion GUI-only |
| Scheduling | `scheduler.py` (APScheduler) | indirect (agents) | ⚠️ Real but no UI scheduler surface |
| MCP connectors (GitHub/Slack/Calendar) | `mcp_manager.py` | chat keywords; `_handle_mcp_request` | ⚠️ Real layer; coverage limited to a few connectors |
| RAG semantic memory | `rag_memory.py` (Chroma) | implicit | ✅ Real (conversation memory) |
| Self-evolution / learning | `self_evolution.py`, `learning.py` | implicit + reward/penalty | ✅ Real |
| Curated knowledge tutor | `knowledge_engine.py` | — none reachable — | 🟥 **Orphaned** (never imported by agent/GUI) |
| Plugin system | `plugin_manager.py` | discovery at init | ⚠️ Discovered; thin execution surface |
| Auto-update / scaling | `auto_update.py`, `auto_scaler.py` | GUI only | ⚠️ GUI-only |

**Orphaned modules (verified by reverse-reference scan — referenced nowhere but their own file):** `knowledge_engine`, `tom_tools`, `verify_tom_system`, `make_icon`, `prepare_migration_package`. (The last three are utilities; the first two are meaningful dead code.)

---

## 4. Skill Mapping Matrix (Skill → Function)

**Inventory:** 47 first-party `skills/*.md` + **864** external `awesome-claude-skills/**/SKILL.md`, all loaded at startup by `SkillManager._load_all` (`skill_manager.py:174-184`, `include_external=True` by default).

How skills are actually used: when no concrete tool handler matches **and** the route is "chat," `agent._handle_skill_routed_task` (`agent.py:1771`) injects the matched skill's trimmed context (`skill_route.context`, max ~90 lines) into the LLM system/human prompt. So skills function as **prompt-augmentation guidance**, not as bound executables.

| Skill family (local) | Backing function/engine | Mapping quality |
|---|---|---|
| 01 UI/UX, 02 Frontend, 03 Backend, 16 Cross-platform | LLM codegen via skill route | ⚠️ Guidance-only (no build tool) |
| 17 Excel, 18 Word, 19 PowerPoint | `document_creator` | ✅ Real executor |
| 20 **Power BI** | none | 🟥 **Broken mapping** (keyword → matplotlib) |
| 08 Data science, 09 Data cleaning, 40 Predictive | `data_analysis`, `ml_engine` | ✅ Real |
| 29 ML, 30 Deep learning, 31 NLP, 32 CV | `ml_engine` (29/30), LLM (31), `file_analyzer` (32 partial) | ⚠️ Mixed; DL/CV thin |
| 27 Game dev | `game_dev` | ✅ (GUI-only) |
| 04 3D animation / Blender | `blender_control` | ✅ (GUI-only, `exec`) |
| 45 IoT, 46 VLSI | `iot_engine`, `vlsi_engine` | ✅ (GUI-only) |
| 22 Cybersecurity, 23 Networking | partial `web_automation` (safety check) | ⚠️ Mostly guidance |
| 21 DevOps, 26 System design, 28 Blockchain | none | ⚠️ Guidance-only |
| 10/11/12/13 Mobile/macOS/Windows, 42/43/44 Flutter/Tauri/RN | LLM codegen | ⚠️ Guidance-only (no SDK/build) |
| 14 Email, 15 Content | `email_tools`, LLM | ✅ Real |
| 38 Medical, 39 Media, 41 Desktop UI | knowledge/guidance | ⚠️ Guidance-only |

**Coverage estimate (assessed, defensible):**
- Skills with a **dedicated real executor:** ~14/47 ≈ **30%**
- Skills backed by **LLM codegen/guidance only:** ~32/47 ≈ **68%** (functional but generic; no build/deploy/verify)
- **Broken/fake mapping:** 1 (Power BI) — plus the entire 864-file external library is loaded but only ~handful are ever routed.
- **Redundant:** local `skills/` overlaps the vendored `awesome-claude-skills/` (e.g. brand-guidelines, canvas-design, mcp-builder, slack-gif-creator, theme-factory appear in both) → ambiguous routing, wasted load.

---

## 5. Function Mapping Matrix (Function → UI)

| Function group | In CLI? | In GUI? | Discoverable? | Notes |
|---|---|---|---|---|
| Documents (Word/Excel/PPT/PDF) | ✅ | ✅ quick actions | ✅ | Best-exposed area |
| Email (write/send/triage) | ✅ | ✅ | ⚠️ | Triage buried in chat |
| Web search / website | ✅ | ✅ | ✅ | |
| Data analysis / charts | ✅ | ✅ | ⚠️ | Charts view exists; flow awkward |
| WhatsApp | ✅ | ✅ | ✅ | |
| Screen OCR | ✅ | ✅ | ⚠️ | |
| ML / IoT / VLSI / Hardware / Blender / GameDev / Autonomous / Voice+ / Env / AutoUpdate / Multi-Agent | 🟥 **No** | ✅ | 🟥 prefix-syntax only | **GUI-locked, undiscoverable NL** |
| Scheduler | ⚠️ indirect | 🟥 no surface | 🟥 | No schedule UI |
| MCP connectors | ✅ keywords | ✅ keywords | 🟥 | No connector browser |
| RAG / evolution / learning | implicit | implicit | 🟥 | No memory/insights panel |
| Plugin manager | init | init | 🟥 | No plugin UI |
| Knowledge tutor | 🟥 | 🟥 | 🟥 | Orphaned |
| Settings (model, voice, keys) | env only | partial (model dropdown) | 🟥 | No real settings center |

**UI exposure coverage (assessed):** of ~35 real user-facing capabilities, ~**24 reachable via GUI ≈ 69%**, but only ~**13 reachable via CLI ≈ 37%**, and **natural-language discoverability ≈ 40%** (everything engine-side needs exact prefixes or the right quick-action button).

---

## 6. Knowledge Base Mapping Matrix (Knowledge → Skill/Agent)

| Knowledge asset | Exists | Read at inference? | Consumer |
|---|---|---|---|
| `knowledge/*.md` (36 curated domain files: cybersecurity, medical, data_science, game_dev, web_dev, mobile_dev, 3d-design, audio, etc.) | ✅ | 🟥 **No** | Only `news_agent.update_knowledge_base()` **writes** here |
| `KnowledgeEngine` (`teach_topic`, `search`, `get_domain`, `get_lesson_plan`) | ✅ (363 LOC) | 🟥 **No** | `get_engine()` defined, **never called externally** |
| `tom_brain/` (chroma_db, learned_patterns, user_profile, evolution.json) | ✅ | ✅ | RAG + evolution use this |
| RAG conversation memory | ✅ | ✅ | `agent` stores/reads conversation vectors |

**Critical insight:** The system has TWO "memories" and uses the wrong one for domain expertise. **RAG (conversation history) is wired; the curated KnowledgeEngine (the actual subject-matter library) is not.** So when a user asks a cybersecurity or medical question, the carefully-authored `knowledge/cybersecurity.md` / `medical.md` are **not** consulted — the model answers from its own weights.

**Knowledge-utilization coverage (assessed): ~5–10%.** The curated KB is essentially dead weight today (and is still bundled into the 354 MB exe via the spec `datas`).

---

## 7. UI/UX Audit

**Framework:** Tkinter (`tom_desktop_app.py`, 4,711 LOC, single file). Custom dark theme (`C[...]` palette), sidebar with logo, animated "orb," clock, status ticker.

**Information architecture (current):** 5 nav views — **Dashboard, Chat, System, Charts, Files** — + a sidebar of 3 agent profiles (core/email/instagram) + **25 "quick create" buttons** + Voice Mode + Run Agent.

### Strengths
- Visually coherent dark theme, custom iconography, live status animations, keyboard shortcuts, model-switch dropdown.
- Dashboard has an inline send box; chat has reward/penalty feedback affordances.

### Problems (verified / assessed)
1. **Discoverability collapse.** 25 capabilities are flattened into a single "Quick Create" strip; the most powerful ones (ML/IoT/VLSI/Autonomous/Multi-Agent) open a **bare `askstring` modal** demanding memorised prefix syntax. No inline help, examples-as-placeholders only.
2. **No capability centers.** There is no Skill browser, Tool catalog, Knowledge center, Automation/schedule center, Agent workspace, Developer workspace, Data workspace, or real Settings — all of which the target end-state calls for.
3. **Two interaction grammars.** Chat = natural language; quick-engines = `verb arg=val`. Users must context-switch between an NLP brain and a CLI-in-a-dialog.
4. **Monolithic view layer.** 4,711 lines mixing layout, theming, async glue, AND business routing → unmaintainable, untestable, not portable to web/mobile.
5. **Silent degradation.** Offline subsystems (RAG/MCP/orchestrator) aren't surfaced in the UI; the user can't tell the assistant is running at reduced capability.
6. **Accessibility/responsiveness:** fixed pixel sidebar (236 px), Tkinter (no DPI-aware scaling guarantees, limited screen-reader support, no keyboard-only flows for quick engines, no light theme/contrast options).
7. **No telemetry/health panel** beyond a status ticker; logs live in `tom_logs/` but aren't surfaced.

### Recommended IA redesign (target)
```
┌── Sidebar ───────────────┐  ┌── Main ────────────────────────────────┐
│ ⌂ Dashboard              │  │ Context-aware workspace per nav item     │
│ ▢ Chat (one NL brain)    │  │                                          │
│ ◳ Agents workspace       │  │  • Dashboard: health, recent, shortcuts  │
│ ⚒ Tools catalog          │  │  • Skill Center: search 47/864, preview, │
│ ◈ Skill Center           │  │    "run with this skill"                 │
│ ✦ Knowledge Center       │  │  • Knowledge Center: browse/search KB,   │
│ ⟳ Automations/Schedule   │  │    "use in answers" toggle               │
│ ⌗ Developer workspace    │  │  • Automations: schedules, daemons,      │
│ ◔ Data workspace         │  │    triggers, run history                 │
│ ⚙ Settings               │  │  • Developer: codegen+run+preview        │
│ ── Agents ──             │  │  • Data: load→clean→viz→export, live      │
│ ● Core ● Email ● IG      │  │  • Settings: models, keys, voice, theme, │
└──────────────────────────┘  │    subsystem health, privacy             │
                              └──────────────────────────────────────────┘
```
**Principle:** every capability discoverable from a center; one NL entry point (chat) that can reach *every* engine; advanced "expert syntax" optional, never required.

---

## 8. Desktop Executable Audit

**Artifacts:** `dist/tom_desktop_app.exe` (354 MB), `dist_updated/tom_desktop_app.exe` (354 MB), `build/tom_desktop_app/` (PyInstaller work dir), `installer/tom_installer.iss` (Inno Setup), `tom_desktop_app.spec`.

| Aspect | Finding | Severity |
|---|---|---|
| **Duplicate binaries** | `dist` and `dist_updated` are **byte-identical** (MD5 `9f6af184…`). 708 MB total for one build. | 🟠 High (hygiene) |
| **Size** | 354 MB onefile. Bundles chromadb, onnxruntime, cv2, matplotlib, plotly, pygame, **the entire 18 MB `awesome-claude-skills` incl. its `.git`**, knowledge/, skills/. Much is dead weight (orphaned KB, 864 unused skills). | 🟠 High |
| **Spec correctness** | Sensibly excludes `torch/torchvision/torchaudio` (noted as ~487 MB + CUDA crash risk) and `sentence_transformers`. **But** `sentence-transformers` is in `requirements.txt` and excluded from the exe → any code path expecting it differs between dev and frozen. | 🟡 Medium |
| **Build warnings** | `warn-…txt` = 1,056 lines, but overwhelmingly **benign** cross-platform optional imports (`pwd`, `grp`, `java`, `android`, `_posixshmem`, …). No first-party module flagged missing. | 🟢 Low |
| **Signing** | `codesign_identity=None`, unsigned. Windows SmartScreen will warn; no notarisation. | 🟠 High (distribution) |
| **Console** | `console=False` (windowed) → no stderr surface; crashes vanish unless logged. `disable_windowed_traceback=False` helps a little. | 🟡 Medium |
| **UPX** | `upx=True` — can trip AV heuristics/false positives on an unsigned 354 MB binary. | 🟡 Medium |
| **Installer** | Inno Setup script present (`installer/tom_installer.iss`) — good intent; needs review for bundling secrets, install path, uninstall, and that it points at a single canonical `dist`. | 🟡 Medium |
| **Runtime behaviour** | *Unverified — requires Windows + Ollama.* Cannot measure startup time, RAM, crash recovery from this Linux audit sandbox. | n/a |

**Logging/telemetry:** `tom_logs/startup.log`, `safety_log.txt`, per-agent `*_history.jsonl`/`*_state.json`/`*.pid` exist (good baseline), but there is no structured crash reporter, no rotation policy observed, and no in-app log viewer.

---

## 9. Agent Capability Audit (requested checklist)

Legend: ✅ works · ⚠️ partial/awkward/GUI-only · 🟥 missing/fake. "Verified" = source confirms a real implementation path; runtime success still depends on Windows + installed externals (Ollama, Tesseract, Blender, MS Office not required for python-docx/openpyxl/pptx).

| Requested capability | Verdict | Root cause / required work if not ✅ |
|---|---|---|
| Open applications | ✅ | `os_tools` |
| Open WhatsApp | ✅ | `whatsapp_tools.open_whatsapp` |
| Send messages (WhatsApp) | ✅ | native + web automation |
| Open Word / create/edit docs | ✅ | python-docx |
| Open Excel / create spreadsheets | ✅ | openpyxl |
| Clean data | ✅ | `data_analysis.auto_clean` |
| Analyze data / insights | ✅ | `data_analysis.generate_insights` |
| Generate charts | ⚠️ | matplotlib PNG only; **no interactive dashboards**. Add plotly/HTML export path |
| **Generate Power BI reports** | 🟥 | **No Power BI integration.** Need: Power BI REST API / `.pbix` templating, or honestly relabel as "BI dashboard (HTML)" |
| Open VS Code | ⚠️ | can launch; **no in-IDE automation** (would need VS Code CLI/extension or LSP) |
| Write code | ✅ | code LLM + `file_tools` |
| **Run code** | ⚠️ | only narrow/test paths; need a sandboxed runner (subprocess + timeouts + capture) wired to chat |
| Build websites | ⚠️ | generates files; **no run/preview/deploy**. Add local server + browser preview + (optional) deploy |
| Build applications | ⚠️ | scaffolds/codegen; no compile/package/run for mobile/desktop targets |
| Create presentations | ✅ | python-pptx |
| Manage files | ✅ | `file_tools` |
| Automate workflows | ⚠️ | `scheduler`/daemons exist; **no user-facing workflow builder**; engines not chainable from NL |
| Execute multi-step tasks | ⚠️ | `autonomous_agent` + orchestrator exist but **GUI-only**, not in CLI, not NL-routed in chat |

**Net:** **9/19 fully ✅, 9/19 ⚠️ partial, 1/19 🟥 fake.** The "professional personal assistant" core (apps, docs, email, data, web, messaging, voice) is genuinely there; the "developer/automation/BI" tier is partial, GUI-trapped, or substituted.

---

## 10. Security Audit

| # | Issue | Evidence | Severity | Fix |
|---|---|---|---|---|
| S1 | **No `.gitignore`; secrets in repo root.** `.env` (has `EMAIL_PASSWORD`), `google-credentials.json`, live `google-credentials_token.json`. Git has 0 commits, so not committed *yet* — one `git add .` exposes all. | root `ls`; `grep .gitignore`→none; `git ls-files`→none | 🔴 Critical | Add `.gitignore` (`.env`, `*credential*`, `*token*`, `*.pid`, `venv/`, `dist*/`, `build/`, `__pycache__/`, `*.zip`); rotate the email password + Google token **now** since they've existed in plaintext on disk; move secrets to OS keychain/credential manager |
| S2 | **`eval()` on external data.** `file_analyzer.py:196` `eval(s.get("avg_frame_rate","0/1"))` on ffprobe output. | line 196 | 🟠 High | Replace with `ast.literal_eval` or `num,den = map(int, s.split("/"))` |
| S3 | **`exec()` of generated Blender scripts.** `blender_control.py:523`. | line 523 | 🟡 Medium | Constrain to vetted templates; run Blender via `--python file` subprocess, not in-proc `exec` |
| S4 | **`shell=True` (4 sites).** `hardware_control.py:278/448/456`, `os_tools.py:188` (`f'"{chrome_path}" --profile-directory="{profile_id}"'`). | grep | 🟡 Medium | Pass arg lists, avoid `shell=True`; validate `profile_id` against an allow-list |
| S5 | **LLM-driven action surface w/ limited gating.** Agent can open apps, send email/WhatsApp, control mouse/keyboard. ApprovalManager + SafetyGuards exist and gate "sensitive"/destructive intents (good), but engine paths (Hardware) bypass the agent's safety gate entirely (split routing). | §2.2; `execute_task` safety vs GUI `_run_hardware` | 🟠 High | Route ALL actuators through one safety/approval gate |
| S6 | **Unsigned, UPX-packed 354 MB exe.** | spec | 🟠 High | Code-sign; consider dropping UPX; publish hashes |
| S7 | **Unpinned deps.** | `requirements.txt` | 🟡 Medium | Pin `==`, add hash-locked lockfile, enable Dependabot |
| S8 | **Migration/backup zips in tree** (`tom_migration_package.zip`, `web_version_backup_*.zip`). *Verified they do NOT currently contain `.env`/credentials*, but `prepare_migration_package.py` exists to bundle the project — must explicitly exclude secrets. | `unzip -l` (no secrets found) | 🟡 Medium | Add secret-exclusion to packager; never zip the tree wholesale |

---

## 11. Performance Audit

| Area | Finding | Impact | Fix |
|---|---|---|---|
| **Startup skill load** | `SkillManager` globs **911 SKILL.md** (47 + 864) on every launch and classifies each. | Slow cold start; memory; noisy routing | Lazy-load; index once to a cache; default `include_external=False`; only load what's installed |
| **Exe size** | 354 MB onefile, much dead weight (orphaned KB, 864 unused skills, vendored `.git`). | Slow first-extract, AV scans, distribution cost | Trim `datas`; onedir + installer; drop unused libs |
| **LLM dependency** | `gemma4:latest` (26–31B class) local inference. | Heavy RAM/VRAM; slow on CPU-only | Offer a small-model default + model tiering UX; surface "model not found/Ollama down" clearly |
| **Single-file UI** | 4,711-line Tkinter file, many `root.after` timers (orb/clock/ticker/queue). | UI jank risk; hard to profile | Split modules; throttle animations; move work off the Tk thread (already partly threaded) |
| **RAG writes** | Per-turn background `run_in_executor` stores to Chroma. | Generally fine; can grow unbounded | Add retention/compaction |
| **No caching of model/skill/knowledge** | recomputed per process | repeated cost | add warm caches |

*All performance items are static-analysis inferences; none are runtime-measured (no Windows/Ollama in audit sandbox).*

---

## 12. Missing Features (vs. the stated production end-state)

1. **Unified NL routing** so chat can reach ML/IoT/VLSI/Hardware/Blender/GameDev/Autonomous/Multi-Agent (today GUI-prefix-only).
2. **Knowledge integration** — wire `KnowledgeEngine` into the reasoning prompt (retrieval over `knowledge/*.md`).
3. **Real BI** — either true Power BI export or an honest interactive HTML dashboard generator.
4. **Code execution sandbox** — run generated code/sites with capture, timeout, preview.
5. **Capability centers in UI** — Skill, Tool, Knowledge, Automation, Agent, Developer, Data, Settings.
6. **Settings/secrets manager** — keys in keychain, model config, subsystem health, privacy controls.
7. **Workflow/automation builder** — chain steps, schedule, view run history.
8. **Observability** — in-app logs, crash reporter, subsystem status, telemetry (opt-in).
9. **Release engineering** — signing, single canonical build, pinned deps, CI, versioning, real git history.
10. **Test coverage** — `test_tom_comprehensive.py` + `sandbox_functional_tests.py` exist; need CI gating + coverage for routers and engines.
11. **CLI/GUI parity** — one capability set behind both front-ends.
12. **Cross-platform story** — currently Windows-centric (win32, `cmd /c`, `.exe`).

---

## 13. Root Cause Analysis

| Symptom | Root cause |
|---|---|
| GUI-only engines; CLI can't reach them; safety bypass | **Business logic placed in the Tkinter view layer** instead of a shared service/agent layer. The GUI grew its own dispatcher rather than extending `command_router` + `execute_task`. |
| Knowledge base unused | **Two memory systems built independently** (RAG vs KnowledgeEngine); the curated KB was authored but never connected to the prompt pipeline. |
| Power BI "works" but doesn't | **Capability advertised at the skill/keyword layer without a backing executor**; a substitute (matplotlib) was branded as the feature. |
| Rigid prefix syntax | **Engines were built CLI-first** with `startswith()` parsers and bolted onto buttons, never given to the NLP parser. |
| 708 MB duplicate exe, doc sprawl, no git | **No release engineering / version control discipline** — manual "save-as `dist_updated`," manual `PLAN_V2/3/4` docs, no commits. |
| Secrets on disk | **No secrets-management or repo-hygiene baseline** (`.gitignore`, keychain) was ever established. |
| Silent degradation | **Resilience-by-`try/except`-to-None** without surfacing state to the user. |

The unifying theme: **strong feature breadth, weak system integration & engineering discipline.** Capabilities were added vertically (each its own module + button) without a horizontal contract (one router, one safety gate, one memory, one capability registry, one UI pattern).

---

## 14. Prioritized Fix Roadmap

### P0 — Stop-the-bleeding (days)
1. **Secrets:** add `.gitignore`; rotate `EMAIL_PASSWORD` + Google token; move secrets to OS keychain. *(S1)*
2. **`eval`/`shell=True`:** fix `file_analyzer.py:196`; harden the 4 `shell=True` sites. *(S2,S4)*
3. **De-dupe build:** delete `dist_updated/`; pick one canonical `dist/`; document the build command. *(F6)*
4. **Initialise git properly** + first commit of a clean tree (secrets excluded).

### P1 — Make it trustworthy & coherent (2–4 weeks)
5. **Unify routing:** extract a `CapabilityRegistry`/service layer; move ML/IoT/VLSI/Hardware/Blender/GameDev/Autonomous/Multi-Agent/News/Env out of `tom_desktop_app.py` into the agent so **both CLI and GUI** reach them through `execute_task`. Route ALL actuators through SafetyGuards + ApprovalManager. *(§2.2, S5)*
6. **NL access to engines:** register engine intents with `nlp_parser`/`command_router` so chat understands "train a regression on sales.csv" or "generate ESP32 DHT11 MQTT firmware." Keep prefix syntax as an optional expert mode.
7. **Wire the knowledge base:** inject `KnowledgeEngine` retrieval into the prompt builder (or fold `knowledge/*.md` into RAG with a domain tag). Remove or revive `knowledge_engine`/`tom_tools` orphans.
8. **Honest capabilities:** relabel "Power BI" → "Interactive BI dashboard (HTML)"; either implement real Power BI export or scope it out.
9. **Pin dependencies** (`==` + lockfile).

### P2 — Productize (1–2 months)
10. **UI redesign** into capability centers (§7): Skill/Tool/Knowledge/Automation/Agent/Developer/Data/Settings; one NL entry point; subsystem health surfacing.
11. **Code-execution sandbox** + website preview/run.
12. **Release engineering:** code-sign, onedir+installer, trimmed `datas`, CI (lint+tests+build), semantic versioning, changelog from real git history.
13. **Observability:** in-app log viewer, crash reporter, opt-in telemetry.

### P3 — Scale & harden (quarter)
14. Cross-platform layer (abstract win32/`cmd`), DPI/accessibility, light theme.
15. Plugin/MCP connector browser + expanded connectors.
16. Test coverage targets (routers/engines ≥ 70%), perf budgets, model-tiering UX.

---

## 15. Production Readiness Score

Weighted scorecard (each 0–10, weighted; "Score" = my assessed rating from the evidence above).

| Dimension | Weight | Score /10 | Weighted | Basis |
|---|---:|---:|---:|---|
| Functionality breadth | 15% | 8 | 1.20 | Large, mostly-real capability set |
| Functional reliability / wiring | 15% | 4 | 0.60 | Split routing, fake Power BI, orphans |
| Architecture & maintainability | 12% | 3 | 0.36 | Logic in view layer; 4.7k-line UI; 2 routers |
| Security | 12% | 2 | 0.24 | Secrets on disk, no `.gitignore`, `eval`, unsigned |
| UI/UX & discoverability | 10% | 4 | 0.40 | Looks good, hard to discover/learn |
| Knowledge/skill utilization | 8% | 2 | 0.16 | KB orphaned; 864 skills loaded, few used |
| Build/release engineering | 8% | 2 | 0.16 | Dup 708 MB exe, unsigned, no git, doc sprawl |
| Testing & QA | 6% | 4 | 0.24 | Test files exist; no CI/coverage gate |
| Observability/telemetry | 6% | 3 | 0.18 | Logs exist; nothing surfaced; silent degrade |
| Performance/scalability | 8% | 4 | 0.32 | Heavy startup/exe; static-only assessment |
| **TOTAL** | **100%** | — | **≈ 3.86** | |

### **Production Readiness Score: 38 / 100** — *"Capable alpha; not production-ready."*

What moves the needle fastest: P0 security + P1 routing unification + knowledge wiring would realistically take this to ~60/100. The full P2 set targets ~80/100 (shippable beta).

---

## 16. Final Transformation Plan — to 100% capability utilization

The goal "every skill discoverable & mapped to a real function, every function to a workflow, every workflow to knowledge, no orphans" reduces to **six contracts** the system must adopt:

1. **One Capability Registry (single source of truth).**
   A declarative registry: `capability_id → {skill(s), executor fn, required_tools, knowledge_domains, ui_surface, safety_class, nl_intents, expert_syntax}`. `command_router`, `skill_manager`, `capability_resolver`, the GUI, and the CLI all read from it. This mechanically eliminates orphans (anything not in the registry is dead and flagged) and broken mappings (Power BI without an executor fails validation at build time).

2. **One Brain (service layer), two faces.**
   Move every engine into the agent/service layer behind `execute_task`. CLI and GUI become thin clients. Result: CLI/GUI parity, NL access everywhere, and every actuator passing through SafetyGuards + ApprovalManager.

3. **One Memory with domain knowledge wired in.**
   Fold `knowledge/*.md` into the retrieval path (KnowledgeEngine → prompt, or KB→RAG with domain tags). Every answer in a covered domain cites/uses the curated KB. Add a "Knowledge Center" UI so the asset is visible and editable.

4. **Honest capability contracts.**
   Each capability declares its real backing. No keyword advertises a feature without an executor. "Power BI" is either implemented (Power BI REST/`.pbix`) or relabelled to the HTML BI dashboard it actually produces.

5. **Capability-center UI.**
   Rebuild the UI around centers (Skill/Tool/Knowledge/Automation/Agent/Developer/Data/Settings) driven by the registry, so discoverability == registry coverage. One NL chat reaches all; expert syntax optional.

6. **Engineering discipline.**
   Real git history; `.gitignore` + keychain secrets; pinned deps + lockfile + CI; one signed, trimmed build; doc consolidation (retire PLAN_V2/3/4 and overlapping reports into `docs/`); test coverage gates on routers/engines; observability surfaced.

**Definition of done (measurable):**
- Registry coverage = 100% of advertised capabilities have a real executor (CI-enforced); orphan count = 0.
- CLI/GUI capability parity = 100%.
- Knowledge-domain answer coverage uses the KB (spot-checked).
- 0 secrets in tree; signed single build; deps pinned; CI green.
- NL-discoverability ≥ 90% (engines reachable by plain English).
- Production Readiness ≥ 80/100.

---

### Appendix A — Audit evidence index (selected)
- Entry points: `main.py` (209 LOC), `agent.py` (2,053), `tom_desktop_app.py` (4,711); first-party Python ≈ 39,165 LOC.
- Routing: `agent.py:296-628` (central), `tom_desktop_app.py:2766+` (GUI engines), `tools/command_router.py`.
- Skills: `tools/skill_manager.py:174-184`; 47 local + 864 external SKILL.md.
- Knowledge: `tools/knowledge_engine.py` (orphaned); `knowledge/` = 36 files.
- Build: `tom_desktop_app.spec`; `dist`/`dist_updated` identical MD5 `9f6af184ad1622a013d218f3add87eab`; warn file 1,056 lines (benign).
- Security: no `.gitignore`; `.env`/`google-credentials*.json` in root; `file_analyzer.py:196` `eval`; 4× `shell=True`.
- Orphans: `knowledge_engine, tom_tools, verify_tom_system, make_icon, prepare_migration_package`.
- Verified externally: **Gemma 4 is a real model (Google, April 2026)**, so `gemma4:latest` is plausible (confirm the exact local tag resolves).

*Prepared under the repo's own CLAUDE.md standards: verified-before-stated, runtime-unverifiable items explicitly flagged.*
