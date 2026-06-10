# SECURITY — Actions YOU must do before deploying (15 minutes)

Code-side security is fixed (see git log). These items require **your accounts** — I cannot do them for you.

## 1. Rotate the email password (5 min) — REQUIRED
`.env` has stored `EMAIL_PASSWORD` in plaintext on this disk for weeks.
- If it's a Gmail **App Password**: Google Account → Security → 2-Step Verification → App passwords → delete the old one → create a new one → put the new value in `.env`.
- Never reuse the old value.

## 2. Revoke + reissue the Google OAuth token (5 min) — REQUIRED
`google-credentials_token.json` is a live token.
- Delete `google-credentials_token.json` from the project root.
- Go to https://myaccount.google.com/permissions → remove access for the TOM/Gmail OAuth app.
- Next launch of TOM will re-run the OAuth flow and mint a fresh token (file is now git-ignored).

## 3. Keep secrets out of the package (already enforced)
- `.gitignore` now blocks `.env`, `*credentials*.json`, `*token*.json`.
- `tools/prepare_migration_package.py` now excludes credential/token files.
- The Inno installer must NOT bundle `.env` — copy it manually to target machines.

## 4. Code signing (accept for v1)
A signing cert cannot be procured by tomorrow. Mitigation shipped instead:
- `build.bat` prints the SHA256 of the exe — publish it next to the download.
- Expect a SmartScreen warning on first run; users click "More info → Run anyway".
- Buy an OV/EV cert (Sectigo/DigiCert, ~3–7 days) and sign from v1.1.

## 5. Before first `git push` to any remote
Run: `git ls-files | findstr /i "env credential token"` — output must be empty.
