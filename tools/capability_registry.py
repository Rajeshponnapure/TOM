"""
Capability Registry — the single source of truth for what TOM can do.

Every advertised capability maps to a REAL executor (file + function).
`validate()` proves each mapping exists (no fake capabilities), and
`find_orphan_tools()` proves no tool module is dead (no orphans).
CI runs both — the build fails if either contract breaks.

Executor format: "<relative file>::<function or Class.method>"
"""

import os
import re
from typing import Any, Dict, List

from tools.project_paths import PROJECT_ROOT

# Tool modules that are intentionally NOT runtime capabilities
# (developer/build utilities, test harnesses) — documented, not orphaned.
DEV_UTILITIES = {
    "make_icon": "build utility — generates the app icon",
    "prepare_migration_package": "packaging utility — creates migration zip (secrets excluded)",
    "verify_tom_system": "diagnostic script — run `python tools/verify_tom_system.py`",
    "smoke_tests": "test harness",
    "sandbox_functional_tests": "test harness",
    "instruction_loader": "internal helper consumed via compose_system_prompt",
    "project_paths": "internal path helper used by every module",
}

CAPABILITIES: List[Dict[str, Any]] = [
    # ── Documents ────────────────────────────────────────────────────────
    {"id": "word_doc", "label": "Create Word documents", "category": "documents",
     "triggers": ["create a word document about X"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::_create_word_doc"},
    {"id": "excel", "label": "Create Excel spreadsheets", "category": "documents",
     "triggers": ["create an excel spreadsheet for X"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::_create_excel"},
    {"id": "powerpoint", "label": "Create PowerPoint presentations", "category": "documents",
     "triggers": ["create a powerpoint about X"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::_execute_presentation"},
    {"id": "pdf_report", "label": "Create PDF reports", "category": "documents",
     "triggers": ["create a pdf report about X"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::_create_pdf"},
    {"id": "doc_writing", "label": "Write letters/essays/documents", "category": "documents",
     "triggers": ["write a formal letter to X"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::_execute_document_writing"},

    # ── Communication ────────────────────────────────────────────────────
    {"id": "email_write", "label": "Draft context-aware emails", "category": "communication",
     "triggers": ["write an email to X"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::_handle_email_write"},
    {"id": "email_send", "label": "Send emails (with approval)", "category": "communication",
     "triggers": ["send email to X"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::execute_email_send_flow"},
    {"id": "email_inbox", "label": "Inbox triage", "category": "communication",
     "triggers": ["check my inbox"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::execute_email_inbox_workflow"},
    {"id": "whatsapp", "label": "Send WhatsApp messages", "category": "communication",
     "triggers": ["whatsapp NAME saying MSG"], "surfaces": "chat+cli+gui",
     "executor": "tools/whatsapp_tools.py::WhatsAppTools.send_message"},

    # ── Data & analysis ─────────────────────────────────────────────────
    {"id": "data_analysis", "label": "Data analysis (clean→insights→charts→HTML dashboard)",
     "category": "data", "triggers": ["analyze the data in file.csv"], "surfaces": "chat+cli+gui",
     "executor": "tools/data_analysis.py::DataAnalysisEngine.generate_report"},
    {"id": "file_analysis", "label": "Analyze any file (image/pdf/media)", "category": "data",
     "triggers": ["analyze file: path"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::analyze_file"},
    {"id": "ml", "label": "ML: regression/classification/clustering/forecast/anomaly",
     "category": "data", "triggers": ["train a regression model", "ml classify knn"],
     "surfaces": "chat+cli+gui", "executor": "tools/engine_router.py::EngineRouter._run_ml"},

    # ── Web ──────────────────────────────────────────────────────────────
    {"id": "web_search", "label": "Web search + research", "category": "web",
     "triggers": ["search the web for X"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::_web_search"},
    {"id": "website_build", "label": "Generate websites (with browser preview)", "category": "web",
     "triggers": ["create website for X"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::execute_website_creation"},
    {"id": "web_verify", "label": "Verify web apps / localhost", "category": "web",
     "triggers": ["verify web app on localhost:3000"], "surfaces": "chat+cli+gui",
     "executor": "tools/engine_router.py::EngineRouter._run_webauto"},
    {"id": "web_safety", "label": "Website safety analysis", "category": "web",
     "triggers": ["check website safety: URL"], "surfaces": "chat+cli+gui",
     "executor": "tools/engine_router.py::EngineRouter._run_websafety"},

    # ── System & desktop ─────────────────────────────────────────────────
    {"id": "open_app", "label": "Open any installed application", "category": "system",
     "triggers": ["open chrome"], "surfaces": "chat+cli+gui",
     "executor": "tools/os_tools.py::OSTools.open_application"},
    {"id": "screen_read", "label": "Read screen via OCR", "category": "system",
     "triggers": ["read my screen"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::execute_screen_read"},
    {"id": "hardware", "label": "Mouse/keyboard/volume control", "category": "system",
     "triggers": ["move mouse to 500 300", "volume to 40"], "surfaces": "chat+cli+gui",
     "executor": "tools/engine_router.py::EngineRouter._run_hardware"},
    {"id": "files", "label": "Create/read/manage files", "category": "system",
     "triggers": ["create file X", "read file Y"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::execute_file_command"},

    # ── Code & dev ───────────────────────────────────────────────────────
    {"id": "code_write", "label": "Write code projects", "category": "dev",
     "triggers": ["write code for X"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::_execute_code_project"},
    {"id": "code_run", "label": "Run Python files (sandboxed, approval-gated)", "category": "dev",
     "triggers": ["run code script.py"], "surfaces": "chat+cli+gui",
     "executor": "tools/code_runner.py::CodeRunner.run_python_file"},
    {"id": "code_fix", "label": "Debug/fix code", "category": "dev",
     "triggers": ["fix my code"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::execute_code_help"},
    {"id": "env_mgmt", "label": "Python env/dependency management", "category": "dev",
     "triggers": ["create venv", "check dependency conflicts"], "surfaces": "chat+cli+gui",
     "executor": "tools/engine_router.py::EngineRouter._run_deps"},
    {"id": "iot", "label": "IoT firmware generation (ESP32/Arduino/MicroPython)", "category": "dev",
     "triggers": ["generate esp32 dht11 mqtt firmware"], "surfaces": "chat+cli+gui",
     "executor": "tools/engine_router.py::EngineRouter._run_iot"},
    {"id": "vlsi", "label": "VLSI/Verilog/RTL/embedded design", "category": "dev",
     "triggers": ["create a verilog counter width=8"], "surfaces": "chat+cli+gui",
     "executor": "tools/engine_router.py::EngineRouter._run_vlsi"},
    {"id": "gamedev", "label": "Game scaffolding (pygame/unity/godot)", "category": "dev",
     "triggers": ["scaffold a pygame platformer"], "surfaces": "chat+cli+gui",
     "executor": "tools/engine_router.py::EngineRouter._run_gamedev"},
    {"id": "blender", "label": "Blender 3D control", "category": "dev",
     "triggers": ["blender create a terrain"], "surfaces": "chat+cli+gui",
     "executor": "tools/engine_router.py::EngineRouter._run_blender"},

    # ── Agents & automation ──────────────────────────────────────────────
    {"id": "autonomous", "label": "Autonomous multi-step tasks", "category": "agents",
     "triggers": ["execute autonomous task: X"], "surfaces": "chat+cli+gui",
     "executor": "tools/autonomous_agent.py::AutonomousAgent.execute"},
    {"id": "multi_agent", "label": "Multi-agent orchestration (CEO/CTO/CMO)", "category": "agents",
     "triggers": ["deploy multi-agent task: X"], "surfaces": "chat+cli+gui",
     "executor": "tools/agent_orchestrator.py::AgentOrchestrator.execute_task"},
    {"id": "build_agent", "label": "Scaffold new sub-agents", "category": "agents",
     "triggers": ["build agent called X"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::build_agent"},
    {"id": "email_agent", "label": "Email agent daemon (start/stop/status)", "category": "agents",
     "triggers": ["start email agent"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::manage_email_agent"},
    {"id": "instagram_agent", "label": "Instagram agent daemon + reports", "category": "agents",
     "triggers": ["start instagram agent"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::manage_instagram_agent"},
    {"id": "news", "label": "News briefings & roundups", "category": "agents",
     "triggers": ["give me the daily briefing"], "surfaces": "chat+cli+gui",
     "executor": "tools/news_agent.py::NewsAgent.daily_briefing"},
    {"id": "scheduler", "label": "Background task scheduling", "category": "agents",
     "triggers": ["schedule instagram reports"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::schedule_instagram_reports"},
    {"id": "mcp", "label": "MCP connectors (GitHub/Slack/Calendar)", "category": "agents",
     "triggers": ["check my github repos"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::_handle_mcp_request"},
    {"id": "auto_update", "label": "Self-update checks", "category": "agents",
     "triggers": ["update tom"], "surfaces": "chat+cli+gui",
     "executor": "tools/engine_router.py::EngineRouter._run_autoupdate"},

    # ── Voice & intelligence ─────────────────────────────────────────────
    {"id": "voice", "label": "Voice conversation mode", "category": "voice",
     "triggers": ["talk / voice mode"], "surfaces": "cli+gui",
     "executor": "tools/voice_tools.py::VoiceTools.start_conversation_mode"},
    {"id": "emotion", "label": "Text emotion analysis", "category": "voice",
     "triggers": ["analyze emotion text: ..."], "surfaces": "chat+cli+gui",
     "executor": "tools/voice_enhanced.py::VoiceEnhanced.analyze_emotional_state"},
    {"id": "knowledge", "label": "Curated knowledge retrieval (auto-injected)", "category": "intelligence",
     "triggers": ["(automatic on every relevant query)"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::_build_knowledge_context"},
    {"id": "skills", "label": "Skill-guided expertise (47 local, +864 opt-in)", "category": "intelligence",
     "triggers": ["(automatic skill routing)"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::_handle_skill_routed_task"},
    {"id": "rag_memory", "label": "Semantic conversation memory", "category": "intelligence",
     "triggers": ["(automatic)"], "surfaces": "chat+cli+gui",
     "executor": "tools/rag_memory.py::get_rag"},
    {"id": "evolution", "label": "Self-evolution from feedback", "category": "intelligence",
     "triggers": ["reward / penalty"], "surfaces": "chat+cli+gui",
     "executor": "tools/self_evolution.py::get_evolution"},
    {"id": "vision", "label": "Image/vision analysis", "category": "intelligence",
     "triggers": ["analyze this image"], "surfaces": "chat+cli+gui",
     "executor": "agent.py::_analyze_image_with_vision"},
]


def validate() -> Dict[str, Any]:
    """Prove every capability's executor really exists. Returns report."""
    missing, checked = [], 0
    for cap in CAPABILITIES:
        file_part, func_part = cap["executor"].split("::", 1)
        fpath = os.path.join(str(PROJECT_ROOT), file_part.replace("/", os.sep))
        if not os.path.isfile(fpath):
            missing.append(f"{cap['id']}: file missing — {file_part}")
            continue
        with open(fpath, encoding="utf-8", errors="ignore") as f:
            src = f.read()
        target = func_part.split(".")[-1]
        if not re.search(rf"\bdef {re.escape(target)}\b", src):
            missing.append(f"{cap['id']}: function missing — {func_part} in {file_part}")
        checked += 1
    return {"total": len(CAPABILITIES), "verified": checked - len(missing),
            "missing": missing, "ok": not missing}


def find_orphan_tools() -> List[str]:
    """Tool modules referenced nowhere (excluding documented dev utilities)."""
    tools_dir = os.path.join(str(PROJECT_ROOT), "tools")
    referencing: List[str] = []
    scan_files = []
    skip_dirs = {"venv", "__pycache__", "awesome-claude-skills", "build",
                 "dist", ".git", "legacy", ".pytest_cache"}
    for base in (str(PROJECT_ROOT),):
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for fn in files:
                if fn.endswith(".py"):
                    scan_files.append(os.path.join(root, fn))
    blobs = {}
    for sf in scan_files:
        try:
            with open(sf, encoding="utf-8", errors="ignore") as f:
                blobs[sf] = f.read()
        except OSError:
            pass
    orphans = []
    for fn in sorted(os.listdir(tools_dir)):
        if not fn.endswith(".py") or fn == "__init__.py":
            continue
        mod = fn[:-3]
        if mod in DEV_UTILITIES:
            continue
        used = any(mod in blob for path, blob in blobs.items()
                   if not path.endswith(os.sep + fn))
        if not used:
            orphans.append(mod)
    return orphans


def summary_text() -> str:
    """Human-readable capability list for the 'what can you do' command."""
    by_cat: Dict[str, List[str]] = {}
    for cap in CAPABILITIES:
        by_cat.setdefault(cap["category"], []).append(
            f"  - {cap['label']}  (e.g. \"{cap['triggers'][0]}\")")
    lines = [f"TOM has {len(CAPABILITIES)} registered capabilities:\n"]
    for cat in ("documents", "communication", "data", "web", "system",
                "dev", "agents", "voice", "intelligence"):
        if cat in by_cat:
            lines.append(cat.upper())
            lines.extend(by_cat[cat])
            lines.append("")
    lines.append("Say 'system status' for live subsystem health.")
    return "\n".join(lines)
