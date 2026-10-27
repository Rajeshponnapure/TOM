# Automatic model routing — measurements (2026-10-27)

Hardware: Alienware 16 Aurora, RTX 5060 8 GB (≈7.1 GB usable after TOM's 1 GB reserve), 32 GB RAM, Ollama.
Script: three of TOM's kinds of work, scored automatically, same prompts for every model
(`think: false`, `num_ctx` 4096, temperature 0.2).

* **Code** — fix a buggy `median()`; the returned file is executed against 5 tests.
* **JSON** — extract 5 business facts from a message; each compared exactly.
* **Writing** — 120-word product description; length, key fact, no placeholders, no chatter (4 checks).

| Model | Size | Code | JSON | Writing | Speed (tok/s) | Notes |
|---|---|---|---|---|---|---|
| llama3.2:3b | 1.9 GB | **3/5** | 4/5 | 4/4 | 120–137 | fastest; its code fix was wrong |
| qwen3.5:4b | 3.2 GB | 5/5 | 4/5 | 4/4 | ~90 | |
| qwen3:8b | 4.9 GB | 5/5 | 5/5 | 4/4 | ~63 | fits with an 8k context |
| qwen3.5:9b | 6.1 GB | 5/5 | 5/5 | 4/4 | ~57 | best writing length; needs ~7.3 GB with context — usually doesn't fit after the reserve |
| deepseek-r1:8b | 4.9 GB | **0/5** (broken JSON) | 5/5 | 3/4 | ~62 | unsuitable for TOM's structured work |
| qwen2.5-coder:14b | 8.4 GB | 5/5 | 5/5 | 3/4 | **~16** | larger than the GPU: split onto the CPU, 4× slower, no gain on these tasks |

## Routing (`tom_core/resources/model_router.py`)

| Kind of work (task labels) | Preference | Live result |
|---|---|---|
| code — fix_tests, code_help, scaffold | qwen3.5:9b → qwen3:8b → qwen3.5:4b → llama3.2:3b | qwen3:8b fixed the test repo in 21.8 s |
| writing — documents, website, email drafts | same | qwen3:8b: one-page proposal 53 s, website 75 s |
| reasoning — analysis, research, plans, specialists | same | qwen3:8b: structured analysis 19 s |
| structured — extraction, answers parsing | same | — |
| chat | llama3.2:3b → qwen3.5:4b → qwen3:8b, **reusing a capable model already in GPU memory** | after an analysis, chat reused qwen3:8b: 15.0 s → 10.8 s (no swap) |

Each call checks the GPU memory free *at that moment* (RRM-002/003), so a model that doesn't fit — e.g.
while a game is running — is skipped for the next one that does. One strong model for all heavy work avoids
4–9 s model swaps on an 8 GB card.

Switches: `TOM_MODEL_ROUTING=0` (off), `TOM_MODEL_CODE` / `_WRITING` / `_REASONING` / `_STRUCTURED` / `_CHAT`
(pin a model; a pinned model is used even if it must split onto the CPU, e.g. `TOM_MODEL_CODE=qwen2.5-coder:14b`).
