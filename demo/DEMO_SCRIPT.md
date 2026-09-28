# TOM memory demo — script

A 3-minute walk-through that shows one thing clearly: **TOM gets better at your
workflow the longer you use it**, because every correction is stored in
[Hindsight](https://github.com/vectorize-io/hindsight) and recalled before the next task.

## Setup (once, ~2 minutes)

```bat
pip install -r requirements.txt
copy .env.example .env
```

In `.env` set:

```ini
HINDSIGHT_API_KEY=hsk_...            # Hindsight Cloud key
TOM_LLM_PROVIDER=groq                # or leave as ollama if you run a local model
GROQ_API_KEY=gsk_...
```

Then create an empty demo memory bank and a sandbox Downloads folder:

```bat
python demo\seed_history.py --fresh
```

Your real memory bank and real Downloads folder are never touched — the demo
uses its own bank (`tom-demo-…`) and `demo\sandbox\Downloads`.

## Run it

**Terminal (recommended for recording):**

```bat
python demo\run_demo.py          :: Enter between acts
python demo\run_demo.py --auto   :: no pauses
python demo\run_demo.py --offline :: no accounts needed (in-memory stand-in)
```

**Desktop app:** set the two variables printed by `seed_history.py`, then
`python tom_desktop_app.py` and type the lines below into Chat. Open the
**Memory** view at the end.

## The script

| # | You type | What TOM does | What to point out |
|---|----------|---------------|-------------------|
| 1 | `organize my downloads` | Groups by type with its defaults — invoices land in **Documents/** | No memory yet. Generic. |
| 2 | `No — PDFs always go in Invoices, not Documents.` | Replies *"Got it — I'll remember that"* and shows the rule it extracted: `.pdf files → Invoices/` | One correction, stored to Hindsight (`retain`). No retraining, no config file. |
| 3 | *(skip ahead)* `python demo\seed_history.py --history --refill` | Adds three earlier sessions: screenshots → Screenshots, never move installers, email style, deck format. Drops new files in the sandbox. | Realistic multi-week history, timestamped in the past. |
| 4 | `tidy up my downloads folder` | Green **Remembering** card: `.pdf → Invoices/`, `screenshot → Screenshots/`, `leave installers where they are` — then moves files accordingly and leaves `vscode_setup.exe` in place | Different wording, new files, zero reminders. This is the moment. |
| 5 | `email Ravi about the budget review on Friday` | Short draft, action items as bullets, signed *Rajesh — TSDA* | Same memory shapes writing, not just files (`recall` → prompt). |
| 6 | `what have you learned about me?` | A grouped summary of standing preferences | Hindsight `reflect` over the whole bank. |
| 7 | Memory view → **Recall** `PDFs` | The stored facts behind step 4 | Memory is visible and inspectable. |

## How the memory is used (one slide)

- **retain** — every correction/preference (tagged `preference`, indexed immediately) and every task outcome (tagged `task`, indexed in the background).
- **recall** — before every task, in parallel with request parsing; results go into the prompt and into a visible *Remembering* card. File organizing recalls only `preference`-tagged memories and turns them into concrete rules.
- **reflect** — "what have you learned about me?", and as a fallback that returns structured folder rules (JSON schema) when free-text parsing finds none.
