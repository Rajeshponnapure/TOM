"""Network diagnostics toolkit — the legitimate "devices on my wifi / my
network info / scan my ports". Scoped to the local host and private LAN; it
refuses to scan arbitrary public hosts and contains no attack tooling.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools.network_tools import NetworkTools, _is_private_host


@pytest.fixture
def net():
    return NetworkTools()


# ── target scoping ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("host,expected", [
    ("127.0.0.1", True),
    ("localhost", True),
    ("192.168.1.10", True),
    ("10.0.0.5", True),
    ("172.16.4.9", True),
    ("8.8.8.8", False),
    ("1.1.1.1", False),
    ("93.184.216.34", False),
])
def test_private_host_classification(host, expected):
    assert _is_private_host(host) is expected


def test_scan_refuses_public_targets(net):
    res = net.scan_ports("8.8.8.8")
    assert res["status"] == "blocked"


def test_scan_allows_loopback(net):
    # A high port that is almost certainly closed → deterministic empty result.
    res = net.scan_ports("127.0.0.1", ports=[65000])
    assert res["status"] == "success"
    assert res["open_ports"] == []
    assert res["ip"] in ("127.0.0.1",)


# ── read-only diagnostics ────────────────────────────────────────────────────

def test_network_overview_has_hostname(net):
    res = net.network_overview()
    assert res["status"] == "success"
    assert res["hostname"]


def test_list_devices_returns_a_structured_result(net):
    res = net.list_devices()
    assert res["status"] in ("success", "error")
    if res["status"] == "success":
        assert isinstance(res["devices"], list)


def test_wifi_calls_return_a_status(net):
    # On non-Windows these return an explanatory error; either way a dict.
    for res in (net.wifi_status(), net.wifi_profiles()):
        assert "status" in res


# ── routing ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("cmd", [
    "show devices on my wifi",
    "who is connected to my network",
    "what's my ip info",
    "my wifi status",
    "list saved wifi networks",
    "scan ports on 192.168.1.5",
    "scan my ports",
])
def test_router_detects_network_commands(cmd):
    from tools.engine_router import EngineRouter
    assert EngineRouter().detect(cmd) == "network"


def test_run_network_dispatches_port_scan(monkeypatch):
    from tools.engine_router import EngineRouter
    r = EngineRouter()
    calls = {}

    class _Fake:
        def scan_ports(self, host="127.0.0.1"):
            calls["scan"] = host
            return {"status": "success", "open_ports": []}
        def list_devices(self):
            calls["list"] = True
            return {"status": "success"}

    monkeypatch.setattr(r, "_get", lambda key: _Fake())
    r._run_network("scan ports on 192.168.1.7")
    assert calls.get("scan") == "192.168.1.7"
    r._run_network("show devices on my wifi")
    assert calls.get("list") is True
