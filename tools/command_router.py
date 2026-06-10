from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(slots=True)
class RouteDecision:
    category: str
    intent: str
    handler: str
    needs_approval: bool = False
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)


class CommandRouter:
    """Heuristic command router for TOM.

    This keeps fast local actions off the LLM path when possible and captures
    enough metadata for browser/profile-specific tasks.

    Rules are evaluated top-to-bottom and the first match wins. The order is
    deliberate: specific automation/communication/content routes are checked
    before generic "open app / browser" routes, and the broad "sensitive
    action" gate is checked LAST so it cannot shadow a concrete handler.
    """

    def route(self, command: str) -> RouteDecision:
        text = (command or "").strip()
        if "User request:" in text:
            text = text.rsplit("User request:", 1)[1].strip()
        lower = text.lower()

        if not lower:
            return RouteDecision("chat", "empty", "generate_chat_response", confidence=1.0)

        # Automation / agent intents
        if self._is_build_agent_request(lower):
            return RouteDecision("automation", "build_agent", "build_agent", confidence=0.95)

        if self._is_instagram_request(lower):
            return RouteDecision(
                "automation", "instagram_workflow", "execute_instagram_workflow",
                metadata={}, confidence=0.93,
            )

        if self._is_agent_daemon_command(lower):
            return RouteDecision("automation", "manage_agent", "manage_agent_daemon", confidence=0.95)

        # Communication
        if self._is_email_inbox_request(lower):
            return RouteDecision(
                "communication", "email_inbox_workflow", "execute_email_inbox_workflow",
                confidence=0.94,
            )

        if any(token in lower for token in ("send email", "send the email", "email now")):
            return RouteDecision(
                "sensitive", "send_email", "execute_email_send",
                needs_approval=True, confidence=0.95,
            )

        if any(token in lower for token in ("write email", "draft email", "email to", "mail to")):
            return RouteDecision("communication", "draft_email", "execute_email_task", confidence=0.92)

        if "whatsapp" in lower or "whats app" in lower:
            if any(act in lower for act in ("send", "text", "message", "tell", "write to", "say")):
                return RouteDecision(
                    "communication", "whatsapp_message", "execute_whatsapp_task",
                    needs_approval=True, confidence=0.92,
                )
            if any(act in lower for act in ("open", "launch", "start")):
                return RouteDecision("communication", "open_whatsapp", "execute_open_whatsapp", confidence=0.93)

        # Content creation
        if any(token in lower for token in ("create website", "make website")):
            return RouteDecision("content", "create_website", "execute_website_creation", confidence=0.9)

        if any(token in lower for token in ("presentation", "pptx", "slide", "slides", "powerpoint presentation")):
            if any(act in lower for act in ("create", "make", "build", "generate", "design")):
                return RouteDecision("content", "create_presentation", "execute_presentation_task", confidence=0.88)

        if any(token in lower for token in ("create excel", "make excel", "excel spreadsheet", "spreadsheet",
                                             "budget tracker", "invoice tracker", "data tracker")):
            return RouteDecision("content", "create_excel", "execute_excel_task", confidence=0.88)

        if any(token in lower for token in ("word document", "word doc", "create document", "write document",
                                             "write report", "create report")):
            return RouteDecision("content", "create_word_doc", "execute_word_task", confidence=0.90)

        if any(token in lower for token in ("write letter", "draft letter", "write a letter", "create letter",
                                             "resignation letter", "cover letter", "recommendation letter")):
            return RouteDecision("content", "write_document", "execute_document_writing", confidence=0.90)

        if any(token in lower for token in ("ethical hacking", "hacking", "pentest", "cybersecurity")):
            if not any(act in lower for act in ("build", "create", "make", "develop", "implement")):
                return RouteDecision("chat", "general_chat", "generate_chat_response", confidence=0.72)

        if any(token in lower for token in ("build app", "build application", "create app", "create project",
                                             "make app", "android app", "ios app", "desktop app",
                                             "web app", "mobile app", "react app", "flutter app",
                                             "full stack", "full-stack", "api routes", "authentication")):
            return RouteDecision("content", "create_project", "execute_code_project", confidence=0.88)

        # Data / web search / files
        if any(token in lower for token in ("analyze data", "data analysis", "analyze csv", "analyze excel",
                                             "chart", "plot", "graph", "visualization", "visualize", "statistics")):
            return RouteDecision("data", "data_analysis", "execute_data_analysis", confidence=0.88)

        if any(token in lower for token in ("search for", "search the web", "look up", "research",
                                             "find information", "google", "web search")):
            return RouteDecision("data", "web_search", "execute_web_search", confidence=0.88)

        if any(token in lower for token in ("write code", "create file", "read file", "show me")):
            return RouteDecision("files", "file_operation", "execute_file_or_read", confidence=0.88)

        # Screen
        if any(token in lower for token in ("read screen", "analyze screen", "what is on screen",
                                             "what's on screen", "scan screen", "inspect screen")):
            return RouteDecision("screen", "read_screen", "execute_screen_read", confidence=0.93)

        # Open application / browser
        if self._is_chrome_profile_open(lower):
            return RouteDecision(
                "browser", "open_chrome_profile", "execute_open_command",
                metadata={"profile_query": self._extract_profile_query(text)}, confidence=0.95,
            )

        if any(token in lower for token in ("power bi", "excel", "word", "powerpoint", "canva",
                                             "notepad", "calculator", "paint", "vlc", "spotify",
                                             "telegram", "discord", "slack", "zoom", "teams",
                                             "visual studio", "vscode", "vs code", "obs",
                                             "firefox", "brave", "opera")):
            return RouteDecision("desktop", "office_or_design", "execute_open_command", confidence=0.82)

        if self._is_browser_open(lower):
            return RouteDecision("browser", "open_website_or_app", "execute_open_command", confidence=0.9)

        # Generic sensitive actions (delete/remove/share/publish/...), checked LAST.
        if self._looks_sensitive(lower):
            return RouteDecision(
                "sensitive", self._sensitive_intent(lower), "approval_gate",
                needs_approval=True, confidence=0.9,
            )

        return RouteDecision("chat", "general_chat", "generate_chat_response", confidence=0.5)

    def _is_build_agent_request(self, lower: str) -> bool:
        return any(pattern in lower for pattern in ("build agent", "create agent", "make agent", "agent that", "build an agent"))

    def _is_instagram_request(self, lower: str) -> bool:
        instagram_keywords = ("instagram", "insta", "ig news", "ai news", "news report")
        return any(keyword in lower for keyword in instagram_keywords) and any(
            action in lower for action in ("scroll", "report", "email", "send", "summarize", "extract", "check")
        )

    def _is_email_inbox_request(self, lower: str) -> bool:
        inbox_tokens = (
            "inbox", "triage", "review emails", "review email", "check emails", "check email",
            "summarize emails", "summarize email", "email summary", "mail summary",
            "unread emails", "unread mail",
        )
        action_tokens = ("summarize", "review", "check", "scan", "sort", "prioritize", "important", "latest")
        if any(token in lower for token in inbox_tokens):
            return True
        return ("email" in lower or "mail" in lower) and any(token in lower for token in action_tokens)

    def _looks_sensitive(self, lower: str) -> bool:
        sensitive_terms = ("delete ", "remove ", "send email", "post to", "publish", "share", "transfer")
        return any(term in lower for term in sensitive_terms)

    def _sensitive_intent(self, lower: str) -> str:
        if "delete" in lower or "remove" in lower:
            return "delete_or_remove"
        if "email" in lower:
            return "send_email"
        return "sensitive_action"

    def _is_browser_open(self, lower: str) -> bool:
        return any(term in lower for term in ("open ", "launch ", "go to ", "visit ", "browse "))

    def _is_chrome_profile_open(self, lower: str) -> bool:
        return "chrome" in lower and "profile" in lower and self._is_browser_open(lower)

    def _is_agent_daemon_command(self, lower: str) -> bool:
        agent_names = ("email agent", "instagram agent")
        actions = ("start", "stop", "status", "restart")
        return any(name in lower for name in agent_names) and any(act in lower for act in actions)

    def _extract_profile_query(self, command: str) -> str:
        patterns = [
            r"profile\s+(?:named|called|for|of)?\s*([a-zA-Z0-9_\- ]+)",
            r"(?:with\s+)?([a-zA-Z0-9_\- ]+)\s+profile",
        ]
        for pattern in patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                return match.group(1).strip().strip(". ,")
        return ""
