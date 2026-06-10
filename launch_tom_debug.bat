@echo off
cd /d "%~dp0"
echo === TOM WebUI Debug Launch ===
echo.

if exist "venv\Scripts\python.exe" (
  echo Using venv Python...
  "venv\Scripts\python.exe" tom_desktop_app.py
) else (
  echo Using system Python...
  python tom_desktop_app.py
)

echo.
echo === TOM exited. Press any key to close ===
pause >nul
