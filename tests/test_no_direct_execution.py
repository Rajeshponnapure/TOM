"""TOM-MIG-010 — no direct execution bypass: every side-effecting entry point passes the policy engine.

Static half: each known side-effecting function/method is either wrapped by guard_methods or calls
enforce()/aenforce() itself. Behavioural half: with the emergency stop on, those entry points refuse.
"""
import asyncio
import inspect
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GATE_MARKERS = ("enforce(", "aenforce(", "_gate(", "_policy_gate(")

ENTRY_POINTS = [
    ("tools.whatsapp_tools", "WhatsAppTools.send_message"),
    ("tools.chat_apps", "ChatApps.send"),
    ("tools.email_tools", "EmailTools.send_email"),
    ("tools.email_tools", "EmailTools.send_email_direct"),
    ("tools.gmail_web", "GmailWeb.open_compose"),
    ("tools.gmail_web", "GmailWeb.send_open_draft"),
    ("tools.system_control", "SystemControl.run"),
    ("tools.game_library", "launch"),
    ("tools.file_tools", "FileTools.delete_path"),
    ("tools.tool_acquirer", "ToolAcquirer.install_package"),
    ("tools.tool_acquirer", "ToolAcquirer.clone_repo"),
    ("tools.dependency_manager", "DependencyManager.create_venv"),
    ("tools.dependency_manager", "DependencyManager.install_package"),
    ("tools.dependency_manager", "DependencyManager.uninstall_package"),
    ("tools.dependency_manager", "DependencyManager.update_package"),
    ("tools.dependency_manager", "DependencyManager.migrate_to_python311"),
    ("tools.auto_update", "AutoUpdate.pull_updates"),
    ("tools.auto_update", "AutoUpdate.update_pip_packages"),
    ("tools.auto_update", "AutoUpdate.full_update"),
    ("tools.hardware_control", "HardwareControl.click"),
    ("tools.hardware_control", "HardwareControl.type_text"),
    ("tools.hardware_control", "HardwareControl.press_key"),
    ("tools.hardware_control", "HardwareControl.set_volume"),
    ("tools.os_tools", "OSTools.open_application"),
    ("tools.plugin_manager", "PluginManager.execute_plugin"),
    ("tools.blender_control", "BlenderControl.execute_script"),
    ("tools.email_agent_controller", "EmailAgentController.start"),
    ("tools.instagram_agent_controller", "InstagramAgentController.start"),
    ("tools.document_creator", "_output_path"),
    ("tools.code_runner", "CodeRunner.run_shell"),
    ("tools.code_runner", "CodeRunner.run_python_file"),
    ("tools.code_runner", "CodeRunner.run_python_code"),
    ("tools.code_runner", "CodeRunner.run_node_file"),
    ("tools.engine_router", "EngineRouter._run_fileops"),
]


def _resolve(module, dotted):
    obj = __import__(module, fromlist=["x"])
    for part in dotted.split("."):
        obj = getattr(obj, part)
    return obj


@pytest.mark.parametrize("module,name", ENTRY_POINTS)
def test_every_side_effect_entry_point_is_gated(module, name):
    fn = _resolve(module, name)
    if getattr(fn, "_tom_guarded", False):
        return
    source = inspect.getsource(fn)
    assert any(m in source for m in GATE_MARKERS), f"{module}.{name} acts without the policy engine"


def test_the_desktop_ui_no_longer_runs_handlers_from_raw_dialogs():
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tom_desktop_app.py"),
               encoding="utf-8").read()
    uses = src.count("_prompt_and_run(") - src.count("def _prompt_and_run(")
    assert uses == 0, "quick actions/sidebar buttons must go through the agent (skill modes)"


# The one deliberate exception: "run shell: <command>", approved by the user (run_code) and gated.
SHELL_ALLOWED = {os.path.join("tools", "code_runner.py")}


def test_shell_true_only_in_the_approved_shell_runner():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = [os.path.join(dirpath, f) for folder in ("tools", "tom_core", "safety", "agents")
             for dirpath, _dirs, names in os.walk(os.path.join(root, folder)) for f in names if f.endswith(".py")]
    files += [os.path.join(root, f) for f in ("agent.py", "tom_desktop_app.py", "main.py")]
    import ast
    offenders = []
    for path in files:
        tree = ast.parse(open(path, encoding="utf-8-sig", errors="ignore").read())   # some files have a BOM
        for node in ast.walk(tree):                 # real calls only — docstrings and comments don't count
            if isinstance(node, ast.Call) and any(
                    k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True
                    for k in node.keywords):
                offenders.append(os.path.relpath(path, root))
    assert set(offenders) <= SHELL_ALLOWED, offenders


def test_emergency_stop_refuses_actions_through_the_entry_points(monkeypatch):
    from tom_core.policy import get_policy
    from tools.chat_apps import ChatApps
    from tools.hardware_control import HardwareControl
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    get_policy().halt("test")
    try:
        sent = asyncio.run(ChatApps().send("telegram", "@team", "hello"))
        assert sent["status"] == "blocked" and sent["sent"] is False
        hw = HardwareControl.__new__(HardwareControl)
        assert HardwareControl.click(hw, 10, 10)["status"] == "blocked"
    finally:
        get_policy().resume()
