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
