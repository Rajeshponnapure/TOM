"""ASR worker process: faster-whisper, loaded once, from local files only.

Started by tom_core.voice.asr.LocalWhisperASR — not meant to be run by hand. Configuration comes
from the environment the client sets (TOM_ASR_*), already resolved to a concrete device.
"""
from __future__ import annotations

import os
import sys
import time

from tom_core.voice.workers import fail_startup, protocol_stdout, serve


def _load(model: str, download_root: str, device: str, cuda_dir: str):
    if device == "cuda" and cuda_dir:
        os.environ["PATH"] = cuda_dir + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(cuda_dir)
    import numpy as np
    from faster_whisper import WhisperModel

    compute = "int8_float16" if device == "cuda" else "int8"
    threads = max(4, (os.cpu_count() or 8) - 4)
    kwargs = {"device": device, "compute_type": compute, "local_files_only": True}
    if device == "cpu":
        kwargs["cpu_threads"] = threads
    if download_root:
        kwargs["download_root"] = download_root
    started = time.perf_counter()
    m = WhisperModel(model, **kwargs)
    # Warm-up encode: CUDA library/memory problems only surface on the first encode, not at load.
    segments, _info = m.transcribe(np.zeros(16000, dtype=np.float32), language="en",
                                   vad_filter=False, without_timestamps=True)
    list(segments)
    return m, compute, time.perf_counter() - started


def main() -> None:
    protocol_stdout()   # before any native import, so library prints can't corrupt the protocol
    model_name = os.environ.get("TOM_ASR_MODEL", "large-v3-turbo")
    download_root = os.environ.get("TOM_ASR_DOWNLOAD_ROOT", "")
    device = os.environ.get("TOM_ASR_DEVICE_RESOLVED", "cpu")
    cuda_dir = os.environ.get("TOM_CUDA_LIB_DIR_RESOLVED", "")
    fallback_reason = ""
    try:
        model, compute, load_s = _load(model_name, download_root, device, cuda_dir)
    except Exception as exc:
        if device != "cuda":
            fail_startup(f"Could not load ASR model '{model_name}': {type(exc).__name__}: {exc}")
        # PRD §6.3: one bounded fallback to a smaller/cheaper profile, then report.
        fallback_reason = f"CUDA load failed ({type(exc).__name__}: {str(exc)[:160]}); using CPU"
        print(f"[asr-worker] {fallback_reason}", file=sys.stderr, flush=True)
        device = "cpu"
        try:
            model, compute, load_s = _load(model_name, download_root, "cpu", "")
        except Exception as exc2:
            fail_startup(f"Could not load ASR model '{model_name}' on CPU either: {type(exc2).__name__}: {exc2}")

    from tom_core.voice.asr import clean_transcript

    def handle(op: str, args: dict) -> dict:
        if op == "ping":
            return {}
        if op != "transcribe":
            raise ValueError(f"unknown op {op!r}")
        started = time.perf_counter()
        segments, info = model.transcribe(
            args["wav"], language=args.get("language") or None, beam_size=int(args.get("beam_size", 1)),
            vad_filter=True, condition_on_previous_text=False, without_timestamps=True,
            hotwords=args.get("hotwords") or None)
        segs = [{"text": s.text, "no_speech_prob": s.no_speech_prob, "avg_logprob": s.avg_logprob}
                for s in segments]
        return {"text": clean_transcript(segs), "language": info.language,
                "language_probability": round(float(info.language_probability), 3),
                "audio_seconds": round(float(info.duration), 2),
                "seconds": round(time.perf_counter() - started, 3)}

    serve(handle, {"model": model_name, "device": device, "compute_type": compute,
                   "load_seconds": round(load_s, 2), "fallback": fallback_reason, "pid": os.getpid()})


if __name__ == "__main__":
    main()
