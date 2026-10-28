"""Diagnose a failing test suite, patch the code, re-run, report diff + evidence (PRD AT-013).

    report = await fix_failing_tests("C:/code/app", ask)

1. Snapshot uncommitted work (git.checkpoint) so nothing the user had is lost.
2. Run the tests (policy: running a project's code needs approval for that exact command).
3. Give the model the failure output and the source files the traceback names; it returns one
   whole replacement file as JSON. Test files are never edited — making a test pass by changing
   the test is not a fix.
4. Write it (policy-gated), re-run the tests.
5. Report the diagnosis, the diff and both test outputs. If the tests still fail, the file is put
   back the way it was and the report says so — a failed fix never stays in the code.
"""
from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

from tom_core.llm_json import parse_model_json
from tom_core.policy.engine import ActionClass
from tom_core.tools.guard import aenforce

Ask = Callable[[str, str], Awaitable[str]]
MAX_FILE_CHARS = 8000
_TB_FILE = re.compile(r'(?:File "([^"]+\.py)"|^([\w./\\-]+\.py):\d+)', re.M)

_SYSTEM = ("You fix bugs in a Python project so its failing tests pass. You get the test output and the "
           "source files involved. Change only the source code, never a test file. Return ONLY JSON: "
           '{"diagnosis": "one or two sentences", "file": "relative/path.py", "content": "the complete new file"}')


def _is_test(rel: str) -> bool:
    name = os.path.basename(rel)
    return name.startswith("test_") or name.endswith("_test.py") or "tests" in rel.replace("\\", "/").split("/")[:-1]


def _run(cmd: Sequence[str], cwd: str, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), cwd=cwd, capture_output=True, text=True, timeout=timeout,
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)


async def _tests(repo: str, cmd: Sequence[str]) -> Dict[str, Any]:
    gate = await aenforce("code.run_tests", ActionClass.MATERIAL_CHANGE,
                          payload={"repo": repo, "command": " ".join(cmd)}, approval_action="run_code",
                          summary=f"Run the tests in {repo}: {' '.join(cmd)}")
    if not gate.allowed:
        return {"ran": False, "passed": False, "output": gate.reason}
    try:
        proc = await asyncio.to_thread(_run, cmd, repo)
    except subprocess.TimeoutExpired:
        return {"ran": True, "passed": False, "output": "The tests did not finish within 300 s."}
    out = (proc.stdout + "\n" + proc.stderr).strip()
    return {"ran": True, "passed": proc.returncode == 0, "output": out[-4000:], "returncode": proc.returncode}


def _involved_files(repo: str, output: str) -> List[str]:
    files: List[str] = []
    for m in _TB_FILE.finditer(output):
        path = m.group(1) or m.group(2)
        full = os.path.normpath(path if os.path.isabs(path) else os.path.join(repo, path))
        if full.startswith(os.path.normpath(repo)) and os.path.isfile(full) and full not in files:
            files.append(full)
    # the failing test usually imports the code under test: include sibling modules it names
    for f in list(files):
        if _is_test(os.path.relpath(f, repo)):
            text = open(f, encoding="utf-8", errors="replace").read()
            for mod in re.findall(r"^\s*(?:from|import)\s+([\w.]+)", text, re.M):
                cand = os.path.join(repo, *mod.split(".")) + ".py"
                if os.path.isfile(cand) and cand not in files:
                    files.append(cand)
    return files[:4]


def _git_diff(repo: str) -> str:
    try:
        return _run(["git", "diff", "--no-color"], repo, timeout=30).stdout[-6000:]
    except Exception:
        return ""


def _blank_run(lines: List[str]) -> int:
    n = 0
    for line in lines:
        if line.strip():
            break
        n += 1
    return n


def keep_formatting(original: str, proposed: str) -> str:
    """The model's fix, applied as a minimal change to the original: only lines that really changed come
    from the model; blank lines it dropped, the final newline and the line endings stay as they were.
    Live check 2026-10-27: a one-character fix (a - b → a + b) also deleted the blank lines between
    functions and the file's last newline. Indentation changes are kept — in Python they can be the fix."""
    import difflib
    o, p = original.splitlines(), proposed.splitlines()
    sm = difflib.SequenceMatcher(None, [x.rstrip() for x in o], [x.rstrip() for x in p], autojunk=False)
    out: List[str] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out += o[i1:i2]
        elif tag == "delete":
            if all(not x.strip() for x in o[i1:i2]):
                out += o[i1:i2]                       # keep blank lines the model dropped
        elif tag == "insert":
            if any(x.strip() for x in p[j1:j2]):
                out += p[j1:j2]                       # new code yes, stray blank lines no
        else:                                         # replaced: the model's lines, original blank margins
            seg_o, seg_p = o[i1:i2], p[j1:j2]
            out += [""] * max(0, _blank_run(seg_o) - _blank_run(seg_p)) + seg_p \
                + [""] * max(0, _blank_run(seg_o[::-1]) - _blank_run(seg_p[::-1]))
    nl = "\r\n" if "\r\n" in original else "\n"
    return nl.join(out) + (nl if original.endswith(("\n", "\r")) else "")


async def fix_failing_tests(repo: str, ask: Ask, *, test_cmd: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    repo = os.path.abspath(repo)
    cmd = list(test_cmd or [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"])
    if not os.path.isdir(repo):
        return {"status": "error", "message": f"No folder at {repo}."}

    from tom_core.tools.registry import get_registry
    checkpoint = await get_registry().call("git.checkpoint", {"repo": repo, "label": "before-tom-fix"})

    before = await _tests(repo, cmd)
    if not before["ran"]:
        return {"status": "blocked", "message": before["output"], "tests_before": before}
    if before["passed"]:
        return {"status": "success", "verified": True, "message": "All tests already pass — nothing to fix.",
                "tests_before": before}

    sources = []
    for f in _involved_files(repo, before["output"]):
        rel = os.path.relpath(f, repo)
        text = open(f, encoding="utf-8", errors="replace").read()[:MAX_FILE_CHARS]
        sources.append(f"=== {rel} ===\n{text}")
    reply = await ask(_SYSTEM, f"Test output:\n{before['output']}\n\nFiles:\n" + "\n\n".join(sources))
    try:
        fix = parse_model_json(reply)
        rel, content = str(fix["file"]).replace("\\", "/"), str(fix["content"])
    except Exception:
        return {"status": "error", "message": "The model did not return a usable fix.", "tests_before": before}
    target = os.path.normpath(os.path.join(repo, rel))
    if not target.startswith(os.path.normpath(repo) + os.sep) or not os.path.isfile(target):
        return {"status": "error", "message": f"The proposed fix targets '{rel}', which is not a file in the project.",
                "tests_before": before}
    if _is_test(rel):
        return {"status": "error", "message": f"Refused: the proposed fix edits the test file '{rel}' instead of the code.",
                "tests_before": before}

    gate = await aenforce("code.apply_fix", ActionClass.WORKSPACE_WRITE, payload={"path": target}, paths=[target],
                          approval_action="write_outside_workspace", summary=f"Apply TOM's fix to {target}")
    if not gate.allowed:
        return {"status": "blocked", "message": gate.reason, "tests_before": before}
    with open(target, encoding="utf-8", newline="") as fh:
        original = fh.read()
    content = keep_formatting(original, content)
    with open(target, "w", encoding="utf-8", newline="") as fh:
        fh.write(content)
    diff = _git_diff(repo)
    after = await _tests(repo, cmd)
    report = {"diagnosis": str(fix.get("diagnosis", ""))[:500], "file": rel, "diff": diff,
              "tests_before": before, "tests_after": after,
              "checkpoint": checkpoint.get("message", "")}
    if after["passed"]:
        return {**report, "status": "success", "verified": True,
                "message": f"Fixed {rel}: {report['diagnosis']}\nTests now pass.\n\n{diff}"}
    with open(target, "w", encoding="utf-8", newline="") as fh:
        fh.write(original)                                     # a failed fix never stays in the code
    return {**report, "status": "error", "verified": False,
            "message": f"My change to {rel} did not make the tests pass, so I put the file back.\n"
                       f"Diagnosis: {report['diagnosis']}\n\nLast test output:\n{after['output'][-1500:]}"}
