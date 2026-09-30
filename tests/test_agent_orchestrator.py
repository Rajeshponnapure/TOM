"""AgentOrchestrator: primary routing sends a task to the sub-agent whose keywords
match it, and escalation after a failure must still route to a role suited to the
task -- not just whichever sub-agent happens to be idle first.

Real bug, found by physically running a failure through the orchestrator: a coding
task ("fix a bug in my python script") routed correctly to the Tech Lead (CTO), but
when the CTO's executor raised, _escalate_task handed the SAME task to the Marketing
Lead (CMO) -- purely because CMO was first in dict iteration order among idle agents,
with no regard for whether it fit the task at all.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio

from tools.agent_orchestrator import AgentOrchestrator, AgentRole


def run(coro):
    return asyncio.run(coro)


def _wire_success(agent, role):
    async def exec_fn(desc, intent, role=role):
        return {"status": "success", "message": f"{role.value} handled: {desc}"}
    agent.executor = exec_fn


def test_a_technical_task_routes_to_the_tech_lead():
    orch = AgentOrchestrator(tom_agent=None, llm=None)
    for role, agent in orch._agents.items():
        _wire_success(agent, role)
    result = run(orch.execute_task("fix a bug in my python script", "code"))
    assert result["status"] == "success"
    assert result["role"] == "cto"


def test_escalation_prefers_a_relevant_remaining_agent_over_the_first_idle_one():
    orch = AgentOrchestrator(tom_agent=None, llm=None)

    desc = "coordinate the product launch schedule and roadmap"
    # This description matches both product (cpo) and operations (coo) keywords
    # equally; cpo is primary (tie-break order), cto/cmo/cfo have zero relevance.
    primary_role = orch._determine_best_agent(desc, "")
    assert primary_role == AgentRole.CPO

    async def fail_fn(d, i):
        raise RuntimeError("simulated failure")
    orch._agents[primary_role].executor = fail_fn
    for role, agent in orch._agents.items():
        if role != primary_role:
            _wire_success(agent, role)

    result = run(orch.execute_task(desc, ""))
    assert result["status"] == "error"
    assert result["assigned_to"] == "Product Lead"
    # The relevant remaining agent (Operations Lead, also keyword-matched) must
    # win escalation over Tech Lead, which is first in dict iteration order but
    # has zero keyword relevance to this task.
    assert result["escalated"]["assigned_to"] == "Operations Lead"


def test_escalation_still_picks_someone_when_no_remaining_agent_is_relevant():
    orch = AgentOrchestrator(tom_agent=None, llm=None)

    async def fail_fn(d, i):
        raise RuntimeError("simulated failure")
    orch._agents[AgentRole.CTO].executor = fail_fn
    for role, agent in orch._agents.items():
        if role != AgentRole.CTO:
            _wire_success(agent, role)

    result = run(orch.execute_task("fix a bug in my python script", "code"))
    assert result["status"] == "error"
    assert result["escalated"]["status"] == "success"
