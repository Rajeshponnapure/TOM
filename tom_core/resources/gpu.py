"""Measured GPU memory (RRM-012: decide from what is free now, not from what is installed)."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GpuMemory:
    total_mb: int
    used_mb: int
    free_mb: int


def query_gpu_memory(timeout: float = 4.0) -> Optional[GpuMemory]:
    """First GPU's memory from nvidia-smi, or None when there is no NVIDIA GPU / tool / answer."""
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        out = subprocess.run(
            [exe, "--query-gpu=memory.total,memory.used,memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        total, used, free = (int(float(x)) for x in out.stdout.strip().splitlines()[0].split(","))
        return GpuMemory(total_mb=total, used_mb=used, free_mb=free)
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return None


@dataclass(frozen=True)
class Admission:
    device: str          # "cuda" | "cpu"
    reason: str


def admit_gpu_job(need_mb: int, reserve_mb: int, *, requested: str = "auto",
                  gpu: Optional[GpuMemory] = None, cuda_available: bool = True) -> Admission:
    """PRD RRM-003: only load onto the GPU when measured free VRAM covers need + reserve."""
    if requested == "cpu":
        return Admission("cpu", "CPU requested by configuration")
    if not cuda_available:
        return Admission("cpu", "no usable CUDA runtime found")
    if gpu is None:
        return Admission("cpu", "GPU memory could not be measured")
    if gpu.free_mb >= need_mb + reserve_mb:
        return Admission("cuda", f"{gpu.free_mb} MB VRAM free >= {need_mb} MB needed + {reserve_mb} MB reserve")
    reason = f"only {gpu.free_mb} MB VRAM free; {need_mb} MB + {reserve_mb} MB reserve needed"
    if requested == "cuda":
        return Admission("cpu", f"CUDA requested but refused: {reason}")
    return Admission("cpu", reason)
