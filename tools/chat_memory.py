import json
import os
import re
import time
from typing import Dict, List
from tools.project_paths import project_path_str


class ChatMemory:
    """Persistent chat memory for TOM.

    Stores every turn to disk and can build compact context windows
    (recent + keyword-relevant) for prompt injection.
    """

    MAX_MESSAGES = 500

    def __init__(self, file_path: str = "memories/lifetime_chat.json"):
        self.file_path = file_path if os.path.isabs(file_path) else project_path_str(file_path)
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        self.messages: List[Dict[str, str]] = []
        self._load()

    def _load(self):
        if not os.path.exists(self.file_path):
            self.messages = []
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.messages = json.load(f)
        except Exception:
            self.messages = []

    def _persist(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.messages, f, ensure_ascii=False, indent=2)

    def append(self, role: str, text: str):
        self.messages.append(
            {
                "ts": str(int(time.time())),
                "role": role,
                "text": text,
            }
        )
        # Evict oldest messages if over limit
        if len(self.messages) > self.MAX_MESSAGES:
            self.messages = self.messages[-self.MAX_MESSAGES:]
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
