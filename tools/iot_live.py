"""Live IoT device control: see what is plugged in, what is wired to a microcontroller, flash code to
it, and read back that it runs.

The code generator in `tools/iot_engine.py` writes firmware; this module talks to real hardware over
USB-serial. It leans on what is already on this machine — pyserial for the port, PlatformIO
(`pio`) to compile and upload Arduino/ESP firmware, and MicroPython's raw REPL for boards already
running MicroPython — so nothing new has to be invented at run time.

Every read (list ports, identify a board, scan I2C by REPL, read serial) is observation. Writing
firmware to a device, or running code on it over the REPL, changes an external thing and is gated by
the policy engine (DESTRUCTIVE_OR_EXTERNAL) exactly like a WhatsApp send or a file delete: TOM shows
the owner the port and the board and asks before it flashes. There is no network listener and no
remote access here — it is the USB cable and nothing else.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

# Known USB-serial bridges and native-USB MCUs, keyed by (VID, PID) or VID alone.
# Each value is (human label, default PlatformIO board, platform, framework).
_VIDPID: Dict[Tuple[int, Optional[int]], Tuple[str, str, str, str]] = {
    (0x10C4, 0xEA60): ("CP210x bridge (ESP32/ESP8266 dev board)", "esp32dev", "espressif32", "arduino"),
    (0x1A86, 0x7523): ("CH340 bridge (Arduino/ESP clone)", "esp32dev", "espressif32", "arduino"),
    (0x1A86, 0x55D4): ("CH9102 bridge (ESP32 dev board)", "esp32dev", "espressif32", "arduino"),
    (0x0403, 0x6001): ("FTDI FT232 bridge", "esp32dev", "espressif32", "arduino"),
    (0x2E8A, 0x0005): ("Raspberry Pi Pico (MicroPython)", "pico", "raspberrypi", "arduino"),
    (0x2E8A, 0x000A): ("Raspberry Pi Pico (RP2040)", "pico", "raspberrypi", "arduino"),
}
_VID_ONLY: Dict[int, Tuple[str, str, str, str]] = {
    0x303A: ("Espressif native USB (ESP32-S2/S3/C3)", "esp32-s3-devkitc-1", "espressif32", "arduino"),
    0x2341: ("Arduino (official)", "uno", "atmelavr", "arduino"),
    0x2A03: ("Arduino (official)", "uno", "atmelavr", "arduino"),
    0x239A: ("Adafruit board", "esp32dev", "espressif32", "arduino"),
}

# board word the owner may type -> (PlatformIO board, platform, framework)
_BOARD_ALIASES: Dict[str, Tuple[str, str, str]] = {
    "esp32": ("esp32dev", "espressif32", "arduino"),
    "esp32dev": ("esp32dev", "espressif32", "arduino"),
    "esp32-s3": ("esp32-s3-devkitc-1", "espressif32", "arduino"),
    "esp32-c3": ("esp32-c3-devkitm-1", "espressif32", "arduino"),
    "esp8266": ("nodemcuv2", "espressif8266", "arduino"),
    "nodemcu": ("nodemcuv2", "espressif8266", "arduino"),
    "uno": ("uno", "atmelavr", "arduino"),
    "arduino": ("uno", "atmelavr", "arduino"),
    "nano": ("nanoatmega328", "atmelavr", "arduino"),
    "mega": ("megaatmega2560", "atmelavr", "arduino"),
    "pico": ("pico", "raspberrypi", "arduino"),
}

_I2C_NAMES = {               # a few common addresses, so a scan reads like something
    0x3C: "SSD1306 OLED", 0x3D: "SSD1306 OLED", 0x27: "LCD (PCF8574)", 0x3F: "LCD (PCF8574A)",
    0x76: "BME/BMP280", 0x77: "BME/BMP280", 0x68: "MPU6050 / DS3231 RTC", 0x23: "BH1750 light",
    0x40: "INA219 / HTU21", 0x48: "ADS1115 / LM75", 0x5A: "CCS811 / MLX90614", 0x29: "TSL2561 / VL53L0X",
}


def _ok(message: str, **extra: Any) -> Dict[str, Any]:
    return {"status": "success", "message": message, **extra}


def _err(message: str, **extra: Any) -> Dict[str, Any]:
    return {"status": "error", "message": message, **extra}


@dataclass
class Port:
    device: str                         # "COM5" / "/dev/ttyUSB0"
    description: str = ""
    hwid: str = ""
    vid: Optional[int] = None
    pid: Optional[int] = None
    label: str = ""                     # human board guess
    board: str = ""                     # PlatformIO board id
    platform: str = ""
    framework: str = ""

    def summary(self) -> str:
        bits = [self.device]
        if self.label:
            bits.append(self.label)
        elif self.description and self.description != "n/a":
            bits.append(self.description)
        return " — ".join(bits)


def find_pio() -> Optional[str]:
    """Path to the PlatformIO CLI, from PATH or its default per-user install."""
    found = shutil.which("pio") or shutil.which("platformio")
    if found:
        return found
    cand = os.path.join(os.path.expanduser("~"), ".platformio", "penv", "Scripts",
                        "pio.exe" if os.name == "nt" else "pio")
    if os.path.isfile(cand):
        return cand
    cand_posix = os.path.join(os.path.expanduser("~"), ".platformio", "penv", "bin", "pio")
    return cand_posix if os.path.isfile(cand_posix) else None


def _identify(vid: Optional[int], pid: Optional[int]) -> Tuple[str, str, str, str]:
    if vid is not None and (vid, pid) in _VIDPID:
        return _VIDPID[(vid, pid)]
    if vid in _VID_ONLY:
        return _VID_ONLY[vid]
    return ("", "", "", "")


def list_ports(_lister: Optional[Callable[[], list]] = None) -> List[Port]:
    """Serial ports present right now, each with a best-guess board. `_lister` is for tests."""
    if _lister is None:
        from serial.tools import list_ports as _lp
        _lister = _lp.comports
    out: List[Port] = []
    for p in _lister():
        vid = getattr(p, "vid", None)
        pid = getattr(p, "pid", None)
        label, board, platform, framework = _identify(vid, pid)
        out.append(Port(device=getattr(p, "device", str(p)), description=getattr(p, "description", "") or "",
                        hwid=getattr(p, "hwid", "") or "", vid=vid, pid=pid,
                        label=label, board=board, platform=platform, framework=framework))
    out.sort(key=lambda x: x.device)
    return out


# ── MicroPython raw REPL (no toolchain needed when the board already runs MicroPython) ──────────────
def mpy_exec(device: str, code: str, baud: int = 115200, timeout: float = 4.0,
             _open: Optional[Callable] = None) -> Dict[str, Any]:
    """Run `code` on a MicroPython board over the raw REPL and return its stdout/stderr.

    Running code on the device is an external side effect; callers that are not themselves gated must
    gate this. Reading with it (an expression that only prints) is observation.
    """
    import serial                                             # type: ignore
    opener = _open or (lambda: serial.Serial(device, baud, timeout=0.3))
    try:
        ser = opener()
    except Exception as exc:
        return _err(f"Could not open {device}: {exc}")
    try:
        ser.write(b"\r\x03\x03")                              # Ctrl-C twice: stop any running program
        time.sleep(0.1)
        ser.reset_input_buffer()
        ser.write(b"\x01")                                    # Ctrl-A: enter raw REPL
        _read_until(ser, b"raw REPL; CTRL-B to exit\r\n>", timeout)
        ser.write(code.encode("utf-8") + b"\x04")            # code, then Ctrl-D to execute
        resp = _read_until(ser, b"\x04>", timeout)
        ser.write(b"\x02")                                    # Ctrl-B: back to the friendly REPL
    except Exception as exc:
        try:
            ser.close()
        except Exception:
            pass
        return _err(f"REPL talk failed on {device}: {exc}")
    finally:
        try:
            ser.close()
        except Exception:
            pass
    body = resp
    if b"OK" in body:
        body = body.split(b"OK", 1)[1]
    out, _, rest = body.partition(b"\x04")
    err, _, _ = rest.partition(b"\x04")
    out_s = out.decode("utf-8", "replace").strip()
    err_s = err.replace(b">", b"").decode("utf-8", "replace").strip()
    if err_s:
        return _err(f"Device raised:\n{err_s}", output=out_s)
    return _ok(out_s or "(ran, no output)", output=out_s)


def _read_until(ser, marker: bytes, timeout: float) -> bytes:
    end = time.monotonic() + timeout
    buf = b""
    while time.monotonic() < end:
        chunk = ser.read(256)
        if chunk:
            buf += chunk
            if marker in buf:
                break
        elif marker in buf:
            break
    return buf


def is_micropython(device: str, **kw) -> bool:
    r = mpy_exec(device, "import sys; print(sys.implementation.name)", **kw)
    return r.get("status") == "success" and "micropython" in (r.get("output", "")).lower()


# ── Serial read-back (verification) ────────────────────────────────────────────────────────────────
def read_serial(device: str, baud: int = 115200, seconds: float = 5.0, max_lines: int = 60,
                _open: Optional[Callable] = None) -> Dict[str, Any]:
    """Open the port and collect what the board prints. Pure observation."""
    import serial                                             # type: ignore
    opener = _open or (lambda: serial.Serial(device, baud, timeout=0.5))
    try:
        ser = opener()
    except Exception as exc:
        return _err(f"Could not open {device} at {baud} baud: {exc}")
    lines: List[str] = []
    end = time.monotonic() + seconds
    try:
        while time.monotonic() < end and len(lines) < max_lines:
            raw = ser.readline()
            if not raw:
                continue
            text = raw.decode("utf-8", "replace").rstrip("\r\n")
            if text:
                lines.append(text)
    finally:
        try:
            ser.close()
        except Exception:
            pass
    if not lines:
        return _err(f"{device} opened but sent nothing in {seconds:.0f}s — is the board running and "
                    f"printing to Serial at {baud} baud?", lines=[])
    return _ok(f"{len(lines)} line(s) from {device}:\n" + "\n".join(lines), lines=lines)


# ── I2C scan ─────────────────────────────────────────────────────────────────────────────────────
_I2C_SCANNER_INO = """#include <Wire.h>
void setup(){Serial.begin(115200);Wire.begin();delay(400);Serial.println("I2CSCAN_BEGIN");
for(uint8_t a=1;a<127;a++){Wire.beginTransmission(a);if(Wire.endTransmission()==0){Serial.print("0x");if(a<16)Serial.print("0");Serial.println(a,HEX);}}
Serial.println("I2CSCAN_END");}
void loop(){}
"""

_MPY_I2C_SCAN = (
    "import machine\n"
    "try:\n"
    "    i2c=machine.I2C(0)\n"
    "except Exception:\n"
    "    i2c=machine.SoftI2C(scl=machine.Pin(22),sda=machine.Pin(21))\n"
    "print([hex(a) for a in i2c.scan()])\n"
)


def _name_addr(addr: int) -> str:
    return f"0x{addr:02X}" + (f" ({_I2C_NAMES[addr]})" if addr in _I2C_NAMES else "")


def i2c_scan(port: Port, flasher: Optional[Callable] = None, **kw) -> Dict[str, Any]:
    """Which I2C devices are wired to the board. Uses the MicroPython REPL when the board runs it
    (fast, non-destructive); otherwise flashes a tiny scanner sketch and reads the result.

    `flasher` lets the caller supply a gated flash function (so the one approval covers it). When it is
    None the scan via flashing is refused rather than writing firmware unasked."""
    if is_micropython(port.device, **{k: v for k, v in kw.items() if k in ("baud", "timeout", "_open")}):
        r = mpy_exec(port.device, _MPY_I2C_SCAN, **{k: v for k, v in kw.items() if k in ("baud", "timeout", "_open")})
        if r.get("status") != "success":
            return r
        import ast
        try:
            addrs = [int(x, 16) for x in ast.literal_eval(r.get("output", "[]"))]
        except Exception:
            return _err(f"Scanned, but could not parse the board's reply: {r.get('output')!r}")
        return _i2c_result(addrs, port, "MicroPython I2C.scan()")
    if flasher is None:
        return {"status": "needs_input", "message": (
            f"{port.summary()} is not running MicroPython, so to scan its I2C bus I have to flash a "
            "small scanner sketch to it (its current program is overwritten). Say \"scan i2c on "
            f"{port.device} and flash the scanner\" to let me, and I'll ask once more before writing.")}
    fr = flasher(_I2C_SCANNER_INO, port)
    if fr.get("status") != "success":
        return fr
    rr = read_serial(port.device, seconds=6.0, **{k: v for k, v in kw.items() if k == "_open"})
    if rr.get("status") != "success":
        return rr
    lines = rr.get("lines", [])
    addrs = [int(ln[2:], 16) for ln in lines if ln.lower().startswith("0x")]
    return _i2c_result(addrs, port, "flashed scanner sketch")


def _i2c_result(addrs: List[int], port: Port, how: str) -> Dict[str, Any]:
    if not addrs:
        return _ok(f"No I2C devices answered on {port.device} ({how}). Check wiring (SDA/SCL, pull-ups, "
                   "power) — a floating bus scans empty.", addresses=[])
    named = ", ".join(_name_addr(a) for a in addrs)
    return _ok(f"{len(addrs)} I2C device(s) on {port.device} ({how}): {named}",
               addresses=[f"0x{a:02X}" for a in addrs])


# ── Flash firmware with PlatformIO ─────────────────────────────────────────────────────────────────
def _resolve_board(port: Port, board_hint: str) -> Tuple[str, str, str]:
    hint = (board_hint or "").strip().lower()
    if hint in _BOARD_ALIASES:
        return _BOARD_ALIASES[hint]
    if port.board:
        return (port.board, port.platform, port.framework)
    return _BOARD_ALIASES["esp32"]


def build_and_upload(source: str, port: Port, board_hint: str = "",
                     runner: Optional[Callable] = None, keep: bool = False) -> Dict[str, Any]:
    """Compile `source` (Arduino C++/.ino text) and upload it to `port` with PlatformIO.

    This is the raw action with no approval of its own — callers gate it (see LiveIoT.flash). `runner`
    is for tests; it stands in for subprocess.run and receives the argv list."""
    pio = find_pio()
    if pio is None and runner is None:
        return _err("PlatformIO (pio) is not installed. Install it with: "
                    "python -m pip install platformio  — then try again.")
    board, platform, framework = _resolve_board(port, board_hint)
    proj = tempfile.mkdtemp(prefix="tom_pio_")
    try:
        os.makedirs(os.path.join(proj, "src"), exist_ok=True)
        with open(os.path.join(proj, "src", "main.cpp"), "w", encoding="utf-8") as fh:
            fh.write(source)
        ini = (f"[env:dev]\nplatform = {platform}\nboard = {board}\nframework = {framework}\n"
               f"upload_port = {port.device}\nmonitor_speed = 115200\n")
        with open(os.path.join(proj, "platformio.ini"), "w", encoding="utf-8") as fh:
            fh.write(ini)
        argv = [pio or "pio", "run", "-e", "dev", "-t", "upload", "-d", proj]
        run = runner or (lambda a: subprocess.run(a, capture_output=True, text=True, timeout=600))
        try:
            proc = run(argv)
        except subprocess.TimeoutExpired:
            return _err("Upload timed out after 10 minutes (compile + flash).")
        except Exception as exc:
            return _err(f"Could not run PlatformIO: {exc}")
        out = f"{getattr(proc, 'stdout', '') or ''}\n{getattr(proc, 'stderr', '') or ''}".strip()
        if getattr(proc, "returncode", 1) == 0:
            return _ok(f"Built and flashed to {port.summary()} (board {board}).",
                       board=board, log=out[-2000:])
        return _err(f"Flash to {port.device} failed (board {board}). PlatformIO said:\n{out[-2000:]}",
                    board=board, log=out[-2000:])
    finally:
        if not keep:
            shutil.rmtree(proj, ignore_errors=True)


# ── Façade used by the agent ─────────────────────────────────────────────────────────────────────
class LiveIoT:
    """Observation is open; flashing and running code on a device pass the policy guard first."""

    def detect(self) -> Dict[str, Any]:
        ports = list_ports()
        if not ports:
            return _ok("No serial/USB devices are connected right now. Plug a board in over USB and ask "
                       "again — I look for ESP32/ESP8266, Arduino, and Raspberry Pi Pico.", ports=[])
        lines = []
        for p in ports:
            extra = ""
            try:
                if p.label and is_micropython(p.device):
                    extra = " — running MicroPython"
            except Exception:
                pass
            lines.append(f"• {p.summary()}{extra}")
        return _ok(f"{len(ports)} device(s) connected:\n" + "\n".join(lines),
                   ports=[p.__dict__ for p in ports])

    def _first_board_port(self) -> Optional[Port]:
        ports = list_ports()
        return next((p for p in ports if p.label), ports[0] if ports else None)

    def _port_for(self, device: str = "") -> Optional[Port]:
        ports = list_ports()
        if device:
            return next((p for p in ports if p.device.lower() == device.lower()), None)
        return self._first_board_port()

    def scan_i2c(self, device: str = "", allow_flash: bool = False) -> Dict[str, Any]:
        port = self._port_for(device)
        if port is None:
            return _err("I don't see that board connected. Run \"detect iot devices\" to list what's "
                        "plugged in.")
        flasher = (lambda src, p: self._gated_flash(src, p, "I2C scanner")) if allow_flash else None
        return i2c_scan(port, flasher=flasher)

    def read(self, device: str = "", seconds: float = 5.0) -> Dict[str, Any]:
        port = self._port_for(device)
        if port is None:
            return _err("No board is connected to read from.")
        return read_serial(port.device, seconds=seconds)

    def _gated_flash(self, source: str, port: Port, what: str) -> Dict[str, Any]:
        """Flashing writes firmware to an external device → DESTRUCTIVE_OR_EXTERNAL, gated like a send."""
        from tom_core.policy.engine import ActionClass
        from tom_core.tools.guard import enforce
        board, _, _ = _resolve_board(port, "")
        dec = enforce("iot.flash", ActionClass.DESTRUCTIVE_OR_EXTERNAL,
                      payload={"port": port.device, "board": board, "what": what, "bytes": str(len(source))},
                      approval_action="iot_flash",
                      summary=(f"Flash {what} to {port.summary()} (board {board}) on {port.device}. "
                               "This overwrites the program currently on the device."))
        if not dec.allowed:
            return dec.refusal({"response_type": "iot_flash"})
        return build_and_upload(source, port, "")

    def flash(self, source: str, device: str = "", board_hint: str = "", what: str = "firmware") -> Dict[str, Any]:
        port = self._port_for(device)
        if port is None:
            return _err("I don't see a board to flash. Run \"detect iot devices\" first, then name the "
                        "port, e.g. \"flash to COM5\".")
        if board_hint:
            b, pf, fw = _resolve_board(port, board_hint)
            port.board, port.platform, port.framework = b, pf, fw
        return self._gated_flash(source, port, what)
