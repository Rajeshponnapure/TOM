import json
import os
import re
import time
import threading
import uuid
from typing import Dict, List, Optional, TypedDict
from tools.project_paths import project_path_str


class SessionDict(TypedDict):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[Dict[str, str]]


class ChatMemory:
    """Persistent chat memory for TOM.

    Stores every turn to disk and can build compact context windows
    (recent + keyword-relevant) for prompt injection.
    """

    MAX_MESSAGES = 500

    def __init__(self, file_path: str = "memories/lifetime_chat.json"):
        self.file_path = file_path if os.path.isabs(file_path) else project_path_str(file_path)
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        self._lock = threading.RLock()
        self.sessions: List[SessionDict] = []
        self.active_session_id = ""
        self.messages: List[Dict[str, str]] = []
        self._load()

    def _load(self):
        if not os.path.exists(self.file_path):
            self._create_session("New chat")
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                # Preserve legacy lifetime history as a single readable chat.
                self._create_session("Previous chat", messages=data)
            elif isinstance(data, dict) and isinstance(data.get("sessions"), list):
                self.sessions = data["sessions"]
                self.active_session_id = str(data.get("active_session_id") or "")
                if not self.sessions:
                    self._create_session("New chat")
                elif not any(s.get("id") == self.active_session_id for s in self.sessions):
                    self.active_session_id = str(self.sessions[-1].get("id", ""))
                self.messages = self._active_session()["messages"]
            else:
                self._create_session("New chat")
        except Exception:
            self.sessions = []
            self._create_session("New chat")

    def _create_session(self, title: str, messages: Optional[List[Dict[str, str]]] = None) -> str:
        now = str(int(time.time()))
        session_id = uuid.uuid4().hex
        session: SessionDict = {"id": session_id, "title": title, "created_at": now,
                   "updated_at": now, "messages": list(messages or [])}
        self.sessions.append(session)
        self.active_session_id = session_id
        self.messages = session["messages"]
        return session_id

    def _active_session(self) -> SessionDict:
        for session in self.sessions:
            if session.get("id") == self.active_session_id:
                return session
        self._create_session("New chat")
        return self.sessions[-1]

    def _persist(self):
        temp_path = self.file_path + ".tmp"
        payload = {"version": 2, "active_session_id": self.active_session_id,
                   "sessions": self.sessions}
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, self.file_path)

    def list_sessions(self) -> List[Dict[str, str]]:
        """Return session metadata, newest first, without message content."""
        with self._lock:
            return [{"id": str(s.get("id", "")), "title": str(s.get("title", "New chat")),
                     "updated_at": str(s.get("updated_at", ""))}
                    for s in reversed(self.sessions)]

    def active_session_info(self) -> Dict[str, str]:
        """Id + title of the chat the user is in right now.

        The id is stable for the life of the session, so it can be attached to
        long-term memory writes (Hindsight tags / document_id) and still point
        at the same conversation later.
        """
        with self._lock:
            session = self._active_session()
            return {"id": str(session.get("id", "")), "title": str(session.get("title", "New chat"))}

    def new_session(self) -> str:
        with self._lock:
            session_id = self._create_session("New chat")
            self._persist()
            return session_id

    def select_session(self, session_id: str) -> bool:
        with self._lock:
            for session in self.sessions:
                if session.get("id") == session_id:
                    self.active_session_id = session_id
                    self.messages = session["messages"]
                    self._persist()
                    return True
        return False

    def delete_session(self, session_id: str) -> bool:
        """Delete a chat session by ID. Returns True if deleted."""
        with self._lock:
            for i, session in enumerate(self.sessions):
                if session.get("id") == session_id:
                    self.sessions.pop(i)
                    if self.active_session_id == session_id:
                        if self.sessions:
                            self.active_session_id = self.sessions[-1]["id"]
                            self.messages = self.sessions[-1]["messages"]
                        else:
                            self._create_session("New chat")
                    self._persist()
                    return True
        return False

    def append(self, role: str, text: str):
        with self._lock:
            session = self._active_session()
            messages = session["messages"]
            messages.append({"ts": str(int(time.time())), "role": role, "text": text})
            if len(messages) > self.MAX_MESSAGES:
                session["messages"] = messages[-self.MAX_MESSAGES:]
                messages = session["messages"]
            self.messages = messages
            if len(messages) == 1 and role == "user":
                session["title"] = re.sub(r"\s+", " ", text).strip()[:48] or "New chat"
            session["updated_at"] = str(int(time.time()))
            self._persist()

    def recent(self, n: int = 20) -> List[Dict[str, str]]:
        if n <= 0:
            return []
        return self.messages[-n:]

    def relevant(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        terms = [t for t in re.findall(r"[a-zA-Z0-9_]+", query.lower()) if len(t) > 2]
        if not terms:
            return []

        scored = []
        for idx, m in enumerate(self.messages):
            text = (m.get("text") or "").lower()
            score = sum(1 for t in terms if t in text)
            if score > 0:
                scored.append((score, idx, m))

        scored.sort(key=lambda x: (-x[0], -x[1]))
        return [x[2] for x in scored[:limit]]

    def build_context(self, query: str, recent_n: int = 12, relevant_n: int = 8, max_chars: int = 5000) -> str:
        """Build compact text context from lifetime memory."""
        recent = self.recent(recent_n)
        relevant = self.relevant(query, relevant_n)

        seen = set()
        merged = []
        for item in recent + relevant:
            key = (item.get("ts", ""), item.get("role", ""), item.get("text", ""))
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)

        lines = []
        for item in merged:
            role = item.get("role", "unknown")
            text = (item.get("text") or "").replace("\n", " ").strip()
            lines.append(f"{role}: {text}")

        context = "\n".join(lines)
        if len(context) > max_chars:
            context = context[-max_chars:]
        # Ensure we don't start mid-line
        first_newline = context.find("\n")
        if first_newline > 0:
            context = context[first_newline + 1:]
        return context
