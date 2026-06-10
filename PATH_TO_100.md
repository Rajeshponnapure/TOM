# Path to 100/100 — dated plan with owners

Current: **80/100 source-side** (verified this session). The remaining 20 points
cannot be produced by more code tonight — each is gated on time, your accounts,
or real-world usage. Here is exactly how each point gets claimed:

| Pts | Item | Owner | When | Action |
|---:|---|---|---|---|
| 2 | Credential rotation | **You** | Tonight (10 min) | SECURITY_ACTIONS_REQUIRED.md steps 1–2 |
| 3 | Rebuild + smoke test exe on Windows | **You** | Tonight (20 min) | `build.bat`, then DEPLOYMENT_CHECKLIST.md §A.3–A.4 (the current exe predates ALL fixes) |
| 4 | Code-signing certificate | **You** + CA | Order tomorrow, lands in 3–7 days | Buy OV cert (Sectigo ~$80/yr); add `signtool sign` step to build.bat; removes SmartScreen warning |
| 4 | Runtime soak | **You + early users** | Week 1 after deploy | Run daily tasks; `show logs` + `system status` surface issues; file bugs |
| 3 | UI workspace depth | Next dev session | Week 2 | Knowledge/Automation/Settings views (Capabilities + Health views shipped today; same pattern) |
| 2 | Engine test coverage | Next dev session | Week 2 | Unit tests for ml/iot/vlsi handlers with fixture data (14 tests exist today) |
| 2 | Crash reporter | Next dev session | Week 3 | Wrap Tk mainloop + agent loop with exception hook → tom_logs/crash_*.txt + restart prompt |

## Score trajectory
- Tonight after your 30 min: **~85**
- After cert lands + v1.0.1 signed build (next week): **~91**
- After week-2 UI/tests + crash reporter: **~95**
- After 2 weeks clean soak: **100** — declare GA

## What was verified TODAY (do not re-litigate)
- Full agent constructed and exercised end-to-end in a clean environment:
  `system status`, `what can you do` (44/44 registry-verified), `show logs`
  (PII-masked), and real VLSI generation through the complete NLP→router→engine
  pipeline — all WITHOUT Ollama present, proving graceful degradation.
- Knowledge: auto-discovery loads ALL domain JSONs — 73 sections / 873 concepts
  (was 30/—; half the KB was silently skipped before).
- Skills: 47/47 routable (SKILL.md now registers under its frontmatter name).
- GUI: Capability Center + Health views added (7 nav views).
- Logs: size-capped rotation; in-app `show logs` with PII masking.
- 14/14 tests green; CI enforces capability validation + zero orphans.
