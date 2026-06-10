import os
import json
import time
import re
from typing import Any, Dict, List
from tools.project_paths import project_path_str

MEMORY_DIR = project_path_str("memories")
SESSION_MEMORY = os.path.join(MEMORY_DIR, "session_experiences.json")

def _ensure_memory_dir():
    os.makedirs(MEMORY_DIR, exist_ok=True)


class Learner:
    """Simple episodic learner and memory store.

    Stores experience records, allows rewarding experiences, and can
    summarize learned skills as lightweight metadata.
    This is *not* a full RL training loop — just a persistent experience
    store and a simple scoring mechanism that Tom can consult when planning.
    """

    MAX_EXPERIENCES = 500

    def __init__(self):
        _ensure_memory_dir()
        self._load()

    def _load(self):
        if os.path.exists(SESSION_MEMORY):
            try:
                with open(SESSION_MEMORY, "r", encoding="utf-8") as f:
                    self.experiences = json.load(f)
                if self._normalize_legacy_experiences():
                    self._persist()
            except Exception:
                self.experiences = []
        else:
            self.experiences = []

    def _persist(self):
        with open(SESSION_MEMORY, "w", encoding="utf-8") as f:
            json.dump(self.experiences, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _looks_like_clarifying_question(message: str) -> bool:
        text = (message or "").lower().strip()
        if not text:
            return False

        question_mark = "?" in text
        clarifying_phrases = [
            "can you provide",
            "could you provide",
            "can you tell me",
            "could you tell me",
            "before we get started",
            "what specifically",
            "what kind of",
            "tell me a bit more",
            "let me know",
            "i need a bit more information",
            "do you have",
            "what are you looking for",
            "what's the goal",
        ]
        return question_mark or any(phrase in text for phrase in clarifying_phrases)

    def infer_outcome(self, details: Dict[str, Any], fallback: str = "success") -> str:
        """Infer a truthful outcome label from the recorded result payload."""
        if not isinstance(details, dict):
            return fallback

        if details.get("error"):
            return "failure"

        result = details.get("result")
        if isinstance(result, dict):
            status = str(result.get("status", "")).strip().lower()
            message = str(result.get("message", ""))
            response_type = str(result.get("response_type", "")).strip().lower()

            if status in {"error", "failure", "failed"}:
                return "failure"

            if status == "partial":
                return "partial"

            if status in {"planned", "draft_ready", "cancelled", "skipped"}:
                return "incomplete"

            if status == "success":
                if response_type == "chat" and self._looks_like_clarifying_question(message):
                    return "incomplete"
                return "success"

        if isinstance(result, str) and result.strip():
            if re.search(r"\b(error|failed|failure)\b", result, re.IGNORECASE):
                return "failure"

        return fallback

    def _normalize_legacy_experiences(self) -> bool:
        """Repair stored records that were saved with an overly optimistic outcome."""
        changed = False
        for experience in self.experiences:
            details = experience.get("details", {})
            inferred = self.infer_outcome(details, fallback=str(experience.get("outcome", "success")))
            if experience.get("outcome") != inferred:
                experience["outcome"] = inferred
                changed = True
        return changed

    def log_experience(self, action: str, outcome: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """Record an experience and return the stored entry."""
        normalized_outcome = self.infer_outcome(details, fallback=outcome)
        entry = {
            "id": int(time.time() * 1000),
            "ts": time.time(),
            "action": action,
            "outcome": normalized_outcome,
            "details": details,
            "reward": 0,
        }
        self.experiences.append(entry)
        if len(self.experiences) > self.MAX_EXPERIENCES:
            self.experiences = self.experiences[-self.MAX_EXPERIENCES:]
        self._persist()
        return entry

    def give_reward(self, exp_id: int, amount: float) -> bool:
        """Assign a reward (positive or negative) to an experience."""
        for e in self.experiences:
            if e.get("id") == exp_id:
                e["reward"] = e.get("reward", 0) + float(amount)
                self._persist()
                return True
        return False

    def summarize_skills(self) -> Dict[str, Any]:
        """Generate a lightweight skills summary from experiences.

        - Count successful flows
        - Extract frequent action verbs as 'skills'
        - Provide simple weighted score per skill
        """
        counts: Dict[str, int] = {}
        scores: Dict[str, float] = {}
        for e in self.experiences:
            act = e.get("action", "unknown")
            key = act.split()[0].lower() if act else "unknown"
            counts[key] = counts.get(key, 0) + 1
            scores[key] = scores.get(key, 0.0) + float(e.get("reward", 0))

        skills = []
        for k, c in counts.items():
            skills.append({"skill": k, "uses": c, "score": scores.get(k, 0.0)})

        return {"skills": sorted(skills, key=lambda s: (-s["score"], -s["uses"]))}

    def recent_experiences(self, limit: int = 20) -> List[Dict[str, Any]]:
        return list(reversed(self.experiences))[:limit]

    def get_pattern_insights(self) -> Dict[str, Any]:
        """Extract insights from accumulated experiences."""
        if not self.experiences:
            return {"patterns": [], "suggestions": []}

        from collections import Counter
        actions = [e.get("action", "unknown").split()[0].lower() for e in self.experiences if e.get("action")]
        action_counts = Counter(actions)
        most_common = action_counts.most_common(5)

        successes = [e for e in self.experiences if e.get("outcome") == "success"]
        failures = [e for e in self.experiences if e.get("outcome") == "failure"]

        failure_patterns = Counter()
        for f in failures[-50:]:
            action = f.get("action", "unknown")
            failure_patterns[action] += 1

        insights = {
            "patterns": [
                {"action": action, "count": count, "type": "frequent"}
                for action, count in most_common
            ],
            "suggestions": [
                {"action": action, "suggestion": f"Consider improving approach for: {action}"}
                for action, count in failure_patterns.most_common(3)
                if count > 2
            ],
            "success_rate": f"{len(successes)/max(len(self.experiences), 1)*100:.0f}%",
            "total_experiences": len(self.experiences),
            "success_count": len(successes),
            "failure_count": len(failures),
        }
        return insights

    def predict_best_approach(self, action: str) -> str:
        """Predict the best approach for an action based on past experience."""
        related = [
            e for e in self.experiences
            if e.get("action", "").lower().startswith(action.lower())
            and e.get("outcome") == "success"
            and e.get("reward", 0) >= 0
        ]
        if not related:
            return "standard_approach"

        best = max(related, key=lambda e: e.get("reward", 0))
        return best.get("details", {}).get("approach", "standard_approach")
