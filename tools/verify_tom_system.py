from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.command_router import CommandRouter
from tools.nlp_parser import CommandParser
from tools.plugin_manager import PluginManager
from tools.project_paths import PROJECT_ROOT
from tools.skill_manager import SkillManager


Check = Callable[[], Dict[str, object]]


def _ok(name: str, detail: str = "") -> Dict[str, object]:
    return {"name": name, "status": "PASS", "detail": detail}


def _fail(name: str, detail: str) -> Dict[str, object]:
    return {"name": name, "status": "FAIL", "detail": detail}


def _run(cmd: List[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)


def check_python_version() -> Dict[str, object]:
    version = sys.version_info
    if version.major == 3 and version.minor == 11:
        return _ok("python_version", sys.version.split()[0])
    return _fail("python_version", f"Expected Python 3.11.x, got {sys.version}")


def check_project_root() -> Dict[str, object]:
    if PROJECT_ROOT == ROOT:
        return _ok("project_root", str(PROJECT_ROOT))
    return _fail("project_root", f"Expected {ROOT}, got {PROJECT_ROOT}")


def check_requirements_parse() -> Dict[str, object]:
    req = ROOT / "requirements.txt"
    bad = []
    for line_no, line in enumerate(req.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped and not any(op in stripped for op in ("==", ">=", "<=", "~=", "!=")):
            bad.append(f"{line_no}: {stripped}")
    if bad:
        return _fail("requirements_parse", "; ".join(bad))
    return _ok("requirements_parse", "requirements.txt syntax looks valid")


def check_imports() -> Dict[str, object]:
    modules = [
        "agent",
        "main",
        "tom_desktop_app",
        "tools.skill_manager",
        "tools.capability_resolver",
        "tools.plugin_manager",
        "tools.rag_memory",
    ]
    failed = []
    for name in modules:
        try:
            __import__(name)
        except Exception as exc:
            failed.append(f"{name}: {exc}")
    if failed:
        return _fail("imports", "; ".join(failed))
    return _ok("imports", f"{len(modules)} modules imported")


def check_ollama_models() -> Dict[str, object]:
    required = {"gemma4:latest", "qwen2.5-coder:7b-instruct", "nomic-embed-text:latest"}
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return _fail("ollama_models", f"Ollama unreachable: {exc}")

    installed = {item.get("name") for item in payload.get("models", [])}
    missing = sorted(required - installed)
    if missing:
        return _fail("ollama_models", f"Missing: {', '.join(missing)}")
    return _ok("ollama_models", f"Installed required models: {', '.join(sorted(required))}")


def check_skills() -> Dict[str, object]:
    manager = SkillManager()
    report = manager.health_report()
    if manager.count_skills() < 45:
        return _fail("skills", f"Only {manager.count_skills()} skills loaded")
    required_queries = [
        "frontend website",
        "react native app",
        "medical diagnosis",
        "predictive analysis",
        "iot esp32 mqtt sensor firmware",
        "vlsi verilog rtl fpga testbench",
    ]
    misses = [q for q in required_queries if not manager.route_task(q).matched]
    if misses:
        return _fail("skills", f"Unrouted skill queries: {', '.join(misses)}")
    return _ok("skills", json.dumps({
        "total": report["total"],
        "sources": report["sources"],
        "execution_modes": report["execution_modes"],
    }))


def check_skill_integrity() -> Dict[str, object]:
    manager = SkillManager()
    valid_modes = {"tool_backed", "external_command", "knowledge_only"}
    bad = []
    records = manager.records()
    for record in records:
        path = Path(record.path)
        if not record.name.strip():
            bad.append("blank skill name")
        if not record.content.strip():
            bad.append(f"{record.name}: empty content")
        if record.execution_mode not in valid_modes:
            bad.append(f"{record.name}: bad mode {record.execution_mode}")
        if not path.exists():
            bad.append(f"{record.name}: missing path {record.path}")
        if record.execution_mode in {"tool_backed", "external_command"} and not record.required_tools:
            bad.append(f"{record.name}: {record.execution_mode} without required tools")

    canonical_files = []
    for fpath in sorted((ROOT / "skills").glob("*.md")):
        canonical_files.append(("local", fpath.stem.lower()))
    external_root = ROOT / "awesome-claude-skills"
    if external_root.exists():
        for fpath in sorted(external_root.glob("**/SKILL.md")):
            canonical_files.append(("awesome", fpath.parent.name.lower()))
    seen = set()
    duplicates = []
    for source, name in canonical_files:
        key = (source, name)
        if key in seen:
            duplicates.append(f"{source}:{name}")
        seen.add(key)
    if duplicates:
        bad.append(f"duplicate skill files: {', '.join(sorted(duplicates)[:10])}")

    expected = {
        "iot esp32 mqtt sensor firmware": ("45-iot-skills", "tool_backed"),
        "vlsi verilog rtl fpga testbench": ("46-vlsi-skills", "tool_backed"),
        "ethical hacking web app checklist": ("22-cybersecurity-skills", "knowledge_only"),
        "full stack app with login api routes": ("03-backend-dev", "tool_backed"),
    }
    for query, (skill_name, mode) in expected.items():
        route = manager.route_task(query)
        if not route.matched or route.skill_name != skill_name or route.execution_mode != mode:
            bad.append(
                f"{query}: got {route.skill_name or 'unmatched'} "
                f"[{route.execution_mode}], expected {skill_name} [{mode}]"
            )

    if bad:
        return _fail("skill_integrity", "; ".join(bad[:20]))

    report = manager.health_report()
    return _ok("skill_integrity", json.dumps({
        "total": len(records),
        "sources": report["sources"],
        "execution_modes": report["execution_modes"],
    }))


def check_routing() -> Dict[str, object]:
    router = CommandRouter()
    parser = CommandParser()
    cases = {
        "open chrome": ("browser", "open_app", "execute_open_command"),
        "open vs code": ("desktop", "open_app", "execute_open_command"),
        "review my email inbox": ("communication", "email_inbox", "execute_email_inbox_workflow"),
        "send email to john@example.com saying hello": ("sensitive", "send_email", "execute_email_send"),
        "open whatsapp and send hello to Madhu": ("communication", "whatsapp_message", "execute_whatsapp_task"),
        "create a word document about leave letter": ("content", "create_word_doc", "execute_word_task"),
        "create an excel budget tracker": ("content", "create_excel", "execute_excel_task"),
        "create a powerpoint presentation about AI": ("content", "create_presentation", "execute_presentation_task"),
        "analyze excel sales.xlsx": ("data", "data_analysis", "execute_data_analysis"),
        "build a frontend dashboard": ("chat", "skill_task", "generate_chat_response"),
        "create an NLP classifier": ("chat", "skill_task", "generate_chat_response"),
        "build a full stack web app with login and API routes": ("content", "skill_task", "execute_code_project"),
        "ethical hacking checklist for web app": ("chat", "chat", "generate_chat_response"),
    }
    failures = []
    for command, (route_category, intent, handler) in cases.items():
        route = router.route(command)
        parsed = parser.parse(command)
        if route.category != route_category or parsed.get("intent") != intent or route.handler != handler:
            failures.append(
                f"{command}: route={route.category}, handler={route.handler}, intent={parsed.get('intent')}"
            )
    if failures:
        return _fail("routing", "; ".join(failures))
    return _ok("routing", f"{len(cases)} route cases passed")


def check_plugins() -> Dict[str, object]:
    manager = PluginManager(str(ROOT))
    plugins = manager.discover_plugins()
    names = {plugin.name for plugin in plugins}
    required = {"email_agent", "instagram_agent", "instagram_ai_news_agent"}
    missing = required - names
    if missing:
        return _fail("plugins", f"Missing plugins: {', '.join(sorted(missing))}")
    if not manager.match_plugin("run email agent once"):
        return _fail("plugins", "Plugin matcher failed for email agent")
    return _ok("plugins", f"Discovered {len(plugins)} plugins")


def check_compile() -> Dict[str, object]:
    proc = _run([
        sys.executable,
        "-m",
        "compileall",
        "-q",
        "-x",
        "venv|build|dist|\\.git|\\.cache|__pycache__",
        ".",
    ])
    if proc.returncode != 0:
        return _fail("compile", (proc.stdout + proc.stderr)[-2000:])
    return _ok("compile", "Project Python files compile")


def check_comprehensive_tests() -> Dict[str, object]:
    proc = _run([sys.executable, "test_tom_comprehensive.py"], timeout=180)
    if proc.returncode != 0 or "0 failed" not in proc.stdout:
        return _fail("comprehensive_tests", (proc.stdout + proc.stderr)[-2000:])
    return _ok("comprehensive_tests", "test_tom_comprehensive.py passed")


def check_smoke_tests() -> Dict[str, object]:
    proc = _run([sys.executable, "tools/smoke_tests.py"], timeout=180)
    if proc.returncode != 0:
        return _fail("smoke_tests", (proc.stdout + proc.stderr)[-2000:])
    return _ok("smoke_tests", "tools/smoke_tests.py passed")


def check_sandbox_functional_tests() -> Dict[str, object]:
    proc = _run([sys.executable, "tools/sandbox_functional_tests.py"], timeout=180)
    if proc.returncode != 0:
        return _fail("sandbox_functional_tests", (proc.stdout + proc.stderr)[-2000:])
    return _ok("sandbox_functional_tests", "sandbox dispatch tests passed")


def main() -> int:
    checks: List[Check] = [
        check_python_version,
        check_project_root,
        check_requirements_parse,
        check_imports,
        check_ollama_models,
        check_skills,
        check_skill_integrity,
        check_routing,
        check_plugins,
        check_compile,
        check_comprehensive_tests,
        check_smoke_tests,
        check_sandbox_functional_tests,
    ]

    results = []
    for check in checks:
        try:
            result = check()
        except Exception as exc:
            result = _fail(check.__name__.replace("check_", ""), str(exc))
        results.append(result)
        print(f"[{result['status']}] {result['name']}: {result['detail']}")

    failed = [r for r in results if r["status"] != "PASS"]
    print("\nSUMMARY:", "PASS" if not failed else "FAIL")
    print(json.dumps({"failed": failed, "total": len(results)}, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
