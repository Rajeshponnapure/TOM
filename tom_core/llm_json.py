"""Read the JSON object in a model reply — tolerant of fences, chatter, comments and trailing commas.

Plain json.loads on local-model output turned requested documents into placeholders and made plans
unreadable (owner report 2026-10-21); every structured-output caller uses this instead.
"""
from __future__ import annotations

import json
import re
from typing import Any


def parse_model_json(text: str) -> Any:
    s = (text or "").strip()
    if "```" in s:
        fenced = re.search(r"```(?:json)?\s*(.*?)```", s, re.S)
        if fenced:
            s = fenced.group(1).strip()
    start = min([i for i in (s.find("{"), s.find("[")) if i >= 0], default=-1)
    if start > 0:
        s = s[start:]
    # Cut after the matching closing bracket (ignores trailing chatter).
    depth, in_str, esc, end = 0, False, False, len(s)
    for i, ch in enumerate(s):
        if in_str:
            esc = (ch == "\\" and not esc)
            if ch == '"' and not esc:
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    s = s[:end]
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        repaired = re.sub(r"//[^\n]*", "", s)                     # // comments
        repaired = re.sub(r",\s*([}\]])", r"\1", repaired)        # trailing commas
        repaired = re.sub(r"[“”]", '"', repaired)       # smart quotes
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            # Windows paths with single backslashes (C:\Users\...) make invalid escapes such as \U.
            # Double every backslash that does not start a valid JSON escape.
            return json.loads(_LONE_BACKSLASH.sub(r"\\\\", repaired))


_LONE_BACKSLASH = re.compile(r'\\(?![\\"/bfnrt]|u[0-9a-fA-F]{4})')
