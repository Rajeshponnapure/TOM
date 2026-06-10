import subprocess
import sys
import os
import re
import json
import platform
import tempfile
import shutil
import logging
import venv
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("DependencyManager")


class DependencyManager:
    """Universal dependency & environment manager for Tom.

    Capabilities:
    - Create/manage virtual environments (venv)
    - Install/update/downgrade packages
    - Auto-detect project requirements
    - Conflict resolution
    - Cross-version Python support
    - Requirements file generation
    """

    PACKAGE_KNOWN_MAP = {
        "flask": "Flask",
        "django": "Django",
        "requests": "requests",
        "numpy": "numpy",
        "pandas": "pandas",
        "matplotlib": "matplotlib",
        "scipy": "scipy",
        "pillow": "Pillow",
        "opencv": "opencv-python",
        "cv2": "opencv-python",
        "sklearn": "scikit-learn",
        "tensorflow": "tensorflow",
        "torch": "torch",
        "selenium": "selenium",
        "beautifulsoup4": "beautifulsoup4",
        "bs4": "beautifulsoup4",
        "lxml": "lxml",
        "sqlalchemy": "SQLAlchemy",
        "psycopg2": "psycopg2-binary",
        "redis": "redis",
        "celery": "celery",
        "pytest": "pytest",
        "black": "black",
        "flake8": "flake8",
        "mypy": "mypy",
        "click": "click",
        "jinja2": "Jinja2",
        "werkzeug": "Werkzeug",
        "markupsafe": "MarkupSafe",
        "itsdangerous": "itsdangerous",
        "colorama": "colorama",
        "tqdm": "tqdm",
        "pyyaml": "PyYAML",
        "yaml": "PyYAML",
        "toml": "toml",
        "jsonschema": "jsonschema",
        "pydantic": "pydantic",
        "httpx": "httpx",
        "aiohttp": "aiohttp",
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "gunicorn": "gunicorn",
        "scrapy": "Scrapy",
        "nltk": "nltk",
        "spacy": "spacy",
        "transformers": "transformers",
        "openai": "openai",
        "anthropic": "anthropic",
        "discord": "discord.py",
        "pymongo": "pymongo",
        "boto3": "boto3",
        "botocore": "botocore",
        "paramiko": "paramiko",
        "cryptography": "cryptography",
        "bcrypt": "bcrypt",
        "passlib": "passlib",
        "python-dotenv": "python-dotenv",
        "dotenv": "python-dotenv",
        "schedule": "schedule",
        "apscheduler": "APScheduler",
        "python-dateutil": "python-dateutil",
        "pytz": "pytz",
        "tzlocal": "tzlocal",
        "rich": "rich",
        "prompt_toolkit": "prompt-toolkit",
        "pygments": "Pygments",
        "grpcio": "grpcio",
        "protobuf": "protobuf",
        "websockets": "websockets",
        "sanic": "sanic",
        "asyncpg": "asyncpg",
        "aiosqlite": "aiosqlite",
        "motor": "motor",
        "pydrive": "PyDrive",
        "googleapiclient": "google-api-python-client",
        "oauth2client": "oauth2client",
        "pipdeptree": "pipdeptree",
        "pip_check": "pip-check",
        "pipreqs": "pipreqs",
        "yarg": "yarg",
        "pkginfo": "pkginfo",
        "packaging": "packaging",
        "setuptools": "setuptools",
        "wheel": "wheel",
        "pip": "pip",
        "pipwin": "pipwin",
    }

    TOM_CORE_DEPENDENCIES = [
        "requests",
        "beautifulsoup4",
        "selenium",
        "lxml",
        "Pillow",
        "numpy",
        "pandas",
        "python-dotenv",
        "pydantic",
        "httpx",
        "aiohttp",
        "websockets",
        "cryptography",
        "bcrypt",
        "passlib",
        "pyyaml",
        "jsonschema",
        "tqdm",
        "colorama",
        "rich",
        "schedule",
        "packaging",
        "pipdeptree",
    ]

    def __init__(self, python_path: str = None):
        self._python_path = python_path or sys.executable
        self._venv_base = os.path.join(os.path.expanduser("~"), ".tom_venvs")
        self._system = platform.system()
        logger.info(f"DependencyManager initialized. Python: {self._python_path}, OS: {self._system}")

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _run_cmd(
        self,
        cmd: List[str],
        cwd: str = None,
        timeout: int = 300,
        env: dict = None,
        capture_output: bool = True,
    ) -> Dict[str, Any]:
        """Run a command and return structured result."""
        try:
            logger.debug(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                env=env,
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout or "",
                "stderr": result.stderr or "",
                "success": result.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": "Command timed out",
                "success": False,
            }
        except FileNotFoundError as e:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False,
            }
        except Exception as e:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False,
            }

    def _get_pip_cmd(self, venv_path: str = None) -> List[str]:
        """Get pip command, optionally within a venv."""
        if venv_path:
            return [self._get_venv_python(venv_path), "-m", "pip"]
        return [self._python_path, "-m", "pip"]

    def _get_venv_python(self, venv_path: str) -> str:
        """Get python executable path inside a virtual environment."""
        if self._system == "Windows":
            return os.path.join(venv_path, "Scripts", "python.exe")
        return os.path.join(venv_path, "bin", "python")

    def _get_venv_pip(self, venv_path: str) -> str:
        """Get pip executable path inside a virtual environment."""
        if self._system == "Windows":
            return os.path.join(venv_path, "Scripts", "pip.exe")
        return os.path.join(venv_path, "bin", "pip")

    def _parse_pip_list(self, text: str) -> Dict[str, str]:
        """Parse output of 'pip list --format=json' or 'pip freeze' into {name: version}."""
        packages = {}
        for line in text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            if "==" in line:
                parts = line.split("==", 1)
                name = parts[0].strip().lower()
                version = parts[1].strip()
                packages[name] = version
        return packages

    def _find_python_interpreters(self) -> List[Dict[str, str]]:
        """Auto-detect available Python interpreters on the system."""
        interpreters = []
        seen = set()

        candidates = ["python", "python3", "py"]
        for candidate in candidates:
            try:
                result = subprocess.run(
                    [candidate, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    ver = result.stdout.strip() or result.stderr.strip()
                    m = re.search(r"(\d+\.\d+\.\d+)", ver)
                    full_path = None
                    if self._system == "Windows":
                        try:
                            r2 = subprocess.run(
                                ["where", candidate],
                                capture_output=True, text=True, timeout=10,
                            )
                            if r2.returncode == 0:
                                full_path = r2.stdout.strip().splitlines()[0]
                        except Exception:
                            full_path = shutil.which(candidate)
                    else:
                        full_path = shutil.which(candidate)

                    version_str = m.group(1) if m else "unknown"
                    key = version_str
                    if key not in seen:
                        seen.add(key)
                        interpreters.append({
                            "path": full_path or candidate,
                            "version": version_str,
                            "executable": candidate,
                        })
            except Exception:
                pass

        if self._system == "Windows":
            try:
                r = subprocess.run(
                    ["py", "--list"],
                    capture_output=True, text=True, timeout=10,
                )
                if r.returncode == 0:
                    for line in r.stdout.splitlines():
                        m = re.search(r"(-[\d.]+)", line)
                        if m:
                            ver = m.group(1).lstrip("-")
                            try:
                                r2 = subprocess.run(
                                    ["py", f"-{ver}", "--version"],
                                    capture_output=True, text=True, timeout=10,
                                )
                                if r2.returncode == 0:
                                    key = ver
                                    if key not in seen:
                                        seen.add(key)
                                        interpreters.append({
                                            "path": f"py -{ver}",
                                            "version": ver,
                                            "executable": f"py -{ver}",
                                        })
                            except Exception:
                                pass
            except Exception:
                pass

        interpreters.sort(key=lambda x: x["version"], reverse=True)
        return interpreters

    def _detect_python_version(self, python_path: str) -> str:
        """Get version string from a python interpreter."""
        try:
            r = subprocess.run(
                [python_path, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            out = r.stdout.strip() or r.stderr.strip()
            m = re.search(r"(\d+\.\d+\.\d+)", out)
            return m.group(1) if m else "unknown"
        except Exception:
            return "unknown"

    def _pip_install(
        self,
        packages: List[str],
        venv_path: str = None,
        upgrade: bool = False,
        constraints: str = None,
    ) -> Dict[str, Any]:
        """Install packages using pip."""
        pip_cmd = self._get_pip_cmd(venv_path)
        cmd = pip_cmd + ["install"]
        if upgrade:
            cmd.append("--upgrade")
        cmd.extend(packages)
        if constraints:
            cmd.extend(["-c", constraints])

        result = self._run_cmd(cmd)
        return result

    def _get_installed_packages(self, venv_path: str = None) -> Dict[str, str]:
        """Get all installed packages as {name: version}."""
        pip_cmd = self._get_pip_cmd(venv_path)
        cmd = pip_cmd + ["list", "--format=json"]
        result = self._run_cmd(cmd)
        if result["success"]:
            try:
                data = json.loads(result["stdout"])
                return {p["name"].lower(): p["version"] for p in data}
            except (json.JSONDecodeError, KeyError):
                pass
        cmd2 = pip_cmd + ["freeze"]
        result2 = self._run_cmd(cmd2)
        if result2["success"]:
            return self._parse_pip_list(result2["stdout"])
        return {}

    def _package_is_installed(self, package: str, venv_path: str = None) -> Optional[str]:
        """Check if a package is installed. Returns version or None."""
        installed = self._get_installed_packages(venv_path)
        return installed.get(package.lower())

    def _parse_imports_in_file(self, filepath: str) -> List[str]:
        """Extract top-level import names from a Python file."""
        imports = []
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return imports

        patterns = [
            r"^import\s+(\S+)",
            r"^from\s+(\S+)\s+import",
        ]
        for pattern in patterns:
            for m in re.finditer(pattern, content, re.MULTILINE):
                name = m.group(1).split(".")[0].strip()
                if name and not name.startswith("_"):
                    imports.append(name)
        return imports

    def _map_import_to_package(self, import_name: str) -> str:
        """Map a Python import name to its pip package name."""
        stdlib_modules = {
            "os", "sys", "re", "json", "csv", "math", "datetime", "time",
            "random", "collections", "itertools", "functools", "pathlib",
            "shutil", "glob", "hashlib", "base64", "uuid", "typing",
            "enum", "dataclasses", "threading", "multiprocessing", "subprocess",
            "logging", "warnings", "traceback", "inspect", "textwrap",
            "string", "io", "abc", "argparse", "configparser", "copy",
            "pprint", "tempfile", "pickle", "shelve", "sqlite3",
            "xml", "html", "http", "urllib", "socket", "ssl", "email",
            "zipfile", "tarfile", "gzip", "bz2", "lzma",
        }
        name = import_name.lower()
        if name in stdlib_modules:
            return None

        if name in self.PACKAGE_KNOWN_MAP:
            return self.PACKAGE_KNOWN_MAP[name]

        return import_name

    # ------------------------------------------------------------------
    # 1. create_venv
    # ------------------------------------------------------------------

    def create_venv(
        self, path: str, python_version: str = None
    ) -> Dict[str, Any]:
        """Create a virtual environment at the given path.

        Args:
            path: Path where the venv should be created.
            python_version: e.g. "3.11" or "3.10.11". Auto-detected if None.

        Returns:
            dict with status, result (venv path), python version, message.
        """
        logger.info(f"create_venv called: path={path}, python_version={python_version}")
        try:
            abs_path = os.path.abspath(path)

            if os.path.exists(abs_path):
                return {
                    "status": "error",
                    "result": None,
                    "message": f"Path already exists: {abs_path}",
                }

            python_exe = self._python_path
            used_version = self._detect_python_version(python_exe)

            if python_version:
                interpreters = self._find_python_interpreters()
                target = None
                for i in interpreters:
                    if i["version"].startswith(python_version):
                        target = i
                        break
                if target is None:
                    return {
                        "status": "error",
                        "result": None,
                        "message": (
                            f"Python {python_version} not found. "
                            f"Available: {[i['version'] for i in interpreters]}"
                        ),
                    }
                python_exe = target["path"]
                used_version = target["version"]

            os.makedirs(os.path.dirname(abs_path), exist_ok=True)

            venv.create(abs_path, symlinks=(self._system != "Windows"), with_pip=True)

            if self._system == "Windows":
                python_in_venv = os.path.join(abs_path, "Scripts", "python.exe")
            else:
                python_in_venv = os.path.join(abs_path, "bin", "python")

            if not os.path.exists(python_in_venv):
                return {
                    "status": "error",
                    "result": None,
                    "message": f"Venv creation failed - python not found at {python_in_venv}",
                }

            upgrade_cmd = [python_in_venv, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"]
            self._run_cmd(upgrade_cmd, timeout=120)

            return {
                "status": "success",
                "result": {
                    "path": abs_path,
                    "python": python_in_venv,
                    "python_version": used_version,
                },
                "message": f"Virtual environment created at {abs_path} (Python {used_version})",
            }

        except Exception as e:
            logger.exception("create_venv failed")
            return {
                "status": "error",
                "result": None,
                "message": str(e),
            }

    # ------------------------------------------------------------------
    # 2. install_package
    # ------------------------------------------------------------------

    def install_package(
        self,
        package: str,
        version: str = None,
        upgrade: bool = False,
        venv_path: str = None,
    ) -> Dict[str, Any]:
        """Install a pip package (optionally at specific version).

        Args:
            package: Package name.
            version: Specific version (e.g. "2.1.0").
            upgrade: If True, pass --upgrade.
            venv_path: Optional venv path to install into.

        Returns:
            dict with status, result (installed version), message.
        """
        logger.info(f"install_package: {package}=={version or 'latest'}, upgrade={upgrade}")
        try:
            target = f"{package}=={version}" if version else package
            pkgs = [target]
            result = self._pip_install(pkgs, venv_path=venv_path, upgrade=upgrade)

            if not result["success"]:
                stderr = result["stderr"]
                if "conflict" in stderr.lower() or "depend" in stderr.lower():
                    logger.warning(f"Conflict detected during install of {package}, retrying with --no-deps")
                    no_deps_cmd = self._get_pip_cmd(venv_path) + ["install", "--no-deps", target]
                    if upgrade:
                        no_deps_cmd.append("--upgrade")
                    result = self._run_cmd(no_deps_cmd)

            if result["success"]:
                installed = self._package_is_installed(package, venv_path)
                return {
                    "status": "success",
                    "result": {"name": package, "version": installed},
                    "message": f"Package '{package}' installed (version: {installed})",
                }
            else:
                return {
                    "status": "error",
                    "result": None,
                    "message": f"Failed to install '{package}': {result['stderr']}",
                }

        except Exception as e:
            logger.exception("install_package failed")
            return {
                "status": "error",
                "result": None,
                "message": str(e),
            }

    # ------------------------------------------------------------------
    # 3. uninstall_package
    # ------------------------------------------------------------------

    def uninstall_package(
        self, package: str, venv_path: str = None
    ) -> Dict[str, Any]:
        """Uninstall a package."""
        logger.info(f"uninstall_package: {package}")
        try:
            pip_cmd = self._get_pip_cmd(venv_path)
            cmd = pip_cmd + ["uninstall", "-y", package]
            result = self._run_cmd(cmd)

            if result["success"]:
                return {
                    "status": "success",
                    "result": {"name": package},
                    "message": f"Package '{package}' uninstalled successfully",
                }
            else:
                stderr = result["stderr"].lower()
                if "not installed" in stderr or "not recognized" in stderr:
                    return {
                        "status": "success",
                        "result": {"name": package},
                        "message": f"Package '{package}' was not installed",
                    }
                return {
                    "status": "error",
                    "result": None,
                    "message": f"Failed to uninstall '{package}': {result['stderr']}",
                }

        except Exception as e:
            logger.exception("uninstall_package failed")
            return {
                "status": "error",
                "result": None,
                "message": str(e),
            }

    # ------------------------------------------------------------------
    # 4. update_package
    # ------------------------------------------------------------------

    def update_package(
        self,
        package: str,
        target_version: str = None,
        venv_path: str = None,
    ) -> Dict[str, Any]:
        """Update to latest or specified version. Handles downgrade if needed.

        Args:
            package: Package name.
            target_version: Specific version or None for latest.
            venv_path: Optional venv path.

        Returns:
            dict with status, result, message.
        """
        logger.info(f"update_package: {package} -> {target_version or 'latest'}")
        try:
            current = self._package_is_installed(package, venv_path)

            if target_version:
                if current and self._compare_versions(current, target_version) > 0:
                    return self.downgrade_package(package, target_version, venv_path)

                result = self._pip_install(
                    [f"{package}=={target_version}"],
                    venv_path=venv_path,
                    upgrade=True,
                )
            else:
                result = self._pip_install(
                    [package], venv_path=venv_path, upgrade=True
                )

            if result["success"]:
                new_version = self._package_is_installed(package, venv_path)
                return {
                    "status": "success",
                    "result": {
                        "name": package,
                        "previous": current,
                        "current": new_version,
                    },
                    "message": (
                        f"Package '{package}' updated: "
                        f"{current} -> {new_version}" if current
                        else f"Package '{package}' installed (version: {new_version})"
                    ),
                }
            else:
                return {
                    "status": "error",
                    "result": None,
                    "message": f"Failed to update '{package}': {result['stderr']}",
                }

        except Exception as e:
            logger.exception("update_package failed")
            return {
                "status": "error",
                "result": None,
                "message": str(e),
            }

    # ------------------------------------------------------------------
    # 5. downgrade_package
    # ------------------------------------------------------------------

    def downgrade_package(
        self,
        package: str,
        target_version: str,
        venv_path: str = None,
    ) -> Dict[str, Any]:
        """Explicitly downgrade to an older version.

        Args:
            package: Package name.
            target_version: Target version string.
            venv_path: Optional venv path.

        Returns:
            dict with status, result, message.
        """
        logger.info(f"downgrade_package: {package} -> {target_version}")
        try:
            current = self._package_is_installed(package, venv_path)
            result = self._pip_install(
                [f"{package}=={target_version}"],
                venv_path=venv_path,
                upgrade=False,
            )

            if not result["success"]:
                stderr = result["stderr"]
                if "conflict" in stderr.lower():
                    logger.warning(f"Conflict during downgrade of {package}, retrying with --ignore-deps")
                    pip_cmd = self._get_pip_cmd(venv_path)
                    cmd = pip_cmd + ["install", "--no-deps", f"{package}=={target_version}"]
                    result = self._run_cmd(cmd)

            if result["success"]:
                new_version = self._package_is_installed(package, venv_path)
                return {
                    "status": "success",
                    "result": {
                        "name": package,
                        "previous": current,
                        "current": new_version,
                    },
                    "message": f"Package '{package}' downgraded: {current} -> {new_version}",
                }
            else:
                return {
                    "status": "error",
                    "result": None,
                    "message": f"Failed to downgrade '{package}' to {target_version}: {result['stderr']}",
                }

        except Exception as e:
            logger.exception("downgrade_package failed")
            return {
                "status": "error",
                "result": None,
                "message": str(e),
            }

    # ------------------------------------------------------------------
    # 6. install_requirements
    # ------------------------------------------------------------------

    def install_requirements(
        self, path: str, venv_path: str = None
    ) -> Dict[str, Any]:
        """Install from requirements.txt. Auto-create if missing.

        Args:
            path: Path to requirements.txt (or directory containing it).
            venv_path: Optional venv path.

        Returns:
            dict with status, result (installed packages), message.
        """
        logger.info(f"install_requirements: path={path}")
        try:
            req_file = path
            if os.path.isdir(path):
                req_file = os.path.join(path, "requirements.txt")

            if not os.path.exists(req_file):
                logger.info(f"requirements.txt not found at {req_file}, auto-generating...")
                gen_result = self.generate_requirements(path, output=req_file)
                if gen_result["status"] == "error":
                    return gen_result

            pip_cmd = self._get_pip_cmd(venv_path)
            cmd = pip_cmd + ["install", "-r", req_file]
            result = self._run_cmd(cmd, timeout=600)

            if result["success"]:
                return {
                    "status": "success",
                    "result": {"requirements_file": req_file},
                    "message": f"Installed all packages from {req_file}",
                }
            else:
                return {
                    "status": "error",
                    "result": None,
                    "message": f"Failed to install requirements: {result['stderr']}",
                }

        except Exception as e:
            logger.exception("install_requirements failed")
            return {
                "status": "error",
                "result": None,
                "message": str(e),
            }

    # ------------------------------------------------------------------
    # 7. generate_requirements
    # ------------------------------------------------------------------

    def generate_requirements(
        self, path: str = ".", output: str = "requirements.txt"
    ) -> Dict[str, Any]:
        """Scan project folder for imports and generate requirements.txt.

        Args:
            path: Project root folder.
            output: Output requirements file path.

        Returns:
            dict with status, result (file path, deps), message.
        """
        logger.info(f"generate_requirements: path={path}, output={output}")
        try:
            project_path = os.path.abspath(path)

            detect_result = self.auto_detect_dependencies(project_path)
            if detect_result["status"] != "success":
                return detect_result

            detected = detect_result["result"]["packages"]
            if not detected:
                return {
                    "status": "success",
                    "result": {"file": output, "packages": []},
                    "message": "No external dependencies detected",
                }

            installed = self._get_installed_packages()
            lines = []
            for dep_name, import_name in sorted(set(
                (d["package"], d["import"]) for d in detected
            )):
                version = installed.get(dep_name.lower())
                if version:
                    lines.append(f"{dep_name}=={version}")
                else:
                    lines.append(dep_name)

            output_path = os.path.abspath(output)
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

            return {
                "status": "success",
                "result": {
                    "file": output_path,
                    "packages": [d["package"] for d in detected],
                    "count": len(lines),
                },
                "message": f"Generated {output_path} with {len(lines)} packages",
            }

        except Exception as e:
            logger.exception("generate_requirements failed")
            return {
                "status": "error",
                "result": None,
                "message": str(e),
            }

    # ------------------------------------------------------------------
    # 8. check_conflicts
    # ------------------------------------------------------------------

    def check_conflicts(
        self, packages: List[str] = None, venv_path: str = None
    ) -> Dict[str, Any]:
        """Check for dependency conflicts between packages.

        Uses pipdeptree if available, falls back to pip check.

        Args:
            packages: List of package names to check. If None, check all.
            venv_path: Optional venv path.

        Returns:
            dict with status, result (conflict report), message.
        """
        logger.info(f"check_conflicts: packages={packages}")
        try:
            pip_cmd = self._get_pip_cmd(venv_path)

            has_pipdeptree = self._package_is_installed("pipdeptree", venv_path)
            report_lines = []

            if has_pipdeptree:
                cmd = pip_cmd + ["list", "--format=json"]
                list_result = self._run_cmd(cmd)
                all_packages = []
                if list_result["success"]:
                    try:
                        all_packages = json.loads(list_result["stdout"])
                    except json.JSONDecodeError:
                        pass

                if packages:
                    all_packages = [p for p in all_packages if p["name"].lower() in [x.lower() for x in packages]]

                if all_packages:
                    pkg_names = [p["name"] for p in all_packages]
                    cmd = pip_cmd + ["install", "--dry-run", "--report", "-"] + pkg_names
                    report_result = self._run_cmd(cmd)
                    if report_result["success"]:
                        report_lines.append("=== pip install --dry-run report ===")
                        report_lines.append(report_result["stdout"])
            else:
                cmd = pip_cmd + ["check"]
                check_result = self._run_cmd(cmd)
                if check_result["success"]:
                    report_lines.append("=== pip check ===")
                    report_lines.append("No conflicts detected (pip check passed)")
                else:
                    report_lines.append("=== pip check ===")
                    report_lines.append(check_result["stdout"])

            if not report_lines:
                cmd = pip_cmd + ["check"]
                check_result = self._run_cmd(cmd)
                if check_result["success"]:
                    report_lines.append("No conflicts detected")
                else:
                    report_lines.append(check_result["stdout"])

            report = "\n".join(report_lines)
            has_conflicts = "conflict" in report.lower() or "incompatible" in report.lower() or "missing" in report.lower()

            return {
                "status": "success",
                "result": {
                    "has_conflicts": has_conflicts,
                    "report": report,
                    "packages_checked": packages or "all",
                },
                "message": "Conflicts detected" if has_conflicts else "No conflicts detected",
            }

        except Exception as e:
            logger.exception("check_conflicts failed")
            return {
                "status": "error",
                "result": None,
                "message": str(e),
            }

    # ------------------------------------------------------------------
    # 9. list_installed
    # ------------------------------------------------------------------

    def list_installed(
        self, venv_path: str = None
    ) -> Dict[str, Any]:
        """List all installed packages with versions.

        Args:
            venv_path: Optional venv path. If None, uses current env.

        Returns:
            dict with status, result (package list), message.
        """
        logger.info(f"list_installed: venv_path={venv_path}")
        try:
            installed = self._get_installed_packages(venv_path)
            package_list = [
                {"name": k, "version": v}
                for k, v in sorted(installed.items())
                if k not in ("python",)
            ]
            return {
                "status": "success",
                "result": {
                    "packages": package_list,
                    "count": len(package_list),
                    "python": self._detect_python_version(
                        self._get_venv_python(venv_path) if venv_path else self._python_path
                    ),
                },
                "message": f"{len(package_list)} packages installed",
            }

        except Exception as e:
            logger.exception("list_installed failed")
            return {
                "status": "error",
                "result": None,
                "message": str(e),
            }

    # ------------------------------------------------------------------
    # 10. auto_detect_dependencies
    # ------------------------------------------------------------------

    def auto_detect_dependencies(
        self, path: str = "."
    ) -> Dict[str, Any]:
        """Scan Python files in path for import statements.

        Maps imports to known package names.

        Args:
            path: Project root folder.

        Returns:
            dict with status, result (detected dependencies), message.
        """
        logger.info(f"auto_detect_dependencies: path={path}")
        try:
            project_path = os.path.abspath(path)
            if not os.path.exists(project_path):
                return {
                    "status": "error",
                    "result": None,
                    "message": f"Path does not exist: {project_path}",
                }

            python_files = []
            if os.path.isfile(project_path) and project_path.endswith(".py"):
                python_files = [project_path]
            else:
                for root, dirs, files in os.walk(project_path):
                    dirs[:] = [d for d in dirs if d not in (
                        "__pycache__", ".git", ".venv", "venv", "env",
                        "node_modules", ".tox", ".eggs", "dist", "build",
                        ".mypy_cache", ".pytest_cache", ".ruff_cache",
                    )]
                    for f in files:
                        if f.endswith(".py"):
                            python_files.append(os.path.join(root, f))

            all_imports = {}
            for filepath in python_files:
                imports = self._parse_imports_in_file(filepath)
                for imp in imports:
                    all_imports.setdefault(imp, 0)
                    all_imports[imp] += 1

            detected_packages = []
            seen_packages = set()
            for import_name, count in sorted(
                all_imports.items(), key=lambda x: -x[1]
            ):
                package_name = self._map_import_to_package(import_name)
                if package_name and package_name.lower() not in seen_packages:
                    seen_packages.add(package_name.lower())
                    detected_packages.append({
                        "import": import_name,
                        "package": package_name,
                        "occurrences": count,
                    })

            return {
                "status": "success",
                "result": {
                    "project_path": project_path,
                    "files_scanned": len(python_files),
                    "packages": detected_packages,
                    "count": len(detected_packages),
                },
                "message": (
                    f"Scanned {len(python_files)} files, "
                    f"detected {len(detected_packages)} external dependencies"
                ),
            }

        except Exception as e:
            logger.exception("auto_detect_dependencies failed")
            return {
                "status": "error",
                "result": None,
                "message": str(e),
            }

    # ------------------------------------------------------------------
    # 11. ensure_tom_dependencies
    # ------------------------------------------------------------------

    def ensure_tom_dependencies(self, venv_path: str = None) -> Dict[str, Any]:
        """Check all packages Tom needs are installed. Install missing ones.

        Args:
            venv_path: Optional venv path. If None, uses current env.

        Returns:
            dict with status, result (status report), message.
        """
        logger.info("ensure_tom_dependencies called")
        try:
            installed = self._get_installed_packages(venv_path)
            report = []
            all_ok = True
            installed_any = False

            for pkg in self.TOM_CORE_DEPENDENCIES:
                version = installed.get(pkg.lower())
                if version:
                    report.append({
                        "package": pkg,
                        "status": "ok",
                        "version": version,
                    })
                else:
                    report.append({
                        "package": pkg,
                        "status": "missing",
                        "version": None,
                    })
                    all_ok = False

            if not all_ok:
                missing = [r["package"] for r in report if r["status"] == "missing"]
                logger.info(f"Installing missing Tom dependencies: {missing}")
                for pkg in missing:
                    result = self.install_package(pkg, venv_path=venv_path)
                    if result["status"] == "success":
                        installed_any = True
                        for r in report:
                            if r["package"] == pkg:
                                r["status"] = "ok"
                                r["version"] = result["result"]["version"]
                                break
                    else:
                        for r in report:
                            if r["package"] == pkg:
                                r["status"] = "failed"
                                break

            all_ok = all(r["status"] == "ok" for r in report)
            ok_count = sum(1 for r in report if r["status"] == "ok")
            failed_count = sum(1 for r in report if r["status"] == "failed")

            return {
                "status": "success" if all_ok else "partial",
                "result": {
                    "total_required": len(self.TOM_CORE_DEPENDENCIES),
                    "ok": ok_count,
                    "failed": failed_count,
                    "installed_new": installed_any,
                    "report": report,
                },
                "message": (
                    f"Tom dependencies: {ok_count}/{len(self.TOM_CORE_DEPENDENCIES)} OK"
                    + (f", {failed_count} failed" if failed_count else "")
                ),
            }

        except Exception as e:
            logger.exception("ensure_tom_dependencies failed")
            return {
                "status": "error",
                "result": None,
                "message": str(e),
            }

    # ------------------------------------------------------------------
    # 12. migrate_to_python311
    # ------------------------------------------------------------------

    def migrate_to_python311(self, target_dir: str = None) -> Dict[str, Any]:
        """Create a Python 3.11 venv for Tom and install all dependencies.

        Args:
            target_dir: Directory for the 3.11 venv. Defaults to ~/.tom_venvs/tom_py311.

        Returns:
            dict with status, result (migration report), message.
        """
        logger.info("migrate_to_python311 called")
        try:
            interpreters = self._find_python_interpreters()
            py311 = None
            for i in interpreters:
                if i["version"].startswith("3.11"):
                    py311 = i
                    break

            if py311 is None:
                return {
                    "status": "error",
                    "result": None,
                    "message": "Python 3.11 not found on this system. "
                               "Please install Python 3.11 first.",
                }

            venv_dir = target_dir or os.path.join(self._venv_base, "tom_py311")

            if os.path.exists(venv_dir):
                shutil.rmtree(venv_dir)
                logger.info(f"Removed existing venv at {venv_dir}")

            create_result = self.create_venv(venv_dir, python_version="3.11")
            if create_result["status"] != "success":
                return create_result

            venv_python = create_result["result"]["python"]
            old_python_version = self._detect_python_version(self._python_path)

            pip_cmd = [venv_python, "-m", "pip"]
            self._run_cmd(pip_cmd + ["install", "--upgrade", "pip", "setuptools", "wheel"], timeout=120)

            install_report = []
            all_ok = True
            for pkg in self.TOM_CORE_DEPENDENCIES:
                logger.info(f"Installing {pkg} in Python 3.11 venv...")
                result = self.install_package(pkg, venv_path=venv_dir)
                install_report.append({
                    "package": pkg,
                    "status": result["status"],
                    "version": result.get("result", {}).get("version") if result.get("result") else None,
                })
                if result["status"] != "success":
                    all_ok = False

            py311_version = self._detect_python_version(venv_python)

            import_test_results = {}
            test_imports = ["requests", "bs4", "selenium", "numpy", "pandas", "PIL", "yaml", "pydantic", "dotenv"]
            for mod_name in test_imports:
                try:
                    r = subprocess.run(
                        [venv_python, "-c", f"import {mod_name}; print(getattr({mod_name}, '__version__', 'ok'))"],
                        capture_output=True, text=True, timeout=15,
                    )
                    import_test_results[mod_name] = {
                        "success": r.returncode == 0,
                        "output": (r.stdout or r.stderr).strip(),
                    }
                except Exception as e:
                    import_test_results[mod_name] = {"success": False, "output": str(e)}

            successful_imports = sum(1 for v in import_test_results.values() if v["success"])
            total_tested = len(test_imports)

            return {
                "status": "success" if all_ok else "partial",
                "result": {
                    "venv_path": venv_dir,
                    "venv_python": venv_python,
                    "python_version": py311_version,
                    "old_python_version": old_python_version,
                    "dependencies_installed": install_report,
                    "total_deps": len(self.TOM_CORE_DEPENDENCIES),
                    "successful_deps": sum(1 for r in install_report if r["status"] == "success"),
                    "failed_deps": sum(1 for r in install_report if r["status"] != "success"),
                    "import_tests": import_test_results,
                    "import_tests_passed": successful_imports,
                    "import_tests_total": total_tested,
                },
                "message": (
                    f"Migration {'complete' if all_ok else 'partial'}: "
                    f"Python {old_python_version} -> {py311_version} at {venv_dir}. "
                    f"Imports: {successful_imports}/{total_tested} passed."
                ),
            }

        except Exception as e:
            logger.exception("migrate_to_python311 failed")
            return {
                "status": "error",
                "result": None,
                "message": str(e),
            }

    # ------------------------------------------------------------------
    # 13. analyze_project
    # ------------------------------------------------------------------

    def analyze_project(self, path: str) -> Dict[str, Any]:
        """Analyze a project folder comprehensively.

        Args:
            path: Project root path.

        Returns:
            dict with status, result (analysis report), message.
        """
        logger.info(f"analyze_project: path={path}")
        try:
            project_path = os.path.abspath(path)
            if not os.path.exists(project_path):
                return {
                    "status": "error",
                    "result": None,
                    "message": f"Path does not exist: {project_path}",
                }

            analysis = {
                "project_path": project_path,
                "python_version": None,
                "venv_detected": False,
                "venv_paths": [],
                "dependencies": [],
                "requirements_files": [],
                "project_type": None,
                "file_count": 0,
                "python_file_count": 0,
                "total_lines_of_code": 0,
                "has_setup_py": False,
                "has_setup_cfg": False,
                "has_pyproject_toml": False,
                "has_tox_ini": False,
                "has_makefile": False,
                "has_dockerfile": False,
                "estimated_complexity": "low",
            }

            analysis["python_version"] = self._detect_python_version(self._python_path)

            venv_names = [".venv", "venv", "env", ".env"]
            for vname in venv_names:
                vpath = os.path.join(project_path, vname)
                if os.path.exists(vpath):
                    analysis["venv_detected"] = True
                    analysis["venv_paths"].append(vpath)

            has_venv_parent = False
            parent_venvs = [".venv", "venv", "env"]
            for vname in parent_venvs:
                vpath = os.path.join(os.path.dirname(project_path), vname)
                if os.path.exists(vpath):
                    has_venv_parent = True
                    analysis["venv_paths"].append(vpath)
            if has_venv_parent and not analysis["venv_detected"]:
                analysis["venv_detected"] = True

            analysis["has_setup_py"] = os.path.exists(os.path.join(project_path, "setup.py"))
            analysis["has_setup_cfg"] = os.path.exists(os.path.join(project_path, "setup.cfg"))
            analysis["has_pyproject_toml"] = os.path.exists(os.path.join(project_path, "pyproject.toml"))
            analysis["has_tox_ini"] = os.path.exists(os.path.join(project_path, "tox.ini"))
            analysis["has_makefile"] = os.path.exists(os.path.join(project_path, "Makefile"))
            analysis["has_dockerfile"] = os.path.exists(os.path.join(project_path, "Dockerfile"))

            req_candidates = ["requirements.txt", "requirements-dev.txt", "requirements-test.txt"]
            for rc in req_candidates:
                rp = os.path.join(project_path, rc)
                if os.path.exists(rp):
                    analysis["requirements_files"].append(rp)

            total_files = 0
            python_files = 0
            total_loc = 0
            for root, dirs, files in os.walk(project_path):
                dirs[:] = [d for d in dirs if d not in (
                    "__pycache__", ".git", ".venv", "venv", "env",
                    "node_modules", ".tox", ".eggs", "dist", "build",
                    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".gitlab",
                )]
                for f in files:
                    total_files += 1
                    if f.endswith(".py"):
                        python_files += 1
                        fpath = os.path.join(root, f)
                        try:
                            with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                                loc = sum(1 for line in fh if line.strip() and not line.strip().startswith("#"))
                                total_loc += loc
                        except Exception:
                            pass

            analysis["file_count"] = total_files
            analysis["python_file_count"] = python_files
            analysis["total_lines_of_code"] = total_loc

            detect_result = self.auto_detect_dependencies(project_path)
            if detect_result["status"] == "success":
                analysis["dependencies"] = detect_result["result"]["packages"]
                analysis["dependency_count"] = detect_result["result"]["count"]
            else:
                analysis["dependencies"] = []
                analysis["dependency_count"] = 0

            if analysis["has_pyproject_toml"]:
                pyproject_path = os.path.join(project_path, "pyproject.toml")
                try:
                    analysis["pyproject_toml"] = self._parse_toml_like(pyproject_path)
                except Exception:
                    analysis["pyproject_toml"] = None
            else:
                analysis["pyproject_toml"] = None

            analysis["project_type"] = self._classify_project(analysis)

            loc = analysis["total_lines_of_code"]
            if loc > 50000:
                analysis["estimated_complexity"] = "very high"
            elif loc > 10000:
                analysis["estimated_complexity"] = "high"
            elif loc > 3000:
                analysis["estimated_complexity"] = "medium"
            elif loc > 500:
                analysis["estimated_complexity"] = "low"
            else:
                analysis["estimated_complexity"] = "trivial"

            return {
                "status": "success",
                "result": analysis,
                "message": (
                    f"Analyzed project at {project_path}: "
                    f"{python_files} Python files, ~{total_loc} LOC, "
                    f"{analysis['dependency_count']} external deps, "
                    f"type: {analysis['project_type']}"
                ),
            }

        except Exception as e:
            logger.exception("analyze_project failed")
            return {
                "status": "error",
                "result": None,
                "message": str(e),
            }

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _compare_versions(v1: str, v2: str) -> int:
        """Compare two semver strings. Returns -1, 0, or 1."""
        try:
            parts1 = [int(x) for x in re.split(r"[\.\-]", v1.split("+")[0])]
            parts2 = [int(x) for x in re.split(r"[\.\-]", v2.split("+")[0])]
            max_len = max(len(parts1), len(parts2))
            parts1.extend([0] * (max_len - len(parts1)))
            parts2.extend([0] * (max_len - len(parts2)))
            for a, b in zip(parts1, parts2):
                if a < b:
                    return -1
                if a > b:
                    return 1
            return 0
        except Exception:
            return 0

    @staticmethod
    def _classify_project(analysis: dict) -> str:
        """Classify the project type based on detected features."""
        deps = [d["import"].lower() for d in analysis.get("dependencies", [])]
        has = {
            "django": "django" in deps,
            "flask": "flask" in deps or "flask" in str(analysis.get("dependencies", [])).lower(),
            "fastapi": "fastapi" in deps,
            "selenium": "selenium" in deps,
            "scrapy": "scrapy" in deps,
            "tensorflow": "tensorflow" in deps or "tf" in deps,
            "torch": "torch" in deps,
            "requests": "requests" in deps,
            "bs4": "bs4" in deps or "beautifulsoup" in deps,
            "numpy": "numpy" in deps,
            "pandas": "pandas" in deps,
        }

        if has["django"]:
            return "django-webapp"
        if has["flask"]:
            return "flask-webapp"
        if has["fastapi"]:
            return "fastapi-api"
        if has["scrapy"]:
            return "scrapy-scraper"
        if has["tensorflow"] or has["torch"]:
            if has["numpy"] and has["pandas"]:
                return "ml-data-science"
            return "deep-learning"
        if has["selenium"]:
            return "browser-automation"
        if has["bs4"] and has["requests"]:
            return "web-scraper"
        if has["numpy"] and has["pandas"]:
            return "data-analysis"
        if analysis.get("has_setup_py") or analysis.get("has_pyproject_toml"):
            return "python-library"
        if analysis.get("python_file_count", 0) > 10:
            return "multi-module-application"
        if analysis.get("python_file_count", 0) > 0:
            return "script-collection"
        return "unknown"

    def _parse_toml_like(self, filepath: str) -> dict:
        """Parse a basic TOML file without the toml library."""
        result = {}
        current_section = result
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    section_match = re.match(r"^\[(.+)\]$", line)
                    if section_match:
                        keys = section_match.group(1).split(".")
                        current_section = result
                        for key in keys:
                            key = key.strip().strip('"').strip("'")
                            if key not in current_section:
                                current_section[key] = {}
                            current_section = current_section[key]
                        continue
                    kv_match = re.match(r'^(\w+)\s*=\s*(.+)$', line)
                    if kv_match:
                        key = kv_match.group(1).strip()
                        value = kv_match.group(2).strip()
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        elif value.lower() == "true":
                            value = True
                        elif value.lower() == "false":
                            value = False
                        else:
                            try:
                                if "." in value:
                                    value = float(value)
                                else:
                                    value = int(value)
                            except ValueError:
                                pass
                        current_section[key] = value
        except Exception:
            pass
        return result

    # ------------------------------------------------------------------
    # UTILITY METHODS
    # ------------------------------------------------------------------

    def get_python_versions(self) -> Dict[str, Any]:
        """Get all detected Python interpreters."""
        interpreters = self._find_python_interpreters()
        return {
            "status": "success",
            "result": {
                "interpreters": interpreters,
                "count": len(interpreters),
                "current": self._python_path,
            },
            "message": f"Found {len(interpreters)} Python interpreters",
        }

    def self_check(self) -> Dict[str, Any]:
        """Run a self-check to verify the DependencyManager works."""
        logger.info("Running self-check...")
        checks = {}

        checks["python_version"] = self._detect_python_version(self._python_path)
        checks["platform"] = self._system

        pkg_list = self.list_installed()
        checks["list_works"] = pkg_list["status"] == "success"
        checks["installed_count"] = pkg_list.get("result", {}).get("count", 0)

        with tempfile.TemporaryDirectory() as tmpdir:
            test_venv_path = os.path.join(tmpdir, "test_venv")
            cr = self.create_venv(test_venv_path)
            checks["create_venv_works"] = cr["status"] == "success"

            checks["pip_available"] = False
            if checks["create_venv_works"]:
                list_r = self.list_installed(venv_path=test_venv_path)
                checks["pip_in_venv"] = list_r["status"] == "success"
                checks["pip_available"] = checks["pip_in_venv"]

                ir = self.install_package("pipdeptree", venv_path=test_venv_path)
                checks["install_works"] = ir["status"] == "success"

                if checks["install_works"]:
                    ur = self.uninstall_package("pipdeptree", venv_path=test_venv_path)
                    checks["uninstall_works"] = ur["status"] == "success"

        all_pass = all(
            v is True for v in checks.values() if isinstance(v, bool)
        )

        return {
            "status": "success" if all_pass else "partial",
            "result": {
                "checks": checks,
                "all_passed": all_pass,
            },
            "message": f"Self-check {'passed' if all_pass else 'partial failures'}",
        }

    def freeze_environment(
        self, venv_path: str = None, output: str = None
    ) -> Dict[str, Any]:
        """Freeze current environment to a requirements file.

        Args:
            venv_path: Optional venv path.
            output: Output file path. Returns text if None.

        Returns:
            dict with status, result (frozen text / file path), message.
        """
        logger.info(f"freeze_environment: output={output}")
        try:
            pip_cmd = self._get_pip_cmd(venv_path)
            cmd = pip_cmd + ["freeze", "--all"]
            result = self._run_cmd(cmd)

            if not result["success"]:
                return {
                    "status": "error",
                    "result": None,
                    "message": f"Freeze failed: {result['stderr']}",
                }

            frozen_text = result["stdout"].strip()

            if output:
                output_path = os.path.abspath(output)
                os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(frozen_text + "\n")
                return {
                    "status": "success",
                    "result": {"file": output_path, "packages": len(frozen_text.splitlines())},
                    "message": f"Frozen environment to {output_path}",
                }
            else:
                return {
                    "status": "success",
                    "result": {"text": frozen_text, "packages": len(frozen_text.splitlines())},
                    "message": f"Environment frozen ({len(frozen_text.splitlines())} packages)",
                }

        except Exception as e:
            logger.exception("freeze_environment failed")
            return {
                "status": "error",
                "result": None,
                "message": str(e),
            }

    def clone_venv(
        self, source_venv: str, target_path: str
    ) -> Dict[str, Any]:
        """Clone a virtual environment by creating a new one and installing same packages.

        Args:
            source_venv: Path to source venv.
            target_path: Path for new venv.

        Returns:
            dict with status, result, message.
        """
        logger.info(f"clone_venv: {source_venv} -> {target_path}")
        try:
            if not os.path.exists(source_venv):
                return {
                    "status": "error",
                    "result": None,
                    "message": f"Source venv does not exist: {source_venv}",
                }

            freeze_result = self.freeze_environment(venv_path=source_venv)
            if freeze_result["status"] != "success":
                return freeze_result

            source_python = self._get_venv_python(source_venv)
            source_version = self._detect_python_version(source_python)

            create_result = self.create_venv(target_path, python_version=source_version.split(".")[0] + "." + source_version.split(".")[1])
            if create_result["status"] != "success":
                return create_result

            frozen_text = freeze_result["result"]["text"]
            temp_req = os.path.join(tempfile.gettempdir(), "_clone_req.txt")
            with open(temp_req, "w", encoding="utf-8") as f:
                f.write(frozen_text + "\n")

            try:
                install_result = self.install_requirements(temp_req, venv_path=target_path)
                return install_result
            finally:
                if os.path.exists(temp_req):
                    os.remove(temp_req)

        except Exception as e:
            logger.exception("clone_venv failed")
            return {
                "status": "error",
                "result": None,
                "message": str(e),
            }

    def search_package(
        self, query: str, venv_path: str = None
    ) -> Dict[str, Any]:
        """Search for packages on PyPI.

        Args:
            query: Search query string.
            venv_path: Optional venv (for pip index).

        Returns:
            dict with status, result (search results), message.
        """
        logger.info(f"search_package: {query}")
        try:
            pip_cmd = self._get_pip_cmd(venv_path)
            cmd = pip_cmd + ["search", query]
            result = self._run_cmd(cmd, timeout=30)

            if result["success"]:
                lines = [l for l in result["stdout"].splitlines() if l.strip()]
                return {
                    "status": "success",
                    "result": {
                        "query": query,
                        "results": lines,
                        "count": len(lines),
                    },
                    "message": f"Found {len(lines)} results for '{query}'",
                }
            else:
                test_cmd = pip_cmd + ["index", "versions", query]
                test_result = self._run_cmd(test_cmd, timeout=30)
                if test_result["success"]:
                    lines = [l for l in test_result["stdout"].splitlines() if l.strip()]
                    return {
                        "status": "success",
                        "result": {
                            "query": query,
                            "results": lines,
                            "count": len(lines),
                        },
                        "message": f"Found info for '{query}' via index",
                    }
                return {
                    "status": "error",
                    "result": None,
                    "message": f"Search failed: {result['stderr']}",
                }

        except Exception as e:
            logger.exception("search_package failed")
            return {
                "status": "error",
                "result": None,
                "message": str(e),
            }

    def verify_venv(
        self, venv_path: str
    ) -> Dict[str, Any]:
        """Verify a virtual environment is intact and functional.

        Args:
            venv_path: Path to venv.

        Returns:
            dict with status, result (verification report), message.
        """
        logger.info(f"verify_venv: {venv_path}")
        try:
            issues = []
            venv_abs = os.path.abspath(venv_path)

            if not os.path.exists(venv_abs):
                return {
                    "status": "error",
                    "result": None,
                    "message": f"Venv does not exist: {venv_abs}",
                }

            if self._system == "Windows":
                scripts_dir = os.path.join(venv_abs, "Scripts")
                python_exe = os.path.join(scripts_dir, "python.exe")
                pip_exe = os.path.join(scripts_dir, "pip.exe")
            else:
                scripts_dir = os.path.join(venv_abs, "bin")
                python_exe = os.path.join(scripts_dir, "python")
                pip_exe = os.path.join(scripts_dir, "pip")

            if not os.path.exists(scripts_dir):
                issues.append("Scripts/bin directory missing")
            if not os.path.exists(python_exe):
                issues.append("Python executable missing")

            py_ver = "unknown"
            if os.path.exists(python_exe):
                ver_result = self._run_cmd([python_exe, "--version"])
                if ver_result["success"]:
                    py_ver = ver_result["stdout"].strip() or ver_result["stderr"].strip()

            pip_works = False
            if os.path.exists(python_exe):
                test_cmd = [python_exe, "-m", "pip", "--version"]
                pr = self._run_cmd(test_cmd)
                pip_works = pr["success"]
                if not pip_works:
                    issues.append("pip is not working")

            site_packages = self._find_site_packages(venv_abs)
            if site_packages and os.path.exists(site_packages):
                pkg_count = len([
                    d for d in os.listdir(site_packages)
                    if os.path.isdir(os.path.join(site_packages, d))
                    and not d.startswith("_")
                    and not d.endswith(".dist-info")
                    and not d.endswith(".egg-info")
                ])
            else:
                pkg_count = 0
                if not issues:
                    issues.append("site-packages directory not found")

            is_functional = len(issues) == 0 and pip_works

            return {
                "status": "success" if is_functional else "degraded",
                "result": {
                    "path": venv_abs,
                    "exists": True,
                    "python_version": py_ver,
                    "pip_works": pip_works,
                    "package_count": pkg_count,
                    "issues": issues,
                    "is_functional": is_functional,
                },
                "message": (
                    "Venv is functional" if is_functional
                    else f"Venv has issues: {'; '.join(issues)}"
                ),
            }

        except Exception as e:
            logger.exception("verify_venv failed")
            return {
                "status": "error",
                "result": None,
                "message": str(e),
            }

    def _find_site_packages(self, venv_path: str) -> Optional[str]:
        """Find site-packages directory inside a venv."""
        if self._system == "Windows":
            lib_dir = os.path.join(venv_path, "Lib")
        else:
            lib_dir = os.path.join(venv_path, "lib")

        if not os.path.exists(lib_dir):
            return None

        for item in os.listdir(lib_dir):
            sp = os.path.join(lib_dir, item, "site-packages")
            if os.path.exists(sp):
                return sp
        return None

    def remove_venv(self, venv_path: str) -> Dict[str, Any]:
        """Remove a virtual environment.

        Args:
            venv_path: Path to venv to remove.

        Returns:
            dict with status, result, message.
        """
        logger.info(f"remove_venv: {venv_path}")
        try:
            abs_path = os.path.abspath(venv_path)
            if not os.path.exists(abs_path):
                return {
                    "status": "success",
                    "result": {"path": abs_path},
                    "message": f"Venv at {abs_path} did not exist",
                }

            shutil.rmtree(abs_path)
            return {
                "status": "success",
                "result": {"path": abs_path},
                "message": f"Removed venv at {abs_path}",
            }

        except Exception as e:
            logger.exception("remove_venv failed")
            return {
                "status": "error",
                "result": None,
                "message": str(e),
            }

    def batch_install(
        self, packages: List[Dict[str, Any]], venv_path: str = None
    ) -> Dict[str, Any]:
        """Install multiple packages in batch.

        Args:
            packages: List of dicts with 'name' and optional 'version'.
            venv_path: Optional venv path.

        Returns:
            dict with status, result (per-package results), message.
        """
        logger.info(f"batch_install: {len(packages)} packages")
        try:
            results = []
            successes = 0
            failures = 0

            for pkg_spec in packages:
                name = pkg_spec["name"]
                version = pkg_spec.get("version")
                upgrade = pkg_spec.get("upgrade", False)
                result = self.install_package(name, version, upgrade, venv_path)
                results.append({
                    "package": name,
                    "version": version,
                    "status": result["status"],
                    "installed_version": result.get("result", {}).get("version") if result.get("result") else None,
                })
                if result["status"] == "success":
                    successes += 1
                else:
                    failures += 1

            return {
                "status": "success" if failures == 0 else "partial",
                "result": {
                    "results": results,
                    "total": len(packages),
                    "successes": successes,
                    "failures": failures,
                },
                "message": f"Batch install: {successes}/{len(packages)} succeeded" + (f", {failures} failed" if failures else ""),
            }

        except Exception as e:
            logger.exception("batch_install failed")
            return {
                "status": "error",
                "result": None,
                "message": str(e),
            }


# ------------------------------------------------------------------
# CLI ENTRY POINT
# ------------------------------------------------------------------

def main():
    """Command-line interface for DependencyManager."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Tom's Universal Dependency & Environment Manager"
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=[
            "create-venv",
            "install",
            "uninstall",
            "update",
            "downgrade",
            "install-reqs",
            "generate-reqs",
            "check-conflicts",
            "list",
            "auto-detect",
            "ensure-tom",
            "migrate-311",
            "analyze",
            "self-check",
            "freeze",
            "search",
            "verify-venv",
            "clone-venv",
            "remove-venv",
            "versions",
            "batch-install",
        ],
        help="Action to perform",
    )
    parser.add_argument("--path", default=".", help="Path (for venv/project)")
    parser.add_argument("--package", help="Package name")
    parser.add_argument("--version", help="Version string")
    parser.add_argument("--output", help="Output path")
    parser.add_argument("--venv", help="Venv path")
    parser.add_argument("--target", help="Target version")
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--python", help="Python executable path")
    parser.add_argument("--upgrade", action="store_true", help="Upgrade flag")

    args = parser.parse_args()

    dm = DependencyManager(python_path=args.python)

    actions = {
        "create-venv": lambda: dm.create_venv(args.path, args.version),
        "install": lambda: dm.install_package(args.package, args.version, args.upgrade, args.venv),
        "uninstall": lambda: dm.uninstall_package(args.package, args.venv),
        "update": lambda: dm.update_package(args.package, args.target, args.venv),
        "downgrade": lambda: dm.downgrade_package(args.package, args.target, args.venv),
        "install-reqs": lambda: dm.install_requirements(args.path, args.venv),
        "generate-reqs": lambda: dm.generate_requirements(args.path, args.output or "requirements.txt"),
        "check-conflicts": lambda: dm.check_conflicts(
            args.package.split(",") if args.package else None, args.venv
        ),
        "list": lambda: dm.list_installed(args.venv),
        "auto-detect": lambda: dm.auto_detect_dependencies(args.path),
        "ensure-tom": lambda: dm.ensure_tom_dependencies(args.venv),
        "migrate-311": lambda: dm.migrate_to_python311(args.path),
        "analyze": lambda: dm.analyze_project(args.path),
        "self-check": lambda: dm.self_check(),
        "freeze": lambda: dm.freeze_environment(args.venv, args.output),
        "search": lambda: dm.search_package(args.query, args.venv),
        "verify-venv": lambda: dm.verify_venv(args.path),
        "clone-venv": lambda: dm.clone_venv(args.path, args.target or (args.path + "_clone")),
        "remove-venv": lambda: dm.remove_venv(args.path),
        "versions": lambda: dm.get_python_versions(),
        "batch-install": lambda: dm.batch_install(
            [{"name": p.split("==")[0], "version": p.split("==")[1] if "==" in p else None}
             for p in (args.package.split(",") if args.package else [])],
            args.venv,
        ),
    }

    if args.action in actions:
        result = actions[args.action]()
        print(json.dumps(result, indent=2, default=str))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
