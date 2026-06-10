# TOM Desktop UI

This adds a desktop-style white theme UI for TOM.

## What It Does
- Launches a GUI chat app (`tom_desktop_app.py`)
- Auto-checks Ollama on startup and attempts `ollama serve` if needed
- Uses existing `TomAgent` logic for responses
- Provides feedback controls:
  - `Reward +1`
  - `Penalty -1 + Revise`

## Run
```powershell
.\launch_tom_ui.bat
```

Or directly:
```powershell
venv\Scripts\python.exe .\tom_desktop_app.py
```

## Notes
- This is a local desktop UI using Tkinter.
- If Ollama is not installed/in PATH, start it manually before launching the app.
- The feedback actions use your current reward/penalty memory system.
