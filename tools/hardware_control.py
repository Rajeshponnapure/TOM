"""
TOM Hardware Control — Mouse and keyboard automation for desktop control.
Tom can control the mouse, keyboard, and screen of any Windows system.
"""
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import List, Optional, Tuple
from tools.project_paths import project_path_str

try:
    import pyautogui
    _HAS_PYAUTOGUI = True
except ImportError:
    _HAS_PYAUTOGUI = False

try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

# Windows-specific imports
if os.name == "nt":
    try:
        import ctypes
        from ctypes import wintypes
        _user32 = ctypes.windll.user32
        _HAS_WINAPI = True
    except Exception:
        _HAS_WINAPI = False
else:
    _HAS_WINAPI = False

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


class HardwareControl:
    """
    Full system hardware control.
    Capabilities: mouse movement/clicking, keyboard typing, screen capture,
    window management, clipboard operations, audio/speaker control,
    system information, display control.
    """

    def __init__(self):
        if _HAS_PYAUTOGUI:
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1
        self._screen_size = self._get_screen_size()
        self._audio_available = self._init_audio()

    def _get_screen_size(self) -> Tuple[int, int]:
        if _HAS_WINAPI:
            return (_user32.GetSystemMetrics(0), _user32.GetSystemMetrics(1))
        if _HAS_PYAUTOGUI:
            return pyautogui.size()
        return (1920, 1080)

    def is_available(self) -> bool:
        return _HAS_PYAUTOGUI

    # ── Mouse Control ───────────────────────────────────────────────────

    def move_mouse(self, x: int, y: int, duration: float = 0.2) -> dict:
        """Move mouse to absolute screen coordinates."""
        if not _HAS_PYAUTOGUI:
            return {"status": "error", "message": "pyautogui not available"}
        try:
            pyautogui.moveTo(x, y, duration=duration)
            return {"status": "success", "position": (x, y)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def click(self, x: int = None, y: int = None, button: str = "left",
              clicks: int = 1) -> dict:
        """Click at current position or specified coordinates."""
        if not _HAS_PYAUTOGUI:
            return {"status": "error", "message": "pyautogui not available"}
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y, button=button, clicks=clicks)
            else:
                pyautogui.click(button=button, clicks=clicks)
            pos = pyautogui.position()
            return {"status": "success", "position": (pos.x, pos.y), "button": button}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def double_click(self, x: int = None, y: int = None) -> dict:
        return self.click(x, y, clicks=2)

    def right_click(self, x: int = None, y: int = None) -> dict:
        return self.click(x, y, button="right")

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int,
             duration: float = 0.5) -> dict:
        if not _HAS_PYAUTOGUI:
            return {"status": "error", "message": "pyautogui not available"}
        try:
            pyautogui.moveTo(start_x, start_y, duration=0.1)
            pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration)
            return {"status": "success", "from": (start_x, start_y), "to": (end_x, end_y)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def scroll(self, clicks: int, x: int = None, y: int = None) -> dict:
        """Scroll. Positive = up, negative = down."""
        if not _HAS_PYAUTOGUI:
            return {"status": "error", "message": "pyautogui not available"}
        try:
            if x is not None and y is not None:
                pyautogui.scroll(clicks, x, y)
            else:
                pyautogui.scroll(clicks)
            return {"status": "success", "clicks": clicks}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_mouse_position(self) -> dict:
        if not _HAS_PYAUTOGUI:
            return {"status": "error", "message": "pyautogui not available"}
        try:
            pos = pyautogui.position()
            return {"status": "success", "x": pos.x, "y": pos.y}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ── Keyboard Control ────────────────────────────────────────────────

    def type_text(self, text: str, interval: float = 0.05) -> dict:
        """Type text with optional delay between characters."""
        if not _HAS_PYAUTOGUI:
            return {"status": "error", "message": "pyautogui not available"}
        try:
            pyautogui.typewrite(text, interval=interval)
            return {"status": "success", "characters": len(text)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def press_key(self, key: str) -> dict:
        """
        Press a single key. Use key names like 'enter', 'tab', 'escape',
        'ctrl', 'shift', 'alt', 'f1'-'f12', 'up', 'down', 'left', 'right',
        'home', 'end', 'pageup', 'pagedown', 'backspace', 'delete', 'space'.
        """
        if not _HAS_PYAUTOGUI:
            return {"status": "error", "message": "pyautogui not available"}
        try:
            pyautogui.press(key)
            return {"status": "success", "key": key}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def hotkey(self, *keys: str) -> dict:
        """Press multiple keys simultaneously. E.g., hotkey('ctrl', 'c') for copy."""
        if not _HAS_PYAUTOGUI:
            return {"status": "error", "message": "pyautogui not available"}
        try:
            pyautogui.hotkey(*keys)
            return {"status": "success", "keys": list(keys)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def key_down(self, key: str) -> dict:
        if not _HAS_PYAUTOGUI:
            return {"status": "error", "message": "pyautogui not available"}
        try:
            pyautogui.keyDown(key)
            return {"status": "success", "key": key}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def key_up(self, key: str) -> dict:
        if not _HAS_PYAUTOGUI:
            return {"status": "error", "message": "pyautogui not available"}
        try:
            pyautogui.keyUp(key)
            return {"status": "success", "key": key}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ── Screen Control ──────────────────────────────────────────────────

    def screenshot(self, region: Tuple[int, int, int, int] = None) -> dict:
        """Take a screenshot. Optionally specify region (left, top, width, height)."""
        if not _HAS_PYAUTOGUI:
            return {"status": "error", "message": "pyautogui not available"}
        try:
            if region:
                img = pyautogui.screenshot(region=region)
            else:
                img = pyautogui.screenshot()
            path = project_path_str("output", f"screenshot_{int(time.time())}.png")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            img.save(path)
            return {"status": "success", "path": path, "size": img.size}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def locate_on_screen(self, image_path: str, confidence: float = 0.9) -> dict:
        """Locate an image on screen and return its coordinates."""
        if not _HAS_PYAUTOGUI:
            return {"status": "error", "message": "pyautogui not available"}
        try:
            pos = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if pos:
                center = pyautogui.center(pos)
                return {"status": "success", "position": (int(center.x), int(center.y)),
                        "region": (pos.left, pos.top, pos.width, pos.height)}
            return {"status": "error", "message": "Image not found on screen"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_pixel_color(self, x: int, y: int) -> dict:
        """Get the color of a pixel at screen coordinates."""
        if not _HAS_PYAUTOGUI:
            return {"status": "error", "message": "pyautogui not available"}
        try:
            color = pyautogui.pixel(x, y)
            return {"status": "success", "color": color, "hex": "#{:02x}{:02x}{:02x}".format(*color)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ── Window Control (Windows only) ───────────────────────────────────

    def get_active_window_title(self) -> str:
        if _HAS_WINAPI:
            try:
                hwnd = _user32.GetForegroundWindow()
                length = _user32.GetWindowTextLengthW(hwnd) + 1
                buffer = ctypes.create_unicode_buffer(length)
                _user32.GetWindowTextW(hwnd, buffer, length)
                return buffer.value
            except Exception:
                return ""
        return ""

    def focus_window(self, title_substring: str) -> dict:
        """Find and focus a window by title substring."""
        if not _HAS_WINAPI:
            return {"status": "error", "message": "Windows API not available"}

        def enum_callback(hwnd, results):
            if _user32.IsWindowVisible(hwnd):
                length = _user32.GetWindowTextLengthW(hwnd) + 1
                buffer = ctypes.create_unicode_buffer(length)
                _user32.GetWindowTextW(hwnd, buffer, length)
                if title_substring.lower() in buffer.value.lower():
                    results.append(hwnd)
            return True

        try:
            results = []
            enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            _user32.EnumWindows(enum_proc(enum_callback), results)
            if results:
                _user32.ShowWindow(results[0], 5)  # SW_SHOW
                _user32.SetForegroundWindow(results[0])
                return {"status": "success", "window": title_substring}
            return {"status": "error", "message": f"Window '{title_substring}' not found"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ── Clipboard ───────────────────────────────────────────────────────

    def copy_to_clipboard(self, text: str) -> dict:
        """Copy text to clipboard."""
        try:
            import subprocess
            # SECURITY: no shell pipeline with user text — feed clip.exe via stdin.
            subprocess.run(["clip"], input=text, text=True,
                           capture_output=True, timeout=5)
            return {"status": "success", "text": text[:50]}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_clipboard_text(self) -> str:
        try:
            import subprocess
            result = subprocess.run(["powershell", "-command", "Get-Clipboard"],
                                    capture_output=True, text=True, timeout=5)
            return result.stdout.strip()
        except Exception:
            return ""

    # ── Audio / Speaker Control ─────────────────────────────────────────

    def _init_audio(self) -> bool:
        """Initialize audio control interfaces."""
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            try:
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                return True
            except ImportError:
                pass
        except Exception:
            pass
        return os.name == "nt"

    def is_audio_available(self) -> bool:
        return self._audio_available

    def get_volume(self) -> dict:
        """Get current system volume level (0.0 to 1.0)."""
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            current = volume.GetMasterVolumeLevelScalar()
            muted = volume.GetMute()
            return {"status": "success", "volume": round(current, 2), "muted": bool(muted), "percent": int(current * 100)}
        except ImportError:
            ps = f'(Get-AudioDevice -PlaybackVolume).Volume'
            try:
                import subprocess
                r = subprocess.run(["powershell", "-Command", ps], capture_output=True, text=True, timeout=5)
                if r.stdout.strip():
                    return {"status": "success", "volume": float(r.stdout.strip()), "message": "Windows audio (basic)"}
            except Exception:
                pass
            return {"status": "error", "message": "Audio control requires pycaw: pip install pycaw comtypes"}

    def set_volume(self, level: float) -> dict:
        """Set system volume. Level is 0.0 (mute) to 1.0 (max)."""
        level = max(0.0, min(1.0, float(level)))
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(level, None)
            return {"status": "success", "volume": level, "percent": int(level * 100)}
        except ImportError:
            ps = f'Set-AudioDevice -PlaybackVolume {int(level * 100)}'
            try:
                r = subprocess.run(["powershell", "-Command", ps], capture_output=True, text=True, timeout=5)
                return {"status": "success", "volume": level, "percent": int(level * 100)}
            except Exception:
                pass
            return {"status": "error", "message": "Audio control requires pycaw: pip install pycaw comtypes"}

    def mute_audio(self) -> dict:
        """Mute system audio."""
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMute(True, None)
            return {"status": "success", "muted": True}
        except ImportError:
            return {"status": "error", "message": "pycaw required for mute control"}

    def unmute_audio(self) -> dict:
        """Unmute system audio."""
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMute(False, None)
            return {"status": "success", "muted": False}
        except ImportError:
            return {"status": "error", "message": "pycaw required for mute control"}

    def volume_up(self, step: float = 0.1) -> dict:
        v = self.get_volume()
        current = v.get("volume", 0.5) if v.get("status") == "success" else 0.5
        return self.set_volume(min(1.0, current + step))

    def volume_down(self, step: float = 0.1) -> dict:
        v = self.get_volume()
        current = v.get("volume", 0.5) if v.get("status") == "success" else 0.5
        return self.set_volume(max(0.0, current - step))

    # ── System Information ──────────────────────────────────────────────

    def get_system_info(self) -> dict:
        """Get comprehensive system information."""
        info = {}
        if os.name == "nt" and _HAS_WINAPI:
            try:
                kernel32 = ctypes.windll.kernel32
                info["os"] = "Windows"
                info["username"] = os.environ.get("USERNAME", "")
                info["computer"] = os.environ.get("COMPUTERNAME", "")
                info["processor"] = os.environ.get("PROCESSOR_IDENTIFIER", "")
                info["ram_gb"] = round(psutil.virtual_memory().total / (1024**3), 1) if _HAS_PSUTIL else "N/A"
                info["ram_used_gb"] = round(psutil.virtual_memory().used / (1024**3), 1) if _HAS_PSUTIL else "N/A"
                info["cpu_percent"] = psutil.cpu_percent(interval=0.5) if _HAS_PSUTIL else "N/A"
                info["screen"] = f"{self._screen_size[0]}x{self._screen_size[1]}"
                info["disk_free_gb"] = round(psutil.disk_usage("/").free / (1024**3), 1) if _HAS_PSUTIL else "N/A"
                info["disk_total_gb"] = round(psutil.disk_usage("/").total / (1024**3), 1) if _HAS_PSUTIL else "N/A"
                info["boot_time"] = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M") if _HAS_PSUTIL else "N/A"
            except Exception:
                pass
        info["active_window"] = self.get_active_window_title()
        info["python_version"] = sys.version.split()[0]
        return {"status": "success", "info": info}

    def get_display_info(self) -> dict:
        """Get display/monitor information."""
        displays = []
        if os.name == "nt" and _HAS_WINAPI:
            try:
                from ctypes import wintypes
                i = 0
                while True:
                    mi = wintypes.RECT()
                    if _user32.EnumDisplayMonitors(None, None, None, ctypes.byref(mi)):
                        break
                    displays.append({
                        "left": mi.left, "top": mi.top,
                        "right": mi.right, "bottom": mi.bottom,
                        "width": mi.right - mi.left,
                        "height": mi.bottom - mi.top,
                    })
                    i += 1
                    if i > 4:
                        break
            except Exception:
                pass
        if not displays:
            w, h = self._screen_size
            displays.append({"width": w, "height": h})
        return {"status": "success", "displays": displays, "count": len(displays)}

    def open_speaker_settings(self) -> dict:
        """Open Windows sound settings."""
        try:
            # Fixed argument list, no shell — os.startfile handles URI schemes on Windows.
            os.startfile("ms-settings:sound")  # noqa: S606 (fixed constant, not user input)
            return {"status": "success", "message": "Opened sound settings"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def open_volume_mixer(self) -> dict:
        """Open Windows volume mixer."""
        try:
            subprocess.run(["sndvol"], timeout=5)  # fixed binary name, no shell
            return {"status": "success", "message": "Opened volume mixer"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
