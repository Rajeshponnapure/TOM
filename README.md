<!-- ════════════════════════════════════════════════════════════════════════ -->
<!--  TOM — Local Autonomous Desktop Agent · flagship README                   -->
<!--  Hero banner is a self-contained animated SVG (docs/assets/banner.svg),   -->
<!--  so animation works on GitHub without any external service. Typing/badges -->
<!--  use shields.io + readme-typing-svg (render on GitHub with internet).     -->
<!--  Screenshot/GIF links point at docs/assets/* — see that folder's README   -->
<!--  for how to drop the real captures in. Missing files show alt-text.       -->
<!-- ════════════════════════════════════════════════════════════════════════ -->

<div align="center">

<img src="docs/assets/banner.svg" alt="TOM — Local Autonomous Desktop Agent" width="100%"/>

<br/>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=22&duration=2800&pause=700&color=4F8CFF&center=true&vCenter=true&width=840&lines=Correct+it+once.+It+remembers+next+time.;Long-term+memory+powered+by+Hindsight.;Files+%C2%B7+email+%C2%B7+docs+%C2%B7+browser+%C2%B7+desktop+%C2%B7+voice.;Not+a+chatbot.+An+agent+that+learns+your+workflow." alt="Tagline"/>

<br/><br/>

<!-- Tech / status badges -->
![Python](https://img.shields.io/badge/Python-3.11_only-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/LLM-Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![Playwright](https://img.shields.io/badge/Browser-Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)
![Windows](https://img.shields.io/badge/Platform-Windows_10%2F11-0078D6?style=for-the-badge&logo=windows&logoColor=white)

<!-- Live repo badges -->
![Stars](https://img.shields.io/github/stars/Rajeshponnapure/TOM?style=flat-square&color=4F8CFF)
![Forks](https://img.shields.io/github/forks/Rajeshponnapure/TOM?style=flat-square&color=7C5CFF)
![Issues](https://img.shields.io/github/issues/Rajeshponnapure/TOM?style=flat-square&color=EC4899)
![Last commit](https://img.shields.io/github/last-commit/Rajeshponnapure/TOM?style=flat-square)
![Repo size](https://img.shields.io/github/repo-size/Rajeshponnapure/TOM?style=flat-square)
![Top language](https://img.shields.io/github/languages/top/Rajeshponnapure/TOM?style=flat-square)

<!-- Feature flags -->
![Hindsight](https://img.shields.io/badge/Memory-Hindsight-22C55E?style=flat-square)
![Voice](https://img.shields.io/badge/Voice-STT_%2B_TTS-7C5CFF?style=flat-square)
![Safety](https://img.shields.io/badge/Safety-Approval--gated-EF4444?style=flat-square)
![RAG](https://img.shields.io/badge/Context-RAG_%2F_ChromaDB-EC4899?style=flat-square)

<br/>

### [ 🚀 Quick start ](#-quick-start) · [ 🧩 Features ](#-feature-showcase) · [ 🏛️ Architecture ](#️-architecture) · [ 🧠 Intelligence ](#-intelligence-layer) · [ 🛠️ Setup ](docs/SETUP.md) · [ ❓ FAQ ](#-faq)

</div>

---

<div align="center">

> ### TOM is a desktop automation agent that **gets better at your workflow the longer you use it.**
>
> Correct it once — *"PDFs go in Invoices, not Documents"* — and it applies that next week, to new
> files, however you phrase the request. Corrections, preferences and task outcomes live in
> **[Hindsight](https://github.com/vectorize-io/hindsight)** long-term memory; files, email, documents,
> browser and desktop control run on your own Windows machine.

</div>

<table align="center">
<tr>
<td align="center" width="33%">🧠<br/><b>Remembers how you work</b><br/><sub>Hindsight retain · recall · reflect — corrections carry across sessions</sub></td>
<td align="center" width="33%">🗣️<br/><b>One natural-language surface</b><br/><sub>GUI chat · 25 quick actions · CLI · voice — same brain behind all</sub></td>
<td align="center" width="33%">🛡️<br/><b>Safe by design</b><br/><sub>human approval before sending, deleting, running code; full audit trail</sub></td>
</tr>
</table>

---

## 🧠 TOM remembers how you work

**The problem.** Assistants forget. You tell one how you like your Downloads folder, your email
sign-off or your deck format, and next session you are explaining it again. Chat history is not
the fix: it is a transcript of what was *said*, not a record of what was *learned*.

**What TOM does.** Every correction and standing preference is stored as a fact in Hindsight.
Before every task TOM recalls the ones that matter and acts on them — and shows you which it used.

| | Session 1 (no memory) | You say once | Weeks later, new files, different wording |
|---|---|---|---|
| **Request** | `organize my downloads` | `No — PDFs always go in Invoices, not Documents.` | `tidy up my downloads folder` |
| **TOM** | Groups by type; invoices land in `Documents/` | *"Got it — I'll remember that."* `.pdf files → Invoices/` | **Remembering:** `.pdf → Invoices/` · `screenshot → Screenshots/` · `leave installers where they are` — then moves files accordingly |

### How Hindsight memory is used

| Operation | When TOM calls it | Code |
|---|---|---|
| **`retain`** | A correction or preference ("always…", "never…", "from now on…", "no, …") — tagged `preference`, indexed immediately so the very next request can use it | `TomAgent._retain_preference` |
| **`retain`** | Every finished task, with its outcome — tagged `task` + category, indexed in the background | `TomAgent._retain_outcome` |
| **`recall`** | Before every task, in parallel with request parsing (no added latency). Results go into every LLM prompt and into a visible *Remembering* card | `TomAgent.execute_task`, `_build_memory_context` |
| **`recall`** | Before organizing a folder — only `preference` memories, turned into concrete rules (`.pdf → Invoices/`, `leave installers`) that the file engine applies deterministically | `TomAgent.remembered_folder_rules`, `tools/memory_rules.py`, `tools/file_ops.py` |
| **`reflect`** | *"What have you learned about me?"* and the **Memory** view — a grouped summary of how you work | `TomAgent._memory_command` |
| **`reflect`** | Fallback with a JSON `response_schema` when recalled facts don't parse into folder rules | `memory_rules.FOLDER_RULES_SCHEMA` |

One bank per installation (`tom-<id>`), created with a mission that tells Hindsight what to learn.
Every call is time-boxed; if Hindsight is unreachable TOM keeps working and queues retains to disk,
syncing them on the next successful call ([`tools/hindsight_memory.py`](tools/hindsight_memory.py)).

```text
 you ──► TomAgent.execute_task
            │  ┌──────────── recall(request) ◄──────────────┐
            ├──┤ parse request (NLP)          Hindsight bank │
            │  └──► memories → prompts + "Remembering" card  │
            ▼                                                │
   router → file engine / email / docs / web / desktop       │
            │                                                │
            └──► retain(outcome) ─────────────────────────────┤
 "no — PDFs go in Invoices" ──► retain(preference) ──────────┘
 "what have you learned?"   ──► reflect()
```

Learn more: [Hindsight on GitHub](https://github.com/vectorize-io/hindsight) ·
[Hindsight docs](https://hindsight.vectorize.io/) ·
[What is agent memory?](https://vectorize.io/what-is-agent-memory)

**Try it:** [demo/DEMO_SCRIPT.md](demo/DEMO_SCRIPT.md) — `python demo/seed_history.py --fresh` then
`python demo/run_demo.py` (add `--offline` to run without any accounts).

Memory commands anywhere (chat, CLI, voice): `what have you learned about me?` ·
`what do you remember about <topic>` · `memory status` · `remember that …`

---

## 🗺️ Navigation

<div align="center">

| Get going | Understand it | Go deeper |
|:--|:--|:--|
| [🚀 Quick start](#-quick-start) | [🧩 Feature showcase](#-feature-showcase) | [🧱 Module / capability reference](#-module--capability-reference) |
| [🛠️ Configuration](#️-configuration) | [🏛️ Architecture](#️-architecture) | [🗂️ Project structure](#️-project-structure) |
| [🖥️ The desktop app](#️-the-desktop-app) | [🔀 Command workflow](#-command-workflow) | [🧪 Testing & CI](#-testing--ci) |
| [📦 Build & deploy](#-build--deploy) | [🧠 Intelligence layer](#-intelligence-layer) | [🤝 Contributing](#-contributing) |
| [🩹 Troubleshooting](#-troubleshooting) | [🤖 Models](#-models) | [🗓️ Roadmap](#️-roadmap) · [❓ FAQ](#-faq) |

</div>

---

## ✨ Demo

<div align="center">

<img src="docs/assets/demo.gif" alt="TOM organizes Downloads with defaults, is corrected once, then applies the remembered rules to a new batch of files" width="70%"/>

<sub>Organize → one correction → weeks later, <i>"tidy up my downloads folder"</i>: the remembered rules are applied unprompted.
Recorded from the real desktop app with the offline memory stand-in (<code>tests/fake_hindsight.py</code>) so the clip is reproducible.</sub>

</div>

<table>
<tr>
<td width="50%"><img src="docs/assets/dashboard.png" alt="TOM dashboard — animated orb, live status and quick actions"/></td>
<td width="50%"><img src="docs/assets/chat.png" alt="Chat — a green Remembering card lists the rules recalled from memory before TOM acts"/></td>
</tr>
<tr>
<td align="center"><sub>🟦 Dashboard — animated orb + quick actions</sub></td>
<td align="center"><sub>🟩 Chat — the <b>Remembering</b> card shows which memories shaped the action</sub></td>
</tr>
</table>

---

## 🧩 Feature showcase

> The list below mirrors `tools/capability_registry.py`, which **CI validates against real
> executors** on every push. If a capability is listed here, it maps to code that runs —
> **no vapourware.** Every capability is reachable from the GUI chat, the quick-action
> buttons, and the CLI (a few are GUI/CLI-only, noted inline).

<table>
<tr>
<td align="center" width="25%">📄<br/><b>Documents</b><br/><sub>Word · Excel · PPT · PDF · letters</sub></td>
<td align="center" width="25%">✉️<br/><b>Communication</b><br/><sub>email draft/send · inbox triage · WhatsApp · Slack · Discord · Telegram</sub></td>
<td align="center" width="25%">📊<br/><b>Data &amp; ML</b><br/><sub>analysis · dashboards · ML · vision</sub></td>
<td align="center" width="25%">🌐<br/><b>Web</b><br/><sub>search · site gen · scrape · verify · safety</sub></td>
</tr>
<tr>
<td align="center">🖥️<br/><b>System &amp; desktop</b><br/><sub>open apps · OCR · mouse/kbd · file ops</sub></td>
<td align="center">💻<br/><b>Code &amp; dev</b><br/><sub>write/run code · IoT · VLSI · games · Blender</sub></td>
<td align="center">🤖<br/><b>Agents</b><br/><sub>autonomous · multi-agent · daemons · MCP · scheduler</sub></td>
<td align="center">🎙️<br/><b>Voice &amp; brain</b><br/><sub>voice mode · RAG memory · skills · self-evolution</sub></td>
</tr>
</table>

<details open>
<summary><b>📄 Documents</b></summary>

| Capability | Example command | Executor |
|---|---|---|
| Word documents | `create a professional Word document about renewable energy` | `agent.py::_create_word_doc` |
| Excel spreadsheets | `create an Excel spreadsheet for a monthly budget` | `agent.py::_create_excel` |
| PowerPoint decks | `create a PowerPoint about our Q3 results` | `agent.py::_execute_presentation` |
| PDF reports | `create a PDF report about market trends` | `agent.py::_create_pdf` |
| Letters / essays / long-form | `write a formal letter to my landlord` | `agent.py::_execute_document_writing` |

</details>

<details>
<summary><b>✉️ Communication</b></summary>

| Capability | Example | Notes |
|---|---|---|
| Draft context-aware emails | `write an email to John about the meeting` | LLM-drafted |
| Send email | `send email to john@x.com` | **approval-gated** |
| Inbox triage (summarize · rank · draft replies) | `check my inbox` | Gmail OAuth / IMAP |
| WhatsApp messages (approved first; exact number if known) | `send Mom a message on WhatsApp saying I'll be late` | WhatsApp Desktop (Windows) or WhatsApp Web |
| Slack / Discord / Telegram messages (approved first, confirmed by the service) | `message Ravi on telegram: running late` | bot token / webhook in `.env` |

</details>

<details>
<summary><b>📊 Data, analysis &amp; machine learning</b></summary>

| Capability | Example |
|---|---|
| Full pipeline: clean → insights → charts → **HTML dashboard** | `analyze the data in sales.csv` |
| Analyze any file (image / PDF / media) | `analyze file: C:\reports\scan.pdf` |
| ML — regression · classification · clustering · forecast · anomaly | `train a regression model` |
| Image / vision analysis | `analyze this image` |

`tools/ml_engine.py` auto-detects backends (scikit-learn, optionally XGBoost / LightGBM /
CatBoost / PyTorch / TensorFlow) and degrades gracefully when one is absent.

</details>

<details>
<summary><b>🌐 Web</b></summary>

| Capability | Example |
|---|---|
| Web search + research | `search the web for the latest on Llama models` |
| Generate websites (live browser preview) | `create a website for a coffee shop` |
| Verify running web apps / localhost | `verify web app on localhost:3000` |
| Website safety analysis | `check website safety: https://example.com` |
| Scrape web tables → CSV | `scrape the tables from <URL>` |
| Download files from URLs (capped 200 MB) | `download the file from <URL>` |

</details>

<details>
<summary><b>🖥️ System &amp; desktop</b></summary>

| Capability | Example |
|---|---|
| Open any installed application | `open chrome` |
| Read the screen via OCR (Tesseract) | `read my screen` |
| Mouse / keyboard / volume control | `move mouse to 500 300`, `volume to 40` |
| Create / read / manage files | `create file notes.txt`, `read file report.md` |
| File ops: find / organize / rename / zip | `organize my downloads folder by type` *(dry-run + approval)* |
| Convert images between formats | `convert all images in pictures to png` |

</details>

<details>
<summary><b>💻 Code &amp; development</b></summary>

| Capability | Example |
|---|---|
| Write code projects | `write code for a REST API in FastAPI` |
| Run Python files | `run code script.py` *(sandboxed · approval-gated · timed)* |
| Run Node.js files | `run app.js` *(approval-gated)* |
| Run shell commands | `run shell: dir` *(approval-gated · denylisted)* |
| Debug / fix code | `fix my code` |
| Python env / dependency management | `create venv`, `check dependency conflicts` |
| IoT firmware (ESP32 / Arduino / MicroPython) | `generate esp32 dht11 mqtt firmware` |
| VLSI / Verilog / VHDL / RTL / embedded | `create a verilog counter width=8` |
| Game scaffolding (pygame / Unity / Godot) | `scaffold a pygame platformer` |
| Blender 3D control | `blender create a terrain` |

</details>

<details>
<summary><b>🤖 Agents &amp; automation</b></summary>

| Capability | Example |
|---|---|
| Autonomous multi-step (plan → research → execute → verify → learn) | `execute autonomous task: research and summarize X` |
| Multi-agent orchestration (CEO/CTO/CMO/CPO/CFO/COO) | `deploy multi-agent task: launch a product page` |
| Scaffold new sub-agents | `build agent called price_watcher` |
| Email agent daemon | `start email agent` |
| Instagram agent daemon + AI-news reports | `start instagram agent` |
| News briefings & roundups | `give me the daily briefing` |
| Schedule **any** task on a repeat interval | `schedule: check inbox every 2 hours` |
| Background task scheduling (APScheduler) | `schedule instagram reports` |
| MCP connectors (GitHub / Slack / Notion / Calendar / Weather …) | `check my github repos` |
| Self-update checks | `update tom` |

</details>

<details>
<summary><b>🎙️ Voice &amp; intelligence</b></summary>

| Capability | Notes |
|---|---|
| Voice conversation mode | Speech-to-text in, text-to-speech out · GUI + CLI |
| Text emotion analysis | `analyze emotion text: ...` |
| Curated knowledge retrieval | auto-injected into relevant queries |
| Skill-guided expertise | 47 local skills, +864 opt-in (auto-routed) |
| Semantic conversation memory (RAG / ChromaDB) | remembers everything by meaning |
| Self-evolution from feedback | learns your preferences from reward/penalty |

</details>

---

## 🧰 Technology stack

<div align="center">

**Core brain**
&nbsp;
![Ollama](https://img.shields.io/badge/Ollama-000000?logo=ollama&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?logo=langchain&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6F61)
![sentence--transformers](https://img.shields.io/badge/sentence--transformers-FFD21E)

**Automation**
&nbsp;
![Playwright](https://img.shields.io/badge/Playwright-2EAD33?logo=playwright&logoColor=white)
![PyAutoGUI](https://img.shields.io/badge/PyAutoGUI-306998)
![Tesseract](https://img.shields.io/badge/Tesseract_OCR-5C3EE8)
![APScheduler](https://img.shields.io/badge/APScheduler-2C5BB4)

**Data / ML**
&nbsp;
![pandas](https://img.shields.io/badge/pandas-150458?logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?logo=numpy&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?logo=scikitlearn&logoColor=white)
![Matplotlib](https://img.shields.io/badge/Matplotlib-11557C)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?logo=plotly&logoColor=white)

**UI / docs / packaging**
&nbsp;
![Tkinter](https://img.shields.io/badge/Tkinter-3776AB?logo=python&logoColor=white)
![python-docx](https://img.shields.io/badge/python--docx-2B579A)
![python-pptx](https://img.shields.io/badge/python--pptx-D24726)
![ReportLab](https://img.shields.io/badge/ReportLab-PDF-red)
![PyInstaller](https://img.shields.io/badge/PyInstaller-EXE-yellow)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?logo=pytest&logoColor=white)

</div>

---

## 🏛️ Architecture

TOM is a layered local platform. One agent core (`agent.py` → `TomAgent`) sits behind every
surface and routes each request through safety, intent, and specialized engines.

```mermaid
flowchart TB
    subgraph UI["🖥️ Surfaces"]
        G["Tkinter GUI<br/>chat · 25 quick actions"]
        C["CLI · main.py"]
        V["Voice I/O<br/>STT + TTS"]
    end

    subgraph CORE["🧠 Agent core — agent.py · TomAgent"]
        SG["🛡️ SafetyGuards<br/>allow/deny + audit"]
        CR["🧭 CommandRouter<br/>intent + metadata"]
        ER["⚙️ EngineRouter"]
        SK["🧩 SkillManager"]
        KN["📚 KnowledgeEngine"]
        RAG["🔎 RAG memory"]
    end

    subgraph ENG["🚀 Specialized engines — tools/"]
        B["Browser · Playwright"]
        D["Desktop · PyAutoGUI / OCR"]
        DOC["Docs · Word/Excel/PPT/PDF"]
        ML["ML · IoT · VLSI · GameDev · Blender"]
        AG["Autonomous · Multi-agent · MCP · Scheduler"]
    end

    subgraph SVC["🔌 Services & data"]
        O["Ollama models"]
        CH["ChromaDB vectors"]
        EM["Gmail OAuth / IMAP"]
        FS["Local files · logs"]
    end

    UI --> SG --> CR
    CR --> ER & SK & KN & RAG
    ER --> ENG
    SK --> ENG
    ENG --> AP{"Sensitive?"}
    AP -->|yes| HL["✋ ApprovalManager"] --> OUT
    AP -->|no| OUT["📒 Result + outcome log + learning"]
    CORE --> SVC
    ENG --> SVC

    classDef g fill:#EF4444,stroke:#fff,color:#fff
    classDef b fill:#7C5CFF,stroke:#fff,color:#fff
    classDef d fill:#22C55E,stroke:#fff,color:#fff
    class SG,HL g
    class CR,ER,SK,KN,RAG b
    class OUT d
```

> Full layer-by-layer spec, DB schema, and plugin contract live in [ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 🔀 Command workflow

What happens between you typing and TOM acting:

```mermaid
sequenceDiagram
    autonumber
    actor U as You
    participant G as GUI / CLI / Voice
    participant T as TomAgent
    participant S as SafetyGuards
    participant R as Routers (Command/Engine/Skill)
    participant E as Executor
    participant A as ApprovalManager

    U->>G: "send email to boss about the delay"
    G->>T: execute_task(command)
    T->>S: gate(command)
    S-->>T: allowed
    T->>R: classify intent + extract metadata
    R->>T: route = email_send
    T->>E: draft email (LLM) + recall context (RAG)
    E-->>T: draft ready
    T->>A: request approval (sensitive)
    A-->>U: show approval modal
    U-->>A: ✅ approve
    A-->>E: send via Gmail
    E-->>T: sent
    T-->>G: result + honest outcome log
```

Routing is **additive & failure-isolated**: no clear engine match → falls through to normal
skill/chat routing. Engines are lazy-loaded — a missing optional dependency degrades to an
explanatory message instead of crashing.

---

## 🖥️ The desktop app

`tom_desktop_app.py` is a Tkinter shell tuned for a bright room and high contrast (design
rationale: [PRODUCT.md](docs/PRODUCT.md)). Opens at **1420×880**.

```
┌──────────────┬───────────────────────────────────────────────┐
│  ▦ Dashboard │   ◍ animated "alive" orb · live status         │
│  ▤ Chat      │   ▸ 25 quick-action buttons                    │
│  ◎ System    │   ┌─────────────────────────────────────────┐  │
│  ▧ Charts    │   │  chat / active view                     │  │
│  ▥ Files     │   │  + approval modals (sensitive actions)  │  │
│  ◈ Capabil.  │   └─────────────────────────────────────────┘  │
│  ⚕ Health    │   profiles: Core TOM · Email · Instagram        │
│  ◉ Memory    │   what TOM has learned · recall · reflect       │
│  ♪ Voice     │   ▶ Run Agent      ♫ Voice Mode                 │
└──────────────┴───────────────────────────────────────────────┘
```

| View | What it shows |
|---|---|
| **Dashboard** | Animated orb, live status, metrics, **25 quick actions** |
| **Chat** | Main conversation + approval modals |
| **System / Charts / Files** | Runtime panels |
| **Capabilities** | Browsable list of everything TOM can do |
| **Health** | Runtime capability-health report (`tools/capability_health.py`) |
| **Memory** | Long-term memory status, *What have you learned?* (reflect), recall search, recently stored rules and outcomes. Answers shaped by memory show a green **Remembering** card in Chat |

**Agent profiles:** Core TOM · Email Agent · Instagram Agent. **Voice Mode** opens a
push-to-talk window. Shortcuts: `Ctrl+D` Dashboard · `Ctrl+C` Chat.

---

## 🧠 Intelligence layer

| Layer | Module | What it gives you |
|---|---|---|
| 🧠 **Long-term memory** | `tools/hindsight_memory.py` | Hindsight retain/recall/reflect — corrections, preferences and task outcomes that carry across sessions. Offline queue, never blocks a task. |
| 📏 **Memory → rules** | `tools/memory_rules.py` | Spots corrections/preferences; turns recalled facts into concrete folder rules the file engine applies. |
| 🔎 **RAG memory** | `tools/rag_memory.py` | ChromaDB + `nomic-embed-text`; recalls conversations/docs/knowledge by *meaning*. Runs locally. |
| 🌱 **Self-evolution** | `tools/self_evolution.py` | Adaptive prompting from reward/penalty; learns your preferences. No GPU training. |
| 🧩 **Skills** | `tools/skill_manager.py` | 47 local domain skills + opt-in `SKILL.md` packs, classified knowledge-only vs executable. |
| 📈 **Skill telemetry** | `tools/skill_telemetry.py` | Tracks which skills actually run + complete/fail/degrade. |
| ⚕️ **Capability health** | `tools/capability_health.py` | Runtime self-check (shown in the Health view). |
| 📚 **Knowledge base** | `knowledge/` | JSON domain packs (Game Dev, 3D/CGI, Web, Cybersecurity, Data Science & AI, Mobile, Medical) + Markdown notes, auto-injected. |

---

## 🤖 Models

**Model-agnostic** — every slot is an env var, hot-swappable at runtime via `switch_model(name)`.

| Slot | Env var | Default |
|---|---|---|
| 🧠 Primary (complex reasoning) | `OLLAMA_MODEL` | `gemma4:latest` |
| ⚡ Fast (parsing · NLP · chat) | `OLLAMA_FAST_MODEL` | `qwen2.5-coder:7b-instruct` |
| 💻 Code generation | `OLLAMA_CODE_MODEL` | `qwen2.5-coder:7b-instruct` |
| 🔢 Embeddings (RAG memory) | `OLLAMA_EMBED_MODEL` | `nomic-embed-text:latest` |

> Ollama offline → UI still starts, but reasoning, planning, and RAG memory are limited.

**Hosted by default:** set `GROQ_API_KEY` in `.env` and every chat slot runs on Groq
(`GROQ_MODEL`, default `openai/gpt-oss-120b`) through the same interface
([`tools/llm_factory.py`](tools/llm_factory.py)) — no `TOM_LLM_PROVIDER` needed. To force the
local model instead, set `TOM_LLM_PROVIDER=ollama`; TOM never falls back to local on its
own. The embedding slot stays local either way (Groq has no embeddings endpoint).

---

## 🚀 Quick start

> ⚠️ **Requires Python 3.11.x specifically** (not 3.10, not 3.12). Full guide → [SETUP.md](docs/SETUP.md).

```mermaid
flowchart LR
    A["① Install<br/>Python 3.11"] --> B["② setup_python311_env.bat<br/>(.venv311 + deps)"]
    B --> C["③ ollama serve<br/>+ pull 3 models"]
    C --> D["④ copy .env.example .env<br/>+ HINDSIGHT_API_KEY"]
    D --> E["⑤ launch_tom_ui.bat"]
    E --> F["🎉 TOM running"]
    classDef done fill:#22C55E,stroke:#fff,color:#fff
    class F done
```

```powershell
# 1️⃣  Create the 3.11 environment + install deps (one-time)
setup_python311_env.bat

# 2️⃣  Start Ollama and pull the models
#     (or set GROQ_API_KEY in .env and skip this — Groq is used automatically;
#      only the embedding model below is still needed locally)
ollama serve
ollama pull gemma4:latest
ollama pull qwen2.5-coder:7b-instruct
ollama pull nomic-embed-text:latest

# 3️⃣  Copy config and add your Hindsight key so TOM remembers across sessions
copy .env.example .env
#     HINDSIGHT_API_KEY=...   (Hindsight Cloud)  — or HINDSIGHT_BASE_URL for a self-hosted server

# 4️⃣  Launch
launch_tom_ui.bat
```

| Launcher | When to use |
|---|---|
| `launch_tom_ui.bat` | Normal launch (auto-finds Python 3.11, checks deps) |
| `launch_tom_safe.bat` | Voice disabled, console visible — **use first if it crashes** |
| `launch_tom_debug.bat` | Console visible for full tracebacks |
| `create_desktop_shortcut.bat` | Puts a double-clickable **TOM** icon on your Desktop |
| `python main.py` | CLI mode (no GUI) |
| Desktop **TOM** shortcut | Built `dist\tom_desktop_app.exe`, or the source app via `launch_tom_ui.vbs` if there is no build |

---

## ⚙️ Configuration

Settings live in `.env` (copy from [.env.example](.env.example)). Nothing is required to
*start* — every value has a default.

<details>
<summary><b>Show all config groups</b></summary>

- **Long-term memory:** `HINDSIGHT_API_KEY` (Hindsight Cloud) or `HINDSIGHT_BASE_URL`
  (self-hosted), `HINDSIGHT_BANK_ID`, `HINDSIGHT_TIMEOUT_SECONDS`, `HINDSIGHT_ENABLED`.
- **LLM provider:** `GROQ_API_KEY` (hosted Groq is the default the moment this is set),
  `TOM_LLM_PROVIDER` (`ollama` forces local; also accepts `local`), `GROQ_MODEL`,
  `GROQ_FAST_MODEL`, `GROQ_CODE_MODEL`, `GROQ_VISION_MODEL`, `NLP_PARSE_TIMEOUT_SECONDS`.
  A variable already exported in your shell wins over `.env`; TOM reports the conflict in chat.
- **Core (LLM):** `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_FAST_MODEL`,
  `OLLAMA_CODE_MODEL`, `OLLAMA_EMBED_MODEL`, `OLLAMA_TIMEOUT_SECONDS`, `TASK_TIMEOUT_SECONDS`.
- **Email** (Gmail/inbox): `EMAIL_ADDRESS`, `EMAIL_PASSWORD` (app password) **or**
  `GMAIL_CREDENTIALS_FILE` / `GMAIL_TOKEN_FILE` (OAuth), `IMAP_HOST`, `IMAP_PORT`, `IMAP_SSL`,
  `SMTP_SERVER`, `SMTP_PORT`, `SMTP_STARTTLS`, `EMAIL_AUTO_REPLY_ENABLED` (opt-in, off by default)
  → see [GMAIL_OAUTH_SETUP.md](docs/GMAIL_OAUTH_SETUP.md); create the OAuth token with
  `python tools/generate_gmail_token.py`.
- **WhatsApp:** `WHATSAPP_MODE` (`auto` / `web` / `desktop`), `WHATSAPP_CONTACTS` (name → phone number,
  so a message goes to an exact chat instead of a name search).
- **Chat apps:** `SLACK_BOT_TOKEN`, `DISCORD_WEBHOOK_URL` / `DISCORD_WEBHOOKS`,
  `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHATS`. Without them TOM opens the app and says nothing was sent.
- **Instagram agent:** `INSTAGRAM_CHROME_PROFILE`, `INSTAGRAM_POSTS_PER_RUN`,
  `INSTAGRAM_CHECK_INTERVAL_SECONDS`, `INSTAGRAM_AUTO_SEND_REPORT_EMAIL`, …
- **Browser:** `CHROME_EXECUTABLE`, `CHROME_PROFILE_PATH`.
- **OCR:** `TESSERACT_CMD` (only if Tesseract isn't on PATH).
- **Voice:** `VOICE_INPUT_ENABLED`, `VOICE_OUTPUT_ENABLED`, `TOM_VOICE`, `TOM_VOICE_RATE`,
  `VOICE_RECOGNITION_ENGINE`, tuning thresholds.

</details>

> ✅ **No API keys** for Chrome automation, Instagram/YouTube browsing, or local Office —
> those use your signed-in browser session and local apps.

Full annotated reference: [.env.example](.env.example).

---

## 🧱 Module / capability reference

TOM has no public HTTP API — it's a local agent. The "API" is the **capability registry**
(`tools/capability_registry.py`): a single source of truth mapping each advertised
capability to a real executor. `validate()` proves every executor exists; `find_orphan_tools()`
proves no tool module is dead. **CI fails the build if either contract breaks.**

<details>
<summary><b>Capability → executor map (excerpt)</b></summary>

| ID | Capability | Executor |
|---|---|---|
| `word_doc` | Create Word documents | `agent.py::_create_word_doc` |
| `excel` | Create Excel spreadsheets | `agent.py::_create_excel` |
| `email_send` | Send emails (with approval) | `agent.py::execute_email_send_flow` |
| `data_analysis` | Clean→insights→charts→dashboard | `tools/data_analysis.py::DataAnalysisEngine.generate_report` |
| `ml` | ML train/predict | `tools/engine_router.py::EngineRouter._run_ml` |
| `website_build` | Generate websites | `agent.py::execute_website_creation` |
| `code_run` | Run Python (sandboxed) | `tools/code_runner.py::CodeRunner.run_python_file` |
| `iot` | IoT firmware | `tools/engine_router.py::EngineRouter._run_iot` |
| `vlsi` | Verilog / RTL | `tools/engine_router.py::EngineRouter._run_vlsi` |
| `autonomous` | Multi-step autonomous | `tools/autonomous_agent.py::AutonomousAgent.execute` |
| `multi_agent` | CEO/CTO/CMO orchestration | `tools/agent_orchestrator.py::AgentOrchestrator.execute_task` |
| `mcp` | External connectors | `agent.py::_handle_mcp_request` |
| `rag_memory` | Semantic memory | `tools/rag_memory.py::get_rag` |

…and ~30 more. See the registry file for the full, CI-checked list.

</details>

**Built-in MCP connectors** (`tools/mcp_manager.py`): `github`, `gmail`, `slack`, `notion`,
`whatsapp`, `instagram`, `calendar`, `weather`, `websearch`, `filesystem`, `database`.

---

## 🗂️ Project structure

```text
TOM/
├─ 🖥️  tom_desktop_app.py        # Tkinter GUI (primary entry point)
├─ 🧠  agent.py                  # TomAgent — orchestration, routing, execution, logging
├─ ⌨️   main.py                   # CLI entry point
├─ 🛡️  safety/guards.py          # allow/deny rules, protected paths, audit logging
├─ 🧰  tools/                    # capability engines (60+ modules)
│   ├─ command_router · engine_router · skill_manager · knowledge_engine
│   ├─ capability_registry · capability_health · skill_telemetry · approval
│   ├─ hindsight_memory · memory_rules · chat_memory · rag_memory
│   ├─ browser_tools · chrome_profiles · screen_tools · file_tools · file_ops
│   ├─ email_tools · whatsapp_tools · chat_apps · web_recipes · web_automation
│   ├─ code_runner · ml_engine · iot_engine · vlsi_engine · game_dev · blender_control
│   ├─ data_analysis · document_creator · pdf_tools · hardware_control
│   ├─ voice_tools · voice_enhanced · self_evolution · learning
│   └─ scheduler · autonomous_agent · agent_orchestrator · mcp_manager · news_agent …
├─ 🤖  agents/                   # discoverable sub-agents (email, instagram, ai-news)
├─ 📚  knowledge/                # JSON domain packs + Markdown notes
├─ 🧩  skills/                   # 47 numbered domain skills + SKILL.md packs
├─ ⚙️   config/                   # system_prompt.txt
├─ 🎨  resources/                # icons / artwork
├─ 📖  docs/                     # ARCHITECTURE · SETUP · GMAIL_OAUTH_SETUP · INSTAGRAM_WORKFLOW · …
├─ 🎬  demo/                     # scripted memory demo + recording script
├─ 📦  installer/                # Inno Setup script
├─ 🧪  tests/                    # pytest suite (tests/manual/scorecard.py = scored self-check)
├─ 🔁  .github/                  # CI workflow, issue/PR templates, Dependabot
├─ 🪟  *.bat / *.ps1 / *.vbs     # Windows launchers, setup, build
└─ 📌  requirements.txt · requirements-ci.txt · pyproject.toml
```

---

## 🧪 Testing & CI

```powershell
# Diagnostic self-check (imports, capabilities, optional libs)
.venv311\Scripts\python.exe tools\verify_tom_system.py

# Test suite (pyproject.toml pins --basetemp to .pytest_tmp for Windows)
.venv311\Scripts\python.exe -m pytest

# Lint gate used by CI (syntax errors, undefined names)
.venv311\Scripts\python.exe -m pip install ruff
.venv311\Scripts\python.exe -m ruff check .
```

**GitHub Actions** (`.github/workflows/ci.yml`) runs on every pull request and every push to `main`:

```mermaid
flowchart LR
    P["push / PR"] --> S["setup-python 3.11"]
    S --> C["compile all first-party modules"]
    C --> L["ruff check<br/>(syntax · undefined names)"]
    L --> T["pytest<br/>(routing · mail · chat apps · files · memory · registry integrity)"]
    T --> R{green?}
    R -->|yes| OK["✅ merge-ready"]
    R -->|no| X["❌ build fails"]
    classDef ok fill:#22C55E,stroke:#fff,color:#fff
    class OK ok
```

The suite covers command routing, engine detection, **capability-registry integrity** (no
fake capabilities, no orphan tools), and whole-agent runs through `TomAgent.execute_task`
against in-process fake SMTP / IMAP / Slack / Discord / Telegram servers (real sockets, no
network), a real Chromium page standing in for WhatsApp Web (skipped when Chromium isn't
installed), file organizing with undo, and the long-term-memory contract.

---

## 📦 Build & deploy

```powershell
build.bat        # cleans → PyInstaller via tom_desktop_app.spec → emits SHA256
# Output: dist\tom_desktop_app.exe  (+ dist\SHA256SUMS.txt)

SETUP_TOM.bat    # one-shot: env setup → build → Desktop shortcut

iscc installer\tom_installer.iss   # Windows installer (Inno Setup)
```

> ⚠️ Binary is **unsigned** → SmartScreen may warn on first run. **Rebuild after every code
> change** — the frozen EXE doesn't auto-pick-up edits and **does not read `.env`** (env-gated
> features fall back to bootstrap defaults; voice defaults ON in the bundle).

---

## ⚡ Performance & reliability highlights

- **Timeouts everywhere** — `OLLAMA_TIMEOUT_SECONDS` and `TASK_TIMEOUT_SECONDS` keep a slow
  model or stuck task from freezing the UI.
- **Lazy + failure-isolated engines** — a missing optional dependency degrades to a message,
  never a crash.
- **Honest outcome logging** — results recorded as success / partial / failed, not
  optimistically faked.
- **Multi-model routing** — heavy reasoning, fast parsing, and code generation use separate
  model slots so light tasks stay snappy.
- **Local-first** — no network round-trips for inference or memory.

---

## 🔒 Security & privacy

- ✋ **Human-in-the-loop approval** before sending email/messages, deleting or moving/renaming
  files, and running code/shell.
- 🛡️ **SafetyGuards** (`safety/guards.py`) apply allow/deny rules + a timestamped audit trail
  in `tom_logs/`.
- 📋 **File ops** that move/rename build a **dry-run plan first** with exact counts; system
  directories are never traversed.
- 📦 **Code/shell** runs in an isolated subprocess with a hard timeout + denylist — never
  in-process `exec()`.
- 🔑 **Secrets stay out of git** — `.env`, `*credentials*.json`, `*token*.json`, `*.pem`,
  `*.key` are git-ignored. No passwords in code; prefer OAuth / existing browser sessions.
- 🏠 **Everything local** — Ollama, ChromaDB memory, and your data stay on your machine.

---

## 🗓️ Roadmap

```mermaid
timeline
    title TOM evolution
    Shipped : Multi-surface agent core : Browser + desktop + OCR : Word/Excel/PPT/PDF gen : RAG memory + self-evolution : File-ops + web recipes + sandboxed runners : Capability registry + health + telemetry
    In progress : Richer approval UI : Per-app regression coverage : Skill telemetry-driven tuning
    Planned : SQLite memory/audit backend : Plugin metadata + install/update flow : FastAPI service for remote control : Power BI automation hooks
```

> Roadmap is distilled from [ARCHITECTURE.md](docs/ARCHITECTURE.md) §14. Items move as the code lands.

---

## 🤝 Contributing

```mermaid
flowchart LR
    F["🍴 Fork"] --> B["🌿 branch<br/>feat/your-change"]
    B --> C["💻 code + test<br/>pytest green"]
    C --> R["🔁 registry intact<br/>verify_tom_system.py"]
    R --> P["📤 PR to main"]
    P --> CI["🤖 CI runs compile + pytest"]
```

1. **Fork** and create a feature branch: `git checkout -b feat/my-change`.
2. Work in the **Python 3.11** env (`setup_python311_env.bat`).
3. Add a real executor for any new capability **and** register it in
   `tools/capability_registry.py` — CI rejects fake capabilities and orphan tools.
4. Run `pytest`, `ruff check .` and `python tools/verify_tom_system.py` before opening a PR (details in [CONTRIBUTING.md](CONTRIBUTING.md)).
5. Keep changes **additive and failure-isolated** (lazy imports, graceful degradation).
6. Match the house rules in [CLAUDE.md](CLAUDE.md) / [AGENTS.md](AGENTS.md): verify before
   you ship, no untested code, honest uncertainty.

---

## ❓ FAQ

<details>
<summary><b>Does TOM send my data to the cloud?</b></summary>

No. The LLM (Ollama), vector memory (ChromaDB), and your files all stay local. The only
network calls are ones you explicitly trigger — web search, browser automation on sites
you visit, or Gmail if you configure it.
</details>

<details>
<summary><b>Do I need any API keys?</b></summary>

Not for the core. Chrome automation, Instagram/YouTube browsing, WhatsApp-via-browser, and
local Office automation use your signed-in sessions. Only Gmail OAuth (optional) and some
MCP connectors need credentials.
</details>

<details>
<summary><b>Why Python 3.11 only?</b></summary>

The pinned dependency set and the frozen EXE build target 3.11. The launchers refuse other
versions to avoid hard-to-debug native/ABI mismatches.
</details>

<details>
<summary><b>Can I use a different model?</b></summary>

Yes — set `OLLAMA_MODEL` (and the fast/code/embed slots) to any Ollama model, or call
`switch_model(name)` at runtime to hot-swap all slots.
</details>

<details>
<summary><b>Voice won't start — what now?</b></summary>

Launch with `launch_tom_safe.bat` (voice off) to confirm the rest works, then install
`SpeechRecognition` + PyAudio (a prebuilt `cp311` wheel on Windows). See [SETUP.md](docs/SETUP.md).
</details>

<details>
<summary><b>Is there a web/remote UI?</b></summary>

Not yet — a FastAPI service is on the roadmap. Today TOM is a local Tkinter desktop app
(plus a CLI).
</details>

---

## 🩹 Troubleshooting

| Symptom | Fix |
|---|---|
| "TOM requires Python 3.11.x" | Install official Python 3.11, then `setup_python311_env.bat`. |
| "TOM dependencies are missing" | Re-run `setup_python311_env.bat`. |
| LLM replies limited / empty | Start Ollama (`ollama serve`) and pull the models above. |
| Voice error re `SpeechRecognition`/`pyaudio` | Install them; on Windows use a prebuilt PyAudio wheel (see docs/SETUP.md). |
| Voice misbehaving | `launch_tom_safe.bat` (voice off) or `VOICE_INPUT_ENABLED=false`. |
| Chrome profile launch fails | Confirm Chrome installed + profile exists; optionally set `CHROME_PROFILE_PATH`. |
| Screen reading does nothing | Install Tesseract OCR; set `TESSERACT_CMD` if not on PATH. |
| EXE ignores edits / `.env` | Rebuild with `build.bat`; run from source for `.env`. |
| Memory screen says "CONNECTED but N memories are waiting to be saved" | Hindsight rejected or could not be reached; the reason is shown next to it (wrong/expired `HINDSIGHT_API_KEY`, no credits, offline). Nothing is lost: waiting memories are kept on disk and sent automatically on the next successful call or the next start. |
| TOM organized a different folder than the one I named | Give the full path (in quotes if it has spaces). Names like "downloads" mean your profile's folder; `TOM_DOWNLOADS_DIR` redirects that name (used by the demo sandbox). |
| pytest permission errors in temp | Don't override `--basetemp`; it's pinned to `.pytest_tmp` in `pyproject.toml`. |

Deeper setup + new-machine checklist → [SETUP.md](docs/SETUP.md).

---

## 🙌 Credits & license

**Author / owner:** Rajesh Ponnapureddy — built TOM as a daily-driver personal automation
agent (see [PRODUCT.md](docs/PRODUCT.md)).

Built on the open-source ecosystem: **Ollama**, **LangChain**, **ChromaDB**,
**sentence-transformers**, **Playwright**, **PyAutoGUI**, **Tesseract**, **pandas /
NumPy / scikit-learn**, **python-docx / python-pptx / ReportLab**, **APScheduler**,
**PyInstaller**, **pytest**.

Long-term memory by **[Hindsight](https://github.com/vectorize-io/hindsight)**
([docs](https://hindsight.vectorize.io/) · [what is agent memory?](https://vectorize.io/what-is-agent-memory)).

**License:** [MIT](LICENSE).

<div align="center">

<br/>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=18&duration=4000&pause=1000&color=7C5CFF&center=true&vCenter=true&width=620&lines=Verify+before+you+speak.;Test+before+you+ship.;Everything+local." alt="motto"/>

<br/>

⭐ **Star this repo** if TOM is useful — it helps a lot.

<sub>TOM — Local Autonomous Desktop Agent · Windows · Python 3.11 · Ollama</sub>

</div>
