import asyncio
import subprocess
import os
import shutil
import sys
import time
import glob as _glob
import re as _re
import logging
from typing import Optional, Dict, Any, List
from tools.project_paths import project_path_str

logger = logging.getLogger(__name__)


def _run_ps(script: str, timeout: int = 10) -> str:
    """Run a short PowerShell snippet and return stdout."""
    try:
        kwargs = {"capture_output": True, "text": True, "timeout": timeout}
        if os.name == "nt":
            # TOM invokes these short discovery commands from the desktop UI.
            # Never create a visible terminal for an internal background check.
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            **kwargs,
        )
        return proc.stdout.strip()
    except Exception:
        return ""


class OSTools:
    """Handles opening applications and system interactions safely.

    Key improvement: dynamic app discovery — TOM can find and launch ANY
    application installed on the laptop instead of relying on hardcoded paths.
    """

    def __init__(self):
        self.config_dir = project_path_str("config")
        os.makedirs(self.config_dir, exist_ok=True)
        self._app_cache: Dict[str, str] = {}

    # ── Dynamic App Discovery ────────────────────────────────────────────────

    def find_application(self, query: str) -> Optional[str]:
        """Search the entire system for an application matching *query*.

        Returns the launch command/path, or None if not found.
        Search order (first match wins):
        1. Cached previous lookup
        2. Start Menu shortcuts (.lnk)
        3. UWP / Store apps via shell:AppsFolder
        4. Common install directories scan
        5. Windows PATH (where.exe)
        6. Windows Registry uninstall keys
        """
        q = query.lower().strip()
        if q in self._app_cache:
            return self._app_cache[q]

        if os.name != "nt":
            result = self._find_application_posix(q)
            if result:
                self._app_cache[q] = result
            return result

        result = (
            self._search_start_menu(q)
            or self._search_uwp_apps(q)
            or self._search_program_dirs(q)
            or self._search_path(q)
            or self._search_registry(q)
        )

        if result:
            self._app_cache[q] = result
        return result

    # ── Linux / macOS discovery ──────────────────────────────────────────────

    @staticmethod
    def _desktop_dirs() -> List[str]:
        home = os.path.expanduser("~")
        return [
            "/usr/share/applications", "/usr/local/share/applications",
            os.path.join(home, ".local/share/applications"),
            "/var/lib/flatpak/exports/share/applications",
            os.path.join(home, ".local/share/flatpak/exports/share/applications"),
            "/var/lib/snapd/desktop/applications",
        ]

    @staticmethod
    def _desktop_name(path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                in_entry = False
                for line in handle:
                    line = line.strip()
                    if line.startswith("["):
                        in_entry = line == "[Desktop Entry]"
                    elif in_entry and line.startswith("Name="):
                        return line[5:].strip()
        except OSError:
            pass
        return ""

    def _find_application_posix(self, query: str) -> Optional[str]:
        """macOS: an .app bundle. Linux: an executable on PATH, else a .desktop entry.

        Returns 'mac:<bundle>', 'desktop:<file>' or a plain executable path.
        """
        if sys.platform == "darwin":
            for base in ("/Applications", "/System/Applications", os.path.expanduser("~/Applications")):
                if os.path.isdir(base):
                    for name in sorted(os.listdir(base)):
                        if name.lower().endswith(".app") and query in name[:-4].lower():
                            return "mac:" + os.path.join(base, name)
            return shutil.which(query.replace(" ", "-")) or shutil.which(query)
        on_path = shutil.which(query) or shutil.which(query.replace(" ", "-"))
        if on_path:
            return on_path
        for base in self._desktop_dirs():
            if not os.path.isdir(base):
                continue
            for name in sorted(os.listdir(base)):
                if not name.endswith(".desktop"):
                    continue
                path = os.path.join(base, name)
                if query in name[:-8].lower() or query in self._desktop_name(path).lower():
                    return "desktop:" + path
        return None

    @staticmethod
    def _launch(cmd: List[str]) -> Optional[str]:
        """Start a program; return None on success or the reason it failed.

        Popen succeeding only means the process was created, so also look for an
        immediate non-zero exit (bad path, missing runtime) before claiming success.
        """
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as exc:
            return str(exc)
        time.sleep(0.6)
        code = proc.poll()
        if code not in (None, 0):
            return f"exited immediately with code {code}"
        return None

    def _launch_posix(self, target: str) -> Optional[str]:
        if target.startswith("mac:"):
            return self._launch(["open", target[4:]])
        if target.startswith("desktop:"):
            path = target[8:]
            base = os.path.basename(path)[:-8]
            for tool in (["gtk-launch", base], ["gio", "launch", path]):
                if shutil.which(tool[0]):
                    return self._launch(tool)
            return "no launcher (gtk-launch/gio) is installed to start a desktop entry"
        return self._launch([target])

    def _search_start_menu(self, query: str) -> Optional[str]:
        """Scan Start Menu .lnk files for a matching app."""
        search_dirs = [
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        ]
        for base in search_dirs:
            if not os.path.isdir(base):
                continue
            for root, _dirs, files in os.walk(base):
                for f in files:
                    if not f.lower().endswith(".lnk"):
                        continue
                    name_lower = f[:-4].lower()
                    if query in name_lower or name_lower in query:
                        return os.path.join(root, f)
        return None

    def _search_uwp_apps(self, query: str) -> Optional[str]:
        """Find UWP / Microsoft Store apps using Get-StartApps."""
        ps = f'Get-StartApps | Where-Object {{ $_.Name -like "*{query}*" }} | Select-Object -First 1 -ExpandProperty AppID'
        app_id = _run_ps(ps)
        if app_id:
            return f"shell:AppsFolder\\{app_id}"
        return None

    def _search_program_dirs(self, query: str) -> Optional[str]:
        """Scan common install directories for executables matching query."""
        scan_roots = [
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
            os.path.expandvars(r"%LOCALAPPDATA%"),
        ]
        for root in scan_roots:
            if not os.path.isdir(root):
                continue
            try:
                for entry in os.scandir(root):
                    if not entry.is_dir():
                        continue
                    if query in entry.name.lower():
                        for sub_root, _d, sub_files in os.walk(entry.path):
                            for sf in sub_files:
                                if sf.lower().endswith(".exe") and query in sf.lower():
                                    return os.path.join(sub_root, sf)
                            # Only go 3 levels deep
                            depth = sub_root.replace(entry.path, "").count(os.sep)
                            if depth >= 3:
                                break
            except PermissionError:
                continue
        return None

    def _search_path(self, query: str) -> Optional[str]:
        """Use where.exe to find an executable on PATH."""
        try:
            proc = subprocess.run(
                ["where.exe", f"*{query}*.exe"],
                capture_output=True, text=True, timeout=5,
            )
            if proc.returncode == 0:
                first_line = proc.stdout.strip().splitlines()[0]
                if os.path.isfile(first_line):
                    return first_line
        except Exception:
            pass
        return None

    def _search_registry(self, query: str) -> Optional[str]:
        """Search Windows Registry uninstall keys for the app's install location."""
        ps = (
            f'$keys = @("HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*",'
            f'"HKLM:\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*",'
            f'"HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*");'
            f'Get-ItemProperty $keys 2>$null | '
            f'Where-Object {{ $_.DisplayName -like "*{query}*" }} | '
            f'Select-Object -First 1 -ExpandProperty InstallLocation'
        )
        install_loc = _run_ps(ps, timeout=8)
        if install_loc and os.path.isdir(install_loc):
            for f in os.listdir(install_loc):
                if f.lower().endswith(".exe") and query in f.lower():
                    return os.path.join(install_loc, f)
            # If no exact match, grab the first .exe
            for f in os.listdir(install_loc):
                if f.lower().endswith(".exe"):
                    return os.path.join(install_loc, f)
        return None

    def list_installed_apps(self, filter_query: str = "") -> List[Dict[str, str]]:
        """Return a list of installed applications (name + path) for discovery."""
        ps = 'Get-StartApps | Select-Object Name, AppID | ConvertTo-Csv -NoTypeInformation'
        raw = _run_ps(ps, timeout=15)
        apps = []
        for line in raw.splitlines()[1:]:  # skip CSV header
            parts = line.strip('"').split('","')
            if len(parts) >= 2:
                name, app_id = parts[0], parts[1]
                if filter_query and filter_query.lower() not in name.lower():
                    continue
                apps.append({"name": name, "app_id": app_id})
        return apps

    # ── Open Application ─────────────────────────────────────────────────────

    async def open_application(self, app_name: str, profile_id: Optional[str] = None) -> Dict[str, Any]:
        """Open any installed application by name using dynamic discovery."""
        result = {
            "action": "open_app",
            "app": app_name,
            "status": "success",
            "message": ""
        }

        app_lower = app_name.lower().strip()

        # Chrome with profile gets special handling
        if "chrome" in app_lower and profile_id:
            if os.name == "nt":
                chrome_path = self.find_application("chrome") or "chrome.exe"
            else:
                chrome_path = next((shutil.which(n) for n in ("google-chrome", "google-chrome-stable", "chromium",
                                                                 "chromium-browser", "chrome") if shutil.which(n)),
                                   "google-chrome")
            # SECURITY: argument list, no shell — profile_id cannot inject a command.
            # Also constrain profile_id to Chrome's real format (Default / Profile N).
            safe_profile = _re.sub(r"[^A-Za-z0-9 _-]", "", str(profile_id))[:64] or "Default"
            cmd = [chrome_path, f"--profile-directory={safe_profile}"]
            try:
                subprocess.Popen(cmd)
                result["message"] = f"Opened Chrome with profile: {profile_id}"
            except Exception as e:
                result["status"] = "error"
                result["message"] = f"Failed to open Chrome with profile: {e}"
            self.log_action(result)
            return result

        # Dynamic discovery for any app
        launch_path = self.find_application(app_lower)

        if launch_path and os.name != "nt":
            problem = await asyncio.to_thread(self._launch_posix, launch_path)
            if problem:
                result["status"] = "error"
                result["message"] = f"Found {app_name} ({launch_path}) but could not launch it: {problem}"
            else:
                result["message"] = f"Opened {app_name} ({launch_path})"
        elif os.name != "nt":
            result["status"] = "error"
            result["message"] = (f"Could not find '{app_name}' on this computer. "
                                 f"Searched: PATH and installed application entries.")
        elif launch_path:
            try:
                if launch_path.startswith("shell:AppsFolder"):
                    subprocess.Popen(
                        ["cmd", "/c", "start", "", launch_path],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                elif launch_path.lower().endswith(".lnk"):
                    os.startfile(launch_path)
                else:
                    subprocess.Popen([launch_path])
                result["message"] = f"Opened {app_name} ({launch_path})"
            except Exception as e:
                result["status"] = "error"
                result["message"] = f"Found {app_name} at {launch_path} but failed to launch: {e}"
        else:
            # Last resort: try the Windows 'start' command
            try:
                subprocess.Popen(
                    ["cmd", "/c", "start", "", app_name],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                result["message"] = f"Launched '{app_name}' via system start command"
            except Exception as e:
                result["status"] = "error"
                result["message"] = (
                    f"Could not find '{app_name}' on this laptop. "
                    f"Searched: Start Menu, installed programs, PATH, and registry."
                )

        self.log_action(result)
        return result

    async def read_file(self, file_path: str) -> Optional[str]:
        """Reads a file and returns its content"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                return {
                    "status": "success",
                    "content": content[:2000],  # Limit output size
                    "file_size": len(content)
                }
        except FileNotFoundError:
            return {
                "status": "error",
                "message": f"File not found: {file_path}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error reading file: {str(e)}"
            }

    async def write_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Writes content to a file (creates if doesn't exist)"""
        # Check for safe directory
        from safety.guards import SafetyGuards
        safety = SafetyGuards()
        if not safety.check_file_path_safe(file_path):
            return {
                "status": "error",
                "message": "Access denied: unsafe file path"
            }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {
                "status": "success",
                "message": f"Wrote to file: {file_path}",
                "bytes_written": len(content)
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to write file: {str(e)}"
            }

    async def list_directory(self, path: str) -> Optional[list]:
        """Lists files in a directory"""
        try:
            entries = os.listdir(path)
            return {"status": "success", "files": entries[:50]}  # Limit output
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_chrome_profiles(self) -> list:
        """Gets list of Chrome profiles"""
        chrome_base = os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Local\Google\Chrome\User Data")
        try:
            # Try to find profile directories
            import subprocess
            result = subprocess.run(
                ["powershell", "-Command", "Get-ChildItem -Path", f'"{chrome_base}\"', "-Directory"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                profiles = [d.replace("Default", "Rajesh Ponnapureddy") for d in result.stdout.split("\n") if d.strip()]
                return {"status": "success", "profiles": profiles}
            else:
                return {"status": "error", "message": "Could not access Chrome profiles"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def log_action(self, result: Dict[str, Any]):
        """Logs action using Safety Guards"""
        from safety.guards import SafetyGuards
        safety = SafetyGuards()
        status = "APPROVED" if result.get("status") == "success" else "DENIED"
        safety.log_action(
            action=result["action"],
            target=result.get("app", ""),
            status=status,
            message=result.get("message", "")
        )
        return result
