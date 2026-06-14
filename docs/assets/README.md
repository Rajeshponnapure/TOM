# README assets

This folder holds everything the project `README.md` embeds. Keeping assets here (not in
the repo root) keeps the top level clean and makes the README portable.

```
docs/assets/
├─ banner.svg          # animated hero banner (self-contained SMIL — works on GitHub, no external service)
├─ dashboard.png       # ⬜ TODO: screenshot of the Dashboard view
├─ chat.png            # ⬜ TODO: screenshot of the Chat view + an approval modal
├─ voice.png           # ⬜ TODO: screenshot of the Voice Mode window
├─ capabilities.png    # ⬜ TODO: screenshot of the Capabilities / Health view
└─ demo.gif            # ⬜ TODO: 10–20s screen capture of a real command end-to-end
```

## How to capture the screenshots / GIF

1. Launch TOM: `launch_tom_ui.bat`.
2. **dashboard.png** — open the Dashboard view (the animated orb + 25 quick actions).
   `Win+Shift+S` (Snip) or `Alt+PrtScn` for the active window.
3. **chat.png** — run a command that triggers an approval modal (e.g. `send email to ...`)
   and capture the chat surface with the modal visible.
4. **voice.png** — click **♫ Voice Mode** and capture the push-to-talk window.
5. **capabilities.png** — open the Capabilities view, then the Health view.
6. **demo.gif** — record a short clip with [ScreenToGif](https://www.screentogif.com/)
   (free, Windows). Keep it under ~5 MB; crop to the window; 12–15 fps is plenty.

### Recommended sizes

| Asset | Width | Notes |
|---|---|---|
| `banner.svg` | 1200×340 | already vector — no change needed |
| `*.png` | 1280–1600 wide | PNG, app window only, no desktop clutter |
| `demo.gif` | ≤ 1000 wide | < 5 MB so GitHub renders it inline |

Until the real captures exist, the README links them with explanatory alt-text, so a
missing file shows the description instead of a broken layout. Drop the files in with the
exact names above and they appear automatically — no README edit needed.

## Branding source

The app logo/icon already lives in `resources/` (`tom_icon.png`, `tom_icon.svg`). Reuse it
for social previews or a favicon if you publish a docs site.
