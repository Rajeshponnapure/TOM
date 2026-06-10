# TOM — Deployment Checklist (target: tomorrow)

## A. On this machine, tonight (~30 min, in order)

1. **Secrets (10 min)** — follow `SECURITY_ACTIONS_REQUIRED.md`:
   rotate the Gmail app password, delete + revoke `google-credentials_token.json`.
2. **Rebuild the exe (10 min)** — double-click **`build.bat`** (or run it in a terminal).
   It cleans old output, rebuilds from the fixed source, and writes
   `dist\SHA256SUMS.txt`. The old exe does NOT contain today's fixes.
3. **Smoke test from source (5 min)** — with Ollama running (`ollama serve`,
   models pulled: `ollama pull gemma4 && ollama pull qwen2.5-coder:7b-instruct && ollama pull nomic-embed-text`):
   - `python main.py` → expect startup lines including `[KNOWLEDGE] Curated knowledge online`
     and `[ENGINES] Unified engine router online.`
   - Try: `create a verilog counter with width=8` → real Verilog (new: works in CLI/chat).
   - Try: `analyze the data in <some>.csv` → "real pipeline" + HTML dashboard path.
   - Try: `give me the daily briefing` → news engine (new: works in chat).
4. **Smoke test the new exe (5 min)** — launch `dist\tom_desktop_app.exe`, send one
   chat message, one quick action. Watch `tom_logs/startup.log` if anything fails.
5. **Run the test suite (optional, 3 min)** — `python -m pytest tests/ -v`
   (11 tests incl. the 100%-utilization contract) and `python test_tom_comprehensive.py`.
6. **Try the new meta commands** — in chat or CLI type `what can you do`
   (registry-backed capability list) and `system status` (live subsystem health).
7. **Deep diagnostic (optional)** — `python tools/verify_tom_system.py`.

## B. What changed today (deploy notes)

| Area | Change |
|---|---|
| Security | `.gitignore` added; `eval()` on media metadata removed; all 4 `shell=True` sites hardened; migration packager now excludes credentials/tokens |
| Routing | NEW `tools/engine_router.py` — ML/IoT/VLSI/Hardware/Blender/GameDev/News/Env/Auto-update/Autonomous/Multi-agent now reachable from **chat and CLI in plain English** (GUI buttons unchanged); all engine calls now pass the SafetyGuards gate |
| Knowledge | `KnowledgeEngine` wired into reasoning (`[KNOWLEDGE]` at startup); legacy `knowledge/*.md` content actually loaded and retrieved per-query |
| Data analysis | Real pipeline (clean → insights → charts → HTML dashboard) now runs from chat when a data file is referenced; honest labeling (BI-style HTML, not `.pbix`); fixed pandas-3 silent no-op fill bug |
| Skills | External 864-skill library now opt-in (`TOM_INCLUDE_EXTERNAL_SKILLS=1`); default startup loads 47 local skills |
| Build | `dist_updated/` duplicate (354 MB) deleted; spec excludes vendored `.git`; `build.bat` = one-command canonical build + SHA256 |
| Deps | `requirements.txt` fully pinned to the venv's exact versions (38 pins) |
| QA | `tests/` with 7 pure-logic tests; `.github/workflows/ci.yml` (compile + tests on push) |

## C. Known limitations to state honestly in release notes

- Binary is **unsigned** → SmartScreen warning on first run (cert ordered for v1.1).
- Requires a local **Ollama** install with models pulled; no cloud fallback.
- "Power BI" requests produce a **BI-style HTML dashboard**, not a `.pbix` file.
- Voice+ audio emotion analysis needs the GUI voice mode; chat handles text emotion only.
- Windows-only.

## D. Rollback plan

`git log` now exists. If the new build misbehaves:
`git diff HEAD~1` to inspect, `git checkout HEAD~1 -- <file>` to revert a file,
rebuild with `build.bat`. (Initial commit = today's fixed state.)
