from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Iterable


ROOT_DIR = Path(__file__).resolve().parents[1]


def _read_text(relative_path: str) -> str:
    path = ROOT_DIR / relative_path
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def _summarize_block(title: str, text: str, max_lines: int = 24) -> str:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if len(lines) <= max_lines:
        body = "\n".join(lines)
    else:
        body = "\n".join(lines[:max_lines]) + "\n..."
    return f"## {title}\n{body}" if body else f"## {title}\n(none found)"


def _join_nonempty(parts: Iterable[str]) -> str:
    return "\n\n".join(part for part in parts if part and part.strip())


@cache
def build_runtime_instruction_block(agent_name: str, *, include_ui: bool = False) -> str:
    """Compose a compact runtime policy block from the repo instruction files."""
    claude = _read_text("CLAUDE.md")
    agents = _read_text("AGENTS.md")
    system_prompt = _read_text("config/system_prompt.txt")
    skill = _read_text("skills/SKILL.md")
    design_systems = _read_text("skills/design-systems.md")
    uniqueness = _read_text("skills/uniqueness-engine.md")
    platform_specs = _read_text("skills/platform-specs.md")
    ui_patterns = _read_text("skills/ui-patterns.md")

    base_digest = _join_nonempty(
        [
            f"# Runtime Instruction Stack for {agent_name}",
            "Loaded source files: CLAUDE.md, AGENTS.md, config/system_prompt.txt.",
            _summarize_block("CLAUDE.md", claude),
            _summarize_block("AGENTS.md", agents),
            _summarize_block("system_prompt.txt", system_prompt, max_lines=18),
            "Runtime rules: verify before answering, avoid hallucination, keep outputs concise and role-appropriate, and prefer reversible actions.",
        ]
    )

    if not include_ui:
        return base_digest

    ui_digest = _join_nonempty(
        [
            "UI / visual-output policy is active for any PDF, report, email template, web UI, dashboard, document, or other visible artifact.",
            "Loaded source files: skills/SKILL.md, skills/design-systems.md, skills/uniqueness-engine.md, skills/platform-specs.md, skills/ui-patterns.md.",
            _summarize_block("skills/SKILL.md", skill, max_lines=24),
            _summarize_block("skills/design-systems.md", design_systems, max_lines=20),
            _summarize_block("skills/uniqueness-engine.md", uniqueness, max_lines=20),
            _summarize_block("skills/platform-specs.md", platform_specs, max_lines=20),
            _summarize_block("skills/ui-patterns.md", ui_patterns, max_lines=20),
            "Design rules: choose a distinct aesthetic, use a deliberate palette and type hierarchy, preserve accessibility, and avoid template-looking layouts.",
        ]
    )

    return _join_nonempty([base_digest, ui_digest])


def _escape_braces(text: str) -> str:
    """Escape { and } so LangChain ChatPromptTemplate treats them as literals."""
    return text.replace("{", "{{").replace("}", "}}")


def compose_system_prompt(base_prompt: str, agent_name: str, *, include_ui: bool = False) -> str:
    base_prompt = (base_prompt or "").strip()
    instruction_block = build_runtime_instruction_block(agent_name, include_ui=include_ui)
    if base_prompt:
        return f"{base_prompt}\n\n{instruction_block}"
    return instruction_block
