"""
Sandboxed code runner — closes the "write code but can't run it" gap.

Safety contract:
  * Only runs through TomAgent's approval gate (the engine router requests
    explicit user approval before every run).
  * Subprocess isolation with a hard timeout — never in-process exec().
  * Output captured and truncated; non-zero exit reported honestly.
"""

import os
import subprocess
import sys
import tempfile
from typing import Any, Dict

from tools.project_paths import project_path_str

DEFAULT_TIMEOUT = 60
MAX_OUTPUT = 4000


class CodeRunner:
    def __init__(self):
        self.scratch_dir = project_path_str("output", "scratch")
        os.makedirs(self.scratch_dir, exist_ok=True)

    def run_python_file(self, path: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
        """Run an existing .py file in a subprocess with timeout + capture."""
        if not path.lower().endswith(".py"):
            return {"status": "error", "message": "Only .py files can be run."}
        abs_path = path if os.path.isabs(path) else project_path_str(path)
        if not os.path.isfile(abs_path):
            return {"status": "error", "message": f"File not found: {path}"}
        return self._run([sys.executable, abs_path], timeout, cwd=os.path.dirname(abs_path) or None)

    def run_python_code(self, code: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
        """Write code to a scratch file and run it (subprocess, never exec())."""
        fd, tmp = tempfile.mkstemp(suffix=".py", dir=self.scratch_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(code)
            result = self._run([sys.executable, tmp], timeout, cwd=self.scratch_dir)
            result["script_path"] = tmp
            return result
        except Exception as exc:
            return {"status": "error", "message": f"Could not stage code: {exc}"}

    @staticmethod
    def _run(cmd, timeout: int, cwd=None) -> Dict[str, Any]:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=timeout, cwd=cwd)
            out = (proc.stdout or "")[:MAX_OUTPUT]
            err = (proc.stderr or "")[:MAX_OUTPUT]
            ok = proc.returncode == 0
            msg = f"Exit code: {proc.returncode}\n"
            if out:
                msg += f"--- stdout ---\n{out}\n"
            if err:
                msg += f"--- stderr ---\n{err}\n"
            return {"status": "success" if ok else "error",
                    "message": msg.strip(), "returncode": proc.returncode,
                    "stdout": out, "stderr": err}
        except subprocess.TimeoutExpired:
            return {"status": "error",
                    "message": f"Execution timed out after {timeout}s (hard limit enforced)."}
        except Exception as exc:
            return {"status": "error", "message": f"Run failed: {exc}"}
