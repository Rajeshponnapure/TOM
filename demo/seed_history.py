"""
Prepare a TOM memory demo: a sandbox Downloads folder plus a few weeks of
realistic history in a dedicated Hindsight bank.

    python demo/seed_history.py --fresh      # new empty bank + refilled sandbox (cold start)
    python demo/seed_history.py --history    # add three past sessions of corrections/outcomes
    python demo/seed_history.py --refill     # put a new batch of files in the sandbox

The bank id and sandbox path are written to demo/.demo_env and printed as
`set …` lines; demo/run_demo.py and the desktop app pick them up via .env or
your shell. Your real TOM memory bank is never touched.

Needs HINDSIGHT_API_KEY (Hindsight Cloud) or HINDSIGHT_BASE_URL (self-hosted)
in .env. Use --offline to exercise the flow with an in-memory stand-in.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

DEMO_DIR = ROOT / "demo"
SANDBOX = DEMO_DIR / "sandbox" / "Downloads"
ENV_FILE = DEMO_DIR / ".demo_env"

# Two batches of the kind of files that pile up in a real Downloads folder.
BATCH_1 = [
    "Invoice_AWS_Aug-2026.pdf", "TSDA_workshop_attendance.xlsx", "Screenshot 2026-09-18 101422.png",
    "ZoomInstaller.exe", "resume_final_v3.docx", "team_photo_offsite.jpg", "project_notes.txt",
    "Q3_review_deck.pptx", "node-v22.9.0-x64.msi", "electricity_bill_sep.pdf",
]
BATCH_2 = [
    "Invoice_Figma_Sep-2026.pdf", "Screenshot 2026-09-27 181530.png", "vscode_setup.exe",
    "hackerrank_certificate.pdf", "cafe_menu_photos.zip", "sunset_hyderabad.jpg",
    "budget_2026.csv", "Screenshot 2026-09-28 094410.png",
]

# Three earlier sessions: what the user said, and what TOM did — with real dates.
def history(now: datetime):
    d = lambda days: now - timedelta(days=days)  # noqa: E731
    return [
        # ── 3 weeks ago ───────────────────────────────────────────────────
        (d(21), "task", "file_organization",
         'The user asked TOM: "organize my downloads". TOM handled it as \'engine_fileops\' and the '
         "outcome was success. TOM's reply: Done: 23 file(s) processed. Now in: Documents (9), Images (7), "
         "Installers (3), Spreadsheets (4)", None),
        (d(21), "preference", "file_organization",
         'After TOM organized the Downloads folder, the user corrected TOM: "No — PDFs always go in '
         'Invoices, not Documents. That is where I look for bills."',
         "No — PDFs always go in Invoices, not Documents. That is where I look for bills."),
        # ── 2 weeks ago ───────────────────────────────────────────────────
        (d(14), "preference", "file_organization",
         'The user told TOM a standing instruction: "Screenshots should go into a Screenshots folder, '
         'not Images — I share those in bug reports."',
         "Screenshots should go into a Screenshots folder, not Images — I share those in bug reports."),
        (d(14), "preference", "file_organization",
         'The user told TOM a standing instruction: "Never move installers — leave .exe and .msi '
         'files where they are, I delete them myself after installing."',
         "Never move installers — leave .exe and .msi files where they are, I delete them myself after installing."),
        (d(14), "task", "email",
         'The user asked TOM: "write an email to the TSDA trainers about the workshop schedule". TOM '
         "handled it as 'email_draft' and the outcome was success.", None),
        # ── last week ─────────────────────────────────────────────────────
        (d(7), "preference", "email",
         'After TOM drafted a long email, the user corrected TOM: "Too long. Keep my emails under 120 '
         "words, put action items as bullet points, and sign off as 'Rajesh — TSDA'.\"",
         "Keep my emails under 120 words, put action items as bullet points, and sign off as 'Rajesh — TSDA'."),
        (d(7), "task", "documents",
         'The user asked TOM: "create a word doc summarizing the Q3 training feedback". TOM handled it '
         "as 'document' and the outcome was success.", None),
        (d(3), "preference", "presentations",
         'The user told TOM a standing instruction: "For decks, use at most 6 bullets per slide and '
         'always end with a next-steps slide."',
         "For decks, use at most 6 bullets per slide and always end with a next-steps slide."),
    ]


def fill_sandbox(names, clear: bool) -> None:
    if clear and SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    SANDBOX.mkdir(parents=True, exist_ok=True)
    for name in names:
        path = SANDBOX / name
        if not path.exists():
            path.write_bytes(os.urandom(512))
    print(f"Sandbox: {SANDBOX}  ({len(list(SANDBOX.iterdir()))} items)")


def read_env() -> dict:
    out = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def write_env(bank_id: str) -> None:
    ENV_FILE.write_text(f"HINDSIGHT_BANK_ID={bank_id}\nTOM_DOWNLOADS_DIR={SANDBOX}\n", encoding="utf-8")
    print("\nUse these for the demo session (already read by demo/run_demo.py):")
    print(f"  Windows (cmd):  set HINDSIGHT_BANK_ID={bank_id} && set TOM_DOWNLOADS_DIR={SANDBOX}")
    print(f"  PowerShell:     $env:HINDSIGHT_BANK_ID='{bank_id}'; $env:TOM_DOWNLOADS_DIR='{SANDBOX}'")
    print(f"  bash/zsh:       export HINDSIGHT_BANK_ID={bank_id} TOM_DOWNLOADS_DIR='{SANDBOX}'")


def make_memory(bank_id: str, offline: bool):
    from tools.hindsight_memory import HindsightMemory
    if offline:
        sys.path.insert(0, str(ROOT / "tests"))
        from fake_hindsight import FakeHindsight  # type: ignore[import-not-found]
        mem = HindsightMemory(client=FakeHindsight(), bank_id=bank_id,
                              state_dir=DEMO_DIR / "sandbox" / "memory_state")
        mem.enabled = True
        return mem
    mem = HindsightMemory(bank_id=bank_id, state_dir=DEMO_DIR / "sandbox" / "memory_state")
    if not mem.available:
        sys.exit(f"Hindsight is not configured: {mem.last_error}\n"
                 "Add HINDSIGHT_API_KEY to .env (or run with --offline).")
    return mem


def seed_history(mem) -> None:
    now = datetime.now(timezone.utc)
    for when, kind, category, content, words in history(now):
        tags = [kind, category] if kind == "task" else ["preference", category]
        if "corrected" in content:
            tags.append("correction")
        meta = {"category": category}
        if words:
            meta["user_words"] = words
        ok = mem.retain(content, context=f"{'task outcome' if kind == 'task' else 'user preference'} — "
                                         f"{category.replace('_', ' ')}",
                        tags=tags, metadata=meta, timestamp=when, wait=True, index_now=True)
        mark = "ok " if ok else "ERR"
        print(f"  [{mark}] {when:%b %d}  {kind:<10} {(words or content)[:80]}")
        if not ok:
            print(f"        {mem.last_error}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fresh", action="store_true", help="new empty demo bank + clean sandbox (batch 1)")
    ap.add_argument("--history", action="store_true", help="add three earlier sessions to the demo bank")
    ap.add_argument("--refill", action="store_true", help="drop a new batch of files into the sandbox")
    ap.add_argument("--offline", action="store_true", help="use an in-memory stand-in instead of Hindsight")
    args = ap.parse_args()
    if not (args.fresh or args.history or args.refill):
        ap.print_help()
        return

    env = read_env()
    bank_id = env.get("HINDSIGHT_BANK_ID")
    if args.fresh or not bank_id:
        bank_id = f"tom-demo-{uuid.uuid4().hex[:8]}"
        fill_sandbox(BATCH_1, clear=True)
        print(f"New demo bank: {bank_id} (empty — TOM starts with no memory of you)")
    if args.history:
        mem = make_memory(bank_id, args.offline)
        print(f"Seeding earlier sessions into '{bank_id}' ({mem.base_url}):")
        seed_history(mem)
    if args.refill:
        fill_sandbox(BATCH_2, clear=False)
    write_env(bank_id)


if __name__ == "__main__":
    main()
