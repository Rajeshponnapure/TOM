# R0 Baseline Report

> Measured 2026-10-20 on the target laptop, commit `4dd8da7`. Methods are given so each number can be re-run.
> Numbers marked *indicative* were taken while another client was using the same Ollama server; treat them as
> order-of-magnitude only and re-measure on a quiet machine before setting budgets (PRD §6.5).

## 1. Hardware / OS (verified, not user-reported)

| Item | PRD assumption | Measured | Method |
|---|---|---|---|
| OS | Windows 11 **Pro** | Windows 11 **Home** 10.0.26300 | `Win32_OperatingSystem` |
| CPU | "Intel Core i9, SKU unconfirmed" | Intel Core **Ultra 9 275HX**, 24 cores / 24 threads | `Win32_Processor` |
| GPU | RTX 5060, 8 GB | NVIDIA GeForce RTX 5060 **Laptop** GPU, 8151 MiB, driver 617.42 | `nvidia-smi` |
| RAM | 32 GB | 31.5 GB visible; **10.1 GB free** at audit time | `Win32_OperatingSystem` |
| Disk C: | 1 TB | 184 GB free / 923 GB | `Get-PSDrive C` |

Implications: Home edition has no Group Policy editor / Hyper-V management UI. Anything in the PRD relying on Pro-only
features (e.g. Windows Sandbox) needs a fallback. Free RAM was ~⅓ of installed at idle, so RRM-012 ("use measured
available capacity") matters.

## 2. Python environment

| Item | Value |
|---|---|
| Interpreter | `.venv311` → Python 3.11.9 (`pyproject.toml` pins `>=3.11,<3.12`) |
| Lock | `requirements.txt`, exact pins (no hash lock file) |
| Missing vs PRD §12.4 | `psutil` (not pinned, not installed), `pywinauto` (not pinned), `pynvml` (absent; `nvidia-smi` CLI used instead) |
| Present | `pydantic 2.13.5` (transitive), `playwright 1.59.0`, `apscheduler 3.11.2` |

## 3. Test suite

| Metric | Value | Method |
|---|---|---|
| Result | **453 passed, 15 skipped, 0 failed** | `.venv311/Scripts/python -m pytest -q` |
| Wall-clock | **602.75 s** first run, **330.06 s** second run (high variance) | same |
| Slowest test | `test_e2e_agent.py::test_everyday_words_do_not_start_a_connector_call[draft a note about the commit …]` **92.6 s**; next `test_send_email_asks_once…` 28.5 s | `pytest --durations=25` |
| CI | GitHub Actions `ci.yml`: compileall + `ruff` (E9/F63/F7/F82) + `pytest -v`, 20-min timeout | — |

The 10-minute wall-clock is half the CI timeout. See §7.

## 4. Start-up

| Metric | Value | Method |
|---|---|---|
| `import agent` | 3.5 – 6.3 s (3 runs) | scratch probe, `HINDSIGHT_ENABLED=0`, `TOM_LLM_PROVIDER=ollama` |
| `TomAgent()` construction | 2.1 – 3.3 s | same |
| Process working set after construction | **362 MB** | `GetProcessMemoryInfo` |
| Resolved model slots | primary/fast/code = `qwen3:8b`, embed = `nomic-embed-text` | `TomAgent.model_name` etc. |

GUI start-up was not measured (needs an interactive session); do this in R8.

## 5. Model runtime (Ollama)

Installed models (`/api/tags`):

| Model | On-disk | Params | Quant | Fits 8 GB VRAM with headroom? |
|---|---|---|---|---|
| qwen3:8b | 4.87 GB | 8.2 B | Q4_K_M | Weights yes; **not with default 40 k context** (see below) |
| qwen3.5:4b | 3.16 GB | 4.7 B | Q4_K_M | Likely — needs measurement |
| qwen3.5:9b | 6.14 GB | 9.7 B | Q4_K_M | Marginal |
| deepseek-r1:8b | 4.87 GB | 8.2 B | Q4_K_M | Weights yes |
| qwen2.5-coder:14b | 8.37 GB | 14.8 B | Q4_K_M | **No** — weights alone exceed VRAM |
| SparkLLM/Spark-X2.5-4B | 7.66 GB | 4.1 B | **BF16** (unquantized) | No headroom |
| nomic-embed-text | 0.26 GB | 137 M | F16 | Yes |

**Key finding (solid, from `/api/ps`):** `qwen3:8b` loaded at its default `context_length=40960` reports
`size=11098 MB, size_vram=5762 MB`, so **~48 % of the model runs from system RAM**. The KV cache for a 40 k
context roughly doubles the footprint. A smaller `num_ctx` profile is the first R6 lever (RRM-002).

*Indicative* (shared server): warm generation ≈ 34–38 tok/s; a request with the model already resident returns in
0.4–2.1 s for a 2-token reply. A clean cold-load time could not be isolated because another client kept reloading
the model; re-measure in R6 with the benchmark harness (10 repeats, cold/warm separated, PRD §6.5).

Idle GPU memory used by other processes fluctuated between 2.6 and 5.9 GB during the audit. That is a large and
variable share of 8 GB, so the VRAM reserve must be computed from live `nvidia-smi` readings, not a constant.

## 6. Configuration and privacy routes (non-secret values only)

| Setting | Value | Consequence |
|---|---|---|
| `TOM_LLM_PROVIDER` | defined **twice** in `.env`: `ollama`, then `groq` | Effective provider is **Groq (cloud)**. Conflicts with "local-first" default (RRM-007) |
| `OLLAMA_MODEL/FAST/CODE` | `llama3.2:3b` | **Not installed**; silently resolved to `qwen3:8b` |
| `GROQ_API_KEY` | present | If `TOM_LLM_PROVIDER` were unset, `llm_factory.provider()` would also auto-pick Groq |
| `HINDSIGHT_API_KEY` | present, `HINDSIGHT_ENABLED=1` | Memory content goes to Hindsight Cloud |
| `VOICE_RECOGNITION_ENGINE` | `google` | Microphone audio goes to Google's recognizer |
| `VOICE_INPUT/OUTPUT_ENABLED` | `true` | Voice on by default |

Three cloud routes are active by default (inference, memory, ASR). None is disclosed per request. Fixing this is a
user decision (ADR-005), not something the refactor should silently flip.

## 7. Known failures and risks at baseline

- Audit-log redaction, CWD-relative log path, dead GUI forward, and concurrency races (D1–D7 in `current-state.md`).
- Test wall-clock (10 min) leaves little CI margin. Characterization tests added in R1 are designed to run in seconds.
- No task persistence. A crash or restart loses in-flight work without trace (fails AT-006 / TOM-MIG-005 today).

## 8. Voice pipeline (measured 2026-10-21, after the local-first change)

| Item | Value | Method |
|---|---|---|
| Local voices installed | Microsoft David, Zira, Mark (all en-US); **no en-IN voice installed** | WinRT `SpeechSynthesizer.all_voices` |
| TTS (Windows voice, worker) | 14–42 ms per reply sentence | session probe (not committed); reproduced by `tests/test_voice_core.py` |
| ASR model | faster-whisper `large-v3-turbo`, from `C:\voice-agent-data\cache\huggingface\hub` (existing cache, no download) | — |
| ASR on GPU (int8_float16, admitted from measured free VRAM) | load 3.8–4.0 s once; **256–337 ms** per 6 s utterance | same |
| ASR on CPU (int8, 16 threads) | **3.3 s** per 6 s utterance (large-v3: 4.3 s) | session probe (not committed) |
| Accuracy (TTS→ASR round trip) | word-exact except homophones ("docx"→"docs", "9 AM"→"9am") | `test_local_voice_round_trip_is_accurate` |
| `whisper-large-v3-vaani-telugu-ct2` | Unsuitable for English commands: transcribes English speech in Telugu script even with `language=en`; ~10 s/clip on CPU | same probe |
| WinRT + native ML in one process | access violation (onnxruntime, torch, CTranslate2, TomAgent) when WinRT loads first | session probe (not committed) → ADR-009 |
| PyAudio before this change | not installed → "No microphone devices detected"; after: Realtek mic, 19 device entries | — |

## 9. PySide6 interface smoke (real TomAgent, offscreen)

Ready in 5.2 s; "system status" 0.1 s (SUCCEEDED, `desktop-qt`); a local `qwen3:8b` chat answer in 8.7 s (SUCCEEDED);
privacy panel 4 local / 0 cloud.
