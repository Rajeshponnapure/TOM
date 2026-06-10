# TOM — Next Implementation Plan: "Do Any Task" Professional Assistant

Goal you stated: *TOM should do any task I ask.* This plan is the honest,
engineered route to the strongest possible version of that. It separates what
is genuinely achievable (a very wide, reliable task surface) from what no
assistant can promise (literally unbounded action), and gives a concrete build
order.

---

## 0. The honest framing (read first)

"Any task" splits into three buckets:

1. **Should + can do reliably** — documents, data, code, web research, email,
   messaging, file ops, app control, multi-step automation, scheduled jobs.
   *This is where 95% of real requests live. The plan maximizes this.*
2. **Can do, needs guardrails** — sending messages/email, spending money,
   deleting files, system changes. These MUST stay approval-gated. A pro
   assistant confirms before irreversible actions; that's a feature, not a gap.
3. **Cannot / must not** — illegal, unsafe, or physically impossible tasks.
   A professional assistant declines these clearly. "Any task" excludes these
   by design, and that boundary is what makes TOM trustworthy.

So the target is precise: **"TOM reliably handles the full range of legitimate
desktop + knowledge-work tasks, asks before irreversible ones, and degrades
gracefully when a dependency is missing."** That is a 100%-professional
assistant. This plan builds exactly that.

---

## 1. Foundation already in place (don't rebuild)

- Unified router + 44-capability registry (CI-validated, zero orphans)
- NL access to every engine from chat/CLI; approval gate on sensitive actions
- Knowledge (73 sections) + skills (47) wired into reasoning
- Health/Capability surfaces; logs with rotation + PII masking
- Sandboxed code runner; real data pipeline; pinned deps; build.bat + CI

---

## 2. Phase A — Reliability & "never silently fails" — ✅ SHIPPED 2026-06-10  → 80→88

The #1 thing separating "demo" from "does any task" is **failure handling**.

| # | Build | File(s) | Why it widens task coverage |
|---|---|---|---|
| A1 | **Universal task fallback**: when no concrete handler matches, run a *plan→tool-pick→execute→verify* loop using the orchestrator instead of a chat reply | agent.py + autonomous_agent.py | Unknown requests still get attempted, not deflected |
| A2 | **Per-capability dependency preflight**: each engine reports `is_available()` + the exact install/command to fix it; surfaced in Health and on first failure | engine_router.py, capability_registry.py | "It just doesn't work" → "Tesseract not installed; here's the 1 command" |
| A3 | **Crash isolation**: wrap Tk mainloop + agent loop with an exception hook → `tom_logs/crash_*.txt` + a friendly "recovered" toast | tom_desktop_app.py, main.py | App survives any single-task failure |
| A4 | **Retry + clarify**: on failure, TOM auto-asks one targeted clarifying question rather than dying | agent.py | Ambiguous tasks resolve instead of erroring |

Exit check: kill each dependency in turn; TOM stays up and tells the user what to do.

## 3. Phase B — Widen the task surface (Week 2)  → 88→93

| # | Build | Why |
|---|---|---|
| B1 | **Real "run code" for more languages** (Node, shell) behind approval | "build & run X" works beyond Python |
| B2 | **File-system task suite**: search, bulk rename, move, organize, zip, convert | "organize my downloads", "convert these to PDF" |
| B3 | **Browser task recipes** via existing web_automation: fill forms, scrape tables, download | "log into X and pull my invoices" |
| B4 | **Scheduling UI**: turn any task into a recurring job (scheduler.py exists) | "every morning email me the news" |
| B5 | **MCP connector expansion**: wire more of GitHub/Slack/Calendar/Drive end-to-end | real workplace tasks |

## 4. Phase C — Professional polish (Week 3)  → 93→97

- UI workspace depth: Knowledge browser, Automation center, real Settings (keys/model/voice/theme) — same pattern as the Capability/Health views shipped today
- Engine unit tests with fixtures (ml/iot/vlsi/data) → coverage gate ≥70%
- Voice mode parity in-app; streaming responses for long tasks

## 5. Phase D — GA hardening (ongoing)  → 97→100

- Code-signing cert applied to build.bat (removes SmartScreen warning)
- 2-week soak with real daily use; triage from `show logs`
- Auto-update channel verified end-to-end

---

## 6. Phase A delivery record (shipped 2026-06-10)
- A2 ✅ tools/preflight.py — 22 capability checks, exact fix commands, wired into `system status` and engine failure messages (verified live: surfaced 4 real gaps in the audit sandbox)
- A1 ✅ universal fallback — task-like unmatched commands run the autonomous plan→execute loop (kill switch: TOM_UNIVERSAL_FALLBACK=0); gating verified 13/13 cases
- A4 ✅ clarify-on-failure — one targeted LLM-generated question appended when an attempt fails
- A3 ✅ tools/crash_guard.py — process + thread + Tk-callback hooks, crash_*.txt reports (verified live: thread crash captured); wired into both entry points
- Tests: 17/17 passing

## 6b. Next session (Phase B starts here)

1. **A2 dependency preflight** — biggest reliability win, low risk. Every
   capability gains a `requires` + `check()` so failures become actionable.
2. **A1 universal fallback** — route unmatched tasks through the plan/execute
   loop so "any task" genuinely gets attempted.
3. **A3 crash isolation** — guarantee the app never dies on one bad task.
4. Tests for all three; commit; update PATH_TO_100.

Each ships behind the existing patterns (additive, CI-gated, graceful), so no
regression risk to tomorrow's deploy.

---

## 7. What stays true regardless

TOM will **confirm before** sending, deleting, paying, or changing system
state — and will **decline** illegal/unsafe tasks. That is not a limitation to
fix; it is the definition of a *professional* assistant you can actually trust
with "any task."
