"""
tools/self_evolution.py — TOM's Self-Evolution & Adaptive Intelligence Engine

This is TOM's ability to get smarter over time by learning from YOU.

How it works:
1. Every time you give TOM a command and it succeeds, TOM stores what worked.
2. Every time you give negative feedback ("that's wrong", "try again"), TOM
   records what failed and avoids the same approach in the future.
3. TOM builds a personal profile of your preferences — how you like things
   explained, what formats you prefer, your workflow patterns.
4. TOM adapts its prompt strategy based on all of this — so after a few days
   of use, TOM understands you better than any generic AI assistant.

This is NOT model fine-tuning (that requires GPU training infrastructure).
This IS adaptive prompt engineering + experience-based reasoning — which is
what makes TOM genuinely smarter the more you use it.
"""

import os
import json
import time
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from tools.project_paths import project_path

logger = logging.getLogger(__name__)

BRAIN_DIR = project_path("tom_brain")
EVOLUTION_FILE = BRAIN_DIR / "evolution.json"
PROFILE_FILE   = BRAIN_DIR / "user_profile.json"
PATTERNS_FILE  = BRAIN_DIR / "learned_patterns.json"


def _load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


# ── SelfEvolution ─────────────────────────────────────────────────────────────

class SelfEvolution:
    """
    TOM's adaptive intelligence layer.

    Tracks successes, failures, and user preferences to evolve TOM's
    behaviour over time without retraining the underlying model.
    """

    def __init__(self):
        BRAIN_DIR.mkdir(parents=True, exist_ok=True)
        self._data     = _load_json(EVOLUTION_FILE, self._default_data())
        self._profile  = _load_json(PROFILE_FILE,   self._default_profile())
        self._patterns = _load_json(PATTERNS_FILE,  {})
        self._session_commands: List[Dict] = []
        logger.info("[EVOLUTION] Self-evolution engine initialised.")

    # ── Defaults ─────────────────────────────────────────────────────────────

    @staticmethod
    def _default_data() -> Dict:
        return {
            "total_interactions": 0,
            "successes": 0,
            "failures": 0,
            "reward_history": [],
            "avoided_approaches": [],
            "preferred_approaches": [],
        }

    @staticmethod
    def _default_profile() -> Dict:
        return {
            "name": "Rajesh",
            "response_style": "professional",   # professional / casual / technical
            "preferred_length": "concise",       # concise / detailed / exhaustive
            "preferred_format": "prose",         # prose / bullets / structured
            "frequent_tasks": {},
            "time_patterns": {},
            "domain_expertise": [],
            "communication_notes": [],
            "last_updated": None,
        }

    # ── Record Outcomes ───────────────────────────────────────────────────────

    def record_success(self, command: str, intent: str, approach: str,
                       response_snippet: str) -> None:
        """Record a successful command execution."""
        self._data["total_interactions"] += 1
        self._data["successes"] += 1

        # Track frequent tasks
        self._profile["frequent_tasks"][intent] = (
            self._profile["frequent_tasks"].get(intent, 0) + 1
        )

        # Store as a preferred approach
        entry = {
            "command_pattern": self._generalise(command),
            "intent": intent,
            "approach": approach,
            "response_snippet": response_snippet[:200],
            "timestamp": datetime.now().isoformat(),
            "score": 1.0,
        }
        self._data["preferred_approaches"].append(entry)
        # Keep only the 200 most recent
        self._data["preferred_approaches"] = self._data["preferred_approaches"][-200:]

        # Store in patterns index
        self._patterns[intent] = self._patterns.get(intent, {"hits": 0, "best_approach": ""})
        self._patterns[intent]["hits"] += 1
        self._patterns[intent]["best_approach"] = approach[:300]

        self._persist()

    def record_failure(self, command: str, intent: str, approach: str,
                       error: str) -> None:
        """Record a failed command so TOM avoids the same approach."""
        self._data["total_interactions"] += 1
        self._data["failures"] += 1

        entry = {
            "command_pattern": self._generalise(command),
            "intent": intent,
            "approach": approach,
            "error": error[:200],
            "timestamp": datetime.now().isoformat(),
        }
        self._data["avoided_approaches"].append(entry)
        self._data["avoided_approaches"] = self._data["avoided_approaches"][-100:]
        self._persist()

    def apply_reward(self, score: float, context: str = "") -> None:
        """
        Apply a reward signal (-1.0 to 1.0) from user feedback.
        Positive = good response. Negative = bad, try differently.
        """
        entry = {
            "score": score,
            "context": context[:100],
            "timestamp": datetime.now().isoformat(),
        }
        self._data["reward_history"].append(entry)
        self._data["reward_history"] = self._data["reward_history"][-500:]

        # Adjust preferred response style based on reward
        if score < -0.5:
            # User didn't like this — log it for avoidance
            logger.info(f"[EVOLUTION] Negative reward ({score:.1f}) — adapting approach")
        elif score > 0.7:
            logger.info(f"[EVOLUTION] Positive reward ({score:.1f}) — reinforcing approach")

        self._persist()

    # ── Learn from Feedback ───────────────────────────────────────────────────

    def learn_from_feedback(self, feedback_text: str, last_command: str,
                             last_response: str) -> str:
        """
        Process natural language feedback to update user profile and avoid
        repeating the same mistake.

        Returns a message explaining what TOM learned.
        """
        fb = feedback_text.lower()
        notes = []

        # Detect style preferences
        if any(w in fb for w in ("too long", "shorter", "brief", "concise", "tldr")):
            self._profile["preferred_length"] = "concise"
            notes.append("shorter responses")
        elif any(w in fb for w in ("more detail", "elaborate", "explain more", "too short")):
            self._profile["preferred_length"] = "detailed"
            notes.append("more detailed responses")

        if any(w in fb for w in ("bullet", "list", "points")):
            self._profile["preferred_format"] = "bullets"
            notes.append("bullet-point format")
        elif any(w in fb for w in ("paragraph", "prose", "no bullets", "no list")):
            self._profile["preferred_format"] = "prose"
            notes.append("prose format (no bullets)")

        if any(w in fb for w in ("casual", "friendly", "informal", "like a friend")):
            self._profile["response_style"] = "casual"
            notes.append("casual/friendly tone")
        elif any(w in fb for w in ("professional", "formal", "business")):
            self._profile["response_style"] = "professional"
            notes.append("professional tone")

        # Record what to avoid
        if any(w in fb for w in ("wrong", "incorrect", "bad", "terrible", "awful", "no")):
            self.record_failure(last_command, "unknown", last_response[:100],
                                f"User feedback: {feedback_text[:100]}")
            self.apply_reward(-0.8, context=last_command[:50])
            notes.append("avoiding this approach in the future")

        # Update profile timestamp
        self._profile["last_updated"] = datetime.now().isoformat()
        if feedback_text not in self._profile["communication_notes"]:
            self._profile["communication_notes"].append(feedback_text[:100])
            self._profile["communication_notes"] = self._profile["communication_notes"][-20:]

        self._persist()

        if notes:
            return f"Got it! I've learned: {', '.join(notes)}. I'll apply this going forward."
        return "Thanks for the feedback — I've noted that and will do better."

    # ── Generate Adaptive System Prompt ──────────────────────────────────────

    def get_adaptive_system_prompt(self) -> str:
        """
        Generate a personalised system prompt segment based on everything
        TOM has learned about the user's preferences.
        """
        p = self._profile
        parts = []

        # Name
        if p.get("name"):
            parts.append(f"The user's name is {p['name']}.")

        # Style preferences
        style_map = {
            "casual":       "Speak casually and warmly, like a knowledgeable friend.",
            "professional": "Maintain a professional, polished tone.",
            "technical":    "Use precise technical language without over-explaining basics.",
        }
        parts.append(style_map.get(p.get("response_style", "professional"),
                                   style_map["professional"]))

        # Length
        length_map = {
            "concise":    "Keep responses concise — get to the point quickly.",
            "detailed":   "Give thorough, detailed explanations when relevant.",
            "exhaustive": "Be comprehensive — the user wants full context.",
        }
        parts.append(length_map.get(p.get("preferred_length", "concise"),
                                    length_map["concise"]))

        # Format
        fmt = p.get("preferred_format", "prose")
        if fmt == "bullets":
            parts.append("Use bullet points and lists for clarity.")
        elif fmt == "prose":
            parts.append("Write in flowing prose — avoid excessive bullet points.")

        # Frequent tasks
        top_tasks = sorted(p.get("frequent_tasks", {}).items(),
                           key=lambda x: x[1], reverse=True)[:3]
        if top_tasks:
            task_names = [t[0].replace("_", " ") for t in top_tasks]
            parts.append(f"This user frequently asks about: {', '.join(task_names)}.")

        # Recent notes
        recent_notes = p.get("communication_notes", [])[-3:]
        if recent_notes:
            parts.append("Recent user preferences: " + "; ".join(recent_notes) + ".")

        # Success rate context
        total = self._data.get("total_interactions", 0)
        if total > 10:
            success_rate = self._data["successes"] / total
            if success_rate < 0.7:
                parts.append("Be extra careful — there have been some failures. "
                             "Double-check your work before responding.")

        return "\n".join(parts)

    def get_approach_hints(self, intent: str) -> str:
        """
        Return hints about the best known approach for a given intent,
        based on past experience.
        """
        pattern = self._patterns.get(intent, {})
        if not pattern or not pattern.get("best_approach"):
            return ""
        return (f"[LEARNED APPROACH for {intent}]: {pattern['best_approach']}")

    def get_avoided_approaches(self, intent: str) -> List[str]:
        """Return approaches that have failed for this intent."""
        avoided = self._data.get("avoided_approaches", [])
        return [e["approach"] for e in avoided
                if e.get("intent") == intent][-3:]   # Last 3 failures

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Return evolution statistics."""
        total = self._data.get("total_interactions", 0)
        return {
            "total_interactions": total,
            "successes": self._data.get("successes", 0),
            "failures": self._data.get("failures", 0),
            "success_rate": f"{self._data['successes']/total:.0%}" if total > 0 else "N/A",
            "learned_strategies": len(self._patterns),
            "preferred_approaches_stored": len(self._data.get("preferred_approaches", [])),
            "user_profile": self._profile,
            "days_of_training": self._days_active(),
        }

    def _days_active(self) -> int:
        rewards = self._data.get("reward_history", [])
        if not rewards:
            return 0
        try:
            first = datetime.fromisoformat(rewards[0]["timestamp"])
            return (datetime.now() - first).days
        except Exception:
            return 0

    # ── Generalise command patterns ───────────────────────────────────────────

    @staticmethod
    def _generalise(command: str) -> str:
        """
        Strip specifics from a command to create a reusable pattern.
        e.g. "send email to john@gmail.com about meeting" →
             "send email to [EMAIL] about [TOPIC]"
        """
        import re
        cmd = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL]', command)
        cmd = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', '[DATE]', cmd)
        cmd = re.sub(r'\bhttps?://\S+', '[URL]', cmd)
        cmd = re.sub(r'["\'"].*?["\'"]', '[QUOTED]', cmd)
        return cmd[:120]

    # ── Persistence ───────────────────────────────────────────────────────────

    def _persist(self) -> None:
        try:
            _save_json(EVOLUTION_FILE, self._data)
            _save_json(PROFILE_FILE,   self._profile)
            _save_json(PATTERNS_FILE,  self._patterns)
        except Exception as e:
            logger.debug(f"[EVOLUTION] Persist error: {e}")


# ── Singleton ─────────────────────────────────────────────────────────────────

_evolution_instance: Optional[SelfEvolution] = None

def get_evolution() -> SelfEvolution:
    """Get the global SelfEvolution singleton."""
    global _evolution_instance
    if _evolution_instance is None:
        _evolution_instance = SelfEvolution()
    return _evolution_instance
