# This file makes 'tools' a package.
#
# Imports are LAZY (PEP 562). Importing a single submodule -- e.g.
# `from tools.command_router import CommandRouter` -- must NOT drag in heavy,
# optional dependencies (playwright, google API libs, pygame, ...) via this
# __init__. Eagerly importing them here previously meant that a single missing
# optional dependency made the entire `tools` package unimportable, which broke
# app startup. With lazy loading, `tools.OSTools` etc. still work, but the heavy
# module is only imported the first time that name is actually accessed.
import importlib

_LAZY_EXPORTS = {
    "OSTools": "tools.os_tools",
    "BrowserTools": "tools.browser_tools",
    "FileTools": "tools.file_tools",
    "EmailTools": "tools.email_tools",
    "VoiceTools": "tools.voice_tools",
    "NewsAgent": "tools.news_agent",
    "GameDevEngine": "tools.game_dev",
    "BlenderControl": "tools.blender_control",
    "AutoUpdate": "tools.auto_update",
}

__all__ = list(_LAZY_EXPORTS)


def __getattr__(name: str):
    """Lazily import and return a public tool class on first access."""
    module_path = _LAZY_EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module 'tools' has no attribute {name!r}")
    module = importlib.import_module(module_path)
    return getattr(module, name)


def __dir__():
    return sorted(set(list(globals().keys()) + __all__))
