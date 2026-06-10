"""
Dependency preflight — turns "it doesn't work" into "here is the exact fix".

For each capability we declare what it needs (Python modules, executables,
services). `check()` uses find_spec/which/socket only — nothing heavy is
imported, nothing is executed — so preflight itself can never crash a feature.

Used by:
  * agent._health_response()  — full preflight section in `system status`
  * EngineRouter              — when an engine fails to load, the user gets
                                the precise install command, not a shrug
"""

import importlib.util
import shutil
import socket
from typing import Any, Dict, List, Optional

# capability_id → requirements
# mods: python modules (find_spec) · bins: executables (PATH) · svc: (host, port)
CHECKS: Dict[str, Dict[str, Any]] = {
    "llm": {
        "label": "Ollama LLM server",
        "svc": ("localhost", 11434),
        "fix": "Start Ollama (`ollama serve`), then `ollama pull gemma4` "
               "and `ollama pull qwen2.5-coder:7b-instruct`.",
    },
    "word_doc":  {"label": "Word documents", "mods": ["docx"],
                  "fix": "pip install python-docx"},
    "excel":     {"label": "Excel spreadsheets", "mods": ["openpyxl"],
                  "fix": "pip install openpyxl"},
    "powerpoint": {"label": "PowerPoint", "mods": ["pptx"],
                   "fix": "pip install python-pptx"},
    "pdf_report": {"label": "PDF reports", "mods": ["reportlab"],
                   "fix": "pip install reportlab"},
    "data_analysis": {"label": "Data analysis", "mods": ["pandas", "matplotlib"],
                      "fix": "pip install pandas matplotlib seaborn"},
    "ml":        {"label": "ML engine", "mods": ["numpy"],
                  "fix": "pip install numpy  (optional: scikit-learn for more algorithms)"},
    "web_search": {"label": "Web search", "mods": ["requests", "bs4"],
                   "fix": "pip install requests beautifulsoup4"},
    "web_verify": {"label": "Web automation", "mods": ["playwright"],
                   "fix": "pip install playwright && playwright install chromium"},
    "whatsapp":  {"label": "WhatsApp", "mods": ["playwright"],
                  "fix": "pip install playwright && playwright install chromium"},
    "screen_read": {"label": "Screen OCR", "mods": ["pytesseract", "PIL"],
                    "bins": ["tesseract"],
                    "fix": "pip install pytesseract pillow + install Tesseract-OCR "
                           "(https://github.com/UB-Mannheim/tesseract/wiki) and add to PATH"},
    "hardware":  {"label": "Hardware control", "mods": ["pyautogui"],
                  "fix": "pip install pyautogui"},
    "email_send": {"label": "Email (Gmail OAuth/IMAP)", "mods": ["google_auth_oauthlib", "imapclient"],
                   "fix": "pip install google-auth-oauthlib imapclient"},
    "voice":     {"label": "Voice mode", "mods": ["speech_recognition", "pyttsx3"],
                  "fix": "pip install SpeechRecognition pyttsx3  (PyAudio: pip install pipwin && pipwin install pyaudio)"},
    "rag_memory": {"label": "RAG semantic memory", "mods": ["chromadb"],
                   "fix": "pip install chromadb"},
    "blender":   {"label": "Blender 3D", "bins": ["blender"],
                  "fix": "Install Blender from blender.org and add blender.exe to PATH"},
    "vision":    {"label": "Vision/image analysis", "mods": ["cv2", "PIL"],
                  "fix": "pip install opencv-python pillow"},
    "code_run":  {"label": "Code runner", "mods": [],
                  "fix": ""},  # uses sys.executable — always available
    "iot":       {"label": "IoT codegen", "mods": [], "fix": ""},
    "vlsi":      {"label": "VLSI codegen", "mods": [], "fix": ""},
    "gamedev":   {"label": "Game-dev scaffolding", "mods": [], "fix": ""},
    "news":      {"label": "News briefings", "mods": ["requests", "bs4"],
                  "fix": "pip install requests beautifulsoup4"},
    "file_ops":  {"label": "File operations", "mods": [], "fix": ""},
    "image_convert": {"label": "Image conversion", "mods": ["PIL"],
                      "fix": "pip install Pillow"},
    "web_scrape": {"label": "Web scraping", "mods": ["requests", "bs4"],
                   "fix": "pip install requests beautifulsoup4"},
    "code_run_node": {"label": "Node.js runner", "bins": ["node"],
                      "fix": "Install Node.js from nodejs.org"},
    "schedule_user": {"label": "Task scheduling", "mods": ["apscheduler"],
                      "fix": "pip install apscheduler"},
}

# EngineRouter key → capability id (for precise unavailable-messages)
ENGINE_TO_CAPABILITY = {
    "ml": "ml", "iot": "iot", "vlsi": "vlsi", "hardware": "hardware",
    "gamedev": "gamedev", "blender": "blender", "news": "news",
    "voiceplus": "voice", "webauto": "web_verify", "coderun": "code_run", "fileops": "file_ops", "webrecipes": "web_scrape", "schedule": "schedule_user",
}


def _mod_ok(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def _svc_ok(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check(capability_id: str) -> Dict[str, Any]:
    """Check one capability. Returns {ok, missing, fix, label}."""
    spec = CHECKS.get(capability_id)
    if not spec:
        return {"ok": True, "missing": [], "fix": "", "label": capability_id}
    missing: List[str] = []
    for m in spec.get("mods", []):
        if not _mod_ok(m):
            missing.append(f"python module '{m}'")
    for b in spec.get("bins", []):
        if not shutil.which(b):
            missing.append(f"executable '{b}'")
    svc = spec.get("svc")
    if svc and not _svc_ok(*svc):
        missing.append(f"service {svc[0]}:{svc[1]} not reachable")
    return {"ok": not missing, "missing": missing,
            "fix": spec.get("fix", ""), "label": spec.get("label", capability_id)}


def check_all() -> Dict[str, Dict[str, Any]]:
    return {cid: check(cid) for cid in CHECKS}


def report_text(only_problems: bool = True) -> str:
    """Human-readable preflight report for `system status`."""
    lines = []
    results = check_all()
    problems = {k: v for k, v in results.items() if not v["ok"]}
    if not problems:
        return "Dependency preflight: all capability dependencies satisfied."
    lines.append(f"Dependency preflight: {len(problems)} capability(ies) need attention:")
    for cid, r in problems.items():
        lines.append(f"  [{r['label']}] missing: {', '.join(r['missing'])}")
        if r["fix"]:
            lines.append(f"      fix: {r['fix']}")
    if not only_problems:
        ok_names = [v["label"] for v in results.values() if v["ok"]]
        lines.append(f"  OK: {', '.join(ok_names)}")
    return "\n".join(lines)


def fix_hint(engine_key: str) -> str:
    """Exact fix text for an engine that failed to load (EngineRouter)."""
    cid = ENGINE_TO_CAPABILITY.get(engine_key, engine_key)
    r = check(cid)
    if r["ok"]:
        return ""
    return f"Missing: {', '.join(r['missing'])}. Fix: {r['fix']}"
