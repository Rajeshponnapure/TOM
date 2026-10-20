"""TTS worker process: Windows OneCore voices through WinRT, isolated from TOM's process.

WinRT must not load inside TOM itself (it breaks onnxruntime/torch/CTranslate2 there), so all
synthesis happens here and only WAV file paths travel back.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
import time

from tom_core.voice.workers import fail_startup, protocol_stdout, serve


def main() -> None:
    protocol_stdout()
    try:
        from winrt.windows.media.speechsynthesis import SpeechSynthesizer
        from winrt.windows.storage.streams import DataReader
    except Exception as exc:
        fail_startup(f"Windows speech (WinRT) unavailable: {type(exc).__name__}: {exc}. "
                     "Fix: pip install winrt-Windows.Media.SpeechSynthesis winrt-Windows.Storage.Streams")
        return

    from tom_core.voice.tts import choose_voice

    synth = SpeechSynthesizer()
    voices = list(SpeechSynthesizer.all_voices)
    catalogue = [{"name": v.display_name, "language": v.language, "gender": str(v.gender)} for v in voices]
    out_dir = tempfile.mkdtemp(prefix="tom_tts_")
    counter = [0]

    async def _synth(text: str) -> bytes:
        stream = await synth.synthesize_text_to_stream_async(text)
        reader = DataReader(stream.get_input_stream_at(0))
        await reader.load_async(stream.size)
        buf = bytearray(stream.size)
        reader.read_bytes(buf)
        return bytes(buf)

    def handle(op: str, args: dict) -> dict:
        if op == "voices":
            return {"voices": catalogue}
        if op != "synth":
            raise ValueError(f"unknown op {op!r}")
        chosen = choose_voice([(c["name"], c["language"]) for c in catalogue], args.get("preference") or [])
        if chosen is None:
            raise RuntimeError("No Windows voices are installed.")
        voice = voices[chosen]
        if synth.voice.display_name != voice.display_name:
            synth.voice = voice
        try:
            synth.options.speaking_rate = float(args.get("rate", 1.0))
        except Exception:
            pass  # older Windows builds without SpeechSynthesizerOptions.SpeakingRate
        started = time.perf_counter()
        data = asyncio.run(_synth(str(args.get("text", ""))[:4000]))
        counter[0] += 1
        path = os.path.join(out_dir, f"utt_{counter[0]}.wav")
        with open(path, "wb") as fh:
            fh.write(data)
        return {"wav": path, "voice": voice.display_name, "language": voice.language,
                "seconds": round(time.perf_counter() - started, 3)}

    serve(handle, {"voices": catalogue, "pid": os.getpid()})


if __name__ == "__main__":
    main()
