"""
TOM Agent Orchestrator — Multi-Agent System with CEO/CTO/CMO/CPO Hierarchy.

Architecture:
```
CEO (Orchestrator)
├── CTO (Technical Lead)     — code, architecture, debugging, web automation
├── CMO (Marketing Lead)     — content, social, communication, brand
├── CPO (Product Lead)       — product decisions, features, user needs
├── CFO (Finance Lead)       — budget, expenses, financial analysis
└── COO (Operations Lead)    — scheduling, task management, workflows
```

Each agent:
- Has defined capabilities and workflows
- Can accept delegated tasks
- Returns structured results
- Can escalate errors to CEO for re-routing
"""
import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    CEO = "ceo"
    CTO = "cto"
    CMO = "cmo"
    CPO = "cpo"
    CFO = "cfo"
    COO = "coo"



# Tool grants per specialist (PRD C10 "constrained tool grants"). The registry refuses anything else,
# and the policy engine still applies (approvals; privileged actions are never granted).
ROLE_TOOLS: Dict[AgentRole, tuple] = {
    AgentRole.CTO: ("git.status", "git.diff", "git.log", "git.checkpoint", "shell.run", "fs.read_text",
                    "fs.list_dir", "fs.find_files", "fs.largest_files", "system.info", "system.top_processes",
                    "net.open_ports", "web.search", "web.fetch"),
    AgentRole.CMO: ("web.search", "web.fetch", "fs.write_text", "fs.make_dir", "tom.request"),
    AgentRole.CPO: ("web.search", "web.fetch", "fs.read_text", "fs.list_dir", "fs.write_text"),
    AgentRole.CFO: ("fs.read_text", "fs.list_dir", "fs.find_files", "web.search", "tom.request"),
    AgentRole.COO: ("app.open", "system.info", "system.top_processes", "fs.list_dir", "fs.make_dir",
                    "tom.request"),
}
# Work that needs the PC or the live web (files, folders, repos, processes, ports, apps, current
# facts); anything else is thinking work a specialist answers directly.
_NEEDS_TOOLS = re.compile(
    r"[A-Za-z]:[\/]|\b(files?|folders?|director(y|ies)|disk|drive|repo(sitory)?|git|commits?|"
    r"process(es)?|cpu|ram|ports?|(open|launch|start) (the )?(app|program|application)|install(ed)?|search (the )?(web|internet|online)|"
    r"look up|latest|current|today'?s|news|prices?|download(s)?|desktop|workspace)\b", re.I)
ROLE_FOCUS: Dict[AgentRole, str] = {
    AgentRole.CTO: "engineering — code, repositories, diagnostics, technical research",
    AgentRole.CMO: "communication — writing, content, presentations, research for them",
    AgentRole.CPO: "product — requirements, comparisons, user needs, specifications",
    AgentRole.CFO: "finance — budgets, costs, numbers in files, financial research",
    AgentRole.COO: "operations — scheduling, apps, system resources, organizing work",
}

@dataclass
class Task:
    id: str
    description: str
    intent: str = ""
    priority: int = 1
    assigned_to: Optional[AgentRole] = None
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, in_progress, completed, failed, escalated
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = 0.0
    completed_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SubAgent:
    role: AgentRole
    name: str
    description: str
    capabilities: List[str]
    executor: Optional[Callable] = None
    status: str = "idle"
    current_task: Optional[Task] = None
    task_history: List[str] = field(default_factory=list)
    performance_score: float = 1.0


class AgentOrchestrator:
    """CEO-level orchestrator that manages sub-agents and delegates tasks."""

    def __init__(self, tom_agent=None, llm=None):
        self.tom_agent = tom_agent
        self.llm = llm
        self._task_counter = 0
        self._agents: Dict[AgentRole, SubAgent] = {}
        self._pending_tasks: List[Task] = []
        self._active_tasks: Dict[str, Task] = {}
        self._completed_tasks: List[Task] = []
        self._initialize_agents()

    def _initialize_agents(self):
        """Create the sub-agent hierarchy."""
        agents_config = [
            SubAgent(
                role=AgentRole.CTO,
                name="Tech Lead",
                description="Handles all technical tasks: code generation, debugging, web automation, architecture design",
                capabilities=[
                    "code_generation", "debugging", "web_automation",
                    "architecture_design", "code_review", "testing",
                    "devops", "browser_automation",
                ],
                executor=self._execute_cto_task,
            ),
            SubAgent(
                role=AgentRole.CMO,
                name="Marketing Lead",
                description="Handles content creation, social media, communications, brand management",
                capabilities=[
                    "content_creation", "social_media", "email_marketing",
                    "brand_management", "copywriting", "presentation_design",
                ],
                executor=self._execute_cmo_task,
            ),
            SubAgent(
                role=AgentRole.CPO,
                name="Product Lead",
                description="Handles product decisions, feature planning, user needs analysis",
                capabilities=[
                    "product_planning", "feature_analysis", "user_research",
                    "requirement_gathering", "specification_writing",
                ],
                executor=self._execute_cpo_task,
            ),
            SubAgent(
                role=AgentRole.CFO,
                name="Finance Lead",
                description="Handles financial analysis, budgeting, expense tracking, cost optimization",
                capabilities=[
                    "financial_analysis", "budgeting", "expense_tracking",
                    "cost_optimization", "reporting",
                ],
                executor=self._execute_cfo_task,
            ),
            SubAgent(
                role=AgentRole.COO,
                name="Operations Lead",
                description="Handles scheduling, task management, workflow optimization, resource allocation",
                capabilities=[
                    "scheduling", "task_management", "workflow_optimization",
                    "resource_allocation", "process_automation",
                ],
                executor=self._execute_coo_task,
            ),
        ]

        for agent in agents_config:
            self._agents[agent.role] = agent

    async def execute_task(self, task_description: str, intent: str = "",
                           coordinate: bool = False) -> Dict[str, Any]:
        """CEO entry point: decompose task, delegate to sub-agents, aggregate results."""
        task_id = self._generate_task_id()

        task = Task(
            id=task_id,
            description=task_description,
            intent=intent,
            created_at=time.time(),
        )

        # coordinate (the Multi-Agent quick action): the coordinator splits the job across specialists
        role = AgentRole.CEO if coordinate else self._determine_best_agent(task_description, intent)
        task.assigned_to = role

        if role == AgentRole.CEO:
            return await self._handle_as_ceo(task)

        result = await self._delegate_task(task, role)
        return result

    _KEYWORD_MAP = None  # built lazily by _keyword_map(); a class-level cache

    @classmethod
    def _keyword_map(cls) -> List[tuple]:
        if cls._KEYWORD_MAP is not None:
            return cls._KEYWORD_MAP
        tech_keywords = [
            "code", "debug", "fix", "build", "program", "script", "function",
            "class", "api", "server", "database", "sql", "algorithm",
            "refactor", "test", "deploy", "git", "github", "terminal",
            "command", "browser", "web page", "html", "css", "javascript",
            "python", "react", "node", "npm", "docker", "kubernetes",
            "localhost", "network", "console", "error", "bug",
        ]
        marketing_keywords = [
            "email", "newsletter", "content", "blog", "social media",
            "post", "tweet", "linkedin", "instagram", "facebook",
            "campaign", "brand", "copy", "write up", "article",
            "presentation", "slide", "marketing", "seo", "audience",
        ]
        product_keywords = [
            "feature", "product", "requirement", "spec", "roadmap",
            "user story", "backlog", "priority", "mvp", "prototype",
            "design thinking", "ux", "user experience", "feedback",
        ]
        finance_keywords = [
            "budget", "cost", "expense", "revenue", "profit", "finance",
            "invoice", "payment", "price", "spend", "saving", "invest",
            "tax", "salary", "forecast", "financial",
        ]
        operations_keywords = [
            "schedule", "plan", "workflow", "process", "task", "assign",
            "timeline", "deadline", "appointment", "reminder", "organize",
            "coordinate", "logistics", "resource",
        ]
        cls._KEYWORD_MAP = [
            (AgentRole.CTO, tech_keywords),
            (AgentRole.CMO, marketing_keywords),
            (AgentRole.CPO, product_keywords),
            (AgentRole.CFO, finance_keywords),
            (AgentRole.COO, operations_keywords),
        ]
        return cls._KEYWORD_MAP

    def _score_agents(self, task_description: str, intent: str) -> List[tuple]:
        """Every sub-agent role ranked by keyword relevance to this task,
        highest first. Shared by primary routing and failure escalation, so
        a failed task is re-routed to whichever *remaining* agent actually
        fits it instead of just the next idle one."""
        desc_lower = task_description.lower()
        intent_lower = intent.lower()
        scored = [
            (role, sum(1 for kw in keywords if kw in desc_lower or kw in intent_lower))
            for role, keywords in self._keyword_map()
        ]
        scored.sort(key=lambda item: -item[1])
        return scored

    def _determine_best_agent(self, task_description: str, intent: str) -> AgentRole:
        """Determine which sub-agent should handle this task."""
        best_role, best_score = self._score_agents(task_description, intent)[0]
        return best_role if best_score > 0 else AgentRole.CEO

    async def _delegate_task(self, task: Task, role: AgentRole) -> Dict[str, Any]:
        """Delegate a task to a specific sub-agent."""
        agent = self._agents.get(role)
        if not agent:
            return {"status": "error", "message": f"No agent found for role: {role}"}

        if agent.status == "busy":
            self._pending_tasks.append(task)
            return {"status": "queued", "message": f"Task queued for {agent.name}. They are currently busy."}

        agent.status = "busy"
        agent.current_task = task
        task.status = "in_progress"
        self._active_tasks[task.id] = task

        try:
            if agent.executor:
                result = await agent.executor(task.description, task.intent)
            else:
                result = {"status": "success", "message": f"Agent {agent.name} processed task"}

            task.status = "completed"
            task.result = result
            task.completed_at = time.time()
            agent.performance_score = min(1.0, agent.performance_score + 0.05)
            agent.task_history.append(task.id)
            self._completed_tasks.append(task)
            self._active_tasks.pop(task.id, None)

            result["assigned_to"] = agent.name
            result["role"] = role.value
            return result

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            agent.performance_score = max(0.1, agent.performance_score - 0.1)

            result = {
                "status": "error",
                "message": f"{agent.name} failed: {e}",
                "assigned_to": agent.name,
                "role": role.value,
            }

            can_escalate = agent.performance_score > 0.3
            if can_escalate:
                result["escalated"] = await self._escalate_task(task)

            self._active_tasks.pop(task.id, None)
            self._completed_tasks.append(task)
            return result

        finally:
            agent.status = "idle"
            agent.current_task = None
            self._process_pending_queue()

    async def _escalate_task(self, failed_task: Task) -> Dict[str, Any]:
        """When a sub-agent fails, re-route to whichever remaining idle agent
        actually fits the task (by the same keyword scoring as primary
        routing) — not just whichever one happens to be idle first, which
        used to hand a failed coding task to the Marketing Lead."""
        idle_roles = {
            r for r, a in self._agents.items()
            if a.status == "idle" and r != failed_task.assigned_to
        }
        other_agents = [role for role, _score in self._score_agents(failed_task.description, failed_task.intent)
                        if role in idle_roles]
        other_agents += [r for r in idle_roles if r not in other_agents]
        if other_agents:
            new_role = other_agents[0]
            new_task = Task(
                id=self._generate_task_id(),
                description=failed_task.description,
                intent=failed_task.intent,
                priority=failed_task.priority,
                assigned_to=new_role,
                metadata={"escalated_from": failed_task.assigned_to.value},
            )
            return await self._delegate_task(new_task, new_role)

        return {"escalation": "failed", "message": "No available agents for escalation"}

    async def _handle_as_ceo(self, task: Task) -> Dict[str, Any]:
        """Coordinator: split the job across specialists, run each, show each result as it is
        (a model-written merge invented facts in the live check of 2026-10-22).

        It used to answer "[CEO] <your task>" — an echo, with no work done (owner report 2026-10-21).
        """
        if not self._can_think():
            return {"status": "error", "role": "ceo",
                    "message": "Coordinating specialists needs the language model, which is not available."}
        roles = ", ".join(f"{r.value} ({a.name}: {ROLE_FOCUS[r]})" for r, a in self._agents.items())
        system = ("You are TOM's coordinator. Split the user's job into 1-4 assignments for these specialists: "
                  f"{roles}. Each assignment is one concrete piece of work for one role. "
                  'Return ONLY JSON: {"assignments": [{"role": "cto|cmo|cpo|cfo|coo", "task": "..."}]}')
        valid = {r.value for r in self._agents}
        try:
            from tom_core.llm_json import parse_model_json
            plan = parse_model_json(await self._ask(system, f"Job: {task.description}"))
            assignments = [(AgentRole(a["role"]), str(a["task"])) for a in (plan or {}).get("assignments", [])
                           if isinstance(a, dict) and a.get("role") in valid and a.get("task")][:4]
        except Exception:
            assignments = []
        if not assignments:
            best = self._determine_best_agent(task.description, task.intent)
            assignments = [(best if best != AgentRole.CEO else AgentRole.CPO, task.description)]

        results = []
        for role, piece in assignments:
            sub = Task(id=self._generate_task_id(), description=piece, intent=task.intent,
                       created_at=time.time(), assigned_to=role)
            results.append((role, piece, await self._delegate_task(sub, role)))

        worked = [r for r in results if r[2].get("status") in ("success", "unverified")]
        digest = "\n\n".join(f"### {self._agents[role].name} — {piece}\nStatus: {res.get('status')}\n"
                               f"{str(res.get('message', ''))[:2500]}" for role, piece, res in results)
        who = "\n".join(f"- {self._agents[role].name}: {res.get('status')} — {piece}" for role, piece, res in results)
        return {"status": "success" if worked else "error", "role": "ceo",
                "message": f"{digest}\n\nWho did what:\n{who}",
                "assignments": [{"role": r.value, "task": p, "status": res.get("status")} for r, p, res in results]}

    # ── Specialists (PRD C10): real work with the tools each role is granted ──

    def _can_think(self) -> bool:
        return self.llm is not None or (self.tom_agent is not None and hasattr(self.tom_agent, "_invoke_llm"))

    async def _ask(self, system: str, user: str) -> str:
        agent = self.tom_agent
        if agent is not None and hasattr(agent, "_invoke_llm"):
            from langchain_core.prompts import ChatPromptTemplate
            prompt = ChatPromptTemplate.from_messages([("system", "{system}"), ("user", "{user}")])
            resp = await agent._invoke_llm(prompt, {"system": system, "user": user}, "specialist",
                                           getattr(agent, "llm", None))
            return getattr(resp, "content", "") or ""
        if self.llm is not None:
            from langchain_core.messages import HumanMessage, SystemMessage
            resp = await self.llm.ainvoke([SystemMessage(content=system), HumanMessage(content=user)])
            return getattr(resp, "content", "") or ""
        raise RuntimeError("No language model is available.")

    async def _specialist(self, role: AgentRole, task: str) -> Dict[str, Any]:
        """Do `task` as this role. Thinking work (a tagline, a budget split, a spec) is answered from
        the role's expertise in one model call; only work that touches this PC or the live web is
        planned and run with the role's granted tools (live check 2026-10-22: planning a tagline
        produced failing file writes instead of a tagline)."""
        name = self._agents[role].name
        if not self._can_think():
            return {"status": "error", "role": role.value, "message": f"{name} needs the language model."}
        report = None
        if _NEEDS_TOOLS.search(task):
            from tom_core.planning import run_goal
            from tom_core.tasks import service as _svc
            from tom_core.tools.registry import get_registry
            token = _svc._current_interface.set(f"specialist:{role.value}")   # audit + policy actor
            try:
                report = await run_goal(task, self._ask, get_registry(), allowed=ROLE_TOOLS[role])
            finally:
                _svc._current_interface.reset(token)
            if report.results and report.status in ("success", "unverified"):
                return {"status": report.status, "role": role.value, "message": f"[{name}]\n{report.text()}"}
        advice = await self._ask(
            f"You are TOM's {name}: {ROLE_FOCUS[role]}. Do this piece of work directly and concretely in "
            "American English — analysis, a draft, a plan or a recommendation. You cannot act outside this "
            "answer, so never claim you sent, saved, opened or ran anything.", task)
        message = f"[{name}]\n{advice.strip()}"
        if report is not None and report.results:          # tools were tried and failed: say so
            message += f"\n\n(Tool steps that did not work:\n{report.text()})"
            return {"status": "partial", "role": role.value, "response_type": "specialist_answer",
                    "message": message}
        return {"status": "success", "role": role.value, "response_type": "specialist_answer", "message": message}

    async def _execute_cto_task(self, task: str, intent: str) -> Dict[str, Any]:
        return await self._specialist(AgentRole.CTO, task)

    async def _execute_cmo_task(self, task: str, intent: str) -> Dict[str, Any]:
        return await self._specialist(AgentRole.CMO, task)

    async def _execute_cpo_task(self, task: str, intent: str) -> Dict[str, Any]:
        return await self._specialist(AgentRole.CPO, task)

    async def _execute_cfo_task(self, task: str, intent: str) -> Dict[str, Any]:
        return await self._specialist(AgentRole.CFO, task)

    async def _execute_coo_task(self, task: str, intent: str) -> Dict[str, Any]:
        return await self._specialist(AgentRole.COO, task)

    def _process_pending_queue(self):
        """Process the next pending task if a suitable agent is free."""
        if not self._pending_tasks:
            return
        for task in list(self._pending_tasks):
            agent = self._agents.get(task.assigned_to) if task.assigned_to else None
            if agent and agent.status == "idle":
                self._pending_tasks.remove(task)
                asyncio.create_task(self._delegate_task(task, task.assigned_to))

    # ── Utilities ───────────────────────────────────────────────────────

    def _generate_task_id(self) -> str:
        self._task_counter += 1
        return f"TASK-{int(time.time())}-{self._task_counter}"

    def get_agents_status(self) -> Dict[str, Any]:
        """Get status of all agents including CEO (orchestrator)."""
        status = {
            "ceo": {
                "name": "CEO Orchestrator",
                "status": "active",
                "capabilities": ["task_decomposition", "delegation", "escalation", "coordination"],
                "performance": 1.0,
                "tasks_completed": len(self._completed_tasks),
                "current_task": None,
            }
        }
        for role, agent in self._agents.items():
            status[role.value] = {
                "name": agent.name,
                "status": agent.status,
                "capabilities": agent.capabilities,
                "performance": round(agent.performance_score, 2),
                "tasks_completed": len(agent.task_history),
                "current_task": agent.current_task.description[:80] if agent.current_task else None,
            }
        return status

    def get_metrics(self) -> Dict[str, Any]:
        """Get orchestration metrics."""
        return {
            "total_tasks_created": self._task_counter,
            "completed_tasks": len(self._completed_tasks),
            "active_tasks": len(self._active_tasks),
            "pending_tasks": len(self._pending_tasks),
            "agent_count": len(self._agents),
            "agents": self.get_agents_status(),
        }

    async def deploy_multi_agent_task(self, task_description: str) -> Dict[str, Any]:
        """Multi-Agent quick action: the coordinator splits the job across specialists."""
        result = await self.execute_task(task_description, coordinate=True)
        return {
            "status": result.get("status", "completed"),
            "message": result.get("message", ""),
            "orchestration": self.get_metrics(),
        }
