"""
Crash isolation (A3) — TOM never dies silently.

install():      process-wide hooks — unhandled exceptions in the main thread,
                worker threads, and native faults all land in tom_logs/crash_*.txt
install_tk():   Tkinter callback exceptions are logged and surfaced to the user
                instead of killing the UI loop.
"""

import datetime
import faulthandler
import os
import sys
import threading
import traceback

_LOG_DIR = os.path.join(os.getcwd(), "tom_logs")
_native_log_handle = None  # kept open for faulthandler


def _crash_path() -> str:
    os.makedirs(_LOG_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(_LOG_DIR, f"crash_{stamp}.txt")


def write_crash(kind: str, exc_type, exc, tb) -> str:
    """Write a crash report; returns the file path ('' on failure)."""
    try:
        path = _crash_path()
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"TOM crash report — {kind}\n")
            f.write(f"Time: {datetime.datetime.now().isoformat()}\n")
            f.write(f"Python: {sys.version}\n\n")
            traceback.print_exception(exc_type, exc, tb, file=f)
        return path
    except Exception:
        return ""


def install(app_name: str = "tom") -> None:
    """Process-wide crash hooks. Safe to call more than once."""
    global _native_log_handle
    os.makedirs(_LOG_DIR, exist_ok=True)
    # Native-level faults (segfault in a C extension etc.)
    try:
        if _native_log_handle is None:
            _native_log_handle = open(
                os.path.join(_LOG_DIR, "crash_native.log"), "a", encoding="utf-8")
        faulthandler.enable(file=_native_log_handle)
    except Exception:
        pass

    prev_hook = sys.excepthook

    def _hook(exc_type, exc, tb):
        path = write_crash(f"{app_name} main thread", exc_type, exc, tb)
        try:
            print(f"\n[TOM CRASH GUARD] Unhandled error logged to: {path or 'console only'}")
        except Exception:
            pass
        prev_hook(exc_type, exc, tb)

    sys.excepthook = _hook

    def _thread_hook(args):
        write_crash(f"{app_name} thread '{getattr(args.thread, 'name', '?')}'",
                    args.exc_type, args.exc_value, args.exc_traceback)

    try:
        threading.excepthook = _thread_hook
    except Exception:
        pass


def install_tk(root, notify=None) -> None:
    """Tk callback exceptions: log + notify, never kill the mainloop."""
    def _tk_hook(exc_type, exc, tb):
        path = write_crash("tkinter callback", exc_type, exc, tb)
        msg = f"A UI action failed and was contained (log: {os.path.basename(path) if path else 'console'})."
        try:
            if notify:
                notify(msg)
            else:
                print(f"[TOM CRASH GUARD] {msg}")
        except Exception:
            pass
    try:
        root.report_callback_exception = _tk_hook
    except Exception:
        pass
