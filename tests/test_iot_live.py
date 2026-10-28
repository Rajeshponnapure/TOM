"""Live IoT: port detection, MicroPython REPL, I2C scan, and gated flashing — all with fakes for the
serial port and PlatformIO, so the suite runs with no hardware attached."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools import iot_live
from tools.iot_live import LiveIoT, Port


class FakePortInfo:
    def __init__(self, device, vid, pid, description="dev", hwid="hw"):
        self.device, self.vid, self.pid = device, vid, pid
        self.description, self.hwid = description, hwid


class FakeSerial:
    """A scripted serial port: `script` is the bytes the device would send, in order of reads."""
    def __init__(self, chunks=(), lines=()):
        self._chunks = list(chunks)
        self._lines = list(lines)
        self.written = b""
        self.closed = False

    def write(self, data):
        self.written += data

    def read(self, n=1):
        return self._chunks.pop(0) if self._chunks else b""

    def readline(self):
        return self._lines.pop(0) if self._lines else b""

    def reset_input_buffer(self):
        pass

    def close(self):
        self.closed = True


# ── port detection ────────────────────────────────────────────────────────
def test_list_ports_identifies_known_boards():
    infos = [FakePortInfo("COM5", 0x10C4, 0xEA60), FakePortInfo("COM3", 0x2E8A, 0x0005),
             FakePortInfo("COM9", 0x9999, 0x9999)]
    ports = iot_live.list_ports(_lister=lambda: infos)
    by = {p.device: p for p in ports}
    assert "ESP32" in by["COM5"].label and by["COM5"].board == "esp32dev"
    assert "Pico" in by["COM3"].label
    assert by["COM9"].label == "" and by["COM9"].board == ""        # unknown stays blank, not guessed


def test_detect_reports_nothing_when_no_ports(monkeypatch):
    monkeypatch.setattr(iot_live, "list_ports", lambda *a, **k: [])
    r = LiveIoT().detect()
    assert r["status"] == "success" and r["ports"] == [] and "No serial" in r["message"]


# ── MicroPython raw REPL ───────────────────────────────────────────────────
def _repl_reply(output: bytes):
    # raw REPL handshake marker, then OK + output + 0x04 (no error) + 0x04 + '>'
    return [b"raw REPL; CTRL-B to exit\r\n>", b"OK" + output + b"\x04\x04>"]

def test_mpy_exec_parses_output():
    fake = FakeSerial(chunks=_repl_reply(b"micropython"))
    r = iot_live.mpy_exec("COM3", "print(1)", _open=lambda: fake)
    assert r["status"] == "success" and r["output"] == "micropython"
    assert b"\x01" in fake.written and b"\x04" in fake.written    # entered raw REPL and executed

def test_mpy_exec_surfaces_device_error():
    fake = FakeSerial(chunks=[b"raw REPL; CTRL-B to exit\r\n>",
                              b"OK\x04Traceback: boom\x04>"])
    r = iot_live.mpy_exec("COM3", "x", _open=lambda: fake)
    assert r["status"] == "error" and "boom" in r["message"]


# ── I2C scan ───────────────────────────────────────────────────────────────
def test_i2c_scan_via_micropython(monkeypatch):
    monkeypatch.setattr(iot_live, "is_micropython", lambda *a, **k: True)
    monkeypatch.setattr(iot_live, "mpy_exec",
                        lambda dev, code, **k: {"status": "success", "output": "['0x3c', '0x76']"})
    port = Port(device="COM3", label="Pico (MicroPython)")
    r = iot_live.i2c_scan(port)
    assert r["status"] == "success" and r["addresses"] == ["0x3C", "0x76"]
    assert "OLED" in r["message"] and "BME" in r["message"]        # addresses named

def test_i2c_scan_without_micropython_refuses_to_flash_unasked(monkeypatch):
    monkeypatch.setattr(iot_live, "is_micropython", lambda *a, **k: False)
    port = Port(device="COM5", label="ESP32", board="esp32dev")
    r = iot_live.i2c_scan(port, flasher=None)
    assert r["status"] == "needs_input" and "flash" in r["message"].lower()

def test_i2c_scan_flashes_scanner_when_allowed(monkeypatch):
    monkeypatch.setattr(iot_live, "is_micropython", lambda *a, **k: False)
    monkeypatch.setattr(iot_live, "read_serial",
                        lambda dev, **k: {"status": "success", "lines": ["I2CSCAN_BEGIN", "0x27", "I2CSCAN_END"]})
    flashed = {}
    def fake_flash(src, p):
        flashed["src"] = src
        return {"status": "success", "message": "flashed"}
    port = Port(device="COM5", label="ESP32", board="esp32dev")
    r = iot_live.i2c_scan(port, flasher=fake_flash)
    assert r["status"] == "success" and r["addresses"] == ["0x27"]
    assert "Wire" in flashed["src"]                                # the scanner sketch was flashed


# ── serial read-back ─────────────────────────────────────────────────────
def test_read_serial_collects_lines():
    fake = FakeSerial(lines=[b"Temp: 24.1C\r\n", b"Hum: 55%\r\n", b""])
    r = iot_live.read_serial("COM5", seconds=0.3, _open=lambda: fake)
    assert r["status"] == "success" and r["lines"] == ["Temp: 24.1C", "Hum: 55%"]

def test_read_serial_reports_silence():
    fake = FakeSerial(lines=[])
    r = iot_live.read_serial("COM5", seconds=0.2, _open=lambda: fake)
    assert r["status"] == "error" and "sent nothing" in r["message"]


# ── build + upload ─────────────────────────────────────────────────────────
class FakeProc:
    def __init__(self, rc, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = rc, stdout, stderr

def test_build_and_upload_success_passes_board_and_port(tmp_path):
    seen = {}
    def runner(argv):
        seen["argv"] = argv
        # the temp project dir is argv[-1]; its platformio.ini should name the port
        d = argv[argv.index("-d") + 1]
        seen["ini"] = open(os.path.join(d, "platformio.ini")).read()
        seen["src"] = open(os.path.join(d, "src", "main.cpp")).read()
        return FakeProc(0, stdout="SUCCESS")
    port = Port(device="COM5", label="ESP32", board="esp32dev", platform="espressif32", framework="arduino")
    r = iot_live.build_and_upload("void setup(){} void loop(){}", port, runner=runner)
    assert r["status"] == "success" and r["board"] == "esp32dev"
    assert "upload_port = COM5" in seen["ini"] and "espressif32" in seen["ini"]
    assert "setup()" in seen["src"] and "upload" in seen["argv"]

def test_build_and_upload_reports_failure_log(tmp_path):
    port = Port(device="COM5", board="esp32dev", platform="espressif32", framework="arduino")
    r = iot_live.build_and_upload("x", port, runner=lambda a: FakeProc(1, stderr="error: no board"))
    assert r["status"] == "error" and "no board" in r["message"]


# ── flashing is gated by the policy engine ─────────────────────────────────
def test_flash_is_refused_without_approval(monkeypatch):
    monkeypatch.setattr(iot_live, "list_ports",
                        lambda *a, **k: [Port(device="COM5", label="ESP32", board="esp32dev",
                                              platform="espressif32", framework="arduino")])
    import tom_core.tools.guard as guard
    monkeypatch.setattr(guard, "_approval_manager", None)    # no approval channel → blocked
    called = {"built": False}
    monkeypatch.setattr(iot_live, "build_and_upload", lambda *a, **k: called.__setitem__("built", True))
    r = LiveIoT().flash("void setup(){}", device="COM5")
    assert r["status"] in ("blocked", "cancelled") and called["built"] is False

def test_flash_proceeds_after_approval(monkeypatch):
    monkeypatch.setattr(iot_live, "list_ports",
                        lambda *a, **k: [Port(device="COM5", label="ESP32", board="esp32dev",
                                              platform="espressif32", framework="arduino")])
    import tom_core.tools.guard as guard
    from tools.approval import ApprovalManager
    mgr = ApprovalManager()
    mgr.provider = lambda req: True
    monkeypatch.setattr(guard, "_approval_manager", mgr)
    monkeypatch.setattr(iot_live, "build_and_upload",
                        lambda src, port, hint="": {"status": "success", "message": "flashed", "board": port.board})
    r = LiveIoT().flash("void setup(){}", device="COM5")
    assert r["status"] == "success" and "flashed" in r["message"]
