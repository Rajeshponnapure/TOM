import asyncio
import os
import subprocess
from email.header import decode_header, make_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Any, Dict, List, Optional

import smtplib
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from imapclient import IMAPClient
from tools.project_paths import project_path_str

load_dotenv()


def safe_print(message: str):
    print(message.encode("ascii", errors="ignore").decode("ascii"))


def _decode_mime_header(value: str) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value))).strip()
    except Exception:
        return value.strip()


def classify_email_item(email_item: Dict[str, Any]) -> Dict[str, Any]:
    """Classify a single email dict into priority/reply metadata."""
    import re as _re

    def _extract_address(header_value: str) -> str:
        if not header_value:
            return ""
        match = _re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", header_value)
        return match.group(0) if match else header_value.strip()

    subject = _decode_mime_header(str(email_item.get("subject", "")).strip())
    sender = _decode_mime_header(str(email_item.get("from", "")).strip())
    preview = str(email_item.get("body_preview", "")).strip()
    combined = f"{subject} {sender} {preview}".lower()

    low_priority_signals = (
        "newsletter", "unsubscribe", "promo", "promotion", "digest",
        "notification", "no-reply", "noreply", "marketing", "receipt",
        "welcome", "verify your email",
    )
    important_signals = (
        "urgent", "asap", "action required", "deadline", "invoice",
        "payment", "meeting", "interview", "contract", "client",
        "boss", "manager", "approval", "today", "reply by",
    )

    has_low_priority = any(token in combined for token in low_priority_signals)
    has_important = any(token in combined for token in important_signals)
    asks_for_reply = any(
        token in combined
        for token in ("please reply", "please respond", "can you", "could you",
                      "question", "?", "confirm", "need your input")
    )

    if has_important and not has_low_priority:
        priority = "important"
    elif has_low_priority and not has_important:
        priority = "low"
    elif asks_for_reply:
        priority = "important"
    else:
        priority = "normal"

    sender_address = _extract_address(sender)
    need_reply = priority != "low" and (asks_for_reply or has_important)
    subject_prefix = subject or "No subject"
    body_preview = preview[:260] if preview else "No preview available"
    reply_subject = subject_prefix if subject_prefix.lower().startswith("re:") else f"Re: {subject_prefix}"
    reply_body = (
        "Thanks for the update. I reviewed your message and have noted it for follow-up. "
        "If anything needs immediate action, I will handle it next."
    )

    return {
        "id": str(email_item.get("id", "")),
        "sender": sender_address,
        "raw_sender": sender,
        "subject": subject_prefix,
        "priority": priority,
        "needs_reply": need_reply,
        "summary": f"{subject_prefix} - {body_preview}",
        "reply_subject": reply_subject,
        "reply_body": reply_body,
        "auto_send": priority == "low",
    }


class EmailTools:
    def __init__(self):
        self.gmail_credentials_file = os.environ.get("GMAIL_CREDENTIALS_FILE", "")
        self.gmail_token_file = os.environ.get("GMAIL_TOKEN_FILE", self._default_gmail_token_file())
        self.email_address = os.environ.get("EMAIL_ADDRESS", "")
        self.email_password = os.environ.get("EMAIL_PASSWORD", "")
        self.gmail_scopes = ["https://mail.google.com/"]

        self.gsmtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
        self.gsmtp_port = int(os.environ.get("SMTP_PORT", 587))
        self.smtp_starttls = True

        self.imap_host = os.environ.get("IMAP_HOST", "imap.gmail.com")
        self.imap_port = int(os.environ.get("IMAP_PORT", 993))

        self.connection_pool: Dict[str, Any] = {}

    def _default_gmail_token_file(self) -> str:
        if self.gmail_credentials_file:
            base, _ = os.path.splitext(self.gmail_credentials_file)
            return f"{base}_token.json"
        return project_path_str("gmail_token.json")

    def _load_gmail_credentials(self) -> Credentials:
        if not self.gmail_credentials_file:
            raise FileNotFoundError("GMAIL_CREDENTIALS_FILE is not set in the environment")
        if not os.path.exists(self.gmail_credentials_file):
            raise FileNotFoundError(f"Gmail OAuth client file not found at: {self.gmail_credentials_file}")

        creds = None
        if self.gmail_token_file and os.path.exists(self.gmail_token_file):
            creds = Credentials.from_authorized_user_file(self.gmail_token_file, scopes=self.gmail_scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.gmail_credentials_file, scopes=self.gmail_scopes,
                )
                creds = flow.run_local_server(port=0)

            if self.gmail_token_file:
                token_dir = os.path.dirname(self.gmail_token_file)
                if token_dir:
                    os.makedirs(token_dir, exist_ok=True)
                with open(self.gmail_token_file, "w", encoding="utf-8") as token_file:
                    token_file.write(creds.to_json())
        return creds

    @staticmethod
    def _build_xoauth2_response(email_address: str, access_token: str) -> str:
        return f"user={email_address}\x01auth=Bearer {access_token}\x01\x01"

    async def connect_email_service(self, provider: str = "gmail") -> Dict[str, Any]:
        try:
            if provider == "gmail" and self.gmail_credentials_file:
                return await self._connect_gmail_oauth()
            else:
                return await self._connect_imap_generic(provider)
        except Exception as e:
            return {"status": "error", "message": f"Failed to connect: {str(e)}"}

    async def _connect_gmail_oauth(self) -> Dict[str, Any]:
        try:
            credentials = await asyncio.to_thread(self._load_gmail_credentials)
            if not self.email_address:
                return {"status": "error", "message": "EMAIL_ADDRESS is required"}

            imap_mail = await asyncio.to_thread(lambda: IMAPClient(self.imap_host, port=self.imap_port, ssl=True))
            await asyncio.to_thread(imap_mail.oauth2_login, self.email_address, credentials.token)

            smtp_mail = await asyncio.to_thread(lambda: smtplib.SMTP(self.gsmtp_server, self.gsmtp_port))
            await asyncio.to_thread(smtp_mail.ehlo)
            if self.smtp_starttls:
                await asyncio.to_thread(smtp_mail.starttls)
                await asyncio.to_thread(smtp_mail.ehlo)
            await asyncio.to_thread(
                smtp_mail.auth, "XOAUTH2",
                lambda challenge=None: self._build_xoauth2_response(self.email_address, credentials.token),
            )

            self.connection_pool["gmail_oauth_imap"] = imap_mail
            self.connection_pool["gmail_oauth_smtp"] = smtp_mail
            return {"status": "success", "message": "Connected to Gmail via OAuth2", "connection_type": "oauth2"}
        except Exception as e:
            return {"status": "error", "message": f"OAuth2 error: {str(e)}"}

    async def _connect_imap_generic(self, provider: str) -> Dict[str, Any]:
        try:
            mail = await asyncio.to_thread(lambda: IMAPClient(host=self.imap_host, port=self.imap_port))
            if hasattr(mail, 'login'):
                await asyncio.to_thread(mail.login, self.email_address, self.email_password)
            self.connection_pool["imap"] = mail
            return {"status": "success", "message": f"Connected to {provider} IMAP", "connection_type": "imap"}
        except Exception as e:
            return {"status": "error", "message": f"IMAP connection failed: {str(e)}"}

    async def _get_active_mail_connection(self):
        if "gmail_oauth_imap" in self.connection_pool:
            return self.connection_pool["gmail_oauth_imap"]
        if "imap" in self.connection_pool:
            return self.connection_pool["imap"]
        connect_result = await self.connect_email_service()
        if connect_result.get("status") != "success":
            return None
        if "gmail_oauth_imap" in self.connection_pool:
            return self.connection_pool["gmail_oauth_imap"]
        if "imap" in self.connection_pool:
            return self.connection_pool["imap"]
        return None

    async def close_email_connections(self):
        try:
            for _, connection in self.connection_pool.items():
                try:
                    await asyncio.to_thread(connection.logout)
                except Exception:
                    pass
            self.connection_pool.clear()
            return {"status": "success", "message": "Email connections closed"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def fetch_imap_emails(self, account_type: str = "inbox", max_count: int = 10) -> Dict[str, Any]:
        try:
            mail = await self._get_active_mail_connection()
            if mail is None:
                return {"status": "error", "message": "No active email connection"}
            folder_name = account_type.lower().replace(" ", "")
            await asyncio.to_thread(mail.select_folder, folder_name)
            messages = []
            seq_nums = await asyncio.to_thread(mail.search, "ALL")
            for seq_num in seq_nums[-max_count:]:
                msg = await asyncio.to_thread(
                    mail.fetch, [seq_num],
                    [
                        "BODY.PEEK[HEADER.FIELDS (DATE FROM SUBJECT TO)]",
                        "RFC822.SIZE",
                        "BODY.PEEK[TEXT]<0.2048>",
                    ],
                )
                try:
                    email_data = self._parse_email_message(msg)
                    if not email_data.get("id"):
                        email_data["id"] = str(seq_num)
                    messages.append(email_data)
                except Exception:
                    pass
            return {"status": "success", "emails_count": len(messages), "emails": messages}
        except Exception as e:
            return {"status": "error", "message": f"Failed to fetch emails: {str(e)}"}

    def _parse_email_message(self, msg) -> Dict[str, Any]:
        email_data = {"id": "", "date": "", "subject": "", "from": "", "to": "", "body_preview": ""}
        try:
            message_data = next(iter(msg.values()))
            headers = message_data.get(b"BODY[HEADER.FIELDS (DATE FROM SUBJECT TO)]") or b""
            raw_message = message_data.get(b"BODY[TEXT]<0>") or message_data.get(b"BODY[TEXT]") or b""
            if headers:
                header_text = headers.decode("utf-8", errors="replace")
                for line in header_text.splitlines():
                    lower_line = line.lower()
                    if lower_line.startswith("date:"):
                        email_data["date"] = line.split(":", 1)[1].strip()
                    elif lower_line.startswith("subject:"):
                        email_data["subject"] = _decode_mime_header(line.split(":", 1)[1].strip())
                    elif lower_line.startswith("from:"):
                        email_data["from"] = _decode_mime_header(line.split(":", 1)[1].strip())
                    elif lower_line.startswith("to:"):
                        email_data["to"] = _decode_mime_header(line.split(":", 1)[1].strip())
            if raw_message:
                preview = raw_message.decode("utf-8", errors="replace")
                preview = " ".join(preview.split())
                email_data["body_preview"] = preview[:300] + "..." if len(preview) > 300 else preview
        except Exception:
            pass
        return email_data

    async def draft_email(self, recipient: str, subject: str, body: str, attachments: Optional[List[str]] = None) -> Dict[str, Any]:
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, recipient):
            return {"status": "error", "message": f"Invalid email format: {recipient}"}

        attachment_info = []
        if attachments:
            for attachment_path in attachments:
                if not os.path.exists(attachment_path):
                    return {"status": "error", "message": f"Attachment not found: {attachment_path}"}
                file_size = os.path.getsize(attachment_path)
                file_name = os.path.basename(attachment_path)
                attachment_info.append({"name": file_name, "size": file_size, "path": attachment_path})

        draft = {
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "attachments": attachment_info,
            "status": "draft_ready",
            "message": "Email drafted successfully. Ready for your review before sending.",
        }

        safe_print(f"\nTOM DRAFTED EMAIL:")
        safe_print(f"To: {recipient}")
        safe_print(f"Subject: {subject}")
        safe_print(f"Body:\n{body[:500]}...")
        return draft

    async def draft_email_with_llm(self, recipient: str, context: str, llm) -> Dict[str, Any]:
        """Use LLM to draft a contextually relevant email."""
        from langchain_core.messages import SystemMessage, HumanMessage

        sys_msg = (
            "You are TOM, a professional email assistant. Draft a complete, polished email "
            "based on the recipient and context provided. Return ONLY a JSON object:\n"
            '{"subject": "<subject line>", "body": "<full email body>"}\n'
            "Make the email professional, well-structured, and contextually appropriate."
        )
        try:
            import json
            messages = [SystemMessage(content=sys_msg),
                        HumanMessage(content=f"Recipient: {recipient}\nContext: {context}")]
            resp = await llm.ainvoke(messages)
            content = resp.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            parsed = json.loads(content)
            return await self.draft_email(
                recipient,
                parsed.get("subject", "Message from TOM"),
                parsed.get("body", context),
            )
        except Exception as e:
            return await self.draft_email(recipient, "Message from TOM", context)

    async def open_email_client_draft(self, recipient: str, subject: str, body: str) -> Dict[str, Any]:
        import urllib.parse
        trimmed_body = (body or "")[:1200]
        mailto_uri = (
            "mailto:" + urllib.parse.quote(recipient)
            + "?subject=" + urllib.parse.quote(subject or "")
            + "&body=" + urllib.parse.quote(trimmed_body)
        )
        try:
            if os.name == "nt":
                await asyncio.to_thread(os.startfile, mailto_uri)
            else:
                await asyncio.to_thread(subprocess.Popen, ["xdg-open", mailto_uri])
            return {"status": "success", "message": "Draft opened in email client",
                    "recipient": recipient, "subject": subject}
        except Exception as e:
            return {"status": "error", "message": f"Could not open draft: {str(e)}"}

    async def send_email(self, recipient: str, subject: str, body: str,
                         attachments: Optional[List[str]] = None,
                         approval_callback=None) -> Dict[str, Any]:
        """
        Send email with async approval callback instead of blocking input().
        approval_callback: async function(recipient, subject, body) -> bool
        """
        from safety.guards import SafetyGuards

        safe_print(f"\nTOM EMAIL SEND CHECK:")
        safe_print(f"To: {recipient}")
        safe_print(f"Subject: {subject}")

        # Use approval callback if provided
        if approval_callback:
            approved = await approval_callback(recipient, subject, body)
            if not approved:
                return {"status": "cancelled", "message": "Email sending cancelled by user."}
        else:
            safe_print("No approval callback set. Cancelling send.")
            return {"status": "cancelled", "message": "No approval mechanism available."}

        try:
            email_connection = await self._prepare_email_sender()
            if not email_connection["success"]:
                return {"status": "error", "message": email_connection.get("message", "Connection failed")}
            message = self._compose_email_message(recipient, subject, body, attachments)
            await asyncio.to_thread(email_connection["sender"].send_message, message)
            safety = SafetyGuards()
            safety.log_action("EMAIL_SENT", target=recipient, status="SUCCESS")
            return {"status": "success", "message": "Email sent successfully!", "safety_logged": True}
        except Exception as e:
            safety = SafetyGuards()
            safety.log_action("EMAIL_SEND_ERROR", target=recipient, status="FAILURE", message=str(e))
            return {"status": "error", "message": f"Failed to send email: {str(e)}"}

    async def send_email_direct(self, recipient: str, subject: str, body: str,
                                 attachments: Optional[List[str]] = None) -> Dict[str, Any]:
        from safety.guards import SafetyGuards
        try:
            email_connection = await self._prepare_email_sender()
            if not email_connection["success"]:
                return {"status": "error", "message": email_connection.get("message", "Connection failed")}
            message = self._compose_email_message(recipient, subject, body, attachments)
            await asyncio.to_thread(email_connection["sender"].send_message, message)
            safety = SafetyGuards()
            safety.log_action("EMAIL_SENT", target=recipient, status="SUCCESS", message="Automated reply sent")
            return {"status": "success", "message": "Email sent successfully!", "safety_logged": True}
        except Exception as e:
            safety = SafetyGuards()
            safety.log_action("EMAIL_SEND_ERROR", target=recipient, status="FAILURE", message=str(e))
            return {"status": "error", "message": f"Failed to send email: {str(e)}"}

    async def _prepare_email_sender(self) -> Dict[str, Any]:
        try:
            if "gmail_oauth_smtp" in self.connection_pool:
                return {"success": True, "sender": self.connection_pool["gmail_oauth_smtp"], "connection_type": "oauth2"}
            connect_result = await self.connect_email_service()
            if connect_result.get("status") != "success":
                return {"success": False, "message": connect_result.get("message", "SMTP connection failed")}
            if "gmail_oauth_smtp" in self.connection_pool:
                return {"success": True, "sender": self.connection_pool["gmail_oauth_smtp"], "connection_type": "oauth2"}
            return {"success": False, "message": "SMTP connection was not established"}
        except Exception as e:
            return {"success": False, "message": f"Failed to prepare sender: {str(e)}"}

    def _compose_email_message(self, recipient: str, subject: str, body: str,
                                attachments: Optional[List[str]] = None) -> MIMEMultipart:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = self.email_address if self.email_address else "your-email@gmail.com"
        msg['To'] = recipient
        msg.attach(MIMEText(body, 'plain'))

        if attachments:
            for file_path in attachments:
                try:
                    if not os.path.exists(file_path):
                        continue
                    filename = os.path.basename(file_path)
                    with open(file_path, 'rb') as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f'attachment; filename= {filename}')
                        msg.attach(part)
                except Exception as e:
                    print(f"Warning: Could not attach file {file_path}: {e}")
        return msg

    def format_report_email(self, title: str, summary_lines: List[str],
                             highlights: List[Dict[str, Any]]) -> Dict[str, str]:
        plain_lines = [title, "", "Executive Summary", "------------------"]
        plain_lines.extend(f"- {line}" for line in summary_lines if line)
        plain_lines.append("")
        plain_lines.append("Top Items")
        plain_lines.append("---------")

        html_rows = []
        for item in highlights:
            importance = str(item.get("importance", ""))
            heading = item.get("heading", "Untitled item")
            detail = item.get("detail", "")
            source = item.get("source", "")
            html_rows.append(f"""
                <tr>
                    <td style="padding:16px;border:1px solid #d8c6af;border-radius:14px;background:#fff8ef;">
                        <div style="font:700 12px/1.2 Arial,sans-serif;color:#7c1d12;text-transform:uppercase;letter-spacing:.08em;">Priority {importance}</div>
                        <div style="font:700 18px/1.3 Georgia,serif;color:#1a1a1e;margin:6px 0 8px;">{heading}</div>
                        <div style="font:400 14px/1.65 Arial,sans-serif;color:#2c2c34;">{detail}</div>
                        <div style="font:400 12px/1.6 Arial,sans-serif;color:#6f6f78;margin-top:10px;">Source: {source}</div>
                    </td>
                </tr>
            """)
        if not highlights:
            html_rows.append("""
                <tr>
                    <td style="padding:16px;border:1px solid #d8c6af;border-radius:14px;background:#fff8ef;">
                        <div style="font:700 18px/1.3 Georgia,serif;color:#1a1a1e;">No high-signal items surfaced.</div>
                    </td>
                </tr>
            """)

        plain_body = "\n".join(plain_lines)
        html_body = f"""
<html><body style="margin:0;padding:0;background:#f7f2ea;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f7f2ea;padding:24px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:600px;background:#fffdf8;border:1px solid #d8c6af;border-radius:20px;overflow:hidden;">
<tr><td style="padding:28px 30px 10px;border-bottom:1px solid #ead9c6;">
<div style="font:700 12px/1.2 Arial,sans-serif;color:#8a6a3f;letter-spacing:.16em;text-transform:uppercase;">TOM Reporting Desk</div>
<div style="font:700 28px/1.15 Georgia,serif;color:#1a1a1e;margin-top:8px;">{title}</div>
</td></tr>
<tr><td style="padding:24px 30px 30px;">
<div style="font:700 14px/1.2 Arial,sans-serif;color:#1a1a1e;text-transform:uppercase;letter-spacing:.12em;margin-bottom:14px;">Top Items</div>
<table width="100%" cellpadding="0" cellspacing="0" border="0">{''.join(html_rows)}</table>
</td></tr>
</table></td></tr>
</table></body></html>"""

        return {"plain_text": plain_body, "html_text": html_body}

    async def __aenter__(self):
        await self.connect_email_service("gmail")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_email_connections()
