@echo off
setlocal
cd /d "%~dp0"
echo === TOM Debug Launch ===
echo.

set "TOM_PY="
set "TOM_PY_ARGS="
if exist ".venv311\Scripts\python.exe" (
  ".venv311\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
  if not errorlevel 1 set "TOM_PY=.venv311\Scripts\python.exe"
)

if exist "venv\Scripts\python.exe" (
  "venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
  if not errorlevel 1 if not defined TOM_PY set "TOM_PY=venv\Scripts\python.exe"
)

if not defined TOM_PY (
  py -3.11 -c "import sys" >nul 2>&1
  if not errorlevel 1 (
    set "TOM_PY=py"
    set "TOM_PY_ARGS=-3.11"
  )
)

if not defined TOM_PY (
  if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    "%LocalAppData%\Programs\Python\Python311\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
    if not errorlevel 1 set "TOM_PY=%LocalAppData%\Programs\Python\Python311\python.exe"
  )
)

if not defined TOM_PY (
  python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
  if not errorlevel 1 set "TOM_PY=python"
)

if not defined TOM_PY (
  echo TOM requires Python 3.11.x.
  echo Current Python is not compatible or Python 3.11 is not installed.
  echo Install official Python 3.11, then run setup_python311_env.bat.
  pause
  exit /b 1
)

"%TOM_PY%" %TOM_PY_ARGS% -c "import langchain_core, langchain_ollama, dotenv" >nul 2>&1
if errorlevel 1 (
  echo Python 3.11 is available, but TOM dependencies are missing.
  echo Run setup_python311_env.bat, then launch TOM again.
  pause
  exit /b 1
)

echo Using %TOM_PY%...
"%TOM_PY%" %TOM_PY_ARGS% tom_desktop_app.py
echo.
echo === TOM exited. Press any key to close ===
pause >nul
endlocal
