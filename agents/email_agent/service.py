from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from tools.email_tools import EmailTools, classify_email_item as _classify_email_item_fn
from tools.instruction_loader import compose_system_prompt


def safe_print(message: str) -> None:
    print(message.encode("ascii", errors="ignore").decode("ascii"))


class EmailAgentService:
    """Standalone inbox triage loop with persisted state and history."""

    def __init__(self) -> None:
        self.provider = os.environ.get("EMAIL_PROVIDER", "gmail")
        self.max_count = int(os.environ.get("EMAIL_INBOX_MAX_COUNT", "10"))
        self.auto_reply_enabled = os.environ.get("EMAIL_AUTO_REPLY_ENABLED", "false").lower() == "true"
        self.check_interval_seconds = int(os.environ.get("EMAIL_CHECK_INTERVAL_SECONDS", "300"))
        self.reply_generation_timeout_seconds = int(os.environ.get("EMAIL_REPLY_TIMEOUT_SECONDS", "30"))
        self.open_important_in_client = os.environ.get("EMAIL_IMPORTANT_OPEN_IN_CLIENT", "true").lower() == "true"
        self.history_max_bytes = int(os.environ.get("EMAIL_AGENT_HISTORY_MAX_BYTES", str(2 * 1024 * 1024)))
        self.summary_max_chars = int(os.environ.get("EMAIL_AGENT_SUMMARY_MAX_CHARS", "420"))

        self.model_name = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.llm = None
        try:
            self.llm = ChatOllama(model=self.model_name, base_url=self.base_url, temperature=0.1)
        except Exception:
            self.llm = None

        self.email_tools = EmailTools()

        root_dir = Path(__file__).resolve().parents[2]
        log_dir = Path(os.environ.get("EMAIL_AGENT_STATE_DIR", str(root_dir / "tom_logs")))
        log_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = log_dir / "email_agent_state.json"
        self.pid_file = log_dir / "email_agent.pid"
        self.history_file = log_dir / "email_agent_history.jsonl"

    def write_pid_file(self, pid: int) -> None:
        self.pid_file.write_text(str(pid), encoding="utf-8")

    def remove_pid_file(self) -> None:
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
        except Exception:
            pass

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _next_run_at(self) -> str:
        return (datetime.now(timezone.utc) + timedelta(seconds=self.check_interval_seconds)).isoformat()

    def _read_state(self) -> Dict[str, Any]:
        try:
            if self.state_file.exists():
                return json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _write_state(self, payload: Dict[str, Any]) -> None:
        payload = dict(payload)
        payload.setdefault("agent_name", "email_agent")
        payload.setdefault("updated_at", self._now())
        temp_file = self.state_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        temp_file.replace(self.state_file)

    def _append_history(self, payload: Dict[str, Any]) -> None:
        try:
            self._trim_history_file()
            with self.history_file.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(self._history_record(payload), ensure_ascii=False) + "\n")
            self._trim_history_file()
        except Exception:
            pass

    def _extract_email_address(self, header_value: str) -> str:
        import re

        if not header_value:
            return ""

        match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", header_value)
        return match.group(0) if match else header_value.strip()

    def _classify_email_item(self, email_item: Dict[str, Any]) -> Dict[str, Any]:
        return _classify_email_item_fn(email_item)

    def _compact_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": result.get("status", "unknown"),
            "last_run_at": result.get("last_run_at"),
            "emails_reviewed": result.get("emails_reviewed", 0),
            "important_count": result.get("important_count", 0),
            "low_priority_count": result.get("low_priority_count", 0),
            "draft_reply_count": result.get("draft_reply_count", 0),
            "auto_replied_count": result.get("auto_replied_count", 0),
            "summary_lines": result.get("summary_lines", []),
        }

    def _short_text(self, value: Any, max_chars: int | None = None) -> str:
        text = " ".join(str(value or "").split())
        limit = max_chars or self.summary_max_chars
        return text[:limit] + "..." if len(text) > limit else text

    def _compact_email(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": item.get("id", ""),
            "sender": self._short_text(item.get("raw_sender") or item.get("sender"), 160),
            "subject": self._short_text(item.get("subject"), 180),
            "priority": item.get("priority", "unknown"),
            "needs_reply": bool(item.get("needs_reply", False)),
            "summary": self._short_text(item.get("summary")),
        }

    def _compact_draft(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        open_result = draft.get("open_result") or {}
        return {
            "recipient": self._short_text(draft.get("recipient"), 160),
            "subject": self._short_text(draft.get("subject"), 180),
            "status": draft.get("status", "unknown"),
            "priority": draft.get("priority", "unknown"),
            "approval_key": draft.get("approval_key", ""),
            "reply_body_preview": self._short_text(draft.get("reply_body") or draft.get("body"), 350),
            "open_status": open_result.get("status", "unknown"),
            "open_message": self._short_text(open_result.get("message"), 240),
        }

    def _history_record(self, result: Dict[str, Any]) -> Dict[str, Any]:
        compact = self._compact_result(result)
        compact.update(
            {
                "message": self._short_text(result.get("message"), 1200),
                "important_emails": [self._compact_email(item) for item in result.get("important_emails", [])[:10]],
                "low_priority_emails": [self._compact_email(item) for item in result.get("low_priority_emails", [])[:10]],
                "draft_replies": [self._compact_draft(item) for item in result.get("draft_replies", [])[:10]],
                "next_run_at": result.get("next_run_at"),
            }
        )
        return compact

    def _trim_history_file(self) -> None:
        try:
            if self.history_max_bytes <= 0 or not self.history_file.exists():
                return
            size = self.history_file.stat().st_size
            if size <= self.history_max_bytes:
                return
            keep_bytes = max(64 * 1024, self.history_max_bytes // 2)
            with self.history_file.open("rb") as handle:
                handle.seek(max(0, size - keep_bytes))
                data = handle.read()
            first_newline = data.find(b"\n")
            if first_newline > 0:
                data = data[first_newline + 1:]
            temp_file = self.history_file.with_suffix(".jsonl.tmp")
            temp_file.write_bytes(data)
            temp_file.replace(self.history_file)
        except Exception:
            pass

    def _important_key(self, analysis: Dict[str, Any]) -> str:
        message_id = str(analysis.get("id", "")).strip()
        if message_id:
            return message_id
        sender = str(analysis.get("sender", "")).strip().lower()
        subject = str(analysis.get("subject", "")).strip().lower()
        return f"{sender}|{subject}"

    async def _draft_reply_body(self, analysis: Dict[str, Any]) -> str:
        subject = analysis.get("subject", "No subject")
        sender = analysis.get("raw_sender", analysis.get("sender", "Unknown sender"))
        preview = analysis.get("summary", "")
        priority = analysis.get("priority", "normal")

        if not self.llm:
            return (
                "Thanks for the update. I reviewed your message and have noted it for follow-up. "
                "If anything needs immediate action, I will handle it next."
            )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    compose_system_prompt(
                        "You are a concise email assistant. Read the email context and draft a short, natural reply. "
                    "Do not mention that you are an AI. Keep the response polite, specific, and low-risk. "
                    "If the email is important, acknowledge it and note the next action. If it is spam or not important, "
                    "reply with a brief acknowledgment and safe summary. Return only the reply body.",
                        "email_agent",
                        include_ui=False,
                    ),
                ),
                (
                    "user",
                    "Subject: {subject}\nSender: {sender}\nPriority: {priority}\nContext: {preview}\n\nWrite the reply.",
                ),
            ]
        )

        chain = prompt | self.llm
        try:
            response = await asyncio.wait_for(
                chain.ainvoke(
                    {
                        "subject": subject,
                        "sender": sender,
                        "priority": priority,
                        "preview": preview,
                    }
                ),
                timeout=self.reply_generation_timeout_seconds,
            )
            content = str(getattr(response, "content", "")).strip()
            if content:
                return content
        except Exception:
            pass

        return (
            "Thanks for the update. I reviewed your message and have noted it for follow-up. "
            "If anything needs immediate action, I will handle it next."
        )

    def _store_result(self, result: Dict[str, Any]) -> None:
        state = self._read_state()
        recent_runs = list(state.get("recent_runs", []))
        recent_runs.insert(0, self._compact_result(result))
        recent_runs = recent_runs[:20]

        state.update(
            {
                "agent_name": "email_agent",
                "status": result.get("status", "unknown"),
                "provider": self.provider,
                "max_count": self.max_count,
                "auto_reply_enabled": self.auto_reply_enabled,
                "check_interval_seconds": self.check_interval_seconds,
                "last_run_at": result.get("last_run_at", self._now()),
                "next_run_at": result.get("next_run_at", self._next_run_at()),
                "emails_reviewed": result.get("emails_reviewed", 0),
                "important_count": result.get("important_count", 0),
                "low_priority_count": result.get("low_priority_count", 0),
                "draft_reply_count": result.get("draft_reply_count", 0),
                "auto_replied_count": result.get("auto_replied_count", 0),
                "summary_lines": result.get("summary_lines", []),
                "main_screen_items": result.get("main_screen_items", []),
                "pending_approval_replies": result.get("pending_approval_replies", []),
                "opened_important_keys": result.get("opened_important_keys", state.get("opened_important_keys", []))[-300:],
                "recent_runs": recent_runs,
                "message": result.get("message", ""),
            }
        )
        self._write_state(state)
        self._append_history(result)

    async def run_once(self) -> Dict[str, Any]:
        state_snapshot = self._read_state()
        opened_important_keys = set(state_snapshot.get("opened_important_keys", []))

        connect_result = await self.email_tools.connect_email_service(self.provider)
        if connect_result.get("status") != "success":
            result = {
                "status": "error",
                "message": connect_result.get("message", "Email connection failed"),
                "last_run_at": self._now(),
                "next_run_at": self._next_run_at(),
            }
            self._store_result(result)
            return result

        try:
            fetch_result = await self.email_tools.fetch_imap_emails("inbox", max_count=self.max_count)
            if fetch_result.get("status") != "success":
                result = {
                    "status": "error",
                    "message": fetch_result.get("message", "Email fetch failed"),
                    "last_run_at": self._now(),
                    "next_run_at": self._next_run_at(),
                }
                self._store_result(result)
                return result

            emails = fetch_result.get("emails", [])
            if not emails:
                result = {
                    "status": "success",
                    "message": "No inbox emails were found to triage.",
                    "emails_reviewed": 0,
                    "important_count": 0,
                    "low_priority_count": 0,
                    "draft_reply_count": 0,
                    "auto_replied_count": 0,
                    "summary_lines": ["Reviewed 0 emails.", "Important: 0.", "Spam: 0.", "Draft replies: 0.", "Auto-replied: 0."],
                    "main_screen_items": [],
                    "last_run_at": self._now(),
                    "next_run_at": self._next_run_at(),
                }
                self._store_result(result)
                return result

            important_emails: List[Dict[str, Any]] = []
            low_priority_emails: List[Dict[str, Any]] = []
            draft_replies: List[Dict[str, Any]] = []
            auto_replied: List[Dict[str, Any]] = []
            main_screen_items: List[Dict[str, Any]] = []
            pending_approval_replies: List[Dict[str, Any]] = []

            for email_item in emails:
                analysis = self._classify_email_item(email_item)
                if analysis["priority"] == "important":
                    important_emails.append(analysis)
                    main_screen_items.append(
                        {
                            "subject": analysis["subject"],
                            "sender": analysis["raw_sender"],
                            "summary": analysis["summary"],
                        }
                    )
                else:
                    low_priority_emails.append(analysis)

                if analysis["priority"] == "important" and analysis["needs_reply"]:
                    approval_key = self._important_key(analysis)
                    if approval_key in opened_important_keys:
                        continue
                    reply_body = await self._draft_reply_body(analysis)
                    if analysis["sender"]:
                        draft_result = await self.email_tools.draft_email(
                            analysis["sender"],
                            analysis["reply_subject"],
                            reply_body,
                        )
                        open_result = {"status": "skipped", "message": "Opening disabled"}
                        if self.open_important_in_client and approval_key not in opened_important_keys:
                            open_result = await self.email_tools.open_email_client_draft(
                                analysis["sender"],
                                analysis["reply_subject"],
                                (
                                    f"Original summary:\n{analysis.get('summary', '')}\n\n"
                                    f"Suggested reply:\n{reply_body}\n\n"
                                    "Please review and click Send if you approve this important reply."
                                ),
                            )
                            opened_important_keys.add(approval_key)

                        draft_result["reply_body"] = reply_body
                        draft_result["priority"] = "important"
                        draft_result["approval_key"] = approval_key
                        draft_result["open_result"] = open_result
                        draft_replies.append(draft_result)

                        pending_approval_replies.append(
                            {
                                "approval_key": approval_key,
                                "to": analysis["sender"],
                                "from": analysis.get("raw_sender", ""),
                                "subject": analysis["reply_subject"],
                                "original_subject": analysis.get("subject", ""),
                                "summary": analysis.get("summary", ""),
                                "reply_body_preview": reply_body[:350],
                                "open_status": open_result.get("status", "unknown"),
                                "open_message": open_result.get("message", ""),
                            }
                        )

            inbox_summary = [
                f"Reviewed {len(emails)} emails.",
                f"Important: {len(important_emails)}.",
                f"Spam: {len(low_priority_emails)}.",
                f"Draft replies: {len(draft_replies)}.",
                f"Auto-replied: {len(auto_replied)}." if self.auto_reply_enabled else "Auto-replied: 0 (disabled).",
            ]

            message_parts = ["\n".join(inbox_summary)]
            if important_emails:
                message_parts.append("\n--- IMPORTANT EMAILS ---")
                for index, email_info in enumerate(important_emails, 1):
                    message_parts.append(
                        f"\n{index}. From: {email_info.get('raw_sender', 'Unknown')}\n"
                        f"   Subject: {email_info.get('subject', 'No subject')}\n"
                        f"   Summary: {email_info.get('summary', 'N/A')}"
                    )

            if low_priority_emails:
                message_parts.append("\n--- SPAM / NOT IMPORTANT EMAILS ---")
                for index, email_info in enumerate(low_priority_emails, 1):
                    message_parts.append(
                        f"\n{index}. From: {email_info.get('raw_sender', 'Unknown')}\n"
                        f"   Subject: {email_info.get('subject', 'No subject')}\n"
                        f"   Summary: {email_info.get('summary', 'N/A')}"
                    )

            if draft_replies:
                message_parts.append("\n--- DRAFT REPLIES ---")
                for index, draft in enumerate(draft_replies, 1):
                    message_parts.append(
                        f"\n{index}. To: {draft.get('recipient', 'Unknown')}\n"
                        f"   Subject: {draft.get('subject', 'No subject')}"
                    )

            result = {
                "status": "success",
                "message": "\n".join(message_parts),
                "emails_reviewed": len(emails),
                "important_count": len(important_emails),
                "low_priority_count": len(low_priority_emails),
                "spam_count": len(low_priority_emails),
                "draft_reply_count": len(draft_replies),
                "auto_replied_count": len(auto_replied),
                "summary_lines": inbox_summary,
                "important_emails": important_emails,
                "low_priority_emails": low_priority_emails,
                "draft_replies": draft_replies,
                "pending_approval_replies": pending_approval_replies,
                "auto_replied": auto_replied,
                "main_screen_items": main_screen_items,
                "opened_important_keys": sorted(opened_important_keys),
                "last_run_at": self._now(),
                "next_run_at": self._next_run_at(),
            }
            self._store_result(result)

            safe_print("\nEMAIL TRIAGE SUMMARY")
            for line in inbox_summary:
                safe_print(f"- {line}")

            return result

        finally:
            await self.email_tools.close_email_connections()

    def summarize_state(self) -> Dict[str, Any]:
        state = self._read_state()
        if not state:
            return {
                "status": "idle",
                "running": self.pid_file.exists(),
                "message": "Email agent has not run yet.",
            }

        return {
            "status": state.get("status", "unknown"),
            "running": self.pid_file.exists(),
            "provider": state.get("provider", self.provider),
            "max_count": state.get("max_count", self.max_count),
            "auto_reply_enabled": state.get("auto_reply_enabled", self.auto_reply_enabled),
            "check_interval_seconds": state.get("check_interval_seconds", self.check_interval_seconds),
            "last_run_at": state.get("last_run_at"),
            "next_run_at": state.get("next_run_at"),
            "emails_reviewed": state.get("emails_reviewed", 0),
            "important_count": state.get("important_count", 0),
            "low_priority_count": state.get("low_priority_count", 0),
            "spam_count": state.get("spam_count", state.get("low_priority_count", 0)),
            "draft_reply_count": state.get("draft_reply_count", 0),
            "auto_replied_count": state.get("auto_replied_count", 0),
            "summary_lines": state.get("summary_lines", []),
            "main_screen_items": state.get("main_screen_items", []),
            "pending_approval_replies": state.get("pending_approval_replies", []),
            "recent_runs": state.get("recent_runs", []),
            "message": state.get("message", ""),
        }

    async def run_forever(self) -> None:
        self.write_pid_file(os.getpid())
        safe_print("EMAIL AGENT DAEMON STARTED")
        safe_print(f"Provider: {self.provider}")
        safe_print(f"Max count: {self.max_count}")
        safe_print(f"Auto reply enabled: {self.auto_reply_enabled}")
        safe_print(f"Check interval: {self.check_interval_seconds}s")

        try:
            while True:
                result = await self.run_once()
                if result.get("status") == "error":
                    safe_print(f"Email agent error: {result.get('message', 'Unknown error')}")
                await asyncio.sleep(self.check_interval_seconds)
        except asyncio.CancelledError:
            raise
        except KeyboardInterrupt:
            safe_print("Email agent stopping on keyboard interrupt.")
        finally:
            await self.email_tools.close_email_connections()
            self.remove_pid_file()
