@echo off
setlocal
cd /d "%~dp0"

echo [1/5] Selecting Python 3.11 runtime...
set "PY=.venv311\Scripts\python.exe"
if not exist "%PY%" (
  echo .venv311 is missing. Run setup_python311_env.bat first.
  exit /b 1
)

"%PY%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
if errorlevel 1 (
  echo .venv311 is not Python 3.11. Run setup_python311_env.bat with official Python 3.11 installed.
  exit /b 1
)

echo [2/5] Cleaning previous build output...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [3/5] Building with PyInstaller...
"%PY%" -m PyInstaller tom_desktop_app.spec --noconfirm
if errorlevel 1 (
  echo BUILD FAILED
  exit /b 1
)

echo [4/5] Generating SHA256 checksum...
certutil -hashfile dist\tom_desktop_app.exe SHA256 > dist\SHA256SUMS.txt
type dist\SHA256SUMS.txt

echo [5/5] Done. Canonical artifact: dist\tom_desktop_app.exe
echo NOTE: binary is unsigned; Windows SmartScreen may warn.
endlocal
