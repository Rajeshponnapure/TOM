"""Standalone email agent entrypoint.

Run once for a single triage pass or use --daemon to keep it active in the
background. TOM can control the daemon by starting and stopping this process.
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.email_agent.service import EmailAgentService


async def main() -> None:
    parser = argparse.ArgumentParser(description="Standalone email agent")
    parser.add_argument("--daemon", action="store_true", help="Keep the agent running on a loop")
    parser.add_argument("--once", action="store_true", help="Run one inbox triage pass and exit")
    args = parser.parse_args()

    service = EmailAgentService()

    if args.daemon:
        await service.run_forever()
        return

    result = await service.run_once()
    print("EMAIL AGENT WORKFLOW")
    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Emails reviewed: {result.get('emails_reviewed', 0)}")
    print(f"Important emails: {result.get('important_count', 0)}")
    print(f"Spam emails: {result.get('spam_count', result.get('low_priority_count', 0))}")
    print(f"Draft replies: {result.get('draft_reply_count', 0)}")
    print(f"Auto replied: {result.get('auto_replied_count', 0)}")

    summary_lines = result.get("summary_lines", [])
    if summary_lines:
        print("\nSummary:")
        for line in summary_lines:
            print(f"- {line}")


if __name__ == "__main__":
    asyncio.run(main())