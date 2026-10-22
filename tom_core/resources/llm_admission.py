"""LLM admission and OOM fallback (PRD R6: RRM-002/003/006/009/012, §6.3, AT-008, AT-009).

Before a local model is used, its peak VRAM is predicted from what Ollama reports (weights) plus a
KV-cache estimate for the context size, and compared with the VRAM measured free *now* minus a
safety reserve. If it does not fit, TOM tries a smaller context profile, then a smaller installed
model (TOM_FALLBACK_MODEL first), and only then lets Ollama split the model across CPU and GPU —
saying why, so a slow answer is explained instead of mysterious. An out-of-memory failure during
inference gets exactly one retry with a smaller profile (fallback_model), never a loop.

Numbers here are estimates (KV ≈ 0.125 MB per token of context, the order of an 8B model with
grouped-query attention); the benchmark harness (tests/manual/benchmark_llm.py) records measured values.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional

from tom_core.resources.gpu import GpuMemory, query_gpu_memory

# Context sizes per kind of work (num_ctx). TOM_NUM_CTX overrides all of them.
PROFILES: Dict[str, int] = {"chat": 4096, "plan": 4096, "fast": 2048, "code": 8192, "document": 8192}
MIN_CTX = 2048
KV_MB_PER_TOKEN = 0.125
RUNTIME_OVERHEAD_MB = 300
DEFAULT_RESERVE_MB = 1024           # leave room for the ASR model, the desktop and other apps
CACHE_SECONDS = 30.0

OOM_MARKERS = ("out of memory", "cuda error", "cudamalloc", "requires more system memory",
               "not enough memory", "failed to allocate", "insufficient memory", "oom")


@dataclass(frozen=True)
class LlmAdmission:
    model: str
    num_ctx: int
    num_gpu: Optional[int]          # None: Ollama decides (all layers on GPU when it fits); 0: CPU only
    decision: str                   # "gpu" | "smaller_context" | "fallback_model" | "split_cpu_gpu" | "unmeasured"
    reason: str
    need_mb: int = 0
    free_mb: int = 0


def reserve_mb() -> int:
    try:
        return int(os.environ.get("TOM_VRAM_RESERVE_MB", DEFAULT_RESERVE_MB))
    except ValueError:
        return DEFAULT_RESERVE_MB


def profile_ctx(profile: str) -> int:
    try:
        override = int(os.environ.get("TOM_NUM_CTX", "0"))
    except ValueError:
        override = 0
    return override if override >= MIN_CTX else PROFILES.get(profile, PROFILES["chat"])


def need_mb(weights_mb: int, num_ctx: int) -> int:
    return int(weights_mb * 1.05 + num_ctx * KV_MB_PER_TOKEN + RUNTIME_OVERHEAD_MB)


def is_oom(exc: BaseException) -> bool:
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(m in text for m in OOM_MARKERS)


# ── what Ollama reports ─────────────────────────────────────────────────────
def _get(path: str, timeout: float = 2.0) -> dict:
    base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    with urllib.request.urlopen(base + path, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def installed_sizes() -> Dict[str, int]:
    """{model: weights MB} for installed chat models (embedding models left out)."""
    try:
        models = _get("/api/tags").get("models", [])
    except Exception:
        return {}
    return {m["name"]: int(m.get("size", 0) / 2**20) for m in models
            if "embed" not in m["name"].lower() and m.get("size")}


def loaded_vram() -> Dict[str, int]:
    """{model: MB of VRAM} for models Ollama has loaded right now."""
    try:
        models = _get("/api/ps").get("models", [])
    except Exception:
        return {}
    return {m["name"]: int(m.get("size_vram", 0) / 2**20) for m in models}


# ── the decision ─────────────────────────────────────────────────────────────
def admit(model: str, profile: str = "chat", *, gpu: Optional[GpuMemory] = None,
          sizes: Optional[Dict[str, int]] = None, loaded: Optional[Dict[str, int]] = None,
          reserve: Optional[int] = None, measure: bool = True) -> LlmAdmission:
    reserve = reserve_mb() if reserve is None else reserve
    ctx = profile_ctx(profile)
    gpu = gpu if gpu is not None or not measure else query_gpu_memory()
    sizes = installed_sizes() if sizes is None else sizes
    loaded = loaded_vram() if loaded is None else loaded
    if gpu is None or model not in sizes:
        why = "GPU memory could not be measured" if gpu is None else f"size of {model} unknown"
        return LlmAdmission(model, ctx, None, "unmeasured", f"{why}; Ollama decides placement")
    # Memory held by the model itself, or by other idle models Ollama will swap out (RRM-004:
    # one GPU-heavy inference workload at a time), counts as available for it.
    budget = gpu.free_mb + loaded.get(model, 0) + sum(v for k, v in loaded.items() if k != model and k in sizes)
    for c in [ctx] + [x for x in (4096, MIN_CTX) if x < ctx]:
        need = need_mb(sizes[model], c)
        if budget - reserve >= need:
            kind = "gpu" if c == ctx else "smaller_context"
            return LlmAdmission(model, c, None, kind, f"{need} MB needed, {budget} MB available "
                                f"(reserve {reserve} MB)" + ("" if c == ctx else f"; context cut {ctx}→{c}"),
                                need, budget)
    preferred = os.environ.get("TOM_FALLBACK_MODEL", "").strip()
    candidates: List[str] = ([preferred] if preferred in sizes else []) + sorted(
        (m for m in sizes if sizes[m] < sizes[model] and m != preferred), key=lambda m: -sizes[m])
    for alt in candidates:
        need = need_mb(sizes[alt], MIN_CTX)
        if budget - reserve >= need:
            return LlmAdmission(alt, MIN_CTX, None, "fallback_model",
                                f"{model} needs {need_mb(sizes[model], MIN_CTX)} MB but only {budget - reserve} MB "
                                f"is free after the {reserve} MB reserve; using {alt} instead", need, budget)
    return LlmAdmission(model, MIN_CTX, None, "split_cpu_gpu",
                        f"{model} does not fit in {budget - reserve} MB of free VRAM and no smaller model does; "
                        "Ollama will run part of it on the CPU (slower)", need_mb(sizes[model], MIN_CTX), budget)


_cache: Dict[tuple, tuple] = {}


def cached_admit(model: str, profile: str = "chat") -> LlmAdmission:
    key = (model, profile)
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
        return hit[1]
    result = admit(model, profile)
    _cache[key] = (time.monotonic(), result)
    return result


def fallback_after_oom(model: str, num_ctx: Optional[int], *, sizes: Optional[Dict[str, int]] = None) -> LlmAdmission:
    """The one retry after an out-of-memory failure: half the context (not below MIN_CTX) and, when
    that is already the minimum, the next smaller installed model; CPU-only as the last resort."""
    sizes = installed_sizes() if sizes is None else sizes
    ctx = max(MIN_CTX, int((num_ctx or PROFILES["chat"]) // 2))
    if num_ctx and num_ctx > MIN_CTX:
        return LlmAdmission(model, ctx, None, "smaller_context", f"out of memory at num_ctx={num_ctx}; retrying at {ctx}")
    smaller = sorted((m for m in sizes if model in sizes and sizes[m] < sizes[model]), key=lambda m: -sizes[m])
    if smaller:
        return LlmAdmission(smaller[0], MIN_CTX, None, "fallback_model", f"out of memory with {model}; retrying with {smaller[0]}")
    return LlmAdmission(model, MIN_CTX, 0, "split_cpu_gpu", f"out of memory with {model}; retrying on the CPU only")
