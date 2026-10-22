"""R9 acceptance: watchers (C11), reviewed workflows (C12), cloud escalation gate (RRM-007),
no remote listener — each off by default."""
import ast
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tom_core import features, watchers, workflows  # noqa: E402
from tom_core.planning.planner import Plan, Step  # noqa: E402
from tom_core.resources import cloud  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_every_advanced_feature_is_off_by_default(monkeypatch):
    for env in features.FLAGS.values():
        monkeypatch.delenv(env, raising=False)
    assert not any(features.enabled(n) for n in features.FLAGS)
    assert watchers.start(lambda n: None) is None


def test_watchers_notify_on_change_only():
    state = {"v": None}
    ws = watchers.WatcherSet({"disk": lambda: state["v"]})
    assert ws.poll() == []
    state["v"] = "Only 4.0 GB free on C:\\ (alert below 10 GB)."
    first = ws.poll()
    assert [n.level for n in first] == ["warning"]
    state["v"] = "Only 3.9 GB free on C:\\ (alert below 10 GB)."
    assert ws.poll() == []                                  # drift is not news
    state["v"] = None
    assert [n.level for n in ws.poll()] == ["resolved"]
    assert ws.poll() == []


def test_a_broken_watcher_stays_silent():
    def boom():
        raise RuntimeError("sensor gone")
    assert watchers.WatcherSet({"x": boom}).poll() == []


def test_workflow_paths_become_inputs_and_drafts_cannot_run(tmp_path):
    plan = Plan("tidy a folder", [Step(1, "fs.list_dir", {"path": "C:/Users/me/Downloads"}),
                                  Step(2, "fs.make_dir", {"path": "C:/Users/me/Downloads"})])
    wf = workflows.save_draft("tidy", plan)
    assert wf["status"] == "draft" and wf["inputs"] == {"path": "C:/Users/me/Downloads"}
    assert all(s["args"]["path"] == "{{input:path}}" for s in wf["steps"])
    from tom_core.tools.registry import get_registry
    with pytest.raises(PermissionError, match="draft"):
        asyncio.run(workflows.run("tidy", get_registry()))


def test_an_approved_workflow_runs_with_new_inputs(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    plan = Plan("list a folder", [Step(1, "fs.list_dir", {"path": "C:/old/place"})])
    workflows.save_draft("lister", plan)
    workflows.approve("lister")
    from tom_core.tools.registry import get_registry
    report = asyncio.run(workflows.run("lister", get_registry(), {"path": str(tmp_path)}))
    assert report.status == "success" and "a.txt" in str(report.results[0].raw["output"])
    with pytest.raises(ValueError, match="Unknown input"):
        asyncio.run(workflows.run("lister", get_registry(), {"folder": "x"}))


def test_workflow_chat_commands_need_the_flag_and_follow_review(monkeypatch, tmp_path):
    import agent as agent_mod
    a = agent_mod.TomAgent.__new__(agent_mod.TomAgent)
    monkeypatch.delenv("TOM_WORKFLOWS", raising=False)
    off = asyncio.run(a._advanced_command("list workflows"))
    assert "TOM_WORKFLOWS=1" in off["message"]
    monkeypatch.setenv("TOM_WORKFLOWS", "1")
    a.last_plan = Plan("list a folder", [Step(1, "fs.list_dir", {"path": str(tmp_path)})])
    saved = asyncio.run(a._advanced_command("save this as workflow folder check"))
    assert "draft" in saved["message"]
    blocked = asyncio.run(a._advanced_command("run workflow folder check"))
    assert blocked["status"] == "error" and "draft" in blocked["message"]
    asyncio.run(a._advanced_command("approve workflow folder check"))
    ran = asyncio.run(a._advanced_command(f"run workflow folder check with path={tmp_path}"))
    assert ran["status"] == "success"
    assert asyncio.run(a._advanced_command("what is the weather")) is None


@pytest.mark.parametrize("env,expected", [
    ({}, "off"),
    ({"TOM_CLOUD_ESCALATION": "1"}, "key"),
    ({"TOM_CLOUD_ESCALATION": "1", "GROQ_API_KEY": "k"}, "data-sharing policy"),
    ({"TOM_CLOUD_ESCALATION": "1", "GROQ_API_KEY": "k", "TOM_CLOUD_DATA_POLICY": "allow"}, "cost limit"),
])
def test_cloud_escalation_needs_flag_key_policy_and_limit(monkeypatch, env, expected):
    for k in ("TOM_CLOUD_ESCALATION", "GROQ_API_KEY", "TOM_CLOUD_DATA_POLICY", "TOM_CLOUD_DAILY_LIMIT"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    ok, why = cloud.allowed("explain recursion")
    assert not ok and expected in why


def test_cloud_policy_keeps_personal_data_local_and_counts_the_limit(monkeypatch):
    monkeypatch.setenv("TOM_CLOUD_ESCALATION", "1")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setenv("TOM_CLOUD_DATA_POLICY", "no-personal-data")
    monkeypatch.setenv("TOM_CLOUD_DAILY_LIMIT", "1")
    assert not cloud.allowed("summarize my email inbox")[0]
    assert cloud.allowed("explain recursion")[0]
    cloud.record_use()
    ok, why = cloud.allowed("explain recursion")
    assert not ok and "used up" in why


def test_tom_opens_no_network_listener():
    """Remote access is not implemented; nothing may bind a socket or start a server."""
    bad = []
    for folder in ("tools", "tom_core", "agents"):
        for dirpath, _d, files in os.walk(os.path.join(ROOT, folder)):
            for f in files:
                if not f.endswith(".py"):
                    continue
                path = os.path.join(dirpath, f)
                tree = ast.parse(open(path, encoding="utf-8-sig", errors="ignore").read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and \
                            node.func.attr in ("bind", "serve_forever", "listen") and \
                            not isinstance(node.func.value, ast.Constant):
                        bad.append(f"{os.path.relpath(path, ROOT)}:{node.lineno}:{node.func.attr}")
    assert bad == [], bad
