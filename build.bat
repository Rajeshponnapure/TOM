@echo off
REM ════════════════════════════════════════════════════════════════════
REM  TOM — canonical production build (run from the project root)
REM  Output: dist\tom_desktop_app.exe  +  dist\SHA256SUMS.txt
REM ════════════════════════════════════════════════════════════════════
setlocal
cd /d "%~dp0"

echo [1/5] Activating venv...
call venv\Scripts\activate.bat || (echo venv missing — run SETUP_TOM.bat first & exit /b 1)

echo [2/5] Cleaning previous build output...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo [3/5] Building with PyInstaller (this takes several minutes)...
pyinstaller tom_desktop_app.spec --noconfirm || (echo BUILD FAILED & exit /b 1)

echo [4/5] Generating SHA256 checksum (publish this next to the download)...
certutil -hashfile dist\tom_desktop_app.exe SHA256 > dist\SHA256SUMS.txt
type dist\SHA256SUMS.txt

echo [5/5] Done. Canonical artifact: dist\tom_desktop_app.exe
echo NOTE: binary is UNSIGNED — SmartScreen will warn. See SECURITY_ACTIONS_REQUIRED.md item 4.
endlocal
