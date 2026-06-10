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
import json
import logging
import os
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

    async def execute_task(self, task_description: str, intent: str = "") -> Dict[str, Any]:
        """CEO entry point: decompose task, delegate to sub-agents, aggregate results."""
        task_id = self._generate_task_id()

        task = Task(
            id=task_id,
            description=task_description,
            intent=intent,
            created_at=time.time(),
        )

        role = self._determine_best_agent(task_description, intent)
        task.assigned_to = role

        if role == AgentRole.CEO:
            return await self._handle_as_ceo(task)

        result = await self._delegate_task(task, role)
        return result

    def _determine_best_agent(self, task_description: str, intent: str) -> AgentRole:
        """Determine which sub-agent should handle this task."""
        desc_lower = task_description.lower()
        intent_lower = intent.lower()

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

        keyword_map = [
            (AgentRole.CTO, tech_keywords),
            (AgentRole.CMO, marketing_keywords),
            (AgentRole.CPO, product_keywords),
            (AgentRole.CFO, finance_keywords),
            (AgentRole.COO, operations_keywords),
        ]

        best_role = AgentRole.CEO
        best_score = 0

        for role, keywords in keyword_map:
            score = sum(1 for kw in keywords if kw in desc_lower or kw in intent_lower)
            if score > best_score:
                best_score = score
                best_role = role

        return best_role

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
        """When a sub-agent fails, escalate to CEO for re-routing."""
        other_agents = [
            r for r, a in self._agents.items()
            if a.status == "idle" and r != failed_task.assigned_to
        ]
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
        """CEO handles tasks that don't fit any sub-agent or require coordination."""
        if self.llm:
            from langchain_core.prompts import ChatPromptTemplate
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are TOM acting as CEO. Analyze the task and break it down if needed. "
                           "Return JSON: {\"plan\": [\"step1\", \"step2\"], \"delegation\": \"self|cto|cmo|cpo|cfo|coo\"}"),
                ("user", "Task: {task}"),
            ])
            try:
                resp = await (prompt | self.llm).ainvoke({"task": task.description})
                content = resp.content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                analysis = json.loads(content)
                delegation = analysis.get("delegation", "self")

                if delegation != "self":
                    try:
                        role = AgentRole(delegation)
                        return await self._delegate_task(task, role)
                    except ValueError:
                        pass

                return {
                    "status": "success",
                    "message": f"[CEO] Processed: {task.description}",
                    "plan": analysis.get("plan", []),
                    "role": "ceo",
                }
            except Exception as e:
                return {"status": "success", "message": f"[CEO] {task.description}", "role": "ceo"}

        return {"status": "success", "message": f"[CEO] {task.description}", "role": "ceo"}

    def _process_pending_queue(self):
        """Process the next pending task if a suitable agent is free."""
        if not self._pending_tasks:
            return
        for task in list(self._pending_tasks):
            agent = self._agents.get(task.assigned_to) if task.assigned_to else None
            if agent and agent.status == "idle":
                self._pending_tasks.remove(task)
                asyncio.create_task(self._delegate_task(task, task.assigned_to))

    # ── Sub-agent Executors ─────────────────────────────────────────────

    async def _execute_cto_task(self, task: str, intent: str) -> Dict[str, Any]:
        """CTO handles technical tasks."""
        tech_keywords = ["web automation", "browser", "localhost", "debug", "code"]
        if any(kw in task.lower() for kw in tech_keywords) and self.tom_agent:
            if "web automation" in task.lower() or "browser" in task.lower() or "localhost" in task.lower():
                try:
                    from tools.web_automation import WebAutomationSuite
                    auto = WebAutomationSuite(self.tom_agent.browser_tools)
                    page = await self.tom_agent.browser_tools._get_active_page()
                    if page and ("localhost" in task.lower() or "http" in task.lower()):
                        url_match = __import__("re").search(r'https?://[^\s]+', task)
                        if url_match:
                            result = await auto.wait_and_verify(url_match.group(0))
                            return result
                except Exception as e:
                    return {"status": "error", "message": f"[CTO] Web automation failed: {e}", "role": "cto"}

        return {"status": "info", "message": f"[CTO] Technical assessment: {task}", "role": "cto"}

    async def _execute_cmo_task(self, task: str, intent: str) -> Dict[str, Any]:
        """CMO handles marketing/content tasks."""
        return {"status": "info", "message": f"[CMO] Marketing assessment: {task}", "role": "cmo"}

    async def _execute_cpo_task(self, task: str, intent: str) -> Dict[str, Any]:
        """CPO handles product tasks."""
        return {"status": "info", "message": f"[CPO] Product assessment: {task}", "role": "cpo"}

    async def _execute_cfo_task(self, task: str, intent: str) -> Dict[str, Any]:
        """CFO handles financial tasks."""
        return {"status": "info", "message": f"[CFO] Financial assessment: {task}", "role": "cfo"}

    async def _execute_coo_task(self, task: str, intent: str) -> Dict[str, Any]:
        """COO handles operational tasks."""
        return {"status": "info", "message": f"[COO] Operations assessment: {task}", "role": "coo"}

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
        """Deploy a complex task across multiple agents with coordination."""
        result = await self.execute_task(task_description)
        return {
            "status": result.get("status", "completed"),
            "message": result.get("message", ""),
            "orchestration": self.get_metrics(),
        }
