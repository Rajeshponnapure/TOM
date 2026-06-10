import os
import datetime
import json
import re
import socket
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def safe_print(message: str):
    print(message.encode("ascii", errors="ignore").decode("ascii"))


class SafetyGuards:
    """
    Complete safety system for Tom autonomous agent.
    Prevents unauthorized file deletion, email sending without approval,
    and system modification.

    Enhanced with:
    - Website legitimacy checking
    - User detail sharing rules
    - Context-aware security decisions
    - Full audit trail
    """

    TRUSTED_DOMAINS = {
        "google.com", "gmail.com", "accounts.google.com", "mail.google.com",
        "whatsapp.com", "web.whatsapp.com",
        "github.com", "gitlab.com", "bitbucket.org",
        "microsoft.com", "login.microsoftonline.com", "outlook.com", "office.com",
        "facebook.com", "instagram.com", "linkedin.com",
        "twitter.com", "x.com",
        "youtube.com", "youtu.be",
        "slack.com", "discord.com", "telegram.org",
        "zoom.us", "teams.microsoft.com",
        "notion.so", "notion.com",
        "spotify.com", "netflix.com",
        "amazon.in", "amazon.com", "flipkart.com",
        "paytm.com", "phonepe.com", "googlepay.google.com",
        "localhost", "127.0.0.1",
        "stackoverflow.com", "stackexchange.com",
        "medium.com", "dev.to", "hashnode.com",
        "npmjs.com", "pypi.org", "docker.com",
        "chatgpt.com", "openai.com", "anthropic.com",
        "claude.ai",
    }

    BLOCKED_DOMAINS = {
        "bit.ly", "tinyurl.com", "shorturl.at", "goo.gl",
        "malware-sites", "phishing-example.com",
    }

    def __init__(self):
        self.log_file = os.path.join(
            os.getcwd(), "tom_logs", "safety_log.txt"
        )
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        self.blocked_actions = {
            "delete_files": True,
            "send_emails_without_approval": True,
            "install_software": True,
            "modify_system32": True,
            "access_cryptocurrency": True,
        }
        self.user_profile = self._load_user_profile()

    def _load_user_profile(self) -> Dict[str, Any]:
        profile_path = os.path.join(os.getcwd(), "tom_brain", "user_profile.json")
        try:
            if os.path.exists(profile_path):
                with open(profile_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_user_profile(self):
        profile_path = os.path.join(os.getcwd(), "tom_brain", "user_profile.json")
        try:
            os.makedirs(os.path.dirname(profile_path), exist_ok=True)
            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(self.user_profile, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save user profile: {e}")

    def log_action(self, action: str, target: str = "",
                   status: str = "SUCCESS", message: str = ""):
        """Logs all Tom actions with timestamp"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record = f"[{timestamp}] {action}: [{status.upper()}] | Target: {target} | Note: {message}\n"

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(record)
        except Exception as e:
            print(f"[Safety Error] Could not log action: {e}")

    async def is_action_safe(self, action_name: str, target: Optional[str] = None) -> Dict[str, Any]:
        """
        Checks if an action is safe to execute.
        Returns dict with approval status and required confirmations.
        Uses keyword detection to catch dangerous actions in user commands.
        """
        result = {
            "safe": True,
            "requires_approval": False,
            "action_name": action_name,
            "message": ""
        }

        action_lower = action_name.lower()

        hard_blocked = {
            "modify_system32": ["system32"],
            "access_cryptocurrency": ["crypto", "bitcoin", "wallet", "send money"],
        }
        approval_required = {
            "delete_files": ["delete ", "erase ", "unlink "],
            "send_emails_without_approval": ["send email", "send mail", "email now"],
            "install_software": ["install software", "install package", "pip install"],
        }

        for block_key, keywords in hard_blocked.items():
            if any(kw in action_lower for kw in keywords):
                result["safe"] = False
                result["requires_approval"] = False
                result["message"] = f"Action blocked: '{action_name}' matches '{keywords[0]}' which is permanently restricted."
                break

        if result["safe"]:
            for block_key, keywords in approval_required.items():
                if any(kw in action_lower for kw in keywords):
                    result["requires_approval"] = True
                    result["message"] = f"Action '{action_name}' requires approval before proceeding."
                    break

        self.log_action(
            action=action_name,
            target=target or "unknown",
            status="REQUESTED" if not result["safe"] else "APPROVED"
        )

        return result

    async def require_user_confirmation(self, action: str, details: Dict[str, Any]) -> bool:
        """
        Requests user confirmation for sensitive actions.
        Returns True only if user approves.
        """
        safe_print(f"\nTOM SAFETY ALERT")
        safe_print(f"Action Requested: {action}")
        safe_print(f"Details: {details}")
        safe_print("Type 'yes' to proceed or 'no' to cancel.\n")

        try:
            response = input("User Input: ").strip().lower()
            return response in ["yes", "y", "confirm"]
        except KeyboardInterrupt:
            print("\n[User cancelled]")
            return False

    # ── Website Legitimacy ──────────────────────────────────────────────

    def extract_domain(self, url: str) -> str:
        """Extract clean domain from URL."""
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        domain = domain.lower().strip()
        if domain.startswith("www."):
            domain = domain[4:]
        if ":" in domain:
            domain = domain.split(":")[0]
        return domain

    def analyze_website(self, url: str) -> Dict[str, Any]:
        """
        Analyze a website URL for safety and legitimacy.
        Returns a comprehensive safety analysis.
        """
        domain = self.extract_domain(url)
        analysis = {
            "domain": domain,
            "url": url,
            "trust_level": "unknown",
            "score": 50,
            "flags": [],
            "recommendation": "proceed_with_caution",
        }

        if domain in self.TRUSTED_DOMAINS:
            analysis["trust_level"] = "trusted"
            analysis["score"] = 95
            analysis["recommendation"] = "safe"
            analysis["flags"].append("known_trusted_domain")
            return analysis

        if domain in self.BLOCKED_DOMAINS:
            analysis["trust_level"] = "blocked"
            analysis["score"] = 5
            analysis["recommendation"] = "block"
            analysis["flags"].append("known_blocked_domain")
            return analysis

        if domain == "localhost" or domain == "127.0.0.1":
            analysis["trust_level"] = "local"
            analysis["score"] = 90
            analysis["recommendation"] = "safe"
            analysis["flags"].append("localhost")
            return analysis

        analysis["flags"].append("unknown_domain")

        parsed = urlparse(url)
        if parsed.scheme == "https":
            analysis["score"] += 15
            analysis["flags"].append("has_https")
        else:
            analysis["score"] -= 10
            analysis["flags"].append("no_https")

        suspicious_patterns = [
            (r'login\.\w+\.\w+\.\w+', "suspicious_subdomain"),
            (r'secure-', "fake_security_prefix"),
            (r'account-', "fake_account_prefix"),
            (r'verify', "verification_page"),
            (r'-secure\.', "fake_secure_domain"),
            (r'[0-9]{4,}', "numbers_in_domain"),
        ]
        for pattern, flag in suspicious_patterns:
            if re.search(pattern, domain):
                analysis["score"] -= 20
                analysis["flags"].append(flag)

        if len(domain.split(".")) > 3:
            analysis["score"] -= 10
            analysis["flags"].append("many_subdomains")

        tld = domain.split(".")[-1] if "." in domain else ""
        risky_tlds = {"tk", "ml", "ga", "cf", "gq"}
        if tld in risky_tlds:
            analysis["score"] -= 15
            analysis["flags"].append("risky_tld")

        if analysis["score"] >= 70:
            analysis["trust_level"] = "likely_safe"
            analysis["recommendation"] = "safe"
        elif analysis["score"] >= 40:
            analysis["trust_level"] = "uncertain"
            analysis["recommendation"] = "proceed_with_caution"
        else:
            analysis["trust_level"] = "suspicious"
            analysis["recommendation"] = "block"

        return analysis

    def validate_url(self, url: str) -> bool:
        """Basic URL validation."""
        if "localhost" in url:
            return True
        ip_pattern = r'^(https?:\/\/)?(\d{1,3}\.){3}\d{1,3}(:\d+)?(\/.*)?$'
        if re.match(ip_pattern, url):
            return True
        domain_pattern = r'^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$'
        return bool(re.match(domain_pattern, url))

    # ── User Detail Sharing Security ────────────────────────────────────

    def can_share_detail(self, detail_name: str, url: str, purpose: str = "") -> Dict[str, Any]:
        """
        Check if a user detail can be shared on a given website.
        Applies multi-layer security checks before allowing detail release.

        Returns:
            {"allowed": bool, "requires_approval": bool, "reason": str, "security_level": int}
        """
        result = {
            "allowed": False,
            "requires_approval": True,
            "reason": "",
            "security_level": 0,
        }

        domain = self.extract_domain(url)
        detail_lower = detail_name.lower()

        detail_sensitivity = {
            "name": 1,
            "email": 2,
            "phone": 3,
            "mobile": 3,
            "address": 4,
            "city": 1,
            "state": 1,
            "zip": 2,
            "pincode": 2,
            "password": 5,
            "credit card": 5,
            "payment": 5,
            "aadhar": 5,
            "pan": 5,
            "ssn": 5,
        }
        sensitivity = detail_sensitivity.get(detail_lower, 3)

        site_analysis = self.analyze_website(url)
        trust_level = site_analysis.get("trust_level", "unknown")

        if site_analysis.get("recommendation") == "block":
            result["allowed"] = False
            result["reason"] = f"Website '{domain}' is blocked by security policy"
            result["security_level"] = 5
            return result

        allowed = False
        requires_approval = True

        if trust_level == "trusted":
            allowed = True
            requires_approval = sensitivity >= 4
            result["reason"] = f"Trusted website: {domain}"
        elif trust_level == "local":
            allowed = True
            requires_approval = sensitivity >= 5
            result["reason"] = f"Local server: {domain}"
        elif trust_level == "likely_safe":
            allowed = sensitivity <= 2
            requires_approval = sensitivity >= 2
            result["reason"] = f"Unknown but likely safe website: {domain}"
        else:
            allowed = False
            requires_approval = True
            result["reason"] = f"Unverified website: {domain}. Cannot share {detail_name}."

        result["allowed"] = allowed
        result["requires_approval"] = requires_approval
        result["security_level"] = sensitivity

        self.log_action(
            "DETAIL_SHARE_CHECK",
            target=f"{detail_name}@{domain}",
            status="ALLOWED" if allowed else "DENIED",
            message=f"Sensitivity: {sensitivity}/5, Website trust: {trust_level}, Purpose: {purpose}",
        )

        return result

    def get_detail_for_site(self, detail_name: str, url: str, purpose: str = "") -> Dict[str, Any]:
        """
        Get a user detail for use on a specific website.
        Only returns the value if the security check passes.
        """
        check = self.can_share_detail(detail_name, url, purpose)
        if not check["allowed"]:
            return {
                "status": "denied",
                "value": None,
                "reason": check["reason"],
                "requires_approval": check.get("requires_approval", True),
            }

        profile = self._load_user_profile()
        detail_key = detail_name.lower()
        direct = profile.get(detail_key)
        if direct:
            return {"status": "approved", "value": direct, "reason": check["reason"]}

        field_mapping = {
            "name": "name",
            "email": "email",
            "phone": "phone",
            "mobile": "phone",
            "address": "address",
            "city": "city",
            "state": "state",
            "zip": "zip",
            "pincode": "zip",
        }
        mapped_key = field_mapping.get(detail_key)
        if mapped_key and mapped_key in profile:
            return {"status": "approved", "value": profile[mapped_key], "reason": check["reason"]}

        return {"status": "not_found", "value": None, "reason": f"Detail '{detail_name}' not found in profile"}

    # ── Store User Details ──────────────────────────────────────────────

    async def store_user_detail(self, key: str, value: str) -> Dict[str, Any]:
        """Securely store a user detail in the profile."""
        if not value or not key:
            return {"status": "error", "message": "Key and value required"}

        key_lower = key.lower().strip()
        value_clean = value.strip()

        self.user_profile[key_lower] = value_clean
        self._save_user_profile()

        self.log_action(
            "STORE_USER_DETAIL",
            target=key_lower,
            status="SUCCESS",
            message=f"Stored {key_lower}",
        )
        return {"status": "success", "message": f"Stored {key_lower}"}

    async def remember_user_details(self, command: str) -> Dict[str, Any]:
        """Extract and store user details from a natural language command."""
        patterns = {
            "name": r"(?:my name is|i am|call me|i'm)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            "email": r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
            "phone": r"(\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9})",
            "address": r"(?:address is|live at|residence)\s+(.+?)(?:\.|$)",
            "city": r"(?:from|in|city of)\s+([A-Z][a-zA-Z]+)",
        }

        stored = []
        for key, pattern in patterns.items():
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                value = match.group(1).strip() if match.lastindex else match.group(0).strip()
                if value and key not in self.user_profile:
                    self.user_profile[key] = value
                    stored.append(key)

        if stored:
            self._save_user_profile()
            self.log_action("REMEMBER_DETAILS", target=",".join(stored), status="SUCCESS")
            return {"status": "success", "stored": stored, "message": f"Remembered: {', '.join(stored)}"}

        return {"status": "nothing_to_store", "message": "No new details found in command"}

    # ── Basic Validation ────────────────────────────────────────────────

    def validate_email(self, email: str) -> bool:
        """Basic email validation."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def check_file_path_safe(self, path: str) -> bool:
        """Prevents accessing dangerous system folders."""
        unsafe_paths = [
            "c:\\windows\\",
            "c:\\program files\\",
            "c:\\programdata\\",
            "/sys/",
            "/proc/"
        ]
        path_lower = path.lower()
        for unsafe in unsafe_paths:
            if unsafe in path_lower:
                return False
        return True
