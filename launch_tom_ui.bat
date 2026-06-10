@echo off
cd /d "%~dp0"

if exist "venv\Scripts\python.exe" (
  "venv\Scripts\python.exe" tom_desktop_app.py
) else (
  python tom_desktop_app.py
)
