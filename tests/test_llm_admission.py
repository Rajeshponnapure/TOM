"""R6: LLM VRAM admission (AT-008) and bounded OOM fallback (AT-009), with simulated GPUs/models."""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tom_core.resources import llm_admission as la  # noqa: E402
from tom_core.resources.gpu import GpuMemory  # noqa: E402

SIZES = {"llama3.2:3b": 1926, "qwen3:8b": 4983, "qwen2.5-coder:14b": 8572}


def _gpu(free):
    return GpuMemory(total_mb=8151, used_mb=8151 - free, free_mb=free)


def test_a_model_that_fits_runs_on_the_gpu_at_its_profile_context():
    adm = la.admit("qwen3:8b", "chat", gpu=_gpu(7124), sizes=SIZES, loaded={}, reserve=1024)
    assert adm.decision == "gpu" and adm.model == "qwen3:8b" and adm.num_ctx == 4096


def test_at008_low_vram_cuts_context_then_selects_the_configured_fallback(monkeypatch):
    # enough for qwen3:8b only at a smaller context
    adm = la.admit("qwen3:8b", "code", gpu=_gpu(6900), sizes=SIZES, loaded={}, reserve=1024)
    assert adm.decision == "smaller_context" and adm.num_ctx < 8192
    # not enough for qwen3:8b at all → the configured fallback is chosen, not a blind load
    monkeypatch.setenv("TOM_FALLBACK_MODEL", "llama3.2:3b")
    adm = la.admit("qwen3:8b", "chat", gpu=_gpu(4000), sizes=SIZES, loaded={}, reserve=1024)
    assert adm.decision == "fallback_model" and adm.model == "llama3.2:3b"
    assert "only" in adm.reason and "reserve" in adm.reason


def test_nothing_fits_means_a_stated_cpu_split_not_a_silent_failure():
    adm = la.admit("qwen2.5-coder:14b", "chat", gpu=_gpu(900), sizes=SIZES, loaded={}, reserve=1024)
    assert adm.decision == "split_cpu_gpu" and "CPU" in adm.reason


def test_idle_models_ollama_will_swap_out_count_as_available():
    adm = la.admit("qwen3:8b", "chat", gpu=_gpu(3500), sizes=SIZES, loaded={"llama3.2:3b": 3600}, reserve=1024)
    assert adm.decision == "gpu"


def test_unmeasurable_gpu_leaves_placement_to_ollama():
    adm = la.admit("qwen3:8b", gpu=None, sizes=SIZES, loaded={}, measure=False)
    assert adm.decision == "unmeasured" and adm.num_gpu is None


def test_oom_errors_are_recognised():
    assert la.is_oom(RuntimeError("CUDA error: out of memory"))
    assert la.is_oom(Exception("model requires more system memory (9.1 GiB) than is available"))
    assert not la.is_oom(ValueError("bad json"))


def test_oom_fallback_halves_context_then_steps_down_a_model():
    first = la.fallback_after_oom("qwen3:8b", 8192, sizes=SIZES)
    assert first.model == "qwen3:8b" and first.num_ctx == 4096
    second = la.fallback_after_oom("qwen3:8b", 2048, sizes=SIZES)
    assert second.model == "llama3.2:3b"
    last = la.fallback_after_oom("llama3.2:3b", 2048, sizes=SIZES)
    assert last.num_gpu == 0


class _OOMModel:
    """A fake chat model: the first invoke runs out of memory; the fallback copy answers."""
    calls = []

    def __init__(self, name="qwen3:8b", num_ctx=8192, fail=True):
        self.model, self.num_ctx, self.fail = name, num_ctx, fail

    def model_copy(self, update):
        return _OOMModel(update["model"], update["num_ctx"], fail=update.get("fail_again", False) or self._again)

    _again = False


def _agent(model, monkeypatch):
    import agent as agent_mod
    from tools import llm_factory
    monkeypatch.setattr(llm_factory, "provider", lambda: "ollama")
    monkeypatch.setattr(la, "installed_sizes", lambda: SIZES)
    a = agent_mod.TomAgent.__new__(agent_mod.TomAgent)
    a.llm, a.model_timeout_seconds = model, 5
    return a


class _Chain:
    def __or__(self, model):
        class Bound:
            async def ainvoke(self, payload):
                _OOMModel.calls.append((model.model, model.num_ctx))
                if model.fail:
                    raise RuntimeError("CUDA error: out of memory")
                return "answer"
        return Bound()


def test_at009_one_bounded_fallback_after_oom(monkeypatch):
    _OOMModel.calls = []
    a = _agent(_OOMModel(), monkeypatch)
    assert asyncio.run(a._invoke_llm(_Chain(), {}, "chat")) == "answer"
    assert _OOMModel.calls == [("qwen3:8b", 8192), ("qwen3:8b", 4096)]
    assert "retrying at 4096" in a.last_llm_fallback


def test_at009_a_second_oom_is_reported_not_retried_again(monkeypatch):
    _OOMModel.calls = []
    monkeypatch.setattr(_OOMModel, "_again", True)
    a = _agent(_OOMModel(), monkeypatch)
    with pytest.raises(RuntimeError, match="the one retry"):
        asyncio.run(a._invoke_llm(_Chain(), {}, "chat"))
    assert len(_OOMModel.calls) == 2
