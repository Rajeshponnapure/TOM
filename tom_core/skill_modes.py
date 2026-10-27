"""Quick-action skill modes: every interface shortcut becomes "do this kind of work with TOM's brain".

Owner report 2026-10-21: Web Auto, Security and most other quick actions opened a dialog asking
for a raw URL / fixed syntax and then called a handler directly — bypassing the agent (no
understanding, memory, safety gate or task record; also PRD TOM-MIG-010). Now a quick action only
selects a mode. The user's next message (typed or spoken) is sent through
TomAgent.execute_task with the mode attached as a hint; the agent tries the matching engine and,
when the request is not something the engine can execute, answers from the matching skill's
knowledge (skills/*.md) instead of failing.

The hint travels inside the task text as a short tag (TaskService keeps a single text field):
"[[mode:security]] is example.com safe?". split() removes it before anything else reads the text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

_TAG = re.compile(r"^\s*\[\[mode:([a-z_]+)\]\]\s*")
# A request that already says what to do ("make a doc on ...") is sent as typed; a bare topic
# ("quarterly sales") is wrapped in the mode's template.
_STARTS_WITH_ACTION = re.compile(
    r"^(?:please\s+|can you\s+|could you\s+)?(?:create|make|write|draft|build|generate|send|open|search|find|"
    r"analy[sz]e|check|scan|run|train|predict|design|show|list|summari[sz]e|update|install|scaffold|render|"
    r"trim|cut|edit|resize|convert|is|are|what|how|why|who|when|where|tell|explain|give|set ?up|test|verify)\b",
    re.IGNORECASE)


@dataclass(frozen=True)
class SkillMode:
    key: str
    label: str
    hint: str                                  # placeholder / one-line explanation in the UI
    examples: Tuple[str, ...]                  # clickable sample requests
    template: str = ""                         # wraps a bare topic: "Create a Word document about {}"
    engine: str = ""                           # tools.engine_router key tried first
    skill: str = ""                            # skills/ record used for knowledge answers
    needs_file: str = ""                       # "", "any", "data", "media" — the UI opens a file picker
    engines: Tuple[str, ...] = field(default=())   # other engines that also belong to this mode
    # When the engine router does not recognise the request as one of this mode's engines:
    #   "skill"    answer from the mode's skill knowledge (never an engine's demo output)
    #   "engine"   still run the mode's engine (it understands plain requests itself)
    #   "pipeline" normal TOM routing (documents, email, browser, chat …)
    fallback: str = "pipeline"


MODES: Dict[str, SkillMode] = {m.key: m for m in (
    SkillMode("word", "Word Doc", "What should the document be about?",
              ("a one-page project proposal for a mobile app", "meeting notes template for weekly standups"),
              template="Create a professional Word document about {}", skill="word-skills"),
    SkillMode("excel", "Excel", "What should the spreadsheet track or calculate?",
              ("a monthly budget with income, expenses and savings", "a sales tracker by region and month"),
              template="Create an Excel spreadsheet for {}", skill="excel-skills"),
    SkillMode("powerpoint", "PowerPoint", "What is the presentation about?",
              ("5 slides introducing our product to investors", "a training deck on password safety"),
              template="Create a professional PowerPoint about {}", skill="powerpoint-skills"),
    SkillMode("pdf", "PDF Report", "What should the report cover?",
              ("a report on renewable energy trends in India", "a summary of this week's AI news"),
              template="Create a professional PDF report about {}", skill="content-generation"),
    SkillMode("website", "Website", "Which business or project is the website for? I'll ask for anything I need.",
              ("a bakery called Sweet Crumbs in Hyderabad", "my dental clinic in Pune",
               "a landing page for our fitness app"),
              template="Build a professional website for {}"),
    SkillMode("email", "Email", "Who is it to, and what is it about?",
              ("Ravi about moving tomorrow's meeting to 4 pm", "my manager asking for Friday off"),
              template="Write an email to {}", skill="email-writing"),
    SkillMode("search", "Web Search", "What do you want to find out?",
              ("latest news on electric scooters in India", "best laptops under 60000 rupees"),
              template="Search the web for {}"),
    SkillMode("analyze", "Analyze", "Describe what to analyze, or attach a file.",
              ("compare iPhone 16 and Pixel 9 for battery life", "pros and cons of remote work"),
              template="Analyze {}", skill="predictive-analysis-skills"),
    SkillMode("whatsapp", "WhatsApp", "Who should get the message, and what should it say?",
              ("Ravi saying I'll be 10 minutes late", "Mom saying I reached home"),
              template="Send a WhatsApp message to {}"),
    SkillMode("webauto", "Web Auto", "What should I do in the browser? Give a site or localhost port to verify "
              "or debug, or just say what you want done.",
              ("open youtube and search lofi music", "check that http://localhost:3000 loads",
               "debug http://localhost:5173"),
              engine="webauto", engines=("webrecipes",), skill="frontend-dev"),
    SkillMode("multiagent", "Multi-Agent", "Describe a bigger job to split across agents.",
              ("research the top 3 CRM tools and write a comparison", "plan a 3-day Goa trip and draft the itinerary"),
              engine="orchestrator", template="Deploy multi-agent task: {}", fallback="engine"),
    SkillMode("security", "Security", "Ask about safety — a website, this PC, your network or a security topic.",
              ("is example.com safe to open?", "which ports are open on this PC?",
               "how do I make my Wi-Fi more secure?"),
              engine="websafety", engines=("network",), skill="cybersecurity-skills", fallback="skill"),
    SkillMode("file", "File Anal", "Pick a file; then ask what you want to know about it.",
              ("summarize this document", "what are the key numbers in this file?"),
              needs_file="any"),
    SkillMode("data", "Data Anal", "Pick a CSV/Excel file; then ask your question.",
              ("show the main trends", "which month had the highest sales?"),
              needs_file="data", skill="data-science"),
    SkillMode("autonomous", "Autonomous", "Describe a multi-step task to plan, run and verify.",
              ("create a folder of 3 short poems as text files on my desktop",
               "find the 5 largest files in my Downloads and list them"),
              engine="autonomous", template="Execute autonomous task: {}", fallback="engine"),
    SkillMode("hardware", "Hardware", "Say what to do with the mouse, keyboard, volume or screen.",
              ("set the volume to 30", "take a screenshot", "show system info"),
              engine="hardware", fallback="engine"),
    SkillMode("skill", "Skill", "Ask which skills TOM has, or ask a question in any skill area.",
              ("what skills are loaded?", "explain REST vs GraphQL using your backend skill")),
    SkillMode("ml", "ML", "Describe the prediction or model, or attach data.",
              ("train a regression on X=[[1],[2],[3]] y=[2,4,6]", "how would I forecast monthly sales?"),
              engine="ml", skill="machine-learning", fallback="skill"),
    SkillMode("iot", "IoT", "Describe the board and what it should do.",
              ("ESP32 reading a DHT11 and publishing over MQTT", "Arduino blinking an LED every second"),
              engine="iot", skill="iot-skills", fallback="skill"),
    SkillMode("vlsi", "VLSI", "Describe the hardware design.",
              ("8-bit up counter in Verilog with a testbench", "a 4-state traffic light FSM"),
              engine="vlsi", skill="vlsi-skills", fallback="skill"),
    SkillMode("env", "Env Setup", "Say what to set up or check in a Python environment.",
              ("check this project for dependency conflicts", "create a venv here with flask"),
              engine="deps", skill="devops-skills", fallback="skill"),
    SkillMode("news", "News", "Ask for a briefing or a topic.",
              ("daily briefing", "tech roundup", "latest news on AI regulation"),
              engine="news", fallback="engine"),
    SkillMode("voiceplus", "Voice+", "Type text to analyse its emotion, or ask about voice features.",
              ("analyze the emotion in: I'm worried about tomorrow's exam",),
              engine="voiceplus", fallback="engine"),
    SkillMode("gamedev", "Game Dev", "Describe the game or script.",
              ("scaffold a pygame platformer", "a Unity player movement script"),
              engine="gamedev", skill="game-dev-skills", fallback="skill"),
    SkillMode("blender", "Blender 3D", "Describe the 3D scene.",
              ("a low-poly house with lights", "a terrain with a sunset"),
              engine="blender", skill="3d-animation", fallback="engine"),
    SkillMode("media", "Media Edit", "Pick a video or photo; then say what to do.",
              ("trim the first 5 seconds", "apply a sepia filter", "resize to 1280x720"),
              engine="media", needs_file="media", skill="media-production-skills", fallback="engine"),
    SkillMode("scaler", "Auto Scaler", "Ask about workers, load or resources.",
              ("status", "system resources", "simulate load with 20 tasks"),
              engine="scaler", fallback="engine"),
    SkillMode("autoupdate", "Auto-Update", "Check for or apply TOM updates.",
              ("check for updates", "show update history"),
              engine="autoupdate", fallback="engine"),
)}

# Dashboard/quick-action labels → mode keys.
BY_LABEL: Dict[str, str] = {m.label: m.key for m in MODES.values()}


def tag(text: str, mode_key: str) -> str:
    return f"[[mode:{mode_key}]] {text}" if mode_key in MODES else text


def split(text: str) -> Tuple[str, Optional[SkillMode]]:
    """(text without the tag, the mode) — the mode is None for an untagged or unknown tag."""
    m = _TAG.match(text or "")
    if not m:
        return text, None
    return text[m.end():], MODES.get(m.group(1))


def compose(mode: SkillMode, user_text: str) -> str:
    """What the agent should read: the user's words, wrapped in the template when they are a bare topic."""
    text = (user_text or "").strip()
    if mode.template and text and not _STARTS_WITH_ACTION.match(text):
        return mode.template.format(text)
    return text
