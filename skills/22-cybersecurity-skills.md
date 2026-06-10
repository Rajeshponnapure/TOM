# Cybersecurity Skills — Mastery Guide

> **Knowledge Base Reference:** Load these files for deeper domain coverage:
> - `knowledge/cybersecurity/linux_windows_mobile.json` — Linux hardening (GrSec, AppArmor), Windows Defender/EDR bypass, Active Directory attacks/defense, iOS/Android mobile security testing (Frida, objection)
> - `knowledge/cybersecurity/exploit_malware_reverse.json` — x64/x86 assembly crash course, Ghidra/IDA reverse engineering workflow, malware analysis (static/dynamic, YARA rules), exploit development (stack overflow, ROP chains, SEH, Metasploit modules)
> - `knowledge/cybersecurity/red_blue_forensics_wireless.json` — Red team C2 infrastructure (Sliver, Covenant), blue team/SOC playbooks, Splunk detection rules, Sigma rules, Volatility memory forensics, Wi-Fi/Bluetooth auditing (Aircrack-ng, Bettercap)
> - `knowledge/cybersecurity/iot_cloud_container_api.json` — AWS/Azure/GCP security auditing, Docker/K8s hardening, secure API design (Node.js, REST), firmware extraction/analysis, Modbus/ICS scanning
> - `knowledge/cybersecurity/advanced_ai_bugbounty_certs.json` — LLM security (prompt injection, extraction), bug bounty recon automation, report templates, home lab setup, browser exploitation, fuzzing (libFuzzer, AFL), certification roadmaps
> - `knowledge/cybersecurity/compliance_reporting_architecture.json` — Zero Trust Architecture (NIST 800-207), GDPR/HIPAA/PCI-DSS compliance checklists, NIST CSF mappings, pentest reporting templates, DevSecOps CI/CD security pipelines, custom security scanners
> - `knowledge/cybersecurity/ethical_hacking.json` — Core penetration testing methodology, Metasploit, nmap, Burp Suite, web app testing

## Overview
Cybersecurity encompasses protecting systems, networks, and data from digital attacks. This guide covers the OWASP Top 10, encryption, authentication, authorization, network security, application security, cloud security, incident response, vulnerability management, and compliance.

---

## OWASP Top 10 (2021)

### A01: Broken Access Control

**Examples:**
- Bypassing access controls by modifying URL parameters
- Accessing admin endpoints without authentication
- IDOR (Insecure Direct Object References): /api/user/12345 returns data for any user

**Prevention:**
`javascript
// BAD: No access check
app.get('/api/user/:id', (req, res) => {
  const user = db.findUser(req.params.id);
  res.json(user);
});

// GOOD: Check authorization
app.get('/api/user/:id', authenticate, (req, res) => {
  if (req.user.id !== req.params.id && !req.user.isAdmin) {
    return res.status(403).json({ error: 'Forbidden' });
  }
  const user = db.findUser(req.params.id);
  res.json(user);
});
`

### A02: Cryptographic Failures

- Storing passwords in plaintext
- Using weak hashing algorithms (MD5, SHA1)
- Not encrypting sensitive data in transit
- Using self-signed or expired certificates

**Prevention:**
`python
import bcrypt

password = b"super_secret"
hashed = bcrypt.hashpw(password, bcrypt.gensalt(rounds=12))
if bcrypt.checkpw(password, hashed):
    print("Password matches")
`

### A03: Injection

**SQL Injection:**
`python
# BAD: String concatenation
query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"

# GOOD: Parameterized query
query = "SELECT * FROM users WHERE username = %s AND password = %s"
cursor.execute(query, (username, password))
`

**NoSQL Injection:**
`javascript
// BAD
db.collection('users').find({ username: req.body.username, password: req.body.password });

// GOOD — validate input types
if (typeof req.body.username !== 'string') throw new Error('Invalid input');
db.collection('users').find({ username: req.body.username, password: req.body.password });
`

### A04: Insecure Design

- Missing rate limiting on authentication
- No password complexity rules
- Sequential order IDs (guessable)
- Trusting client-side validation only

**Prevention:** Threat modeling, rate limiting on auth, server-side validation always, use UUIDs.

### A05: Security Misconfiguration

- Default credentials unchanged, directory listing, verbose errors, CORS misconfiguration

`javascript
app.use(cors({
  origin: ['https://app.example.com'],
  methods: ['GET', 'POST'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  credentials: true,
  maxAge: 86400
}));
`

### A06: Vulnerable and Outdated Components

`ash
npm audit
pip-audit
safety check
# Dependabot / Renovate in CI
`

### A07: Identification and Authentication Failures

`python
from flask_limiter import Limiter
limiter = Limiter(app, key_func=lambda: request.remote_addr)

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    pass
`

### A08: Software and Data Integrity Failures

**Prevention:** Code signing, SBOM, verify signatures, private registries, CI/CD scanning.

### A09: Security Logging and Monitoring

`javascript
const securityLogger = winston.createLogger({
  level: 'warn', format: winston.format.json(),
  defaultMeta: { type: 'security_event' }
});

app.post('/login', async (req, res) => {
  const success = await authenticate(req.body);
  securityLogger.warn('Login attempt', {
    username: req.body.username, ip: req.ip,
    userAgent: req.headers['user-agent'], success,
    timestamp: new Date().toISOString()
  });
});
`

### A10: Server-Side Request Forgery (SSRF)

`python
import ipaddress
def validate_url(url):
    parsed = urlparse(url)
    host = socket.gethostbyname(parsed.hostname)
    ip = ipaddress.ip_address(host)
    if ip.is_private or ip.is_loopback or ip.is_link_local:
        raise ValueError("URL points to internal resource")
    allowed_domains = ['api.example.com', 'data.example.com']
    if parsed.hostname not in allowed_domains:
        raise ValueError("Domain not allowed")
`

---

## Encryption

### AES (Symmetric)

`python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
cipher = Fernet(key)
encrypted = cipher.encrypt(b"Sensitive data")
decrypted = cipher.decrypt(encrypted)
`

### RSA (Asymmetric)

`python
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

encrypted = public_key.encrypt(b"data", padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
decrypted = private_key.decrypt(encrypted, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
`

### Hashing Algorithms

| Algorithm | Output | Use | Status |
|-----------|--------|-----|--------|
| MD5 | 128 bits | Checksums | Broken |
| SHA-1 | 160 bits | Legacy | Deprecated |
| SHA-256 | 256 bits | Signatures | Secure |
| bcrypt | var | Passwords | Secure |
| Argon2 | var | Passwords | Recommended |
| PBKDF2 | var | Key derivation | Secure |

`python
from argon2 import PasswordHasher
ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
hash = ph.hash("my_password")
ph.verify(hash, "my_password")
`

### TLS 1.3 Configuration

`
ginx
server {
    listen 443 ssl http2;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_stapling on;
    ssl_stapling_verify on;
    add_header Strict-Transport-Security "max-age=63072000" always;
}
`

---

## Authentication

### MFA / TOTP

`javascript
const speakeasy = require('speakeasy');
const secret = speakeasy.generateSecret({ name: 'MyApp:user@example.com' });
const verified = speakeasy.totp.verify({
  secret: secret.base32, encoding: 'base32',
  token: userInputToken, window: 1
});
`

### WebAuthn / FIDO2

`javascript
// Registration
const credential = await navigator.credentials.create({
  publicKey: {
    challenge: new Uint8Array(32),
    rp: { name: "MyApp", id: "example.com" },
    user: { id: new Uint8Array(16), name: "user@example.com", displayName: "User" },
    pubKeyCredParams: [{ type: "public-key", alg: -7 }]
  }
});

// Authentication
const assertion = await navigator.credentials.get({
  publicKey: {
    challenge: new Uint8Array(32),
    allowCredentials: [{ type: "public-key", id: credentialId }]
  }
});
`

### OAuth 2.0

Authorization Code Flow:
1. User -> Client -> Auth Server (login)
2. Auth Server -> User -> Redirect with code
3. Client -> Auth Server (code + client_secret)
4. Auth Server -> Client (access_token + refresh_token)
5. Client -> Resource Server (access_token)

`python
from authlib.integrations.flask_client import OAuth
oauth = OAuth(app)
oauth.register(name='google', client_id='ID', client_secret='SECRET',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    client_kwargs={'scope': 'openid email profile'})

@app.route('/login/google')
def login_google():
    return oauth.google.authorize_redirect(url_for('authorize', _external=True))
`

---

## Authorization

### RBAC

`javascript
const roles = {
  admin: ['read', 'write', 'delete', 'manage_users'],
  editor: ['read', 'write'],
  viewer: ['read']
};

function authorize(...allowedRoles) {
  return (req, res, next) => {
    if (allowedRoles.includes(req.user.role)) next();
    else res.status(403).json({ error: 'Insufficient permissions' });
  };
}
`

### ABAC

`python
def can_access(user, resource, action):
    policies = [
        {'effect': 'allow', 'condition': lambda u, r: u.id == r.owner_id},
        {'effect': 'allow', 'condition': lambda u, r: r.is_public and action == 'read'},
        {'effect': 'allow', 'condition': lambda u, r: u.role == 'admin'},
        {'effect': 'deny', 'condition': lambda u, r: True},
    ]
    for policy in policies:
        if policy['condition'](user, resource):
            return policy['effect'] == 'allow'
    return False
`

### OPA (Open Policy Agent)

`ego
package app.authz
default allow = false

allow { input.method == "GET"; input.path == ["api", "users", input.user_id]; input.user.role == "admin" }
allow { input.method == "GET"; input.path == ["api", "public", _] }
`

---

## Network Security

### Firewall (iptables)

`ash
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -A INPUT -i lo -j ACCEPT
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -p tcp --dport 22 -s 10.0.0.0/8 -j ACCEPT
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
`

### Web Application Firewall

`
ginx
server {
    location / {
        modsecurity on;
        modsecurity_rules_file /etc/nginx/modsec/crs/rules.conf;
    }
}
`

### Zero Trust

Principles: Never trust/always verify, least privilege, micro-segmentation, assume breach.

### IDS/IPS Comparison

| System | Type | Method |
|--------|------|--------|
| Snort | NIDS/NIPS | Signature + Protocol |
| Suricata | NIDS/NIPS | Signature + Protocol + Anomaly |
| Zeek | NMS | Protocol analysis |
| Wazuh | HIDS | File integrity, log analysis |

---

## Application Security

### Input Validation (Joi)

`javascript
const schema = Joi.object({
  username: Joi.string().alphanum().min(3).max(30).required(),
  password: Joi.string().min(8).max(128).pattern(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/),
  email: Joi.string().email().required()
});
const { error, value } = schema.validate(req.body);
`

### Output Encoding

`javascript
// HTML context
res.send(escape(userInput));
// JavaScript context
res.send(<script>var name = \;</script>);
// URL context
res.send(<a href="/profile/\">);
`

### CSP Header

`
Content-Security-Policy:
  default-src 'self';
  script-src 'self' https://analytics.example.com;
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https://*.cloudfront.net;
  connect-src 'self' https://api.example.com;
  frame-ancestors 'none';
  form-action 'self';
  upgrade-insecure-requests;
`

### CORS

`python
from flask_cors import CORS
CORS(app, resources={r"/api/*": {"origins": ["https://app.example.com"], "methods": ["GET", "POST"], "allow_headers": ["Content-Type", "Authorization"], "supports_credentials": True}})
`

---

## Cloud Security

### AWS IAM Policy

`json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject", "s3:ListBucket"],
    "Resource": ["arn:aws:s3:::myapp-data", "arn:aws:s3:::myapp-data/*"],
    "Condition": { "IpAddress": { "aws:SourceIp": "10.0.0.0/8" } }
  }, {
    "Effect": "Deny", "Action": "*", "Resource": "*",
    "Condition": { "BoolIfExists": { "aws:SecureTransport": "false" } }
  }]
}
`

### Security Groups vs NACLs

| Feature | Security Group | NACL |
|---------|---------------|------|
| Scope | Instance | Subnet |
| Rules | Allow only | Allow + Deny |
| Stateful | Yes | No |
| Default | Deny inbound | Allow inbound |

### KMS / Secrets Management

`python
import boto3
kms = boto3.client('kms')
def encrypt_data(plaintext):
    response = kms.encrypt(KeyId='alias/myapp-key', Plaintext=plaintext)
    return response['CiphertextBlob'].hex()
`

`yaml
# HashiCorp Vault
vault write secret/myapp db_password="super_secret" api_key="xyz123"
`

---

## Incident Response

### NIST Framework

| Phase | Activities |
|-------|------------|
| Preparation | IR plan, training, runbooks |
| Detection | Monitoring, alerts, threat intel |
| Containment | Isolate systems, block IOCs |
| Eradication | Remove threat, patch |
| Recovery | Restore from backup, validate |
| Lessons Learned | Post-mortem, improve controls |

### Detection Engineering

`python
# Sigma rule example
title: Suspicious PowerShell Execution
detection:
  selection:
    EventID: 4104
    ScriptBlockText|contains:
      - '-EncodedCommand'
      - 'DownloadString'
      - 'Invoke-Mimikatz'
  condition: selection
`

### Containment Playbook

`
1. Identify affected systems (alert triage)
2. Isolate host from network (EDR quarantine)
3. Revoke compromised credentials
4. Block attacker IPs (WAF/firewall)
5. Preserve forensic artifacts
6. Declare incident severity
`

---

## Vulnerability Management

### CVSS Scoring

| Score | Severity | Example |
|-------|----------|---------|
| 9.0-10.0 | Critical | Remote code execution |
| 7.0-8.9 | High | SQL injection |
| 4.0-6.9 | Medium | XSS |
| 0.1-3.9 | Low | Information disclosure |

### Scanning Schedule

- **Daily**: Container image scanning (CI/CD)
- **Weekly**: Internal infrastructure scans
- **Monthly**: External penetration tests
- **Quarterly**: Full attack surface assessment
- **Continuous**: Dependency scanning (Dependabot/Renovate)

### Prioritization Framework

`
Priority = (Severity * Exploitability * AssetValue) / (CompensatingControls)

Factors:
  - CVE score (CVSS)
  - Public exploit available?
  - Asset criticality (crown jewel vs internal tool)
  - Network exposure (internet-facing vs internal)
  - Existing controls (WAF, segmentation)
`

---

## Compliance Frameworks

| Framework | Focus | Key Requirements |
|-----------|-------|------------------|
| SOC 2 | Service organizations | Security, availability, confidentiality |
| ISO 27001 | ISMS | Risk assessment, controls, continuous improvement |
| GDPR | Data privacy | Consent, right to deletion, breach notification |
| HIPAA | Healthcare | PHI protection, BAAs, access controls |
| PCI DSS | Payment cards | Cardholder data protection, quarterly scans |

### GDPR Compliance Checklist

`
[ ] Data Protection Impact Assessment (DPIA)
[ ] Lawful basis for processing documented
[ ] Consent mechanisms (opt-in, withdrawable)
[ ] Data Subject Access Request (DSAR) process
[ ] Breach notification within 72 hours
[ ] Data Protection Officer (DPO) appointed
[ ] Data Processing Agreement (DPA) with vendors
[ ] Right to erasure process
[ ] Data portability capability
[ ] Privacy notice on all data collection points
`

### SOC 2 Controls (Trust Services Criteria)

| Category | Examples |
|----------|----------|
| Security | Firewalls, access controls, encryption |
| Availability | Monitoring, incident response, DR |
| Processing Integrity | Data validation, error handling |
| Confidentiality | Encryption, access controls, NDAs |
| Privacy | Notice, choice, consent, access |

---

## Penetration Testing

### Methodology

`
1. Reconnaissance (passive/active)
2. Scanning (nmap, masscan)
3. Enumeration (dirb, gobuster, nikto)
4. Exploitation (metasploit, custom exploits)
5. Privilege Escalation
6. Lateral Movement
7. Data Exfiltration (proof)
8. Reporting
`

### Common Tools

| Category | Tools |
|----------|-------|
| Recon | Shodan, Censys, theHarvester |
| Scanning | Nmap, Masscan, RustScan |
| Web | Burp Suite, OWASP ZAP, ffuf |
| Exploit | Metasploit, Empire, Cobalt Strike |
| Wireless | Aircrack-ng, Reaver, Kismet |
| Password | Hashcat, John the Ripper |
| OSINT | Maltego, Recon-ng, SpiderFoot |

### Web Testing Checklist

`
[ ] SQL injection (UNION, blind, time-based)
[ ] XSS (reflected, stored, DOM-based)
[ ] CSRF protection testing
[ ] SSRF testing (external callback server)
[ ] File upload (RCE, path traversal)
[ ] IDOR (parameter manipulation)
[ ] JWT security (alg confusion, none alg)
[ ] Rate limiting testing
[ ] CORS misconfiguration
[ ] Subdomain takeover
[ ] Dependency vulnerabilities
[ ] Business logic flaws
`

---

## Security Best Practices

### Password Policy

- Minimum 12 characters
- Encouraged: passphrases over passwords
- No arbitrary complexity rules (mixed case, special chars)
- MFA mandatory for all accounts
- Password manager required
- Regular audit of unused accounts

### Secure Development Lifecycle

`
[ ] Threat modeling in design phase
[ ] Static analysis (SAST) in CI
[ ] Dependency scanning per commit
[ ] Dynamic scanning (DAST) for staging
[ ] Secrets scanning pre-commit
[ ] Code review with security checklist
[ ] Penetration test before major releases
[ ] Bug bounty program
`

### Data Classification

| Level | Examples | Controls |
|-------|----------|----------|
| Public | Marketing materials | No special controls |
| Internal | Emails, org charts | Access control |
| Confidential | Financial data, source code | Encryption, logging |
| Restricted | PII, trade secrets | Encryption, MFA, audit logging |

### Security Architecture Principles

- Defense in depth: multiple layers of security
- Least privilege: minimal access for each role
- Fail secure: deny by default, allow by exception
- Separation of duties: no single person has all privileges
- Secure defaults: most secure option is default
- Complete mediation: every access attempt checked
- Minimize attack surface: fewer features = fewer vulnerabilities
- Zero Trust: never trust, always verify
