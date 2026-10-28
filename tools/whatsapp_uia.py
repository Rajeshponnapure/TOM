"""WhatsApp Desktop through Windows UI Automation: search contacts and open an exact chat without
keystrokes or focus changes.

Why (owner report 2026-10-21): "text mounish as hi ... if there are multiple people with the same
name ask me which one". The keyboard path typed the name and pressed Enter on the FIRST search
match. WhatsApp Desktop (a WebView2 app) exposes its UI to UI Automation, so TOM can read every
match and select exactly the one the user chose. Measured on the owner's machine (WhatsApp
2.2640.100.0): searching "mounish" through the search box's ValuePattern listed both
"Mounish Sai" and "Koteswara Rao Mounish Vp"; result rows support SelectionItemPattern.

Read-only operations (search/candidates) never send anything. Windows only; every entry point
raises UIAError when UI Automation or WhatsApp is unavailable so callers can fall back safely.
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

# Trailing time/date WhatsApp shows after a chat name ("12:55", "Yesterday", "21/06/2026", "Monday").
_TRAILING_STAMP = re.compile(
    r"\s+(?:\d{1,2}:\d{2}(?:\s?[AaPp][Mm])?|yesterday|today|monday|tuesday|wednesday|thursday|friday|saturday"
    r"|sunday|\d{1,2}/\d{1,2}/\d{2,4})\s*$", re.IGNORECASE)


class UIAError(RuntimeError):
    """UI Automation or WhatsApp Desktop is not usable; nothing was done."""


@dataclass(frozen=True)
class Candidate:
    label: str           # the chat/contact name as WhatsApp shows it
    row_text: str        # the full row text (name + time + preview), shown when names repeat


def clean_label(item_name: str) -> str:
    """'Mounish Sai 12:55' → 'Mounish Sai'; 'Koteswara Rao Mounish Vp' stays as it is."""
    label = re.sub(r"\s+", " ", item_name or "").strip()
    while True:
        stripped = _TRAILING_STAMP.sub("", label)
        if stripped == label:
            return label
        label = stripped


def candidates_from_rows(rows: Sequence[Tuple[str, str]], query: str) -> List[Candidate]:
    """Distinct chats/contacts whose name contains `query`, in the order WhatsApp lists them.

    `rows` are (row_text, first_item_text) pairs. Message hits inside other chats (a group whose
    name doesn't contain the query) are dropped: the user asked for a person, not a message.
    """
    wanted = (query or "").strip().lower()
    out: List[Candidate] = []
    seen = set()
    for row_text, item_text in rows:
        label = clean_label(item_text or row_text)
        if not label or wanted not in label.lower() or label.lower() in seen:
            continue
        seen.add(label.lower())
        out.append(Candidate(label=label, row_text=re.sub(r"\s+", " ", row_text or "").strip()))
    return out


def choose(candidates: Sequence[Candidate], query: str) -> Optional[Candidate]:
    """The one candidate to use without asking, or None when the user has to pick.

    Exactly one match → it. Several → only an exact (case-insensitive) name match counts, and only
    if it is the single exact one. "mounish" never silently means "Mounish Sai".
    """
    if len(candidates) == 1:
        return candidates[0]
    exact = [c for c in candidates if c.label.lower() == (query or "").strip().lower()]
    return exact[0] if len(exact) == 1 else None


class WhatsAppDesktopUIA:
    """Thin UI Automation layer. Tests replace `_rows`, `_set_search` and `_select_row`."""

    SEARCH_SETTLE_S = 2.0

    def __init__(self, sleep: Callable[[float], None] = time.sleep) -> None:
        self._sleep = sleep
        self._uia = None
        self._U = None

    # ── low level (real UI Automation) ───────────────────────────────────
    def _automation(self):
        # tests/conftest.py sets this so no test can ever drive the owner's real WhatsApp window.
        if os.environ.get("TOM_DISABLE_UI_AUTOMATION") == "1":
            raise UIAError("UI Automation is disabled (TOM_DISABLE_UI_AUTOMATION=1).")
        if self._uia is None:
            try:
                import comtypes.client
                comtypes.client.GetModule("UIAutomationCore.dll")
                from comtypes.gen import UIAutomationClient as U
                self._uia = comtypes.client.CreateObject(U.CUIAutomation, interface=U.IUIAutomation)
                self._U = U
            except Exception as exc:
                raise UIAError(f"Windows UI Automation is unavailable: {exc}") from None
        return self._uia, self._U

    def _window(self):
        import ctypes
        from ctypes import wintypes
        if not hasattr(ctypes, "windll"):
            raise UIAError("Windows UI Automation is unavailable on this operating system.")
        user32 = ctypes.windll.user32
        found = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def _cb(hwnd, _):
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, buf, 256)
            if user32.IsWindowVisible(hwnd) and buf.value.strip().lower() == "whatsapp":
                found.append(hwnd)
            return True
        user32.EnumWindows(_cb, 0)
        if not found:
            raise UIAError("WhatsApp Desktop is not open.")
        uia, _ = self._automation()
        return uia.ElementFromHandle(found[0])

    def _search_box(self, root):
        uia, U = self._automation()
        box = root.FindFirst(U.TreeScope_Descendants,
                             uia.CreatePropertyCondition(U.UIA_ControlTypePropertyId, U.UIA_EditControlTypeId))
        if box is None or "search" not in (box.CurrentName or "").lower():
            raise UIAError("WhatsApp's search box was not found (its layout may have changed).")
        return box

    def _set_search(self, text: str) -> None:
        root = self._window()
        _, U = self._automation()
        box = self._search_box(root)
        pattern = box.GetCurrentPattern(U.UIA_ValuePatternId)
        if pattern is None:
            raise UIAError("WhatsApp's search box does not accept text through UI Automation.")
        pattern.QueryInterface(U.IUIAutomationValuePattern).SetValue(text)

    def _row_elements(self):
        root = self._window()
        uia, U = self._automation()
        everything = root.FindAll(U.TreeScope_Descendants, uia.CreateTrueCondition())
        rows = []
        for i in range(everything.Length):
            el = everything.GetElement(i)
            try:
                if el.CurrentLocalizedControlType == "row":
                    rows.append(el)
            except Exception:
                continue
        return rows

    def _first_item(self, row):
        uia, U = self._automation()
        items = row.FindAll(U.TreeScope_Descendants,
                            uia.CreatePropertyCondition(U.UIA_ControlTypePropertyId, U.UIA_DataItemControlTypeId))
        names = [items.GetElement(i).CurrentName or "" for i in range(items.Length)]
        row_text = row.CurrentName or ""
        # The shortest non-empty item that starts the row is "<name> <time>" / "<name>".
        prefixes = [n for n in names if n and row_text.startswith(n)]
        return min(prefixes, key=len) if prefixes else row_text

    def _rows(self) -> List[Tuple[str, str]]:
        return [(r.CurrentName or "", self._first_item(r)) for r in self._row_elements()]

    def _select_row(self, label: str) -> None:
        _, U = self._automation()
        for row in self._row_elements():
            if clean_label(self._first_item(row)).lower() != label.lower():
                continue
            target = row
            item = row.FindFirst(U.TreeScope_Children,
                                 self._uia.CreatePropertyCondition(U.UIA_IsSelectionItemPatternAvailablePropertyId, True))
            if item is not None:
                target = item
            pattern = target.GetCurrentPattern(U.UIA_SelectionItemPatternId)
            if pattern is None:
                raise UIAError(f"The result for '{label}' cannot be opened through UI Automation.")
            pattern.QueryInterface(U.IUIAutomationSelectionItemPattern).Select()
            return
        raise UIAError(f"'{label}' is no longer in WhatsApp's search results.")

    # ── high level ───────────────────────────────────────────────────────
    def candidates(self, query: str) -> List[Candidate]:
        """Search WhatsApp for `query` and list the matching chats/contacts. Sends nothing."""
        self._set_search(query)
        self._sleep(self.SEARCH_SETTLE_S)
        return candidates_from_rows(self._rows(), query)

    def open_chat(self, label: str, query: Optional[str] = None) -> None:
        """Open the chat whose name is exactly `label` (searching `query` or the label first)."""
        self._set_search(query or label)
        self._sleep(self.SEARCH_SETTLE_S)
        self._select_row(label)
        self._sleep(1.0)
