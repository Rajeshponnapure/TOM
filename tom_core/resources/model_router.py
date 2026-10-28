"""Pick the right local model for each kind of work, automatically (owner request 2026-10-27).

Every model call already names its task ("code_help", "document_docx", "analysis", …). The router maps
that to a category and picks the first model in the category's preference list that is installed AND
fits in the GPU memory measured right now (tom_core.resources.llm_admission, PRD RRM-002/003). A model
that would have to be split onto the CPU is skipped for interactive work; the configured model is the
last resort, so the router never makes TOM unable to answer.

Preference order comes from measurements on the owner's laptop (RTX 5060 8 GB, 2026-10-27,
docs/benchmarks/model-routing.md): quality on TOM's own kinds of work first, then speed.

    TOM_MODEL_ROUTING=0          off — every call uses the model it was given
    TOM_MODEL_CODE=<name>        pin a category (CODE, WRITING, REASONING, STRUCTURED, CHAT)
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

CATEGORIES: Tuple[Tuple[str, str], ...] = (
    ("code", r"code|fix_tests|scaffold|program|script"),
    ("structured", r"extract|_answers|json_retry|parse|classif|route$|nlp"),
    ("writing", r"document|website|email_draft|revise|letter|writing|copy|slides?|deck"),
    ("reasoning", r"analysis|research|specialist|plan|explanation|skill_route|web_search|reason|summar"),
)

# Measured 2026-10-27 (docs/benchmarks/model-routing.md). qwen3.5:9b passed every check (code fix executed
# against tests, exact JSON extraction, writing to length) and fits the 8 GB GPU; using one strong model for
# all heavy work also avoids 4-9 s model swaps. llama3.2:3b failed the code fix (3/5) but is 2x faster, so
# it keeps quick chat. qwen2.5-coder:14b scored no better here and runs 4x slower (split onto the CPU), so
# it is used only when pinned (TOM_MODEL_CODE=qwen2.5-coder:14b). deepseek-r1:8b broke JSON (0/5): never.
_HEAVY = ["qwen3.5:9b", "qwen3:8b", "qwen3.5:4b", "llama3.2:3b"]
PREFERENCES: Dict[str, List[str]] = {
    "code": list(_HEAVY),
    "writing": list(_HEAVY),
    "reasoning": list(_HEAVY),
    "structured": list(_HEAVY),
    "chat": ["llama3.2:3b", "qwen3.5:4b", "qwen3:8b"],
}
# Categories where waiting for a CPU/GPU split is worth it. None by default; a pinned model may always split.
SPLIT_OK: set = set()
# Quick work that should reuse a capable model already in GPU memory instead of forcing a swap.
STICKY = {"chat"}


def enabled() -> bool:
    return os.environ.get("TOM_MODEL_ROUTING", "1").strip() != "0"


def category(task: str) -> str:
    t = (task or "").lower()
    return next((c for c, rx in CATEGORIES if re.search(rx, t)), "chat")


@dataclass
class Choice:
    model: str
    category: str
    num_ctx: Optional[int]
    reason: str


_cache: Dict[str, Tuple[float, Choice]] = {}
CACHE_SECONDS = 20.0


def choose(task: str, current: str, *, sizes: Optional[Dict[str, int]] = None,
           admit: Optional[Callable] = None, loaded: Optional[Callable[[], Dict[str, int]]] = None,
           profile: str = "chat") -> Choice:
    """The model for `task`. `current` is what the caller would have used (the fallback)."""
    cat = category(task)
    pinned = os.environ.get(f"TOM_MODEL_{cat.upper()}", "").strip()
    key = f"{cat}|{current}|{pinned}"
    injected = sizes is not None or admit is not None or loaded is not None   # tests
    cacheable = not injected and cat not in STICKY     # what is loaded changes all the time
    hit = _cache.get(key)
    if hit and cacheable and time.monotonic() - hit[0] < CACHE_SECONDS:
        return hit[1]
    from tom_core.resources import llm_admission as la
    sizes = la.installed_sizes() if sizes is None else sizes
    admit = admit or (lambda m: la.admit(m, profile))
    candidates = ([pinned] if pinned else []) + [m for m in PREFERENCES.get(cat, []) if m != pinned]
    if cat in STICKY and not pinned:
        # Quick work uses a capable model that is already in GPU memory rather than swapping it out (a swap
        # on 8 GB costs 4-9 s: chat right after a document took 15 s in a live run, 2026-10-27).
        resident = loaded() if loaded is not None else ({} if injected else la.loaded_vram())
        warm = [m for m in candidates if m in resident]
        candidates = warm + [m for m in candidates if m not in warm]
    choice = None
    for m in candidates:
        if m not in sizes:
            continue
        a = admit(m)
        if m == pinned:                                    # the owner's explicit choice, even if it must split
            choice = Choice(m, cat, a.num_ctx if a.model == m else None, f"{cat} → {m} (pinned; {a.reason})")
            break
        if a.model != m:                                   # admission would swap it: it doesn't fit
            continue
        if a.decision in ("gpu", "smaller_context", "unmeasured") or (
                a.decision == "split_cpu_gpu" and (cat in SPLIT_OK or m == pinned)):
            choice = Choice(m, cat, a.num_ctx, f"{cat} → {m} ({a.decision}: {a.reason})")
            break
    if choice is None:
        choice = Choice(current, cat, None, f"{cat} → {current} (no preferred model fits right now)")
    if cacheable:
        _cache[key] = (time.monotonic(), choice)
    return choice
