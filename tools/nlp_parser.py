from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── spaCy-powered deep linguistic analysis ───────────────────────────────────

_nlp = None

def _get_nlp():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
        except Exception:
            _nlp = False
    return _nlp if _nlp else None


def deep_analyze(text: str) -> Dict[str, Any]:
    """
    Full linguistic analysis of a user message using spaCy.
    Returns tokens, POS tags, dependency parse, entities, and semantic roles.
    """
    nlp = _get_nlp()
    if not nlp:
        return {"available": False}

    doc = nlp(text)

    # ── Tokenization + POS tagging ────────────────────────────────────
    tokens = []
    for t in doc:
        tokens.append({
            "text": t.text, "lemma": t.lemma_, "pos": t.pos_,
            "tag": t.tag_, "dep": t.dep_, "head": t.head.text,
        })

    # ── Find the root verb (main action) ──────────────────────────────
    root_verb = None
    for t in doc:
        if t.dep_ == "ROOT":
            root_verb = {"text": t.text, "lemma": t.lemma_, "pos": t.pos_}
            break

    # ── Extract subject / direct object / indirect object ─────────────
    subjects = []
    direct_objects = []
    indirect_objects = []
    prepositions = {}

    for t in doc:
        if t.dep_ in ("nsubj", "nsubjpass"):
            subjects.append({"text": t.text, "lemma": t.lemma_,
                             "subtree": " ".join(c.text for c in t.subtree)})
        elif t.dep_ in ("dobj", "attr"):
            direct_objects.append({"text": t.text, "lemma": t.lemma_,
                                   "subtree": " ".join(c.text for c in t.subtree)})
        elif t.dep_ == "dative":
            indirect_objects.append({"text": t.text, "lemma": t.lemma_,
                                     "subtree": " ".join(c.text for c in t.subtree)})
        elif t.dep_ == "pobj":
            prep = t.head.text.lower()
            phrase = " ".join(c.text for c in t.subtree)
            prepositions[prep] = prepositions.get(prep, [])
            prepositions[prep].append(phrase)

    # ── Named Entity Recognition ──────────────────────────────────────
    entities = []
    for ent in doc.ents:
        entities.append({"text": ent.text, "label": ent.label_,
                         "description": _ent_description(ent.label_)})

    # ── Noun chunks (key phrases) ─────────────────────────────────────
    noun_chunks = [{"text": ch.text, "root": ch.root.text, "dep": ch.root.dep_}
                   for ch in doc.noun_chunks]

    # ── Sentence-level analysis ───────────────────────────────────────
    sentence_type = _classify_sentence(doc)

    # ── Action-target extraction ──────────────────────────────────────
    action = root_verb["lemma"] if root_verb else None
    target = None
    topic = None

    if direct_objects:
        target = direct_objects[0]["subtree"]
    if "about" in prepositions:
        topic = prepositions["about"][0]
    elif "on" in prepositions:
        topic = prepositions["on"][0]
    elif "for" in prepositions:
        topic = prepositions["for"][0]

    recipient = None
    if "to" in prepositions:
        recipient = prepositions["to"][0]
    for ent in entities:
        if ent["label"] == "PERSON" and not recipient:
            recipient = ent["text"]

    return {
        "available": True,
        "tokens": tokens,
        "root_verb": root_verb,
        "subjects": subjects,
        "direct_objects": direct_objects,
        "indirect_objects": indirect_objects,
        "prepositions": prepositions,
        "entities": entities,
        "noun_chunks": noun_chunks,
        "sentence_type": sentence_type,
        "action": action,
        "target": target,
        "topic": topic,
        "recipient": recipient,
    }


def _classify_sentence(doc) -> str:
    root = None
    for t in doc:
        if t.dep_ == "ROOT":
            root = t
            break
    if not root:
        return "unknown"
    if root.pos_ == "VERB" and root.tag_ in ("VB", "VBP"):
        return "imperative"
    has_subj = any(t.dep_ in ("nsubj", "nsubjpass") for t in doc)
    has_aux = any(t.dep_ == "aux" and t.tag_ in ("MD",) for t in doc)
    if doc.text.strip().endswith("?"):
        return "question"
    if has_aux and not has_subj:
        return "question"
    if root.pos_ == "VERB" and has_subj:
        return "declarative"
    if root.pos_ == "VERB":
        return "imperative"
    return "declarative"


def _ent_description(label: str) -> str:
    return {
        "PERSON": "Person name", "ORG": "Organization", "GPE": "Country/City/State",
        "LOC": "Location", "DATE": "Date", "TIME": "Time", "MONEY": "Money amount",
        "PERCENT": "Percentage", "PRODUCT": "Product", "EVENT": "Event",
        "WORK_OF_ART": "Title/Work", "LAW": "Law/Regulation", "LANGUAGE": "Language",
        "FAC": "Facility", "NORP": "Nationality/Group", "QUANTITY": "Quantity",
        "ORDINAL": "Ordinal number", "CARDINAL": "Number",
    }.get(label, label)

INTENTS = [
    "open_app", "write_email", "send_email", "whatsapp_message",
    "open_whatsapp", "create_word_doc", "create_excel", "create_presentation",
    "create_pdf", "create_file", "read_file", "data_analysis", "analyze_file",
    "web_search", "screen_read", "voice_mode", "instagram_workflow",
    "email_inbox", "build_agent", "schedule_task", "skill_task", "chat", "compound",
]

class CommandParser:
    DOMAIN_KEYWORDS = {
        "frontend": ("frontend", "react", "next.js", "website", "web app", "html", "css"),
        "backend": ("backend", "api", "server", "fastapi", "django", "flask"),
        "database": ("database", "sql", "postgres", "mysql", "sqlite", "mongodb"),
        "data science": ("data science", "statistics", "data analysis", "visualization"),
        "machine learning": ("machine learning", "ml model", "classification", "regression", "clustering"),
        "deep learning": ("deep learning", "neural network", "transformer"),
        "nlp": ("nlp", "natural language", "text classification", "sentiment"),
        "computer vision": ("computer vision", "image recognition", "object detection"),
        "mobile": ("mobile app", "android", "ios", "flutter", "react native"),
        "desktop": ("desktop app", "electron", "tauri", "tkinter", "windows app"),
        "devops": ("devops", "docker", "kubernetes", "ci/cd", "deployment"),
        "cybersecurity": ("cybersecurity", "security", "hacking", "ethical hacking", "pentest", "vulnerability"),
        "testing": ("testing", "test suite", "unit test", "e2e", "pytest"),
        "game": ("game", "pygame", "unity", "godot", "unreal"),
        "iot": ("iot", "esp32", "arduino", "mqtt", "sensor"),
        "vlsi": ("vlsi", "verilog", "rtl", "fpga"),
        "medical": ("medical", "health", "diagnosis", "clinical"),
        "media": ("media", "video editing", "audio", "podcast"),
        "excel": ("excel", "spreadsheet", "xlsx"),
        "word": ("word document", "docx"),
        "powerpoint": ("powerpoint", "presentation", "pptx", "slides"),
    }

    TASK_ACTIONS = (
        "build", "create", "make", "develop", "implement", "design", "debug",
        "fix", "review", "analyze", "analyse", "explain", "guide", "generate",
        "write", "test", "deploy",
    )

    _LLM_SYSTEM = """You are an expert NLU parser for TOM, a professional AI assistant.
Given a natural language command, extract structured data with MAXIMUM ACCURACY.

Return ONLY a valid JSON object (no markdown):

{
  "intent": "<one of: open_app|write_email|send_email|whatsapp_message|open_whatsapp|create_word_doc|create_excel|create_presentation|create_pdf|create_file|read_file|data_analysis|web_search|screen_read|voice_mode|instagram_workflow|email_inbox|build_agent|schedule_task|skill_task|chat|compound>",
  "app_name": "<app to open/use>",
  "app_action": "<what to do in the app: open|text|message|create|edit|delete|send|read|play|close>",
  "person_name": "<full name of any person mentioned>",
  "person_email": "<email if given, or infer from person name if known>",
  "recipient_name": "<who to send to - name only>",
  "email_address": "<explicit email address>",
  "file_name": "<filename.extension>",
  "file_type": "<docx|xlsx|pptx|pdf|py|html|css|js|txt|md>",
  "subject": "<topic/subject>",
  "message_body": "<full content/message to write or send>",
  "data_source": "<file path for analysis>",
  "search_topic": "<topic to research>",
  "context_summary": "<one sentence summarizing what user wants>",
  "urgency": "<low|medium|high>",
  "requires_data_from_internet": <true|false>,
  "skill_domain": "<domain skill needed, or null>",
  "requires_skill": <true|false>,
  "requires_tool": <true|false>,
  "confidence": <0.0 to 1.0>,
  "compound_tasks": [
    {
      "intent": "<intent>",
      "app_name": "<app>",
      "app_action": "<action>",
      "person_name": "<person>",
      "message_body": "<message>",
      "recipient_name": "<recipient>",
      "subject": "<subject>"
    }
  ]
}

CRITICAL RULES:
- If command has multiple steps joined by "and", "then", "after that", "also" — use intent "compound" and list each step in compound_tasks
- app_action describes WHAT TO DO in the app: "text" for sending texts, "open" for launching, "create" for making documents, "send" for sending, "read" for reading
- compound_tasks: if the command has multiple steps, list each as separate object
- person_name: extract ANY person name mentioned
- message_body: extract quoted text or text after "say", "text", "message"
- Be precise — extract real names, real messages, real app names
- If unsure about any field, use null — do NOT guess
"""

    def __init__(self, llm=None):
        self.llm = llm

    def parse(self, command: str) -> Dict[str, Any]:
        # ── Deep linguistic analysis first ──
        analysis = deep_analyze(command)
        skill_domain = self._extract_skill_domain(command)
        intent = self._detect_intent(command)
        whatsapp_details = self._extract_whatsapp_details(command)

        result = {
            "raw": command,
            "intent": intent,
            "app_name": "whatsapp" if whatsapp_details else self._extract_app_name(command),
            "app_action": "send" if whatsapp_details else self._extract_app_action(command),
            "person_name": whatsapp_details.get("contact") if whatsapp_details else self._extract_person_name(command),
            "person_email": self._extract_email(command),
            "recipient_name": whatsapp_details.get("contact") if whatsapp_details else self._extract_recipient(command),
            "email_address": self._extract_email(command),
            "file_name": self._extract_filename(command),
            "file_type": self._extract_file_type(command),
            "subject": self._extract_subject(command),
            "message_body": whatsapp_details.get("message") if whatsapp_details else self._extract_message_body(command),
            "data_source": self._extract_data_source(command),
            "search_topic": self._extract_search_topic(command),
            "context_summary": self._summarize_context(command),
            "urgency": self._detect_urgency(command),
            "requires_data_from_internet": self._needs_internet(command),
            "skill_domain": skill_domain,
            "requires_skill": bool(skill_domain),
            "requires_tool": intent not in ("chat", "skill_task") or bool(skill_domain),
            "confidence": self._confidence(command, intent, skill_domain),
            "compound_tasks": self._extract_compound_tasks(command),
        }

        # ── Enrich with spaCy deep analysis ──
        if analysis.get("available"):
            if not result["person_name"] and analysis.get("recipient"):
                for ent in analysis["entities"]:
                    if ent["label"] == "PERSON":
                        result["person_name"] = ent["text"]
                        break
            if not result["recipient_name"] and analysis.get("recipient"):
                result["recipient_name"] = analysis["recipient"]
            if not result["subject"] and analysis.get("topic"):
                result["subject"] = analysis["topic"]
            if not result["search_topic"] and analysis.get("topic"):
                result["search_topic"] = analysis["topic"]
            if not result["app_action"] and analysis.get("action"):
                result["app_action"] = analysis["action"]

            result["nlp_analysis"] = {
                "action": analysis.get("action"),
                "target": analysis.get("target"),
                "topic": analysis.get("topic"),
                "recipient": analysis.get("recipient"),
                "sentence_type": analysis.get("sentence_type"),
                "entities": analysis.get("entities", []),
                "noun_chunks": [c["text"] for c in analysis.get("noun_chunks", [])],
            }

        return result

    async def parse_with_llm(self, command: str) -> Dict[str, Any]:
        # Always run deep linguistic analysis first
        analysis = deep_analyze(command)
        fallback = self.parse(command)

        if not self.llm:
            return fallback

        # Skip expensive LLM parse for simple chat — regex is sufficient
        if fallback.get("intent") == "chat" and len(command.split()) <= 12:
            return fallback

        from langchain_core.messages import SystemMessage, HumanMessage
        try:
            # Feed spaCy analysis into the LLM prompt for better understanding
            nlp_hint = ""
            if analysis.get("available"):
                parts = []
                if analysis.get("action"):
                    parts.append(f"Main verb: {analysis['action']}")
                if analysis.get("target"):
                    parts.append(f"Object: {analysis['target']}")
                if analysis.get("topic"):
                    parts.append(f"Topic: {analysis['topic']}")
                if analysis.get("recipient"):
                    parts.append(f"Recipient: {analysis['recipient']}")
                if analysis.get("entities"):
                    ent_str = ", ".join(f"{e['text']} ({e['description']})" for e in analysis["entities"])
                    parts.append(f"Entities: {ent_str}")
                if analysis.get("sentence_type"):
                    parts.append(f"Sentence type: {analysis['sentence_type']}")
                if parts:
                    nlp_hint = "\n\nLinguistic analysis: " + " | ".join(parts)

            messages = [
                SystemMessage(content=self._LLM_SYSTEM),
                HumanMessage(content=f"Command: {command}{nlp_hint}"),
            ]
            resp = await self.llm.ainvoke(messages)
            content = resp.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            parsed: Dict[str, Any] = json.loads(content)
            parsed["raw"] = command

            for key in ["intent", "app_name", "app_action", "person_name", "recipient_name",
                        "email_address", "file_name", "file_type", "subject", "message_body"]:
                if key not in parsed or parsed.get(key) in (None, "", "null"):
                    parsed[key] = fallback.get(key)

            if not parsed.get("compound_tasks"):
                parsed["compound_tasks"] = fallback.get("compound_tasks", [])

            # Attach deep analysis
            if analysis.get("available"):
                parsed["nlp_analysis"] = fallback.get("nlp_analysis", {})

            return parsed
        except Exception as exc:
            logger.warning("LLM parse failed (%s), using regex fallback.", exc)
            return fallback

    def _extract_whatsapp_details(self, command: str) -> Dict[str, str]:
        text = (command or "").strip()
        if "User request:" in text:
            text = text.rsplit("User request:", 1)[1].strip()
        if not re.search(r'\bwhats\s*app\b', text, re.IGNORECASE):
            return {}

        clean = re.sub(r'\s+', ' ', text).strip().strip(".,")
        clean = re.sub(
            r'^(?:open|launch|start)\s+whats\s*app\s+(?:and\s+)?',
            '',
            clean,
            flags=re.IGNORECASE,
        ).strip()

        patterns = [
            # send hello to Madhu on WhatsApp
            r'^(?:send|text|message|tell|write|say)\s+(.+?)\s+to\s+(.+?)(?:\s+(?:on|via|through|using)\s+whats\s*app)?$',
            # send to Madhu hello
            r'^(?:send|text|message|tell|write|say)\s+to\s+(.+?)\s+(.+?)$',
            # WhatsApp Madhu saying hello
            r'^(?:whats\s*app\s+)?(.+?)\s+(?:saying|say|text|message|tell)\s+(.+?)$',
            # text Madhu hello / open WhatsApp and text Madhu hello
            r'^(?:send|text|message|tell|write|say)\s+([A-Za-z][A-Za-z0-9_. -]{1,60}?)\s+(.+?)$',
        ]

        for idx, pattern in enumerate(patterns):
            match = re.search(pattern, clean, re.IGNORECASE)
            if not match:
                continue

            first = match.group(1).strip().strip(".,")
            second = match.group(2).strip().strip(".,")
            if idx == 0:
                message, contact = first, second
            else:
                contact, message = first, second

            contact = re.sub(r'\s+(?:on|via|through|using)\s+whats\s*app$', '', contact, flags=re.IGNORECASE).strip()
            message = re.sub(r'\s+(?:on|via|through|using)\s+whats\s*app$', '', message, flags=re.IGNORECASE).strip()
            if contact and message and contact.lower() not in {"whatsapp", "whats app"}:
                return {"contact": contact, "message": message}

        return {}

    def _detect_intent(self, command: str) -> str:
        c = command.lower()

        compound_delimiters = [
            r'\b(?:and\s+then|and\s+also|then\s+also)\b',
            r'\b(?:open\s+\w+\s+and\s+(?:send|text|message|create|write))\b',
            r'\b(?:text|message|send)\s+\w+\s+(?:on|via|through|using)\s+\w+\b',
        ]
        if any(re.search(p, c) for p in compound_delimiters):
            pass

        if "instagram" in c:
            return "instagram_workflow"

        if any(x in c for x in ("voice mode", "talk to me", "let's talk", "hey tom", "voice chat", "talk")):
            return "voice_mode"

        if any(x in c for x in ("read screen", "what's on screen", "analyze screen", "scan screen")):
            return "screen_read"

        # File/image analysis — must be before create_* intents
        if re.search(r'\.(?:csv|xlsx|xls|json|xml|db|sqlite)\b', c) and any(
                x in c for x in ("analyze", "analyse", "analysis", "chart", "graph", "plot",
                                  "visualize", "visualise", "statistics", "dashboard", "pivot")):
            return "data_analysis"

        _file_analysis_triggers = ("analyze image", "analyse image", "analyze photo",
                                   "analyze picture", "analyze this image", "what is in this",
                                   "describe this image", "analyze file", "analyse file",
                                   "analyze this file", "analyze the file", "analyze document",
                                   "what does this file", "read this image", "analyze this photo",
                                   "what's in this image", "what is this image", "look at this")
        _file_exts = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg",
                      ".pdf", ".docx", ".xlsx", ".pptx", ".csv", ".mp4", ".mp3")
        if any(x in c for x in _file_analysis_triggers):
            return "analyze_file"
        if any(ext in c for ext in _file_exts) and any(
                x in c for x in ("analyze", "analyse", "describe", "what is", "explain",
                                  "summarize", "summarise", "inspect", "review")):
            if not any(x in c for x in ("data", "chart", "graph", "plot", "statistics", "visualize")):
                return "analyze_file"

        if any(x in c for x in ("build agent", "create agent", "make agent")):
            return "build_agent"

        if any(x in c for x in ("inbox", "triage", "check email", "review email", "summarize email", "unread")):
            return "email_inbox"

        if any(x in c for x in ("send email", "send the email", "email now", "send this email")):
            return "send_email"

        if any(x in c for x in ("write email", "draft email", "compose email", "email to", "write a mail",
                                  "write mail", "write letter", "cover letter", "resignation",
                                  "recommendation letter", "draft a letter")):
            if any(x in c for x in ("@", "mail to", "send to")):
                return "write_email"
            if any(x in c for x in ("boss", "manager", "hr", "team", "company")):
                if re.search(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', command):
                    return "write_email"
                return "create_word_doc"
            return "write_email"

        if "whatsapp" in c or "whats app" in c:
            if any(x in c for x in ("send", "message", "text", "tell", "say", "wish")):
                return "whatsapp_message"
            return "open_whatsapp"

        if any(x in c for x in ("presentation", "slide deck", "slideshow", "ppt", "powerpoint")):
            return "create_presentation"

        if any(x in c for x in ("word document", "word doc", ".docx", "write a report", "write report",
                                  "write a document", "create document", "letter", "resume", "cv")):
            return "create_word_doc"

        if any(x in c for x in ("excel", "spreadsheet", ".xlsx", "create a table", "budget",
                                  "invoice", "tracker", "data entry")):
            return "create_excel"

        if any(x in c for x in ("pdf report", "create pdf", "generate pdf", "make pdf", ".pdf")):
            return "create_pdf"

        if (self._extract_skill_domain(command)
                and not self._extract_data_source(command)
                and any(action in c for action in self.TASK_ACTIONS)):
            return "skill_task"

        if any(x in c for x in ("analyze", "analyse", "analysis", "chart", "graph", "plot",
                                  "visualize", "visualise", "power bi", "powerbi", "data report",
                                  "insights", "statistics", "dashboard", "pivot")):
            return "data_analysis"

        if any(x in c for x in ("create file", "write code", "write a python", "write a script",
                                  ".py", ".html", ".css", ".js", ".tsx", ".jsx")):
            return "create_file"

        if any(x in c for x in ("read file", "show me", "open file", "display file")):
            return "read_file"

        if any(x in c for x in ("search for", "search the web", "look up", "find information about",
                                  "research", "google", "find on the internet")):
            return "web_search"

        if any(x in c for x in ("open ", "launch ", "start ")):
            remaining = re.sub(r'^(open|launch|start)\s+', '', c).strip()
            if remaining and not any(x in remaining for x in ("a ", "an ", "the task", "the process")):
                return "open_app"

        return "chat"

    def _extract_skill_domain(self, command: str) -> Optional[str]:
        c = command.lower()
        if "react native" in c or "mobile app" in c:
            return "mobile"
        if "ethical hacking" in c or "hacking" in c:
            return "cybersecurity"
        if "full stack" in c or "full-stack" in c or "api routes" in c or "authentication" in c:
            return "backend"
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            for keyword in keywords:
                if re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", c):
                    return domain
        return None

    def _confidence(self, command: str, intent: str, skill_domain: Optional[str]) -> float:
        c = command.lower()
        score = 0.45
        if intent != "chat":
            score += 0.25
        if skill_domain:
            score += 0.2
        if any(action in c for action in self.TASK_ACTIONS):
            score += 0.1
        return round(min(score, 0.98), 2)

    def _detect_compound(self, command: str) -> bool:
        c = command.lower()
        patterns = [
            r'\b(?:open|launch|start)\s+\w+\s+and\s+(?:send|text|message|create|write|open)\b',
            r'\b(?:send|text|message)\s+\w+\s+(?:on|via|through|using)\s+\w+\b',
            r'\b(?:create|make|build)\s+\w+\s+and\s+(?:send|open|save|share)\b',
        ]
        return any(re.search(p, c) for p in patterns)

    def _extract_compound_tasks(self, command: str) -> List[Dict[str, Any]]:
        c = command.lower()
        tasks = []

        whatsapp_details = self._extract_whatsapp_details(command)
        if whatsapp_details:
            return [{
                "intent": "whatsapp_message",
                "app_name": "whatsapp",
                "app_action": "send",
                "person_name": whatsapp_details["contact"],
                "recipient_name": whatsapp_details["contact"],
                "message_body": whatsapp_details["message"],
            }]

        if not self._detect_compound(command):
            return tasks

        patterns = [
            r'(?:open|launch|start)\s+(\w+(?:\s+\w+)?)\s+and\s+(?:send|text|message)\s+(\w+)\s+(.+?)$',
            r'(?:send|text|message)\s+(\w+)\s+(.+?)\s+(?:on|via|through|using)\s+(\w+(?:\s+\w+)?)',
            r'(?:open|launch|start)\s+(\w+(?:\s+\w+)?)\s+and\s+(?:then\s+)?(create|make|write)\s+(.+?)$',
        ]

        for p in patterns:
            m = re.search(p, command, re.IGNORECASE)
            if m:
                groups = m.groups()
                if len(groups) >= 2:
                    if 'text' in p or 'message' in p.lower():
                        if len(groups) == 3:
                            app, person, msg = groups
                            tasks.append({
                                "intent": "open_app",
                                "app_name": app.strip(),
                                "app_action": "open",
                            })
                            tasks.append({
                                "intent": "whatsapp_message",
                                "app_name": app.strip(),
                                "app_action": "text",
                                "person_name": person.strip(),
                                "message_body": msg.strip(),
                            })
                    elif 'send' in p.lower() and 'via' in p.lower() or 'on' in p.lower():
                        person = groups[0]
                        msg = groups[1]
                        app = groups[2] if len(groups) > 2 else ""
                        if 'whatsapp' in app.lower():
                            tasks.append({
                                "intent": "whatsapp_message",
                                "app_name": "whatsapp",
                                "app_action": "text",
                                "person_name": person.strip(),
                                "message_body": msg.strip(),
                            })
                break

        return tasks

    def _extract_app_action(self, command: str) -> Optional[str]:
        c = command.lower()
        if any(x in c for x in ("text ", "message ", "say ", "tell ", "wish ")):
            return "text"
        if any(x in c for x in ("send ", "send a ", "send an ")):
            return "send"
        if any(x in c for x in ("create ", "make ", "build ", "generate ")):
            return "create"
        if any(x in c for x in ("open ", "launch ", "start ", "run ")):
            return "open"
        if any(x in c for x in ("read ", "show ", "display ")):
            return "read"
        if any(x in c for x in ("edit ", "modify ", "change ", "update ")):
            return "edit"
        if any(x in c for x in ("delete ", "remove ", "erase ")):
            return "delete"
        if any(x in c for x in ("close ", "exit ", "quit ")):
            return "close"
        if any(x in c for x in ("play ", "listen ", "watch ")):
            return "play"
        return None

    def _extract_app_name(self, command: str) -> Optional[str]:
        patterns = [
            r'(?:open|launch|start|run)\s+([a-zA-Z][a-zA-Z0-9\s]{1,25}?)(?:\s+(?:with|app|application|program|profile|browser|for\b|and\b|to\b)|$)',
            r'(?:using|use|via)\s+([a-zA-Z][a-zA-Z0-9\s]{1,20}?)(?:\s+(?:to|for|and)|$)',
            r'(?:in|on|with)\s+(excel|powerpoint|word|outlook|chrome|firefox|brave|edge|vlc|spotify|notepad|paint|calculator|whatsapp|telegram|discord|slack|zoom|teams|visual studio code|vs code|vscode)',
            r'(?:text|message|send)\s+\w+\s+(?:on|via|through|using)\s+(\w+(?:\s+\w+)?)',
            r'(?:on|via|through|using)\s+(whatsapp|telegram|discord|slack|email|sms|signal)',
        ]
        for p in patterns:
            m = re.search(p, command, re.IGNORECASE)
            if m:
                name = m.group(1).strip().lower()
                if name not in ("a", "an", "the", "my", "file", "task", "agent", "report", "and", "to", "for", "with"):
                    return name
        return None

    def _extract_person_name(self, command: str) -> Optional[str]:
        patterns = [
            r'(?:send|text|message|tell|call|contact|email|mail)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)(?:\s|$)',
            r'(?:to|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'(?:dear|hi|hello|hey)\s+([A-Z][a-z]+)',
            r'\b(?:rajesh|john|sarah|mike|alex|emma|david|boss|manager|hr|teacher|professor|doctor|dr\.)\b',
            r'(?:about|regarding|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:project|task|report)',
        ]
        seen = set()
        for p in patterns:
            m = re.search(p, command, re.IGNORECASE)
            if m:
                candidate = m.group(1) if m.lastindex else m.group(0)
                candidate = candidate.strip()
                if len(candidate) >= 2 and candidate.lower() not in ("the", "a", "an", "my", "your",
                    "with", "for", "and", "but", "not", "are", "was", "were", "has", "had",
                    "on", "via", "through", "using", "by", "from", "to"):
                    if candidate.lower() not in seen:
                        seen.add(candidate.lower())
                        return candidate
        return None

    def _extract_message_body(self, command: str) -> Optional[str]:
        patterns = [
            r'(?:say|text|message|tell|write|type)\s+(?:\w+\s+)?["\u201C\u201D](.+?)["\u201C\u201D]',
            r'(?:say|text|message|tell|write|type)\s+(.+?)(?:\s+(?:on|via|through|using|in|to|for|and|then)\b|$)',
            r'["\u201C\u201D](.+?)["\u201C\u201D]',
        ]
        for p in patterns:
            m = re.search(p, command, re.IGNORECASE)
            if m:
                msg = m.group(1).strip().rstrip(".,!?")
                if 2 < len(msg) < 500:
                    return msg
        return None

    def _extract_email(self, command: str) -> Optional[str]:
        m = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', command)
        return m.group(0) if m else None

    def _extract_recipient(self, command: str) -> Optional[str]:
        email = self._extract_email(command)
        if email:
            return email
        name = self._extract_person_name(command)
        if name:
            return name
        patterns = [
            r'(?:to|send\s+to|email\s+to|mail\s+to|message\s+to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        ]
        for p in patterns:
            m = re.search(p, command)
            if m:
                return m.group(1).strip()
        return None

    def _extract_filename(self, command: str) -> Optional[str]:
        m = re.search(
            r'\b([a-zA-Z0-9_\-]+\.(?:py|html|css|js|json|txt|md|docx|xlsx|pptx|pdf|csv|xml|tsx|jsx|ts))\b',
            command, re.IGNORECASE,
        )
        return m.group(1) if m else None

    def _extract_file_type(self, command: str) -> Optional[str]:
        c = command.lower()
        for ft in ["pptx", "docx", "xlsx", "pdf", "html", "css", "json", "py", "js", "tsx", "ts", "txt", "md", "csv"]:
            if f".{ft}" in c or re.search(rf'\b{ft}\b', c):
                return ft
        if any(x in c for x in ("word", "document", "letter", "report", "essay", "article", "resume", "cv")):
            return "docx"
        if any(x in c for x in ("excel", "spreadsheet", "budget", "invoice", "tracker", "pivot")):
            return "xlsx"
        if any(x in c for x in ("powerpoint", "presentation", "slides", "slide deck", "ppt")):
            return "pptx"
        if "pdf" in c:
            return "pdf"
        if any(x in c for x in ("python", "script", "code")):
            return "py"
        if "html" in c or "webpage" in c or "website" in c:
            return "html"
        return None

    def _extract_subject(self, command: str) -> Optional[str]:
        patterns = [
            r'(?:about|regarding|on the topic of|on|titled|called|named)\s+["\']?(.+?)["\']?(?:\s+(?:to|for|from|with|using|and|in|at)\b|$)',
            r'(?:presentation|report|letter|email|document|analysis)\s+(?:about|on|for|regarding)\s+(.+?)(?:\s+(?:to|for|from|with)\b|$)',
            r'(?:prepare|create|make|write|generate|build)\s+(?:a|an|the)?\s*(?:\w+\s+){0,3}(?:about|on|for)\s+(.+?)(?:\s+(?:to|for|from)\b|$)',
        ]
        for p in patterns:
            m = re.search(p, command, re.IGNORECASE)
            if m:
                subject = m.group(1).strip().rstrip(".,!?")
                if 2 < len(subject) < 120:
                    return subject
        return None

    def _extract_data_source(self, command: str) -> Optional[str]:
        m = re.search(
            r'\b([a-zA-Z0-9_\-/\\\.]+\.(?:csv|xlsx|xls|json|xml|txt|db|sqlite))\b',
            command, re.IGNORECASE,
        )
        return m.group(1) if m else None

    def _extract_search_topic(self, command: str) -> Optional[str]:
        patterns = [
            r'(?:research|search for|find information (?:about|on)|look up)\s+(.+?)(?:\s+(?:for|and|with)\b|$)',
            r'(?:from|using|with)\s+(?:the\s+)?internet\s+(?:about|on)?\s*(.+?)(?:\s+(?:for|and)\b|$)',
            r'(?:get\s+content\s+from\s+internet\s+(?:about|on))\s+(.+?)$',
        ]
        for p in patterns:
            m = re.search(p, command, re.IGNORECASE)
            if m:
                topic = m.group(1).strip().rstrip(".,!?")
                if 2 < len(topic) < 120:
                    return topic
        intent = self._detect_intent(command)
        if intent in ("create_presentation", "data_analysis", "create_pdf", "create_word_doc"):
            return self._extract_subject(command)
        return None

    def _summarize_context(self, command: str) -> str:
        c = command.lower()
        if len(command) < 10:
            return command
        intent = self._detect_intent(command)
        person = self._extract_person_name(command)
        subject = self._extract_subject(command)
        parts = [f"User wants to {intent.replace('_', ' ')}"]
        if person:
            parts.append(f"regarding {person}")
        if subject:
            parts.append(f"about {subject}")
        return " - ".join(parts)

    def _detect_urgency(self, command: str) -> str:
        c = command.lower()
        if any(x in c for x in ("urgent", "asap", "immediately", "right now", "quick", "fast", "hurry")):
            return "high"
        if any(x in c for x in ("soon", "today", "this week", "when you can", "please")):
            return "medium"
        return "low"

    def _needs_internet(self, command: str) -> bool:
        c = command.lower()
        if any(x in c for x in ("search", "research", "look up", "find information", "google",
                                  "from the internet", "web search", "browse", "find on the web")):
            return True
        intent = self._detect_intent(command)
        if intent in ("create_presentation", "create_word_doc", "create_pdf"):
            subject = self._extract_subject(command)
            if subject and ("from internet" in c or "research" in c or "find content" in c):
                return True
        return False
