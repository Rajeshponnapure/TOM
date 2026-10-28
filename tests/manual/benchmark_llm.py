"""Model profile benchmark (PRD R6, RRM-009, §6.4). Not a unit test — run by hand:

    .venv311\\Scripts\\python.exe tests\\manual\\benchmark_llm.py llama3.2:3b qwen3:8b

For each model: load time, prompt and generation speed (tokens/s, from Ollama's own counters),
peak VRAM (nvidia-smi), and structured-output reliability — how many of the planner prompts come
back as a usable plan with only registered tools. Writes docs/benchmarks/llm-profiles.md.
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from tom_core.llm_json import parse_model_json  # noqa: E402
from tom_core.planning import planner  # noqa: E402
from tom_core.resources.gpu import query_gpu_memory  # noqa: E402
from tom_core.tools.registry import get_registry  # noqa: E402

BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
GOALS = [
    "List the 3 largest files in C:/Users/me/Downloads",
    "Create a folder C:/tmp/reports and write notes.txt in it saying 'done'",
    "Show the git status of the repository at C:/code/app",
    "What processes are using the most memory right now?",
    "Search the web for the latest Python release",
]
CHAT = "In two sentences, explain what a context window is in a language model."


def _post(path, body, timeout=300):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _chat(model, system, user, num_ctx=4096):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
    body = {"model": model, "messages": msgs, "stream": False, "options": {"temperature": 0, "num_ctx": num_ctx}}
    if "qwen3" in model:
        body["think"] = False
    return _post("/api/chat", body)


def bench(model):
    reg = get_registry()
    names = set(reg.names())
    alias = {n.replace(".", "_"): n for n in names}
    tools = reg.catalogue()
    for a, n in alias.items():
        tools = tools.replace(f"{n}(", f"{a}(")
    system = planner._PLAN_SYSTEM.format(tools=tools, max_steps=6, **planner._known_folders())
    _post("/api/generate", {"model": model, "keep_alive": 0})          # unload: measure a cold load
    t = time.perf_counter()
    first = _chat(model, "", CHAT)
    cold = time.perf_counter() - t
    peak = query_gpu_memory()
    gen_tps = first.get("eval_count", 0) / max(first.get("eval_duration", 1) / 1e9, 1e-9)
    ok, times = 0, []
    for g in GOALS:
        t = time.perf_counter()
        r = _chat(model, system, f"Goal: {g}")
        times.append(time.perf_counter() - t)
        try:
            data = parse_model_json(r["message"]["content"])
            steps = data.get("steps") if isinstance(data, dict) else data
            if steps and all(alias.get(s.get("tool"), s.get("tool")) in names for s in steps):
                ok += 1
        except Exception:
            pass
    return {"model": model, "cold_load_s": round(first.get("load_duration", 0) / 1e9, 1),
            "first_answer_s": round(cold, 1), "gen_tokens_per_s": round(gen_tps, 1),
            "plan_valid": f"{ok}/{len(GOALS)}", "plan_avg_s": round(sum(times) / len(times), 1),
            "gpu_used_mb": peak.used_mb if peak else None}


def main(models):
    rows = [bench(m) for m in models]
    out = os.path.join(ROOT, "docs", "benchmarks")
    os.makedirs(out, exist_ok=True)
    gpu = query_gpu_memory()
    lines = [f"# Local model profiles (measured {datetime.now():%Y-%m-%d %H:%M})", "",
             f"GPU: {gpu.total_mb} MB total" if gpu else "GPU: not measured", "",
             "| Model | Cold load s | First answer s | Gen tok/s | Valid plans | Avg plan s | GPU used MB |",
             "|---|---|---|---|---|---|---|"]
    lines += [f"| {r['model']} | {r['cold_load_s']} | {r['first_answer_s']} | {r['gen_tokens_per_s']} | "
              f"{r['plan_valid']} | {r['plan_avg_s']} | {r['gpu_used_mb']} |" for r in rows]
    lines += ["", "Valid plan = parsable JSON whose every step names a registered tool (5 fixed goals, temperature 0).",
              "Produced by `tests/manual/benchmark_llm.py`."]
    with open(os.path.join(out, "llm-profiles.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1:] or ["llama3.2:3b"])
