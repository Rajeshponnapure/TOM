from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from tools.project_paths import PROJECT_ROOT


@dataclass(slots=True)
class PluginInfo:
    name: str
    path: str
    entrypoint: Optional[str] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class PluginManager:
    """Discovers simple TOM plugins and generated agent folders.

    The project already uses `agents/<name>/main.py` as a natural extension
    point. This manager formalizes that layout so future automation modules can
    be loaded, listed, or registered without changing the core agent.
    """

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or str(PROJECT_ROOT)
        self.plugin_roots = [
            os.path.join(self.workspace_root, "agents"),
            os.path.join(self.workspace_root, "plugins"),
        ]

    def discover_plugins(self) -> List[PluginInfo]:
        plugins: List[PluginInfo] = []
        for root in self.plugin_roots:
            if not os.path.isdir(root):
                continue
            for entry in sorted(os.listdir(root)):
                candidate = os.path.join(root, entry)
                if not os.path.isdir(candidate):
                    continue

                main_path = os.path.join(candidate, "main.py")
                readme_path = os.path.join(candidate, "README.md")
                manifest_path = os.path.join(candidate, "plugin.json")
                metadata: Dict[str, Any] = {}
                description = ""

                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, "r", encoding="utf-8") as handle:
                            metadata = json.load(handle)
                        description = str(metadata.get("description", ""))
                    except Exception:
                        metadata = {}

                if not description and os.path.exists(readme_path):
                    try:
                        with open(readme_path, "r", encoding="utf-8") as handle:
                            description = handle.readline().strip()
                    except Exception:
                        description = ""

                plugins.append(
                    PluginInfo(
                        name=entry,
                        path=candidate,
                        entrypoint=main_path if os.path.exists(main_path) else None,
                        description=description,
                        metadata=metadata,
                    )
                )
        return plugins

    def describe_plugins(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": plugin.name,
                "path": plugin.path,
                "entrypoint": plugin.entrypoint,
                "description": plugin.description,
                "metadata": plugin.metadata,
            }
            for plugin in self.discover_plugins()
        ]

    def load_plugin_module(self, plugin_name: str):
        for plugin in self.discover_plugins():
            if plugin.name != plugin_name or not plugin.entrypoint:
                continue
            module_name = f"tom_plugin_{plugin.name}"
            spec = importlib.util.spec_from_file_location(module_name, plugin.entrypoint)
            if spec is None or spec.loader is None:
                raise ImportError(f"Unable to load plugin: {plugin_name}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        raise FileNotFoundError(f"Plugin not found: {plugin_name}")

    def match_plugin(self, command: str) -> Optional[PluginInfo]:
        text = (command or "").lower()
        if not text:
            return None
        for plugin in self.discover_plugins():
            name_text = plugin.name.replace("_", " ").replace("-", " ")
            aliases = {plugin.name.lower(), name_text}
            if plugin.metadata:
                aliases.update(str(x).lower() for x in plugin.metadata.get("aliases", []) if x)
            if plugin.description:
                aliases.add(plugin.description.lower())
            if any(alias and alias in text for alias in aliases):
                return plugin
        return None

    def execute_plugin(self, plugin_name: str, args: Optional[List[str]] = None,
                       timeout: int = 180) -> Dict[str, Any]:
        plugin = next((p for p in self.discover_plugins() if p.name == plugin_name), None)
        if not plugin:
            return {"status": "error", "message": f"Plugin not found: {plugin_name}"}
        if not plugin.entrypoint:
            return {"status": "error", "message": f"Plugin has no main.py entrypoint: {plugin_name}"}

        cmd = [sys.executable, plugin.entrypoint]
        if args:
            cmd.extend(args)
        try:
            proc = subprocess.run(
                cmd,
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "status": "success" if proc.returncode == 0 else "error",
                "plugin": plugin.name,
                "returncode": proc.returncode,
                "output": proc.stdout.strip()[:4000],
                "error": proc.stderr.strip()[:2000],
            }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "plugin": plugin.name, "message": f"Plugin timed out after {timeout}s"}
        except Exception as exc:
            return {"status": "error", "plugin": plugin.name, "message": str(exc)}
