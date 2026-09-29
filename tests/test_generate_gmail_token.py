"""The token generator: paths, client-file checks, and the file it writes (Google's browser step is faked)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import stat
import types

import pytest

from tools import generate_gmail_token as gen

DESKTOP = {"installed": {"client_id": "id.apps.googleusercontent.com", "client_secret": "s",
                         "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                         "token_uri": "https://oauth2.googleapis.com/token", "redirect_uris": ["http://localhost"]}}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in ("GMAIL_CREDENTIALS_FILE", "GMAIL_TOKEN_FILE", "EMAIL_ADDRESS"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)


def test_default_token_name_matches_what_tom_looks_for(tmp_path):
    from tools.email_tools import EmailTools
    cred = tmp_path / "google-credentials.json"
    _, token = gen.resolve_paths(str(cred))
    assert token == tmp_path / "google-credentials_token.json"
    os.environ["GMAIL_CREDENTIALS_FILE"] = str(cred)
    try:
        assert EmailTools().gmail_token_file == str(token)          # same file, byte for byte
    finally:
        del os.environ["GMAIL_CREDENTIALS_FILE"]


def test_explicit_token_and_env_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("GMAIL_CREDENTIALS_FILE", str(tmp_path / "a.json"))
    monkeypatch.setenv("GMAIL_TOKEN_FILE", str(tmp_path / "t.json"))
    assert gen.resolve_paths() == (tmp_path / "a.json", tmp_path / "t.json")


def test_client_file_checks(tmp_path):
    good = tmp_path / "g.json"
    good.write_text(json.dumps(DESKTOP))
    assert gen.check_client_secret(good) == ""
    assert "can't find" in gen.check_client_secret(tmp_path / "missing.json")
    web = tmp_path / "w.json"
    web.write_text(json.dumps({"web": {}}))
    assert "Web application" in gen.check_client_secret(web)
    svc = tmp_path / "s.json"
    svc.write_text(json.dumps({"type": "service_account"}))
    assert "service_account" in gen.check_client_secret(svc)
    bad = tmp_path / "b.json"
    bad.write_text("not json")
    assert "not valid JSON" in gen.check_client_secret(bad)


def _fake_flow(monkeypatch, refresh_token="1//refresh"):
    from google.oauth2.credentials import Credentials
    creds = Credentials(token="ya29.access", refresh_token=refresh_token, token_uri="https://oauth2.googleapis.com/token",
                        client_id="id", client_secret="s", scopes=gen.SCOPES)
    seen = {}

    class Flow:
        @classmethod
        def from_client_secrets_file(cls, path, scopes):
            seen["path"], seen["scopes"] = path, scopes
            return cls()

        def run_local_server(self, **kwargs):
            seen["kwargs"] = kwargs
            return creds
    import google_auth_oauthlib.flow as flow_mod
    monkeypatch.setattr(flow_mod, "InstalledAppFlow", Flow)
    return seen


def test_generator_writes_a_token_tom_can_load(tmp_path, monkeypatch, capsys):
    cred = tmp_path / "google-credentials.json"
    cred.write_text(json.dumps(DESKTOP))
    seen = _fake_flow(monkeypatch)
    code = gen.main(["--credentials", str(cred), "--skip-verify"])
    assert code == 0
    token = tmp_path / "google-credentials_token.json"
    assert token.is_file()
    from google.oauth2.credentials import Credentials
    loaded = Credentials.from_authorized_user_file(str(token), gen.SCOPES)
    assert loaded.refresh_token == "1//refresh" and loaded.client_id == "id"
    assert seen["scopes"] == ["https://mail.google.com/"]
    assert seen["kwargs"]["access_type"] == "offline" and seen["kwargs"]["prompt"] == "consent"
    if os.name != "nt":
        assert stat.S_IMODE(token.stat().st_mode) == 0o600
    assert "Saved" in capsys.readouterr().out


def test_missing_refresh_token_is_reported_not_saved(tmp_path, monkeypatch, capsys):
    cred = tmp_path / "google-credentials.json"
    cred.write_text(json.dumps(DESKTOP))
    _fake_flow(monkeypatch, refresh_token=None)
    assert gen.main(["--credentials", str(cred), "--skip-verify"]) == 3
    assert not (tmp_path / "google-credentials_token.json").exists()


def test_bad_client_file_stops_before_opening_a_browser(tmp_path, monkeypatch, capsys):
    seen = _fake_flow(monkeypatch)
    assert gen.main(["--credentials", str(tmp_path / "nope.json")]) == 2
    assert "kwargs" not in seen and "can't find" in capsys.readouterr().out


def test_existing_token_is_not_replaced_without_consent(tmp_path, monkeypatch):
    cred = tmp_path / "google-credentials.json"
    cred.write_text(json.dumps(DESKTOP))
    token = tmp_path / "google-credentials_token.json"
    token.write_text("OLD")
    seen = _fake_flow(monkeypatch)
    monkeypatch.setattr("builtins.input", lambda _="": "n")
    assert gen.main(["--credentials", str(cred), "--skip-verify"]) == 0
    assert token.read_text() == "OLD" and "kwargs" not in seen


def test_verify_reports_missing_email_address(tmp_path, monkeypatch):
    token = tmp_path / "t.json"
    token.write_text(json.dumps({"token": "x", "refresh_token": "r", "client_id": "i", "client_secret": "s",
                                 "token_uri": "https://oauth2.googleapis.com/token", "scopes": gen.SCOPES}))
    from google.oauth2.credentials import Credentials
    monkeypatch.setattr(Credentials, "valid", property(lambda self: True))
    assert "EMAIL_ADDRESS" in gen.verify_token(token, "")


# ── sign-in that survives "localhost refused to connect" (real oauthlib flow, fake Google token endpoint) ──
import re
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse


@pytest.fixture
def google(tmp_path, monkeypatch):
    """A real InstalledAppFlow whose token endpoint is a local fake."""
    class Token(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            body = parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode())
            self.server.calls.append(body)
            ok = body.get("code") == ["good-code"] and body.get("code_verifier")     # PKCE verifier must be sent
            raw = json.dumps({"access_token": "ya29.x", "refresh_token": "1//r", "expires_in": 3600,
                              "token_type": "Bearer", "scope": "https://mail.google.com/"} if ok
                             else {"error": "invalid_grant"}).encode()
            self.send_response(200 if ok else 400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = HTTPServer(("127.0.0.1", 0), Token)
    server.calls = []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("OAUTHLIB_INSECURE_TRANSPORT", "1")
    client = json.loads(json.dumps(DESKTOP))
    client["installed"]["token_uri"] = f"http://127.0.0.1:{server.server_address[1]}/token"
    path = tmp_path / "client.json"
    path.write_text(json.dumps(client))
    from google_auth_oauthlib.flow import InstalledAppFlow
    yield InstalledAppFlow.from_client_secrets_file(str(path), scopes=gen.SCOPES), server
    server.shutdown()
    server.server_close()


def _state_of(url):
    return parse_qs(urlparse(url).query)["state"][0]


def test_listener_uses_the_loopback_ip_and_completes_the_sign_in(google, monkeypatch):
    flow, server = google
    seen = {}

    class FakeBrowser:                      # plays the part of "you clicked Allow": Google redirects to the listener
        def open(self, url, new=0, autoraise=True):
            seen["auth_url"] = url
            redirect = parse_qs(urlparse(url).query)["redirect_uri"][0]
            hit = f"{redirect}?state={_state_of(url)}&code=good-code"
            threading.Thread(target=lambda: urllib.request.urlopen(hit, timeout=10).read(), daemon=True).start()
            return True
    import webbrowser
    monkeypatch.setattr(webbrowser, "get", lambda browser=None: FakeBrowser())
    creds = gen.sign_in(flow, timeout=20)
    assert creds.refresh_token == "1//r"
    redirect = parse_qs(urlparse(seen["auth_url"]).query)["redirect_uri"][0]
    assert redirect.startswith("http://127.0.0.1:") and "localhost" not in redirect
    assert server.calls[-1]["code_verifier"]                                    # PKCE intact


def _listener_that_cannot_be_reached(flow, captured):
    """What happened on your PC: the URL is shown, you sign in, but the redirect never reaches the listener."""
    def run(**kwargs):
        flow.redirect_uri = "http://127.0.0.1:50548/"
        captured["url"], _ = flow.authorization_url(**{k: v for k, v in kwargs.items()
                                                       if k in ("access_type", "prompt")})
        raise KeyboardInterrupt
    flow.run_local_server = run


def test_ctrl_c_then_pasting_the_failed_page_url_finishes_the_sign_in(google, capsys):
    flow, server = google
    captured = {}
    _listener_that_cannot_be_reached(flow, captured)
    pasted = f"http://127.0.0.1:50548/?state={_state_of(captured.get('url', '')) if captured else ''}"

    def ask(_prompt):                       # runs after the KeyboardInterrupt, when captured["url"] exists
        return f"http://127.0.0.1:50548/?state={_state_of(captured['url'])}&code=good-code&scope=https://mail.google.com/"
    creds = gen.sign_in(flow, input_fn=ask)
    assert creds.refresh_token == "1//r"
    out = capsys.readouterr().out
    assert "Stopped waiting" in out and "Paste the URL" not in out.split("Copy the WHOLE")[0]
    assert server.calls[-1]["code"] == ["good-code"] and server.calls[-1]["code_verifier"]


def test_pasting_only_the_code_also_works(google):
    flow, _ = google
    captured = {}
    _listener_that_cannot_be_reached(flow, captured)
    creds = gen.sign_in(flow, input_fn=lambda _p: "good-code")
    assert creds.refresh_token == "1//r"


def test_manual_mode_prints_a_loopback_url_and_accepts_the_final_address(google, capsys):
    flow, _ = google

    def ask(_prompt):
        url = re.search(r"https://accounts\.google\.com\S+", capsys.readouterr().out).group(0)
        assert "redirect_uri=http%3A%2F%2F127.0.0.1%3A" in url and "access_type=offline" in url
        return f"http://127.0.0.1:8080/?state={_state_of(url)}&code=good-code"
    assert gen.sign_in(flow, manual=True, input_fn=ask).refresh_token == "1//r"


def test_a_pasted_url_from_another_sign_in_is_rejected(google, tmp_path, monkeypatch, capsys):
    flow, _ = google
    captured = {}
    _listener_that_cannot_be_reached(flow, captured)
    with pytest.raises(Exception):
        gen.sign_in(flow, input_fn=lambda _p: "http://127.0.0.1:50548/?state=SOMEONE-ELSES&code=good-code")


def test_main_falls_back_and_writes_the_token(google, tmp_path, monkeypatch):
    flow, _ = google
    cred = tmp_path / "google-credentials.json"
    cred.write_text(json.dumps(DESKTOP))
    captured = {}
    import google_auth_oauthlib.flow as flow_mod
    monkeypatch.setattr(flow_mod.InstalledAppFlow, "from_client_secrets_file", classmethod(lambda cls, *a, **k: flow))
    _listener_that_cannot_be_reached(flow, captured)
    monkeypatch.setattr("builtins.input", lambda _="": f"http://127.0.0.1:50548/?state={_state_of(captured['url'])}&code=good-code")
    assert gen.main(["--credentials", str(cred), "--skip-verify", "--force"]) == 0
    assert json.loads((tmp_path / "google-credentials_token.json").read_text())["refresh_token"] == "1//r"


def test_cancelling_leaves_no_token(google, tmp_path, monkeypatch):
    flow, _ = google
    cred = tmp_path / "google-credentials.json"
    cred.write_text(json.dumps(DESKTOP))
    import google_auth_oauthlib.flow as flow_mod
    monkeypatch.setattr(flow_mod.InstalledAppFlow, "from_client_secrets_file", classmethod(lambda cls, *a, **k: flow))
    _listener_that_cannot_be_reached(flow, {})

    def eof(_=""):
        raise EOFError
    monkeypatch.setattr("builtins.input", eof)
    assert gen.main(["--credentials", str(cred), "--skip-verify", "--force"]) == 1
    assert not (tmp_path / "google-credentials_token.json").exists()
