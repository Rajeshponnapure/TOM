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
import os
import re
from typing import Any, Dict, List, Optional

from tools.text_utils import without_addresses


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


def _probe_https(domain: str, timeout: float = 6.0) -> str:
    """One HTTPS request with certificate verification: a short description of what happened, "" if no domain."""
    if not domain or not re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", domain.lower()):
        return ""
    try:
        import requests
        r = requests.get(f"https://{domain}", timeout=timeout, allow_redirects=True, stream=True,
                         headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        final = r.url
        r.close()
        return f"valid HTTPS certificate; responded HTTP {r.status_code}" + (
            f" (redirects to {final})" if final.rstrip("/") != f"https://{domain}" else "")
    except Exception as exc:
        name = type(exc).__name__
        if "SSL" in name or "SSL" in str(exc)[:200]:
            return f"certificate problem — the HTTPS certificate could not be verified ({name})"
        return f"site did not answer over HTTPS ({name})"


def _ml_predictions(command: str, res: Any, X: Optional[Any]) -> str:
    """"... and predict for 5" — use the model that was just trained (live check 2026-10-27: the request
    was ignored). Also states the fitted equation for a one-feature linear model."""
    model = res.get("result") if isinstance(res, dict) else None
    if model is None or not hasattr(model, "predict"):
        return ""
    out = ""
    coef, icpt = getattr(model, "coef_", None), getattr(model, "intercept_", None)
    try:
        import numpy as np
        if coef is not None and icpt is not None and np.ndim(coef) == 1 and len(coef) == 1 \
                and not hasattr(model, "poly_features_"):
            out += f"\nFitted line: y = {float(coef[0]):.4g}·x + {float(icpt):.4g}"
    except Exception:
        pass
    m = re.search(r"\bpredict(?:ion)?s?\b(?:\s+(?:the\s+)?(?:value\s+)?(?:for|at|of|when\s+x\s*(?:is|=)|x\s*=))?\s*"
                  r"(\[\[.*?\]\]|\[[^\]]*\]|-?\d+(?:\.\d+)?(?:\s*(?:,|and)\s*-?\d+(?:\.\d+)?)*)", command, re.I)
    if not m:
        return out
    raw = m.group(1)
    n_features = len(X[0]) if X and isinstance(X[0], (list, tuple)) else 1
    if raw.startswith("[["):
        rows = _safe_literal(raw)
    else:
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", raw)]
        rows = [[v] for v in nums] if n_features == 1 else [nums[:n_features]]
    try:
        feats = getattr(model, "poly_features_", None)
        preds = model.predict(feats.transform(rows) if feats is not None else rows)
        lines = [f"  x = {r[0] if len(r) == 1 else r} → {float(p):.4g}" for r, p in zip(rows, preds)]
        return out + "\nPredictions:\n" + "\n".join(lines)
    except Exception as exc:
        return out + f"\n(Could not predict for {raw}: {exc})"


def _extract_kv_num(command: str, key: str, default: int) -> int:
    m = re.search(rf"\b{key}\s*=\s*(\d+)", command)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return default
    return default


def _extract_quoted(command: str) -> Optional[str]:
    """Pull 'this exact text' / "this exact text" out of a command."""
    m = re.search(r"['\"]([^'\"]+)['\"]", command)
    return m.group(1) if m else None


_HIDDEN_KEYS = frozenset({"status", "raw", "success"})


def _fmt_scalar(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def humanize(value: Any, limit: int = 2400) -> str:
    """An engine's result (nested dicts/lists) as readable lines instead of a Python repr.

    Owner report 2026-10-21: answers like "Hardware: {'status': 'success', 'info': {...}}".
    Code and other multi-line text are kept verbatim.
    """
    lines: List[str] = []

    def label(key: str) -> str:
        return key.replace("_", " ").strip().capitalize()

    def walk(v: Any, indent: int, key: Optional[str]) -> None:
        pad = "  " * indent
        head = f"{label(key)}: " if key else ""
        if isinstance(v, dict):
            items = [(k, x) for k, x in v.items() if str(k) not in _HIDDEN_KEYS]
            if key:
                lines.append(f"{pad}{label(key)}:")
            for k, x in items:
                walk(x, indent + (1 if key else 0), str(k))
        elif isinstance(v, (list, tuple)):
            if not v:
                lines.append(f"{pad}{head}none")
            elif all(not isinstance(x, (dict, list, tuple)) for x in v):
                shown = ", ".join(_fmt_scalar(x) for x in v[:12])
                lines.append(f"{pad}{head}{shown}" + (f" … (+{len(v) - 12} more)" if len(v) > 12 else ""))
            else:
                if key:
                    lines.append(f"{pad}{label(key)}:")
                for x in v[:10]:
                    walk(x, indent + 1, None)
                    lines.append("")
                if len(v) > 10:
                    lines.append(f"{pad}  … {len(v) - 10} more")
        else:
            text = _fmt_scalar(v)
            if "\n" in text:
                lines.append(f"{pad}{head}\n{text}")
            else:
                lines.append(f"{pad}{head}{text}")

    walk(value, 0, None)
    out = "\n".join(line for i, line in enumerate(lines) if line or (i and lines[i - 1])).strip()
    return out if len(out) <= limit else out[:limit] + " …"


_VIDEO_EXT = r"[\w:\\/.\-]+\.(?:mp4|mov|avi|mkv|webm|flv|wmv)"
_PHOTO_EXT = r"[\w:\\/.\-]+\.(?:png|jpe?g|gif|bmp|webp|tiff?)"


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
            elif key == "scaler":
                from tools.auto_scaler import AutoScaler
                engine = AutoScaler()
            elif key == "media":
                from tools.media_engine import MediaEngine
                engine = MediaEngine()
            elif key == "network":
                from tools.network_tools import NetworkTools
                engine = NetworkTools()
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
        c = without_addresses(command_lower).strip()

        # Expert prefixes (same vocabulary the GUI dialogs used)
        for prefix, key in (
            ("ml ", "ml"), ("iot ", "iot"), ("vlsi ", "vlsi"),
            ("hardware ", "hardware"), ("hardware:", "hardware"),
            ("blender ", "blender"), ("game dev ", "gamedev"),
            ("gamedev ", "gamedev"), ("news ", "news"), ("env ", "deps"),
            ("auto-update ", "autoupdate"), ("auto update ", "autoupdate"),
            ("scaler ", "scaler"), ("autoscale ", "scaler"), ("auto-scale ", "scaler"),
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
        if re.search(r"\bfix\b.*\b(failing|broken)?\s*tests?\b.*\b(in|at|for)\s+\S", c):
            return "fixtests"
        if re.search(r"\b(multi[- ]agent|deploy (the )?agents?\b.*task|orchestrat)", c):
            return "orchestrator"
        if re.search(r"\b(verilog|vhdl|systemverilog|rtl design|testbench|fpga|freertos|soc design)\b", c):
            return "vlsi"
        if re.search(r"\b(esp32|esp8266|micropython|arduino|raspberry pi pico)\b", c) and \
           re.search(r"\b(code|firmware|sketch|generate|sensor|mqtt|pinout)\b", c):
            return "iot"
        # Live hardware over USB: "detect my iot devices", "scan i2c on COM5", "flash X to my esp32",
        # "read serial from the board", "what's connected to my microcontroller".
        if re.search(r"\b(detect|list|find|show|what(?:'s| is| are))\b.*\b(iot|microcontroller|serial|usb)\b.*\b(devices?|boards?|ports?|connected)\b", c) or \
           re.search(r"\b(connected|plugged in)\b.*\b(boards?|microcontrollers?)\b|\b(list|show|detect)\b.*\bconnected\b.*\bboards?\b", c) or \
           re.search(r"\bi2c\b.*\b(scan|wired|connected|devices?)\b|\bscan\b.*\bi2c\b", c) or \
           re.search(r"\b(flash|upload|burn|program)\b.*\b(esp32|esp8266|arduino|pico|board|com\d|microcontroller)\b", c) or \
           re.search(r"\bserial (monitor|port|console|output)\b", c) or \
           (re.search(r"\b(read|monitor)\b.*\bserial\b", c) and
            re.search(r"\b(board|device|port|baud|com\d|esp32|esp8266|arduino|pico|microcontroller)\b", c)) or \
           re.search(r"\bwhat(?:'s| is)\b.*\b(connected|wired|plugged)\b.*\b(board|microcontroller|esp32|arduino|pico)\b", c):
            return "iot"
        if (re.search(r"\b(trim|cut|clip|concat(enate)?|combine|merge|join|caption|subtitle|"
                      r"text overlay|extract audio|resize|scale|mute|convert|color correct)\b", c) and
                (re.search(r"\bvideos?\b", c) or re.search(_VIDEO_EXT, c, re.I))) or \
           (re.search(r"\b(crop|resize|scale|rotate|watermark|grayscale|black and white|blur|sharpen|"
                      r"smooth|contour|brighten|darken|high contrast|saturate|sepia|filter|convert)\b", c) and
                re.search(r"\b(photo|image|picture)s?\b", c)) or \
           re.search(r"\bedit (the |this |my )?(video|photo|image|picture)\b", c):
            return "media"
        if re.search(r"\b(predictive analysis|prediction|predict|forecast|regression|classif\w+|cluster\w*|auto[_ ]?ml|anomal\w+|time[- ]series)\b", c) and \
           re.search(r"\b(model|train|ml|data|dataset|algorithm|analysis|forecast|kmeans|knn|svm|x=|y=)", c):
            return "ml"
        if re.search(r"\b(move (the )?mouse|click at \d|press (the )?key|type text|take a screenshot|"
                     r"volume (up|down|to \d+)|mute|unmute|system info|screen ?shot)\b", c):
            return "hardware"
        if re.search(r"\b(auto[- ]?scaler|resource manager|worker pool)\b.*\bstatus\b", c) or \
           re.search(r"\b(scaler|autoscaler) (status|performance report)\b", c) or \
           re.search(r"\b(simulate load|benchmark parallel|stress test (the )?(scaler|workers?))\b", c) or \
           re.search(r"\b(optimal|optimize)\b.*\bworkers?\b", c) or \
           re.search(r"\bsystem resources?\b", c) or \
           re.search(r"\bhow many cpu cores\b", c):
            return "scaler"
        if "blender" in c:
            return "blender"
        if re.search(r"\b(scaffold|make|create|build)\b.*\b(pygame|unity|godot)\b", c) or \
           re.search(r"\b(pygame|unity|godot)\b.*\b(game|script)\b", c):
            return "gamedev"
        if re.search(r"\b(daily briefing|news briefing|tech(nology)? roundup|world events|"
                     r"trending topics|latest news)\b", c):
            return "news"
        if re.search(r"\b(create|make)\b.*\bvenv\b", c) or \
           re.search(r"\b(check (dependency |package )?conflicts|migrate (to )?(python ?)?3\.11)\b", c) or \
           re.search(r"\b(dependency|package|version|pip)\s+conflicts?\b", c) or \
           re.search(r"\b(outdated|installed)\s+(packages|dependencies)\b", c):
            return "deps"
        if re.search(r"\bupdate (tom|yourself|the system)\b", c) or c.startswith("auto-update"):
            return "autoupdate"
        if re.search(r"\b(analy[sz]e|detect)\b.*\bemotion\w*\b", c) or "emotional state" in c:
            return "voiceplus"
        if re.search(r"\bwebsite safety\b|\bis (this|that) (web)?site safe\b", c) or (
                re.search(r"\b(safe|safety|scam|phishing|legit(imate)?|trust(worthy)?|malicious|fraud\w*)\b", c)
                and re.search(r"(https?://\S+|www\.\S+|\b[a-z0-9-]+\.(?:com|in|org|net|io|co|ai|app|dev|info|xyz"
                              r"|biz|me|ly)\b)", command_lower)):       # c has addresses removed
            return "websafety"
        # The URL itself is removed from `c`, so look for it in the original text.
        if re.search(r"\b(verify|check|test|debug|diagnose)\b.*\b(localhost|web ?app|webapp)\b", c) or \
           re.search(r"\b(verify|check|test|debug|diagnose|auto[- ]?debug)\b.*(localhost|127\.0\.0\.1|\bport\s*\d{2,5}\b)",
                     command_lower) or \
           re.search(r"\b(verify|check|test)\b.*https?://\S+.*\b(loads?|works?|is up|is running|responds?)\b",
                     command_lower) or \
           c.startswith("verify website"):
            return "webauto"
        if re.search(r"\b(revert|undo|roll ?back|restore)\b.*\b(downloads|folder|files|changes|what you (?:have )?done)\b", c) or \
           re.search(r"\b(organi[sz]e|tidy(?: up)?|clean ?up|declutter|sort(?: out)?)\b.*\b(folder|downloads|desktop|documents|files|photos|pictures)\b", c) or \
           re.search(r"\bfind (all |every )?[\w*.]*\s*(files|pdfs|images|photos|documents)\b", c) or \
           re.search(r"\b(move|put|relocate|transfer|gather|collect|shift)\b.*\b(pdfs?|images?|photos?|pictures|videos?|songs|"
                     r"spreadsheets?|zips?|archives?|installers?|files)\b.*\b(folder|subfolder|downloads|desktop|"
                     r"documents|pictures|photos|into|to)\b", c) or \
           re.search(r"\b(move|put|relocate|transfer|gather|collect|shift)\b.*\b(docs?|documents|music|audio|slides?|slide decks?|decks?|presentations?)\b"
                     r".*\b(folder|subfolder|downloads|desktop|pictures)\b", c) or \
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
        # Network diagnostics (own LAN / this host) — the legitimate
        # "show devices on my wifi / my network info / scan my ports".
        if re.search(r"\b(devices?|who ?is|what ?is)\b.*\b(on|connected to)\b.*\b(my )?(wi[- ]?fi|network|lan|router)\b", c) or \
           re.search(r"\b(list|show|scan|see)\b.*\b(devices?|machines?|hosts?)\b.*\b(network|wi[- ]?fi|lan)\b", c) or \
           re.search(r"\b(my )?(wi[- ]?fi|wlan)\b.*\b(status|info|profiles?|networks?|signal|connection)\b", c) or \
           re.search(r"\b(what'?s|show|list)\b.*\b(wi[- ]?fi|networks?)\b.*\b(know|saved|remember)", c) or \
           re.search(r"\b(my )?(network|ip)\b.*\b(info|overview|address|details)\b", c) or \
           re.search(r"\bwhat'?s my (ip|local ip|network)\b", c) or \
           re.search(r"\b(scan|check)\b.*\bports?\b", c) or \
           re.search(r"\b(open|listening)\s+ports?\b|\bports?\b.*\b(open|listening)\b", c) or \
           re.search(r"\bnetwork\b.*\b(overview|diagnostics?|scan)\b", c):
            return "network"
        return None

    # ── Dispatch ─────────────────────────────────────────────────────────
    async def execute(self, command: str, key: Optional[str] = None) -> Dict[str, Any]:
        c = command.strip()
        key = key or self.detect(c.lower())
        if not key:
            return {"status": "unhandled", "message": ""}
        try:
            if key == "orchestrator":
                result: Any = await self._run_orchestrator(c)
            elif key == "fixtests":
                result = await self._run_fixtests(c)
            elif key == "autonomous":
                result = await self._run_autonomous(c)
            elif key == "webauto":
                result = await self._run_webauto(c)
            elif key == "coderun":
                result = await self._run_coderun(c)
            elif key == "fileops":
                result = await self._run_fileops(c)
            elif key == "schedule":
                result = self._run_schedule(c)
            else:
                result = getattr(self, f"_run_{key}")(c)
        except Exception as exc:
            return {"status": "error", "response_type": f"engine_{key}",
                    "message": f"[{key.upper()} engine] failed: {exc}"}
        # Every engine result passes the same independent check before TOM is
        # allowed to report it as done.
        return self._apply_verification(key, c, result)

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

    # ── Verification ─────────────────────────────────────────────────────
    # "No task is successful from text alone": after an engine claims success,
    # TOM re-checks the filesystem for what the engine says it produced. Only a
    # failure found here can change an outcome (a success is never invented).
    _ARTIFACT_KEYS = ("path", "paths", "zip", "artifact", "artifacts",
                      "created", "created_paths", "output", "outputs")

    @staticmethod
    def _looks_like_path(value: str) -> bool:
        """True only for strings that are plausibly filesystem paths, not prose."""
        if not value or len(value) > 400:
            return False
        if os.path.exists(value):
            return True
        return "\\" in value or "/" in value

    @classmethod
    def _declared_artifacts(cls, result: Dict[str, Any]) -> List[tuple]:
        """(path, exists) for each file/dir the engine says it produced."""
        out: List[tuple] = []
        for key in cls._ARTIFACT_KEYS:
            value = result.get(key)
            values = value if isinstance(value, (list, tuple, set)) else [value]
            for item in values:
                if not isinstance(item, str) or not cls._looks_like_path(item.strip()):
                    continue
                target = item.strip()
                if not os.path.isabs(target):
                    target = os.path.abspath(target)
                out.append((target, os.path.exists(target)))
        return out

    def verify(self, key: str, command: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Re-check an engine's claim against the real filesystem.

        checked=False means the engine declared nothing that can be re-checked,
        so the result stands exactly as the engine reported it.
        """
        evidence: List[str] = []
        ok = True
        moves = result.get("completed_moves") or []
        for move in moves:
            try:
                source, destination = move
            except (TypeError, ValueError):
                continue
            if os.path.exists(destination):
                evidence.append(f"{os.path.basename(str(destination))} is in place")
            else:
                ok = False
                evidence.append(f"{destination} is missing")
            if os.path.exists(source):
                ok = False
                evidence.append(f"{source} was never moved")
        if moves and ok:
            evidence.append(f"{len(moves)} move(s) confirmed on disk")
        artifacts = self._declared_artifacts(result)
        for path, exists in artifacts:
            evidence.append(f"{path} exists" if exists
                            else f"{path} was not created")
            if not exists:
                ok = False
        if not moves and not artifacts:
            return {"checked": False, "ok": True,
                    "evidence": f"[{key}] no filesystem artifact declared to re-check"}
        return {"checked": True, "ok": ok, "evidence": "; ".join(evidence[:12])}

    def _apply_verification(self, key: str, command: str, result: Any) -> Any:
        """Attach the evidence, and refuse to report an unconfirmed success."""
        if not isinstance(result, dict):
            return result
        if str(result.get("status", "")).lower() != "success":
            return result
        verification = self.verify(key, command, result)
        checked_result = dict(result)
        checked_result["verification"] = verification
        if verification["checked"] and not verification["ok"]:
            checked_result["status"] = "error"
            checked_result["response_type"] = (checked_result.get("response_type")
                                               or f"engine_{key}")
            checked_result["message"] = (
                "I could not confirm that this was actually done, so I am not reporting it as "
                f"complete. {verification['evidence']}\n\n{result.get('message', '')}")
        return checked_result

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
        series = _extract_kv_list(command, "data")

        # No data, no run: a question ("how would I forecast monthly sales?") used to be answered
        # with a model trained on built-in demo numbers (owner report 2026-10-21). Demo runs only
        # when asked for explicitly.
        if not (X or series) and not re.search(r"\b(demo|example|sample)\b", c):
            return {"status": "needs_input", "response_type": "engine_ml",
                    "message": "To train or run a model I need data: give values like X=[[1],[2],[3]] "
                               "y=[2,4,6] (or data=[...] for a forecast), attach a CSV with Data Anal, "
                               "or say 'demo' to see it on sample numbers."}

        # The engine's own names ("linearregression", "decisiontreeregressor", …).
        regression_names = {"linear": "linearregression", "tree": "decisiontreeregressor",
                            "forest": "randomforestregressor", "random_forest": "randomforestregressor",
                            "gradient": "gradientboostingregressor", "adaboost": "adaboostregressor",
                            "svm": "svr"}
        classifier_names = {"logistic": "logisticregression", "svm": "svc", "tree": "decisiontreeclassifier",
                            "forest": "randomforestclassifier", "random_forest": "randomforestclassifier",
                            "gradient": "gradientboostingclassifier", "adaboost": "adaboostclassifier",
                            "naive_bayes": "naivebayes"}

        if "auto" in c and "ml" in c:
            dX, dy = X or self._DEMO_XY[0], y or self._DEMO_XY[1]
            res = eng.auto_ml(dX, dy)
        elif re.search(r"\bcluster", c):
            res = eng.cluster(algo or "kmeans", X or self._DEMO_CLUSTER)
        elif re.search(r"\bclassif", c):
            dX, dy = (X or self._DEMO_CLS[0]), (y or self._DEMO_CLS[1])
            res = eng.classify(classifier_names.get(algo, algo or "knn"), dX, dy)
        elif re.search(r"\banomal", c):
            res = eng.detect_anomalies(algo or "isolation_forest", X or self._DEMO_ANOM)
        elif re.search(r"time[- ]series|forecast|arima|holt", c):
            res = eng.time_series(algo or "arima", series or self._DEMO_SERIES)
        else:  # regression default
            dX, dy = (X or self._DEMO_XY[0]), (y or self._DEMO_XY[1])
            res = eng.regression(regression_names.get(algo, algo or "linearregression"), dX, dy)

        note = "" if (X and y) or (X and "cluster" in c) or series else \
            "\n(Demo data used, as you asked — supply X=[[...]] y=[...] or a CSV for real runs.)"
        if isinstance(res, dict) and str(res.get("status", "")).lower() == "error":
            return {"status": "error", "response_type": "engine_ml", "raw": res,
                    "message": f"The ML engine could not run this: {res.get('message', res)}"}
        extra = _ml_predictions(command, res, X)
        return self._ok("engine_ml", f"ML result:\n{humanize(res)}{extra}{note}", raw=res)

    # ── IoT ──────────────────────────────────────────────────────────────
    def _run_iot(self, command: str) -> Dict[str, Any]:
        c = command.lower()
        # Live hardware over USB-serial ("detect my iot devices", "scan i2c on COM5", "flash this to
        # my esp32", "read serial") — distinct from generating firmware text below.
        live = self._run_iot_live(command, c)
        if live is not None:
            return live
        eng = self._get("iot")
        if not eng:
            return self._unavailable("IoT", "")
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
            res = eng.generate_esp_code(board, comps or ["dht11"],      # the engine reads "protocols"
                                        protocols=[proto_m.group(1) if proto_m else "mqtt"])
        if isinstance(res, dict) and str(res.get("status", "")).lower() == "error":
            return {"status": "error", "response_type": "engine_iot", "raw": res,
                    "message": f"IoT: {res.get('message', 'failed')}"}
        return self._ok("engine_iot", f"IoT code generated:\n{humanize(res, limit=4000)}", raw=res)

    _COM_RE = re.compile(r"\b(COM\d{1,3}|/dev/tty\w+)\b", re.I)

    def _run_iot_live(self, command: str, c: str) -> Optional[Dict[str, Any]]:
        """Talk to a board that is physically plugged in. Returns None when the command is really about
        generating firmware text (handled by the code generator above)."""
        wants_detect = re.search(r"\b(detect|list|find|show|what(?:'s| is| are))\b.*\b(devices?|boards?|ports?|"
                                 r"connected|plugged|wired|microcontroller|serial|usb)\b", c) or \
            re.search(r"\b(connected|plugged in)\b.*\b(iot|devices?|boards?|microcontroller)\b", c)
        wants_i2c = "i2c" in c and re.search(r"\b(scan|list|detect|what|find|wired|connected)\b", c)
        wants_flash = re.search(r"\b(flash|upload|burn|write|deploy|program|push)\b", c) and \
            re.search(r"\b(board|esp32|esp8266|arduino|pico|device|com\d|microcontroller|chip|firmware|it|this)\b", c)
        wants_read = re.search(r"\bserial (monitor|port|console|output)\b", c) or \
            (re.search(r"\b(read|monitor|show|check)\b.*\bserial\b", c) and
             re.search(r"\b(board|device|port|baud|com\d|esp32|esp8266|arduino|pico|microcontroller)\b", c)) or \
            re.search(r"\bis\b.*\b(board|esp32|arduino|pico)\b.*\b(working|running|alive)\b", c)
        if not (wants_detect or wants_i2c or wants_flash or wants_read):
            return None
        try:
            from tools.iot_live import LiveIoT
        except Exception as exc:
            return {"status": "error", "response_type": "engine_iot_live",
                    "message": f"Live IoT needs pyserial: {exc}. Install it with "
                               "'python -m pip install pyserial platformio'."}
        live = LiveIoT()
        port_m = self._COM_RE.search(command)
        device = port_m.group(1) if port_m else ""
        try:
            if wants_detect and not (wants_flash or wants_i2c):
                r = live.detect()
            elif wants_i2c:
                allow = bool(re.search(r"\bflash\b|\bscanner\b|\byes\b", c))
                r = live.scan_i2c(device, allow_flash=allow)
            elif wants_read:
                secs = _extract_kv_num(command, "seconds", 6)
                r = live.read(device, seconds=float(secs))
            elif wants_flash:
                r = self._iot_flash(command, c, live, device)
            else:
                r = live.detect()
        except Exception as exc:
            return {"status": "error", "response_type": "engine_iot_live",
                    "message": f"Live IoT failed: {type(exc).__name__}: {exc}"}
        r.setdefault("response_type", "engine_iot_live")
        return r

    def _iot_flash(self, command: str, c: str, live, device: str) -> Dict[str, Any]:
        """Get the firmware to flash — a named source file, or generate it from the request — then flash
        it (LiveIoT.flash gates the write with the policy engine)."""
        import os as _os
        source = ""
        file_m = re.search(r"\b([\w./\\-]+\.(?:ino|cpp|c))\b", command)
        if file_m:
            from tom_core import user_files
            hits = user_files.find(file_m.group(1))
            if hits and _os.path.isfile(hits[0]):
                source = open(hits[0], encoding="utf-8", errors="replace").read()
            elif not hits:
                return {"status": "error", "response_type": "engine_iot_live",
                        "message": f"I couldn't find {file_m.group(1)} in your folders. Give me its full path."}
        if not source:
            # generate firmware from the request (DHT11 blink-style default if nothing specific)
            eng = self._get("iot")
            board_m = re.search(r"\b(esp32|esp8266|arduino|uno|nano|mega|pico)\b", c)
            board = (board_m.group(1) if board_m else "esp32")
            comps = re.findall(r"\b(dht11|dht22|bme280|bmp180|ds18b20|pir|hc-sr04|relay|servo|led|oled|lcd)\b", c)
            gen = eng.generate_esp_code(board if board in ("esp32", "esp8266") else "esp32",
                                        comps or ["led"], protocols=["mqtt"]) if eng else {}
            source = gen.get("result", "") if isinstance(gen, dict) else ""
            if not source:
                return {"status": "needs_input", "response_type": "engine_iot_live",
                        "message": "Tell me what to flash: a source file (e.g. \"flash blink.ino to COM5\") "
                                   "or what the firmware should do (e.g. \"flash a DHT11 reader to my esp32\")."}
        board_hint = ""
        bm = re.search(r"\b(esp32-s3|esp32-c3|esp32|esp8266|nodemcu|uno|nano|mega|pico|arduino)\b", c)
        if bm:
            board_hint = bm.group(1)
        return live.flash(source, device=device, board_hint=board_hint, what="your firmware")

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
            return {"status": "needs_input", "response_type": "engine_hardware",
                    "message": "Hardware commands: move mouse to X Y · click [at X Y] · double/right click · "
                               "type text <...> · press key <k> · screenshot · volume up/down/to N · "
                               "mute/unmute · system info"}
        if isinstance(r, dict) and str(r.get("status", "")).lower() == "error":
            return {"status": "error", "response_type": "engine_hardware", "raw": r,
                    "message": f"Hardware: {r.get('message', 'failed')}"}
        extra = {"path": r["path"]} if isinstance(r, dict) and r.get("path") else {}
        return self._ok("engine_hardware", humanize(r), raw=r, **extra)

    # ── Auto-scaler (resource management, parallel execution) ────────────
    def _run_scaler(self, command: str) -> Dict[str, Any]:
        eng = self._get("scaler")
        if not eng:
            return self._unavailable("Auto-scaler", "")
        c = command.lower()
        if re.search(r"\b(optimal|optimize)\b.*\bworkers?\b", c):
            type_m = re.search(
                r"\b(cpu[-_]?bound|io[-_]?bound|network|disk|file|compute|computation|cpu|io)\b", c)
            res = eng.optimize_workers(type_m.group(1) if type_m else "cpu")
        elif re.search(r"\b(simulate load|benchmark parallel|stress test)\b", c):
            n_m = re.search(r"\b(\d+)\s*tasks?\b", c)
            count = min(int(n_m.group(1)), 200) if n_m else 10
            res = eng.simulate_load(count)
        elif "performance report" in c:
            res = eng.performance_report()
        elif "status" in c:
            res = eng.get_status()
        else:
            res = eng.detect_resources()
        body = res.get("result", res) if isinstance(res, dict) else res
        return self._ok("engine_scaler",
                        f"Auto-scaler: {res.get('message', '')}\n{humanize(body)}", raw=res)

    # ── Network diagnostics (own LAN / this host, read-only) ─────────────
    def _run_network(self, command: str) -> Dict[str, Any]:
        eng = self._get("network")
        if not eng:
            return self._unavailable("Network diagnostics", "")
        c = command.lower()
        # Port scan: "scan ports on 192.168.1.10" / "scan my ports".
        if re.search(r"\b(scan|check)\b.*\bports?\b", c) or \
                re.search(r"\b(open|listening)\s+ports?\b|\bports?\b.*\b(open|listening)\b", c):
            host_m = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", command)
            host = host_m.group(1) if host_m else "127.0.0.1"
            return eng.scan_ports(host)
        if re.search(r"\bprofiles?\b", c) or re.search(r"\b(saved|known|remember)\b.*\b(wi[- ]?fi|networks?)\b", c):
            return eng.wifi_profiles()
        if re.search(r"\bwi[- ]?fi\b|\bwlan\b", c) and re.search(r"\b(status|signal|connection|connected|current)\b", c):
            return eng.wifi_status()
        if re.search(r"\b(wi[- ]?fi|wlan)\b", c) and not re.search(r"\bdevices?\b", c):
            return eng.wifi_status()
        if re.search(r"\b(ip|overview|address|hostname|adapters?)\b", c) and not re.search(r"\bdevices?\b", c):
            return eng.network_overview()
        # Default: who is on my network.
        return eng.list_devices()

    # ── Media (real video via ffmpeg, real photo via Pillow) ──────────────
    def _run_media(self, command: str) -> Dict[str, Any]:
        eng = self._get("media")
        if not eng:
            return self._unavailable("Media", "")
        c = command.lower()
        video_m = re.search(_VIDEO_EXT, command, re.I)
        photo_m = re.search(_PHOTO_EXT, command, re.I)
        is_photo = bool(photo_m) and not video_m
        path = (video_m or photo_m).group(0) if (video_m or photo_m) else None
        if not path:
            return self._ok("engine_media",
                            "Tell me the file to edit (a full path ending in .mp4/.mov/... for video, "
                            ".png/.jpg/... for photo), e.g. 'trim video C:\\clips\\a.mp4 from 5s for 10s' "
                            "or 'apply sepia filter to photo C:\\pics\\a.png'.")

        if is_photo:
            if not eng.photo_available():
                return self._unavailable("Photo editing", "Pillow must be installed.", "media")
            if "crop" in c:
                nums = [int(x) for x in re.findall(r"\d+", command.replace(path, ""))][:4]
                if len(nums) < 4:
                    return self._ok("engine_media",
                                    "Give me 4 numbers for the crop box: left top right bottom "
                                    "(pixels), e.g. 'crop photo a.png 0 0 400 300'.")
                res = eng.crop_image(path, *nums)
            elif re.search(r"\bresize|scale\b", c):
                wh = re.search(r"(\d+)\s*[x\u00d7]\s*(\d+)", c)
                if not wh:
                    return self._ok("engine_media", "Give me a size, e.g. 'resize photo a.png to 800x600'.")
                res = eng.resize_image(path, int(wh.group(1)), int(wh.group(2)))
            elif re.search(r"\brotate\b", c):
                deg_m = re.search(r"(-?\d+(?:\.\d+)?)\s*deg", c) or re.search(r"\bby\s+(-?\d+(?:\.\d+)?)", c)
                res = eng.rotate_image(path, float(deg_m.group(1)) if deg_m else 90.0)
            elif re.search(r"\bwatermark\b", c):
                text = _extract_quoted(command) or "TOM"
                pos_m = re.search(r"\b(top-left|top-right|bottom-left|bottom-right|center)\b", c)
                res = eng.add_watermark(path, text, pos_m.group(1) if pos_m else "bottom-right")
            elif re.search(r"\bconvert\b", c):
                fmt_m = re.search(r"\bto\s+(png|jpe?g|gif|bmp|webp)\b", c)
                if not fmt_m:
                    return self._ok("engine_media", "Convert to which format? e.g. 'convert photo a.png to jpg'.")
                res = eng.convert_image_format(path, fmt_m.group(1))
            else:
                filt_m = re.search(
                    r"\b(grayscale|black and white|blur|sharpen|smooth|contour|brighten|darken|"
                    r"high contrast|saturate|sepia)\b", c)
                if not filt_m:
                    return self._ok("engine_media",
                                    "Which filter? grayscale, blur, sharpen, smooth, contour, brighten, "
                                    "darken, high_contrast, saturate, sepia.")
                name = "grayscale" if filt_m.group(1) == "black and white" else filt_m.group(1).replace(" ", "_")
                res = eng.apply_filter(path, name)
        else:
            if not eng.video_available():
                return self._unavailable("Video editing", "ffmpeg must be installed.", "media")
            if re.search(r"\btrim|cut|clip\b", c):
                start_m = re.search(r"from\s+(\d+(?:\.\d+)?)\s*s", c)
                dur_m = re.search(r"for\s+(\d+(?:\.\d+)?)\s*s", c)
                res = eng.trim_video(path, float(start_m.group(1)) if start_m else 0.0,
                                     float(dur_m.group(1)) if dur_m else 10.0)
            elif re.search(r"\bconcat(enate)?|combine|merge|join\b", c):
                paths = re.findall(_VIDEO_EXT, command, re.I)
                if len(paths) < 2:
                    return self._ok("engine_media", "Give me at least 2 video file paths to combine.")
                res = eng.concat_videos(paths)
            elif re.search(r"\bcaption|subtitle|text overlay|add text\b", c):
                text = _extract_quoted(command) or "TOM"
                pos_m = re.search(r"\b(top|center|bottom)\b", c)
                res = eng.add_text_overlay(path, text, pos_m.group(1) if pos_m else "bottom")
            elif "extract audio" in c:
                res = eng.extract_audio(path)
            elif re.search(r"\bresize|scale\b", c):
                wh = re.search(r"(\d+)\s*[x\u00d7]\s*(\d+)", c)
                if not wh:
                    return self._ok("engine_media", "Give me a size, e.g. 'resize video a.mp4 to 1280x720'.")
                res = eng.resize_video(path, int(wh.group(1)), int(wh.group(2)))
            elif "mute" in c:
                res = eng.set_video_volume(path, 0.0)
            elif "volume" in c:
                factor_m = re.search(r"(\d+(?:\.\d+)?)\s*%", c)
                res = eng.set_video_volume(path, (float(factor_m.group(1)) / 100.0) if factor_m else 1.5)
            elif re.search(r"\bconvert\b", c):
                fmt_m = re.search(r"\bto\s+(mp4|mov|avi|mkv|webm|flv|wmv)\b", c)
                if not fmt_m:
                    return self._ok("engine_media", "Convert to which format? e.g. 'convert video a.mov to mp4'.")
                res = eng.convert_video_format(path, fmt_m.group(1))
            else:
                res = eng.adjust_video(path)

        # Same lesson as Blender: don't hardcode success via _ok() regardless of
        # what the engine actually reported, and promote path/paths to the top
        # level so the verification pass below re-checks the file on disk.
        if res.get("status") != "success":
            return {"status": "error", "response_type": "engine_media",
                    "message": f"Media: {res.get('message', 'failed')}", "raw": res}
        extra = {"raw": res}
        if res.get("path"):
            extra["path"] = res["path"]
        if res.get("paths"):
            extra["paths"] = res["paths"]
        return self._ok("engine_media", f"Media: {res.get('message', 'done')}", **extra)

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
        if isinstance(res, dict) and str(res.get("status", "")).lower() == "error":
            return {"status": "error", "response_type": "engine_gamedev", "raw": res,
                    "message": f"Game dev: {res.get('message', 'failed')}"}
        extra = {"path": res["path"]} if isinstance(res, dict) and res.get("path") else {}
        return self._ok("engine_gamedev", humanize(res, limit=4000), raw=res, **extra)

    # ── Blender ──────────────────────────────────────────────────────────
    def _run_blender(self, command: str) -> Dict[str, Any]:
        eng = self._get("blender")
        if not eng:
            return self._unavailable("Blender", "", "blender")
        if not eng.is_available():
            return {"status": "error", "response_type": "engine_blender",
                    "message": "Blender is not installed (or TOM can't find it), so nothing was built. "
                               "Install Blender from blender.org, or set BLENDER_PATH to blender.exe, "
                               "and ask again."}
        task = re.sub(r"^blender\s*", "", command, flags=re.I).strip() or "cube"
        res = eng.generate_and_execute(task)
        # _ok() hardcodes status="success" -- it used to be returned unconditionally
        # here regardless of what the engine actually reported, so a Blender script
        # that produced nothing still read as a success to the caller. Also promote
        # path/paths to the top level (not just nested in "raw") so the verification
        # pass below (_apply_verification/_declared_artifacts) actually re-checks the
        # file on disk instead of silently skipping an unrecognized artifact shape.
        if res.get("status") != "success":
            return {"status": "error", "response_type": "engine_blender",
                    "message": f"Blender: {res.get('message', 'failed')}", "raw": res}
        extra = {"raw": res}
        if res.get("path"):
            extra["path"] = res["path"]
        if res.get("paths"):
            extra["paths"] = res["paths"]
        return self._ok("engine_blender", f"Blender:\n{humanize(res)}", **extra)

    # ── News ─────────────────────────────────────────────────────────────
    def _run_news(self, command: str) -> Dict[str, Any]:
        # Current, dated articles with their own links (tools.news_briefing); the older feed engine is only a
        # fallback — its feeds returned stale SEO pages with the feed URL as every link (live check 2026-10-27).
        from tools import news_briefing
        c = command.lower()
        topic = ""
        m = re.search(r"(?:news|headlines|updates)\s+(?:on|about|for|regarding)\s+(.+)|search(?: news)?(?: for)?\s+(.+)", c)
        if m:
            topic = (m.group(1) or m.group(2) or "").strip(" ?.!")
        kind = "tech" if re.search(r"\btech", c) else "world" if "world" in c else "daily"
        brief = news_briefing.build(kind, topic=topic)
        if brief["status"] == "success":
            return self._ok("engine_news", brief["message"], raw={"count": brief["count"]})
        eng = self._get("news")
        if not eng:
            return {"status": "error", "response_type": "engine_news", "message": brief["message"]}
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
        if isinstance(res, dict) and str(res.get("status", "")).lower() == "error":
            return {"status": "error", "response_type": "engine_news", "raw": res,
                    "message": f"News: {res.get('message', 'failed')}"}
        # The headlines themselves, not just "61 stories across 5 sections".
        payload = res.get("result") if isinstance(res, dict) and isinstance(res.get("result"), dict) else {}
        msg = (payload.get("markdown") or res.get("briefing") or res.get("summary")
               or res.get("message") or humanize(res))
        return self._ok("engine_news", str(msg)[:3500], raw=res)

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
        if isinstance(r, dict) and str(r.get("status", "")).lower() == "error":
            return {"status": "error", "response_type": "engine_deps", "raw": r,
                    "message": f"Env/Deps: {r.get('message', 'failed')}"}
        if "conflict" in c and isinstance(r, dict):
            import sys as _sys
            return self._ok("engine_deps", f"Dependency check ({_sys.executable}):\n{r.get('message', '')}", raw=r)
        return self._ok("engine_deps", f"Env/Deps:\n{humanize(r)}", raw=r)

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
        if isinstance(r, list) and not r:
            return self._ok("engine_autoupdate", "No updates have been applied yet (the update history is empty).",
                            raw=r)
        if isinstance(r, dict) and str(r.get("status", "")).lower() == "error":
            return {"status": "error", "response_type": "engine_autoupdate", "raw": r,
                    "message": f"Auto-update: {r.get('message', 'failed')}"}
        if isinstance(r, dict) and r.get("message") and "behind" in r:        # check_git_updates: already readable
            return self._ok("engine_autoupdate", r["message"], raw=r)
        return self._ok("engine_autoupdate", f"Auto-update:\n{humanize(r)}", raw=r)

    # ── Voice+ (text emotion only — audio needs the GUI/voice mode) ─────
    def _run_voiceplus(self, command: str) -> Dict[str, Any]:
        eng = self._get("voiceplus")
        if not eng:
            return self._unavailable("Voice+", "", "voiceplus")
        m = re.search(r"(?:text\s*:\s*)(.+)$", command, flags=re.I | re.S)
        text = m.group(1).strip() if m else command
        r = eng.analyze_emotional_state(text)
        result = r.get("result", r) if isinstance(r, dict) else r
        if isinstance(result, dict):
            scores = {k: v for k, v in (result.get("emotion_scores") or {}).items() if v}
            lines = [f"Main emotion: {result.get('dominant_emotion', 'unknown')} "
                     f"(confidence {_fmt_scalar(result.get('emotion_confidence'))})"]
            if scores:
                lines.append("Detected: " + ", ".join(f"{k} {_fmt_scalar(v)}" for k, v in
                                                      sorted(scores.items(), key=lambda kv: -kv[1])))
            if result.get("crisis_detected"):
                lines.append("Crisis language detected — if you are in danger, please contact local "
                             "emergency services or a crisis line now.")
            return self._ok("engine_voiceplus", "\n".join(lines), raw=r)
        return self._ok("engine_voiceplus", f"Emotion analysis:\n{humanize(r)}", raw=r)

    # ── Autonomous (async) ───────────────────────────────────────────────
    async def _run_autonomous(self, command: str) -> Dict[str, Any]:
        eng = self._get("autonomous")
        if not eng:
            return self._unavailable("Autonomous agent", "")
        task = re.sub(r"^(execute\s+)?autonomous(ly)?\s*(task)?\s*:?\s*", "", command, flags=re.I).strip()
        res = await eng.execute(task or command)
        if res.get("status") != "success":
            # failed / unverified / partial / nothing plannable: never reported as done
            return {"status": res.get("status", "error"), "response_type": "engine_autonomous",
                    "message": res.get("message", ""), "raw": res}
        extra = {"paths": res["paths"]} if res.get("paths") else {}
        return self._ok("engine_autonomous", str(res.get("message", ""))[:4000], raw=res,
                        verified=res.get("verified", False), **extra)

    # ── Coding workflow (AT-013) ──────────────────────────────────────────
    async def _run_fixtests(self, command: str) -> Dict[str, Any]:
        from tom_core import projects
        m = re.search(r"\b(?:in|at|for)\s+[\"']?([A-Za-z]:[\\/][^\"']+|[./~][^\"'\s]+)", command)
        named = re.search(r"\b(?:in|at|for)\s+(?:the\s+|my\s+)?(?:project\s+)?[\"']?([\w .-]+?)[\"']?\s*(?:project)?$",
                          command, re.I)
        profile = projects.get(m.group(1).strip()) if m else (projects.get(named.group(1)) if named else None)
        if not m and not profile:
            return {"status": "needs_input", "response_type": "engine_fixtests",
                    "message": "Which project folder? For example: fix the failing tests in C:/code/myapp "
                               "(or save it once: add project myapp at C:/code/myapp with tests: pytest -q)"}
        repo = profile["root"] if profile and not m else os.path.expanduser(m.group(1).strip().rstrip(".").strip())
        test_cmd = (profile or {}).get("test_command") or ""
        agent = self._agent
        if agent is None or not hasattr(agent, "_invoke_llm"):
            return self._unavailable("Coding workflow", "")

        async def ask(system, user):
            from langchain_core.prompts import ChatPromptTemplate
            prompt = ChatPromptTemplate.from_messages([("system", "{system}"), ("user", "{user}")])
            resp = await agent._invoke_llm(prompt, {"system": system, "user": user}, "fix_tests",
                                           getattr(agent, "code_llm", None) or agent.llm)
            return getattr(resp, "content", "") or ""

        from tom_core.coding import fix_failing_tests
        import shlex
        res = await fix_failing_tests(repo, ask, test_cmd=shlex.split(test_cmd, posix=False) if test_cmd else None)
        if res.get("status") != "success":
            return {"status": res.get("status", "error"), "response_type": "engine_fixtests",
                    "message": res.get("message", ""), "raw": res}
        return self._ok("engine_fixtests", res["message"][:6000], raw=res, verified=res.get("verified", False))

    # ── Multi-agent orchestrator (lives on the agent) ────────────────────
    async def _run_orchestrator(self, command: str) -> Dict[str, Any]:
        orch = getattr(self._agent, "orchestrator", None)
        if not orch:
            return self._unavailable("Multi-agent orchestrator", "")
        task = re.sub(r"^deploy multi[- ]agent task\s*:?\s*", "", command, flags=re.I).strip()
        res = await orch.execute_task(task or command, coordinate=True)
        msg = res.get("message") or res.get("result") or str(res)
        if res.get("status") not in ("success",):
            return {"status": res.get("status", "error"), "response_type": "engine_orchestrator",
                    "message": str(msg), "raw": res}
        return self._ok("engine_orchestrator", str(msg)[:4000], raw=res)

    # ── Web automation: verify a URL / localhost app ─────────────────────
    async def _run_webauto(self, command: str) -> Dict[str, Any]:
        wa = getattr(self._agent, "web_automation", None)
        if not wa:
            return self._unavailable("Web automation", "Playwright must be installed.", "webauto")
        m = re.search(r"(https?://\S+|localhost:?\d*|\b\d{2,5}\b)", command, re.I)
        if not m:
            return {"status": "needs_input", "response_type": "engine_webauto",
                    "message": "Give me a URL or localhost port, e.g. 'verify web app on localhost:3000'."}
        target = m.group(1).rstrip(".,:;")
        if target.isdigit():
            target = f"http://localhost:{target}"
        elif not target.startswith("http"):
            target = "http://" + target
        if re.search(r"\b(debug|fix|diagnose)\b", command, re.I) and hasattr(wa, "auto_debug_loop"):
            res = await wa.auto_debug_loop(target, max_iterations=3)
            return self._ok("engine_webauto",
                            f"Auto-debug ({target}): {res.get('message', 'done')} "
                            f"({res.get('total_iterations', 0)} iterations)", raw=res)
        res = await wa.wait_and_verify(target)
        ok = isinstance(res, dict) and str(res.get("status", "")).lower() in ("success", "ok", "passed")
        if isinstance(res, dict) and not ok:
            return {"status": "error", "response_type": "engine_webauto", "raw": res,
                    "message": f"Web verification of {target} failed:\n{humanize(res)}"}
        return self._ok("engine_webauto", f"Web verification of {target}:\n{humanize(res)}", raw=res)

    # ── Website safety analysis (SafetyGuards) ───────────────────────────
    def _run_websafety(self, command: str) -> Dict[str, Any]:
        safety = getattr(self._agent, "safety", None)
        if not safety or not hasattr(safety, "analyze_website"):
            return self._unavailable("Website safety analyzer", "")
        m = re.search(r"(https?://\S+|www\.\S+|[a-z0-9-]+(?:\.[a-z0-9-]+)+\S*)", command, re.I)
        if not m:
            return {"status": "needs_input", "response_type": "engine_websafety",
                    "message": "Give me a URL to check, e.g. 'is example.com safe?'."}
        res = safety.analyze_website(m.group(1).rstrip(".,:;"))
        if isinstance(res, dict):
            probe = _probe_https(res.get("domain") or "") if res.get("trust_level") not in ("trusted", "blocked", "local") \
                else ""
            if probe and isinstance(res.get("flags"), list):
                # "example.com" typed without https:// used to be scored as "no https" (live check 2026-10-27);
                # the site itself is now tested.
                res["flags"] = [f for f in res["flags"] if f != "no_https"]
                if probe.startswith("valid"):
                    res["flags"].append("valid_https_certificate")
                    res["score"] = min(100, int(res.get("score", 50)) + 20)
                elif probe.startswith("certificate"):
                    res["flags"].append("certificate_error")
                    res["score"] = max(0, int(res.get("score", 50)) - 25)
                    res["recommendation"] = "avoid"
                score = int(res.get("score", 50))
                res["trust_level"] = "likely_safe" if score >= 70 else "uncertain" if score >= 40 else "suspicious"
                if score >= 70 and res.get("recommendation") == "proceed_with_caution":
                    res["recommendation"] = "looks safe — still don't enter passwords from a link you didn't expect"
            if isinstance(res.get("score"), (int, float)):
                res["score"] = max(0, min(100, int(res["score"])))
            flags = ", ".join(str(f).replace("_", " ") for f in res.get("flags") or []) or "none"
            verdict = str(res.get("recommendation", "unknown")).replace("_", " ")
            text = (f"Website safety for {res.get('domain', m.group(1))}:\n"
                    f"Trust level: {str(res.get('trust_level', 'unknown')).replace('_', ' ')} "
                    f"(score {res.get('score', '?')}/100)\n"
                    f"Signals: {flags}\n" + (f"Live check: {probe}\n" if probe else "") +
                    f"Recommendation: {verdict}\n"
                    "(Address heuristics plus one HTTPS request to the site — the page itself is not opened or "
                    "rendered. For a link in an email, also check the sender.)")
            return self._ok("engine_websafety", text, raw=res)
        return self._ok("engine_websafety", f"Website safety:\n{humanize(res)}", raw=res)

    # ── Code runner (subprocess + timeout, ALWAYS behind approval) ───────
    async def _run_coderun(self, command: str) -> Dict[str, Any]:
        eng = self._get("coderun")
        if not eng:
            return self._unavailable("Code runner", "")
        shell_m = re.match(r"^(?:run shell:|run command:|shell:)\s*(.+)$", command.strip(), re.I)
        js_m = re.search(r"([\w\-./\\:]+\.js)\b", command)
        m = re.search(r"([\w\-./\\:]+\.py)\b", command)
        if not (shell_m or js_m or m):
            return {"status": "needs_input", "response_type": "engine_coderun",
                    "message": "Tell me what to run: a .py/.js file, or 'run shell: <command>'."}
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
                            details={"target": shell_m.group(1) if shell_m else path}, risk_level="high"))
        if not approved:
            return {"status": "cancelled", "response_type": "engine_coderun",
                    "message": "Code run cancelled by user."}
        # The CodeRunner method itself passes the policy engine (it consumes this approval).
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
    # The sentence is read by tools/file_intent.py (rules + an optional, validated LLM pass).
    @staticmethod
    def _pick_folder(command: str) -> str:
        from tools.file_intent import pick_folder
        return pick_folder(command)

    async def _confirm_and_apply(self, plan: Dict[str, Any], op_label: str = "organize") -> Dict[str, Any]:
        """Show the plan (with the exact folder), ask, then execute and record it for undo."""
        if plan.get("status") != "plan":
            return self._ok("engine_fileops", plan.get("message", "Could not build a plan."))
        extras = self._memory_extras(plan)
        preface = extras.pop("memory_preface", "")
        if not plan["moves"]:
            return self._ok("engine_fileops", preface + "Nothing to do — " + plan["message"], **extras)
        agent = self._agent
        if agent is None or not getattr(agent, "approval_manager", None):
            return self._ok("engine_fileops",
                            preface + "[DRY RUN — approval system unavailable]\n" + plan["message"], **extras)
        import asyncio as _aio
        from tools.approval import ApprovalRequest
        approved = await _aio.to_thread(
            agent.approval_manager.request_approval,
            ApprovalRequest(action="file_ops", summary=preface + plan["message"],
                            details={"folder": plan.get("folder", ""), "count": len(plan["moves"]),
                                     "remembered_rules": [r["rule"] for r in plan.get("applied_rules", [])]},
                            risk_level="medium"))
        if not approved:
            return {"status": "cancelled", "response_type": "engine_fileops",
                    "message": "File operation cancelled. (Plan was: " + plan["message"][:200] + ")", **extras}
        # R3 policy gate: moves in the user's own folder are a material change the user just approved
        # (protected locations stay blocked; the approval above is consumed, not asked again).
        from tom_core.policy.engine import ActionClass
        from tom_core.tools.guard import aenforce
        gate = await aenforce("fs.organize", ActionClass.MATERIAL_CHANGE, payload={"folder": plan.get("folder", "")},
                              paths=[plan.get("folder", "")], approval_action="file_ops",
                              manager=agent.approval_manager)
        if not gate.allowed:
            return {**gate.refusal(), "response_type": "engine_fileops", **extras}
        from tools.file_ops import FileOps
        ops = FileOps()
        res = ops.execute_plan(plan)
        ops.record_organization(plan, res)
        summary = ", ".join(f"{k} ({v})" for k, v in sorted(plan.get("summary", {}).items()))
        detail = f"{res['message']}\nNow in: {summary}" if summary else res["message"]
        if plan.get("kept"):
            detail += f"\nLeft in place: {', '.join(plan['kept'][:8])}"
        extras["completed_moves"] = res.get("completed_moves") or []
        return self._ok("engine_fileops", preface + detail, **extras)

    async def _run_fileops(self, command: str) -> Dict[str, Any]:
        from tools.file_intent import understand
        from tools.file_ops import FileOps
        ops = FileOps()
        agent = self._agent
        llm = (getattr(agent, "fast_llm", None) or getattr(agent, "llm", None)) if agent is not None else None
        intent = await understand(command, llm)
        op, folder = intent.operation, intent.folder

        if op == "unknown":
            return self._ok("engine_fileops",
                            "I can organize, move, rename, zip, convert or find files. Tell me which, and the folder "
                            "(for example: 'organize my downloads by type').")

        # Undo is supported only for TOM's own recorded organization actions. With no folder named
        # ("revert what you just did") it reverts the most recent one, wherever it happened.
        if op == "undo":
            plan = ops.plan_undo_last_organization(folder or None)
            if plan.get("status") != "plan":
                return self._ok("engine_fileops", plan["message"])
            agent = self._agent
            if agent is None or not getattr(agent, "approval_manager", None):
                return self._ok("engine_fileops", "[DRY RUN — approval system unavailable]\n" + plan["message"])
            import asyncio as _aio
            from tools.approval import ApprovalRequest
            approved = await _aio.to_thread(
                agent.approval_manager.request_approval,
                ApprovalRequest(action="file_ops", summary=plan["message"],
                                details={"count": len(plan["moves"]), "operation": "undo"},
                                risk_level="medium"))
            if not approved:
                return {"status": "cancelled", "response_type": "engine_fileops",
                        "message": "Undo cancelled. (Plan was: " + plan["message"] + ")"}
            from tom_core.policy.engine import ActionClass
            from tom_core.tools.guard import aenforce
            gate = await aenforce("fs.organize_undo", ActionClass.MATERIAL_CHANGE,
                                  payload={"operation": "undo", "count": len(plan["moves"])},
                                  approval_action="file_ops", manager=agent.approval_manager)
            if not gate.allowed:
                return {**gate.refusal(), "response_type": "engine_fileops"}
            undone = ops.execute_undo_plan(plan)
            return self._ok("engine_fileops", undone["message"],
                            completed_moves=undone.get("completed_moves") or [])

        if not folder:
            # Used to default silently to the Downloads folder, whatever the request said.
            return self._ok("engine_fileops",
                            "Which folder should I work in? Name it (for example Downloads or Desktop) or give the full path.")

        if op == "find":
            return self._ok("engine_fileops", ops.find_files(folder, intent.find_pattern)["message"])
        if op == "zip":
            return self._ok("engine_fileops", ops.zip_folder(folder)["message"])
        if op == "convert":
            return self._ok("engine_fileops", ops.convert_images(folder, intent.convert_to)["message"])

        if op == "rename":
            if not intent.rename_from:
                return self._ok("engine_fileops",
                                "Tell me the pattern, e.g.: bulk rename in downloads 'IMG_' to 'Holiday_'")
            plan = ops.plan_bulk_rename(folder, intent.rename_from, intent.rename_to)
        elif op == "move":
            from tools.file_intent import KNOWN_FOLDER_WORDS
            if intent.move_type is None:
                return self._ok("engine_fileops", "Which files should I move? For example: "
                                "'move the pdfs in downloads into a folder called Invoices'.")
            if not intent.destination:
                return self._ok("engine_fileops", "Which folder should they go into? For example: "
                                "'move the pdfs in downloads into a folder called Invoices'.")
            if intent.destination.lower() in KNOWN_FOLDER_WORDS:
                return self._ok("engine_fileops", f"I can only move files into a subfolder of the folder "
                                f"they are in, not into {intent.destination.title()}. Name a subfolder instead.")
            kind, value = intent.move_type
            plan = (ops.plan_move_by_extension(folder, value, intent.destination) if kind == "ext"
                    else ops.plan_move_by_group(folder, value, intent.destination))
        else:
            # Long-term memory: the user's remembered folder rules override defaults.
            rules, memory_note = [], ""
            if agent is not None and hasattr(agent, "remembered_folder_rules"):
                try:
                    rules, memory_note = await agent.remembered_folder_rules(command)
                except Exception as exc:
                    memory_note = f"(memory unavailable: {str(exc)[:80]})"
            if intent.organize_by == "year":
                plan = ops.plan_organize_by_year(folder, rules=rules)
            else:
                plan = ops.plan_organize_by_type(folder, rules=rules)
            if plan.get("status") == "plan":
                plan["memory_note"] = memory_note
                plan["rules_available"] = [r.describe() for r in rules]
        return await self._confirm_and_apply(plan)

    @staticmethod
    def _memory_extras(plan: Dict[str, Any]) -> Dict[str, Any]:
        """Surface which remembered rules shaped this plan (shown as 'Remembering: …')."""
        applied = plan.get("applied_rules") or []
        extras: Dict[str, Any] = {"applied_rules": applied,
                                  "memories_used": [a["rule"] for a in applied]}
        if applied:
            lines = "\n".join(f"  • {a['rule']}  ({a['files']} file{'s' if a['files'] != 1 else ''})"
                               for a in applied)
            extras["memory_preface"] = f"Remembering how you like this folder organized:\n{lines}\n\n"
        elif plan.get("memory_note"):
            extras["memory_preface"] = plan["memory_note"] + "\n\n"
        else:
            extras["memory_preface"] = ""
        return extras

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
