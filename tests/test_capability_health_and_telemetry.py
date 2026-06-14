import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_capability_health_builds():
    from tools.capability_health import build_capability_health

    report = build_capability_health()
    assert report["capability_registry"]["ok"] is True
    assert report["capability_registry"]["total"] >= 50
    assert "python" in report
    assert "skills" in report
    assert "knowledge" in report


def test_skill_telemetry_records_tmp_path(tmp_path):
    from tools.skill_telemetry import SkillTelemetry

    path = tmp_path / "skill_usage.json"
    telemetry = SkillTelemetry(path)
    telemetry.record_route(
        "40-predictive-analysis-skills",
        "tool_backed",
        "success",
        elapsed_seconds=1.25,
        command="predictive analysis for sales data",
    )
    summary = telemetry.summary()
    assert summary["tracked_skills"] == 1
    assert summary["total_routes"] == 1
    assert summary["skills"][0]["success_rate"] == 100.0


def test_new_knowledge_domains_searchable():
    from tools.knowledge_engine import KnowledgeEngine

    eng = KnowledgeEngine()
    assert eng.search("predictive analysis")
    assert eng.search("web automation")
    assert eng.search("medical")
