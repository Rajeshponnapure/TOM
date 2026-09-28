"""
Scripted walk-through of TOM's long-term memory — the before/after in ~3 minutes.

    python demo/seed_history.py --fresh     # once: empty demo bank + sandbox
    python demo/run_demo.py                 # press Enter between steps
    python demo/run_demo.py --auto          # no pauses (for recordings / CI)
    python demo/run_demo.py --offline       # no Hindsight account needed

Act 1  cold start      — "organize my downloads": generic grouping, PDFs → Documents
Act 2  one correction  — "No — PDFs always go in Invoices …": retained to Hindsight
Act 3  time passes     — seed_history adds three earlier sessions (screenshots, installers, email style)
Act 4  payoff          — "tidy up my downloads folder": every remembered rule applied, unprompted
Act 5  beyond files    — "email Ravi about the budget": short, bulleted, signed the way the user asked
Act 6  reflection      — "what have you learned about me?": Hindsight reflect() summary

Everything runs through the same TomAgent.execute_task() the desktop app and CLI use.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo"
sys.path.insert(0, str(ROOT))

BOLD, DIM, GREEN, CYAN, RESET = "\033[1m", "\033[2m", "\033[32m", "\033[36m", "\033[0m"
if os.name == "nt":
    os.system("")  # enable ANSI colours in Windows terminals


def load_demo_env() -> None:
    env_file = DEMO / ".demo_env"
    if not env_file.exists():
        sys.exit("Run `python demo/seed_history.py --fresh` first.")
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()


def banner(title: str, note: str = "") -> None:
    print(f"\n{BOLD}{CYAN}━━ {title} {'━' * max(0, 60 - len(title))}{RESET}")
    if note:
        print(f"{DIM}{textwrap.fill(note, 78)}{RESET}")


def tree(folder: Path) -> str:
    lines = []
    for p in sorted(folder.rglob("*")):
        if p.is_file():
            lines.append("   " + str(p.relative_to(folder)).replace("\\", "/"))
    return "\n".join(lines) or "   (empty)"


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto", action="store_true", help="do not pause between acts")
    ap.add_argument("--offline", action="store_true", help="in-memory stand-in for Hindsight")
    args = ap.parse_args()

    if args.offline and not (DEMO / ".demo_env").exists():
        subprocess.run([sys.executable, str(DEMO / "seed_history.py"), "--fresh"], check=True)
    load_demo_env()
    os.environ.setdefault("NLP_PARSE_TIMEOUT_SECONDS", "20")

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")                      # keys; demo_env values already set win
    from tools import hindsight_memory
    if args.offline:
        sys.path.insert(0, str(ROOT / "tests"))
        from fake_hindsight import FakeHindsight
        mem = hindsight_memory.HindsightMemory(client=FakeHindsight(),
                                               state_dir=DEMO / "sandbox" / "memory_state")
        mem.enabled = True
        mem.base_url = "offline stand-in (tests/fake_hindsight.py)"
        hindsight_memory.set_memory(mem)

    import agent as agent_mod
    agent_mod.safe_print = lambda *_a, **_k: None   # keep the demo output clean
    tom = agent_mod.TomAgent()
    tom.approval_manager.request_approval = lambda req: (
        print(f"{DIM}   [approval] {req.summary.splitlines()[-1][:110]} → approved{RESET}") or True)
    sandbox = Path(os.environ["TOM_DOWNLOADS_DIR"])

    def pause() -> None:
        if not args.auto:
            input(f"{DIM}   ↵ next{RESET}")

    async def say(cmd: str) -> dict:
        print(f"\n{BOLD}You:{RESET} {cmd}")
        result = await tom.execute_task(cmd)
        msg = str(result.get("message", ""))
        if msg.startswith("Remembering") or result.get("response_type") == "preference_saved":
            head, _, rest = msg.partition("\n\n")
            print(f"{GREEN}{head}{RESET}")
            msg = rest
        if msg:
            print(f"{BOLD}TOM:{RESET} " + msg.replace("\n", "\n     "))
        return result

    print(f"{BOLD}TOM — an automation agent that remembers how you work{RESET}")
    print(f"{DIM}{tom.memory.status_line()}{RESET}")

    banner("Act 1 · Cold start", "No history with this user yet. TOM organizes with its defaults.")
    print(f"{DIM}Downloads before:\n{tree(sandbox)}{RESET}")
    pause()
    await say("organize my downloads")
    print(f"{DIM}Downloads after:\n{tree(sandbox)}{RESET}")
    pause()

    banner("Act 2 · One correction", "The user says it once. TOM stores it in Hindsight.")
    await say("No — PDFs always go in Invoices, not Documents.")
    tom.memory.flush()
    pause()

    banner("Act 3 · Time passes", "Three earlier sessions are added to the same memory bank: "
                                  "screenshots, installers, email style, deck format.")
    seed = [sys.executable, str(DEMO / "seed_history.py"), "--history", "--refill"]
    if args.offline:
        # Offline memory lives in this process, so seed it directly.
        sys.path.insert(0, str(DEMO))
        import seed_history
        seed_history.seed_history(tom.memory)
        seed_history.fill_sandbox(seed_history.BATCH_2, clear=False)
    else:
        subprocess.run(seed, check=True)
    pause()

    banner("Act 4 · Payoff", "A new batch of files, a differently worded request, no reminders.")
    print(f"{DIM}New files:\n{tree(sandbox)}{RESET}")
    pause()
    await say("tidy up my downloads folder")
    print(f"{DIM}Downloads after:\n{tree(sandbox)}{RESET}")
    pause()

    banner("Act 5 · Beyond files", "The same memory shapes writing.")
    drafted = await say("email Ravi about the budget review on Friday")
    if drafted.get("status") == "error":
        print(f"{DIM}   (drafting needs a language model — start Ollama or set "
              f"TOM_LLM_PROVIDER=groq with GROQ_API_KEY in .env){RESET}")
    pause()

    banner("Act 6 · Reflection", "Hindsight reflect() over everything TOM has learned.")
    await say("what have you learned about me?")
    tom.memory.flush()
    print(f"\n{DIM}{tom.memory.status_line()}{RESET}\n")


if __name__ == "__main__":
    asyncio.run(main())
