"""Create google-credentials_token.json (the Gmail OAuth token TOM uses to read and send mail).

Run this ON YOUR OWN COMPUTER, from the TOM folder - it opens your browser so you can sign in to
Google and click Allow. Nobody else (including an AI assistant) can do that step for you, and the
token it writes is a password-equivalent: keep it out of git (*token*.json is already ignored).

    python tools/generate_gmail_token.py
    python tools/generate_gmail_token.py --credentials C:\\path\\google-credentials.json
    python tools/generate_gmail_token.py --no-browser      # prints a URL to open instead
    python tools/generate_gmail_token.py --manual          # paste the final browser URL yourself
    python tools/generate_gmail_token.py --skip-verify     # don't test the token against Gmail

If the browser ends on "This site can't be reached ... localhost refused to connect", nothing is
wrong with your sign-in: the page just couldn't reach the script. Press Ctrl+C (or wait) and the
script asks you to paste that page's address-bar URL, which contains everything it needs.

It uses the same settings as TOM (.env: GMAIL_CREDENTIALS_FILE, GMAIL_TOKEN_FILE, EMAIL_ADDRESS,
IMAP_HOST) and the same scope, so the token it writes is exactly the file TOM looks for.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SCOPES = ["https://mail.google.com/"]          # same scope as tools/email_tools.py
DEFAULT_CREDENTIALS = "google-credentials.json"


def resolve_paths(credentials: Optional[str] = None, token: Optional[str] = None) -> tuple[Path, Path]:
    """(client-secret file, token file) - explicit args, else .env, else TOM's defaults."""
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    def _abs(value: str) -> Path:
        path = Path(os.path.expandvars(os.path.expanduser(value)))
        return path if path.is_absolute() else ROOT / path

    cred_path = _abs(credentials or os.environ.get("GMAIL_CREDENTIALS_FILE") or DEFAULT_CREDENTIALS)
    explicit_token = token or os.environ.get("GMAIL_TOKEN_FILE")
    # TOM's own default (EmailTools._default_gmail_token_file): "<credentials name>_token.json"
    token_path = _abs(explicit_token) if explicit_token else cred_path.with_name(cred_path.stem + "_token.json")
    return cred_path, token_path


def check_client_secret(path: Path) -> str:
    """'' if `path` is a usable OAuth *desktop* client file, else what is wrong."""
    if not path.is_file():
        return (f"I can't find the client file at {path}\n"
                f"  Download it from Google Cloud Console > APIs & Services > Credentials > your OAuth client "
                f"(type: Desktop app) > Download JSON, and save it there (see docs/GMAIL_OAUTH_SETUP.md).")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return f"{path} is not valid JSON ({exc})."
    if "installed" in data:
        return ""
    if "web" in data:
        return ("This is a *Web application* client. TOM needs a *Desktop app* client: create a new OAuth "
                "client with application type 'Desktop app' and download that JSON.")
    if data.get("type") in ("service_account", "authorized_user"):
        return f"This is a '{data['type']}' file, not an OAuth client secret ('installed' Desktop client)."
    return "This doesn't look like a Google OAuth client-secret file (no 'installed' section)."


def write_token(creds, token_path: Path) -> None:
    """Save the token where TOM expects it, readable only by you where the OS supports it."""
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    try:
        token_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def verify_token(token_path: Path, email_address: str, imap_host: str = "imap.gmail.com") -> str:
    """Log in to Gmail over IMAP with the saved token. '' on success, else the reason it failed."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from imapclient import IMAPClient

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds.valid:
        if creds.refresh_token:
            creds.refresh(Request())
        else:
            return "The token has no refresh token, so it can't be renewed - generate it again."
    if not email_address:
        return "EMAIL_ADDRESS is not set in .env (TOM needs it to log in), so I could not test the token."
    with IMAPClient(imap_host, ssl=True) as client:
        client.oauth2_login(email_address, creds.token)
        client.select_folder("INBOX", readonly=True)
    return ""


LOOPBACK = "127.0.0.1"      # not "localhost": that can resolve to IPv6 (::1) while the script listens on IPv4


def exchange_pasted_response(flow, pasted: str):
    """Finish the sign-in from what the user pasted: the full redirected URL (or just the code)."""
    pasted = (pasted or "").strip().strip('"').strip("'")
    if not pasted:
        raise ValueError("Nothing was pasted.")
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")     # the redirect is http://127.0.0.1 by design
    if pasted.lower().startswith("http"):
        flow.fetch_token(authorization_response="https" + pasted[pasted.index(":"):])   # oauthlib insists on https
    else:
        flow.fetch_token(code=pasted)
    return flow.credentials


def manual_sign_in(flow, input_fn=None):
    """Sign in without the script's local web server: open the URL, sign in, paste the final URL back."""
    if not flow.redirect_uri:
        flow.redirect_uri = f"http://{LOOPBACK}:8080/"
        url, _ = flow.authorization_url(access_type="offline", prompt="consent")
        print("\nOpen this address in your browser and sign in:\n\n" + url + "\n")
    else:
        print("\nUse the sign-in address printed above (open it again if you closed it).")
    print("After you click Allow, the browser may show 'This site can't be reached' - that is expected.\n"
          "Copy the WHOLE address from the browser's address bar (it starts with "
          f"http://{LOOPBACK}:... and contains code=...) and paste it here.\n")
    return exchange_pasted_response(flow, (input_fn or input)("Paste the URL here: "))


def sign_in(flow, *, manual: bool = False, open_browser: bool = True, timeout: int = 180, input_fn=None):
    """Google sign-in via a local listener, with a paste-the-URL fallback if that can't work."""
    if manual:
        return manual_sign_in(flow, input_fn)
    try:
        # access_type=offline + prompt=consent make Google return a refresh token every time.
        return flow.run_local_server(host=LOOPBACK, bind_addr=LOOPBACK, port=0, open_browser=open_browser,
                                     timeout_seconds=timeout, access_type="offline", prompt="consent")
    except KeyboardInterrupt:
        print("\nStopped waiting for the browser.")
    except Exception as exc:                                     # timeout, port in use, blocked loopback ...
        print(f"\nThe browser never reached this script ({exc.__class__.__name__}).")
    return manual_sign_in(flow, input_fn)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate TOM's Gmail OAuth token (google-credentials_token.json).")
    parser.add_argument("--credentials", help="path to the OAuth client JSON (default: .env GMAIL_CREDENTIALS_FILE)")
    parser.add_argument("--token", help="where to write the token (default: <credentials>_token.json)")
    parser.add_argument("--no-browser", action="store_true", help="print the sign-in URL instead of opening a browser")
    parser.add_argument("--manual", action="store_true",
                        help="skip the local listener: open the URL yourself and paste the final address back")
    parser.add_argument("--timeout", type=int, default=180, help="seconds to wait for the browser (default 180)")
    parser.add_argument("--skip-verify", action="store_true", help="don't test the new token against Gmail")
    parser.add_argument("--force", action="store_true", help="replace an existing token without asking")
    args = parser.parse_args(argv)

    cred_path, token_path = resolve_paths(args.credentials, args.token)
    problem = check_client_secret(cred_path)
    if problem:
        print(f"\nCannot continue: {problem}")
        return 2
    if token_path.exists() and not args.force:
        answer = input(f"{token_path} already exists. Replace it? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Kept the existing token.")
            return 0

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Missing dependency. Run: pip install google-auth-oauthlib google-auth imapclient")
        return 2

    print(f"Client file : {cred_path}\nToken file  : {token_path}\n")
    print("A browser window will open. Sign in with the Gmail account TOM should use and click Allow.")
    print("If the page then says 'This site can't be reached', come back here and press Ctrl+C - I'll ask for that page's URL.")
    print("(If Google says the app isn't verified: Advanced > Go to <app> (unsafe) - it's your own client.)\n")
    flow = InstalledAppFlow.from_client_secrets_file(str(cred_path), scopes=SCOPES)
    try:
        creds = sign_in(flow, manual=args.manual, open_browser=not args.no_browser, timeout=args.timeout)
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled. No token was written.")
        return 1
    except Exception as exc:
        print(f"\nSign-in failed: {exc.__class__.__name__}: {exc}\n"
              f"If it mentions access_denied, add your Gmail address under Google Cloud > Audience > Test users.")
        return 1
    if not creds.refresh_token:
        print("Google did not return a refresh token, so this token would stop working within an hour. "
              "Remove TOM from https://myaccount.google.com/permissions and run this again.")
        return 3
    write_token(creds, token_path)
    print(f"\nSaved {token_path}")

    if args.skip_verify:
        return 0
    try:
        problem = verify_token(token_path, os.environ.get("EMAIL_ADDRESS", ""),
                               os.environ.get("IMAP_HOST", "imap.gmail.com"))
    except Exception as exc:                    # network, wrong account, IMAP disabled ...
        problem = f"{exc.__class__.__name__}: {exc}"
    if problem:
        print(f"\nThe token was saved, but the Gmail test failed: {problem}\n"
              f"Check that EMAIL_ADDRESS in .env is the account you just signed in with and that IMAP is "
              f"enabled (Gmail > Settings > Forwarding and POP/IMAP).")
        return 4
    print("Gmail login with the new token works. TOM can now read and send mail.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
