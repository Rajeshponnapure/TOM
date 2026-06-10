"""The 100%-utilization contract: every capability real, zero orphans.
CI fails if any advertised capability loses its executor, or any tool
module becomes unreachable dead code."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.capability_registry import validate, find_orphan_tools, summary_text, CAPABILITIES

def test_every_capability_has_real_executor():
    v = validate()
    assert v["ok"], f"Broken capability mappings: {v['missing']}"
    assert v["verified"] == v["total"] == len(CAPABILITIES)

def test_zero_orphan_tools():
    orphans = find_orphan_tools()
    assert orphans == [], f"Orphaned tool modules found: {orphans}"

def test_summary_renders():
    s = summary_text()
    assert "capabilities" in s and len(s) > 500

def test_all_capabilities_chat_reachable():
    # Every capability except hardware-bound voice mode must be chat-reachable
    not_chat = [c["id"] for c in CAPABILITIES if "chat" not in c["surfaces"]]
    assert not_chat == ["voice"], f"Unexpected non-chat capabilities: {not_chat}"
