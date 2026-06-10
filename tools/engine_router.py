"""
Unified Engine Router — gives the agent brain (and therefore BOTH the CLI and
the GUI chat box) natural-language access to the specialized engines that were
previously reachable only through GUI quick-action buttons:

    ML, IoT, VLSI, Hardware, Game Dev, Blender, News, Env/Dependencies,
    Auto-Update, Autonomous multi-step, Multi-Agent orchestration,
    Voice+ text emotion analysis.

Design contract (production-safety):
  * ADDITIVE — detection is conservative; if no engine clearly matches, the
    agent falls through to its existing skill/chat routing exactly as before.
  * Every engine is lazy-loaded and failure-isolated: a missing dependency
    degrades to an explanatory message, never an exception.
  * All calls inherit the agent's SafetyGuards gate because dispatch happens
    inside TomAgent.execute_task (unlike the old GUI-only path, which bypassed
    safety entirely).
  * Both grammars work: natural language ("train a linear regression on ...")
    and the expert prefix syntax the GUI dialogs used ("regression linear
    X=[[1],[2],[3]] y=[2,4,6]").
"""

import ast
import re
from typing import Any, Dict, List, Optional


def _safe_literal(text: str) -> Optional[Any]:
    """Parse a Python literal (list/number) without eval()."""
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return None


def _extract_kv_list(command: str, key: str) -> Optional[Any]:
    """Extract X=[[1],[2]] / y=[1,2] style values from a command string."""
    m = re.search(rf"\b{key}\s*=\s*(\[[^=]*?\])(?:\s|$)", command)
    if m:
        return _safe_literal(m.group(1))
    return None


def _extract_kv_num(command: str, key: str, default: int) -> int:
    m = re.search(rf"\b{key}\s*=\s*(\d+)", command)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return default
    return default


def parse_schedule_command(command: str):
    """'schedule X every N hours/minutes' / 'every morning' → (task, hours).
    Returns (None, None) if no schedule intent."""
    c = command.strip()
    low = c.lower()
    m = re.search(r"\bevery\s+(\d+(?:\.\d+)?)\s*(hour|hr|minute|min)s?\b", low)
    hours = None
    if m:
        val = float(m.group(1))
        hours = val if m.group(2).startswith(("hour", "hr")) else val / 60.0
    elif re.search(r"\bevery\s+(morning|day|daily)\b", low):
        hours = 24.0
    elif re.search(r"\bevery\s+hour\b", low):
        hours = 1.0
    if hours is None:
        return None, None
    task = re.sub(r"^\s*schedule\s*:?\s*", "", c, flags=re.I)
    task = re.sub(r"\bevery\s+(\d+(?:\.\d+)?\s*(?:hour|hr|minute|min)s?|morning|day|daily|hour)\b.*$",
                  "", task, flags=re.I).strip(" ,.-")
    return (task or None), hours


class EngineRouter:
    """Detects and dispatches engine-class commands for TomAgent."""

    # Demo data used when the user asks for an algorithm without data —
    # identical fallbacks to the original GUI handlers.
    _DEMO_XY = ([[1], [2], [3], [4]], [2, 4, 6, 8])
    _DEMO_CLS = ([[1], [2], [3], [4]], [0, 0, 1, 1])
    _DEMO_CLUSTER = [[1, 2], [2, 3], [8, 9], [9, 10]]
    _DEMO_SERIES = [10, 12, 15, 14, 18, 20, 22, 25]
    _DEMO_ANOM = [[1], [2], [10], [3], [4], [100]]

    def __init__(self, agent=None):
        self._agent = agent
        self._engines: Dict[str, Any] = {}

    # ── Lazy engine loading ──────────────────────────────────────────────
    def _get(self, key: str):
        if key in self._engines:
            return self._engines[key]
        engine = None
        try:
            if key == "ml":
                from tools.ml_engine import MLEngine
                engine = MLEngine()
            elif key == "iot":
                from tools.iot_engine import IoTEngine
                engine = IoTEngine()
            elif key == "vlsi":
                from tools.vlsi_engine import VLSIEngine
                engine = VLSIEngine()
            elif key == "hardware":
                from tools.hardware_control import HardwareControl
                engine = HardwareControl()
            elif key == "gamedev":
                from tools.game_dev import GameDevEngine
                engine = GameDevEngine()
            elif key == "blender":
                from tools.blender_control import BlenderControl
                engine = BlenderControl()
            elif key == "news":
                from tools.news_agent import NewsAgent
                engine = NewsAgent()
            elif key == "deps":
                from tools.dependency_manager import DependencyManager
                engine = DependencyManager()
            elif key == "autoupdate":
                from tools.auto_update import AutoUpdate
                engine = AutoUpdate()
            elif key == "voiceplus":
                from tools.voice_enhanced import VoiceEnhanced
                engine = VoiceEnhanced()
            elif key == "coderun":
                from tools.code_runner import CodeRunner
                engine = CodeRunner()
            elif key == "autonomous":
                from tools.autonomous_agent import AutonomousAgent
                engine = AutonomousAgent(
                    tom_agent=self._agent,
                    llm=getattr(self._agent, "llm", None),
                )
        except Exception as exc:  # missing optional dependency etc.
            self._engines[key] = None
            self._last_load_error = f"{key}: {exc}"
            return None
        self._engines[key] = engine
        return engine

    # ── Detection ────────────────────────────────────────────────────────
    def detect(self, command_lower: str) -> Optional[str]:
        """Return an engine key if this command clearly targets an engine.

        Conservative on purpose: anything ambiguous returns None so the
        agent's existing routing behaves exactly as before.
        """
        c = command_lower.strip()

        # Expert prefixes (same vocabulary the GUI dialogs used)
        for prefix, key in (
            ("ml ", "ml"), ("iot ", "iot"), ("vlsi ", "vlsi"),
            ("hardware ", "hardware"), ("hardware:", "hardware"),
            ("blender ", "blender"), ("game dev ", "gamedev"),
            ("gamedev ", "gamedev"), ("news ", "news"), ("env ", "deps"),
            ("auto-update ", "autoupdate"), ("auto update ", "autoupdate"),
        ):
            if c.startswith(prefix):
                return key

        # Natural language — require strong, unambiguous signals.
        # Schedule is checked FIRST: "schedule X every N hours" wraps any other
        # capability (the wrapped task re-routes normally when the job fires).
        if ("schedule" in c and "every" in c) or c.startswith(("unschedule", "list scheduled")):
            return "schedule"
        if re.search(r"\b(autonomous(ly)?\s+(task|execute|run|do)|execute autonomous)\b", c):
            return "autonomous"
        if re.search(r"\b(multi[- ]agent|deploy (the )?agents?\b.*task|orchestrat)", c):
            return "orchestrator"
        if re.search(r"\b(verilog|vhdl|systemverilog|rtl design|testbench|fpga|freertos|soc design)\b", c):
            return "vlsi"
        if re.search(r"\b(esp32|esp8266|micropython|arduino|raspberry pi pico)\b", c) and \
           re.search(r"\b(code|firmware|sketch|generate|sensor|mqtt|pinout)\b", c):
            return "iot"
        if re.search(r"\b(regression|classif\w+|cluster\w*|auto[_ ]?ml|anomal\w+|time[- ]series)\b", c) and \
           re.search(r"\b(model|train|ml|data|dataset|algorithm|forecast|kmeans|knn|svm|x=|y=)", c):
            return "ml"
        if re.search(r"\b(move (the )?mouse|click at \d|press (the )?key|type text|take a screenshot|"
                     r"volume (up|down|to \d+)|mute|unmute|system info|screen ?shot)\b", c):
            return "hardware"
        if "blender" in c:
            return "blender"
        if re.search(r"\b(scaffold|make|create|build)\b.*\b(pygame|unity|godot)\b", c) or \
           re.search(r"\b(pygame|unity|godot)\b.*\b(game|script)\b", c):
            return "gamedev"
        if re.search(r"\b(daily briefing|news briefing|tech(nology)? roundup|world events|"
                     r"trending topics|latest news)\b", c):
            return "news"
        if re.search(r"\b(create|make)\b.*\bvenv\b", c) or \
           re.search(r"\b(check (dependency |package )?conflicts|migrate (to )?(python ?)?3\.11)\b", c):
            return "deps"
        if re.search(r"\bupdate (tom|yourself|the system)\b", c) or c.startswith("auto-update"):
            return "autoupdate"
        if re.search(r"\b(analy[sz]e|detect)\b.*\bemotion\w*\b", c) or "emotional state" in c:
            return "voiceplus"
        if re.search(r"\bwebsite safety\b|\bis (this|that) (web)?site safe\b", c):
            return "websafety"
        if re.search(r"\b(verify|check)\b.*\b(localhost|web ?app|webapp)\b", c) or \
           c.startswith("verify website"):
            return "webauto"
        if re.search(r"\borganize\b.*\b(folder|downloads|desktop|documents|files|photos|pictures)\b", c) or \
           re.search(r"\bfind (all |every )?[\w*.]*\s*(files|pdfs|images|photos|documents)\b", c) or \
           re.search(r"\b(bulk rename|rename all)\b", c) or \
           re.search(r"\b(zip|compress)\b.*\b(folder|directory|downloads|documents)\b", c) or \
           re.search(r"\bconvert\b.*\b(images?|photos?|pngs?|jpe?gs?)\b", c):
            return "fileops"
        if (re.search(r"\bscrape\b.*\btables?\b", c) or
                re.search(r"\bdownload\b.*https?://", c) or
                re.search(r"\bextract\b.*\btables?\b.*\bfrom\b", c)):
            return "webrecipes"
        if re.search(r"\b(run|execute)\b[^.]*\.js\b", c) or \
           c.startswith(("run shell:", "run command:", "shell:")):
            return "coderun"
        if re.search(r"\b(run|execute)\b[^.]*\.py\b", c) or \
           re.search(r"^run (the )?(code|script)\b", c) or c.startswith("run code"):
            return "coderun"
        return None

    # ── Dispatch ─────────────────────────────────────────────────────────
    async def execute(self, command: str, key: Optional[str] = None) -> Dict[str, Any]:
        c = command.strip()
        key = key or self.detect(c.lower())
        if not key:
            return {"status": "unhandled", "message": ""}
        try:
            if key == "orchestrator":
                return await self._run_orchestrator(c)
            if key == "autonomous":
                return await self._run_autonomous(c)
            if key == "webauto":
                return await self._run_webauto(c)
            if key == "coderun":
                return await self._run_coderun(c)
            if key == "fileops":
                return await self._run_fileops(c)
            if key == "schedule":
                return self._run_schedule(c)
            handler = getattr(self, f"_run_{key}")
            return handler(c)
        except Exception as exc:
            return {"status": "error", "response_type": f"engine_{key}",
                    "message": f"[{key.upper()} engine] failed: {exc}"}

    @staticmethod
    def _unavailable(name: str, hint: str, engine_key: str = "") -> Dict[str, Any]:
        # Enrich with preflight: tell the user EXACTLY what to install.
        try:
            if engine_key:
                from tools.preflight import fix_hint
                precise = fix_hint(engine_key)
                if precise:
                    hint = precise
        except Exception:
            pass
        return {"status": "error", "response_type": "engine_unavailable",
                "message": f"The {name} engine could not be loaded on this machine. {hint}"}

    @staticmethod
    def _ok(rtype: str, message: str, **extra) -> Dict[str, Any]:
        out = {"status": "success", "response_type": rtype, "message": message}
        out.update(extra)
        return out

    # ── ML ───────────────────────────────────────────────────────────────
    def _run_ml(self, command: str) -> Dict[str, Any]:
        eng = self._get("ml")
        if not eng:
            return self._unavailable("ML", "Check that numpy is installed.", "ml")
        c = command.lower()
        X = _extract_kv_list(command, "x") or _extract_kv_list(command, "X")
        y = _extract_kv_list(command, "y")

        algo_match = re.search(
            r"\b(linear|ridge|lasso|logistic|knn|svm|tree|forest|random_forest|"
            r"kmeans|dbscan|arima|holt|naive_bayes|gradient|adaboost)\b", c)
        algo = algo_match.group(1) if algo_match else None

        if "auto" in c and "ml" in c:
            dX, dy = X or self._DEMO_XY[0], y or self._DEMO_XY[1]
            res = eng.auto_ml(dX, dy)
        elif re.search(r"\bcluster", c):
            res = eng.cluster(algo or "kmeans", X or self._DEMO_CLUSTER)
        elif re.search(r"\bclassif", c):
            dX, dy = (X or self._DEMO_CLS[0]), (y or self._DEMO_CLS[1])
            res = eng.classify(algo or "knn", dX, dy)
        elif re.search(r"\banomal", c):
            res = eng.detect_anomalies(algo or "isolation_forest", X or self._DEMO_ANOM)
        elif re.search(r"time[- ]series|forecast|arima|holt", c):
            series = _extract_kv_list(command, "data") or self._DEMO_SERIES
            res = eng.time_series(algo or "arima", series)
        else:  # regression default
            dX, dy = (X or self._DEMO_XY[0]), (y or self._DEMO_XY[1])
            res = eng.regression(algo or "linear", dX, dy)

        note = "" if (X and y) or (X and "cluster" in c) else \
            "\n(Demo data used — supply X=[[...]] y=[...] or a CSV for real runs.)"
        return self._ok("engine_ml", f"ML result:\n{str(res)[:1800]}{note}", raw=res)

    # ── IoT ──────────────────────────────────────────────────────────────
    def _run_iot(self, command: str) -> Dict[str, Any]:
        eng = self._get("iot")
        if not eng:
            return self._unavailable("IoT", "")
        c = command.lower()
        board_m = re.search(r"\b(esp32|esp8266|arduino(?: uno| nano)?|pico|raspberry pi pico)\b", c)
        board = (board_m.group(1).replace("raspberry pi ", "") if board_m else "esp32").replace(" ", "_")
        comps = re.findall(r"\b(dht11|dht22|bme280|bmp180|ds18b20|pir|hc-sr04|relay|servo|led|oled|lcd)\b", c)
        proto_m = re.search(r"\b(mqtt|http|websocket|coap|ble)\b", c)

        if "micropython" in c:
            res = eng.generate_micropython(board, comps or ["dht11"])
        elif "pinout" in c:
            res = eng.generate_pinout(comps or ["dht11"], board)
        elif proto_m and ("protocol" in c or "broker" in c or not comps):
            res = eng.generate_protocol_code(proto_m.group(1), "client")
        else:
            res = eng.generate_esp_code(board, comps or ["dht11"],
                                        protocol=proto_m.group(1) if proto_m else "mqtt")
        return self._ok("engine_iot", f"IoT code generated:\n{str(res)[:1800]}", raw=res)

    # ── VLSI ─────────────────────────────────────────────────────────────
    def _run_vlsi(self, command: str) -> Dict[str, Any]:
        eng = self._get("vlsi")
        if not eng:
            return self._unavailable("VLSI", "")
        c = command.lower()
        width = _extract_kv_num(command, "width", 8)

        if "testbench" in c or re.search(r"\btb\b", c):
            lang_m = re.search(r"\b(verilog|vhdl|systemverilog)\b", c)
            mod_m = re.search(r"\b(counter|adder|alu|fifo|uart|fsm|mux|register)\b", c)
            res = eng.generate_testbench(lang_m.group(1) if lang_m else "verilog",
                                         mod_m.group(1) if mod_m else "counter")
        elif "fpga" in c:
            vend_m = re.search(r"\b(xilinx|intel|lattice|altera)\b", c)
            res = eng.generate_fpga_flow(vend_m.group(1) if vend_m else "xilinx", "top")
        elif re.search(r"\b(freertos|zephyr|rtthread|rtos)\b", c):
            rtos_m = re.search(r"\b(freertos|zephyr|rtthread)\b", c)
            n = _extract_kv_num(command, "tasks", 2)
            res = eng.generate_rtos(rtos_m.group(1) if rtos_m else "freertos",
                                    [f"task{i}" for i in range(n)])
        elif "embedded" in c or re.search(r"\b(stm32|avr|pic32)\b", c):
            tgt_m = re.search(r"\b(stm32|avr|pic32|esp32)\b", c)
            peri_m = re.search(r"\b(gpio|uart|spi|i2c|adc|pwm|timer)\b", c)
            res = eng.generate_embedded_c(tgt_m.group(1) if tgt_m else "stm32",
                                          peri_m.group(1) if peri_m else "gpio")
        elif "soc" in c:
            res = eng.generate_soc("riscv", ["uart", "gpio"], width=max(width, 32))
        elif "rtl" in c:
            dt_m = re.search(r"\b(adder|counter|alu|fifo|multiplier|fsm)\b", c)
            res = eng.generate_rtl(dt_m.group(1) if dt_m else "adder", width=width)
        else:
            lang_m = re.search(r"\b(verilog|vhdl|systemverilog)\b", c)
            mod_m = re.search(r"\b(counter|adder|alu|fifo|uart|fsm|mux|register|shift)\b", c)
            res = eng.generate_hdl(lang_m.group(1) if lang_m else "verilog",
                                   mod_m.group(1) if mod_m else "counter", width=width)
        body = res.get("result", str(res)) if isinstance(res, dict) else str(res)
        return self._ok("engine_vlsi", f"VLSI output:\n{body[:1800]}", raw=res)

    # ── Hardware ─────────────────────────────────────────────────────────
    def _run_hardware(self, command: str) -> Dict[str, Any]:
        eng = self._get("hardware")
        if not eng or not getattr(eng, "is_available", lambda: True)():
            return self._unavailable("Hardware control", "pyautogui must be installed.", "hardware")
        c = command.lower()
        m = re.search(r"move (?:the )?mouse (?:to )?(\d+)[ ,]+(\d+)", c)
        if m:
            r = eng.move_mouse(int(m.group(1)), int(m.group(2)))
        elif re.search(r"click at (\d+)[ ,]+(\d+)", c):
            mm = re.search(r"click at (\d+)[ ,]+(\d+)", c)
            r = eng.click(int(mm.group(1)), int(mm.group(2)))
        elif "double click" in c:
            r = eng.double_click()
        elif "right click" in c:
            r = eng.right_click()
        elif "click" in c:
            r = eng.click()
        elif re.search(r"\btype text\b", c):
            text = command[command.lower().find("type text") + 9:].strip(" :\"'")
            r = eng.type_text(text)
        elif re.search(r"press (?:the )?key", c):
            keym = re.search(r"press (?:the )?key\s+(\w+)", c)
            r = eng.press_key(keym.group(1)) if keym else {"status": "error", "message": "Which key?"}
        elif "screenshot" in c or "screen shot" in c:
            r = eng.screenshot()
        elif "volume up" in c:
            r = eng.volume_up()
        elif "volume down" in c:
            r = eng.volume_down()
        elif re.search(r"volume to (\d+)", c):
            vm = re.search(r"volume to (\d+)", c)
            r = eng.set_volume(int(vm.group(1)))
        elif "unmute" in c:
            r = eng.unmute_audio()
        elif "mute" in c:
            r = eng.mute_audio()
        elif "system info" in c:
            r = eng.get_system_info()
        else:
            return self._ok("engine_hardware",
                            "Hardware commands: move mouse to X Y · click [at X Y] · double/right click · "
                            "type text <...> · press key <k> · screenshot · volume up/down/to N · "
                            "mute/unmute · system info")
        return self._ok("engine_hardware", f"Hardware: {str(r)[:600]}", raw=r)

    # ── Game Dev ─────────────────────────────────────────────────────────
    def _run_gamedev(self, command: str) -> Dict[str, Any]:
        eng = self._get("gamedev")
        if not eng:
            return self._unavailable("Game Dev", "")
        c = command.lower()
        if "unity" in c or "godot" in c:
            engine_name = "unity" if "unity" in c else "godot"
            res = eng.generate_script(engine_name, command)
        else:
            name_m = re.search(r"(?:called|named)\s+([a-zA-Z0-9_]+)", c)
            genre_m = re.search(r"\b(platformer|shooter|puzzle|runner|rpg)\b", c)
            res = eng.scaffold_pygame(name_m.group(1) if name_m else "my_game",
                                      genre_m.group(1) if genre_m else "platformer")
        return self._ok("engine_gamedev", f"Game dev:\n{str(res)[:1500]}", raw=res)

    # ── Blender ──────────────────────────────────────────────────────────
    def _run_blender(self, command: str) -> Dict[str, Any]:
        eng = self._get("blender")
        if not eng:
            return self._unavailable("Blender", "", "blender")
        if not eng.is_available():
            return self._ok("engine_blender",
                            "Blender is not installed (or not found). Install Blender and retry.")
        task = re.sub(r"^blender\s*", "", command, flags=re.I).strip() or "cube"
        res = eng.generate_and_execute(task)
        return self._ok("engine_blender", f"Blender:\n{str(res)[:1200]}", raw=res)

    # ── News ─────────────────────────────────────────────────────────────
    def _run_news(self, command: str) -> Dict[str, Any]:
        eng = self._get("news")
        if not eng:
            return self._unavailable("News", "", "news")
        c = command.lower()
        if "tech" in c:
            res = eng.technology_roundup()
        elif "world" in c:
            res = eng.world_events()
        elif "trending" in c:
            res = eng.get_trending_topics()
        elif "search" in c:
            q = re.sub(r".*search( news)?( for)?", "", c).strip() or "technology"
            res = eng.search_news(q)
        else:
            res = eng.daily_briefing()
        msg = res.get("briefing") or res.get("summary") or res.get("message") or str(res)
        return self._ok("engine_news", str(msg)[:2000], raw=res)

    # ── Dependencies / Env ───────────────────────────────────────────────
    def _run_deps(self, command: str) -> Dict[str, Any]:
        eng = self._get("deps")
        if not eng:
            return self._unavailable("Dependency manager", "")
        c = command.lower()
        if "venv" in c:
            r = eng.create_venv(".")
        elif "conflict" in c:
            r = eng.check_conflicts()
        elif "migrate" in c:
            r = eng.migrate_to_python311()
        elif "analyze" in c or "analyse" in c:
            r = eng.analyze_project(".")
        elif re.search(r"\binstall\s+([a-zA-Z0-9_\-\[\]]+)", c):
            pkg = re.search(r"\binstall\s+([a-zA-Z0-9_\-\[\]]+)", c).group(1)
            r = eng.install_package(pkg)
        else:
            r = eng.list_installed()
        return self._ok("engine_deps", f"Env/Deps: {str(r)[:1500]}", raw=r)

    # ── Auto-update ──────────────────────────────────────────────────────
    def _run_autoupdate(self, command: str) -> Dict[str, Any]:
        eng = self._get("autoupdate")
        if not eng:
            return self._unavailable("Auto-update", "")
        c = command.lower()
        if "check" in c:
            r = eng.check_git_updates()
        elif "pull" in c:
            r = eng.pull_updates()
        elif "pip" in c or "packages" in c:
            r = eng.update_pip_packages()
        elif "history" in c:
            r = eng.get_update_history()
        else:
            r = eng.check_git_updates()  # safest default — never auto full_update
        return self._ok("engine_autoupdate", f"Auto-update: {str(r)[:1200]}", raw=r)

    # ── Voice+ (text emotion only — audio needs the GUI/voice mode) ─────
    def _run_voiceplus(self, command: str) -> Dict[str, Any]:
        eng = self._get("voiceplus")
        if not eng:
            return self._unavailable("Voice+", "", "voiceplus")
        m = re.search(r"(?:text\s*:\s*)(.+)$", command, flags=re.I | re.S)
        text = m.group(1).strip() if m else command
        r = eng.analyze_emotional_state(text)
        return self._ok("engine_voiceplus", f"Emotion analysis: {str(r)[:1200]}", raw=r)

    # ── Autonomous (async) ───────────────────────────────────────────────
    async def _run_autonomous(self, command: str) -> Dict[str, Any]:
        eng = self._get("autonomous")
        if not eng:
            return self._unavailable("Autonomous agent", "")
        task = re.sub(r"^(execute\s+)?autonomous(ly)?\s*(task)?\s*:?\s*", "", command, flags=re.I).strip()
        res = await eng.execute(task or command)
        msg = res.get("message") or res.get("summary") or str(res)
        return self._ok("engine_autonomous", str(msg)[:2000], raw=res)

    # ── Multi-agent orchestrator (lives on the agent) ────────────────────
    async def _run_orchestrator(self, command: str) -> Dict[str, Any]:
        orch = getattr(self._agent, "orchestrator", None)
        if not orch:
            return self._unavailable("Multi-agent orchestrator", "")
        task = re.sub(r"^deploy multi[- ]agent task\s*:?\s*", "", command, flags=re.I).strip()
        res = await orch.execute_task(task or command)
        msg = res.get("message") or res.get("result") or str(res)
        return self._ok("engine_orchestrator", str(msg)[:2000], raw=res)

    # ── Web automation: verify a URL / localhost app ─────────────────────
    async def _run_webauto(self, command: str) -> Dict[str, Any]:
        wa = getattr(self._agent, "web_automation", None)
        if not wa:
            return self._unavailable("Web automation", "Playwright must be installed.", "webauto")
        m = re.search(r"(https?://\S+|localhost:?\d*|\b\d{2,5}\b)", command, re.I)
        if not m:
            return self._ok("engine_webauto",
                            "Give me a URL or localhost port, e.g. 'verify web app on localhost:3000'.")
        target = m.group(1).rstrip(".,:;")
        if target.isdigit():
            target = f"http://localhost:{target}"
        elif not target.startswith("http"):
            target = "http://" + target
        res = await wa.wait_and_verify(target)
        return self._ok("engine_webauto", f"Web verification ({target}): {str(res)[:1200]}", raw=res)

    # ── Website safety analysis (SafetyGuards) ───────────────────────────
    def _run_websafety(self, command: str) -> Dict[str, Any]:
        safety = getattr(self._agent, "safety", None)
        if not safety or not hasattr(safety, "analyze_website"):
            return self._unavailable("Website safety analyzer", "")
        m = re.search(r"(https?://\S+|www\.\S+|[a-z0-9-]+(?:\.[a-z0-9-]+)+\S*)", command, re.I)
        if not m:
            return self._ok("engine_websafety",
                            "Give me a URL to check, e.g. 'check website safety: example.com'.")
        res = safety.analyze_website(m.group(1).rstrip(".,:;"))
        return self._ok("engine_websafety", f"Website safety: {str(res)[:1200]}", raw=res)

    # ── Code runner (subprocess + timeout, ALWAYS behind approval) ───────
    async def _run_coderun(self, command: str) -> Dict[str, Any]:
        eng = self._get("coderun")
        if not eng:
            return self._unavailable("Code runner", "")
        shell_m = re.match(r"^(?:run shell:|run command:|shell:)\s*(.+)$", command.strip(), re.I)
        js_m = re.search(r"([\w\-./\\:]+\.js)\b", command)
        m = re.search(r"([\w\-./\\:]+\.py)\b", command)
        if not (shell_m or js_m or m):
            return self._ok("engine_coderun",
                            "Tell me what to run: a .py/.js file, or 'run shell: <command>'.")
        path = (js_m or m).group(1) if (js_m or m) else ""
        run_kind = "shell" if shell_m else ("node" if js_m else "python")
        agent = self._agent
        if agent is None or not getattr(agent, "approval_manager", None):
            return {"status": "error", "response_type": "engine_coderun",
                    "message": "Code execution requires the approval system (agent context)."}
        import asyncio as _aio
        from tools.approval import ApprovalRequest
        approved = await _aio.to_thread(
            agent.approval_manager.request_approval,
            ApprovalRequest(action="run_code", summary=f"Run {run_kind}: {shell_m.group(1) if shell_m else path}",
                            details={"path": path}, risk_level="high"))
        if not approved:
            return {"status": "cancelled", "response_type": "engine_coderun",
                    "message": "Code run cancelled by user."}
        if run_kind == "shell":
            res = eng.run_shell(shell_m.group(1))
            label = "shell"
        elif run_kind == "node":
            res = eng.run_node_file(path)
            label = path
        else:
            res = eng.run_python_file(path)
            label = path
        return self._ok("engine_coderun",
                        f"Code run ({label}):\n{res.get('message', '')[:1500]}", raw=res)

    # ── File operations (Phase B2) — destructive steps approval-gated ────
    async def _run_fileops(self, command: str) -> Dict[str, Any]:
        from tools.file_ops import FileOps, resolve_folder
        ops = FileOps()
        c = command.lower()

        folder_m = re.search(
            r"(?:\bin|\bfrom|\bof)?\s*(my\s+)?(downloads|documents|desktop|pictures|photos|music|videos|[a-z]:\\[^\s\"]+|/[^\s\"]+)",
            c)
        folder = folder_m.group(2) if folder_m else "downloads"

        if re.search(r"\bfind\b", c):
            ext_m = re.search(r"\b(pdfs?|images?|photos?|docs?|documents|videos?|\*?\.[a-z0-9]{2,4})\b", c)
            token = ext_m.group(1) if ext_m else "*"
            pattern = {"pdf": "*.pdf", "pdfs": "*.pdf", "image": "*.jpg", "images": "*.*",
                       "photo": "*.jpg", "photos": "*.*", "doc": "*.doc*", "docs": "*.doc*",
                       "documents": "*.*", "video": "*.mp4", "videos": "*.*"}.get(token, token if "." in token else "*")
            return self._ok("engine_fileops", ops.find_files(folder, pattern)["message"])

        if re.search(r"\bzip|compress\b", c):
            return self._ok("engine_fileops", ops.zip_folder(folder)["message"])

        if re.search(r"\bconvert\b", c):
            to_m = re.search(r"\bto\s+\.?([a-z]{3,4})\b", c)
            return self._ok("engine_fileops",
                            ops.convert_images(folder, to_m.group(1) if to_m else "png")["message"])

        # organize / bulk rename → PLAN then APPROVAL then EXECUTE
        if re.search(r"\b(bulk rename|rename all)\b", c):
            pat_m = re.search(r"['\"]([^'\"]+)['\"]\s*(?:to|->|→)\s*['\"]([^'\"]*)['\"]", command)
            if not pat_m:
                return self._ok("engine_fileops",
                                "Tell me the pattern, e.g.: bulk rename in downloads 'IMG_' to 'Holiday_'")
            plan = ops.plan_bulk_rename(folder, pat_m.group(1), pat_m.group(2))
        elif "year" in c:
            plan = ops.plan_organize_by_year(folder)
        else:
            plan = ops.plan_organize_by_type(folder)

        if plan.get("status") != "plan":
            return self._ok("engine_fileops", plan.get("message", "Could not build a plan."))
        if not plan["moves"]:
            return self._ok("engine_fileops", "Nothing to do — " + plan["message"])

        agent = self._agent
        if agent is None or not getattr(agent, "approval_manager", None):
            return self._ok("engine_fileops", "[DRY RUN — approval system unavailable]\n" + plan["message"])
        import asyncio as _aio
        from tools.approval import ApprovalRequest
        approved = await _aio.to_thread(
            agent.approval_manager.request_approval,
            ApprovalRequest(action="file_ops", summary=plan["message"],
                            details={"count": len(plan["moves"])}, risk_level="medium"))
        if not approved:
            return {"status": "cancelled", "response_type": "engine_fileops",
                    "message": "File operation cancelled. (Plan was: " + plan["message"][:200] + ")"}
        res = ops.execute_plan(plan)
        return self._ok("engine_fileops", res["message"])

    # ── Web recipes (Phase B3) ────────────────────────────────────────────
    def _run_webrecipes(self, command: str) -> Dict[str, Any]:
        from tools import web_recipes as wr
        url_m = re.search(r"https?://\S+", command)
        if not url_m:
            return self._ok("engine_webrecipes",
                            "Give me a URL, e.g. 'scrape the tables from https://example.com/page'.")
        url = url_m.group(0).rstrip(".,);")
        if re.search(r"\bdownload\b", command.lower()):
            return self._ok("engine_webrecipes", wr.download_file(url)["message"])
        return self._ok("engine_webrecipes", wr.scrape_tables(url)["message"])

    # ── Scheduling (Phase B4) ─────────────────────────────────────────────
    def _run_schedule(self, command: str) -> Dict[str, Any]:
        agent = self._agent
        if agent is None:
            return self._unavailable("Scheduler", "agent context required")
        low = command.lower().strip()
        if low.startswith("list scheduled"):
            return agent.list_user_tasks()
        if low.startswith("unschedule"):
            ref = command.split(None, 1)[1].strip() if " " in command else ""
            return agent.unschedule_user_task(ref) if ref else self._ok(
                "schedule", "Which job? Say 'list scheduled tasks' to see names.")
        task, hours = parse_schedule_command(command)
        if not task or not hours:
            return self._ok("schedule",
                            "Tell me what and how often, e.g. "
                            "'schedule: give me the daily briefing every 24 hours'.")
        return agent.schedule_user_task(task, hours)
