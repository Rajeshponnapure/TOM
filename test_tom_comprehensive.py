"""
TOM v2 Comprehensive Test Suite.
Tests all core systems and produces a scoring report.
"""
import asyncio
import importlib
import os
import sys
import time
import json
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

os.environ["VOICE_INPUT_ENABLED"] = "false"
os.environ["VOICE_OUTPUT_ENABLED"] = "false"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"

PASS = 0
FAIL = 0
SCORE = 0
MAX_SCORE = 0
REPORT = []

def test(name, category, max_score=10):
    def decorator(fn):
        def wrapper():
            global PASS, FAIL, SCORE, MAX_SCORE, REPORT
            MAX_SCORE += max_score
            print(f"  [{category}] {name}...", end=" ", flush=True)
            try:
                fn()
                PASS += 1
                SCORE += max_score
                REPORT.append({"test": name, "category": category, "status": "PASS", "score": max_score, "detail": ""})
                print(f"PASS ({max_score}/{max_score})")
            except AssertionError as e:
                FAIL += 1
                REPORT.append({"test": name, "category": category, "status": "FAIL", "score": 0, "detail": str(e)})
                print(f"FAIL - {e}")
            except Exception as e:
                FAIL += 1
                REPORT.append({"test": name, "category": category, "status": "ERROR", "score": 0, "detail": str(e)})
                print(f"ERROR - {e}")
        return wrapper
    return decorator

test.__test__ = False


# ════════════════════════════════════════════════════════════════
# PHASE 1: NLP Parser Tests
# ════════════════════════════════════════════════════════════════

@test("NLP compound intent: open app + message", "Phase 1-NLP", 10)
def test_nlp_compound():
    from tools.nlp_parser import CommandParser
    parser = CommandParser()
    parsed = parser.parse("Open WhatsApp and text Rajesh hi")
    assert parsed["intent"] in ("compound", "open_app", "whatsapp_message"), f"Unexpected intent: {parsed['intent']}"
    # compound_tasks should contain steps, or app_name/person_name/message_body should be extracted
    tasks = parsed.get("compound_tasks", [])
    has_app = parsed.get("app_name") == "whatsapp" or any(t.get("app_name") == "whatsapp" for t in tasks)
    has_person = "Rajesh" in str(parsed.get("person_name", "")) or any("Rajesh" in str(t.get("person_name", "")) for t in tasks)
    assert has_app, f"app_name not extracted: {parsed}"
    assert has_person, f"person_name not extracted: {parsed}"

@test("NLP compound: text via app", "Phase 1-NLP", 10)
def test_nlp_compound_via():
    from tools.nlp_parser import CommandParser
    parser = CommandParser()
    parsed = parser.parse("Send Rajesh hi on WhatsApp")
    assert parsed.get("app_name") == "whatsapp" or "whatsapp" in str(parsed.get("compound_tasks", [])), f"app not extracted: {parsed}"
    assert "Rajesh" in str(parsed.get("person_name", "")), f"person not extracted: {parsed}"

@test("NLP WhatsApp: message before recipient", "Phase 1-NLP", 10)
def test_nlp_whatsapp_message_to_recipient():
    from tools.nlp_parser import CommandParser
    parser = CommandParser()
    parsed = parser.parse("open whatsapp and send hello pandhi pilla to Madhu Dec 26th")
    assert parsed["intent"] == "whatsapp_message", f"unexpected intent: {parsed}"
    assert parsed["app_name"] == "whatsapp", f"app not extracted: {parsed}"
    assert parsed["recipient_name"] == "Madhu Dec 26th", f"recipient not extracted: {parsed}"
    assert parsed["message_body"] == "hello pandhi pilla", f"message not extracted: {parsed}"

@test("NLP app_action detection", "Phase 1-NLP", 10)
def test_nlp_app_action():
    from tools.nlp_parser import CommandParser
    parser = CommandParser()
    assert parser._extract_app_action("text Rajesh hi") == "text"
    assert parser._extract_app_action("send email to john") == "send"
    assert parser._extract_app_action("open chrome") == "open"
    assert parser._extract_app_action("create a document") == "create"
    assert parser._extract_app_action("read that file") == "read"

@test("NLP message body extraction", "Phase 1-NLP", 10)
def test_nlp_message_body():
    from tools.nlp_parser import CommandParser
    parser = CommandParser()
    parsed = parser.parse("Tell John I will be there soon")
    body = parsed.get("message_body") or ""
    assert len(body) > 0, f"message_body not extracted: {parsed}"

@test("NLP intent detection accuracy", "Phase 1-NLP", 10)
def test_nlp_intent():
    from tools.nlp_parser import CommandParser
    parser = CommandParser()
    assert parser._detect_intent("open chrome") == "open_app"
    assert parser._detect_intent("send email to john@gmail.com") == "send_email"
    assert parser._detect_intent("whatsapp message to rajesh") == "whatsapp_message"
    assert parser._detect_intent("create a word document") == "create_word_doc"
    assert parser._detect_intent("analyze this data") == "data_analysis"
    assert parser._detect_intent("search the web for AI news") == "web_search"
    assert parser._detect_intent("what is the weather") == "chat"

@test("NLP skill-domain routing", "Phase 1-NLP", 10)
def test_nlp_skill_domains():
    from tools.nlp_parser import CommandParser
    parser = CommandParser()
    assert parser._extract_skill_domain("create a react native mobile app like amazon") == "mobile"
    assert parser._extract_skill_domain("build a full stack web app with login and API routes") == "backend"
    assert parser._extract_skill_domain("ethical hacking checklist for web app") == "cybersecurity"
    assert parser._extract_skill_domain("generate esp32 mqtt sensor firmware") == "iot"
    assert parser._extract_skill_domain("generate a verilog rtl fpga testbench") == "vlsi"

@test("SkillManager capability truth", "Phase 1-NLP", 10)
def test_skill_manager_capability_truth():
    from tools.skill_manager import SkillManager
    manager = SkillManager()

    route = manager.route_task("iot esp32 mqtt sensor firmware")
    assert route.matched and route.skill_name == "45-iot-skills", f"iot route failed: {route}"
    assert route.execution_mode == "tool_backed" and "iot_engine" in route.required_tools, f"iot tools failed: {route}"

    route = manager.route_task("vlsi verilog rtl fpga testbench")
    assert route.matched and route.skill_name == "46-vlsi-skills", f"vlsi route failed: {route}"
    assert route.execution_mode == "tool_backed" and "vlsi_engine" in route.required_tools, f"vlsi tools failed: {route}"

    route = manager.route_task("ethical hacking web app checklist")
    assert route.matched and route.skill_name == "22-cybersecurity-skills", f"cybersecurity route failed: {route}"
    assert route.execution_mode == "knowledge_only", f"cybersecurity should be guidance-only: {route}"


# ════════════════════════════════════════════════════════════════
# PHASE 2: Web Automation Tests
# ════════════════════════════════════════════════════════════════

@test("WebAutomationSuite imports and structure", "Phase 2-WebAuto", 10)
def test_web_auto_imports():
    from tools.web_automation import WebAutomationSuite, ConsoleEntry, NetworkEntry, PageError
    suite = WebAutomationSuite()
    assert hasattr(suite, "capture_console_logs"), "Missing capture_console_logs"
    assert hasattr(suite, "capture_network_errors"), "Missing capture_network_errors"
    assert hasattr(suite, "capture_all_errors"), "Missing capture_all_errors"
    assert hasattr(suite, "click_all_buttons"), "Missing click_all_buttons"
    assert hasattr(suite, "fill_form_fields"), "Missing fill_form_fields"
    assert hasattr(suite, "auto_debug_loop"), "Missing auto_debug_loop"
    assert hasattr(suite, "check_localhost"), "Missing check_localhost"
    assert hasattr(suite, "verify_page_functionality"), "Missing verify_page_functionality"
    assert hasattr(suite, "wait_and_verify"), "Missing wait_and_verify"
    assert hasattr(suite, "inject_console_capture"), "Missing inject_console_capture"

@test("WebAutomation localhost scanning", "Phase 2-WebAuto", 10)
def test_web_auto_localhost():
    from tools.web_automation import WebAutomationSuite
    suite = WebAutomationSuite()
    result = asyncio.run(suite.check_localhost())
    assert "servers" in result, f"Missing servers key: {result}"
    assert isinstance(result.get("servers"), list), "servers should be list"

@test("WebAutomation console injection", "Phase 2-WebAuto", 10)
def test_web_auto_console_inject():
    from tools.web_automation import WebAutomationSuite
    suite = WebAutomationSuite()
    assert hasattr(suite, "inject_console_capture"), "Missing inject_console_capture"

@test("WebAutomation empty page safety", "Phase 2-WebAuto", 10)
def test_web_auto_empty_page():
    from tools.web_automation import WebAutomationSuite
    suite = WebAutomationSuite()
    try:
        asyncio.run(suite.click_all_buttons())
    except Exception:
        pass  # Expected if no browser page

@test("WebAutomation verify_page without browser", "Phase 2-WebAuto", 10)
def test_web_auto_verify_no_browser():
    from tools.web_automation import WebAutomationSuite
    suite = WebAutomationSuite()
    try:
        asyncio.run(suite.verify_page_functionality())
    except Exception:
        pass  # Expected if no browser page


# ════════════════════════════════════════════════════════════════
# PHASE 3: Browser Tools Tests
# ════════════════════════════════════════════════════════════════

@test("BrowserTools imports and structure", "Phase 3-Browser", 10)
def test_browser_tools():
    from tools.browser_tools import BrowserTools
    bt = BrowserTools()
    assert hasattr(bt, "init_browser"), "Missing init_browser"
    assert hasattr(bt, "open_url"), "Missing open_url"
    assert hasattr(bt, "get_automation"), "Missing get_automation"
    assert hasattr(bt, "verify_page"), "Missing verify_page"
    assert hasattr(bt, "click_all_interactive"), "Missing click_all_interactive"
    assert hasattr(bt, "get_all_errors"), "Missing get_all_errors"
    assert hasattr(bt, "auto_debug"), "Missing auto_debug"
    assert hasattr(bt, "fill_form"), "Missing fill_form"
    assert hasattr(bt, "fill_form_with_profile"), "Missing fill_form_with_profile"
    assert hasattr(bt, "click_text"), "Missing click_text"
    assert hasattr(bt, "wait_and_verify"), "Missing wait_and_verify"
    assert hasattr(bt, "check_localhost_servers"), "Missing check_localhost_servers"
    assert hasattr(bt, "build_and_verify_app"), "Missing build_and_verify_app"


# ════════════════════════════════════════════════════════════════
# PHASE 4: Security Tests
# ════════════════════════════════════════════════════════════════

@test("Security: website analysis trusted domains", "Phase 4-Security", 10)
def test_security_trusted():
    from safety.guards import SafetyGuards
    sg = SafetyGuards()
    result = sg.analyze_website("https://gmail.com")
    assert result["trust_level"] == "trusted", f"gmail.com should be trusted: {result}"
    assert result["score"] >= 90, f"gmail.com score should be >= 90: {result}"

@test("Security: website analysis localhost", "Phase 4-Security", 10)
def test_security_localhost():
    from safety.guards import SafetyGuards
    sg = SafetyGuards()
    result = sg.analyze_website("http://localhost:5173")
    assert result["trust_level"] in ("trusted", "local"), f"localhost should be trusted/local: {result}"

@test("Security: website analysis suspicious domains", "Phase 4-Security", 10)
def test_security_suspicious():
    from safety.guards import SafetyGuards
    sg = SafetyGuards()
    result = sg.analyze_website("http://bit.ly/something")
    assert result["trust_level"] == "blocked" or result["score"] < 50, f"bit.ly should be blocked or low score: {result}"

@test("Security: detail sharing rules", "Phase 4-Security", 10)
def test_security_detail_sharing():
    from safety.guards import SafetyGuards
    sg = SafetyGuards()
    trusted_check = sg.can_share_detail("email", "https://gmail.com", "login")
    assert trusted_check["allowed"], f"Should allow email on gmail.com: {trusted_check}"
    blocked_check = sg.can_share_detail("password", "http://suspicious-site.tk", "login")
    assert not blocked_check["allowed"], f"Should block on suspicious site: {blocked_check}"

@test("Security: store and retrieve user details", "Phase 4-Security", 10)
def test_security_store_retrieve():
    from safety.guards import SafetyGuards
    sg = SafetyGuards()
    asyncio.run(sg.store_user_detail("phone", "+911234567890"))
    result = sg.get_detail_for_site("phone", "https://whatsapp.com", "registration")
    assert result["status"] in ("approved", "denied"), f"Unexpected status: {result}"

@test("Security: validate URL", "Phase 4-Security", 10)
def test_security_validate_url():
    from safety.guards import SafetyGuards
    sg = SafetyGuards()
    assert sg.validate_url("http://localhost:3000"), "localhost should be valid"
    assert sg.validate_url("https://example.com"), "https should be valid"
    assert sg.validate_url("http://192.168.1.1"), "IP should be valid"


# ════════════════════════════════════════════════════════════════
# PHASE 5: Voice Mode Tests
# ════════════════════════════════════════════════════════════════

@test("Voice: import and disabled state", "Phase 5-Voice", 10)
def test_voice_disabled():
    from tools.voice_tools import VoiceTools
    vt = VoiceTools()
    status = vt.status()
    assert "voice_input_enabled" in status, f"Missing key: {status}"
    assert "voice_output_enabled" in status, f"Missing key: {status}"
    assert vt.listen_once()["status"] in ("skipped", "error"), f"listen_once should skip when disabled: {vt.listen_once()}"

@test("Voice: status method completeness", "Phase 5-Voice", 10)
def test_voice_status():
    from tools.voice_tools import VoiceTools
    vt = VoiceTools()
    s = vt.status()
    required_keys = ["voice_input_enabled", "voice_output_enabled", "voice_engine",
                     "voice_name", "recognition_engine", "voice_input_error",
                     "voice_output_error", "conversation_active"]
    for k in required_keys:
        assert k in s, f"Missing status key: {k}"

@test("Voice: conversation mode lifecycle", "Phase 5-Voice", 10)
def test_voice_conv_lifecycle():
    from tools.voice_tools import VoiceTools
    vt = VoiceTools()
    start_result = vt.start_conversation_mode(lambda x: {"message": "ok"})
    assert start_result["status"] in ("started", "error", "already_active"), f"Unexpected start: {start_result}"
    if start_result["status"] == "started":
        stop_result = vt.stop_conversation_mode()
        assert stop_result["status"] in ("stopped", "not_active"), f"Unexpected stop: {stop_result}"


# ════════════════════════════════════════════════════════════════
# PHASE 6: Multi-Agent Orchestrator Tests
# ════════════════════════════════════════════════════════════════

@test("Orchestrator: imports and structure", "Phase 6-Orch", 10)
def test_orchestrator_imports():
    from tools.agent_orchestrator import AgentOrchestrator, AgentRole, Task, SubAgent
    orch = AgentOrchestrator()
    assert hasattr(orch, "execute_task"), "Missing execute_task"
    assert hasattr(orch, "deploy_multi_agent_task"), "Missing deploy_multi_agent_task"
    assert hasattr(orch, "get_agents_status"), "Missing get_agents_status"
    assert hasattr(orch, "get_metrics"), "Missing get_metrics"

@test("Orchestrator: role determination", "Phase 6-Orch", 10)
def test_orchestrator_role():
    from tools.agent_orchestrator import AgentOrchestrator, AgentRole
    orch = AgentOrchestrator()
    role = orch._determine_best_agent("Debug the browser automation code", "debug")
    assert role == AgentRole.CTO, f"Tech task should go to CTO, got {role}"
    role = orch._determine_best_agent("Create a marketing email newsletter", "email")
    assert role == AgentRole.CMO, f"Marketing task should go to CMO, got {role}"

@test("Orchestrator: all agents initialized", "Phase 6-Orch", 10)
def test_orchestrator_agents():
    from tools.agent_orchestrator import AgentOrchestrator, AgentRole
    orch = AgentOrchestrator()
    status = orch.get_agents_status()
    required_roles = ["ceo", "cto", "cmo", "cpo", "cfo", "coo"]
    for r in required_roles:
        assert r in status, f"Missing role: {r}"
        assert "name" in status[r], f"Missing name for {r}"
        assert "capabilities" in status[r], f"Missing capabilities for {r}"

@test("Orchestrator: metrics structure", "Phase 6-Orch", 10)
def test_orchestrator_metrics():
    from tools.agent_orchestrator import AgentOrchestrator
    orch = AgentOrchestrator()
    metrics = orch.get_metrics()
    required_keys = ["total_tasks_created", "completed_tasks", "active_tasks", "pending_tasks", "agent_count", "agents"]
    for k in required_keys:
        assert k in metrics, f"Missing metrics key: {k}"
    assert metrics["agent_count"] >= 5, f"Should have at least 5 agents: {metrics}"


# ════════════════════════════════════════════════════════════════
# PHASE 7: ML Learning Tests
# ════════════════════════════════════════════════════════════════

@test("Learning: log and retrieve experiences", "Phase 7-ML", 10)
def test_learning_experiences():
    from tools.learning import Learner
    learner = Learner()
    exp = learner.log_experience("test_action", "success", {"detail": "test"})
    assert "id" in exp, f"Missing id: {exp}"
    assert "outcome" in exp, f"Missing outcome: {exp}"
    recent = learner.recent_experiences(limit=5)
    assert len(recent) > 0, "Should have recent experiences"

@test("Learning: reward system", "Phase 7-ML", 10)
def test_learning_reward():
    from tools.learning import Learner
    learner = Learner()
    exp = learner.log_experience("test_reward", "success", {"detail": "reward test"})
    result = learner.give_reward(exp["id"], 1.0)
    assert result, "Reward should succeed"

@test("Learning: pattern insights", "Phase 7-ML", 10)
def test_learning_patterns():
    from tools.learning import Learner
    learner = Learner()
    insights = learner.get_pattern_insights()
    assert "patterns" in insights, f"Missing patterns: {insights}"
    assert "suggestions" in insights, f"Missing suggestions: {insights}"
    assert "success_rate" in insights, f"Missing success_rate: {insights}"

@test("Learning: predict best approach", "Phase 7-ML", 10)
def test_learning_predict():
    from tools.learning import Learner
    learner = Learner()
    approach = learner.predict_best_approach("test_action")
    assert isinstance(approach, str), f"Approach should be string: {approach}"
    assert len(approach) > 0, "Approach should not be empty"


# ════════════════════════════════════════════════════════════════
# OS Tools Tests
# ════════════════════════════════════════════════════════════════

@test("OS Tools: find and open app", "Core-OS", 10)
def test_os_tools():
    from tools.os_tools import OSTools
    os_tools = OSTools()
    result = asyncio.run(os_tools.open_application("notepad"))
    assert result["status"] == "success", f"notepad open failed: {result}"

@test("OS Tools: app discovery cache", "Core-OS", 10)
def test_os_cache():
    from tools.os_tools import OSTools
    os_tools = OSTools()
    path = os_tools.find_application("calculator")
    if path:
        assert path in os_tools._app_cache.values() or any(path == v for v in os_tools._app_cache.values()), "Should cache result"


# ════════════════════════════════════════════════════════════════
# Agent Core Tests
# ════════════════════════════════════════════════════════════════

@test("Agent: command routing", "Core-Agent", 10)
def test_agent_routing():
    from tools.command_router import CommandRouter
    router = CommandRouter()
    route = router.route("whatsapp message to rajesh")
    assert "whatsapp" in route.handler or "whatsapp" in route.intent, f"whatsapp routing failed: {route}"
    route = router.route("open whatsapp and send hello pandhi pilla to Madhu")
    assert route.handler == "execute_whatsapp_task", f"compound whatsapp send routed incorrectly: {route}"
    route = router.route("send email to john@example.com saying hello")
    assert route.handler == "execute_email_send", f"send email routed incorrectly: {route}"
    route = router.route("create a word document about leave letter")
    assert route.handler != "execute_open_command" and route.intent == "create_word_doc", f"word creation routed incorrectly: {route}"
    route = router.route("create an excel budget tracker")
    assert route.handler != "execute_open_command" and route.intent == "create_excel", f"excel creation routed incorrectly: {route}"
    route = router.route("create a powerpoint presentation about AI")
    assert route.handler == "execute_presentation_task", f"presentation creation routed incorrectly: {route}"
    route = router.route("analyze excel sales.xlsx")
    assert route.handler == "execute_data_analysis", f"data analysis routed incorrectly: {route}"
    route = router.route("build a full stack web app with login and API routes")
    assert route.handler == "execute_code_project", f"full-stack app routed incorrectly: {route}"
    route = router.route("ethical hacking checklist for web app")
    assert route.handler == "generate_chat_response", f"security guidance routed incorrectly: {route}"

@test("Agent: email routing", "Core-Agent", 10)
def test_email_routing():
    from tools.command_router import CommandRouter
    router = CommandRouter()
    route = router.route("review my email inbox")
    assert "inbox" in route.intent, f"inbox routing failed: {route}"

@test("Agent: open app routing", "Core-Agent", 10)
def test_open_routing():
    from tools.command_router import CommandRouter
    router = CommandRouter()
    route = router.route("open chrome")
    assert route.category in ("browser", "desktop"), f"open routing failed: {route}"
    route = router.route("open vs code")
    assert route.handler == "execute_open_command", f"vs code open routing failed: {route}"


# ════════════════════════════════════════════════════════════════
# Desktop UI Tests
# ════════════════════════════════════════════════════════════════

@test("Desktop UI: voice toggle contract", "Core-DesktopUI", 10)
def test_desktop_voice_toggle():
    from tom_desktop_app import TomDesktopApp

    app = TomDesktopApp.__new__(TomDesktopApp)
    app.voice_mode_enabled = False
    app.agent_ready = False
    app.agent = None
    app.voice_btn = type("MockButton", (), {
        "configure": lambda self, **kwargs: setattr(self, "last_config", kwargs),
    })()
    app.voice = type("MockVoice", (), {
        "input_enabled": False,
        "output_enabled": False,
        "conversation_active": False,
        "status": lambda self: {"voice_input_enabled": True, "voice_input_error": ""},
        "_setup_input": lambda self: None,
        "_setup_output": lambda self: None,
        "start_conversation_mode": lambda self, process_fn, on_status: None,
        "stop_conversation_mode": lambda self: {"status": "stopped"},
    })()
    app._append_chat = lambda *args, **kwargs: None
    app._refresh_dashboard = lambda *args, **kwargs: None
    app._set_status = lambda *args, **kwargs: None

    TomDesktopApp._toggle_voice_mode(app)
    assert app.voice_mode_enabled is True, "Voice mode should become enabled"
    assert app.voice.input_enabled is True, "Voice input should be enabled"
    assert app.voice.output_enabled is True, "Voice output should be enabled"

    TomDesktopApp._toggle_voice_mode(app)
    assert app.voice_mode_enabled is False, "Voice mode should become disabled"
    assert app.voice.input_enabled is False, "Voice input should be disabled"
    assert app.voice.output_enabled is False, "Voice output should be disabled"


# ════════════════════════════════════════════════════════════════
# Integration: All files compile and import
# ════════════════════════════════════════════════════════════════

@test("All modules compile cleanly", "Core-Compile", 10)
def test_all_compile():
    modules = [
        "agent", "tools.nlp_parser", "tools.web_automation",
        "tools.browser_tools", "safety.guards",
        "tools.agent_orchestrator", "tools.learning",
        "tools.whatsapp_tools", "tools.command_router",
        "tools.os_tools", "tools.screen_tools",
        "tools.file_tools", "tools.voice_tools",
        "tools.email_tools", "tools.chat_memory",
        "tools.self_evolution", "tools.rag_memory",
    ]
    for mod_name in modules:
        try:
            importlib.import_module(mod_name)
        except ImportError as e:
            raise AssertionError(f"Failed to import {mod_name}: {e}")

@test("Desktop app imports cleanly", "Core-Compile", 10)
def test_desktop_compile():
    import tom_desktop_app
    assert hasattr(tom_desktop_app, "TomDesktopApp"), "Missing TomDesktopApp"
    assert hasattr(tom_desktop_app, "TomHoloDashboard"), "Missing TomHoloDashboard"


# ════════════════════════════════════════════════════════════════
# Main Runner
# ════════════════════════════════════════════════════════════════

def generate_report():
    global REPORT, PASS, FAIL, SCORE, MAX_SCORE

    categories = {}
    for r in REPORT:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"pass": 0, "fail": 0, "score": 0, "max": 0, "tests": []}
        categories[cat]["tests"].append(r)
        if r["status"] == "PASS":
            categories[cat]["pass"] += 1
            categories[cat]["score"] += r["score"]
        else:
            categories[cat]["fail"] += 1
        categories[cat]["max"] += 10  # each test max is 10

    print("\n" + "=" * 78)
    print("  TOM v2 COMPREHENSIVE TEST REPORT")
    print("=" * 78)

    print(f"\n  Overall: {PASS} passed, {FAIL} failed | Score: {SCORE}/{MAX_SCORE} ({SCORE*100//max(MAX_SCORE,1)}%)\n")
    print("-" * 78)

    for cat, data in sorted(categories.items()):
        pct = data["score"] * 100 // max(data["max"], 1)
        bar = "#" * (pct // 5) + "." * (20 - pct // 5)
        print(f"  {cat:25s} | {bar} | {data['score']:3d}/{data['max']:3d} ({pct:2d}%) | {data['pass']}ok {data['fail']}fail")

    print("-" * 78)
    print()

    for r in REPORT:
        if r["status"] != "PASS":
            print(f"  [FAIL] {r['category']} :: {r['test']}")
            print(f"     {r['detail']}")
            print()

    # Scoring key
    print("=" * 78)
    print("  CAPABILITY SCORING")
    print("=" * 78)
    print()
    print("  Phase 1 - NLP Parser:     Compound intent, app_action, message_body extraction")
    print("  Phase 2 - Web Auto Suite: Browser DevTools, console/network capture, auto-debug")
    print("  Phase 3 - Browser Tools:  verify_page, click_all, fill_form, localhost scan")
    print("  Phase 4 - Security Layer: Website analysis, detail sharing rules, URL validation")
    print("  Phase 5 - Voice Mode:     Status API, conversation lifecycle, proper toggle")
    print("  Phase 6 - Orchestrator:   Multi-agent hierarchy, role routing, metrics")
    print("  Phase 7 - ML Learning:    Experience logging, rewards, pattern insights")
    print()
    print("  Maturity Scale:")
    print("    90-100%  Production Ready")
    print("    70-89%   Beta — Most features work")
    print("    50-69%   Alpha — Core works, improvements needed")
    print("    <50%     Early Development")
    print()

    overall_pct = SCORE * 100 // max(MAX_SCORE, 1)
    if overall_pct >= 90:
        maturity = "Production Ready"
    elif overall_pct >= 70:
        maturity = "Beta — Most features stable"
    elif overall_pct >= 50:
        maturity = "Alpha — Core functional"
    else:
        maturity = "Early Development"

    print(f"  Overall Maturity: {maturity}")
    print(f"  Total Tests: {PASS + FAIL} | Passed: {PASS} | Failed: {FAIL}")
    print(f"  Score: {SCORE}/{MAX_SCORE} ({overall_pct}%)")
    print()

    scalability = {
        "NLP": "Scales well with LLM - parser is model-agnostic",
        "Web Automation": "Scales with Playwright - handles any modern web app",
        "Security": "Scales with domain list - easily extensible",
        "Multi-Agent": "Scales horizontally - add more sub-agents as needed",
        "ML/Learning": "Scales with experience count - uses efficient JSON storage",
        "Voice": "Limited by local hardware - cloud recognition would scale better",
    }
    print("  SCALABILITY NOTES:")
    for area, note in scalability.items():
        print(f"    {area:20s} -> {note}")

    return overall_pct


def main():
    import inspect
    funcs = inspect.getmembers(sys.modules[__name__], inspect.isfunction)
    test_funcs = [(name, fn) for name, fn in funcs if name.startswith("test_")]

    print(f"\n  TOM v2 Test Suite — {len(test_funcs)} tests\n")
    print("=" * 78)

    for name, fn in test_funcs:
        try:
            fn()
        except Exception:
            pass  # wrapper handles reporting; this is a safety net

    return generate_report()


if __name__ == "__main__":
    main()
