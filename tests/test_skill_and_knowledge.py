"""Skill-manager default + knowledge engine content tests (stdlib only)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_external_skills_default_off(monkeypatch):
    monkeypatch.delenv("TOM_INCLUDE_EXTERNAL_SKILLS", raising=False)
    from tools.skill_manager import SkillManager
    sm = SkillManager()
    assert sm.include_external is False
    assert 30 <= sm.count_skills() <= 100  # local set only

def test_external_skills_env_flag(monkeypatch):
    monkeypatch.setenv("TOM_INCLUDE_EXTERNAL_SKILLS", "1")
    from tools.skill_manager import SkillManager
    sm = SkillManager()
    assert sm.include_external is True

def test_knowledge_legacy_content_loaded():
    from tools.knowledge_engine import get_engine
    eng = get_engine()
    legacy = eng.cache.get("legacy", {}).get("topics", [])
    assert legacy, "legacy knowledge should load"
    assert any(t.get("content") for t in legacy), "legacy docs must carry real content"


def test_knowledge_autodiscovers_all_domain_jsons():
    """Every *.json in a registered domain dir must load (no silent skips)."""
    import os
    from tools.knowledge_engine import KnowledgeEngine, DOMAIN_REGISTRY, KNOWLEDGE_DIR
    eng = KnowledgeEngine()
    stats = eng.get_stats()
    # cybersecurity has 7 json files on disk; registry hardcoded only 1.
    assert stats["domain_stats"]["cybersecurity"]["sections"] >= 20
    assert stats["total_sections"] >= 70


def test_every_knowledge_json_file_on_disk_actually_parses():
    """Every knowledge/*.json must be valid JSON the engine can load.

    Real bug: 4 of 26 files silently contributed zero content -- two had a
    UTF-8 BOM that plain `encoding="utf-8"` rejects, and two had genuine
    JSON syntax errors (a trailing comma; a doubled backslash that closed a
    string early). `_load_all()`'s bare `except: pass` swallowed all four
    with no warning anywhere, so `get_stats()` looked fine while an entire
    file's worth of curated knowledge (e.g. mobile security testing with
    Frida, referenced by the cybersecurity skill for "deeper coverage") was
    never actually searchable.
    """
    import glob
    import json
    import os
    from tools.knowledge_engine import KNOWLEDGE_DIR
    bad = []
    for path in glob.glob(os.path.join(KNOWLEDGE_DIR, "**", "*.json"), recursive=True):
        try:
            with open(path, encoding="utf-8-sig") as fh:
                json.load(fh)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            bad.append((path, str(exc)))
    assert bad == [], f"malformed knowledge JSON files: {bad}"

def test_all_local_skills_routable():
    from tools.skill_manager import SkillManager
    sm = SkillManager()
    unroutable = [r.name for r in sm.records()
                  if not sm.route_task("help me with " + r.name.replace("-", " ")).matched]
    assert unroutable == [], f"unroutable skills: {unroutable}"


def test_predictive_analysis_is_tool_backed():
    from tools.skill_manager import SkillManager
    sm = SkillManager()
    route = sm.route_task("predictive analysis forecast for sales data")
    assert route.matched
    assert route.skill_name == "40-predictive-analysis-skills"
    assert route.execution_mode == "tool_backed"
    assert "ml_engine" in route.required_tools


def test_engine_router_detects_predictive_analysis():
    from tools.engine_router import EngineRouter
    router = EngineRouter()
    assert router.detect("predictive analysis forecast for sales data") == "ml"

def test_frontmatter_skill_naming():
    from tools.skill_manager import SkillManager
    sm = SkillManager()
    names = [r.name for r in sm.records()]
    assert "skill" not in names, "SKILL.md must register under its frontmatter name"


def test_a_generic_domain_word_does_not_drown_out_a_specific_one():
    """"design" maps to 5 UI-ish skills in DOMAIN_MAP; "database" maps to just one.
    A query matching both used to tie 4.0 vs 4.0 and the alphabetical-by-name
    tiebreak always picked 01-ui-ux-design over 06-database-skills, regardless
    of the query actually being about a database."""
    from tools.skill_manager import SkillManager
    sm = SkillManager()
    route = sm.route_task("i need to design a database schema")
    assert route.matched and route.skill_name == "06-database-skills", route

    # A genuinely UI-flavored "design" query must still route to UI skills.
    route2 = sm.route_task("design a beautiful modern ui for my app")
    assert route2.matched and route2.skill_name == "01-ui-ux-design", route2
