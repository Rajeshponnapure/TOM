import json
import os
import random

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge")

DOMAIN_REGISTRY = {
    "game_dev": {
        "name": "Game Development",
        "icon": "\U0001f3ae",
        "files": [
            "core_programming.json",
            "game_engines.json",
            "rendering_graphics.json",
            "physics_ai.json",
            "multiplayer_openworld.json",
            "audio_engineering.json",
            "game_design_production.json",
        ],
    },
    "blender_cgi": {
        "name": "3D Modeling & CGI",
        "icon": "\U0001f4fd",
        "files": ["blender_complete.json", "industry_software.json"],
    },
    "web_dev": {
        "name": "Web Development",
        "icon": "\U0001f310",
        "files": ["full_stack.json"],
    },
    "cybersecurity": {
        "name": "Cybersecurity",
        "icon": "\U0001f6e1",
        "files": ["ethical_hacking.json"],
    },
    "data_science": {
        "name": "Data Science & AI",
        "icon": "\U0001f4ca",
        "files": ["data_science.json"],
    },
    "mobile_dev": {
        "name": "Mobile Development",
        "icon": "\U0001f4f1",
        "files": ["mobile_dev.json"],
    },
}


class KnowledgeEngine:
    """TOM's knowledge engine - loads domain knowledge and teaches like a tutor."""

    def __init__(self):
        self.cache = {}
        self._loaded_domains = set()
        self._load_all()

    def _load_all(self):
        for domain, info in DOMAIN_REGISTRY.items():
            domain_dir = os.path.join(KNOWLEDGE_DIR, domain)
            if not os.path.isdir(domain_dir):
                continue
            domain_data = {"domain": info["name"], "sections": [], "topics": []}
            # COVERAGE FIX: auto-discover every *.json in the domain dir so new
            # knowledge files load without registry edits (registry list kept
            # for ordering/backward-compat, then union with what's on disk).
            discovered = sorted(
                f for f in os.listdir(domain_dir) if f.endswith(".json")
            )
            all_files = list(dict.fromkeys(list(info["files"]) + discovered))
            for fname in all_files:
                fpath = os.path.join(domain_dir, fname)
                if os.path.isfile(fpath):
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, dict):
                                domain_data["sections"].extend(
                                    data.get("sections", [])
                                )
                                domain_data["topics"].extend(
                                    data.get("topics", [])
                                )
                    except (json.JSONDecodeError, Exception):
                        pass
            self.cache[domain] = domain_data
            self._loaded_domains.add(domain)

        # Also load legacy .md knowledge files
        legacy = self._load_legacy_md()
        if legacy:
            self.cache["legacy"] = legacy
            self._loaded_domains.add("legacy")

    def _load_legacy_md(self):
        legacy = {"domain": "Legacy Knowledge", "topics": []}
        if not os.path.isdir(KNOWLEDGE_DIR):
            return legacy
        for fname in os.listdir(KNOWLEDGE_DIR):
            if fname.endswith(".md"):
                fpath = os.path.join(KNOWLEDGE_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read()
                    name = fname.replace(".md", "").replace("-", " ").title()
                    # FIX: store the actual content (bounded) so the knowledge
                    # base is genuinely usable in retrieval, not just listed.
                    legacy["topics"].append(
                        {"name": name, "content_length": len(content),
                         "content": content[:20000]}
                    )
                except Exception:
                    continue
        return legacy

    def list_domains(self):
        """List all available knowledge domains."""
        result = []
        for key, info in DOMAIN_REGISTRY.items():
            loaded = key in self._loaded_domains
            section_count = len(self.cache.get(key, {}).get("sections", []))
            result.append(
                {
                    "key": key,
                    "name": info["name"],
                    "icon": info["icon"],
                    "loaded": loaded,
                    "section_count": section_count,
                }
            )
        return result

    def get_domain(self, domain_key):
        """Get all knowledge for a domain."""
        return self.cache.get(domain_key, {})

    def search(self, query):
        """Search across all knowledge for a term."""
        results = []
        query_lower = query.lower()
        for domain_key, domain_data in self.cache.items():
            name = DOMAIN_REGISTRY.get(domain_key, {}).get("name", domain_key)
            for section in domain_data.get("sections", []):
                section_name = section.get("name", "")
                if query_lower in section_name.lower():
                    results.append(
                        {
                            "domain": name,
                            "domain_key": domain_key,
                            "section": section_name,
                            "match_type": "section_name",
                        }
                    )
                for concept in section.get("key_concepts", []):
                    if query_lower in concept.lower():
                        results.append(
                            {
                                "domain": name,
                                "domain_key": domain_key,
                                "section": section_name,
                                "match_type": "concept",
                                "match": concept,
                            }
                        )
                explanation = section.get("explanation_simple", "")
                if query_lower in explanation.lower():
                    results.append(
                        {
                            "domain": name,
                            "domain_key": domain_key,
                            "section": section_name,
                            "match_type": "explanation",
                        }
                    )
        return results

    def teach_topic(
        self, domain_key, topic_name, difficulty="beginner", format="text"
    ):
        """Teach a specific topic with explanations at the right difficulty level.

        Args:
            domain_key: The domain key (e.g. 'game_dev')
            topic_name: Name of the topic/section to teach
            difficulty: 'beginner' (age 15), 'intermediate', 'advanced'
            format: 'text', 'code', 'lesson_plan'
        """
        domain_data = self.cache.get(domain_key)
        if not domain_data:
            return f"Domain '{domain_key}' not found. Available: {list(self.cache.keys())}"

        # Find matching section
        section = None
        for s in domain_data.get("sections", []):
            if topic_name.lower() in s.get("name", "").lower():
                section = s
                break

        if not section:
            # Search topic names too
            for t in domain_data.get("topics", []):
                if topic_name.lower() in t.get("name", "").lower():
                    return self._format_topic(t, difficulty, format)
            return f"Topic '{topic_name}' not found in {domain_key}."

        return self._format_section(section, difficulty, format)

    def _format_section(self, section, difficulty, format):
        lines = []
        name = section.get("name", "Topic")
        explanation = section.get("explanation_simple", section.get("description", ""))
        concepts = section.get("key_concepts", [])
        codes = section.get("code_examples", [])
        path = section.get("learning_path", "")

        lines.append(f"== {name} ==")
        lines.append("")

        if explanation:
            lines.append(explanation)
            lines.append("")

        if concepts:
            lines.append("Key Concepts:")
            for c in concepts:
                lines.append(f"  - {c}")
            lines.append("")

        if difficulty in ("intermediate", "advanced") and codes:
            lines.append("Code Examples:")
            for i, code in enumerate(codes, 1):
                if isinstance(code, dict):
                    title = code.get("title", f"Example {i}")
                    code_text = code.get("code", "")
                    lines.append(f"\n--- {title} ---")
                    lines.append(code_text)
                elif isinstance(code, str):
                    lines.append(f"\n--- Example {i} ---")
                    lines.append(code)
            lines.append("")

        if path:
            lines.append(f"Learning Path: {path}")

        # Add teaching plan if available
        teaching = section.get("teaching_plan")
        if teaching and format == "lesson_plan":
            lines.append("\n== Teaching Plan ==")
            for lesson_key, lesson in teaching.items():
                if isinstance(lesson, dict):
                    lines.append(f"\n{lesson.get('title', lesson_key)}")
                    for c in lesson.get("concepts", []):
                        lines.append(f"  - {c}")
                    for p in lesson.get("projects", []):
                        lines.append(f"  Project: {p}")

        return "\n".join(lines)

    def _format_topic(self, topic, difficulty, format):
        lines = []
        name = topic.get("name", "Topic")
        explanation = topic.get("explanation_simple", "")
        concepts = topic.get("key_concepts", [])
        codes = topic.get("code_examples", [])

        lines.append(f"== {name} ==")
        lines.append("")
        if explanation:
            lines.append(explanation)
            lines.append("")
        if concepts:
            lines.append("Key Concepts:")
            for c in concepts:
                lines.append(f"  - {c}")
            lines.append("")
        if codes:
            lines.append("Code Example:")
            for code in codes[:1]:
                lines.append(code)
        path = topic.get("learning_path", "")
        if path:
            lines.append(f"\nLearning Path: {path}")
        return "\n".join(lines)

    def get_lesson_plan(self, domain_key, topic_name=None):
        """Get a structured lesson plan for learning."""
        domain_data = self.cache.get(domain_key)
        if not domain_data:
            return f"Domain '{domain_key}' not found."

        teaching_plan = domain_data.get("teaching_plan")
        if teaching_plan:
            lines = ["== Complete Lesson Plan =="]
            for key, lesson in teaching_plan.items():
                if isinstance(lesson, dict):
                    lines.append(
                        f"\n{lesson.get('title', key)}"
                    )
                    for c in lesson.get("concepts", []):
                        lines.append(f"  - {c}")
            return "\n".join(lines)

        # Build from sections
        lines = ["== Lesson Plan (Auto-generated) =="]
        for i, section in enumerate(domain_data.get("sections", []), 1):
            lines.append(f"\nLesson {i}: {section.get('name', 'Topic')}")
            for c in section.get("key_concepts", [])[:3]:
                lines.append(f"  - {c}")
        return "\n".join(lines)

    def get_stats(self):
        """Get knowledge base statistics."""
        total_sections = 0
        total_concepts = 0
        total_codes = 0
        domain_stats = {}

        for domain_key, domain_data in self.cache.items():
            sections = domain_data.get("sections", [])
            sc = len(sections)
            conc = sum(len(s.get("key_concepts", [])) for s in sections)
            codc = sum(len(s.get("code_examples", [])) for s in sections)
            total_sections += sc
            total_concepts += conc
            total_codes += codc
            domain_stats[domain_key] = {
                "name": DOMAIN_REGISTRY.get(domain_key, {}).get(
                    "name", domain_key
                ),
                "sections": sc,
                "concepts": conc,
                "code_examples": codc,
            }

        return {
            "domains": len(self.cache),
            "total_sections": total_sections,
            "total_concepts": total_concepts,
            "total_code_examples": total_codes,
            "domain_stats": domain_stats,
        }


# Singleton instance
_instance = None


def get_engine():
    global _instance
    if _instance is None:
        _instance = KnowledgeEngine()
    return _instance


def teach(domain, topic, difficulty="beginner"):
    """Quick-access teaching function."""
    engine = get_engine()
    result = engine.teach_topic(domain, topic, difficulty)
    return result


def search(query):
    """Quick-access search function."""
    engine = get_engine()
    return engine.search(query)


def list_knowledge():
    """Quick-access list function."""
    engine = get_engine()
    return engine.list_domains()


def get_stats():
    """Quick-access stats function."""
    engine = get_engine()
    return engine.get_stats()


if __name__ == "__main__":
    eng = get_engine()
    stats = eng.get_stats()
    print(f"Knowledge Engine Stats:")
    print(f"  Domains loaded: {stats['domains']}")
    print(f"  Total sections: {stats['total_sections']}")
    print(f"  Total concepts: {stats['total_concepts']}")
    print(f"  Total code examples: {stats['total_code_examples']}")
    print()
    print("Available domains:")
    for d in eng.list_domains():
        icon = d.get("icon", "")
        status = "\u2713" if d["loaded"] else "\u2717"
        print(f"  {icon} {d['name']} ({d['key']}) - {d['section_count']} sections")
