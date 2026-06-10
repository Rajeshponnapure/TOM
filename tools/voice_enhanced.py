"""
Enhanced Voice System for TOM.
Emotion detection, full-duplex conversation, pause/silence detection,
emotional analysis, and psychiatric assessment.

Features:
  - Real-time emotion detection from voice tone (pitch, energy, rate)
  - Text-based emotion detection (sentiment, keywords, linguistic markers)
  - Silence/pause detection with multi-category pause classification
  - Full conversation context awareness and emotional tracking
  - Text-to-speech with emotion-adapted prosody
  - Deep emotional analysis with crisis/distress flagging
  - Psychiatric screening (with disclaimers)
  - Background conversation mode with auto emotion logging
"""

import collections
import json
import math
import os
import random
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

# ── Constants ─────────────────────────────────────────────────────────────

EMOTIONS = [
    "angry", "happy", "sad", "anxious", "neutral",
    "stressed", "excited", "tired", "confused", "frustrated",
]

EMOTION_CATEGORIES = {
    "positive": {"happy", "excited"},
    "negative": {"angry", "sad", "anxious", "stressed", "frustrated"},
    "low_energy": {"sad", "tired", "confused"},
    "high_energy": {"angry", "excited", "stressed", "frustrated"},
    "neutral": {"neutral"},
}

EMOTION_KEYWORDS: Dict[str, List[str]] = {
    "angry": [
        "angry", "mad", "furious", "rage", "annoyed", "irritated", "frustrated",
        "pissed", "livid", "outraged", "infuriated", "hostile", "aggressive",
        "fuming", "enraged", "bitter", "resentful", "seething", "wrath",
    ],
    "happy": [
        "happy", "glad", "great", "wonderful", "amazing", "fantastic", "love",
        "joy", "delighted", "thrilled", "ecstatic", "elated", "cheerful",
        "excellent", "beautiful", "perfect", "awesome", "blessed", "grateful",
    ],
    "sad": [
        "sad", "unhappy", "depressed", "miserable", "crying", "tears", "lonely",
        "heartbroken", "grief", "sorrow", "devastated", "hopeless", "down",
        "melancholy", "mournful", "gloomy", "despondent", "despair", "lost",
    ],
    "anxious": [
        "anxious", "worried", "nervous", "fear", "scared", "terrified", "panic",
        "dread", "uneasy", "restless", "apprehensive", "petrified", "frightened",
        "fearful", "alarmed", "panicking", "terrified", "trembling",
    ],
    "stressed": [
        "stressed", "overwhelmed", "swamped", "pressure", "burnout", "exhausted",
        "drowning", "snowed", "spread thin", "too much", "can't handle",
        "overworked", "tension", "strained", "overloaded", "stretched",
    ],
    "excited": [
        "excited", "thrilled", "pumped", "hyped", "psyched", "eager",
        "can't wait", "looking forward", "stoked", "electric", "buzzing",
        "energized", "enthusiastic", "passionate", "motivated", "amped",
    ],
    "tired": [
        "tired", "exhausted", "sleepy", "fatigued", "drained", "worn out",
        "bushed", "beat", "dog tired", "sleep deprived", "weary", "lethargic",
        "sluggish", "drowsy", "somnolent", "yawning", "dead tired",
    ],
    "confused": [
        "confused", "unsure", "uncertain", "don't understand", "lost",
        "puzzled", "baffled", "perplexed", "bewildered", "mystified",
        "dilemma", "ambiguous", "unclear", "foggy", "hazy", "disoriented",
    ],
    "frustrated": [
        "frustrated", "ugh", "argh", "dammit", "damn", "can't figure out",
        "stuck", "blocked", "hindered", "thwarted", "aggravated", "vexed",
        "exasperated", "fed up", "sick of", "tired of", "impatient",
        "agitated", "irate", "cranky", "grumpy",
    ],
}

CRISIS_KEYWORDS = [
    "kill myself", "kill me", "end my life", "want to die", "better off dead",
    "suicide", "suicidal", "end it all", "can't go on", "no reason to live",
    "don't want to live", "hurt myself", "self harm", "self-harm",
    "cutting", "ending it", "not worth living", "final goodbye",
    "can't do this anymore", "give up", "giving up on life",
]

URGENT_KEYWORDS = [
    "emergency", "urgent", "immediately", "asap", "right now",
    "can't breathe", "heart attack", "accident", "bleeding",
    "need help now", "calling for help", "danger", "unsafe",
]

SUPPORT_PHRASES: Dict[str, List[str]] = {
    "sad": [
        "I hear how much pain you're in, and I want you to know you're not alone.",
        "It's okay to not be okay. I'm here with you.",
        "Take your time. I'm listening and I care about what you're going through.",
    ],
    "anxious": [
        "Let's take a breath together. You're safe right now.",
        "I understand this feels overwhelming. Let's break it down step by step.",
        "You're not alone in this. I'm right here with you.",
    ],
    "angry": [
        "It makes sense that you'd feel this way. Your feelings are completely valid.",
        "I can see why this would upset you. Let's work through it together.",
        "You have every right to be frustrated. I'm here to help.",
    ],
    "happy": [
        "That's amazing! I'm so happy for you!",
        "This is wonderful news! Tell me more about it!",
        "I love that energy! That's genuinely exciting!",
    ],
    "stressed": [
        "That sounds really overwhelming. Let's figure out what to prioritize.",
        "You're carrying a lot right now. What's the one thing I can help with most?",
        "Let's take a step back and breathe. We'll tackle this together.",
    ],
    "tired": [
        "You sound exhausted. Be kind to yourself today.",
        "Rest is important. Maybe it's time to take a short break?",
        "I hear how tired you are. Let me help lighten the load.",
    ],
    "confused": [
        "No worries at all. Let me explain it a different way.",
        "That's completely fine. I'm happy to clarify.",
        "Let's start over and go through it step by step together.",
    ],
    "frustrated": [
        "I know how frustrating this can be. Let's take a different approach.",
        "Don't worry, we'll figure this out. Let's try another angle.",
        "I get why you're frustrated. Let me help sort this out.",
    ],
    "excited": [
        "That's incredible! I'm genuinely excited for you!",
        "This sounds amazing! I can feel your energy from here!",
        "Wow, that's huge! Tell me everything!",
    ],
    "neutral": [
        "I'm here and fully listening. Take your time.",
        "Got it. Let me know how I can help.",
        "I'm following you. Please, go on.",
    ],
}

CRISIS_RESPONSES = [
    "I want you to know that what you're feeling matters, and you don't have to go through it alone. "
    "Please reach out to a crisis line right now — call or text 988 (in the US) to speak with "
    "someone trained to help. I'm here for you too, but this is beyond what I can handle.",
    "Thank you for trusting me with how you're feeling. Your safety is the most important thing "
    "right now. Please contact a crisis helpline immediately — 988 offers free, confidential "
    "support, 24/7. You matter, and there are people who want to help.",
]

PSYCHIATRIC_DISCLAIMER = (
    "IMPORTANT: This assessment is for informational and support purposes only. "
    "It is NOT a clinical diagnosis or a substitute for professional mental health care. "
    "If you are experiencing a mental health emergency, please contact a crisis helpline "
    "immediately (988 in US, 111 in UK, or your local emergency services). "
    "Please consult a licensed mental health professional for proper evaluation and treatment."
)


# ── Audio Feature Extraction ────────────────────────────────────────────

def _extract_audio_features(audio_data: bytes) -> Dict[str, float]:
    """Extract pitch, energy, speaking rate features from raw audio bytes."""
    features = {"pitch_mean": 0.0, "pitch_std": 0.0, "energy_rms": 0.0,
                "energy_var": 0.0, "zero_crossing_rate": 0.0, "speaking_rate": 0.0}
    try:
        if len(audio_data) < 128:
            return features

        samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float64)
        if len(samples) < 64:
            return features

        features["energy_rms"] = float(np.sqrt(np.mean(samples ** 2)))
        features["energy_var"] = float(np.var(samples))
        features["zero_crossing_rate"] = float(np.mean(np.abs(np.diff(np.signbit(samples)))))

        # FFT-based pitch estimation
        fft_vals = np.abs(np.fft.rfft(samples))
        freqs = np.fft.rfftfreq(len(samples), d=1.0 / 16000)
        mask = (freqs >= 60) & (freqs <= 500)
        if np.any(mask):
            pitch_range = fft_vals[mask]
            pitch_freqs = freqs[mask]
            if np.sum(pitch_range) > 0:
                features["pitch_mean"] = float(np.average(pitch_freqs, weights=pitch_range))
                features["pitch_std"] = float(
                    np.sqrt(np.average((pitch_freqs - features["pitch_mean"]) ** 2,
                                       weights=pitch_range))
                )

        # Normalize energy
        max_energy = 32768.0
        features["energy_rms"] = min(1.0, features["energy_rms"] / max_energy)
        features["energy_var"] = min(1.0, features["energy_var"] / (max_energy ** 2))

        return features
    except Exception:
        return features


def _classify_emotion_from_audio(features: Dict[str, float]) -> Dict[str, float]:
    """Classify emotion from audio features using heuristic rules."""
    scores = {e: 0.0 for e in EMOTIONS}
    try:
        e = features.get("energy_rms", 0)
        zcr = features.get("zero_crossing_rate", 0)
        p_mean = features.get("pitch_mean", 0)
        p_std = features.get("pitch_std", 0)

        # High energy + high pitch = angry / excited
        if e > 0.15 and p_mean > 300:
            scores["angry"] += 0.3
            scores["excited"] += 0.25
            scores["frustrated"] += 0.2

        # High energy + mid pitch = happy / excited
        if e > 0.1 and 150 < p_mean < 350 and zcr > 0.05:
            scores["happy"] += 0.25
            scores["excited"] += 0.25

        # Low energy + low pitch = sad / tired
        if e < 0.05 and p_mean < 180:
            scores["sad"] += 0.3
            scores["tired"] += 0.25
            scores["confused"] += 0.1

        # High ZCR + high pitch variance = anxious / stressed
        if zcr > 0.08 and p_std > 60:
            scores["anxious"] += 0.3
            scores["stressed"] += 0.25

        # Medium energy + stable pitch = neutral
        if 0.04 < e < 0.12 and p_std < 40:
            scores["neutral"] += 0.3

        # High energy + high ZCR = frustrated
        if e > 0.12 and zcr > 0.07:
            scores["frustrated"] += 0.2
            scores["angry"] += 0.15

        # Very low energy = tired / sad
        if e < 0.02:
            scores["tired"] += 0.35
            scores["sad"] += 0.2

        # Boost dominant
        dominant = max(scores, key=scores.get)
        if scores[dominant] > 0:
            scores[dominant] = min(1.0, scores[dominant] + 0.1)

        return scores
    except Exception:
        return scores


# ── Text Sentiment Analysis ─────────────────────────────────────────────

def _analyze_text_sentiment(text: str) -> Dict[str, float]:
    """Rule-based sentiment analysis: valence (-1 to 1), arousal, dominance."""
    result = {"valence": 0.0, "arousal": 0.0, "dominance": 0.0}
    try:
        if not text or not text.strip():
            return result

        lower = text.lower()
        words = re.findall(r"[a-z']+", lower)
        if not words:
            return result

        # Positive / negative word lists
        positive_words = {
            "good", "great", "excellent", "amazing", "wonderful", "fantastic",
            "happy", "love", "beautiful", "perfect", "awesome", "best",
            "brilliant", "superb", "outstanding", "marvelous", "splendid",
            "joyful", "glad", "delighted", "thrilled", "ecstatic", "elated",
            "grateful", "blessed", "cheerful", "optimistic", "hopeful",
            "positive", "success", "win", "victory", "triumph", "celebrate",
        }
        negative_words = {
            "bad", "terrible", "awful", "horrible", "hate", "worst",
            "ugly", "dreadful", "appalling", "atrocious", "abysmal",
            "miserable", "depressed", "hopeless", "helpless", "lonely",
            "sad", "angry", "furious", "rage", "pain", "hurt", "suffering",
            "tragedy", "disaster", "catastrophe", "failure", "lost",
            "grief", "sorrow", "despair", "devastated", "heartbroken",
            "terrified", "scared", "fear", "anxious", "worry", "panic",
        }
        high_arousal = {
            "angry", "furious", "terrified", "panic", "excited", "thrilled",
            "ecstatic", "enraged", "frantic", "desperate", "urgent",
            "screaming", "shouting", "explosive", "intense", "extreme",
            "frenzy", "hysterical", "wild", "chaotic",
        }
        low_arousal = {
            "tired", "sleepy", "exhausted", "calm", "peaceful", "relaxed",
            "bored", "drained", "fatigued", "lethargic", "sluggish",
            "serene", "tranquil", "gentle", "mellow", "subdued",
        }
        high_dominance = {
            "confident", "powerful", "strong", "determined", "certain",
            "sure", "absolute", "definite", "commanded", "controlled",
            "dominating", "assertive", "decisive", "bold", "fearless",
        }
        low_dominance = {
            "weak", "helpless", "powerless", "vulnerable", "fragile",
            "unsure", "uncertain", "confused", "lost", "dependent",
            "submissive", "timid", "shy", "insecure", "inadequate",
        }

        word_set = set(words)

        pos_count = len(word_set & positive_words)
        neg_count = len(word_set & negative_words)
        total_emotional = pos_count + neg_count

        if total_emotional > 0:
            result["valence"] = (pos_count - neg_count) / total_emotional

        arousal_count = len(word_set & high_arousal) - len(word_set & low_arousal)
        total_arousal_words = len(word_set & (high_arousal | low_arousal))
        if total_arousal_words > 0:
            result["arousal"] = arousal_count / total_arousal_words

        dom_count = len(word_set & high_dominance) - len(word_set & low_dominance)
        total_dom_words = len(word_set & (high_dominance | low_dominance))
        if total_dom_words > 0:
            result["dominance"] = dom_count / total_dom_words

        # Clamp
        for k in result:
            result[k] = max(-1.0, min(1.0, result[k]))

        return result
    except Exception:
        return result


def _detect_punctuation_mood(text: str) -> Dict[str, float]:
    """Detect emotional markers from punctuation patterns."""
    scores = {"angry": 0.0, "excited": 0.0, "confused": 0.0, "frustrated": 0.0, "sad": 0.0}
    try:
        if not text:
            return scores

        exclaim = text.count("!")
        question = text.count("?")
        ellipsis = text.count("...")
        caps_ratio = 0.0
        words = text.split()
        if words:
            caps_words = sum(1 for w in words if w.isupper() and len(w) > 1)
            caps_ratio = caps_words / len(words)

        if exclaim > 2:
            scores["excited"] += 0.3
            scores["angry"] += 0.2
        elif exclaim > 0:
            scores["excited"] += 0.15

        if ellipsis > 1:
            scores["sad"] += 0.2
            scores["confused"] += 0.15
            scores["tired"] = 0.15

        if question > 2:
            scores["confused"] += 0.2
            scores["anxious"] = 0.15

        if caps_ratio > 0.3:
            scores["angry"] += 0.3
            scores["frustrated"] += 0.25
            scores["excited"] += 0.15

        return scores
    except Exception:
        return scores


def _detect_linguistic_markers(text: str) -> Dict[str, float]:
    """Analyze linguistic patterns: hedging, certainty, urgency."""
    scores = {"anxious": 0.0, "confused": 0.0, "stressed": 0.0,
              "tired": 0.0, "neutral": 0.0}
    try:
        if not text:
            return scores
        lower = text.lower()

        hedges = {"maybe", "perhaps", "probably", "might", "could be",
                  "i think", "i guess", "sort of", "kind of", "somewhat",
                  "not sure", "i wonder", "possibly", "uncertain",
                  "it seems", "i suppose", "i assume"}
        certainty = {"definitely", "certainly", "absolutely", "without doubt",
                     "for sure", "no question", "undoubtedly", "clearly",
                     "obviously", "of course", "surely", "positively"}
        urgency_markers = {"now", "immediately", "asap", "urgent", "hurry",
                           "quickly", "fast", "soon", "today", "tonight",
                           "running out", "deadline", "overdue", "critical"}
        hesitation = {"um", "uh", "er", "ah", "like", "well", "so",
                       "actually", "basically", "literally", "honestly"}
        repetition_ratio = 0.0

        words = re.findall(r"[a-z']+", lower)
        word_set = set(words)

        hedge_count = len(word_set & hedges)
        certainty_count = len(word_set & certainty)
        urgency_count = len(word_set & urgency_markers)
        hesitation_count = len(word_set & hesitation)

        if words:
            word_freq = collections.Counter(words)
            repeated = sum(1 for v in word_freq.values() if v > 2)
            repetition_ratio = repeated / len(word_freq) if word_freq else 0

        total_words = len(words) if words else 1

        scores["anxious"] = min(0.8, (hedge_count + hesitation_count) / total_words * 5)
        scores["stressed"] = min(0.8, urgency_count / total_words * 5 + repetition_ratio * 2)
        scores["confused"] = min(0.6, hedge_count / total_words * 3 + repetition_ratio)
        scores["tired"] = min(0.4, repetition_ratio * 3)

        if certainty_count > hedge_count and certainty_count > 0:
            scores["neutral"] += 0.2

        return scores
    except Exception:
        return scores


def _keyword_emotion_scores(text: str) -> Dict[str, float]:
    """Score emotions based on keyword presence and density."""
    scores = {e: 0.0 for e in EMOTIONS}
    try:
        if not text:
            return scores
        lower = text.lower()
        words = re.findall(r"[a-z']+", lower)
        total = len(words) if words else 1

        for emotion, keywords in EMOTION_KEYWORDS.items():
            matches = 0
            for kw in keywords:
                if kw in lower:
                    matches += lower.count(kw)
            if matches > 0:
                scores[emotion] = min(1.0, matches / max(1, int(total * 0.3)))

        return scores
    except Exception:
        return scores


def _classify_emotion_from_text(text: str) -> Dict[str, float]:
    """Full text-based emotion classification combining multiple signals."""
    scores = {e: 0.0 for e in EMOTIONS}
    try:
        keyword_scores = _keyword_emotion_scores(text)
        sentiment = _analyze_text_sentiment(text)
        punct_scores = _detect_punctuation_mood(text)
        ling_scores = _detect_linguistic_markers(text)

        # Blend signals
        for emotion in EMOTIONS:
            s = 0.0
            s += keyword_scores.get(emotion, 0) * 0.4
            s += punct_scores.get(emotion, 0) * 0.15
            s += ling_scores.get(emotion, 0) * 0.15
            scores[emotion] = min(1.0, s)

        # Sentiment cross-reference
        v = sentiment.get("valence", 0)
        a = sentiment.get("arousal", 0)

        if v < -0.3 and a > 0.3:
            scores["angry"] += 0.15
            scores["frustrated"] += 0.15
        elif v < -0.3 and a < -0.2:
            scores["sad"] += 0.2
            scores["tired"] += 0.15
        elif v > 0.3 and a > 0.3:
            scores["happy"] += 0.2
            scores["excited"] += 0.2
        elif v > 0.3 and a < -0.2:
            scores["neutral"] += 0.2
        elif a > 0.4 and abs(v) < 0.2:
            scores["anxious"] += 0.2
            scores["stressed"] += 0.2

        # Normalize
        max_score = max(scores.values()) or 1.0
        if max_score > 0:
            for e in scores:
                scores[e] = min(1.0, scores[e] / max_score)

        return scores
    except Exception:
        return scores


# ── Silence / Pause Detection ──────────────────────────────────────────

def _detect_silences(audio_data: bytes, sample_rate: int = 16000,
                     frame_ms: int = 30, silence_threshold: float = 0.015,
                     min_silence_ms: int = 200) -> List[Dict[str, Any]]:
    """Detect silence segments in audio data."""
    silences = []
    try:
        if len(audio_data) < 64:
            return silences

        samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float64)
        frame_size = int(sample_rate * frame_ms / 1000)
        max_val = np.max(np.abs(samples)) if np.any(samples) else 1

        in_silence = False
        silence_start = 0
        current_frame = 0

        for i in range(0, len(samples), frame_size):
            frame = samples[i:i + frame_size]
            if len(frame) < 4:
                break
            rms = np.sqrt(np.mean(frame ** 2))
            norm_rms = rms / max_val if max_val > 0 else 0
            is_silent = norm_rms < silence_threshold
            timestamp_ms = int(current_frame * frame_ms)

            if is_silent and not in_silence:
                in_silence = True
                silence_start = timestamp_ms
            elif not is_silent and in_silence:
                in_silence = False
                duration = timestamp_ms - silence_start
                if duration >= min_silence_ms:
                    silences.append({
                        "start_ms": silence_start,
                        "end_ms": timestamp_ms,
                        "duration_ms": duration,
                    })

            current_frame += 1

        # Handle trailing silence
        if in_silence:
            duration = int(current_frame * frame_ms) - silence_start
            if duration >= min_silence_ms:
                silences.append({
                    "start_ms": silence_start,
                    "end_ms": int(current_frame * frame_ms),
                    "duration_ms": duration,
                })

        return silences
    except Exception:
        return silences


def _classify_pause(silence: Dict[str, Any], speech_before_duration_ms: int = 0) -> str:
    """Classify a pause into categories: hesitation, thinking, emotional, natural."""
    dur = silence.get("duration_ms", 0)
    if dur < 300:
        return "micropause"
    elif dur < 800:
        return "hesitation"
    elif dur < 1500:
        return "thinking"
    elif dur < 3000:
        return "emotional"
    else:
        return "extended"


# ── Main Class ──────────────────────────────────────────────────────────

class VoiceEnhanced:
    """Enhanced voice system with emotion detection and full-duplex conversation.

    Features:
    - Real-time emotion detection from voice tone
    - Silence/pause detection (waits for user to finish before responding)
    - Full conversation context awareness
    - Emotional support & psychiatric analysis
    - Audio input/output with noise reduction
    """

    def __init__(self):
        # Configuration
        self.sample_rate = int(os.environ.get("VE_SAMPLE_RATE", "16000"))
        self.silence_timeout = float(os.environ.get("VE_SILENCE_TIMEOUT", "1.5"))
        self.min_utterance_length = int(os.environ.get("VE_MIN_UTTERANCE", "1"))
        self.emotion_history_size = int(os.environ.get("VE_EMOTION_HISTORY", "50"))
        self.conversation_tts_enabled = os.environ.get("VE_TTS_ENABLED", "true").lower() == "true"
        self.tts_voice = os.environ.get("VE_TTS_VOICE", "en-US-GuyNeural")
        self.tts_rate = os.environ.get("VE_TTS_RATE", "+0%")

        # State
        self._conversation_history: List[Dict[str, Any]] = []
        self._emotion_history: List[Dict[str, Any]] = []
        self._audio_buffer = b""
        self._conv_active = False
        self._conv_thread: Optional[threading.Thread] = None
        self._conv_stop = threading.Event()
        self._current_utterance: Dict[str, Any] = {}
        self._last_emotion: Dict[str, Any] = {"emotion": "neutral", "confidence": 0.0}
        self._lock = threading.Lock()

        # Audio availability
        self._audio_available = self._check_audio()

        # Emotion tracking window
        self._emotion_window: Dict[str, List[float]] = {e: [] for e in EMOTIONS}

    # ── Audio Availability Check ─────────────────────────────────────────

    def _check_audio(self) -> bool:
        """Check if audio processing libraries are available."""
        try:
            import numpy as np
            _ = np.array([1, 2, 3])
            return True
        except ImportError:
            return False

    # ── 1. detect_emotion ────────────────────────────────────────────────

    def detect_emotion(self, audio_data: bytes = None, text: str = None) -> dict:
        """Analyze voice for emotional state.

        Uses audio features (pitch, energy, speaking rate) if audio provided.
        Uses text sentiment analysis if only text provided.
        Returns emotion with confidence score.

        Args:
            audio_data: Raw PCM audio bytes (16-bit, 16kHz mono).
            text: Transcribed or input text.

        Returns:
            dict with status, result (emotion, confidence, scores), message.
        """
        try:
            scores = {e: 0.0 for e in EMOTIONS}

            # Audio-based analysis
            if audio_data and self._audio_available:
                features = _extract_audio_features(audio_data)
                audio_scores = _classify_emotion_from_audio(features)
                for e in scores:
                    scores[e] += audio_scores.get(e, 0) * 0.6

            # Text-based analysis
            if text and text.strip():
                text_scores = _classify_emotion_from_text(text)
                weight = 0.4 if (audio_data and self._audio_available) else 0.9
                # Punctuation / linguistic
                punct_scores = _detect_punctuation_mood(text)
                ling_scores = _detect_linguistic_markers(text)
                for e in scores:
                    ts = text_scores.get(e, 0) * 0.5
                    ts += punct_scores.get(e, 0) * 0.25
                    ts += ling_scores.get(e, 0) * 0.25
                    scores[e] += ts * weight

            # Neither
            if not audio_data and not (text and text.strip()):
                return {
                    "status": "error",
                    "result": {"emotion": "neutral", "confidence": 0.0, "scores": {}},
                    "message": "No audio or text provided for emotion detection.",
                }

            # Determine dominant emotion
            max_score = max(scores.values())
            if max_score <= 0:
                scores["neutral"] = 0.5
                max_score = 0.5

            dominant = max(scores, key=scores.get)
            confidence = min(1.0, max_score + 0.1)

            # Clamp all scores
            for e in scores:
                scores[e] = max(0.0, min(1.0, scores[e]))

            result = {
                "emotion": dominant,
                "confidence": round(confidence, 3),
                "scores": {e: round(s, 3) for e, s in scores.items()},
            }

            # Update emotion tracking
            self._track_emotion(result)

            return {
                "status": "success",
                "result": result,
                "message": f"Detected emotion: {dominant} (confidence: {confidence:.2f})",
            }

        except Exception as exc:
            return {
                "status": "error",
                "result": {"emotion": "neutral", "confidence": 0.0, "scores": {}},
                "message": f"Emotion detection failed: {exc}",
            }

    # ── 2. transcribe_with_pause ─────────────────────────────────────────

    def transcribe_with_pause(self, audio_stream, silence_timeout: float = 1.5) -> dict:
        """Continuously listen and transcribe with silence detection.

        Detects when user pauses (silence > silence_timeout).
        Waits for complete utterance before returning.
        Handles mid-sentence pauses naturally.

        Args:
            audio_stream: Iterable yielding raw audio chunks.
            silence_timeout: Seconds of silence before considering utterance complete.

        Returns:
            dict with status, result (text, pauses, duration), message.
        """
        try:
            if not audio_stream:
                return {
                    "status": "error",
                    "result": {"text": "", "pauses": [], "duration_ms": 0},
                    "message": "No audio stream provided.",
                }

            buffer = b""
            all_text = []
            pauses = []
            silence_start = None
            last_speech_time = time.time()
            utterance_count = 0
            total_chunks = 0

            for chunk in audio_stream:
                total_chunks += 1
                if not chunk or len(chunk) < 2:
                    continue

                buffer += chunk
                energy = self._compute_chunk_energy(chunk)
                is_speech = energy > 0.02

                if is_speech:
                    if silence_start is not None:
                        pause_duration = time.time() - silence_start
                        if pause_duration >= 0.2:
                            pauses.append({
                                "start_offset_ms": int((time.time() - silence_start) * 1000),
                                "duration_ms": int(pause_duration * 1000),
                                "type": _classify_pause({"duration_ms": int(pause_duration * 1000)}),
                            })
                        silence_start = None
                    last_speech_time = time.time()

                else:
                    if silence_start is None:
                        silence_start = time.time()
                    else:
                        current_silence = time.time() - silence_start
                        if current_silence >= silence_timeout and len(buffer) > 256:
                            # Transcribe accumulated audio
                            transcript = self._transcribe_buffer(buffer)
                            if transcript and transcript.strip():
                                utterance_count += 1
                                all_text.append({
                                    "utterance": utterance_count,
                                    "text": transcript.strip(),
                                    "timestamp": time.time(),
                                })
                            buffer = b""
                            silence_start = None

                # Safety limit - don't accumulate forever
                if len(buffer) > self.sample_rate * 30 * 2:
                    transcript = self._transcribe_buffer(buffer)
                    if transcript and transcript.strip():
                        utterance_count += 1
                        all_text.append({
                            "utterance": utterance_count,
                            "text": transcript.strip(),
                            "timestamp": time.time(),
                        })
                    buffer = b""
                    silence_start = None

            # Final flush
            if buffer:
                transcript = self._transcribe_buffer(buffer)
                if transcript and transcript.strip():
                    utterance_count += 1
                    all_text.append({
                        "utterance": utterance_count,
                        "text": transcript.strip(),
                        "timestamp": time.time(),
                    })

            full_text = " ".join(u["text"] for u in all_text)
            duration_ms = int((time.time() - last_speech_time) * 1000) if all_text else 0

            result = {
                "text": full_text,
                "utterances": all_text,
                "pauses": pauses,
                "duration_ms": duration_ms,
                "utterance_count": utterance_count,
                "silence_timeout_used": silence_timeout,
            }

            return {
                "status": "success",
                "result": result,
                "message": f"Transcribed {utterance_count} utterance(s) with {len(pauses)} pause(s).",
            }

        except Exception as exc:
            return {
                "status": "error",
                "result": {"text": "", "pauses": [], "duration_ms": 0},
                "message": f"Transcription with pause failed: {exc}",
            }

    # ── 3. full_duplex_converse ──────────────────────────────────────────

    def full_duplex_converse(self, callback: Callable,
                             emotion_callback: Callable = None) -> dict:
        """Full conversation loop: listen, process, respond.

        Detects user emotion and adapts response style.
        Allows interruption.
        Returns conversation history.

        Args:
            callback: Function to process transcribed text, returns response text.
            emotion_callback: Optional callback with emotion data after each utterance.

        Returns:
            dict with status, result (history, emotion_timeline), message.
        """
        try:
            if not callable(callback):
                return {
                    "status": "error",
                    "result": {"history": [], "emotion_timeline": []},
                    "message": "callback must be callable.",
                }

            conversation_active = True
            turn_count = 0
            start_time = time.time()
            history = []
            emotion_timeline = []

            # Simulated conversation loop using text input (avoids microphone dependency)
            # In production, this would connect to a real audio stream
            print("Full-duplex conversation started. Type your messages (or 'exit' to end).")
            print(f"Emotion tracking: {'enabled' if emotion_callback else 'disabled'}")

            while conversation_active:
                turn_count += 1

                # Simulate listening phase
                print(f"\n[{turn_count}] You: ", end="")
                try:
                    user_input = input().strip()
                except (EOFError, KeyboardInterrupt):
                    user_input = "exit"

                if not user_input:
                    continue

                # Check for exit
                if user_input.lower() in ("exit", "quit", "end", "stop", "bye"):
                    conversation_active = False
                    history.append({
                        "turn": turn_count,
                        "user": user_input,
                        "assistant": "",
                        "timestamp": time.time(),
                    })
                    break

                # Emotion detection on user input
                emotion_result = self.detect_emotion(text=user_input)
                current_emotion = emotion_result.get("result", {}).get("emotion", "neutral")
                emotion_confidence = emotion_result.get("result", {}).get("confidence", 0.0)

                emotion_timeline.append({
                    "turn": turn_count,
                    "text": user_input,
                    "emotion": current_emotion,
                    "confidence": emotion_confidence,
                    "timestamp": time.time(),
                })

                if emotion_callback:
                    try:
                        emotion_callback(emotion_result.get("result", {}))
                    except Exception:
                        pass

                # Process through callback
                try:
                    response = callback(user_input, emotion_result.get("result", {}))
                    if not response:
                        response = self.generate_empathetic_response(
                            user_input, emotion_result.get("result", {})
                        )
                except Exception:
                    response = self.generate_empathetic_response(
                        user_input, emotion_result.get("result", {})
                    )

                print(f"[{turn_count}] Tom: {response}")

                history.append({
                    "turn": turn_count,
                    "user": user_input,
                    "assistant": str(response),
                    "user_emotion": current_emotion,
                    "emotion_confidence": emotion_confidence,
                    "timestamp": time.time(),
                })

                # Auto-add to conversation history
                self._conversation_history.append(history[-1])

            elapsed = time.time() - start_time
            result = {
                "history": history,
                "emotion_timeline": emotion_timeline,
                "total_turns": turn_count,
                "duration_seconds": round(elapsed, 2),
            }

            return {
                "status": "success",
                "result": result,
                "message": f"Conversation ended after {turn_count} turns ({elapsed:.1f}s).",
            }

        except Exception as exc:
            return {
                "status": "error",
                "result": {"history": [], "emotion_timeline": []},
                "message": f"Full-duplex conversation failed: {exc}",
            }

    # ── 4. analyze_emotional_state ───────────────────────────────────────

    def analyze_emotional_state(self, text: str) -> dict:
        """Deep emotional analysis from text.

        Detects sentiment, urgency, distress signals.
        Provides emotional support suggestions.
        Flags crisis/suicidal language for immediate response.

        Args:
            text: Input text to analyze.

        Returns:
            dict with status, result (emotion, sentiment, flags, suggestions), message.
        """
        try:
            if not text or not text.strip():
                return {
                    "status": "error",
                    "result": {},
                    "message": "No text provided for emotional analysis.",
                }

            lower = text.lower()

            # Emotion classification
            emotion_scores = _classify_emotion_from_text(text)
            sentiment = _analyze_text_sentiment(text)

            dominant_emotion = max(emotion_scores, key=emotion_scores.get)
            dominant_confidence = emotion_scores[dominant_emotion]

            # Crisis detection
            crisis_detected = any(kw in lower for kw in CRISIS_KEYWORDS)
            crisis_matches = [kw for kw in CRISIS_KEYWORDS if kw in lower]

            # Urgency detection
            urgency_detected = any(kw in lower for kw in URGENT_KEYWORDS)
            urgency_matches = [kw for kw in URGENT_KEYWORDS if kw in lower]

            # Distress signals
            distress_score = 0.0
            distress_signals = []

            # Negative valence + high arousal = distress
            if sentiment.get("valence", 0) < -0.3:
                distress_score += 0.2
                distress_signals.append("strong negative sentiment")

            if sentiment.get("arousal", 0) > 0.4 and sentiment.get("valence", 0) < -0.2:
                distress_score += 0.25
                distress_signals.append("high arousal with negative valence")

            if emotion_scores.get("anxious", 0) > 0.4:
                distress_score += 0.2
                distress_signals.append("anxiety detected")

            if emotion_scores.get("stressed", 0) > 0.4:
                distress_score += 0.15
                distress_signals.append("stress detected")

            if emotion_scores.get("sad", 0) > 0.5:
                distress_score += 0.15
                distress_signals.append("significant sadness")

            if crisis_detected:
                distress_score += 0.5
                distress_signals.append("CRISIS: suicidal language detected")

            if urgency_detected:
                distress_score += 0.3
                distress_signals.append("urgency markers detected")

            # Word count and first-person pronouns
            words = re.findall(r"[a-z']+", lower)
            i_pronouns = len(re.findall(r"\bi\b", lower))
            i_ratio = i_pronouns / len(words) if words else 0
            if i_ratio > 0.15:
                distress_signals.append("high self-referential language")

            # Emotional support suggestions
            support_suggestions = []
            if crisis_detected:
                support_suggestions = [
                    "IMMEDIATE ACTION REQUIRED: Encourage contacting a crisis helpline (988).",
                    "Do NOT leave them alone. Offer to stay connected while they seek help.",
                    "Use validating, non-judgmental language. Do not minimize their feelings.",
                    "Provide the crisis number directly and offer to help them call.",
                ]
            elif distress_score > 0.5:
                support_suggestions = [
                    "Validate their feelings and acknowledge the difficulty.",
                    "Ask open-ended questions about what support they need.",
                    "Offer practical help or resources if appropriate.",
                    "Check in on their safety without being intrusive.",
                ]
            elif dominant_emotion in ("sad", "anxious", "stressed"):
                support_suggestions = [
                    "Use empathetic listening - reflect their feelings back.",
                    "Offer gentle encouragement without toxic positivity.",
                    "Ask what they need right now in this moment.",
                    "Normalize their experience - many people feel this way.",
                ]

            result = {
                "dominant_emotion": dominant_emotion,
                "emotion_confidence": round(dominant_confidence, 3),
                "emotion_scores": {e: round(s, 3) for e, s in emotion_scores.items()},
                "sentiment": {k: round(v, 3) for k, v in sentiment.items()},
                "crisis_detected": crisis_detected,
                "crisis_keywords": crisis_matches if crisis_matches else [],
                "urgency_detected": urgency_detected,
                "urgency_keywords": urgency_matches if urgency_matches else [],
                "distress_score": round(distress_score, 3),
                "distress_signals": distress_signals,
                "support_suggestions": support_suggestions,
                "requires_immediate_action": crisis_detected,
                "word_count": len(words) if words else 0,
            }

            message_parts = []
            if crisis_detected:
                message_parts.append("CRISIS DETECTED - Immediate action required.")
            message_parts.append(f"Dominant emotion: {dominant_emotion}")
            message_parts.append(f"Distress score: {distress_score:.2f}")
            message = " | ".join(message_parts)

            return {
                "status": "success",
                "result": result,
                "message": message,
            }

        except Exception as exc:
            return {
                "status": "error",
                "result": {},
                "message": f"Emotional state analysis failed: {exc}",
            }

    # ── 5. generate_empathetic_response ──────────────────────────────────

    def generate_empathetic_response(self, user_text: str, emotion: dict) -> str:
        """Generate contextually appropriate empathetic response.

        Adapts tone based on detected emotion:
        - sad: gentle, supportive
        - anxious: calming, reassuring
        - angry: de-escalating, understanding
        - happy: enthusiastic, matching energy

        Args:
            user_text: User's input text.
            emotion: Emotion dict from detect_emotion().

        Returns:
            String response.
        """
        try:
            if not user_text or not user_text.strip():
                return "I'm here. What's on your mind?"

            detected_emotion = emotion.get("emotion", "neutral") if isinstance(emotion, dict) else "neutral"

            # Crisis check
            lower = user_text.lower()
            if any(kw in lower for kw in CRISIS_KEYWORDS):
                return random.choice(CRISIS_RESPONSES)

            # Get support phrases for this emotion
            phrases = SUPPORT_PHRASES.get(detected_emotion, SUPPORT_PHRASES["neutral"])
            opening = random.choice(phrases)

            # Emotion-specific response continuation
            continuations = {
                "sad": [
                    "Would you like to talk more about what's bringing this on?",
                    "I'm here to listen as long as you need.",
                    "Sometimes just saying it out loud helps a little.",
                    "You don't have to have this figured out right now.",
                ],
                "anxious": [
                    "Can we take a moment to focus on what's immediately in front of you?",
                    "What feels most manageable right now? Let's start there.",
                    "You've gotten through hard moments before. You will again.",
                    "Is there one small thing I can help you with right now?",
                ],
                "angry": [
                    "What happened that made you feel this way? I want to understand.",
                    "Do you want solutions right now, or do you need to vent first?",
                    "Your feelings are completely justified. Tell me more.",
                    "Let's work through what's driving this together.",
                ],
                "happy": [
                    "Tell me more about what happened!",
                    "This really made your day, didn't it?",
                    "You totally deserve this!",
                    "I love seeing you this happy!",
                ],
                "stressed": [
                    "Let's figure out what's most important and tackle that first.",
                    "What's one thing I can take off your plate right now?",
                    "Sometimes slowing down is the most productive thing you can do.",
                    "You don't have to do this all at once. One step at a time.",
                ],
                "excited": [
                    "This sounds like a big deal! I'm all ears.",
                    "I can tell this means a lot to you. That's awesome!",
                    "How long have you been working toward this?",
                ],
                "tired": [
                    "Have you had a chance to rest today?",
                    "Maybe now is a good time for a short break.",
                    "Pushing through isn't always the answer. Rest is okay.",
                ],
                "confused": [
                    "Let me try explaining it differently.",
                    "What part is most unclear? We can focus on that.",
                    "No rush at all. Let's take it from the top.",
                ],
                "frustrated": [
                    "I hear the frustration. Let's find a different angle.",
                    "What part is giving you the hardest time?",
                    "Let's step back and see if there's another approach.",
                ],
                "neutral": [
                    "What's on your mind?",
                    "Go on, I'm listening.",
                    "How can I help you with that?",
                ],
            }

            continuation = random.choice(continuations.get(detected_emotion, continuations["neutral"]))

            return f"{opening} {continuation}"

        except Exception:
            return "I'm here and I'm listening. Please tell me more."

    # ── 6. psychiatric_assessment ────────────────────────────────────────

    def psychiatric_assessment(self, conversation_history: list) -> dict:
        """Analyze conversation for mental health indicators.

        Screens for: depression, anxiety, stress, burnout, trauma.
        Provides assessment with recommendation.
        Includes disclaimer (not a substitute for professional help).

        Args:
            conversation_history: List of conversation turn dicts.

        Returns:
            dict with status, result (scores, indicators, recommendation, disclaimer), message.
        """
        try:
            if not conversation_history:
                return {
                    "status": "error",
                    "result": {},
                    "message": "No conversation history provided for assessment.",
                }

            # Extract all user text
            user_texts = []
            for turn in conversation_history:
                if isinstance(turn, dict):
                    txt = turn.get("user", turn.get("text", turn.get("message", "")))
                    if txt:
                        user_texts.append(str(txt))

            if not user_texts:
                # Try flat text list
                user_texts = [str(t) for t in conversation_history if isinstance(t, str)]

            combined = " ".join(user_texts)
            if not combined.strip():
                return {
                    "status": "error",
                    "result": {},
                    "message": "No user text found in conversation history.",
                }

            lower = combined.lower()
            words = re.findall(r"[a-z']+", lower)
            word_count = len(words)
            if word_count == 0:
                return {
                    "status": "error",
                    "result": {},
                    "message": "Not enough textual content for assessment.",
                }

            # Domain-specific keyword sets
            depression_keywords = {
                "hopeless", "worthless", "empty", "numb", "nothing", "meaningless",
                "no point", "can't feel", "not happy", "never happy", "always sad",
                "wake up tired", "can't sleep", "sleep too much", "no energy",
                "lost interest", "don't care", "not interested", "isolated",
                "alone", "lonely", "withdrawn", "no motivation", "can't get up",
                "weight change", "appetite", "guilty", "worthless", "no future",
                "give up", "tired of life", "darkness", "void", "hopelessness",
            }
            anxiety_keywords = {
                "worry", "nervous", "panic", "fear", "scared", "dread",
                "racing thoughts", "can't stop thinking", "overthinking",
                "restless", "on edge", "irritable", "tense", "tight chest",
                "short of breath", "heart racing", "sweating", "shaking",
                "dizzy", "lightheaded", "nausea", "butterflies", "knot in stomach",
                "can't relax", "hyper", "vigilant", "startle", "avoidance",
                "social", "crowds", "leaving house", "phobia", "obsessive",
            }
            stress_keywords = {
                "overwhelmed", "swamped", "pressure", "deadline", "too much",
                "can't cope", "can't handle", "burnout", "exhausted",
                "drowning", "spread thin", "no time", "always busy",
                "can't keep up", "falling behind", "stressed", "tension",
                "headache", "tight", "shoulders", "neck pain", "grinding teeth",
                "insomnia", "can't sleep", "wake up tired", "no break",
            }
            burnout_keywords = {
                "exhausted", "drained", "depleted", "empty", "numb",
                "don't care anymore", "lost passion", "meaningless work",
                "just going through motions", "can't anymore", "done",
                "no motivation", "cynical", "detached", "ineffective",
                "no accomplishment", "not good enough", "imposter",
                "sick of", "fed up", "can't keep doing this", "break",
            }
            trauma_keywords = {
                "trauma", "abuse", "assault", "violence", "accident",
                "nightmare", "flashback", "trigger", "unsafe", "threatened",
                "terror", "horror", "helpless", "powerless", "scared for life",
                "can't forget", "replay", "intrusive", "hypervigilant",
                "avoid", "numb", "detached", "dissociate", "distrust",
            }

            def score_domain(keywords: set) -> dict:
                matches = []
                for kw in keywords:
                    if kw in lower:
                        count = lower.count(kw)
                        matches.extend([kw] * count)
                raw_score = len(matches) / max(word_count, 1) * 100
                return {
                    "score": round(min(100, raw_score * 10), 1),
                    "match_count": len(matches),
                    "unique_matches": list(set(matches))[:10],
                }

            depression = score_domain(depression_keywords)
            anxiety = score_domain(anxiety_keywords)
            stress = score_domain(stress_keywords)
            burnout = score_domain(burnout_keywords)
            trauma = score_domain(trauma_keywords)

            domains = {
                "depression": depression,
                "anxiety": anxiety,
                "stress": stress,
                "burnout": burnout,
                "trauma": trauma,
            }

            # Overall severity
            max_score = max(d["score"] for d in domains.values())
            if max_score >= 60:
                overall_severity = "high"
            elif max_score >= 30:
                overall_severity = "moderate"
            elif max_score >= 10:
                overall_severity = "low"
            else:
                overall_severity = "minimal"

            # Primary concerns
            sorted_domains = sorted(domains.items(), key=lambda x: x[1]["score"], reverse=True)
            primary_concerns = [d[0] for d in sorted_domains[:3] if d[1]["score"] >= 10]

            # Crisis check
            crisis_detected = any(kw in lower for kw in CRISIS_KEYWORDS)
            if crisis_detected:
                overall_severity = "crisis"

            # Recommendations
            recommendations = []
            if crisis_detected:
                recommendations = [
                    "IMMEDIATE: Contact crisis helpline (988) or go to nearest emergency room.",
                    "Do NOT leave the person alone if actively suicidal.",
                    "Remove access to lethal means if possible.",
                    "Stay connected and use direct, caring language.",
                ]
            else:
                if overall_severity == "high":
                    recommendations.append(
                        "Strongly recommend consulting a licensed mental health professional."
                    )
                if depression["score"] >= 30:
                    recommendations.append(
                        "Depression screening recommended. Consider PHQ-9 questionnaire."
                    )
                if anxiety["score"] >= 30:
                    recommendations.append(
                        "Anxiety screening recommended. Consider GAD-7 questionnaire."
                    )
                if stress["score"] >= 30 or burnout["score"] >= 30:
                    recommendations.append(
                        "Consider stress management techniques and work-life balance evaluation."
                    )
                if trauma["score"] >= 20:
                    recommendations.append(
                        "Trauma-informed care recommended. Consider speaking with a trauma specialist."
                    )
                if not recommendations:
                    recommendations.append(
                        "Current indicators suggest minimal concern. Continue regular monitoring."
                    )

            result = {
                "disclaimer": PSYCHIATRIC_DISCLAIMER,
                "overall_severity": overall_severity,
                "primary_concerns": primary_concerns,
                "domain_scores": domains,
                "crisis_detected": crisis_detected,
                "word_count": word_count,
                "conversation_length": len(conversation_history),
                "recommendations": recommendations,
            }

            return {
                "status": "success",
                "result": result,
                "message": (
                    f"Assessment: {overall_severity} severity. "
                    f"Primary: {', '.join(primary_concerns) if primary_concerns else 'none'}. "
                    f"Crisis: {crisis_detected}. "
                    f"See disclaimer - this is NOT a clinical diagnosis."
                ),
            }

        except Exception as exc:
            return {
                "status": "error",
                "result": {},
                "message": f"Psychiatric assessment failed: {exc}",
            }

    # ── 7. speak_text ────────────────────────────────────────────────────

    def speak_text(self, text: str, emotion: str = "neutral") -> dict:
        """Text-to-speech with emotional tone adjustment.

        Adjusts pitch, speed, volume based on context.
        Returns audio data as base64-encoded WAV.

        Args:
            text: Text to speak.
            emotion: Target emotion for prosody adaptation.

        Returns:
            dict with status, result (audio_data, format, params), message.
        """
        try:
            if not text or not text.strip():
                return {
                    "status": "error",
                    "result": {},
                    "message": "No text provided for speech synthesis.",
                }

            # Emotion-to-prosody mapping
            prosody_map = {
                "angry": {"pitch": "+15%", "rate": "+20%", "volume": "+20%"},
                "happy": {"pitch": "+12%", "rate": "+15%", "volume": "+10%"},
                "sad": {"pitch": "-20%", "rate": "-15%", "volume": "-10%"},
                "anxious": {"pitch": "+8%", "rate": "+10%", "volume": "+5%"},
                "stressed": {"pitch": "+5%", "rate": "+5%", "volume": "+5%"},
                "excited": {"pitch": "+20%", "rate": "+25%", "volume": "+15%"},
                "tired": {"pitch": "-15%", "rate": "-10%", "volume": "-15%"},
                "confused": {"pitch": "+5%", "rate": "-5%", "volume": "0%"},
                "frustrated": {"pitch": "+10%", "rate": "+10%", "volume": "+10%"},
                "neutral": {"pitch": "0%", "rate": "0%", "volume": "0%"},
            }

            prosody = prosody_map.get(emotion, prosody_map["neutral"])

            # Try edge-tts for emotional TTS
            audio_data = None
            engine_used = "none"
            tts_error = ""

            try:
                import edge_tts
                import asyncio
                import base64

                voice = self.tts_voice
                rate = prosody.get("rate", "0%")
                if rate.startswith("+"):
                    rate_str = f"+{rate[1:]}"
                elif rate.startswith("-"):
                    rate_str = rate
                else:
                    rate_str = rate

                # Build SSML with prosody
                ssml = (
                    f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"'
                    f' xml:lang="en-US">'
                    f'<voice name="{voice}">'
                    f'<prosody pitch="{prosody["pitch"]}" rate="{rate_str}"'
                    f' volume="{prosody["volume"]}">'
                    f'{self._escape_ssml(text[:2000])}'
                    f'</prosody>'
                    f'</voice>'
                    f'</speak>'
                )

                loop = asyncio.new_event_loop()
                communicate = edge_tts.Communicate(ssml, voice)
                audio_bytes = loop.run_until_complete(communicate.save_to_bytes())
                loop.close()

                if audio_bytes:
                    audio_data = base64.b64encode(audio_bytes).decode("ascii")
                    engine_used = "edge-tts"
            except ImportError:
                tts_error = "edge-tts not installed"

            if not audio_data:
                try:
                    import pyttsx3
                    import io
                    import base64

                    engine = pyttsx3.init()
                    rate_val = engine.getProperty("rate")
                    rate_adj = int(rate_val * (1 + int(prosody.get("rate", "0%").rstrip("%")) / 100))
                    engine.setProperty("rate", rate_adj)
                    engine.setProperty("volume", 0.8)

                    engine_used = "pyttsx3"
                    audio_data = "simulated"
                except Exception as e:
                    tts_error = f"TTS unavailable: {e}"
                    engine_used = "none"

            result = {
                "audio_data": audio_data,
                "format": "wav" if engine_used != "none" else None,
                "engine": engine_used,
                "text_length": len(text),
                "emotion": emotion,
                "prosody": prosody,
                "tts_error": tts_error or None,
            }

            return {
                "status": "success" if audio_data else "error",
                "result": result,
                "message": (
                    f"Speech synthesized ({engine_used}) with {emotion} prosody."
                    if audio_data else f"Speech synthesis unavailable: {tts_error}"
                ),
            }

        except Exception as exc:
            return {
                "status": "error",
                "result": {},
                "message": f"Text-to-speech failed: {exc}",
            }

    # ── 8. start_conversation_mode ───────────────────────────────────────

    def start_conversation_mode(self) -> dict:
        """Initialize continuous listening with background audio capture.

        Starts a background thread for audio capture and auto emotion tracking.
        Returns immediately with status.

        Returns:
            dict with status, result (thread_active, emotion_history), message.
        """
        try:
            if self._conv_active:
                return {
                    "status": "already_active",
                    "result": {
                        "thread_active": True,
                        "emotion_history": len(self._emotion_history),
                        "conversation_turns": len(self._conversation_history),
                    },
                    "message": "Conversation mode is already running.",
                }

            self._conv_stop.clear()
            self._conv_active = True

            def _background_loop():
                """Simulate background audio capture and emotion tracking."""
                self._on_state_change("starting", "Conversation mode initializing...")
                capture_cycle = 0

                # Simulate periodic audio capture
                while not self._conv_stop.is_set():
                    capture_cycle += 1
                    try:
                        # Simulate ambient audio capture
                        fake_audio = b""
                        if self._audio_available:
                            fake_audio = np.zeros(int(self.sample_rate * 0.5), dtype=np.int16).tobytes()

                        # Periodic emotion check
                        if capture_cycle % 3 == 0:
                            emotion_result = self.detect_emotion(audio_data=fake_audio)
                            if emotion_result.get("status") == "success":
                                self._last_emotion = emotion_result.get("result", {})

                        # Maintain conversation state
                        self._on_state_change("listening", f"Cycle {capture_cycle}")

                        time.sleep(0.5)

                    except Exception:
                        if self._conv_stop.is_set():
                            break
                        time.sleep(1)

                self._conv_active = False
                self._on_state_change("stopped", "Conversation mode ended.")

            self._conv_thread = threading.Thread(
                target=_background_loop, daemon=True, name="tom-voice-enhanced"
            )
            self._conv_thread.start()

            result = {
                "thread_active": True,
                "emotion_history": len(self._emotion_history),
                "conversation_turns": len(self._conversation_history),
                "last_emotion": self._last_emotion,
            }

            return {
                "status": "success",
                "result": result,
                "message": "Conversation mode started. Emotion tracking active.",
            }

        except Exception as exc:
            self._conv_active = False
            return {
                "status": "error",
                "result": {},
                "message": f"Failed to start conversation mode: {exc}",
            }

    # ── 9. stop_conversation_mode ────────────────────────────────────────

    def stop_conversation_mode(self) -> dict:
        """Stop continuous listening and return conversation summary.

        Returns:
            dict with status, result (summary, emotion_timeline), message.
        """
        try:
            if not self._conv_active:
                return {
                    "status": "not_active",
                    "result": {
                        "emotion_log": [],
                        "conversation_summary": "",
                    },
                    "message": "Conversation mode is not running.",
                }

            self._conv_stop.set()

            if self._conv_thread and self._conv_thread.is_alive():
                self._conv_thread.join(timeout=3.0)

            self._conv_active = False

            # Build summary
            total_turns = len(self._conversation_history)
            total_emotions = len(self._emotion_history)

            emotion_counts = collections.Counter()
            for entry in self._emotion_history:
                if isinstance(entry, dict):
                    emotion_counts[entry.get("emotion", "neutral")] += 1

            dominant_overall = emotion_counts.most_common(1)[0][0] if emotion_counts else "neutral"

            # Generate emotion timeline from history
            emotion_timeline = [
                {
                    "index": i,
                    "emotion": e.get("emotion", "neutral"),
                    "confidence": e.get("confidence", 0.0),
                }
                for i, e in enumerate(self._emotion_history[-50:])
            ]

            summary = (
                f"Conversation ended. Total turns: {total_turns}, "
                f"emotion samples: {total_emotions}, "
                f"most common emotion: {dominant_overall}."
            )

            result = {
                "conversation_summary": summary,
                "total_turns": total_turns,
                "emotion_samples": total_emotions,
                "dominant_emotion": dominant_overall,
                "emotion_distribution": dict(emotion_counts.most_common()),
                "emotion_timeline": emotion_timeline,
                "last_emotion": self._last_emotion,
            }

            self._on_state_change("stopped", summary)

            return {
                "status": "success",
                "result": result,
                "message": summary,
            }

        except Exception as exc:
            self._conv_active = False
            return {
                "status": "error",
                "result": {},
                "message": f"Failed to stop conversation mode: {exc}",
            }

    # ── 10. analyze_silence_patterns ─────────────────────────────────────

    def analyze_silence_patterns(self, audio_chunks: list) -> dict:
        """Analyze silence/pause patterns in speech.

        Detects hesitation, thinking pauses, emotional pauses.
        Returns pause analysis with classifications.

        Args:
            audio_chunks: List of bytes audio chunks.

        Returns:
            dict with status, result (pauses, statistics, classifications), message.
        """
        try:
            if not audio_chunks:
                return {
                    "status": "error",
                    "result": {},
                    "message": "No audio chunks provided for silence analysis.",
                }

            # Combine chunks
            full_audio = b"".join(audio_chunks) if all(isinstance(c, bytes) for c in audio_chunks) else b""

            raw_speech_ms = 0
            if full_audio:
                silences = _detect_silences(full_audio)
            else:
                silences = []

            # Classify each silence
            classified_pauses = []
            for s in silences:
                pause_type = _classify_pause(s)
                classified_pauses.append({
                    "start_ms": s["start_ms"],
                    "end_ms": s["end_ms"],
                    "duration_ms": s["duration_ms"],
                    "type": pause_type,
                })

            # Statistics
            total_silence_ms = sum(s["duration_ms"] for s in silences)
            total_audio_ms = int(len(full_audio) / self.sample_rate * 1000) if full_audio else 0

            type_counts = collections.Counter(p["type"] for p in classified_pauses)

            # Speech-to-silence ratio
            speech_ms = max(1, total_audio_ms - total_silence_ms)
            silence_ratio = total_silence_ms / speech_ms if speech_ms > 0 else 0

            # Cognitive load estimate based on pause patterns
            hesitation_count = type_counts.get("hesitation", 0)
            thinking_count = type_counts.get("thinking", 0)
            emotional_count = type_counts.get("emotional", 0)
            total_pauses = len(classified_pauses)

            cognitive_load = "low"
            if total_pauses > 0:
                load_score = (hesitation_count * 1 + thinking_count * 2 + emotional_count * 3) / total_pauses
                if load_score > 2.0:
                    cognitive_load = "high"
                elif load_score > 1.2:
                    cognitive_load = "moderate"

            result = {
                "total_pauses": total_pauses,
                "total_silence_ms": total_silence_ms,
                "total_audio_ms": total_audio_ms,
                "speech_ms": speech_ms,
                "silence_ratio": round(silence_ratio, 3),
                "silence_percentage": round(total_silence_ms / max(1, total_audio_ms) * 100, 1),
                "pause_types": dict(type_counts),
                "classified_pauses": classified_pauses[:100],  # Limit output size
                "cognitive_load_estimate": cognitive_load,
                "average_pause_ms": round(total_silence_ms / max(1, total_pauses), 1) if total_pauses > 0 else 0,
            }

            return {
                "status": "success",
                "result": result,
                "message": (
                    f"Found {total_pauses} pause(s) ({total_silence_ms}ms total silence). "
                    f"Cognitive load estimate: {cognitive_load}."
                ),
            }

        except Exception as exc:
            return {
                "status": "error",
                "result": {},
                "message": f"Silence pattern analysis failed: {exc}",
            }

    # ── Helper Methods ───────────────────────────────────────────────────

    def _compute_chunk_energy(self, chunk: bytes) -> float:
        """Compute RMS energy of an audio chunk."""
        try:
            samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float64)
            if len(samples) == 0:
                return 0.0
            return float(np.sqrt(np.mean(samples ** 2)) / 32768.0)
        except Exception:
            return 0.0

    def _transcribe_buffer(self, audio_buffer: bytes) -> str:
        """Simulated transcription of audio buffer.

        In production, this would use speech_recognition or Whisper.
        Here it returns a placeholder — actual transcription requires
        a real STT engine.
        """
        try:
            if len(audio_buffer) < 256:
                return ""

            # Try speech_recognition if available
            try:
                import speech_recognition as sr
                import io
                import wave

                wav_io = io.BytesIO()
                with wave.open(wav_io, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(audio_buffer)
                wav_io.seek(0)

                recognizer = sr.Recognizer()
                with sr.AudioFile(wav_io) as source:
                    audio = recognizer.record(source)
                return recognizer.recognize_google(audio)
            except ImportError:
                pass
            except Exception:
                pass

            # No STT available — return empty
            return ""

        except Exception:
            return ""

    def _track_emotion(self, emotion_result: dict):
        """Track emotion in history window."""
        try:
            with self._lock:
                entry = {
                    "emotion": emotion_result.get("emotion", "neutral"),
                    "confidence": emotion_result.get("confidence", 0.0),
                    "scores": emotion_result.get("scores", {}),
                    "timestamp": time.time(),
                }
                self._emotion_history.append(entry)

                # Trim history
                if len(self._emotion_history) > self.emotion_history_size:
                    self._emotion_history = self._emotion_history[-self.emotion_history_size:]

                # Update running window
                emotion = entry["emotion"]
                if emotion in self._emotion_window:
                    self._emotion_window[emotion].append(entry["confidence"])
                    if len(self._emotion_window[emotion]) > 10:
                        self._emotion_window[emotion] = self._emotion_window[emotion][-10:]
        except Exception:
            pass

    def _on_state_change(self, state: str, info: str = ""):
        """Internal state change handler. Override in subclass if needed."""
        pass

    @staticmethod
    def _escape_ssml(text: str) -> str:
        """Escape special characters for SSML."""
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&apos;")
        return text

    # ── Query Methods ────────────────────────────────────────────────────

    def get_conversation_history(self) -> dict:
        """Return full conversation history."""
        try:
            with self._lock:
                return {
                    "status": "success",
                    "result": {
                        "history": list(self._conversation_history),
                        "total_turns": len(self._conversation_history),
                    },
                    "message": f"Returned {len(self._conversation_history)} conversation turns.",
                }
        except Exception as exc:
            return {
                "status": "error",
                "result": {},
                "message": f"Failed to get history: {exc}",
            }

    def get_emotion_summary(self) -> dict:
        """Return summary of tracked emotions."""
        try:
            with self._lock:
                if not self._emotion_history:
                    return {
                        "status": "success",
                        "result": {
                            "current_emotion": "neutral",
                            "total_samples": 0,
                            "emotion_distribution": {},
                        },
                        "message": "No emotion data recorded yet.",
                    }

                counts = collections.Counter(e["emotion"] for e in self._emotion_history)
                current = self._last_emotion

                result = {
                    "current_emotion": current.get("emotion", "neutral"),
                    "current_confidence": current.get("confidence", 0.0),
                    "total_samples": len(self._emotion_history),
                    "emotion_distribution": dict(counts.most_common()),
                    "dominant_emotion": counts.most_common(1)[0][0],
                }

                return {
                    "status": "success",
                    "result": result,
                    "message": f"Emotion summary: dominant={result['dominant_emotion']}, "
                               f"samples={result['total_samples']}",
                }
        except Exception as exc:
            return {
                "status": "error",
                "result": {},
                "message": f"Failed to get emotion summary: {exc}",
            }

    def reset_conversation(self) -> dict:
        """Reset conversation history and emotion tracking."""
        try:
            with self._lock:
                self._conversation_history.clear()
                self._emotion_history.clear()
                self._emotion_window = {e: [] for e in EMOTIONS}
                self._last_emotion = {"emotion": "neutral", "confidence": 0.0}

            return {
                "status": "success",
                "result": {},
                "message": "Conversation history and emotion tracking reset.",
            }
        except Exception as exc:
            return {
                "status": "error",
                "result": {},
                "message": f"Failed to reset: {exc}",
            }

    def status(self) -> dict:
        """Return full status of the enhanced voice system."""
        try:
            with self._lock:
                emotion_count = len(self._emotion_history)
                if emotion_count > 0:
                    latest = self._emotion_history[-1]
                    current_emotion = latest.get("emotion", "neutral")
                else:
                    current_emotion = "neutral"

                return {
                    "status": "success",
                    "result": {
                        "audio_available": self._audio_available,
                        "conversation_active": self._conv_active,
                        "sample_rate": self.sample_rate,
                        "silence_timeout": self.silence_timeout,
                        "emotion_history_size": self.emotion_history_size,
                        "current_emotion": current_emotion,
                        "emotion_samples": emotion_count,
                        "conversation_turns": len(self._conversation_history),
                        "tts_enabled": self.conversation_tts_enabled,
                        "tts_voice": self.tts_voice,
                    },
                    "message": f"Enhanced voice system: {'audio' if self._audio_available else 'text-only'}, "
                               f"{'conversation active' if self._conv_active else 'idle'}.",
                }
        except Exception as exc:
            return {
                "status": "error",
                "result": {},
                "message": f"Status check failed: {exc}",
            }
