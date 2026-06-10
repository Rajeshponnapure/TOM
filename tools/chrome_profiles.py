from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class ChromeProfile:
    name: str
    directory: str
    path: str
    is_default: bool = False


class ChromeProfileManager:
    """Detects and launches Chrome profiles on Windows."""

    def __init__(self, chrome_executable: Optional[str] = None, user_data_dir: Optional[str] = None):
        self.chrome_executable = chrome_executable or self._find_chrome_executable()
        self.user_data_dir = user_data_dir or self._default_user_data_dir()

    def _default_user_data_dir(self) -> str:
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        return os.path.join(local_app_data, "Google", "Chrome", "User Data") if local_app_data else ""

    def _find_chrome_executable(self) -> str:
        candidates = [
            os.path.join(os.environ.get("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
        ]
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate
        return "chrome.exe"

    def discover_profiles(self) -> List[ChromeProfile]:
        profiles: List[ChromeProfile] = []
        if not self.user_data_dir or not os.path.isdir(self.user_data_dir):
            return profiles

        display_names: Dict[str, str] = {}
        local_state = os.path.join(self.user_data_dir, "Local State")
        if os.path.exists(local_state):
            try:
                with open(local_state, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                display_names = {
                    key: str(value.get("name", key))
                    for key, value in data.get("profile", {}).get("info_cache", {}).items()
                    if isinstance(value, dict)
                }
            except Exception:
                display_names = {}

        for entry in sorted(os.listdir(self.user_data_dir)):
            profile_dir = os.path.join(self.user_data_dir, entry)
            if not os.path.isdir(profile_dir):
                continue
            if not (entry == "Default" or entry.startswith("Profile")):
                continue

            profiles.append(
                ChromeProfile(
                    name=display_names.get(entry, entry),
                    directory=entry,
                    path=profile_dir,
                    is_default=entry == "Default",
                )
            )

        return profiles

    def find_profile(self, query: str) -> Optional[ChromeProfile]:
        normalized = (query or "").strip().lower()
        if not normalized:
            return None

        for profile in self.discover_profiles():
            if profile.name.lower() == normalized or profile.directory.lower() == normalized:
                return profile

        for profile in self.discover_profiles():
            if normalized in profile.name.lower() or normalized in profile.directory.lower():
                return profile

        return None

    def launch_profile(self, profile_query: str = "", url: str = "") -> Dict[str, Any]:
        if not self.chrome_executable:
            return {"status": "error", "message": "Chrome executable was not found"}

        profile = self.find_profile(profile_query) if profile_query else None
        profile_directory = profile.directory if profile else "Default"

        args = [
            self.chrome_executable,
            f"--user-data-dir={self.user_data_dir}",
            f"--profile-directory={profile_directory}",
        ]
        if url:
            args.append(url)

        try:
            subprocess.Popen(args)
            profile_name = profile.name if profile else profile_directory
            return {
                "status": "success",
                "message": f"Launched Chrome profile '{profile_name}'",
                "profile_directory": profile_directory,
                "url": url,
            }
        except Exception as exc:
            return {"status": "error", "message": f"Failed to launch Chrome profile: {exc}"}
