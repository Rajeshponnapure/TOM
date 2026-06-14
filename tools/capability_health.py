"""Runtime capability health report for TOM."""
from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from typing import Any, Dict

from tools.capability_registry import CAPABILITIES, find_orphan_tools, validate
from tools.knowledge_engine import KnowledgeEngine
from tools.skill_manager import SkillManager


OPTIONAL_IMPORTS = {
    "langchain_ollama": "LLM/Ollama agent brain",
    "playwright": "browser automation",
    "dotenv": ".env loading",
    "numpy": "ML/data arrays",
    "pandas": "data analysis",
    "sklearn": "machine learning",
}


def _import_present(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def build_capability_health() -> Dict[str, Any]:
    registry = validate()
    categories = Counter(cap["category"] for cap in CAPABILITIES)
    skills = SkillManager().health_report()
    knowledge = KnowledgeEngine().get_stats()
    imports = {
        name: {"present": _import_present(name), "purpose": purpose}
        for name, purpose in OPTIONAL_IMPORTS.items()
    }
    missing_imports = [name for name, info in imports.items() if not info["present"]]
    return {
        "python": {
            "executable": sys.executable,
            "version": sys.version.split()[0],
            "compatible": sys.version_info[:2] == (3, 11),
        },
        "capability_registry": {
            **registry,
            "categories": dict(sorted(categories.items())),
            "orphans": find_orphan_tools(),
        },
        "skills": skills,
        "knowledge": knowledge,
        "imports": imports,
        "missing_imports": missing_imports,
    }


def format_capability_health() -> str:
    report = build_capability_health()
    py = report["python"]
    reg = report["capability_registry"]
    skills = report["skills"]
    knowledge = report["knowledge"]
    lines = [
        "TOM capability health",
        "",
        f"Python: {py['version']} at {py['executable']}",
        f"Python 3.11 compatible: {'yes' if py['compatible'] else 'no'}",
        "",
        "Capability registry:",
        f"- Registered: {reg['total']}",
        f"- Verified executors: {reg['verified']}",
        f"- Registry OK: {'yes' if reg['ok'] else 'no'}",
        f"- Orphan tools: {len(reg['orphans'])}",
        "",
        "Capabilities by category:",
    ]
    for category, count in reg["categories"].items():
        lines.append(f"- {category}: {count}")
    lines.extend(
        [
            "",
            "Skills:",
            f"- Loaded: {skills.get('total', 0)}",
            f"- Sources: {skills.get('sources', {})}",
            f"- Execution modes: {skills.get('execution_modes', {})}",
            f"- Limited skills: {len(skills.get('limited', []))}",
            "",
            "Knowledge:",
            f"- Domains: {knowledge.get('domains', 0)}",
            f"- Sections: {knowledge.get('total_sections', 0)}",
            f"- Concepts: {knowledge.get('total_concepts', 0)}",
            f"- Code examples: {knowledge.get('total_code_examples', 0)}",
            "",
            "Dependency imports:",
        ]
    )
    for name, info in report["imports"].items():
        lines.append(f"- {name}: {'present' if info['present'] else 'missing'} ({info['purpose']})")
    if reg["missing"]:
        lines.extend(["", "Broken capability mappings:"])
        lines.extend(f"- {item}" for item in reg["missing"])
    if report["missing_imports"]:
        lines.extend(["", "Install missing runtime packages from the Python 3.11 venv:"])
        lines.append("venv\\Scripts\\python.exe -m pip install -r requirements.txt")
    return "\n".join(lines)
