@echo off
setlocal
cd /d "%~dp0"

set "TOM_VENV=.venv311"
set "PY311="
set "PY311_ARGS="
py -3.11 -c "import sys" >nul 2>&1
if not errorlevel 1 (
  set "PY311=py"
  set "PY311_ARGS=-3.11"
)

if not defined PY311 (
  if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    "%LocalAppData%\Programs\Python\Python311\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
    if not errorlevel 1 set "PY311=%LocalAppData%\Programs\Python\Python311\python.exe"
  )
)

if not defined PY311 (
  python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
  if not errorlevel 1 set "PY311=python"
)

if not defined PY311 (
  echo Python 3.11.x is required and was not found.
  echo Install Python 3.11 from python.org with "Add python.exe to PATH" enabled.
  echo Then run this file again.
  pause
  exit /b 1
)

echo Using Python 3.11 runtime: %PY311% %PY311_ARGS%
if exist "%TOM_VENV%\Scripts\python.exe" (
  "%TOM_VENV%\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
  if errorlevel 1 (
    echo Existing %TOM_VENV% is not Python 3.11. Rename or delete %TOM_VENV%, then rerun this file.
    pause
    exit /b 1
  )
) else (
  "%PY311%" %PY311_ARGS% -m venv "%TOM_VENV%"
  if errorlevel 1 (
    echo Failed to create %TOM_VENV%.
    pause
    exit /b 1
  )
)

"%TOM_VENV%\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 exit /b 1

"%TOM_VENV%\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

"%TOM_VENV%\Scripts\python.exe" -m pip install pyinstaller
if errorlevel 1 exit /b 1

"%TOM_VENV%\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 exit /b 1

echo Python 3.11 environment is ready.
echo Run launch_tom_ui.bat.
pause
endlocal
