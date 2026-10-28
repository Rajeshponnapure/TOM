# Local model profiles (measured 2026-10-22 08:27)

GPU: 8151 MB total

| Model | Cold load s | First answer s | Gen tok/s | Valid plans | Avg plan s | GPU used MB |
|---|---|---|---|---|---|---|
| llama3.2:3b | 3.9 | 6.9 | 104.6 | 4/5 | 3.7 | 3321 |
| qwen3:8b | 9.0 | 12.4 | 46.7 | 2/5 | 4.1 | 5786 |
| qwen3.5:4b | 22.8 | 30.9 | 68.8 | 5/5 | 3.9 | 4152 |

Valid plan = parsable JSON whose every step names a registered tool (5 fixed goals, temperature 0).
Produced by `tests/manual/benchmark_llm.py`.
