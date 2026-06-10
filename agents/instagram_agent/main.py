"""Standalone Instagram agent stub.

This agent was scaffolded by TOM. Extend it with the desired logic.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.instruction_loader import compose_system_prompt

SYSTEM_PROMPT = compose_system_prompt(
    "You are an auto-generated TOM agent. Follow the shared repo instruction stack "
    "and return concise, verified outputs.",
    "instagram_agent",
    include_ui=True,
)

CAPABILITIES = ["open_instagram", "scroll_feed", "extract_posts"]


def run():
    print("Instagram agent started")
    print(f"Capabilities: {', '.join(CAPABILITIES)}")
    # TODO: implement the agent's logic here


if __name__ == "__main__":
    run()
