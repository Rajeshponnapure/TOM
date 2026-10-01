"""
Network & device diagnostics for TOM — the legitimate realization of
"show me the devices on my wifi / my network info".

Everything here is standard network-ADMIN work, scoped to the machine TOM runs
on and the LAN it is already connected to:

  * list_devices()   — who is on my network (ARP table of the local subnet)
  * wifi_status()    — my current WiFi connection (SSID, signal, state)
  * wifi_profiles()  — the WiFi networks THIS machine already knows
  * network_overview() — my IP/hostname/adapters
  * scan_ports(host) — a TCP connect scan, restricted to loopback / private-LAN
                        hosts (your own devices), never arbitrary public targets

It contains NO attack tooling: no WiFi-password cracking, no deauth, no device
takeover, no credential capture. Those cannot be constrained at runtime to
systems the user owns, so they are intentionally absent. Subprocess calls never
use shell=True (project security rule) and always time out.
"""
from __future__ import annotations

import ipaddress
import os
import re
import socket
import subprocess
from typing import Any, Dict, List, Optional

# Hide the console window for the helper processes on Windows.
_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _run(args: List[str], timeout: float = 15.0) -> str:
    """Run a diagnostic command (arg list, never a shell string) and return stdout.

    Decodes as UTF-8 with errors="replace": Windows tools like netsh emit bytes
    the locale codec (cp1252) cannot decode, which otherwise raises
    UnicodeDecodeError in subprocess's reader thread. We only parse ASCII field
    names, so replacement is harmless.
    """
    try:
        proc = subprocess.run(args, capture_output=True, timeout=timeout,
                              creationflags=_NO_WINDOW, encoding="utf-8",
                              errors="replace")
        return proc.stdout or ""
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def _is_private_host(host: str) -> bool:
    """True when host is loopback / link-local / RFC-1918 (one of your devices)."""
    h = (host or "").strip()
    if not h:
        return False
    if h.lower() in ("localhost", socket.gethostname().lower()):
        return True
    try:
        ip = ipaddress.ip_address(h)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        # A bare hostname that resolves to a private address is still local.
        try:
            resolved = socket.gethostbyname(h)
            ip = ipaddress.ip_address(resolved)
            return ip.is_private or ip.is_loopback or ip.is_link_local
        except (OSError, ValueError):
            return False


class NetworkTools:
    """Read-only network diagnostics for the local host and its LAN."""

    # ── Devices on the local network ─────────────────────────────────────
    def list_devices(self) -> Dict[str, Any]:
        """Devices seen on the local network, from the system ARP table.

        The ARP table is populated by normal traffic; it is the same list a
        router's admin page shows. No packets are forged and nothing is probed
        beyond the local subnet.
        """
        out = _run(["arp", "-a"]) if os.name == "nt" else (_run(["ip", "neigh"]) or _run(["arp", "-a"]))
        if not out.strip():
            return {"status": "error",
                    "message": "Could not read the ARP table on this machine."}
        devices: List[Dict[str, str]] = []
        mac_re = re.compile(r"([0-9a-fA-F]{2}([:-])[0-9a-fA-F]{2}(\2[0-9a-fA-F]{2}){4})")
        ip_re = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")
        for line in out.splitlines():
            ipm = ip_re.search(line)
            macm = mac_re.search(line)
            if not ipm or not macm:
                continue
            ip = ipm.group(1)
            mac = macm.group(1).lower().replace("-", ":")
            if ip.endswith(".255") or ip.startswith("224.") or mac == "ff:ff:ff:ff:ff:ff":
                continue  # broadcast / multicast, not a device
            host = ""
            try:
                host = socket.gethostbyaddr(ip)[0]
            except (OSError, socket.herror):
                host = ""
            devices.append({"ip": ip, "mac": mac, "hostname": host})
        # De-duplicate by IP, preserve order.
        seen, unique = set(), []
        for d in devices:
            if d["ip"] in seen:
                continue
            seen.add(d["ip"])
            unique.append(d)
        lines = [f"{d['ip']:<16} {d['mac']:<18} {d['hostname']}".rstrip() for d in unique]
        msg = (f"{len(unique)} device(s) on your local network:\n"
               + "\n".join(lines)) if unique else "No devices found in the ARP table."
        return {"status": "success", "response_type": "network_devices",
                "message": msg, "devices": unique, "count": len(unique)}

    # ── WiFi (this machine) ──────────────────────────────────────────────
    def wifi_status(self) -> Dict[str, Any]:
        """Current WiFi connection of this machine (SSID, signal, state)."""
        if os.name != "nt":
            return {"status": "error",
                    "message": "WiFi status uses Windows 'netsh'; not available on this OS."}
        out = _run(["netsh", "wlan", "show", "interfaces"])
        if not out.strip():
            return {"status": "error",
                    "message": "Could not read WiFi interface info (is WiFi present/enabled?)."}
        fields = {}
        for key in ("Name", "State", "SSID", "Signal", "Radio type", "Channel",
                    "Receive rate (Mbps)", "Transmit rate (Mbps)", "Authentication"):
            m = re.search(rf"^\s*{re.escape(key)}\s*:\s*(.+)$", out, re.MULTILINE)
            if m:
                fields[key] = m.group(1).strip()
        msg = "Your WiFi connection:\n" + "\n".join(f"  {k}: {v}" for k, v in fields.items())
        return {"status": "success", "response_type": "wifi_status",
                "message": msg if fields else out.strip(), "fields": fields}

    def wifi_profiles(self) -> Dict[str, Any]:
        """WiFi networks THIS machine already knows (saved profiles).

        Lists profile names only. It does NOT dump saved passwords — recovering
        a stored key is a separate, sensitive action left to Windows itself.
        """
        if os.name != "nt":
            return {"status": "error",
                    "message": "WiFi profiles use Windows 'netsh'; not available on this OS."}
        out = _run(["netsh", "wlan", "show", "profiles"])
        names = re.findall(r":\s*(.+)$", out, re.MULTILINE)
        names = [n.strip() for n in names if n.strip() and "Profiles on interface" not in n]
        msg = (f"{len(names)} saved WiFi network(s) on this machine:\n"
               + "\n".join(f"  - {n}" for n in names)) if names else "No saved WiFi profiles found."
        return {"status": "success", "response_type": "wifi_profiles",
                "message": msg, "profiles": names}

    # ── Host network overview ────────────────────────────────────────────
    def network_overview(self) -> Dict[str, Any]:
        """This machine's hostname and local IP addresses."""
        hostname = socket.gethostname()
        ips: List[str] = []
        try:
            for info in socket.getaddrinfo(hostname, None):
                addr = info[4][0]
                if addr not in ips and not addr.startswith("fe80"):
                    ips.append(addr)
        except OSError:
            pass
        # Primary outbound IP (no traffic actually sent).
        primary = ""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            primary = s.getsockname()[0]
            s.close()
        except OSError:
            pass
        msg = (f"Host: {hostname}\n"
               f"Primary IP: {primary or 'unknown'}\n"
               f"All addresses: {', '.join(ips) if ips else 'n/a'}")
        return {"status": "success", "response_type": "network_overview",
                "message": msg, "hostname": hostname, "primary_ip": primary, "addresses": ips}

    # ── Port scan (own / private hosts only) ─────────────────────────────
    _COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445,
                     3306, 3389, 5432, 5900, 8000, 8080, 8443]

    def scan_ports(self, host: str = "127.0.0.1",
                   ports: Optional[List[int]] = None,
                   timeout: float = 0.4) -> Dict[str, Any]:
        """TCP connect-scan of common ports on one of YOUR OWN hosts.

        Restricted to loopback / private-LAN targets on purpose: scanning
        arbitrary public hosts is out of scope. This is an ordinary connect scan
        (the OS three-way handshake) — no stealth, no evasion.
        """
        host = (host or "127.0.0.1").strip()
        if not _is_private_host(host):
            return {"status": "blocked",
                    "message": (f"'{host}' is not a loopback or private-LAN address. "
                                "TOM only scans your own devices (localhost or your "
                                "home/office network), not arbitrary public hosts.")}
        try:
            target_ip = socket.gethostbyname(host)
        except OSError:
            return {"status": "error", "message": f"Could not resolve '{host}'."}
        ports = ports or self._COMMON_PORTS
        open_ports: List[int] = []
        for port in ports:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            try:
                if s.connect_ex((target_ip, port)) == 0:
                    open_ports.append(port)
            except OSError:
                pass
            finally:
                s.close()
        msg = (f"Open TCP ports on {host} ({target_ip}): "
               + (", ".join(str(p) for p in open_ports) if open_ports else "none of the common ports"))
        return {"status": "success", "response_type": "port_scan",
                "message": msg, "host": host, "ip": target_ip, "open_ports": open_ports}
