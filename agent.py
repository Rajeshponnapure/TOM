import asyncio
import json
import os
import re
import subprocess
from typing import Any, Dict, Optional

from langchain_core.prompts import ChatPromptTemplate

from tools import llm_factory
from tools.os_tools import OSTools
from tools.browser_tools import BrowserTools
from tools.file_tools import FileTools
from tools.email_tools import EmailTools
from tools.command_router import CommandRouter, RouteDecision
from tools.approval import ApprovalManager, ApprovalRequest
from tools.chrome_profiles import ChromeProfileManager
from tools.screen_tools import ScreenTools
from tools.plugin_manager import PluginManager
from tools.email_agent_controller import EmailAgentController
from tools.instagram_agent_controller import InstagramAgentController
from tools.instruction_loader import compose_system_prompt
from safety.guards import SafetyGuards
from tools.agent_builder import create_agent_scaffold
from tools.email_tools import (classify_email_item as _classify_email_item_fn,
                               AutoReplyLedger, auto_reply_if_allowed, is_valid_address)
from tools.learning import Learner
from tools.chat_memory import ChatMemory
from tools.scheduler import get_scheduler
from tools.whatsapp_tools import WhatsAppTools
from tools.chat_apps import ChatApps
from tools.text_utils import without_addresses
from tools.nlp_parser import CommandParser
from tools.rag_memory import get_rag, RAGMemory
from tools.self_evolution import get_evolution, SelfEvolution
from tools.file_analyzer import FileAnalyzer
from tools.project_paths import PROJECT_ROOT, project_path_str
from tools.skill_manager import SkillManager, SkillRoute
from tools.capability_resolver import CapabilityResolver
from tools.hindsight_memory import get_memory, MemoryHit, TAG_PREFERENCE, TAG_CORRECTION, TAG_TASK
from tools import memory_rules
import base64
import time


_progress_callback = None

def set_progress_callback(fn):
    global _progress_callback
    _progress_callback = fn

_UNREACHABLE_MARKERS = ("all connection attempts failed", "connection refused",
                        "failed to connect to ollama", "max retries exceeded")


def _llm_unreachable_hint(exc: BaseException) -> str:
    """Fix-it hint when a task failed because the model server is unreachable.

    httpx/ollama surface this as "All connection attempts failed", which does
    not tell the user that Ollama (or Groq) is the problem.
    """
    seen = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        text = str(exc).lower()
        if (isinstance(exc, ConnectionError) or type(exc).__name__ == "ConnectError"
                or any(m in text for m in _UNREACHABLE_MARKERS)):
            if llm_factory.provider() == "groq":
                return ("Could not reach the Groq API. Check your internet connection "
                        "and GROQ_API_KEY in .env.")
            base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            return (f"Could not reach the Ollama model server at {base_url}. "
                    f"Start it with 'ollama serve' (and 'ollama pull {llm_factory.resolve_model('primary')}'), "
                    "or set TOM_LLM_PROVIDER=groq with GROQ_API_KEY in .env.")
        exc = exc.__cause__ or exc.__context__
    return ""


# Image containers a vision model can be handed, as a data-URI mime subtype.
_IMAGE_MIME = {".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg",
               ".webp": "webp", ".gif": "gif", ".bmp": "bmp"}


def _image_mime(path: str) -> str:
    return _IMAGE_MIME.get(os.path.splitext(path or "")[1].lower(), "png")


def _message_text(response: Any) -> str:
    """Plain text from a LangChain message (content may be a list of parts)."""
    content = getattr(response, "content", response)
    if isinstance(content, list):
        return " ".join(str(part.get("text", "")) for part in content
                        if isinstance(part, dict)).strip()
    return str(content or "").strip()


def safe_print(message: str):
    clean = message.encode("ascii", errors="ignore").decode("ascii")
    print(clean)
    if _progress_callback and message.strip():
        try:
            _progress_callback(message.strip())
        except Exception:
            pass


class TomAgent:
    def __init__(self):
        # Primary model (Gemma 4 - best for complex reasoning)
        # ── Model slots (resolved against installed Ollama models) ──────
        # Each slot reads its OLLAMA_*_MODEL env var; if the configured model
        # is not pulled on this machine, llm_factory falls back to an
        # installed model so TOM never dies with 404 "model not found".
        self.model_name      = llm_factory.resolve_model("primary")
        self.fast_model_name = llm_factory.resolve_model("fast")
        self.code_model_name = llm_factory.resolve_model("code")
        self.embed_model_name = llm_factory.resolve_model("embed")
        self.model_timeout_seconds = int(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "120"))
        self.task_timeout_seconds = int(os.environ.get("TASK_TIMEOUT_SECONDS", "180"))

        # ── LLM factory (model-agnostic, provider-agnostic) ──────────────
        # TOM_LLM_PROVIDER=ollama (local, default) or groq (hosted).
        # Call switch_model(name) at any time to hot-swap all slots.
        self.llm_provider = llm_factory.provider()
        if self.llm_provider == "groq":
            self.model_name = llm_factory.groq_model("primary")
            self.fast_model_name = llm_factory.groq_model("fast")
            self.code_model_name = llm_factory.groq_model("code")

        def _make(model: str, tokens: int):
            return llm_factory.make_chat_model(model, max_tokens=tokens)

        self.llm      = _make(self.model_name,      4096)  # primary (complex reasoning)
        self.fast_llm = _make(self.fast_model_name, 2048)  # fast (parsing, NLP)
        self.chat_llm = _make(self.fast_model_name,  256)  # chat (short replies)
        self.code_llm = _make(self.code_model_name, 4096)  # code generation

        # NLP Parser — uses fast_llm (updated by switch_model)
        self.nlp_parser = CommandParser(llm=self.fast_llm)

        # Tools
        self.os_tools = OSTools()
        self.browser_tools = BrowserTools()
        self.file_tools = FileTools()
        self.email_tools = EmailTools()
        self.email_agent_controller = EmailAgentController()
        self.instagram_agent_controller = InstagramAgentController()
        self.safety = SafetyGuards()
        self.learner = Learner()
        self.chat_memory = ChatMemory()
        self.command_router = CommandRouter()
        self.skill_manager = SkillManager()
        try:
            from tools.skill_telemetry import SkillTelemetry
            self.skill_telemetry = SkillTelemetry()
        except Exception:
            self.skill_telemetry = None
        self.capability_resolver = CapabilityResolver()
        self.approval_manager = ApprovalManager()
        self.whatsapp_tools = WhatsAppTools(self.browser_tools)
        self.chat_apps = ChatApps()
        self.chrome_profiles = ChromeProfileManager()
        self.screen_tools = ScreenTools()
        self.file_analyzer = FileAnalyzer()
        self.plugin_manager = PluginManager(str(PROJECT_ROOT))
        self.available_plugins = self.plugin_manager.discover_plugins()

        self.system_prompt_file = project_path_str("config", "system_prompt.txt")

        # Tracking for feedback
        self._last_command = ""
        self._last_response = ""
        self._last_exp_id = None
        self._last_result = None

        # ── Long-term memory (Hindsight) ─────────────────────────────────
        # What TOM has *learned* about this user: corrections, standing
        # preferences and task outcomes — recalled before every task.
        self.memory = get_memory()
        self._recalled: list = []          # MemoryHit list for the task in flight
        safe_print(f"[MEMORY] {self.memory.status_line()}")

        # ── RAG semantic memory ──────────────────────────────────────────
        # Stores all conversations, documents, and knowledge as vectors.
        # Retrieves relevant context by meaning, not just keyword match.
        try:
            self.rag = get_rag()
            if self.rag.available:
                safe_print("[RAG] Semantic memory online.")
            else:
                safe_print("[RAG] ChromaDB unavailable — run: pip install chromadb")
        except Exception as _rag_err:
            self.rag = None
            safe_print(f"[RAG] Could not initialise: {_rag_err}")

        # ── Self-evolution / adaptive intelligence ───────────────────────
        # Learns from successes, failures, and user feedback.
        # Adapts system prompts and approach hints over time.
        try:
            self.evolution = get_evolution()
            safe_print("[EVOLUTION] Adaptive intelligence online.")
        except Exception as _evo_err:
            self.evolution = None
            safe_print(f"[EVOLUTION] Could not initialise: {_evo_err}")

        # ── Curated knowledge base (knowledge/ + knowledge/*.md) ────────
        # Previously orphaned; now consulted by _build_knowledge_context so
        # every chat/skill-routed prompt can use the curated domain library.
        try:
            from tools.knowledge_engine import get_engine as _get_knowledge_engine
            self.knowledge = _get_knowledge_engine()
            _ks = self.knowledge.get_stats()
            safe_print(f"[KNOWLEDGE] Curated knowledge online "
                       f"({_ks.get('domains', 0)} domains, {_ks.get('total_sections', 0)} sections).")
        except Exception as _kn_err:
            self.knowledge = None
            safe_print(f"[KNOWLEDGE] Could not initialise: {_kn_err}")

        # ── MCP connector layer ──────────────────────────────────────────
        # Gives TOM access to GitHub, Gmail, Slack, Notion, WhatsApp, etc.
        try:
            from tools.mcp_manager import get_mcp_manager
            self.mcp = get_mcp_manager()
            safe_print("[MCP] Connector layer online.")
        except Exception as _mcp_err:
            self.mcp = None
            safe_print(f"[MCP] Could not initialise: {_mcp_err}")

        # ── Agent Orchestrator (Multi-Agent CEO/CTO/CMO/CPO) ────────────
        try:
            from tools.agent_orchestrator import AgentOrchestrator
            self.orchestrator = AgentOrchestrator(tom_agent=self, llm=self.llm)
            safe_print("[ORCHESTRATOR] Multi-agent system online.")
        except Exception as _orch_err:
            self.orchestrator = None
            safe_print(f"[ORCHESTRATOR] Could not initialise: {_orch_err}")

        # ── Web Automation Suite ─────────────────────────────────────────
        try:
            from tools.web_automation import WebAutomationSuite
            self.web_automation = WebAutomationSuite(self.browser_tools)
            safe_print("[WEB_AUTO] Web automation suite online.")
        except Exception as _web_err:
            self.web_automation = None
            safe_print(f"[WEB_AUTO] Could not initialise: {_web_err}")

        # ── Unified Engine Router ────────────────────────────────────────
        # Routes ML / IoT / VLSI / Hardware / Blender / GameDev / News /
        # Env / Auto-update / Autonomous / Multi-agent commands so the CLI
        # and chat reach the same engines the GUI buttons expose.
        try:
            from tools.engine_router import EngineRouter
            self.engine_router = EngineRouter(agent=self)
            safe_print("[ENGINES] Unified engine router online.")
        except Exception as _eng_err:
            self.engine_router = None
            safe_print(f"[ENGINES] Could not initialise: {_eng_err}")

    def _make_llm(self, model: str, max_tokens: int = 4096):
        """Factory — create a chat model for any model name on the active provider."""
        return llm_factory.make_chat_model(model, max_tokens=max_tokens)

    def switch_model(self, model_name: str) -> None:
        """
        Hot-swap ALL three LLMs to a different locally-installed Ollama model.
        TOM is model-agnostic — it works with Gemma, Qwen, Llama, Mistral,
        Phi, DeepSeek, or any model installed via `ollama pull <name>`.
        """
        self.model_name      = model_name
        self.fast_model_name = model_name   # single-model mode: use same model everywhere
        self.code_model_name = model_name
        env_prefix = "GROQ" if llm_factory.provider() == "groq" else "OLLAMA"
        os.environ[f"{env_prefix}_MODEL"]      = model_name
        os.environ[f"{env_prefix}_FAST_MODEL"] = model_name
        os.environ[f"{env_prefix}_CODE_MODEL"] = model_name
        self._persist_model_env(model_name, env_prefix)

        self.llm      = self._make_llm(model_name, max_tokens=4096)
        self.fast_llm = self._make_llm(model_name, max_tokens=2048)
        self.chat_llm = self._make_llm(model_name, max_tokens=256)
        self.code_llm = self._make_llm(model_name, max_tokens=4096)

        # Rebuild NLP parser with updated LLM
        self.nlp_parser = CommandParser(llm=self.fast_llm)
        safe_print(f"[MODEL] All LLMs switched to: {model_name}")

    def switch_provider(self, provider_name: str) -> Dict[str, Any]:
        """Hot-swap between Groq (hosted) and Ollama (local) at runtime.

        The factory resolves provider and models from the environment on every
        call, so a switch is: set TOM_LLM_PROVIDER, rebuild the four chat slots
        (the embed slot stays local on both providers — Groq has no embeddings
        endpoint) and re-read the model names. Model choice is preserved per
        provider via the GROQ_*/OLLAMA_* env vars already in .env. Raises
        RuntimeError when the target provider cannot serve a chat, leaving the
        previous provider fully intact.
        """
        old_provider = llm_factory.provider()
        new_provider = llm_factory.set_provider(provider_name)
        if new_provider == old_provider:
            return {"provider": new_provider, "model": self.model_name, "changed": False}

        try:
            if new_provider == "groq":
                primary = llm_factory.groq_model("primary")
                if not (os.environ.get("GROQ_API_KEY") or "").strip():
                    raise RuntimeError(
                        "Groq needs GROQ_API_KEY in .env before TOM can switch to it. "
                        "Staying on Ollama.")
            else:
                primary = llm_factory.resolve_model("primary")
                if not llm_factory.ollama_installed_models():
                    raise RuntimeError(
                        "Ollama is not reachable at "
                        f"{os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')}. "
                        "Start it with 'ollama serve' — staying on Groq.")

            self.llm_provider = new_provider
            self.model_name = primary
            self.fast_model_name = primary
            self.code_model_name = primary
            self.llm      = self._make_llm(primary, max_tokens=4096)
            self.fast_llm = self._make_llm(primary, max_tokens=2048)
            self.chat_llm = self._make_llm(primary, max_tokens=256)
            self.code_llm = self._make_llm(primary, max_tokens=4096)
            self.nlp_parser = CommandParser(llm=self.fast_llm)
        except Exception:
            # Put the old provider back before reporting the failure.
            llm_factory.set_provider(old_provider)
            raise

        self._persist_model_env(primary, "GROQ" if new_provider == "groq" else "OLLAMA")
        llm_factory.persist_provider(new_provider)
        safe_print(f"[MODEL] Provider switched to {new_provider} ({primary})")
        return {"provider": new_provider, "model": primary, "changed": True}

    @staticmethod
    def _persist_model_env(model_name: str, env_prefix: str = "OLLAMA",
                           env_path=None) -> None:
        """Write the model choice into the project .env so it survives restarts.

        The desktop dropdown swaps all chat slots to one model (single-model
        mode), so <PREFIX>_MODEL, <PREFIX>_FAST_MODEL and <PREFIX>_CODE_MODEL
        are all persisted (PREFIX is OLLAMA or GROQ, matching the active
        provider). The embed slot is left alone — embeddings need an
        embedding model, not a chat model.
        """
        try:
            if env_path is None:
                env_path = PROJECT_ROOT / ".env"
            lines: list = env_path.read_text(encoding="utf-8").splitlines() \
                if env_path.is_file() else []
            keys = (f"{env_prefix}_MODEL", f"{env_prefix}_FAST_MODEL", f"{env_prefix}_CODE_MODEL")
            for key in keys:
                # Matches "KEY=value", "export KEY=value" and "KEY=value  # note".
                pattern = re.compile(rf"^\s*(?:export\s+)?{re.escape(key)}\s*=")
                replaced = False
                for i, line in enumerate(lines):
                    if pattern.match(line):
                        lines[i] = f"{key}={model_name}"
                        replaced = True
                        break
                if not replaced:
                    if lines and lines[-1].strip():
                        lines.append("")
                    lines.append(f"{key}={model_name}")
            env_path.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
        except Exception as exc:
            safe_print(f"[MODEL] Could not persist model to .env: {exc}")

    # ── Workspace routing (build OUTSIDE the TOM repo) ───────────────────
    # Every user deliverable (website, code scaffold, document) is written to
    # the Desktop workspace, or to an explicit absolute path the user named —
    # never scattered inside the TOM install.

    @staticmethod
    def _extract_target_dir(command: str) -> str:
        """An explicit absolute output directory named in the command, or "".

        Recognises a Windows drive path (C:\\Users\\me\\Proj), a UNC share
        (\\\\server\\share) or a POSIX home/mnt path. Conservative on purpose:
        a false positive would misplace the whole build, so only a clearly
        absolute path counts.
        """
        m = re.search(r'([A-Za-z]:[\\/][^\s"\'<>|?*]*|\\\\[^\s"\'<>|?*]+'
                      r'|/(?:home|mnt|media|Users|tmp)/[^\s"\'<>|?*]+)', command or "")
        if not m:
            return ""
        cand = m.group(1).strip().rstrip(" .,:;\"'")
        if cand.lower().startswith(("http://", "https://")):
            return ""
        return cand

    def _deliverable_target(self, command: str, parsed: Dict, default_name: str) -> str:
        """Absolute directory a user deliverable should be built in.

        Explicit user path wins; otherwise a per-project subfolder in the
        Desktop workspace (keeps each build tidy and out of the TOM repo).
        """
        explicit = self._extract_target_dir(command)
        if explicit:
            try:
                os.makedirs(explicit, exist_ok=True)
            except Exception:
                pass
            return explicit
        from tools.project_paths import resolve_deliverable_dir
        name = (parsed.get("subject") or parsed.get("app_name")
                or parsed.get("file_name") or default_name or "project")
        return str(resolve_deliverable_dir(subfolder=str(name)))

    @staticmethod
    def _place_in(base_dir: str, raw_path: str) -> str:
        """Resolve one '--- FILE: <raw_path> ---' entry under base_dir."""
        raw = (raw_path or "").strip().strip('"').strip("'")
        return raw if os.path.isabs(raw) else os.path.join(base_dir, raw)

    def _build_memory_context(self, query: str) -> str:
        """Build context string: recent chat + RAG semantic retrieval + curated knowledge."""
        chat_ctx = self.chat_memory.build_context(query=query, recent_n=14, relevant_n=10, max_chars=4000)
        parts = []
        long_term = self._long_term_context()
        if long_term:
            parts.append(long_term)
        parts.append(chat_ctx)
        if self.rag and self.rag.available:
            try:
                rag_ctx = self.rag.build_rag_context(query, max_chars=2500)
                if rag_ctx:
                    parts.append(rag_ctx)
            except Exception:
                pass
        know_ctx = self._build_knowledge_context(query)
        if know_ctx:
            parts.append(know_ctx)
        return "\n\n".join(p for p in parts if p)

    # ── LONG-TERM MEMORY (Hindsight) ────────────────────────────────────

    def _long_term_context(self, max_chars: int = 1800) -> str:
        """Recalled memories for the task in flight, formatted for prompts."""
        hits = getattr(self, "_recalled", None) or []
        if not hits:
            return ""
        prefs = [h for h in hits if h.is_preference]
        others = [h for h in hits if not h.is_preference]
        lines = ["Long-term memory — learned from earlier sessions with this user. "
                 "Apply these; if two conflict, the more recent one wins:"]
        for h in prefs + others:
            stamp = f" ({h.when})" if h.when else ""
            lines.append(f"- {h.text}{stamp}")
        return "\n".join(lines)[:max_chars]

    def _relevant_preferences(self, command: str, limit: int = 3) -> list:
        """Recalled preferences worth showing the user for this request."""
        category = memory_rules.categorize(command)
        shown = []
        for h in getattr(self, "_recalled", None) or []:
            if not h.is_preference:
                continue
            if category != "general" and memory_rules.categorize(h.text) not in (category, "general"):
                continue
            shown.append(h.text)
            if len(shown) >= limit:
                break
        return shown

    async def remembered_folder_rules(self, command: str):
        """Folder-organizing rules this user taught TOM in earlier sessions.

        1. recall() preference/correction memories about organizing files
        2. parse them into concrete FolderRules (deterministic)
        3. if memories exist but none parse, ask reflect() for structured rules
        Returns (rules, note) — note explains memory state when no rule applies.
        """
        if not self.memory.available:
            return [], ""
        query = ("How does the user want files in their folders organized? "
                 "Where should PDFs, invoices, screenshots, images, installers and other file "
                 f"types go, and what should be left alone? Request: {command}")
        hits = await self.memory.arecall(query, tags=[TAG_PREFERENCE, TAG_CORRECTION], limit=12,
                                         budget="mid")
        texts = [h.text for h in hits]
        # The user's own words (local journal) back up Hindsight's extracted facts.
        for item in self.memory.recent_journal(limit=40):
            tags = item.get("tags") or []
            if (TAG_PREFERENCE in tags or TAG_CORRECTION in tags) and "file_organization" in tags:
                raw = (item.get("metadata") or {}).get("user_words")
                if raw:
                    texts.append(raw)
        rules = memory_rules.parse_folder_rules(texts)
        if not rules and hits:
            out = await self.memory.areflect(
                "List the user's rules for organizing files into subfolders.",
                response_schema=memory_rules.FOLDER_RULES_SCHEMA, timeout=40.0)
            if out.get("ok"):
                rules = memory_rules.rules_from_structured(out.get("structured"), source="reflect")
        if hits and not rules:
            return [], "(I checked my memory — nothing specific about organizing this folder yet.)"
        return rules, ""

    def _chat_session(self) -> Dict[str, str]:
        """Id + title of the open chat, for tagging long-term memory. Never raises."""
        try:
            return self.chat_memory.active_session_info()
        except Exception:
            return {"id": "", "title": ""}

    def _retain_preference(self, command: str) -> None:
        """Store a correction / standing preference the user just stated."""
        category = memory_rules.categorize(command)
        correction = memory_rules.is_correction(command)
        session = self._chat_session()
        if correction and self._last_command:
            content = (f"After TOM handled the request \"{self._last_command[:200]}\" "
                       f"(TOM replied: \"{' '.join(self._last_response.split())[:240]}\"), the user corrected TOM: "
                       f"\"{command}\"")
        else:
            content = f"The user told TOM a standing instruction: \"{command}\""
        tags = [TAG_PREFERENCE, category] + ([TAG_CORRECTION] if correction else [])
        context = f"user preference about {category.replace('_', ' ')}"
        if session.get("title"):
            context += f" — said in chat \"{session['title'][:60]}\""
        self.memory.retain(content, context=context, tags=tags,
                           metadata={"user_words": command[:400], "category": category,
                                     "session_title": session.get("title", "")},
                           index_now=True, session_id=session.get("id", ""))

    def _retain_outcome(self, command: str, result: Dict[str, Any], intent: str) -> None:
        """Store what TOM did and how it went, so future attempts can learn from it."""
        status = str(result.get("status", "unknown"))
        category = memory_rules.categorize(command)
        how = result.get("response_type") or intent or "general"
        raw = str(result.get("message", ""))
        if raw.startswith("Remembering") and "\n\n" in raw:
            raw = raw.split("\n\n", 1)[1]          # the applied rules are recorded separately below
        message = " ".join(raw.split())[:320]
        content = f"The user asked TOM: \"{command[:300]}\". TOM handled it as '{how}' and the outcome was {status}."
        if message:
            content += f" TOM's reply: {message}"
        applied = result.get("applied_rules") or []
        if applied:
            content += " Remembered rules applied: " + "; ".join(a["rule"] for a in applied) + "."
        session = self._chat_session()
        context = f"task outcome — {category.replace('_', ' ')}"
        if session.get("title"):
            context += f" — chat \"{session['title'][:60]}\""
        self.memory.retain(content, context=context,
                           tags=[TAG_TASK, category, f"status:{status}"],
                           metadata={"category": category, "status": status,
                                     "session_title": session.get("title", "")},
                           session_id=session.get("id", ""))

    async def _memory_command(self, command: str) -> Optional[Dict[str, Any]]:
        """Meta commands about TOM's long-term memory. None if not one."""
        low = command.lower().strip().rstrip("?!. ")
        learned = ("what have you learned about me", "what have you learned",
                   "what do you know about me", "what do you remember about me",
                   "what have you learnt about me", "what did you learn about me",
                   "how do i like things done", "memory summary", "summarize your memory",
                   "what do you remember")
        if low in learned:
            if not self.memory.available:
                return {"status": "error", "response_type": "memory",
                        "message": self.memory.status_line()}
            out = await self.memory.areflect(
                "Summarize what you have learned about how this user likes their work done: "
                "standing preferences, rules and corrections, grouped by area (files, email, "
                "documents, other). Short bullet points, most recent instruction first when they conflict.",
                budget="mid", timeout=60.0)
            text = out.get("text") or "I don't have enough history with you yet — correct me as we go and I'll remember."
            return {"status": "success" if out.get("ok") else "error", "response_type": "memory_reflect",
                    "message": "Here's what I've learned about how you work:\n\n" + text}
        if low in ("memory", "memory status", "show memory", "show memories", "long term memory",
                   "long-term memory", "hindsight status"):
            st = self.memory.status()
            recent = self.memory.recent_journal(limit=8)
            lines = [self.memory.status_line(),
                     f"This session: {st['retained']} retained · {st['recalled']} recalls · "
                     f"{st['reflected']} reflections · {st['failed']} failed · {st['pending']} queued"]
            if recent:
                lines.append("\nMost recent things I stored:")
                for item in recent:
                    tag = "rule" if TAG_PREFERENCE in (item.get("tags") or []) else "task"
                    words = (item.get("metadata") or {}).get("user_words") or item.get("content", "")
                    lines.append(f"  [{tag}] {words[:140]}")
            return {"status": "success", "response_type": "memory_status", "message": "\n".join(lines)}
        m = re.match(r"^(?:what do you (?:remember|know) about|recall|search (?:your )?memory for)\s+(.+)$", low)
        if m:
            topic = m.group(1).strip()
            hits = await self.memory.arecall(topic, limit=8, budget="mid")
            if not hits:
                return {"status": "success", "response_type": "memory_recall",
                        "message": f"Nothing in my long-term memory about '{topic}' yet."}
            body = "\n".join(f"  • {h.text}" + (f"  ({h.when})" if h.when else "") for h in hits)
            return {"status": "success", "response_type": "memory_recall",
                    "message": f"What I remember about '{topic}':\n{body}",
                    "memories_used": [h.text for h in hits]}
        return None

    def _build_knowledge_context(self, query: str, max_chars: int = 1400) -> str:
        """Retrieve curated domain knowledge for the query (fails silently to "").

        Wires the previously-orphaned KnowledgeEngine into reasoning:
        1. structured JSON domains via engine.search()
        2. legacy knowledge/*.md docs via keyword-overlap excerpts
        """
        if not getattr(self, "knowledge", None):
            return ""
        try:
            _stop = {"like", "what", "when", "where", "which", "this", "that",
                     "with", "from", "have", "will", "your", "about", "does",
                     "make", "want", "need", "please", "help", "some", "more",
                     "very", "just", "into", "over", "then", "them", "they",
                     "their", "there", "here", "also", "tell", "give", "show"}
            words = [w for w in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{3,}", query.lower())
                     if w not in _stop][:8]
            blocks = []

            # 1) Structured domain sections
            seen = set()
            for w in words:
                for r in self.knowledge.search(w):
                    key = (r.get("domain_key"), r.get("section"))
                    if key in seen:
                        continue
                    seen.add(key)
                    dom = self.knowledge.cache.get(r.get("domain_key"), {})
                    for section in dom.get("sections", []):
                        if section.get("name") == r.get("section"):
                            expl = (section.get("explanation_simple") or "").strip()
                            concepts = ", ".join(section.get("key_concepts", [])[:6])
                            line = f"[{r.get('domain')} / {r.get('section')}] {expl[:280]}"
                            if concepts:
                                line += f" Key concepts: {concepts}"
                            blocks.append(line)
                            break
                    if len(blocks) >= 3:
                        break
                if len(blocks) >= 3:
                    break

            # 2) Legacy .md docs — score by keyword overlap, excerpt best two
            legacy = self.knowledge.cache.get("legacy", {}).get("topics", [])
            scored = []
            for t in legacy:
                content = t.get("content") or ""
                if not content:
                    continue
                low = content.lower()
                score = sum(low.count(w) for w in words)
                if score > 0:
                    scored.append((score, t))
            scored.sort(key=lambda x: x[0], reverse=True)
            for _score, t in scored[:2]:
                content = t["content"]
                low = content.lower()
                pos = min((low.find(w) for w in words if low.find(w) >= 0), default=0)
                start = max(0, pos - 80)
                blocks.append(f"[KB doc: {t.get('name')}] " + content[start:start + 420].strip())

            if not blocks:
                return ""
            return ("Curated knowledge base context (authoritative project knowledge):\n"
                    + "\n".join(blocks))[:max_chars]
        except Exception:
            return ""

    def get_system_prompt(self) -> str:
        try:
            if os.path.exists(self.system_prompt_file):
                base = compose_system_prompt(
                    open(self.system_prompt_file, "r").read(), "TOM", include_ui=True
                )
            else:
                base = compose_system_prompt(self.get_default_system_prompt(), "TOM", include_ui=True)
        except Exception:
            base = compose_system_prompt(self.get_default_system_prompt(), "TOM", include_ui=True)

        # Inject personalised adaptive section if evolution is running
        if self.evolution:
            try:
                adaptive = self.evolution.get_adaptive_system_prompt()
                if adaptive:
                    base = base + "\n\n[ADAPTIVE PREFERENCES]\n" + adaptive
            except Exception:
                pass
        return base

    def get_default_system_prompt(self) -> str:
        return (
            "You are TOM (Technical Operations Manager), an elite autonomous AI assistant running on the user's Windows laptop. "
            "You have FULL access to the following capabilities — these are REAL, not hypothetical:\n"
            "- VISION: You CAN analyze images. Users attach images via the attachment button and you see them using Gemma 4 vision.\n"
            "- CAMERA: You CAN capture photos from the webcam and analyze them.\n"
            "- SCREEN: You CAN read and analyze what is on the user's screen via OCR.\n"
            "- DOCUMENTS: You CAN create professional Word (.docx), Excel (.xlsx), PowerPoint (.pptx), and PDF files.\n"
            "- EMAIL: You CAN read inbox, draft, and send emails via Gmail OAuth2.\n"
            "- WHATSAPP: You CAN send WhatsApp messages.\n"
            "- APPS: You CAN open any installed application on the laptop.\n"
            "- CODE: You CAN write and create code files in any language.\n"
            "- WEB: You CAN search the internet and analyze web pages.\n"
            "- FILES: You CAN read, write, and analyze any file (PDF, Excel, code, CSV, images, audio, video).\n"
            "- VOICE: You CAN listen and speak using voice conversation mode.\n"
            "- AGENTS: You CAN build and run sub-agents for specialized tasks.\n\n"
            "IMPORTANT: When a user asks if you can do something, say YES confidently and explain how. "
            "Never say 'I cannot analyze images' or 'I don't have access to' — you DO have access. "
            "If asked about image analysis, tell them to attach an image using the attachment button.\n\n"
            "Personality: warm, direct, professional. Talk like a capable friend. "
            "For casual chat keep it short. For tasks, deliver professional-grade results."
        )

    @staticmethod
    def _escape_braces(payload: Dict[str, Any]) -> Dict[str, Any]:
        escaped = {}
        for k, v in payload.items():
            if isinstance(v, str):
                escaped[k] = v.replace("{", "{{").replace("}", "}}")
            else:
                escaped[k] = v
        return escaped

    @staticmethod
    def _safe_prompt(messages: list) -> ChatPromptTemplate:
        safe_msgs = []
        for role, content in messages:
            if role == "system":
                content = content.replace("{", "{{").replace("}", "}}")
            safe_msgs.append((role, content))
        return ChatPromptTemplate.from_messages(safe_msgs)

    async def _invoke_llm(self, chain, payload: Dict[str, Any], task_name: str, llm=None):
        model = llm or self.llm
        safe_print(f"[LLM] Generating {task_name} response...")
        try:
            return await asyncio.wait_for(
                (chain | model).ainvoke(payload),
                timeout=self.model_timeout_seconds,
            )
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"Model timeout while running '{task_name}' after {self.model_timeout_seconds}s."
            )

    # ── NLP-BASED UNDERSTANDING ─────────────────────────────────────────

    async def understand_command(self, command: str) -> Dict[str, Any]:
        """Deep NLP understanding of any command. Returns structured intent."""
        parsed = await self.nlp_parser.parse_with_llm(command)
        safe_print(f"\n[NLP] Intent: {parsed.get('intent')}")
        safe_print(f"[NLP] App: {parsed.get('app_name')}")
        safe_print(f"[NLP] Person: {parsed.get('person_name')}")
        safe_print(f"[NLP] Subject: {parsed.get('subject')}")
        nlp_data = parsed.get("nlp_analysis", {})
        if nlp_data:
            safe_print(f"[NLP] Action: {nlp_data.get('action')} | Target: {nlp_data.get('target')} | Topic: {nlp_data.get('topic')}")
            safe_print(f"[NLP] Sentence: {nlp_data.get('sentence_type')} | Entities: {nlp_data.get('entities', [])}")
        safe_print(f"[NLP] Context: {parsed.get('context_summary')}")
        return parsed

    # ── MAIN TASK EXECUTION ─────────────────────────────────────────────

    async def execute_task(self, command: str) -> Dict[str, Any]:
        safe_print(f"\nTOM RECEIVED: {command}\n")
        self.chat_memory.append("user", command)
        task_started_at = time.perf_counter()
        telemetry_skill_route = None
        self._recalled = []
        recall_task = None
        parsed: Dict[str, Any] = {}

        # Safety check
        safety_check = await self.safety.is_action_safe(command)
        if not safety_check["safe"]:
            return safety_check
        # Remember whether the user already approved at this gate so the
        # router's sensitive gate below doesn't prompt a second time.
        already_approved = False
        if safety_check.get("requires_approval") and self._email_send_defers_approval(command):
            # Approval happens once, on the actual message, in execute_email_send_flow.
            already_approved = True
        elif safety_check.get("requires_approval") and self._is_delete_request(command.lower()):
            # Deletes show their own rich warning (what exactly will be removed)
            # in execute_delete; skip the generic gate to avoid a double prompt.
            already_approved = True
        elif safety_check.get("requires_approval") and self._is_acquire_tool_request(command.lower()):
            # Tool acquisition (install/clone) asks for its own approval in
            # execute_tool_acquisition; skip the generic gate.
            already_approved = True
        elif safety_check.get("requires_approval"):
            approved = await asyncio.to_thread(
                self.approval_manager.request_approval,
                ApprovalRequest(
                    action=safety_check["action_name"],
                    summary=safety_check["message"],
                    details={},
                    risk_level="high",
                ),
            )
            if not approved:
                return {"status": "cancelled", "message": "Action cancelled by user."}
            already_approved = True

        # Store user message in RAG memory (non-blocking)
        if self.rag and self.rag.available:
            try:
                asyncio.get_running_loop().run_in_executor(
                    None, self.rag.store_conversation, "user", command)
            except Exception as _bg:
                self.safety.log_action("WARN", target="rag", status="FAILURE",
                                       message=f"RAG store(user) failed: {_bg}")

        try:
            # ── Meta commands (instant, deterministic — no LLM round-trip) ──
            _meta = command.lower().strip().rstrip("?!. ")
            if _meta in ("what can you do", "capabilities", "list capabilities",
                         "show capabilities", "what are your capabilities",
                         "what all can you do"):
                return self._capabilities_response()
            if _meta in ("system status", "health", "health check", "status",
                         "subsystem status", "system health"):
                return self._health_response()
            if _meta in ("system capability report", "capability health",
                         "capability report", "full capability report"):
                try:
                    from tools.capability_health import format_capability_health
                    return {"status": "success", "response_type": "capability_health",
                            "message": format_capability_health()}
                except Exception as _cap_err:
                    return {"status": "error",
                            "message": f"Capability health unavailable: {_cap_err}"}
            if _meta in ("skill usage", "skill telemetry", "skill usage report",
                         "skill report"):
                if getattr(self, "skill_telemetry", None):
                    return {"status": "success", "response_type": "skill_usage",
                            "message": self.skill_telemetry.format_summary()}
                return {"status": "error", "message": "Skill telemetry is unavailable."}
            if _meta in ("show logs", "logs", "show recent logs", "view logs",
                         "recent activity log"):
                return self._logs_response()
            if _meta in ("voice check", "test voice", "voice test", "check voice",
                         "diagnose voice", "voice diagnostics"):
                try:
                    from tools.voice_tools import VoiceTools
                    vt = VoiceTools()
                    return {"status": "success", "response_type": "voice_check",
                            "message": vt.self_test_text()}
                except Exception as _vt_err:
                    return {"status": "error",
                            "message": f"Voice stack failed to load: {_vt_err}. "
                                       f"Fix: pip install SpeechRecognition pyttsx3 pyaudio edge-tts pygame"}

            # ── Long-term memory: meta commands, preferences, recall ──────
            mem_result = await self._memory_command(command)
            if mem_result is not None:
                return mem_result
            if memory_rules.is_preference_statement(command):
                retained_before = self.memory.stats["retained"]
                self._retain_preference(command)
                if memory_rules.is_pure_preference(command):
                    saved = await self._memory_write_settled(retained_before)
                    return self._acknowledge_preference(command, saved=saved)
            if self.memory.available:
                # Runs while the request is being parsed — no added latency.
                recall_task = asyncio.create_task(self.memory.arecall(command, limit=8))

            safe_print("[STEP 1] Understanding your request...")
            try:
                parsed = await self.understand_command(command)
            finally:
                if recall_task is not None:
                    self._recalled = await recall_task
                    if self._recalled:
                        safe_print(f"[MEMORY] Recalled {len(self._recalled)} relevant memories.")
            command_lower = command.lower().strip()
            intent = parsed.get("intent", "")
            safe_print(f"[STEP 2] Detected intent: {intent}")
            engine_key = self.engine_router.detect(command_lower) if self.engine_router else None
            if engine_key is None and self.engine_router and intent == "file_operation":
                # The keyword router missed it but the sentence was understood as a file request
                # (e.g. "arrange the pdfs on my desktop into a folder called Bills").
                engine_key = "fileops"

            # ── Feedback handling ─────────────────────────────────────────
            # User says "that was wrong", "too long", "more detail", etc.
            if intent == "give_feedback" or any(
                kw in command_lower for kw in (
                    "that was wrong", "incorrect answer", "bad response",
                    "too long", "too short", "more detail", "be more concise",
                    "be more casual", "be more professional", "use bullet",
                    "no bullets", "in prose", "bad job", "not helpful",
                )
            ):
                if self.evolution:
                    msg = self.evolution.learn_from_feedback(
                        command, self._last_command, self._last_response
                    )
                else:
                    msg = "Thanks for the feedback! I'll keep improving."
                if not memory_rules.is_preference_statement(command):
                    self._retain_preference(command)
                return {"status": "success", "message": msg, "response_type": "feedback"}

            # ── MCP connector calls ───────────────────────────────────────
            # e.g. "check my github repos", "list slack channels",
            #      "post to slack #general: hello", "get weather in London"
            chat_request = self.nlp_parser.extract_chat_request(command)
            if self._is_delete_request(command_lower):
                # File/folder deletion — always warns and asks before removing.
                result = await self.execute_delete(command, parsed)

            elif self._is_learn_request(command_lower):
                # "learn about X" — research the web and grow the knowledge base.
                result = await self.acquire_knowledge(self._learn_topic(command))

            elif self._is_acquire_tool_request(command_lower):
                # "install X" / "get X from github" / "build a tool that …"
                result = await self.execute_tool_acquisition(command, parsed)

            elif chat_request:
                # "message Ravi on telegram", "post to slack #dev: ..." - real send, approved on the exact text.
                result = await self._send_chat_app_message(chat_request)

            elif engine_key == "fileops":
                # A file command is never delegated to free-form chat. The
                # engine builds a concrete plan and asks approval before moving
                # anything, so a model cannot merely claim it completed work.
                result = await self.engine_router.execute(command, key=engine_key)
                if result.get("status") == "unhandled":
                    result = {"status": "error", "response_type": "engine_fileops",
                              "message": "I recognized a file task but could not build a safe plan."}

            elif self._is_mcp_request(command_lower, intent):
                result = await self._handle_mcp_request(command, command_lower, parsed)
                # fall through only if mcp returned unhandled
                if result.get("status") != "unhandled":
                    pass  # use result directly
                else:
                    result = await self.generate_chat_response(command)

            # ── Route through handlers
            elif self._is_email_agent_control_request(command_lower):
                result = await self.manage_email_agent(command)

            elif self._is_instagram_agent_control_request(command_lower):
                result = await self.manage_instagram_agent(command)

            else:
                route = self.command_router.route(command)
                handler = route.handler
                skill_route = self.skill_manager.route_task(command)
                telemetry_skill_route = skill_route if skill_route.matched else None

                # Honor needs_approval on ANY category (e.g. whatsapp_message is
                # category "communication" but still flagged). Skip when the
                # safety gate above already collected approval for this command.
                if (route.needs_approval and not already_approved
                        and not self._email_send_defers_approval(command)):
                    approval_summary = f"Approve: {command}"
                    approval_details = dict(route.metadata)
                    if route.intent == "whatsapp_message":
                        # Show the parsed recipient and text, not just the raw command,
                        # so a mis-parse is caught before anything is sent.
                        wa = self.nlp_parser._extract_whatsapp_details(command)
                        if wa:
                            approval_summary = (f"Send WhatsApp message to {wa['contact']}: "
                                                f"\"{wa['message'][:300]}\"")
                            approval_details.update({"to": wa["contact"], "message": wa["message"]})
                    approved = await asyncio.to_thread(
                        self.approval_manager.request_approval,
                        ApprovalRequest(
                            action=route.intent, summary=approval_summary,
                            details=approval_details, risk_level="high",
                        ),
                    )
                    if not approved:
                        return {"status": "cancelled", "message": "Cancelled by user."}

                # Build agent
                if self._is_build_agent_request(command_lower):
                    result = await self._handle_build_agent(command, parsed)

                # Explicit plugin/agent execution
                elif self._should_use_plugin_route(command_lower):
                    result = await self._handle_plugin_routed_task(command)

                # Approved sensitive action (router handler "approval_gate").
                # The approval prompt already ran above; dispatch to a real
                # executor where one exists, otherwise say so explicitly instead
                # of silently falling through to a generic chat reply.
                elif handler == "approval_gate":
                    if route.intent == "send_email":
                        result = await self.execute_email_send_flow(command, parsed)
                    else:
                        result = {
                            "status": "unsupported",
                            "message": (
                                f"Approved, but '{route.intent}' is not wired to an executor, "
                                "so TOM will not perform it silently. Destructive actions such as "
                                "delete/remove/share/publish/post are intentionally not auto-executed."
                            ),
                        }

                # Instagram
                elif route.handler == "execute_instagram_workflow":
                    result = await self.execute_instagram_workflow(command)

                # Email inbox
                elif handler == "execute_email_inbox_workflow":
                    result = await self.execute_email_inbox_workflow(command)

                # Email send
                elif handler == "execute_email_send":
                    result = await self.execute_email_send_flow(command, parsed)

                # Email draft / write (router returns this for "write email", "draft email", "email to", "mail to")
                elif handler == "execute_email_task":
                    result = await self._handle_email_write(command, parsed)

                # File operations (router returns this for "write code", "create file", "read file", "show me")
                elif handler == "execute_file_or_read":
                    if any(t in command_lower for t in ("read file", "show me", "show file", "open file", "cat file")):
                        result = await self.execute_read_file_command(command)
                    else:
                        result = await self.execute_file_command(command, parsed)

                # Agent daemon (start/stop/status of email or instagram agent)
                elif handler == "manage_agent_daemon":
                    if "instagram" in command_lower:
                        result = await self.manage_instagram_agent(command)
                    else:
                        result = await self.manage_email_agent(command)

                # Website creation (router returns this for "create website", "make website")
                elif handler == "execute_website_creation":
                    result = await self.execute_website_creation(command)

                # Screen read
                elif handler == "execute_screen_read":
                    result = await self.execute_screen_read(command)

                # WhatsApp
                elif handler == "execute_open_whatsapp":
                    result = await self.whatsapp_tools.open_whatsapp()

                elif handler == "execute_whatsapp_task":
                    result = await self._execute_whatsapp(command, parsed)

                # Data analysis
                elif handler == "execute_data_analysis":
                    result = await self._execute_data_analysis(command, parsed)

                # Presentation
                elif handler == "execute_presentation_task":
                    result = await self._execute_presentation(command, parsed)

                # Document writing
                elif handler == "execute_document_writing":
                    result = await self._execute_document_writing(command, parsed)

                # Excel creation (router handler — no longer relies solely on parser intent)
                elif handler == "execute_excel_task":
                    result = await self._create_excel(command, parsed)

                # Word doc creation (router handler — no longer relies solely on parser intent)
                elif handler == "execute_word_task":
                    result = await self._create_word_doc(command, parsed)

                # Code project
                elif handler == "execute_code_project":
                    result = await self._execute_code_project(command, parsed)

                # Web search (fast-path from router)
                elif handler == "execute_web_search":
                    result = await self._web_search(command, parsed)

                # Explanation / understanding questions
                elif handler == "explain_how_it_works":
                    result = await self._explain_how_it_works(command, parsed)

                # Email drafting the router didn't claim ("email Ravi about the
                # budget") — must win over skill/topic routes keyed on "budget" etc.
                elif parsed.get("intent") == "write_email" and handler == "generate_chat_response":
                    result = await self._handle_email_write(command, parsed)

                # Specialized engines (ML/IoT/VLSI/Hardware/Blender/GameDev/
                # News/Env/Auto-update/Autonomous/Multi-agent) — previously
                # GUI-only; now natural-language reachable. Conservative
                # detection; unmatched commands fall through unchanged.
                elif self.engine_router and self.engine_router.detect(command_lower):
                    result = await self.engine_router.execute(command)
                    if result.get("status") == "unhandled":
                        result = await self.generate_chat_response(command)

                # Skill-guided tasks not covered by a concrete tool route.
                elif self._should_use_skill_route(route, skill_route, command_lower):
                    result = await self._handle_skill_routed_task(command, skill_route)

                # Open application
                elif parsed.get("intent") == "open_app" or handler == "execute_open_command":
                    result = await self.execute_open_command(command, route=route, parsed=parsed)

                # Word doc creation
                elif parsed.get("intent") == "create_word_doc":
                    result = await self._create_word_doc(command, parsed)

                # Excel creation
                elif parsed.get("intent") == "create_excel":
                    result = await self._create_excel(command, parsed)

                # Presentation creation
                elif parsed.get("intent") == "create_presentation":
                    result = await self._execute_presentation(command, parsed)

                # PDF creation
                elif parsed.get("intent") == "create_pdf":
                    result = await self._create_pdf(command, parsed)

                # Email writing
                elif parsed.get("intent") in ("write_email",):
                    result = await self._handle_email_write(command, parsed)

                # File creation
                elif parsed.get("intent") == "create_file":
                    result = await self.execute_file_command(command, parsed)

                # File reading
                elif parsed.get("intent") == "read_file":
                    result = await self.execute_read_file_command(command)

                # Web search
                elif parsed.get("intent") == "web_search":
                    result = await self._web_search(command, parsed)

                # Website creation
                elif "create website" in command_lower or "make website" in command_lower:
                    result = await self.execute_website_creation(command)

                # File / image analysis
                elif parsed.get("intent") == "analyze_file":
                    fp = parsed.get("file_name") or parsed.get("data_source") or ""
                    if fp and not os.path.isabs(fp):
                        fp = project_path_str(fp)
                    result = await self.analyze_file(fp, command) if fp else {
                        "status": "error", "message": "Please specify a file path to analyze."}

                # Code fix / debug
                elif any(x in command_lower for x in ("fix code", "debug", "fix my code", "repair code")):
                    result = await self.execute_code_help(command)

                # General chat OR universal task attempt (A1):
                # clearly task-like commands with no concrete handler get
                # ATTEMPTED via the autonomous plan→execute→verify loop
                # instead of deflected to a chat reply.
                # Kill-switch: TOM_UNIVERSAL_FALLBACK=0
                else:
                    try:
                        from tools.task_heuristics import should_attempt_universal
                        _go_universal = (self.engine_router is not None and
                                         should_attempt_universal(intent, command))
                    except Exception:
                        _go_universal = False
                    if _go_universal:
                        result = await self._universal_task_attempt(command, parsed)
                    else:
                        result = await self.generate_chat_response(command)

            # Long-term memory: show which remembered preferences shaped this
            # answer, then store the outcome so future attempts learn from it.
            if not result.get("memories_used") and result.get("status") not in ("error", "cancelled"):
                shown = self._relevant_preferences(command)
                if shown:
                    result["memories_used"] = shown
                    result["message"] = ("Remembering from earlier:\n"
                                         + "\n".join(f"  • {t}" for t in shown)
                                         + "\n\n" + str(result.get("message", "")))
            try:
                self._retain_outcome(command, result, parsed.get("intent", ""))
            except Exception as _mem_err:
                self.safety.log_action("WARN", target="hindsight", status="FAILURE",
                                       message=f"retain outcome failed: {_mem_err}")

            # Log completion with the REAL outcome (was: unconditional SUCCESS,
            # which made the audit log claim success for errored tasks).
            _outcome_ok = result.get("status") not in ("error", "cancelled", "unsupported")
            if telemetry_skill_route and getattr(self, "skill_telemetry", None):
                try:
                    failure_reason = "" if _outcome_ok else str(result.get("message", result.get("status", "")))
                    self.skill_telemetry.record_route(
                        skill_name=telemetry_skill_route.skill_name,
                        execution_mode=telemetry_skill_route.execution_mode,
                        status="success" if _outcome_ok else "failure",
                        elapsed_seconds=time.perf_counter() - task_started_at,
                        failure_reason=failure_reason,
                        command=command,
                    )
                except Exception as _tel_err:
                    self.safety.log_action("WARN", target="skill_telemetry", status="FAILURE",
                                           message=f"skill telemetry failed: {_tel_err}")
            self.safety.log_action("COMPLETED", target=command,
                                   status="SUCCESS" if _outcome_ok else "FAILURE",
                                   message=f"Completed ({result.get('status', 'unknown')}): {command[:100]}...")

            # Track for feedback
            message_text = str(result.get("message", ""))
            self._last_command = command
            self._last_response = message_text
            self._last_result = result

            # Learning
            try:
                exp = self.learner.log_experience(
                    command, "success" if _outcome_ok else "error", {"result": result})
                self._last_exp_id = exp.get("id")
                result["experience_id"] = exp.get("id")
            except Exception as _bg:
                self.safety.log_action("WARN", target="learning", status="FAILURE",
                                       message=f"learn log_experience failed: {_bg}")

            # Memory (chat)
            try:
                if message_text:
                    self.chat_memory.append("assistant", message_text)
            except Exception as _bg:
                self.safety.log_action("WARN", target="chat_memory", status="FAILURE",
                                       message=f"chat_memory append failed: {_bg}")

            # RAG — store assistant response (non-blocking)
            if self.rag and self.rag.available and message_text:
                try:
                    asyncio.get_running_loop().run_in_executor(
                        None, self.rag.store_conversation, "assistant", message_text,
                        {"command": command[:120]})
                except Exception as _bg:
                    self.safety.log_action("WARN", target="rag", status="FAILURE",
                                           message=f"RAG store(assistant) failed: {_bg}")

            # Evolution — record success
            if self.evolution:
                try:
                    handler_name = parsed.get("intent", "general")
                    self.evolution.record_success(
                        command=command,
                        intent=handler_name,
                        approach=handler_name,
                        response_snippet=message_text,
                    )
                except Exception as _bg:
                    self.safety.log_action("WARN", target="evolution", status="FAILURE",
                                           message=f"evolution record_success failed: {_bg}")

            return result

        except Exception as e:
            error_msg = f"[ERROR] Task failed: {str(e)}"
            hint = _llm_unreachable_hint(e)
            if hint:
                error_msg += f"\n{hint}"
            self.safety.log_action("ERROR", target=command, status="FAILURE", message=str(e))
            if telemetry_skill_route and getattr(self, "skill_telemetry", None):
                try:
                    self.skill_telemetry.record_route(
                        skill_name=telemetry_skill_route.skill_name,
                        execution_mode=telemetry_skill_route.execution_mode,
                        status="failure",
                        elapsed_seconds=time.perf_counter() - task_started_at,
                        failure_reason=str(e),
                        command=command,
                    )
                except Exception:
                    pass
            safe_print(f"\n{error_msg}\n")
            if recall_task is not None and not recall_task.done():
                recall_task.cancel()
            try:
                self._retain_outcome(command, {"status": "error", "message": str(e)}, "")
            except Exception:
                pass
            try:
                self.learner.log_experience(command, "error", {"error": str(e)})
            except Exception:
                pass
            try:
                self.chat_memory.append("assistant", error_msg)
            except Exception:
                pass
            # RAG — store error response (non-blocking)
            if self.rag and self.rag.available:
                try:
                    asyncio.get_running_loop().run_in_executor(
                        None, self.rag.store_conversation, "assistant", error_msg,
                        {"command": command[:120], "error": "true"})
                except Exception as _bg:
                    self.safety.log_action("WARN", target="rag", status="FAILURE",
                                           message=f"RAG store(error) failed: {_bg}")
            # Evolution — record failure
            if self.evolution:
                try:
                    self.evolution.record_failure(
                        command=command, intent="unknown", approach="unknown", error=str(e)
                    )
                except Exception:
                    pass
            return {"status": "error", "message": error_msg}

    async def _send_chat_app_message(self, request: Dict[str, str]) -> Dict[str, Any]:
        """Slack / Discord / Telegram message: approve the exact target and text, send, report the service's answer."""
        app, target, text = request["app"], request["target"], request["message"]
        problem = self.chat_apps.missing_setup(app)
        if problem:
            opened = await self.os_tools.open_application(app)
            opened_note = (f"I opened {app.title()}, but " if opened.get("status") == "success"
                           else f"I could not open {app.title()}, and ")
            return {"status": "unsupported", "response_type": "chat_app_unsupported", "open_result": opened,
                    "message": f"{opened_note}nothing was sent. To let me send messages there: {problem}"}
        approved = await asyncio.to_thread(
            self.approval_manager.request_approval,
            ApprovalRequest(action="chat_send",
                            summary=f"Send {app.title()} message to {target}: \"{text[:300]}\"",
                            details={"app": app, "to": target, "message": text}, risk_level="high"))
        if not approved:
            return {"status": "cancelled", "message": f"Cancelled. Nothing was sent to {target} on {app.title()}."}
        result = await self.chat_apps.send(app, target, text)
        self.safety.log_action("CHAT_SEND", target=f"{app}:{target}",
                               status="SUCCESS" if result.get("status") == "success" else "FAILURE",
                               message=result.get("message", "")[:120])
        result.setdefault("response_type", "chat_app_send")
        return result

    def _email_send_defers_approval(self, command: str) -> bool:
        """True when 'send an email ...' will reach execute_email_send_flow untouched.

        That flow asks the user to approve the real recipient/subject/body, so the
        generic command-level prompt would be a second, less informative "are you
        sure". Any other path (MCP, engines, plugins, agent control) keeps the
        command-level prompt because nothing later asks.
        """
        lower = command.lower().strip()
        try:
            if self.command_router.route(command).handler != "execute_email_send":
                return False
            if self.engine_router and self.engine_router.detect(lower):
                return False
            return not (self._is_mcp_request(lower, "")
                        or self._is_email_agent_control_request(lower)
                        or self._is_instagram_agent_control_request(lower)
                        or self._is_build_agent_request(lower)
                        or self._should_use_plugin_route(lower))
        except Exception:
            return False

    async def _memory_write_settled(self, retained_before: int) -> bool:
        """Wait (briefly) for the just-issued retain; True only if Hindsight really accepted it."""
        if not self.memory.available:
            return False
        await asyncio.to_thread(self.memory.flush, 8.0)
        return self.memory.stats["retained"] > retained_before

    def _acknowledge_preference(self, command: str, saved: Optional[bool] = None) -> Dict[str, Any]:
        """Reply to a pure preference/correction — no LLM round-trip needed.

        `saved` is what actually happened: True = Hindsight confirmed it, False = it is only kept
        locally for now. The old text said "Saved to long-term memory" whenever memory was merely
        configured, even while every save was failing.
        """
        category = memory_rules.categorize(command)
        lines = ["Got it — I'll remember that."]
        if category == "file_organization":
            rules = memory_rules.parse_folder_rules([command])
            if rules:
                lines.append("Rules I'll apply next time I organize a folder:")
                lines += [f"  • {r.describe()}" for r in rules]
        if saved is None:
            saved = self.memory.available            # legacy callers that did not check
        if saved:
            lines.append("(Saved to long-term memory — it carries over to future sessions.)")
        elif self.memory.available:
            reason = self.memory.last_error or "Hindsight has not answered yet"
            waiting = self.memory.pending_count()
            lines.append(f"(NOT saved to Hindsight yet — {reason}. It is kept on this computer"
                         f"{f' ({waiting} waiting)' if waiting else ''} and I will retry automatically.)")
        else:
            lines.append(f"(Queued locally: {self.memory.status_line()})")
        message = "\n".join(lines)
        try:
            self.chat_memory.append("assistant", message)
        except Exception:
            pass
        self._last_command, self._last_response = command, message
        return {"status": "success", "response_type": "preference_saved", "message": message,
                "memories_used": [command]}

    # ── BUILD AGENT ─────────────────────────────────────────────────────

    def _is_build_agent_request(self, command_lower: str) -> bool:
        patterns = ["build agent", "create agent", "make agent", "agent that", "build an agent"]
        return any(p in command_lower for p in patterns)

    async def _handle_build_agent(self, command: str, parsed: Dict) -> Dict[str, Any]:
        agent_name = self._infer_agent_name(command)
        capabilities = self._infer_capabilities(command)
        result = await self.build_agent(agent_name, capabilities)
        result["agent_name"] = agent_name
        result["message"] = f"Built scaffold agent '{agent_name}' with capabilities: {', '.join(capabilities)}."
        return result

    # ── MCP ROUTING ──────────────────────────────────────────────────────

    # Connector triggers. Deliberately specific: everyday words ("issue", "commit", "forecast", "rain")
    # used to send ordinary sentences to GitHub or the weather service. Gmail is not here: mail is
    # handled by the email workflows (draft / send / inbox), never by a connector.
    _MCP_KEYWORDS = {
        "github":    ["github", "repository", "repositories", "repos", "pull request", "code search"],
        "slack":     ["slack", "post to slack", "slack channel", "slack message"],
        "notion":    ["notion", "notion page", "notion database"],
        "whatsapp":  ["whatsapp business"],  # regular whatsapp handled by whatsapp_tools
        "instagram": ["instagram api", "instagram insights", "instagram media"],
        "calendar":  ["calendar", "my schedule", "upcoming events", "create event", "add to calendar"],
        "weather":   ["weather", "temperature in", "temperature outside", "will it rain", "going to rain",
                      "is it raining", "weather forecast"],
        "websearch": ["search the web", "look up online", "google ", "find information about"],
    }

    _without_addresses = staticmethod(without_addresses)

    def _is_mcp_request(self, command_lower: str, intent: str) -> bool:
        if intent in ("mcp_call", "mcp_status", "mcp_list"):
            return True
        command_lower = self._without_addresses(command_lower)
        if "mcp" in command_lower and any(k in command_lower for k in ("list", "status", "connect", "tools")):
            return True
        for kws in self._MCP_KEYWORDS.values():
            if any(self._mcp_keyword_matches(command_lower, kw) for kw in kws):
                return True
        # "commit" / "issue" are only GitHub when an owner/repo is named.
        return bool(re.search(r"\b(?:commits?|issues?)\b", command_lower)
                    and re.search(r"\b[\w.-]+/[\w.-]+\b", command_lower))

    @staticmethod
    def _mcp_keyword_matches(command_lower: str, keyword: str) -> bool:
        keyword = keyword.lower().strip()
        if not keyword:
            return False
        if len(keyword) <= 3 or re.fullmatch(r"[a-z0-9 ]+", keyword):
            return re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", command_lower) is not None
        return keyword in command_lower

    async def _handle_mcp_request(self, command: str, command_lower: str, parsed: Dict) -> Dict[str, Any]:
        """Route to the correct MCP connector based on command keywords."""
        if not self.mcp:
            return {"status": "error", "message": "MCP system not initialised."}

        # Status / list request
        if any(k in command_lower for k in ("mcp status", "mcp list", "list connectors",
                                             "what connectors", "which tools", "mcp tools")):
            connectors = self.mcp.list_connectors()
            lines = ["**MCP Connector Status:**\n"]
            for c in connectors:
                status = "✓ connected" if c["connected"] else "○ not connected"
                lines.append(f"• **{c['name']}** — {c['description']} [{status}]")
                lines.append(f"  Tools: {', '.join(c['tools'][:5])}")
            return {"status": "success", "message": "\n".join(lines)}

        # Map keywords → connector + tool (on the request without email addresses / URLs)
        matchable = self._without_addresses(command_lower)
        for connector_name, kws in self._MCP_KEYWORDS.items():
            if any(self._mcp_keyword_matches(matchable, kw) for kw in kws):
                return await self._dispatch_mcp(connector_name, command, command_lower, parsed)
        if re.search(r"\b(?:commits?|issues?)\b", matchable) and re.search(r"\b[\w.-]+/[\w.-]+\b", matchable):
            return await self._dispatch_mcp("github", command, command_lower, parsed)

        return {"status": "unhandled", "message": ""}

    async def _dispatch_mcp(self, connector: str, command: str,
                             command_lower: str, parsed: Dict) -> Dict[str, Any]:
        """Call the right tool on the right connector and format the response."""
        try:
            if connector == "github":
                return await self._mcp_github(command, command_lower, parsed)
            elif connector == "weather":
                city = parsed.get("context_summary") or "London"
                m = re.search(r"(?:in|for|at)\s+([A-Z][a-zA-Z\s]+?)(?:\?|$|,)", command)
                if m:
                    city = m.group(1).strip()
                res = await self.mcp.call("weather", "get_current_weather", {"city": city})
                d = res.get("data", {}) or {}
                return {"status": res["status"],
                        "message": f"**{d.get('city','')}: {d.get('temperature_c')}°C** — {d.get('condition','')}. "
                                   f"Humidity {d.get('humidity_pct')}%, Wind {d.get('wind_kph')} km/h"}
            elif connector == "websearch":
                q = command.lower().replace("search the web for ", "").replace("look up online ", "").replace("google ", "")
                res = await self.mcp.call("websearch", "search", {"query": q})
                d   = res.get("data", {}) or {}
                abstract = d.get("abstract", "")
                related  = d.get("related", [])[:4]
                msg = abstract if abstract else "No instant answer found."
                if related:
                    msg += "\n\nRelated:\n" + "\n".join(f"• {r['title']}" for r in related if r.get("title"))
                return {"status": "success", "message": msg}
            elif connector == "slack":
                return await self._mcp_slack(command, command_lower, parsed)
            elif connector == "calendar":
                return await self._mcp_calendar(command, command_lower, parsed)
            else:
                # No natural-language actions are wired for this connector. It used to call a tool
                # named "<connector>_info" that no connector has, always answering "Unknown tool".
                info = next((c for c in self.mcp.list_connectors() if c["name"] == connector), None)
                if info is None:
                    return {"status": "unsupported", "message": f"There is no '{connector}' connector."}
                state = "connected" if info["connected"] else "not connected (add its credentials to .env)"
                return {"status": "info", "response_type": "mcp_info",
                        "message": (f"{connector.title()} — {info['description']}. It is {state}. "
                                    f"TOM can't act on it from plain language yet.")}
        except Exception as e:
            return {"status": "error", "message": f"MCP {connector} error: {e}"}

    async def _mcp_github(self, command: str, command_lower: str, parsed: Dict) -> Dict[str, Any]:
        if "issue" in command_lower and "create" in command_lower:
            m = re.search(r"in\s+([a-zA-Z0-9_.\-]+)/([a-zA-Z0-9_.\-]+)", command)
            owner, repo = (m.group(1), m.group(2)) if m else ("", "")
            title_m = re.search(r'(?:titled?|called?|named?)\s+"?(.+?)"?\s*(?:in|$)', command, re.I)
            title = title_m.group(1) if title_m else parsed.get("subject", "New issue")
            res = await self.mcp.call("github", "create_issue", {"owner": owner, "repo": repo, "title": title})
            return {"status": res["status"], "message": res.get("message", "")}
        elif "repo" in command_lower:
            m = re.search(r"(?:of|for|user)\s+([a-zA-Z0-9_.\-]+)", command_lower)
            username = m.group(1) if m else ""
            res = await self.mcp.call("github", "list_repos", {"username": username})
            repos = res.get("data", []) or []
            lines = [f"**GitHub Repos{' for ' + username if username else ''}:**\n"]
            for r in repos[:10]:
                lines.append(f"• **{r['name']}** ⭐{r['stars']} [{r.get('lang','?')}] — {r.get('description','')[:60]}")
            return {"status": "success", "message": "\n".join(lines)}
        elif "commit" in command_lower:
            m = re.search(r"([a-zA-Z0-9_.\-]+)/([a-zA-Z0-9_.\-]+)", command)
            if m:
                res = await self.mcp.call("github", "get_commits", {"owner": m.group(1), "repo": m.group(2)})
                commits = res.get("data", []) or []
                lines = [f"• `{c['sha']}` {c['message']} — {c['author']}" for c in commits[:8]]
                return {"status": "success", "message": "**Recent commits:**\n" + "\n".join(lines)}
        return {"status": "success", "message": "GitHub connected. Ask me to list repos, issues, or PRs."}

    async def _mcp_slack(self, command: str, command_lower: str, parsed: Dict) -> Dict[str, Any]:
        if "post" in command_lower or "send" in command_lower or "message" in command_lower:
            # Clear requests are handled earlier by _send_chat_app_message (with approval). Anything
            # unclear used to be posted to #general with the whole command as its text.
            return {"status": "error", "message": ("Tell me where and what to send, for example: "
                                                   "'post to slack #dev: deploy finished' or "
                                                   "'message Ravi on slack: lunch?'. Nothing was posted.")}
        elif "channel" in command_lower or "list" in command_lower:
            res = await self.mcp.call("slack", "list_channels", {})
            chs = res.get("data", []) or []
            lines = [f"• #{c['name']}" + (f" — {c['topic'][:50]}" if c.get("topic") else "") for c in chs[:15]]
            return {"status": "success", "message": "**Slack Channels:**\n" + "\n".join(lines)}
        return {"status": "success", "message": "Slack connected. Say 'post to slack #channel: message'."}

    async def _mcp_calendar(self, command: str, command_lower: str, parsed: Dict) -> Dict[str, Any]:
        if "create" in command_lower or "add" in command_lower or "schedule" in command_lower:
            title = parsed.get("subject") or "New Event"
            return {"status": "info",
                    "message": f"To create a calendar event, I need: title, start time, and end time. "
                               f"Try: 'Create calendar event: [title] on [date] from [start] to [end]'"}
        res = await self.mcp.call("calendar", "list_events", {"days": 7})
        events = res.get("data", []) or []
        if not events:
            return {"status": "success", "message": "No upcoming events in the next 7 days."}
        lines = [f"• {e.get('summary','(no title)')} — {e.get('start','')[:16]}" for e in events[:10]]
        return {"status": "success", "message": "**Upcoming Events:**\n" + "\n".join(lines)}

    def _infer_agent_name(self, command: str) -> str:
        m = re.search(r"(?:called|named)\s+([a-zA-Z0-9_\- ]+)", command, re.IGNORECASE)
        if m:
            return m.group(1).strip().replace(" ", "_").lower()[:40]
        c = command.lower()
        if "instagram" in c and ("email" in c or "mail" in c):
            return "instagram_news_to_email_agent"
        if "instagram" in c:
            return "instagram_agent"
        return "custom_task_agent"

    def _infer_capabilities(self, command: str) -> list:
        c = command.lower()
        caps = []
        if "instagram" in c:
            caps += ["open_instagram", "scroll_feed", "extract_posts"]
        if "tech" in c or "news" in c:
            caps += ["classify_tech_news", "summarize_news", "importance_rating"]
        if "email" in c or "mail" in c:
            caps += ["compose_email_digest", "send_email_message"]
        if not caps:
            caps = ["task_planning", "execution"]
        return list(dict.fromkeys(caps))  # deduplicate

    async def build_agent(self, name: str, capabilities: list) -> Dict[str, Any]:
        try:
            path = await asyncio.to_thread(create_agent_scaffold, name, capabilities)
            self.safety.log_action("AGENT_SCAFFOLD", target=name, status="SUCCESS", message=f"Scaffolded at {path}")
            return {"status": "success", "path": path, "message": f"Scaffolded agent at {path}"}
        except Exception as e:
            self.safety.log_action("AGENT_SCAFFOLD", target=name, status="FAILURE", message=str(e))
            return {"status": "error", "message": f"Failed to scaffold agent: {e}"}

    # ── AGENT CONTROLS ──────────────────────────────────────────────────

    def _is_email_agent_control_request(self, command_lower: str) -> bool:
        if "email agent" not in command_lower:
            return False
        return any(t in command_lower for t in ("start", "stop", "status", "summary", "resume", "pause", "restart"))

    def _is_instagram_agent_control_request(self, command_lower: str) -> bool:
        if "instagram agent" not in command_lower:
            return False
        return any(t in command_lower for t in ("start", "stop", "status", "summary", "resume", "pause", "restart"))

    async def manage_email_agent(self, command: str) -> Dict[str, Any]:
        command_lower = command.lower()
        if any(t in command_lower for t in ("stop", "pause")):
            result = await asyncio.to_thread(self.email_agent_controller.stop)
        elif any(t in command_lower for t in ("summary", "report", "activity")):
            result = await asyncio.to_thread(self.email_agent_controller.summary)
        elif any(t in command_lower for t in ("status", "check")):
            result = await asyncio.to_thread(self.email_agent_controller.status)
        else:
            result = await asyncio.to_thread(self.email_agent_controller.start)
        summary_lines = result.get("summary_lines", []) if isinstance(result, dict) else []
        attention = result.get("main_screen_items", []) if isinstance(result, dict) else []
        lines = [result.get("message", "Done.")]
        if summary_lines:
            lines.append("Latest email-agent summary:")
            lines.extend(f"- {l}" for l in summary_lines)
        return {"status": result.get("status", "success"), "message": "\n".join(lines),
                "email_agent_state": result, "main_screen_items": attention}

    async def manage_instagram_agent(self, command: str) -> Dict[str, Any]:
        command_lower = command.lower()
        if any(t in command_lower for t in ("stop", "pause")):
            result = await asyncio.to_thread(self.instagram_agent_controller.stop)
        elif any(t in command_lower for t in ("summary", "report", "activity")):
            result = await asyncio.to_thread(self.instagram_agent_controller.summary)
        elif any(t in command_lower for t in ("status", "check")):
            result = await asyncio.to_thread(self.instagram_agent_controller.status)
        else:
            result = await asyncio.to_thread(self.instagram_agent_controller.start)
        return {"status": result.get("status", "success"), "message": result.get("message", "Done."),
                "instagram_agent_state": result}

    # ── OPEN APPLICATION ───────────────────────────────────────────────

    async def execute_open_command(self, command: str, route=None, parsed=None) -> Dict[str, Any]:
        command_lower = command.lower()

        # Chrome with profile
        if "chrome" in command_lower and "profile" in command_lower:
            profile_query = getattr(route, "metadata", {}).get("profile_query", "") if route else ""
            if not profile_query:
                match = re.search(r"profile\s+(?:named|called|for|of)?\s*([a-zA-Z0-9_\- ]+)", command, re.IGNORECASE)
                if match:
                    profile_query = match.group(1).strip()
            return await asyncio.to_thread(self.chrome_profiles.launch_profile, profile_query)

        chat_app = self._unsupported_chat_app(command_lower)
        if chat_app:
            opened = await self.os_tools.open_application(chat_app)
            opened_note = (f"I opened {chat_app.title()}, but " if opened.get("status") == "success"
                           else f"I could not open {chat_app.title()}, and ")
            return {"status": "unsupported", "response_type": "chat_app_unsupported",
                    "message": (opened_note + "I can't type or send messages in it yet, so nothing was sent. "
                                "TOM can send messages through WhatsApp, and email."),
                    "open_result": opened}

        app_name = (parsed or {}).get("app_name") or self._extract_app_name(command)
        if not app_name:
            app_name = command_lower.replace("open ", "").replace("launch ", "").replace("start ", "").strip()
        if not app_name or app_name in ("a", "an", "the", "app", "application"):
            return {"status": "error", "message": "Could not determine which app to open."}

        safe_print(f"\n[SEARCH] Looking for '{app_name}'...")
        return await self.os_tools.open_application(app_name)

    _CHAT_APPS = ("telegram", "discord", "slack", "signal", "messenger", "skype", "viber", "teams", "sms")
    _CHAT_VERBS = re.compile(r"\b(?:text|message|msg|dm|say|tell|reply|chat with|send)\b")

    def _unsupported_chat_app(self, command_lower: str) -> str:
        """A 'message X on <app>' request for a chat app other than WhatsApp.

        Only WhatsApp (and email) can be driven end to end. For any other chat app
        the request used to fall into a plain 'open the app' and report success,
        silently dropping the message.
        """
        visible = self._without_addresses(command_lower)
        if not self._CHAT_VERBS.search(visible):
            return ""
        for app in self._CHAT_APPS:
            if re.search(rf"\b{app}\b", visible):
                return app
        return ""

    def _extract_app_name(self, command: str) -> str:
        c = command.lower().strip()
        for prefix in ("open ", "launch ", "start ", "run ", "execute "):
            if c.startswith(prefix):
                c = c[len(prefix):]
                break
        for suffix in (" app", " application", " program", " please", " for me", " now"):
            if c.endswith(suffix):
                c = c[:-len(suffix)]
        return c.strip()

    # ── PROFESSIONAL WORD DOCUMENT ──────────────────────────────────────

    async def _create_word_doc(self, command: str, parsed: Dict) -> Dict[str, Any]:
        memory_context = self._build_memory_context(command)
        subject = parsed.get("subject") or "Document"
        file_name = parsed.get("file_name") or f"{subject.lower().replace(' ', '_')}.docx"
        if not file_name.endswith(".docx"):
            file_name = file_name.rsplit(".", 1)[0] + ".docx"
        person = parsed.get("person_name") or ""
        safe_print(f"\n[WORD] Creating document about '{subject}'...")
        needs_internet = parsed.get("requires_data_from_internet", False)

        prompt = self._safe_prompt([
            ("system", compose_system_prompt(
                "You are TOM in Professional Writer mode. Generate a detailed document structure as JSON. "
                "Return ONLY valid JSON:\n"
                '{"title": "Document Title", "sections": [{"type": "heading|paragraph|bullet|table", '
                '"text": "...", "level": 1, "headers": ["Col1"], "rows": [["data"]]}]}',
                "TOM", include_ui=True)),
            ("user", "Conversation memory:\n{memory}\n\nCreate document content for:\n{command}\n\nSubject: {subject}\nPerson: {person}"),
        ])
        try:
            resp = await self._invoke_llm(prompt, {"memory": memory_context, "command": command,
                                                     "subject": subject, "person": person},
                                           "word_doc", self.code_llm)
            content = resp.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            structure = json.loads(content)
            result = await self.file_tools.create_word_document(
                file_name,
                title=structure.get("title", subject),
                author="TOM AI",
                content_sections=structure.get("sections", []),
            )
            if result["status"] == "success":
                self.file_tools.open_file(result["path"])
            return result
        except Exception as e:
            # Fallback: create simple document — but say so instead of
            # silently shipping a near-empty file as "success".
            self.safety.log_action("WORD_DOC", target=file_name, status="FAILURE",
                                   message=f"LLM content generation failed, used fallback: {e}")
            result = await self.file_tools.create_word_document(
                file_name, title=subject, author="TOM AI",
                content_sections=[{"type": "paragraph", "text": f"Document about {subject}. Generated by TOM."}],
            )
            if result["status"] == "success":
                self.file_tools.open_file(result["path"])
                result["message"] = (result.get("message", "") +
                                     f"\n⚠️ Content generation failed ({type(e).__name__}), so this is a "
                                     "basic placeholder document. Try rephrasing for full content.")
            return result

    # ── PROFESSIONAL EXCEL ──────────────────────────────────────────────

    async def _create_excel(self, command: str, parsed: Dict) -> Dict[str, Any]:
        memory_context = self._build_memory_context(command)
        subject = parsed.get("subject") or "Data"
        safe_print(f"\n[EXCEL] Creating spreadsheet about '{subject}'...")
        file_name = parsed.get("file_name") or f"{subject.lower().replace(' ', '_')}.xlsx"
        if not file_name.endswith(".xlsx"):
            file_name = file_name.rsplit(".", 1)[0] + ".xlsx"

        prompt = self._safe_prompt([
            ("system", "You are TOM in Excel mode. Generate Excel data as JSON. "
             "Return ONLY JSON:\n"
             '{"sheets": [{"name": "Sheet1", "headers": ["Col1","Col2"], '
             '"data": [["val1","val2"]], "chart_type": "bar|line|pie|none", "chart_title": "Chart Name"}]}'),
            ("user", "Conversation memory:\n{memory}\n\nCreate spreadsheet for:\n{command}\n\nSubject: {subject}"),
        ])
        try:
            resp = await self._invoke_llm(prompt, {"memory": memory_context, "command": command, "subject": subject},
                                           "excel", self.code_llm)
            content = resp.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            sheets = json.loads(content).get("sheets", [])
            result = await self.file_tools.create_excel_workbook(file_name, sheets=sheets)
            if result["status"] == "success":
                self.file_tools.open_file(result["path"])
            return result
        except Exception as e:
            self.safety.log_action("EXCEL", target=file_name, status="FAILURE",
                                   message=f"LLM content generation failed, used fallback: {e}")
            result = await self.file_tools.create_excel_workbook(file_name)
            if result["status"] == "success":
                self.file_tools.open_file(result["path"])
                result["message"] = (result.get("message", "") +
                                     f"\n⚠️ Content generation failed ({type(e).__name__}), so the workbook "
                                     "is empty. Try rephrasing for full content.")
            return result

    # ── PROFESSIONAL POWERPOINT ─────────────────────────────────────────

    async def _execute_presentation(self, command: str, parsed: Dict) -> Dict[str, Any]:
        memory_context = self._build_memory_context(command)
        subject = parsed.get("subject") or "Presentation"
        file_name = parsed.get("file_name") or f"{subject.lower().replace(' ', '_')}.pptx"
        if not file_name.endswith(".pptx"):
            file_name = file_name.rsplit(".", 1)[0] + ".pptx"
        search_topic = parsed.get("search_topic") or subject

        # Extract requested slide count from command
        slide_count_match = re.search(r'(\d+)\s*(?:slides?|pages?)', command, re.IGNORECASE)
        requested_slides = int(slide_count_match.group(1)) if slide_count_match else 8

        safe_print(f"\n[PPT] Creating {requested_slides}-slide presentation about '{subject}'...")

        internet_content = ""
        if parsed.get("requires_data_from_internet", False) or "internet" in command.lower():
            safe_print(f"[PPT] Researching '{search_topic}' for content...")
            internet_content = await self._research_topic(search_topic)

        prompt = self._safe_prompt([
            ("system",
                "You are a professional presentation designer. "
                "Generate a slide deck structure as JSON. "
                "Return ONLY valid JSON, no other text. "
                "Each slide must have 3-5 detailed bullet points with real, substantive information. "
                "JSON format: "
                '{"theme": {"style": "technology|business|nature|health|creative|education|finance|minimal"}, '
                '"title": "Title", "subtitle": "Subtitle", '
                '"slides": [{"title": "Slide Title", "content": ["Bullet 1","Bullet 2","Bullet 3"], '
                '"notes": "Speaker notes", '
                '"layout": "content|two_column|section_header|table|chart", '
                '"table_data": {"headers": ["Col1"], "rows": [["val"]]}, '
                '"chart_data": {"labels": ["A"], "values": [10], "type": "bar|line|pie", "title": "Title"}'
                '}]}'),
            ("user", "Memory:\n{memory}\n\nCommand: {command}\n\nSubject: {subject}\n\n"
             "Research:\n{internet_content}\n\n"
             "CRITICAL REQUIREMENT: Generate EXACTLY {slide_count} content slides. "
             "Not 3, not 5 — EXACTLY {slide_count} slides. "
             "Each slide must have 3-5 detailed, informative bullet points."),
        ])
        try:
            safe_print(f"[PPT] Generating slide content with LLM...")
            resp = await self._invoke_llm(prompt, {"memory": memory_context, "command": command,
                                                     "subject": subject, "internet_content": internet_content[:3000],
                                                     "slide_count": str(requested_slides)},
                                           "presentation", self.llm)
            content = resp.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            deck = json.loads(content)
            # An explicitly requested theme ("gaming theme", "floral", "bright
            # colours", "gradient") overrides whatever style the LLM guessed.
            theme = deck.get("theme")
            requested = self._extract_requested_theme(command)
            if requested:
                theme = {"style": requested}
            result = await self.file_tools.create_powerpoint(
                file_name,
                slides=deck.get("slides", []),
                title=deck.get("title", subject),
                theme=theme,
            )
            if result["status"] == "success":
                self.file_tools.open_file(result["path"])
            return result
        except Exception as e:
            self.safety.log_action("PRESENTATION", target=file_name, status="FAILURE",
                                   message=f"LLM content generation failed, used fallback: {e}")
            result = await self.file_tools.create_powerpoint(file_name, slides=[
                {"title": subject, "content": [f"Presentation about {subject}"], "layout": "title_only"},
            ], title=subject)
            if result["status"] == "success":
                self.file_tools.open_file(result["path"])
                result["message"] = (result.get("message", "") +
                                     f"\n⚠️ Content generation failed ({type(e).__name__}), so this deck has "
                                     "one placeholder slide. Try rephrasing for full content.")
            return result

    @staticmethod
    def _extract_requested_theme(command: str) -> str:
        """A presentation theme the user named explicitly, else "".

        Matches "<word> theme", "in a <word> theme/style", and common colour
        cues ("bright/vibrant/neon/pastel colours"). Returns the raw word; the
        document creator resolves it to a preset (with aliases).
        """
        cl = (command or "").lower()
        # Known style words win (reliable, unambiguous).
        m = re.search(r'\b(gaming|gamer|neon|cyberpunk|gradient|floral|flower|vibrant|bright|'
                      r'colou?rful|pastel|elegant|luxury|premium|royal|ocean|sunset|dark|minimal|'
                      r'technology|tech|business|corporate|nature|health|creative|education|finance)\b', cl)
        if m:
            return m.group(1).strip()
        # Otherwise the single word immediately before "theme"/"style".
        m = re.search(r'\b([a-z][a-z\-]{2,20})\s+(?:theme|style|palette|vibe)\b', cl)
        return m.group(1).strip() if m else ""

    # ── PROFESSIONAL PDF ────────────────────────────────────────────────

    async def _create_pdf(self, command: str, parsed: Dict) -> Dict[str, Any]:
        memory_context = self._build_memory_context(command)
        subject = parsed.get("subject") or "Report"
        file_name = parsed.get("file_name") or f"{subject.lower().replace(' ', '_')}.pdf"
        if not file_name.endswith(".pdf"):
            file_name = file_name.rsplit(".", 1)[0] + ".pdf"
        safe_print(f"\n[PDF] Creating report about '{subject}'...")

        prompt = self._safe_prompt([
            ("system", compose_system_prompt(
                "You are TOM in Report mode. Generate PDF report content as JSON. "
                "Return ONLY JSON:\n"
                '{"title": "Report Title", "sections": [{"type": "heading|paragraph|bullet|table|chart", '
                '"text": "...", "level": 1, "headers": ["Col1"], "data": [["val"]], '
                '"labels": ["A"], "chart_data": [10]}]}',
                "TOM", include_ui=True)),
            ("user", "Conversation memory:\n{memory}\n\nCommand: {command}\n\nSubject: {subject}"),
        ])
        try:
            resp = await self._invoke_llm(prompt, {"memory": memory_context, "command": command, "subject": subject},
                                           "pdf")
            content = resp.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            report = json.loads(content)
            result = await self.file_tools.create_pdf_report(
                file_name, title=report.get("title", subject),
                author="TOM AI", sections=report.get("sections", []),
            )
            if result["status"] == "success":
                self.file_tools.open_file(result["path"])
            return result
        except Exception as e:
            self.safety.log_action("PDF", target=file_name, status="FAILURE",
                                   message=f"LLM content generation failed, used fallback: {e}")
            result = await self.file_tools.create_pdf_report(file_name, title=subject, author="TOM AI")
            if result["status"] == "success":
                self.file_tools.open_file(result["path"])
                result["message"] = (result.get("message", "") +
                                     f"\n⚠️ Content generation failed ({type(e).__name__}), so this is an "
                                     "empty report shell. Try rephrasing for full content.")
            return result

    # ── DATA ANALYSIS ───────────────────────────────────────────────────

    async def _execute_data_analysis(self, command: str, parsed: Dict) -> Dict[str, Any]:
        memory_context = self._build_memory_context(command)
        data_source = parsed.get("data_source") or ""
        search_topic = parsed.get("search_topic") or ""

        # ── Compound intent: "open <app> and analyze ..." ────────────────
        # If the user asked to OPEN an app (Power BI / Excel / Tableau) as part
        # of the analysis request, actually open it instead of refusing.
        open_note = ""
        _app_m = re.search(r"\bopen\s+(power\s*bi|excel|tableau)\b", command, re.I)
        if _app_m:
            _app = _app_m.group(1).lower().replace(" ", "")
            _app = {"powerbi": "power bi desktop"}.get(_app, _app)
            try:
                _open_res = await self.execute_open_command(f"open {_app}")
                open_note = ("Opened " + _app + ". ") if _open_res.get("status") == "success"                     else (f"Could not open {_app} ({_open_res.get('message', '')[:80]}). ")
            except Exception as _oe:
                open_note = f"Could not open {_app} ({str(_oe)[:60]}). "

        # ── Real pipeline first ──────────────────────────────────────────
        # If an actual data file is referenced, run the genuine
        # DataAnalysisEngine (clean → insights → charts → HTML report)
        # instead of only generating a script. HONEST LABELLING: the HTML
        # report is a BI-style dashboard, NOT a Power BI (.pbix) artifact.
        candidate = data_source.strip()
        if not candidate:
            m = re.search(r"([\w\-./\\:]+\.(?:csv|xlsx|xls|json|parquet))\b", command, re.I)
            candidate = m.group(1) if m else ""
        real_path = ""
        if not candidate and re.search(r"\b(sample|demo|dummy|test)\b.{0,20}\bdata\b", command, re.I):
            # Generate a realistic sample dataset so the REAL pipeline runs
            # (sales-flavoured if the request mentions sales/retail/mart).
            try:
                import pandas as _pd
                import numpy as _np
                rng = _np.random.default_rng(42)
                n = 240
                regions = ["North", "South", "East", "West"]
                cats = ["Groceries", "Apparel", "Electronics", "Home", "Toys"]
                df_s = _pd.DataFrame({
                    "date": _pd.date_range("2025-01-01", periods=n, freq="D"),
                    "region": rng.choice(regions, n),
                    "category": rng.choice(cats, n),
                    "units_sold": rng.integers(5, 220, n),
                    "unit_price": _np.round(rng.uniform(1.5, 90.0, n), 2),
                })
                df_s["revenue"] = _np.round(df_s["units_sold"] * df_s["unit_price"], 2)
                _dir = project_path_str("output", "analysis")
                os.makedirs(_dir, exist_ok=True)
                real_path = os.path.join(_dir, "sample_sales_data.csv")
                df_s.to_csv(real_path, index=False)
                open_note += f"Generated sample dataset ({n} rows): {real_path}. "
            except Exception as _ge:
                self.safety.log_action("WARN", target="data_analysis", status="FAILURE",
                                       message=f"sample generation failed: {_ge}")
        if candidate and not real_path:
            abs_try = candidate if os.path.isabs(candidate) else project_path_str(candidate)
            real_path = candidate if os.path.isfile(candidate) else (
                abs_try if os.path.isfile(abs_try) else "")
        if real_path:
                try:
                    from tools.data_analysis import DataAnalysisEngine
                    engine = DataAnalysisEngine()
                    df = await asyncio.to_thread(engine.load_data, real_path)
                    if df is not None:
                        stem = os.path.splitext(os.path.basename(real_path))[0]
                        df, clean_log = await asyncio.to_thread(engine.auto_clean, df)
                        insights = await asyncio.to_thread(engine.generate_insights, df)
                        charts = await asyncio.to_thread(engine.auto_visualize, df, stem)
                        report = await asyncio.to_thread(
                            engine.generate_report, df, f"{stem} analysis")
                        ov = insights.get("overview", {})
                        recs = insights.get("recommendations", [])[:5]
                        msg = (
                            open_note +
                            f"Data analysis complete (real pipeline, not codegen).\n"
                            f"Rows: {ov.get('rows')} | Columns: {ov.get('columns')} | "
                            f"Missing cells: {ov.get('missing_cells')} | "
                            f"Duplicates: {ov.get('duplicate_rows')}\n"
                            f"Cleaning applied: {str(clean_log)[:280]}\n"
                            f"Charts: {', '.join(charts) if charts else 'none'}\n"
                            f"BI-style HTML dashboard (note: not a Power BI .pbix): {report}\n"
                        )
                        if recs:
                            msg += "Top recommendations:\n" + "\n".join(f"- {r}" for r in recs)
                        return {"status": "success", "message": msg,
                                "response_type": "data_analysis",
                                "report_path": report, "charts": charts}
                except Exception as e:
                    self.safety.log_action(
                        "WARN", target="data_analysis", status="FAILURE",
                        message=f"real pipeline failed, falling back to codegen: {e}")

        prompt = self._safe_prompt([
            ("system", compose_system_prompt(
                "You are TOM in Data Analyst mode (professional level). "
                "Generate a COMPLETE Python script using pandas, matplotlib, seaborn for data analysis. "
                f"{'The data source is: ' + data_source if data_source else 'Generate sample data or instruct user to provide data.'} "
                "Include: data loading, cleaning, analysis, visualizations, and insights. "
                "Output each file with --- FILE: path --- markers if needed. "
                "Provide the COMPLETE runnable script.",
                "TOM", include_ui=True)),
            ("user", "Conversation memory:\n{memory}\n\nCommand: {command}\n\nData source: {data_source}\nTopic: {search_topic}"),
        ])
        try:
            resp = await self._invoke_llm(prompt, {"memory": memory_context, "command": command,
                                                     "data_source": data_source, "search_topic": search_topic},
                                           "data_analysis", self.code_llm)
            content = resp.content.strip()

            # Write any generated files
            base_dir = self._deliverable_target(command, parsed, "data_analysis")
            files_written = []
            if "--- FILE:" in content:
                for match in re.finditer(r"--- FILE:\s*(.+?)\s*---\n(.*?)(?=--- FILE:|$)", content, re.DOTALL):
                    fpath = self._place_in(base_dir, match.group(1))
                    fcontent = match.group(2).strip()
                    try:
                        await self.file_tools.write_file(fpath, fcontent)
                        files_written.append(fpath)
                    except Exception as e:
                        files_written.append(f"{fpath} (failed: {e})")

            msg = open_note + f"Data analysis complete.\n\n{content[:2000]}"
            if files_written:
                msg += f"\n\nFiles written: {', '.join(files_written)}"
            return {"status": "success", "message": msg, "response_type": "data_analysis"}
        except Exception as e:
            return {"status": "error", "message": f"Data analysis failed: {str(e)}"}

    # ── DOCUMENT WRITING ────────────────────────────────────────────────

    async def _execute_document_writing(self, command: str, parsed: Dict) -> Dict[str, Any]:
        memory_context = self._build_memory_context(command)
        person = parsed.get("person_name", "")
        subject = parsed.get("subject", "")

        prompt = self._safe_prompt([
            ("system", compose_system_prompt(
                "You are TOM in Professional Writer mode. Write the requested letter/document with proper formatting, "
                "tone, and structure. Match the formality level. Include proper salutation and closing. "
                "Output the complete document. If it should be a Word document, use --- FILE: path.docx --- markers.",
                "TOM", include_ui=True)),
            ("user", "Conversation memory:\n{memory}\n\nCommand: {command}\n\nPerson/Recipient: {person}\nSubject: {subject}"),
        ])
        resp = await self._invoke_llm(prompt, {"memory": memory_context, "command": command,
                                                 "person": person, "subject": subject},
                                       "document_writing")
        content = resp.content.strip()

        base_dir = self._deliverable_target(command, parsed, "document")
        files_written = []
        if "--- FILE:" in content:
            for match in re.finditer(r"--- FILE:\s*(.+?)\s*---\n(.*?)(?=--- FILE:|$)", content, re.DOTALL):
                fpath = self._place_in(base_dir, match.group(1))
                fcontent = match.group(2).strip()
                try:
                    await self.file_tools.write_file(fpath, fcontent)
                    files_written.append(fpath)
                except Exception as e:
                    files_written.append(f"{fpath} (failed: {e})")

        msg = content
        if files_written:
            msg += f"\n\nFiles written: {', '.join(files_written)}"
        return {"status": "success", "message": msg, "response_type": "document"}

    # ── CODE PROJECT ────────────────────────────────────────────────────

    async def _execute_code_project(self, command: str, parsed: Dict) -> Dict[str, Any]:
        memory_context = self._build_memory_context(command)
        prompt = self._safe_prompt([
            ("system", compose_system_prompt(
                "You are TOM in Full-Stack Developer mode. Generate a complete project scaffold. "
                "Output each file with --- FILE: path/filename --- headers. "
                "Include README.md with setup instructions. Use modern best practices.",
                "TOM", include_ui=True)),
            ("user", "Conversation memory:\n{memory}\n\nCommand: {command}"),
        ])
        resp = await self._invoke_llm(prompt, {"memory": memory_context, "command": command},
                                       "code_project", self.code_llm)
        content = resp.content.strip()
        base_dir = self._deliverable_target(command, parsed, "code_project")
        files_written = []
        if "--- FILE:" in content:
            for match in re.finditer(r"--- FILE:\s*(.+?)\s*---\n(.*?)(?=--- FILE:|$)", content, re.DOTALL):
                fpath = self._place_in(base_dir, match.group(1))
                fcontent = match.group(2).strip()
                try:
                    await self.file_tools.write_file(fpath, fcontent)
                    files_written.append(fpath)
                except Exception as e:
                    files_written.append(f"{fpath} (failed: {e})")
        msg = content[:2000]
        if files_written:
            msg += f"\n\nProject built in: {base_dir}\nFiles written: {', '.join(files_written)}"
        return {"status": "success", "message": msg, "response_type": "code_project",
                "path": base_dir}

    # ── WEBSITE CREATION ────────────────────────────────────────────────

    async def execute_website_creation(self, command: str) -> Dict[str, Any]:
        safe_print(f"\nTOM WILL GENERATE A WEBSITE...\n")
        try:
            name_match = re.search(r'(?:for|called|named)\s+["\']?([a-zA-Z0-9_\-\s]+?)["\']?(?:\s+website|\s+site|$)',
                                   command, re.IGNORECASE)
            project_name = name_match.group(1).strip().replace(" ", "_").lower()[:30] if name_match else "premium_site"
            target_root = self._extract_target_dir(command)
            memory_context = self._build_memory_context(command)

            prompt = self._safe_prompt([
                ("system", compose_system_prompt(
                    "You are a master frontend developer. Generate a premium, modern, responsive website. "
                    "Return ONLY JSON with keys 'index_html' and 'style_css'. "
                    "Write real, engaging content - no placeholders. Modern CSS with flexbox/grid.",
                    "TOM", include_ui=True)),
                ("user", "Conversation memory:\n{memory}\n\nBuild website for: {command}"),
            ])
            resp = await self._invoke_llm(prompt, {"memory": memory_context, "command": command},
                                           "website", self.code_llm)
            content = resp.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            payload = json.loads(content)
            result = await self.file_tools.create_website(
                project_name, payload.get("index_html"), payload.get("style_css"),
                target_root=target_root or None)
            if result.get("status") == "success":
                safe_print(f"Website generated at: {result['path']}/")
                preview_note = "Open index.html in your browser to view it."
                try:
                    import webbrowser
                    index_path = os.path.join(result["path"], "index.html")
                    if os.path.isfile(index_path):
                        webbrowser.open("file:///" + index_path.replace(os.sep, "/"))
                        preview_note = "Preview opened in your browser."
                except Exception:
                    pass
                return {"status": "success",
                        "message": f"Website '{project_name}' created successfully!\nBuilt in: {result['path']}\nFiles: index.html + style.css\n{preview_note}",
                        "path": result["path"]}
            # Friendly error instead of raw internal dict
            err_detail = result.get("message") or result.get("error") or str(result)
            return {"status": "error", "message": f"Could not write website files: {err_detail}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ── DELETE (guarded) ────────────────────────────────────────────────

    @staticmethod
    def _is_delete_request(command_lower: str) -> bool:
        """True only for a filesystem delete ("delete the folder X", "rm C:\\...").

        Requires both a delete verb AND a filesystem signal (file/folder/path
        word, or a path-shaped token) so "delete my last email" or "remove the
        meeting" never reach the file deleter.
        """
        cl = command_lower or ""
        verbs = ("delete ", "remove ", "erase ", "trash ", "get rid of ", "rm -")
        if not any(v in cl for v in verbs):
            return False
        if any(w in cl for w in ("file", "folder", "directory", " dir ", "path")):
            return True
        # A path-shaped token: C:\..., /home/..., or a name.ext
        return bool(re.search(r'[a-z]:[\\/]|/(?:home|mnt|users|tmp)/|["\']?[\w .\-]+\.\w{1,6}\b', cl))

    def _extract_delete_target(self, command: str, parsed: Dict) -> str:
        """Resolve which path the user wants deleted (absolute, best-effort)."""
        explicit = self._extract_target_dir(command)
        if explicit:
            return explicit
        cand = ""
        m = re.search(r'["\']([^"\']+)["\']', command)
        if m:
            cand = m.group(1)
        if not cand:
            cand = parsed.get("file_name") or ""
        if not cand:
            m = re.search(r'(?:folder|directory|dir|file)\s+(?:called\s+|named\s+)?'
                          r'["\']?([\w .\-]+?)["\']?(?:\s|$)', command, re.I)
            cand = m.group(1).strip() if m else ""
        if not cand:
            m = re.search(r'\b([\w .\-]+\.\w{1,6})\b', command)
            cand = m.group(1).strip() if m else ""
        cand = (cand or "").strip().strip('"').strip("'")
        if not cand:
            return ""
        if os.path.isabs(os.path.expanduser(cand)):
            return os.path.expanduser(cand)
        # Bare name: resolve against the most likely locations, in order.
        from tools.project_paths import workspace_root
        from pathlib import Path as _Path
        bases = [workspace_root(), _Path(os.path.expanduser("~/Desktop")),
                 _Path(os.path.expanduser("~/OneDrive/Desktop")), _Path.cwd()]
        for base in bases:
            try:
                p = base / cand
                if p.exists():
                    return str(p)
            except OSError:
                continue
        return str(workspace_root() / cand)  # doesn't exist; delete_path reports it cleanly

    async def execute_delete(self, command: str, parsed: Dict) -> Dict[str, Any]:
        """Delete a file/folder after an explicit, informed confirmation."""
        target = self._extract_delete_target(command, parsed)
        if not target:
            return {"status": "needs_input",
                    "message": "Which file or folder should I delete? "
                               "Give me its name or full path."}
        return await self.file_tools.delete_path(
            target, approval_manager=self.approval_manager)

    # ── EXPLANATION / UNDERSTANDING ──────────────────────────────────────────

    async def _explain_how_it_works(self, command: str, parsed: Dict) -> Dict[str, Any]:
        """Explain how a TOM feature/component works using the LLM with full context."""
        # Extract what the user wants explained
        topic = self._extract_explanation_topic(command)
        
        # Build comprehensive context about TOM's capabilities
        system_prompt = (
            "You are TOM, an AI assistant explaining your own capabilities to the user. "
            "Provide clear, concise explanations of how specific features work. "
            "Structure your response as:\n"
            "1. What the user asked about (confirm understanding)\n"
            "2. How it works (step-by-step)\n"
            "3. What the user needs to do to use it\n"
            "4. Any prerequisites or setup needed\n"
            "Keep it practical and conversational. Don't be verbose."
        )
        
        # Get relevant memory/knowledge context
        memory_context = self._build_memory_context(command)
        
        # Add specific knowledge about the topic if available
        knowledge = self._get_topic_knowledge(topic)
        
        prompt = self._safe_prompt([
            ("system", system_prompt),
            ("user", f"User asked: {command}\n\n"
                     f"Topic to explain: {topic}\n\n"
                     f"Memory context:\n{memory_context}\n\n"
                     f"Knowledge base:\n{knowledge}\n\n"
                     f"Explain how this works in a clear, practical way.")
        ])
        
        resp = await self._invoke_llm(prompt, {"command": command, "topic": topic, "memory": memory_context}, "explanation", self.llm)
        explanation = (getattr(resp, "content", "") or "").strip()
        
        return {
            "status": "success",
            "message": explanation,
            "response_type": "explanation",
            "topic": topic
        }

    def _extract_explanation_topic(self, command: str) -> str:
        """Extract the main topic from an explanation request."""
        import re
        command_lower = command.lower()
        # Patterns like "explain how X works", "how does X work", "what is X"
        patterns = [
            r"explain how\s+(.+?)(?:\s+works?)?(?:\?|$)",
            r"how does\s+(.+?)\s+work(?:\?|$)",
            r"how do\s+(.+?)\s+work(?:\?|$)",
            r"what is\s+(.+?)(?:\?|$)",
            r"what are\s+(.+?)(?:\?|$)",
            r"how\s+(.+?)\s+works?(?:\?|$)",
            r"describe how\s+(.+?)(?:\?|$)",
            r"tell me how\s+(.+?)(?:\?|$)",
            r"explain what\s+(.+?)(?:\?|$)",
            r"explain the\s+(.+?)(?:\?|$)",
            r"how to use\s+(.+?)(?:\?|$)",
            r"how can i\s+(.+?)(?:\?|$)",
            r"what does\s+(.+?)\s+do(?:\?|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, command_lower)
            if match:
                return match.group(1).strip().rstrip("?.,!")
        # Fallback: return the command itself
        return command.strip().rstrip("?.,!")

    def _get_topic_knowledge(self, topic: str) -> str:
        """Get relevant knowledge from TOM's knowledge base about a topic."""
        if not getattr(self, "knowledge", None):
            return "No curated knowledge base available."
        
        topic_lower = topic.lower()
        knowledge_parts = []
        
        # Search knowledge base for relevant sections
        try:
            words = [w for w in topic_lower.split() if len(w) > 3]
            for w in words[:5]:
                results = self.knowledge.search(w)
                for r in results[:2]:
                    dom = self.knowledge.cache.get(r.get("domain_key"), {})
                    for section in dom.get("sections", []):
                        if section.get("name") == r.get("section"):
                            expl = (section.get("explanation_simple") or "").strip()
                            if expl:
                                knowledge_parts.append(f"[{r.get('domain')} / {r.get('section')}] {expl[:300]}")
                            break
                    if len(knowledge_parts) >= 5:
                        break
                if len(knowledge_parts) >= 5:
                    break
        except Exception:
            pass
        
        # Add specific known topics
        if "email agent" in topic_lower:
            knowledge_parts.append(
                "[Email Agent] Automatically monitors inbox, classifies emails by importance, "
                "drafts replies for approval, and sends approved emails via Gmail OAuth2. "
                "Controlled with: 'start email agent', 'stop email agent', 'email agent summary'."
            )
        if "instagram agent" in topic_lower:
            knowledge_parts.append(
                "[Instagram Agent] Scrapes Instagram posts, extracts AI/news content, "
                "generates reports, and can email them. "
                "Controlled with: 'start instagram agent', 'instagram workflow'."
            )
        if "voice" in topic_lower:
            knowledge_parts.append(
                "[Voice] Uses SpeechRecognition (Google/Whisper) for input and edge-tts (Microsoft Neural) "
                "or pyttsx3 for output. Continuous conversation mode available. "
                "Requires: microphone, internet for STT/TTS (or local Whisper)."
            )
        if "rag" in topic_lower or "memory" in topic_lower:
            knowledge_parts.append(
                "[RAG Memory] Semantic memory using ChromaDB - stores conversations, documents, "
                "knowledge as vectors. Retrieves relevant context by meaning. "
                "Long-term memory (Hindsight) stores preferences/corrections across sessions."
            )
        
        return "\n\n".join(knowledge_parts) if knowledge_parts else "No specific knowledge found for this topic."

    # ── EMAIL ───────────────────────────────────────────────────────────

    async def _handle_email_write(self, command: str, parsed: Dict) -> Dict[str, Any]:
        """Write/draft an email with LLM-generated, memory-aware content.

        A real address → saved draft (EmailTools.draft_email). A bare name
        ("email Ravi about …") → the draft text is returned for review, since
        there is no address to attach it to yet.
        """
        email_address = parsed.get("email_address") or ""
        recipient = email_address or parsed.get("recipient_name") or parsed.get("person_name") or ""
        recipient = CommandParser._clean_name(recipient) or ""
        subject = parsed.get("subject") or ""
        message_body = parsed.get("message_body") or ""

        if not recipient:
            return {"status": "error",
                    "message": "Who is the email for? Include a name or an email address."}

        memory_context = self._build_memory_context(command)
        brief = (
            f"Write an email to {recipient}. Request from the user: {command}. "
            + (f"Subject hint: {subject}. " if subject else "")
            + (f"User also said: {message_body[:500]}. " if message_body else "")
            + "Follow every stated preference about tone, length and sign-off found in memory."
            + f"\n\nMemory:\n{memory_context}"
        )

        is_address = is_valid_address(recipient)
        if not is_address:
            safe_print(f"[EMAIL] Drafting for a name (no address yet): {recipient}")
        draft_prompt = self._safe_prompt([
            ("system",
             "You are TOM, a professional email assistant. Draft a complete, polished email. "
             "Respond ONLY with:\nSUBJECT: <subject>\nBODY:\n<body>"),
            ("user", "{brief}"),
        ])
        # One text-format path for addresses and names alike. The old address path asked for
        # JSON and, when a model answered in any other shape, "drafted" the internal prompt
        # (memory dump included) as the email body.
        resp = await self._invoke_llm(draft_prompt, {"brief": brief}, "email_draft", self.llm)
        content = (getattr(resp, "content", "") or "").strip()
        draft_subject, draft_body = "", content
        if "BODY:" in content:
            head, draft_body = content.split("BODY:", 1)
            for line in head.splitlines():
                if line.upper().startswith("SUBJECT:"):
                    draft_subject = line.split(":", 1)[1].strip()
            draft_body = draft_body.strip()
        if not draft_body:
            return {"status": "error", "message": "I couldn't draft that email - the model returned nothing. Try again."}
        draft_subject = draft_subject or subject or "Message from TOM"
        result = {
            "status": "success",
            "response_type": "email_draft",
            "recipient": recipient,
            "subject": draft_subject,
            "body": draft_body,
        }
        tail = (f"Nothing has been sent. To send it, ask: send an email to {recipient} with this subject and text."
                if is_address else
                f"(Tell me {recipient}'s email address and I'll prepare it for sending.)")
        result["message"] = f"Draft email to {recipient}\nSubject: {draft_subject}\n\n{draft_body}\n\n{tail}"
        if is_address:
            saved = await self.email_tools.draft_email(recipient, draft_subject, draft_body)
            result["draft"] = saved
        return result

    async def execute_email_send_flow(self, command: str, parsed: Dict) -> Dict[str, Any]:
        """Send an email with LLM-generated content and async approval."""
        parsed_subject = parsed.get("subject") or ""
        parsed_body = parsed.get("message_body") or ""

        # Only a real address can be sent to. A bare name ("email Ravi") used to be
        # passed straight to SMTP and failed there with an opaque server error.
        match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', command)
        recipient = parsed.get("email_address") or (match.group(1) if match else "")
        if not recipient:
            who = CommandParser._clean_name(parsed.get("recipient_name") or parsed.get("person_name") or "")
            return {"status": "error",
                    "message": (f"I need {who}'s email address to send this (e.g. name@example.com)."
                                if who else "I need the recipient's email address (e.g. name@example.com).")}

        # If we don't have a real body, use LLM to write the whole email
        if not parsed_body or len(parsed_body.strip()) < 20:
            memory_context = self._build_memory_context(command)
            draft_prompt = self._safe_prompt([
                ("system",
                 "You are TOM, a professional AI assistant. The user wants to send an email. "
                 "Generate a professional, contextually appropriate email. "
                 "Respond ONLY with:\nSUBJECT: <subject>\nBODY:\n<body>"),
                ("user",
                 "Memory:\n{memory}\n\n"
                 "User command: {command}\n"
                 "Recipient: {recipient}\n"
                 "Draft the email now."),
            ])
            resp = await self._invoke_llm(
                draft_prompt,
                {"memory": memory_context, "command": command, "recipient": recipient},
                "email_draft_for_send", self.llm,
            )
            content = resp.content.strip()
            subject = ""
            body = ""
            for line in content.splitlines():
                if line.upper().startswith("SUBJECT:"):
                    subject = line.split(":", 1)[1].strip()
                elif line.upper().startswith("BODY:"):
                    body = content.split("BODY:", 1)[-1].split("BODY:\n", 1)[-1].strip()
                    break
            if not body:
                body = content  # fallback: use the whole LLM output as body
            if not subject:
                subject = parsed_subject or "Message from TOM"
        else:
            subject = parsed_subject or "Message from TOM"
            body = parsed_body

        safe_print(f"\n[EMAIL] To: {recipient} | Subject: {subject}")

        # Approval callback for non-blocking send
        # The user must approve the actual message. The earlier gate only saw the
        # command text; the subject/body (often LLM-written) exist only now.
        async def approve_send(rec, subj, bdy):
            request = ApprovalRequest(
                action="send_email",
                summary=f"Send this email to {rec}?\nSubject: {subj}\n\n{bdy[:800]}",
                details={"to": rec, "subject": subj},
                risk_level="high",
            )
            return await asyncio.to_thread(self.approval_manager.request_approval, request)

        result = await self.email_tools.send_email(recipient, subject, body, approval_callback=approve_send)
        return result

    async def execute_email_task(self, command: str) -> Dict[str, Any]:
        """Legacy email drafting."""
        parsed = await self.understand_command(command)
        return await self._handle_email_write(command, parsed)

    async def execute_email_inbox_workflow(self, command: str = "") -> Dict[str, Any]:
        provider = os.environ.get("EMAIL_PROVIDER", "gmail")
        max_count = int(os.environ.get("EMAIL_INBOX_MAX_COUNT", "10"))
        auto_reply_enabled = os.environ.get("EMAIL_AUTO_REPLY_ENABLED", "false").lower() == "true"

        connect_result = await self.email_tools.connect_email_service(provider)
        if connect_result.get("status") != "success":
            return {"status": "error", "message": f"Email connection failed: {connect_result.get('message')}"}

        # "unread emails" / "new mail" means unread only, not simply the last N.
        unread_only = bool(re.search(r"\b(?:unread|unseen)\b|\bnew\s+(?:e-?mails?|mail|messages?)\b",
                                     (command or "").lower()))
        fetch_result = await self.email_tools.fetch_imap_emails("inbox", max_count=max_count,
                                                                 unread_only=unread_only)
        if fetch_result.get("status") != "success":
            return {"status": "error", "message": f"Email fetch failed: {fetch_result.get('message')}"}

        emails = fetch_result.get("emails", [])
        if not emails:
            return {"status": "success",
                    "message": "No unread emails." if unread_only else "No inbox emails found."}

        important_emails = []
        low_priority_emails = []
        draft_replies = []
        auto_replied = []
        main_screen_items = []
        reply_ledger = AutoReplyLedger()

        for email_item in emails:
            analysis = _classify_email_item_fn(email_item)
            if analysis["priority"] == "important":
                important_emails.append(analysis)
                main_screen_items.append({"subject": analysis["subject"], "sender": analysis["raw_sender"],
                                          "summary": analysis["summary"]})
            else:
                low_priority_emails.append(analysis)

            if analysis["needs_reply"]:
                sent = None
                if auto_reply_enabled:
                    sent = await auto_reply_if_allowed(self.email_tools, analysis, reply_ledger,
                                                       analysis["reply_body"], len(auto_replied))
                if sent:
                    auto_replied.append(sent)
                elif analysis["sender"]:
                    dr = await self.email_tools.draft_email(analysis["sender"], analysis["reply_subject"], analysis["reply_body"])
                    draft_replies.append(dr)

        inbox_summary = [
            f"Reviewed {len(emails)} emails.",
            f"Important: {len(important_emails)}.",
            f"Low priority: {len(low_priority_emails)}.",
            f"Draft replies: {len(draft_replies)}.",
            f"Auto-replied: {len(auto_replied)}." if auto_reply_enabled else "Auto-replied: 0 (disabled).",
        ]

        message_parts = ["\n".join(inbox_summary)]
        if important_emails:
            message_parts.append("\n--- IMPORTANT ---")
            for idx, e in enumerate(important_emails, 1):
                message_parts.append(f"\n{idx}. From: {e.get('raw_sender')}\n   Subject: {e.get('subject')}\n   Summary: {e.get('summary')}")

        return {
            "status": "success", "message": "\n".join(message_parts),
            "emails_reviewed": len(emails), "important_count": len(important_emails),
            "low_priority_count": len(low_priority_emails), "draft_reply_count": len(draft_replies),
            "auto_replied_count": len(auto_replied), "summary_lines": inbox_summary,
            "important_emails": important_emails, "main_screen_items": main_screen_items,
        }

    # ── WHATSAPP ────────────────────────────────────────────────────────

    async def _execute_whatsapp(self, command: str, parsed: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        parsed = parsed or {}
        details = self.nlp_parser._extract_whatsapp_details(command)
        contact = details.get("contact") or parsed.get("recipient_name") or parsed.get("person_name") or ""
        message = details.get("message") or parsed.get("message_body") or ""

        if not contact or not message:
            for task in parsed.get("compound_tasks", []) or []:
                if task.get("intent") == "whatsapp_message":
                    contact = contact or task.get("recipient_name") or task.get("person_name") or ""
                    message = message or task.get("message_body") or ""
                    break

        if not contact or not message:
            memory_context = self._build_memory_context(command)
            prompt = self._safe_prompt([
                ("system", "Extract WhatsApp recipient and message. Reply with:\nTO: <name>\nMESSAGE: <text>"),
                ("user", "Memory:\n{memory}\n\nCommand: {command}"),
            ])
            try:
                resp = await self._invoke_llm(
                    prompt,
                    {"memory": memory_context, "command": command},
                    "whatsapp_extract",
                    self.fast_llm,
                )
                lines = resp.content.strip().splitlines()
                for line in lines:
                    if line.upper().startswith("TO:"):
                        contact = line.split(":", 1)[1].strip()
                    elif line.upper().startswith("MESSAGE:"):
                        message = line.split(":", 1)[1].strip()
            except Exception as exc:
                return {"status": "error", "message": f"Could not parse WhatsApp recipient/message: {exc}"}

        contact = str(contact).strip()
        message = str(message).strip()
        if not contact or not message:
            return {"status": "error", "message": f"Could not determine WhatsApp contact or message from: {command}"}

        safe_print(f"\n[WhatsApp] To: {contact} | Message: {message[:80]}...")
        self.safety.log_action("WHATSAPP_SEND", target=contact, status="ATTEMPTING", message=message[:100])
        result = await self.whatsapp_tools.send_message(contact, message)
        self.safety.log_action("WHATSAPP_SEND", target=contact,
                               status={"success": "SUCCESS", "unconfirmed": "UNCONFIRMED"}.get(
                                   result.get("status"), "FAILURE"),
                               message=result.get("message", ""))
        return result

    # ── WEB SEARCH / RESEARCH ───────────────────────────────────────────

    async def _web_search(self, command: str, parsed: Dict) -> Dict[str, Any]:
        search_topic = parsed.get("search_topic") or parsed.get("subject") or command
        result = await self._research_topic(search_topic)
        return {"status": "success", "message": f"Research results for '{search_topic}':\n\n{result[:2000]}",
                "response_type": "web_search", "full_content": result}

    async def _research_topic(self, topic: str) -> str:
        """Search the web for information about a topic."""
        try:
            # Try using googlesearch library first
            from googlesearch import search
            results = []
            for i, url in enumerate(search(topic, num_results=5)):
                if i >= 5:
                    break
                try:
                    import requests
                    from bs4 import BeautifulSoup
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    r = requests.get(url, timeout=5, headers=headers)
                    soup = BeautifulSoup(r.text, 'html.parser')
                    text = soup.get_text()[:1000]
                    results.append(f"Source: {url}\n{text.strip()[:500]}")
                except Exception:
                    results.append(f"Source: {url} (content unavailable)")
            if results:
                return "\n\n".join(results)
        except ImportError:
            pass
        except Exception as e:
            safe_print(f"[WEB] Search error: {e}")

        # Fallback: use LLM to generate content based on its knowledge
        memory_context = self._build_memory_context(topic)
        prompt = self._safe_prompt([
            ("system", "You are TOM researching '{topic}'. Provide comprehensive, factual information. "
             "Include key facts, statistics, and organized sections."),
            ("user", "Research the following topic thoroughly and provide well-structured information:\n{topic}\n\nMemory: {memory}"),
        ])
        try:
            resp = await self._invoke_llm(prompt, {"topic": topic, "memory": memory_context}, "research", self.llm)
            return resp.content.strip()
        except Exception:
            return f"Could not research '{topic}'. Please check internet connection."

    # ── KNOWLEDGE ACQUISITION (learn a missing topic from the web) ───────

    @staticmethod
    def _is_learn_request(command_lower: str) -> bool:
        triggers = ("learn about", "learn how to", "research and remember",
                    "add knowledge about", "teach yourself", "gain knowledge about",
                    "acquire knowledge", "update your knowledge", "study up on",
                    "remember everything about")
        return any(t in command_lower for t in triggers)

    @staticmethod
    def _learn_topic(command: str) -> str:
        """Strip the trigger phrase to leave the topic to learn."""
        t = command or ""
        phrases = ("research and remember", "add knowledge about",
                   "update your knowledge about", "update your knowledge on",
                   "remember everything about", "acquire knowledge about",
                   "acquire knowledge on", "gain knowledge about",
                   "teach yourself about", "teach yourself", "study up on",
                   "learn how to", "learn about", "learn")
        for p in phrases:  # longest first so "learn about" wins over "learn"
            t = re.sub(r'(?i)\b' + re.escape(p) + r'\b', ' ', t, count=1)
            if t != command:
                break
        return t.strip(" .:-\t") or command

    async def acquire_knowledge(self, topic: str) -> Dict[str, Any]:
        """Research a topic TOM lacks, save it to the knowledge base, reload.

        Safe acquisition: it gathers information from the web (or the model's
        knowledge as a fallback) and stores a curated markdown note that the
        knowledge engine then serves. It does NOT download and run code from the
        internet — fetching and executing untrusted tools is intentionally not
        automated.
        """
        topic = (topic or "").strip()
        if not topic:
            return {"status": "needs_input", "message": "What topic should I learn about?"}
        safe_print(f"[LEARN] Acquiring knowledge about '{topic}'...")
        research = await self._research_topic(topic)
        if not research or research.lower().startswith("could not research"):
            return {"status": "error",
                    "message": f"Could not gather reliable information about '{topic}'. "
                               "Check the internet connection and try again."}
        slug = re.sub(r'[^a-z0-9]+', '-', topic.lower()).strip('-')[:50] or "topic"
        import datetime as _dt
        note = (f"# {topic.title()}\n\n"
                f"> Acquired by TOM on {_dt.date.today():%Y-%m-%d} via web research. "
                "Verify critical facts against primary sources before relying on them.\n\n"
                f"{research}\n")
        note_path = project_path_str("knowledge", f"acquired_{slug}.md")
        try:
            with open(note_path, "w", encoding="utf-8") as f:
                f.write(note)
        except Exception as e:
            return {"status": "error",
                    "message": f"Researched '{topic}' but could not save the note: {e}"}
        # Hot-reload the knowledge engine so the note is usable right away.
        try:
            import tools.knowledge_engine as _ke
            _ke._instance = None
            self.knowledge = _ke.get_engine()
        except Exception as _kerr:
            safe_print(f"[LEARN] Note saved but engine reload failed: {_kerr}")
        # Store in RAG for semantic recall too.
        if self.rag and getattr(self.rag, "available", False):
            try:
                self.rag.store_conversation("assistant", note[:4000],
                                            {"topic": topic, "acquired": "true"})
            except Exception:
                pass
        return {"status": "success", "response_type": "knowledge_acquired",
                "message": (f"Learned about '{topic}' and saved it to the knowledge base "
                            f"(knowledge/acquired_{slug}.md) — I can use this now.\n\n"
                            f"Summary:\n{research[:1200]}"),
                "path": note_path}

    # ── TOOL ACQUISITION (install / clone / scaffold a capability) ───────

    # A forge repo reference like "github.com/owner/repo" (NOT a bare "github.com",
    # which also appears inside email addresses such as boss@github.com).
    _REPO_RE = (r"(?:https://)?(?:www\.)?"
                r"(?:github|gitlab|bitbucket|codeberg)\.com/[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+")

    @staticmethod
    def _is_acquire_tool_request(command_lower: str) -> bool:
        cl = command_lower or ""
        # An email command is never a tool-acquisition request, even if the
        # address domain happens to be a forge (boss@github.com).
        if re.search(r"\b(e-?mail|send (?:an? )?(?:mail|message))\b", cl) and "@" in cl:
            return False
        if re.search(TomAgent._REPO_RE, cl) or re.search(r"\bclone\b.*https?://", cl):
            return True
        if re.search(r"\b(get|download|fetch|clone)\b.*\bfrom (?:github|gitlab|a |the )?repo", cl):
            return True
        if re.search(r"\b(acquired tools|tools you(?:'ve| have) acquired|list acquired)\b", cl):
            return True
        if re.search(r"\b(build|make|create|scaffold|generate)\b[^.]*\ba (new )?tool\b", cl):
            return True
        if re.search(r"\bpip install\b", cl):
            return True
        if re.search(r"\binstall(?: the)?\s+[A-Za-z0-9._\-]+", cl) and \
           re.search(r"\b(library|package|module|dependency)\b", cl):
            return True
        if re.search(r"^\s*install\s+[A-Za-z0-9._\-\[\]=<>~!]+\s*$", cl):
            return True
        return False

    @staticmethod
    def _extract_package(command: str) -> str:
        m = re.search(r"\b(?:pip install|install(?: the)?|add(?: the)?)\s+"
                      r"([A-Za-z0-9._\-\[\]=<>~!]+)", command, re.I)
        if not m:
            return ""
        pkg = m.group(1).strip()
        return "" if pkg.lower() in ("library", "package", "module", "dependency", "tool") else pkg

    async def _confirm(self, summary: str, details: Optional[Dict] = None) -> bool:
        return await asyncio.to_thread(
            self.approval_manager.request_approval,
            ApprovalRequest(action="tool_acquisition", summary=summary,
                            details=details or {}, risk_level="high"))

    async def execute_tool_acquisition(self, command: str, parsed: Dict) -> Dict[str, Any]:
        """Acquire a capability TOM lacks: install a library, clone+inspect a
        public repo (read-only), or scaffold a new tool module for review.
        Never downloads-and-runs untrusted code."""
        from tools.tool_acquirer import ToolAcquirer
        acq = ToolAcquirer()
        cl = command.lower()

        if re.search(r"\b(acquired tools|tools you(?:'ve| have) acquired|list acquired)\b", cl):
            return acq.list_acquired()

        url_m = re.search(r"(https://[^\s'\"]+)", command)
        repo_m = re.search(TomAgent._REPO_RE, command, re.I)
        if repo_m or (url_m and "clone" in cl):
            if url_m:
                url = url_m.group(1)
            else:
                url = repo_m.group(0)
                if not url.lower().startswith("http"):
                    url = "https://" + url
            if not url:
                return {"status": "needs_input",
                        "message": "Give me the full https repo URL to clone, e.g. "
                                   "https://github.com/owner/repo."}
            if not await self._confirm(f"Clone and INSPECT this repo (it will not be run)?\n{url}",
                                       {"url": url}):
                return {"status": "cancelled", "message": "Clone cancelled."}
            return await asyncio.to_thread(acq.clone_repo, url)

        if re.search(r"\b(build|make|create|scaffold|generate)\b[^.]*\ba (new )?tool\b", cl):
            return await self._scaffold_tool(command, parsed, acq)

        pkg = self._extract_package(command)
        if not pkg:
            return {"status": "needs_input",
                    "message": "Which package should I install? e.g. 'install requests'."}
        if not await self._confirm(
                f"Install the Python package '{pkg}' into TOM's environment?", {"package": pkg}):
            return {"status": "cancelled", "message": f"Install of '{pkg}' cancelled."}
        return await asyncio.to_thread(acq.install_package, pkg)

    async def _scaffold_tool(self, command: str, parsed: Dict, acq) -> Dict[str, Any]:
        name = parsed.get("subject") or parsed.get("app_name") or "custom_tool"
        prompt = self._safe_prompt([
            ("system", "You are TOM generating a single, self-contained Python tool MODULE. "
             "Return ONLY Python code (no prose). Include a module docstring, imports, and "
             "well-documented functions/classes. No top-level side effects, no network calls "
             "or other work that runs merely on import."),
            ("user", "Build a Python tool for this request:\n{command}"),
        ])
        try:
            resp = await self._invoke_llm(prompt, {"command": command}, "scaffold_tool", self.code_llm)
            code = resp.content.strip()
            if "```" in code:
                blocks = re.findall(r"```(?:python)?\s*(.*?)```", code, re.DOTALL)
                if blocks:
                    code = max(blocks, key=len).strip()
            return acq.save_tool(name, code)
        except Exception as e:
            return {"status": "error", "message": f"Could not scaffold the tool: {e}"}

    # ── SCREEN READ ─────────────────────────────────────────────────────

    async def execute_screen_read(self, command: str) -> Dict[str, Any]:
        try:
            result = await asyncio.to_thread(self.screen_tools.summarize_screen)
            if result.get("status") != "success":
                return result
            screen_text = str(result.get("summary", "")).strip()
            if not screen_text:
                return {"status": "partial", "message": "Screen read succeeded, but no readable text detected."}
            return {"status": "success", "message": "Screen content read.", "screen_summary": screen_text,
                    "text_length": result.get("text_length", 0)}
        except Exception as exc:
            return {"status": "error", "message": f"Failed to read screen: {exc}"}

    # ── FILE / IMAGE ANALYSIS ──────────────────────────────────────────

    async def analyze_file(self, file_path: str, user_question: str = "") -> Dict[str, Any]:
        """Analyze any file — images via Gemma 4 vision, others via FileAnalyzer + LLM."""
        if not os.path.isfile(file_path):
            return {"status": "error", "message": f"File not found: {file_path}"}

        ext = os.path.splitext(file_path)[1].lower()
        is_image = ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")

        if is_image:
            return await self._analyze_image_with_vision(file_path, user_question)

        # Non-image files: use FileAnalyzer + LLM summary
        try:
            analysis = await asyncio.to_thread(self.file_analyzer.analyze, file_path)
            extracted = await asyncio.to_thread(self.file_analyzer.extract_text, file_path)
            file_summary = await asyncio.to_thread(self.file_analyzer.summarize, file_path)

            question = user_question or "Analyze this file and provide key insights."
            prompt = self._safe_prompt([
                ("system", "You are TOM, analyzing a file for the user. "
                 "Provide a clear, useful analysis based on the file content. Be concise."),
                ("user", "File info:\n{file_summary}\n\nFile content:\n{content}\n\nUser question: {question}"),
            ])
            resp = await self._invoke_llm(
                prompt,
                {"file_summary": file_summary, "content": extracted[:3000], "question": question},
                "file_analysis", self.llm)
            return {
                "status": "success",
                "message": resp.content.strip(),
                "file_info": analysis,
                "response_type": "file_analysis",
            }
        except Exception as e:
            return {"status": "error", "message": f"File analysis failed: {e}"}

    async def _analyze_image_with_vision(self, image_path: str, user_question: str = "") -> Dict[str, Any]:
        """Analyze an image with the ACTIVE provider's vision model.

        Groq (hosted) is used when GROQ_VISION_MODEL names a multimodal model on
        the account. Local Ollama vision runs only when the user explicitly
        chose the local provider. With neither available TOM explains why and
        uses local OCR — it never silently calls a local model behind a hosted
        provider setting.
        """
        safe_print(f"[VISION] Analyzing image: {os.path.basename(image_path)}")
        if llm_factory.provider() == "groq":
            hosted_model = llm_factory.groq_vision_model()
            if hosted_model:
                hosted = await self._analyze_image_with_groq_vision(image_path, user_question, hosted_model)
                if hosted is not None:
                    return hosted
                note = ("Groq vision could not analyze this image, so I used local OCR "
                        f"({str(getattr(self, '_vision_error', ''))[:120]}).")
            else:
                note = ("Groq is the active provider and no vision model is configured, so I used "
                        "local OCR. Set GROQ_VISION_MODEL in .env to a multimodal model your Groq "
                        "account can use, or run TOM with TOM_LLM_PROVIDER=ollama for local vision.")
            return await self._analyze_image_with_ocr(image_path, user_question, note)
        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            b64_image = base64.b64encode(image_bytes).decode("utf-8")
            question = user_question or "Describe this image in detail. What do you see?"

            # Direct Ollama API call — guaranteed vision support
            import urllib.request
            base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            payload = json.dumps({
                "model": self.model_name,
                "prompt": question,
                "images": [b64_image],
                "stream": False,
                "options": {"num_predict": 2048},
            }).encode()
            req = urllib.request.Request(
                f"{base_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            safe_print("[VISION] Sending image to the local vision model...")
            resp_data = await asyncio.wait_for(
                asyncio.to_thread(lambda: urllib.request.urlopen(req, timeout=120).read()),
                timeout=self.model_timeout_seconds,
            )
            result = json.loads(resp_data.decode())
            response_text = result.get("response", "").strip()

            if not response_text:
                raise RuntimeError("Empty response from vision model")

            safe_print("[VISION] Analysis complete.")
            return {
                "status": "success",
                "message": response_text,
                "response_type": "image_analysis",
            }
        except Exception as e:
            safe_print(f"[VISION] Local vision failed ({e}), falling back to OCR...")
            return await self._analyze_image_with_ocr(
                image_path, user_question,
                f"The local vision model could not analyze this image ({str(e)[:120]}).")

    async def _analyze_image_with_groq_vision(self, image_path: str, user_question: str,
                                              model_id: str) -> Optional[Dict[str, Any]]:
        """Hosted image analysis through Groq. Returns None (never raises) on failure."""
        try:
            from langchain_core.messages import HumanMessage
            with open(image_path, "rb") as fh:
                b64_image = base64.b64encode(fh.read()).decode("utf-8")
            question = user_question or "Describe this image in detail. What do you see?"
            message = HumanMessage(content=[
                {"type": "text", "text": question},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/{_image_mime(image_path)};base64,{b64_image}"}},
            ])
            llm = llm_factory.make_groq_model(model_id, max_tokens=2048)
            response = await asyncio.wait_for(llm.ainvoke([message]),
                                              timeout=self.model_timeout_seconds)
            text = _message_text(response)
            if not text:
                raise RuntimeError("empty response from the Groq vision model")
            safe_print(f"[VISION] Groq vision analysis complete ({model_id}).")
            return {"status": "success", "message": text,
                    "response_type": "image_analysis", "model": model_id}
        except Exception as exc:
            self._vision_error = str(exc)[:200]
            safe_print(f"[VISION] Groq vision failed ({exc}); using OCR instead.")
            return None

    async def _analyze_image_with_ocr(self, image_path: str, user_question: str,
                                      note: str = "") -> Dict[str, Any]:
        """OCR + file metadata fallback — local tooling, not a hidden model swap."""
        try:
            summary = await asyncio.to_thread(self.file_analyzer.summarize, image_path)
            extracted = await asyncio.to_thread(self.file_analyzer.extract_text, image_path)
            ocr_text = extracted.strip() if extracted else ""

            if ocr_text and len(ocr_text) > 20:
                fallback_prompt = self._safe_prompt([
                    ("system", "You are TOM. The user attached an image. "
                     "Vision analysis is unavailable, but OCR extracted text from the image. "
                     "Analyze the extracted text and answer the user's question."),
                    ("user", "Image info:\n{summary}\n\nOCR text from image:\n{ocr_text}\n\nUser question: {question}"),
                ])
                question = user_question or "What does this image contain?"
                resp = await self._invoke_llm(
                    fallback_prompt,
                    {"summary": summary, "ocr_text": ocr_text[:2000], "question": question},
                    "image_ocr_analysis", self.llm)
                body = _message_text(resp)
                return {"status": "success",
                        "message": f"{note}\n\n{body}" if note else body,
                        "response_type": "image_analysis_ocr"}
            return {"status": "success",
                    "message": f"Image details:\n{summary}" + (f"\n\n({note})" if note else ""),
                    "response_type": "image_analysis_fallback"}
        except Exception as fallback_err:
            detail = f"{note} " if note else ""
            return {"status": "error",
                    "message": f"Image analysis failed: {detail}{fallback_err}".strip()}

    # ── FILE COMMANDS ───────────────────────────────────────────────────

    async def execute_file_command(self, command: str, parsed: Dict) -> Dict[str, Any]:
        try:
            filename = parsed.get("file_name") or ""
            if not filename or "." not in filename:
                return {"status": "error", "message": "Could not identify file. Include the filename with extension."}

            ft = filename.split(".")[-1].lower()
            base = filename.rsplit(".", 1)[0]

            if ft == "py":
                content = self._get_python_template(filename)
            elif ft == "html":
                content = self._get_html_template(filename)
            elif ft == "css":
                content = (
                    f"/* {filename} — Created by TOM */\n\n"
                    "*, *::before, *::after {\n  box-sizing: border-box;\n}\n\n"
                    "body {\n  margin: 0;\n  padding: 0;\n"
                    "  font-family: 'Segoe UI', Arial, sans-serif;\n"
                    "  color: #212529;\n  background: #f8f9fa;\n}\n\n"
                    "h1, h2, h3 {\n  margin: 0 0 0.5rem;\n}\n\n"
                    "a {\n  color: #0d6efd;\n  text-decoration: none;\n}\n"
                )
            elif ft == "js":
                content = (
                    f"// {filename} — Created by TOM\n\n"
                    "'use strict';\n\n"
                    "document.addEventListener('DOMContentLoaded', () => {\n"
                    "  console.log('TOM-generated script loaded');\n"
                    "});\n"
                )
            elif ft == "json":
                content = '{\n  "name": "' + base + '",\n  "version": "1.0.0",\n  "description": "Created by TOM"\n}\n'
            elif ft == "md":
                content = f"# {base}\n\n> Created by TOM\n\n## Overview\n\nDescribe the project here.\n\n## Usage\n\n```bash\n# Add your usage here\n```\n"
            elif ft == "txt":
                content = f"{base}\n{'=' * len(base)}\n\nCreated by TOM.\n"
            elif ft in ("ts", "tsx"):
                content = f"// {filename} — Created by TOM\n\nexport {{}};\n"
            elif ft in ("yaml", "yml"):
                content = f"# {filename} — Created by TOM\nname: {base}\nversion: '1.0'\n"
            elif ft in ("sh", "bash"):
                content = f"#!/usr/bin/env bash\n# {filename} — Created by TOM\nset -euo pipefail\n\necho 'Running {base}...'\n"
            else:
                content = f"# {filename}\n# Created by TOM\n"

            # Write into the workspace (or an explicit path), not the TOM repo.
            if os.path.isabs(os.path.expanduser(filename)):
                out_path = os.path.expanduser(filename)
            else:
                from tools.project_paths import workspace_root
                target = self._extract_target_dir(command)
                base = target if target else str(workspace_root())
                out_path = os.path.join(base, filename)
            result = await self.file_tools.write_file(out_path, content)
            if not result or result.get("status") != "success":
                err_detail = (result or {}).get("message", "unknown error")
                return {"status": "error", "message": f"Could not create {filename}: {err_detail}"}
            return {"status": "success", "message": f"Created {out_path} ({len(content)} bytes).",
                    "filename": out_path, "content_written": len(content)}
        except Exception as e:
            return {"status": "error", "message": f"File creation failed: {str(e)}"}

    async def execute_read_file_command(self, command: str) -> Dict[str, Any]:
        try:
            # Pattern 1: explicit keyword + optional "file" word + filename
            patterns = [
                r'(?:read|open|show(?:\s+me)?|display|cat|view)\s+(?:file\s+)?'
                r'([a-zA-Z0-9./\\\-_ ]+\.(?:py|html|css|txt|js|ts|json|md|yaml|yml|sh|bash|csv|log|ini|env|cfg|toml))',
                # Pattern 2: bare filename with extension (fallback)
                r'([a-zA-Z0-9./\\\-_]+\.(?:py|html|css|txt|js|ts|json|md|yaml|yml|sh|bash|csv|log|ini|env|cfg|toml))',
            ]
            file_path = None
            for pattern in patterns:
                match = re.search(pattern, command, re.IGNORECASE)
                if match:
                    candidate = match.group(1).strip()
                    if not os.path.isabs(candidate):
                        candidate = project_path_str(candidate)
                    # Prefer the match if file exists; take it even if not (user may give relative path)
                    file_path = candidate
                    if os.path.isfile(file_path):
                        break  # Confirmed file exists
            if not file_path:
                return {"status": "error", "message": "Could not identify file to read. Please include the filename."}
            result = await self.file_tools.read_file(file_path)
            if result and result.get("status") == "success":
                content = result.get("content", "")
                return {"status": "success",
                        "message": f"Contents of {os.path.basename(file_path)}:\n\n{content}",
                        "content": content, "file_path": file_path}
            return {"status": "error", "message": result.get("message", f"Could not read {file_path}.")}
        except Exception as e:
            return {"status": "error", "message": f"Failed to read file: {str(e)}"}

    # ── CHAT ────────────────────────────────────────────────────────────

    @staticmethod
    def _user_request_text(command: str) -> str:
        """The user's own words, without the desktop app's agent-mode preamble.

        In Email/Instagram Agent mode the app sends "You are Email Agent
        mode. ...\n\nUser request: <text>". The preamble names the agent, so
        matching plugins against the whole string ran that plugin for every
        message (inbox triage instead of "write an email to ...").
        """
        command = command or ""
        marker = "user request:"
        idx = command.lower().rfind(marker)
        return command[idx + len(marker):].strip() if idx >= 0 else command

    def _should_use_plugin_route(self, command_lower: str) -> bool:
        request = self._user_request_text(command_lower).lower()
        if not any(token in request for token in ("plugin", "agent", "run ", "execute ", "launch ")):
            return False
        return self.plugin_manager.match_plugin(request) is not None

    async def _handle_plugin_routed_task(self, command: str) -> Dict[str, Any]:
        request = self._user_request_text(command)
        plugin = self.plugin_manager.match_plugin(request)
        if not plugin:
            return {"status": "error", "message": "No matching plugin found."}

        lower = request.lower()
        args = []
        if "daemon" in lower or "background" in lower:
            args = ["--daemon"]
        elif plugin.name in {"email_agent", "instagram_ai_news_agent"}:
            args = ["--once"]

        result = await asyncio.to_thread(self.plugin_manager.execute_plugin, plugin.name, args)
        output = result.get("output") or result.get("message") or ""
        error = result.get("error") or ""
        message = f"Plugin `{plugin.name}` status: {result.get('status')}."
        if output:
            message += f"\n\nOutput:\n{output}"
        if error:
            message += f"\n\nError:\n{error}"
        return {
            "status": result.get("status", "unknown"),
            "message": message,
            "response_type": "plugin_route",
            "plugin": plugin.name,
            "plugin_result": result,
        }

    def _should_use_skill_route(self, route: RouteDecision, skill_route: SkillRoute, command_lower: str) -> bool:
        if not skill_route.matched:
            return False
        if route.category != "chat" or route.handler != "generate_chat_response":
            return False
        explicit = any(token in command_lower for token in (
            "skill", "using skill", "based on skill", "can tom", "can you",
            "how do i", "how to", "guide me", "explain", "build", "create",
            "design", "develop", "implement",
        ))
        return explicit or skill_route.confidence >= 0.45

    async def _handle_skill_routed_task(self, command: str, skill_route: SkillRoute) -> Dict[str, Any]:
        decision = self.capability_resolver.resolve(skill_route)
        memory_context = self._build_memory_context(command)
        prompt = self._safe_prompt([
            ("system", compose_system_prompt(
                "You are TOM executing a skill-routed task. Use the selected skill context as the primary source. "
                "Be direct. If the skill is guidance-only or external-tool-backed, state that truth and provide the usable path. "
                "If local tools are available, give implementation-level steps or code-ready output. No emoji.",
                "TOM",
                include_ui=True,
            )),
            ("human",
             "User request:\n{command}\n\n"
             "Capability decision:\n{capability}\n\n"
             "Relevant memory:\n{memory}\n\n"
             "Selected skill context:\n{skill_context}\n\n"
             "Return the best usable response."),
        ])
        payload = self._escape_braces({
            "command": command,
            "capability": (
                f"status={decision.status}; skill={decision.skill_name}; "
                f"reason={decision.reason}; required_tools={', '.join(decision.required_tools) or 'none'}"
            ),
            "memory": memory_context,
            "skill_context": skill_route.context,
        })
        resp = await self._invoke_llm(
            prompt,
            payload,
            "skill_route",
            self.llm,
        )
        message = resp.content if hasattr(resp, "content") else str(resp)
        message = re.sub(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0E\uFE0F]", "", message)
        return {
            "status": "success",
            "message": message.strip(),
            "response_type": "skill_route",
            "skill": skill_route.skill_name,
            "skill_confidence": skill_route.confidence,
            "capability_status": decision.status,
            "required_tools": decision.required_tools,
        }

    async def generate_chat_response(self, command: str) -> Dict[str, Any]:
        # For short casual messages, skip expensive RAG retrieval
        if len(command.split()) <= 8:
            memory_context = self.chat_memory.build_context(
                query=command, recent_n=10, relevant_n=0, max_chars=2000)
        else:
            memory_context = self._build_memory_context(command)

        # Base personality — potentially enriched by evolution adaptive prompt
        chat_system = (
            "You are TOM, the user's personal AI assistant running on their Windows laptop. "
            "You have REAL capabilities: image/vision analysis (attach images via the button), "
            "camera capture, screen reading, document creation (Word/Excel/PPT/PDF), "
            "email, WhatsApp, web search, file analysis, voice mode, and app launching. "
            "You also have specialized engines reachable by plain language: ML training "
            "(regression/classification/clustering/forecasting), IoT firmware generation "
            "(ESP32/Arduino/MicroPython), VLSI/Verilog/RTL design, hardware control "
            "(mouse/keyboard/volume), game-dev scaffolding, Blender 3D, news briefings, "
            "Python environment management, autonomous multi-step tasks, and multi-agent "
            "orchestration. "
            "When asked if you can do something, say YES and explain how. "
            "Never say you cannot analyze images or files — you CAN. "
            "Keep replies short and natural — 1-3 sentences for casual chat. "
            "Be friendly, direct, and concise. Talk like a helpful friend."
        )
        if self.evolution:
            try:
                adaptive = self.evolution.get_adaptive_system_prompt()
                if adaptive:
                    chat_system = chat_system + "\n\n" + adaptive
                hints = self.evolution.get_approach_hints("general_chat")
                if hints:
                    chat_system = chat_system + f"\n\nLearned hint: {hints}"
            except Exception:
                pass

        prompt = self._safe_prompt([
            ("system", chat_system),
            ("user", "Conversation memory:\n{memory}\n\nUser says:\n{message}"),
        ])
        resp = await self._invoke_llm(prompt, {"message": command, "memory": memory_context}, "chat", self.chat_llm)
        return {"status": "success", "message": resp.content.strip(), "response_type": "chat"}

    async def generate_voice_response(self, command: str) -> Dict[str, Any]:
        command_lower = command.lower().strip()
        # If action request — or anything about memory/preferences — use the full pipeline
        if any(k in command_lower for k in ("open ", "send ", "create ", "write ", "make ",
                                              "email ", "whatsapp", "analyze", "search",
                                              "launch ", "start ", "read ", "show ",
                                              "organize", "organise", "tidy", "clean up",
                                              "remember", "learned", "learnt")) or \
                memory_rules.is_preference_statement(command):
            result = await self.execute_task(command)
            raw = result.get("message", "")
            result["message"] = self._strip_for_speech(raw)
            return result

        self._recalled = await self.memory.arecall(command, limit=5) if self.memory.available else []
        memory_context = self._build_memory_context(command)
        voice_system = (
            "You are TOM in VOICE mode. Keep responses under 2-3 sentences. "
            "Sound natural and warm. No markdown, no bullet points. "
            "Just plain spoken English. Talk like a smart friend."
        )
        prompt = self._safe_prompt([
            ("system", voice_system),
            ("user", "Memory:\n{memory}\n\nUser said:\n{message}"),
        ])
        resp = await self._invoke_llm(prompt, {"message": command, "memory": memory_context}, "voice", self.fast_llm)
        spoken = self._strip_for_speech(resp.content.strip())
        try:
            self.chat_memory.append("user", command)
            self.chat_memory.append("assistant", spoken)
        except Exception:
            pass
        return {"status": "success", "message": spoken, "response_type": "voice_chat"}

    @staticmethod
    def _strip_for_speech(text: str) -> str:
        import re
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'`(.+?)`', r'\1', text)
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    async def execute_code_help(self, command: str) -> Dict[str, Any]:
        memory_context = self._build_memory_context(command)
        prompt = self._safe_prompt([
            ("system", compose_system_prompt(
                "You are TOM, a coding assistant. Help fix code by explaining the root cause "
                "and providing the corrected code. Be practical and concise.", "TOM", include_ui=False)),
            ("user", "Memory:\n{memory}\n\nIssue: {message}"),
        ])
        resp = await self._invoke_llm(prompt, {"message": command, "memory": memory_context}, "code_help", self.code_llm)
        return {"status": "success", "message": resp.content.strip(), "response_type": "code_help"}

    async def plan_task(self, user_request: str) -> Dict[str, Any]:
        memory_context = self._build_memory_context(user_request)
        prompt = self._safe_prompt([
            ("system", self.get_system_prompt()),
            ("user", "Memory:\n{memory}\n\nTask: {request}\n\nPlan concrete steps. Prefer action over questions."),
        ])
        resp = await self._invoke_llm(prompt, {"request": user_request, "memory": memory_context}, "plan")
        return {"plan": resp.content, "status": "planned"}

    async def give_reward(self, experience_id: int, amount: float) -> Dict[str, Any]:
        try:
            ok = await asyncio.to_thread(self.learner.give_reward, experience_id, amount)
            if ok:
                self.safety.log_action("REWARD", target=str(experience_id), status="SUCCESS",
                                       message=f"Reward {amount}")
                return {"status": "success", "message": f"Reward {amount} applied to {experience_id}"}
            return {"status": "error", "message": "Experience id not found"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def revise_response_with_feedback(self, user_command: str, previous_response: str,
                                             feedback: str) -> Dict[str, Any]:
        memory_context = self._build_memory_context(user_command)
        prompt = self._safe_prompt([
            ("system", "You are TOM. Improve your previous response using user feedback. "
                       "Return only the revised response."),
            ("user", "Memory:\n{memory}\n\nOriginal: {user_command}\n\n"
                     "Previous response: {prev}\n\nFeedback: {fb}\n\nBetter response:"),
        ])
        resp = await self._invoke_llm(
            prompt,
            {"memory": memory_context, "user_command": user_command,
             "prev": previous_response, "fb": feedback},
            "revise",
        )
        revised = resp.content.strip()
        try:
            self.chat_memory.append("assistant", revised)
            self.learner.log_experience(
                f"revise_response {user_command[:80]}", "success",
                {"feedback": feedback, "revised_message": revised},
            )
        except Exception:
            pass
        return {"status": "success", "message": revised, "response_type": "revised"}

    def _logs_response(self, lines: int = 40) -> Dict[str, Any]:
        """Tail the safety/action log so users can see recent activity in-app."""
        try:
            log_path = self.safety.log_file
            if not os.path.isfile(log_path):
                return {"status": "success", "response_type": "logs",
                        "message": "No activity logged yet this session."}
            with open(log_path, encoding="utf-8", errors="ignore") as f:
                tail = f.readlines()[-lines:]
            text = "".join(tail)[-3500:]
            # PRIVACY: mask emails / long digit runs (phones, card-like) in the
            # surfaced tail — the raw file on disk is unchanged.
            text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "<email>", text)
            text = re.sub(r"(?<!\d)\d{8,}(?!\d)", "<number>", text)
            return {"status": "success", "response_type": "logs",
                    "message": f"Last {len(tail)} log entries (PII masked):\n" + text}
        except Exception as e:
            return {"status": "error", "message": f"Could not read logs: {e}"}

    async def _universal_task_attempt(self, command: str, parsed: Dict) -> Dict[str, Any]:
        """A1: attempt unmatched task-like commands via the autonomous loop.
        A4: on failure, fall back to chat plus ONE targeted clarifying question."""
        safe_print("[UNIVERSAL] No concrete handler matched — attempting autonomous execution...")
        try:
            res = await asyncio.wait_for(
                self.engine_router._run_autonomous(command),
                timeout=max(60, self.task_timeout_seconds - 20),
            )
            if res.get("status") == "success" and (res.get("message") or "").strip():
                res["response_type"] = "universal_task"
                res["message"] = "[Attempted as autonomous task]\n" + res["message"]
                return res
        except asyncio.TimeoutError:
            self.safety.log_action("WARN", target="universal", status="FAILURE",
                                   message="universal attempt timed out")
        except Exception as _ue:
            self.safety.log_action("WARN", target="universal", status="FAILURE",
                                   message=f"universal attempt failed: {_ue}")
        chat = await self.generate_chat_response(command)
        question = await self._clarify_question(command)
        if question:
            chat["message"] = (str(chat.get("message", "")).rstrip()
                               + f"\n\nTo actually execute this, one detail would help: {question}")
        chat["response_type"] = "universal_fallback_chat"
        return chat

    async def _clarify_question(self, command: str) -> str:
        """A4: generate exactly one short unblock question. '' on any failure."""
        try:
            prompt = self._safe_prompt([
                ("system",
                 "You are TOM. The user gave a task you could not fully execute. "
                 "Ask exactly ONE short, specific question whose answer would let you "
                 "do it (a file path, app name, account, or target). Reply with only "
                 "the question."),
                ("human", "{command}"),
            ])
            resp = await self._invoke_llm(
                prompt, self._escape_braces({"command": command}), "clarify", self.fast_llm)
            q = (resp.content if hasattr(resp, "content") else str(resp)).strip()
            return q[:200] if q and "?" in q else ""
        except Exception:
            return ""

    # ── Phase B4: schedule ANY task from chat ───────────────────────────
    def schedule_user_task(self, command: str, hours: float) -> Dict[str, Any]:
        """Run `command` through execute_task every N hours (until restart)."""
        import json as _json
        import threading as _th
        from tools.scheduler import get_scheduler
        if hours <= 0 or hours > 720:
            return {"status": "error", "message": "Interval must be between 0 and 720 hours."}
        job_id = "user_" + re.sub(r"[^a-z0-9]+", "_", command.lower())[:40].strip("_")

        def _job(cmd=command):
            def _runner():
                try:
                    asyncio.run(self.execute_task(cmd))
                except Exception as _e:
                    self.safety.log_action("WARN", target="scheduled_task",
                                           status="FAILURE", message=str(_e))
            _th.Thread(target=_runner, daemon=True, name=f"sched-{job_id}").start()

        sched = get_scheduler()
        sched.start()
        whole_h = int(hours)
        mins = int(round((hours - whole_h) * 60))
        sched.schedule_interval_task(job_id, _job, hours=whole_h, minutes=mins)
        # Persist a registry of user schedules (informational; jobs re-register
        # on demand — surviving restarts ships in Phase C).
        try:
            reg_path = os.path.join(os.getcwd(), "tom_logs", "scheduled_user_tasks.json")
            entries = {}
            if os.path.isfile(reg_path):
                with open(reg_path, encoding="utf-8") as f:
                    entries = _json.load(f)
            entries[job_id] = {"command": command, "every_hours": hours}
            with open(reg_path, "w", encoding="utf-8") as f:
                _json.dump(entries, f, indent=1)
        except Exception:
            pass
        return {"status": "success", "response_type": "schedule",
                "job_id": job_id,
                "message": f"Scheduled: \"{command}\" every {hours:g} hour(s) "
                           f"(job: {job_id}). Note: schedules last until TOM restarts; "
                           f"say 'list scheduled tasks' or 'unschedule {job_id}'."}

    def unschedule_user_task(self, job_ref: str) -> Dict[str, Any]:
        from tools.scheduler import get_scheduler
        ok = get_scheduler().unschedule_task(job_ref.strip())
        return {"status": "success" if ok else "not_found", "response_type": "schedule",
                "message": ("Unscheduled: " + job_ref) if ok else f"No job named '{job_ref}'."}

    def list_user_tasks(self) -> Dict[str, Any]:
        from tools.scheduler import get_scheduler
        jobs = get_scheduler().get_scheduled_jobs()
        if not jobs:
            return {"status": "success", "response_type": "schedule",
                    "message": "No scheduled tasks right now."}
        lines = [f"  - {jid}: {info}" for jid, info in jobs.items()]
        return {"status": "success", "response_type": "schedule",
                "message": "Scheduled tasks:\n" + "\n".join(lines)}

    def _capabilities_response(self) -> Dict[str, Any]:
        """Registry-backed capability listing (single source of truth)."""
        try:
            from tools.capability_registry import summary_text, validate
            v = validate()
            header = (f"All {v['total']} capabilities verified against real executors.\n\n"
                      if v["ok"] else
                      f"WARNING: {len(v['missing'])} capability mappings broken!\n\n")
            return {"status": "success", "response_type": "capabilities",
                    "message": header + summary_text()}
        except Exception as e:
            return {"status": "error", "message": f"Capability registry unavailable: {e}"}

    def _health_response(self) -> Dict[str, Any]:
        """Live subsystem health — ends silent degradation."""
        checks = []
        def _line(name, ok, detail=""):
            checks.append(f"  [{'ONLINE ' if ok else 'OFFLINE'}] {name}" + (f" — {detail}" if detail else ""))
        _line("LLM config", True, f"{self.model_name} / code: {self.code_model_name}")
        _line("RAG semantic memory", bool(self.rag and getattr(self.rag, 'available', False)))
        _line("Self-evolution", bool(self.evolution))
        _line("MCP connectors", bool(self.mcp))
        _line("Multi-agent orchestrator", bool(self.orchestrator))
        _line("Web automation", bool(self.web_automation))
        _line("Engine router", bool(getattr(self, 'engine_router', None)),
              "ML/IoT/VLSI/HW/Blender/GameDev/News/Env/Code-run")
        kn = getattr(self, "knowledge", None)
        try:
            ks = kn.get_stats() if kn else {}
            _line("Curated knowledge", bool(kn),
                  f"{ks.get('domains', 0)} domains, {ks.get('total_sections', 0)} sections")
        except Exception:
            _line("Curated knowledge", False)
        try:
            _line("Skills", True, f"{self.skill_manager.count_skills()} loaded "
                  f"(external {'ON' if self.skill_manager.include_external else 'off — set TOM_INCLUDE_EXTERNAL_SKILLS=1'})")
        except Exception:
            _line("Skills", False)
        _line("Plugins", True, f"{len(self.available_plugins or [])} discovered")
        offline = sum(1 for c in checks if "OFFLINE" in c)
        head = "All subsystems online." if offline == 0 else f"{offline} subsystem(s) OFFLINE — features degrade gracefully."
        # Dependency preflight: exact missing deps + the command that fixes each.
        try:
            from tools.preflight import report_text
            preflight = report_text()
        except Exception as _pf:
            preflight = f"(preflight unavailable: {_pf})"
        return {"status": "success", "response_type": "health",
                "message": (f"TOM system health:\n{head}\n\n" + "\n".join(checks)
                            + "\n\n" + preflight)}

    def get_skills_summary(self) -> Dict[str, Any]:
        try:
            return self.learner.summarize_skills()
        except Exception:
            return {"skills": []}

    def _get_python_template(self, filename: str) -> str:
        name = filename.replace(".py", "")
        return (
            f"# {filename}\nimport asyncio\n\n"
            f"async def main():\n    print('Hello from {name}')\n\n"
            f"if __name__ == '__main__':\n    asyncio.run(main())\n"
        )

    def _get_html_template(self, filename: str) -> str:
        title = filename.replace(".html", "")
        return (
            "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
            "    <meta charset=\"UTF-8\">\n"
            "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
            f"    <title>{title}</title>\n"
            "</head>\n<body>\n"
            f"    <h1>Welcome to {title}</h1>\n"
            "    <p>Created by TOM.</p>\n"
            "</body>\n</html>\n"
        )

    # ── INSTAGRAM ───────────────────────────────────────────────────────

    async def execute_instagram_workflow(self, command: str = None) -> Dict[str, Any]:
        try:
            from agents.instagram_ai_news_agent.main import InstagramAINNewsAgent
            safe_print("\n" + "=" * 60)
            safe_print("INSTAGRAM AI NEWS WORKFLOW")
            safe_print("=" * 60)
            agent = InstagramAINNewsAgent()
            result = await agent.run_workflow()
            status = "success" if result["success"] else "incomplete"
            msg = (f"Instagram workflow: {result['posts_extracted']} posts, "
                   f"{result['ai_posts_found']} AI posts.")
            if result.get("report_path"):
                safe_print(f"Report: {result['report_path']}")
            return {"status": status, "message": msg, "workflow_result": result}
        except ImportError as e:
            return {"status": "error", "message": f"Instagram agent not found: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"Instagram workflow failed: {str(e)}"}

    def schedule_instagram_reports(self, interval_hours: int = 3) -> Dict[str, Any]:
        """Schedule the Instagram AI-news workflow to run every N hours."""
        try:
            scheduler = get_scheduler()
            jobs = scheduler.get_scheduled_jobs()
            if "instagram_ai_news" in jobs:
                return {"status": "already_scheduled",
                        "message": f"Already scheduled every {interval_hours}h"}

            def run_task():
                # Run the async workflow in its own thread with its own event loop,
                # avoiding RuntimeError if called from within an already-running loop.
                import threading
                result_holder = {}

                def _thread_target():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result_holder["result"] = loop.run_until_complete(
                            self.execute_instagram_workflow()
                        )
                    except Exception as exc:
                        result_holder["result"] = {"status": "error", "message": str(exc)}
                    finally:
                        loop.close()

                thread = threading.Thread(target=_thread_target, daemon=True)
                thread.start()
                thread.join()
                return result_holder.get("result", {"status": "error", "message": "No result produced"})

            job_id = scheduler.schedule_interval_task(
                "instagram_ai_news", run_task,
                hours=interval_hours, replace_existing=True,
            )
            return {"status": "scheduled",
                    "message": f"Instagram reports scheduled every {interval_hours}h",
                    "job_id": job_id}
        except Exception as e:
            return {"status": "error", "message": f"Failed to schedule Instagram reports: {str(e)}"}

    def unschedule_instagram_reports(self) -> Dict[str, Any]:
        """Stop the scheduled Instagram AI-news workflow."""
        try:
            scheduler = get_scheduler()
            result = scheduler.unschedule_task("instagram_ai_news")
            if result:
                return {"status": "success", "message": "Instagram reports unscheduled"}
            return {"status": "not_found", "message": "No scheduled Instagram reports found"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to unschedule Instagram reports: {str(e)}"}
