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

def test_all_local_skills_routable():
    from tools.skill_manager import SkillManager
    sm = SkillManager()
    unroutable = [r.name for r in sm.records()
                  if not sm.route_task("help me with " + r.name.replace("-", " ")).matched]
    assert unroutable == [], f"unroutable skills: {unroutable}"

def test_frontmatter_skill_naming():
    from tools.skill_manager import SkillManager
    sm = SkillManager()
    names = [r.name for r in sm.records()]
    assert "skill" not in names, "SKILL.md must register under its frontmatter name"
