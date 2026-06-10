from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from tools.skill_manager import SkillRoute


@dataclass(frozen=True)
class CapabilityDecision:
    status: str
    reason: str
    skill_name: str = ""
    required_tools: List[str] = field(default_factory=list)


class CapabilityResolver:
    """Truth layer for what TOM can actually do with a routed skill."""

    def resolve(self, route: Optional[SkillRoute]) -> CapabilityDecision:
        if not route or not route.matched:
            return CapabilityDecision("unmatched", "No matching skill was found.")

        if route.execution_mode == "tool_backed":
            return CapabilityDecision(
                "yes_executable",
                "Matched skill has a local TOM tool path.",
                route.skill_name,
                route.required_tools,
            )

        if route.execution_mode == "external_command":
            return CapabilityDecision(
                "yes_with_external_tool",
                "Matched skill requires an external command, service, or credential.",
                route.skill_name,
                route.required_tools,
            )

        if route.execution_mode == "blocked":
            return CapabilityDecision(
                "blocked_missing_dependency",
                "; ".join(route.limitations) or "Skill is blocked.",
                route.skill_name,
                route.required_tools,
            )

        return CapabilityDecision(
            "guidance_only",
            "Matched skill is loaded as guidance, but no local execution tool is mapped.",
            route.skill_name,
            route.required_tools,
        )
