"""
Unified TOM skill registry.

Loads local domain skills and external Claude-style SKILL.md directories, then
classifies each skill by how Tom can use it.
"""
from __future__ import annotations

import os

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from tools.project_paths import PROJECT_ROOT, project_path


@dataclass(frozen=True)
class SkillRecord:
    name: str
    path: str
    source: str
    content: str
    aliases: List[str] = field(default_factory=list)
    execution_mode: str = "knowledge_only"
    required_tools: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class SkillRoute:
    matched: bool
    skill_name: str = ""
    confidence: float = 0.0
    execution_mode: str = "unmatched"
    context: str = ""
    required_tools: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)


class SkillManager:
    """
    Loads every supported skill source:
    - skills/*.md
    - awesome-claude-skills/**/SKILL.md

    Existing UI methods are preserved: get_skill, search_skills,
    get_context_for_task, list_skills, count_skills.
    """

    TOOL_BACKED_TERMS = {
        "frontend": ["file_tools", "web_automation"],
        "backend": ["file_tools"],
        "database": ["file_tools", "data_analysis"],
        "data": ["data_analysis"],
        "excel": ["document_creator"],
        "word": ["document_creator"],
        "powerpoint": ["document_creator"],
        "ppt": ["document_creator"],
        "email": ["email_tools"],
        "web": ["web_automation"],
        "browser": ["browser_tools"],
        "testing": ["web_automation"],
        "game": ["game_dev"],
        "desktop": ["file_tools"],
        "windows": ["os_tools"],
        "ml": ["ml_engine"],
        "machine": ["ml_engine"],
        "nlp": ["ml_engine"],
        "predictive": ["ml_engine"],
        "prediction": ["ml_engine"],
        "forecast": ["ml_engine"],
        "time series": ["ml_engine"],
        "regression": ["ml_engine"],
        "classification": ["ml_engine"],
        "iot": ["iot_engine"],
        "esp32": ["iot_engine"],
        "esp8266": ["iot_engine"],
        "arduino": ["iot_engine"],
        "mqtt": ["iot_engine"],
        "vlsi": ["vlsi_engine"],
        "verilog": ["vlsi_engine"],
        "vhdl": ["vlsi_engine"],
        "systemverilog": ["vlsi_engine"],
        "rtl": ["vlsi_engine"],
        "fpga": ["vlsi_engine"],
        "blender": ["blender_control"],
        "3d": ["blender_control"],
    }

    EXTERNAL_COMMAND_TERMS = {
        "video": ["external_cli"],
        "youtube": ["external_cli"],
        "mcp": ["external_cli"],
        "connect": ["external_cli"],
        "composio": ["external_api"],
        "slack": ["external_api"],
        "github": ["external_api"],
        "notion": ["external_api"],
        "react native": ["external_cli"],
        "expo": ["external_cli"],
    }

    KNOWLEDGE_ONLY_SKILLS = {
        "cybersecurity-skills",
        "medical-skills",
    }

    DOMAIN_MAP = {
        "design": ["ui-ux-design", "mobile-ui-design", "design-systems", "canvas-design", "brand-guidelines"],
        "ui": ["ui-ux-design", "desktop-ui-skills", "mobile-ui-design"],
        "frontend": ["frontend-dev", "react-native-mobile-ui", "webapp-testing"],
        "backend": ["backend-dev", "system-design"],
        "api": ["backend-dev", "system-design"],
        "database": ["database-skills"],
        "data engineering": ["data-engineering"],
        "data science": ["data-science"],
        "data clean": ["data-cleaning"],
        "android": ["android-dev"],
        "ios": ["ios-dev", "mobile-ui-design"],
        "macos": ["macos-dev"],
        "windows": ["windows-dev"],
        "desktop": ["desktop-ui-skills", "windows-dev"],
        "email": ["email-writing"],
        "content": ["content-generation", "content-research-writer"],
        "excel": ["excel-skills", "xlsx"],
        "word": ["word-skills", "docx"],
        "powerpoint": ["powerpoint-skills", "pptx"],
        "power bi": ["powerbi-skills"],
        "devops": ["devops-skills"],
        "security": ["cybersecurity-skills"],
        "cybersecurity": ["cybersecurity-skills"],
        "hacking": ["cybersecurity-skills"],
        "ethical hacking": ["cybersecurity-skills"],
        "pentest": ["cybersecurity-skills"],
        "network": ["networking-skills"],
        "testing": ["testing-skills", "webapp-testing"],
        "system design": ["system-design"],
        "game": ["game-dev-skills"],
        "blockchain": ["blockchain-skills"],
        "machine learning": ["machine-learning", "deep-learning"],
        "ml": ["machine-learning", "deep-learning"],
        "deep learning": ["deep-learning"],
        "nlp": ["nlp-skills"],
        "computer vision": ["computer-vision"],
        "iot": ["iot-skills", "bolt-iot-automation"],
        "esp32": ["iot-skills", "bolt-iot-automation"],
        "esp8266": ["iot-skills"],
        "arduino": ["iot-skills"],
        "mqtt": ["iot-skills"],
        "sensor": ["iot-skills"],
        "firmware": ["iot-skills", "vlsi-skills"],
        "vlsi": ["vlsi-skills"],
        "verilog": ["vlsi-skills"],
        "vhdl": ["vlsi-skills"],
        "systemverilog": ["vlsi-skills"],
        "rtl": ["vlsi-skills"],
        "fpga": ["vlsi-skills"],
        "asic": ["vlsi-skills"],
        "medical": ["medical-skills"],
        "media": ["media-production-skills"],
        "video": ["media-production-skills", "video-downloader"],
        "predictive": ["predictive-analysis-skills"],
        "forecast": ["predictive-analysis-skills", "machine-learning"],
        "time series": ["predictive-analysis-skills", "machine-learning"],
        "3d": ["3d-animation", "motion-animation"],
        "animation": ["motion-animation", "3d-animation"],
        "cross platform": ["cross-platform-dev"],
        "flutter": ["flutter-advanced", "cross-platform-dev"],
        "react native": ["react-native-mobile-ui", "cross-platform-dev"],
        "electron": ["tauri-electron-react"],
        "tauri": ["tauri-electron-react"],
        "kotlin": ["android-dev", "cross-platform-dev"],
        "swift": ["ios-dev", "macos-dev"],
        "c#": ["windows-dev"],
        ".net": ["windows-dev"],
    }

    def __init__(self, skills_dir: str = None, include_external: bool = None):
        self.skills_dir = Path(skills_dir) if skills_dir else project_path("skills")
        # PERF: the external awesome-claude-skills library is 864 SKILL.md files.
        # Loading them all on every startup is slow and pollutes routing, so it is
        # now OPT-IN. Set TOM_INCLUDE_EXTERNAL_SKILLS=1 in .env to re-enable.
        if include_external is None:
            include_external = os.environ.get(
                "TOM_INCLUDE_EXTERNAL_SKILLS", "0"
            ).strip().lower() in ("1", "true", "yes", "on")
        self.include_external = include_external
        self._records: Dict[str, SkillRecord] = {}
        self._load_all()

    def _load_all(self) -> None:
        for fpath in sorted(self.skills_dir.glob("*.md")):
            self._register(fpath, source="local")

        if self.include_external:
            external_root = project_path("awesome-claude-skills")
            if external_root.exists():
                for fpath in sorted(external_root.glob("**/SKILL.md")):
                    self._register(fpath, source="awesome")

    def _register(self, fpath: Path, source: str) -> None:
        try:
            content = fpath.read_text(encoding="utf-8")
        except Exception as exc:
            print(f"[SkillManager] Failed to load {fpath}: {exc}")
            return

        name = fpath.stem if source == "local" else fpath.parent.name
        # Prefer the YAML frontmatter `name:` when present (e.g. SKILL.md
        # declares `name: ui-design-skill` — far more routable than "skill").
        if content.startswith("---"):
            m = re.search(r"^name:\s*([A-Za-z0-9_\- ]+)\s*$", content[:600], re.M)
            if m:
                name = m.group(1).strip()
        canonical = self._canonical_name(name)
        aliases = self._aliases_for(name, content)
        mode, tools, limitations = self._classify(canonical, content, source)
        self._records[canonical] = SkillRecord(
            name=canonical,
            path=str(fpath),
            source=source,
            content=content,
            aliases=aliases,
            execution_mode=mode,
            required_tools=tools,
            limitations=limitations,
        )

    @staticmethod
    def _canonical_name(name: str) -> str:
        return re.sub(r"\s+", "-", name.strip().lower())

    def _aliases_for(self, name: str, content: str) -> List[str]:
        aliases = {name, self._canonical_name(name), name.replace("-", " ")}
        for token in re.split(r"[^a-zA-Z0-9+#.]+", name.lower()):
            if len(token) >= 3:
                aliases.add(token)
        first_heading = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if first_heading:
            heading = first_heading.group(1).strip()
            aliases.add(heading.lower())
        return sorted(aliases)

    def _classify(self, name: str, content: str, source: str) -> tuple[str, List[str], List[str]]:
        if any(skill_name in name for skill_name in self.KNOWLEDGE_ONLY_SKILLS):
            return "knowledge_only", [], ["Loaded as guidance; Tom must not execute this as an autonomous action."]

        blob = f"{name}\n{content[:2000]}".lower()
        tools = []
        for term, required in self.TOOL_BACKED_TERMS.items():
            if self._has_term(blob, term):
                tools.extend(required)
        if tools:
            return "tool_backed", sorted(set(tools)), []

        ext_tools = []
        for term, required in self.EXTERNAL_COMMAND_TERMS.items():
            if self._has_term(blob, term):
                ext_tools.extend(required)
        if ext_tools:
            return "external_command", sorted(set(ext_tools)), ["Requires external CLI, API credential, or service login."]

        if source == "awesome":
            return "knowledge_only", [], ["Loaded as guidance; no project tool is mapped yet."]
        return "knowledge_only", [], []

    @staticmethod
    def _has_term(text: str, term: str) -> bool:
        escaped = re.escape(term.lower())
        return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text.lower()) is not None

    def get_skill(self, name: str) -> Optional[str]:
        record = self.get_record(name)
        return record.content if record else None

    def get_record(self, name: str) -> Optional[SkillRecord]:
        query = self._canonical_name(name)
        if query in self._records:
            return self._records[query]
        for record in self._records.values():
            if query in record.name or record.name in query:
                return record
            if any(query in self._canonical_name(alias) for alias in record.aliases):
                return record
        return None

    def get_skill_by_domain(self, domain: str) -> Optional[str]:
        route = self.route_task(domain)
        return route.context if route.matched else None

    def search_skills(self, query: str) -> List[str]:
        query_lower = query.lower().strip()
        if not query_lower:
            return []
        scored = self._score_records(query_lower)
        return [record.name for _score, record in scored[:10]]

    def route_task(self, task_description: str) -> SkillRoute:
        scored = self._score_records(task_description.lower())
        if not scored:
            return SkillRoute(matched=False)
        score, record = scored[0]
        confidence = min(0.98, score / 5.0)
        if confidence < 0.2:
            return SkillRoute(matched=False)
        return SkillRoute(
            matched=True,
            skill_name=record.name,
            confidence=round(confidence, 2),
            execution_mode=record.execution_mode,
            context=self._trim_context(record),
            required_tools=record.required_tools,
            limitations=record.limitations,
        )

    def _score_records(self, query_lower: str) -> List[tuple[float, SkillRecord]]:
        query_terms = self._terms(query_lower)
        desired_names = []
        for keyword, names in self.DOMAIN_MAP.items():
            if self._has_term(query_lower, keyword):
                desired_names.extend(names)

        scored: List[tuple[float, SkillRecord]] = []
        for record in self._records.values():
            score = 0.0
            haystack = " ".join([record.name, *record.aliases]).lower()
            if record.name != "skill" and (record.name in query_lower or record.name.replace("-", " ") in query_lower):
                score += 5.0
            for desired in desired_names:
                if desired in record.name:
                    score += 4.0
            score += len(query_terms.intersection(self._terms(haystack))) * 0.8
            if query_lower and query_lower in record.content.lower():
                score += 1.0
            if score > 0:
                scored.append((score, record))
        scored.sort(key=lambda item: (-item[0], item[1].name))
        return scored

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {t for t in re.split(r"[^a-z0-9+#.]+", text.lower()) if len(t) >= 3}

    @staticmethod
    def _trim_context(record: SkillRecord, max_lines: int = 90) -> str:
        lines = [line.rstrip() for line in record.content.splitlines()]
        body = "\n".join(lines[:max_lines])
        return (
            f"--- Skill: {record.name} [{record.execution_mode}] ---\n"
            f"Source: {record.source}\nPath: {record.path}\n"
            f"Required tools: {', '.join(record.required_tools) or 'none'}\n"
            f"{body}"
        )

    def get_context_for_task(self, task_description: str) -> str:
        scored = self._score_records(task_description.lower())
        if not scored:
            return ""
        contexts = [self._trim_context(record, max_lines=60) for _score, record in scored[:3]]
        return "\n\n".join(contexts)

    def list_skills(self) -> List[str]:
        return list(self._records.keys())

    def count_skills(self) -> int:
        return len(self._records)

    def records(self) -> List[SkillRecord]:
        return list(self._records.values())

    def health_report(self) -> Dict[str, object]:
        modes: Dict[str, int] = {}
        sources: Dict[str, int] = {}
        blocked = []
        for record in self._records.values():
            modes[record.execution_mode] = modes.get(record.execution_mode, 0) + 1
            sources[record.source] = sources.get(record.source, 0) + 1
            if record.limitations:
                blocked.append({
                    "name": record.name,
                    "mode": record.execution_mode,
                    "limitations": record.limitations,
                })
        return {
            "total": len(self._records),
            "sources": sources,
            "execution_modes": modes,
            "limited": blocked,
        }
