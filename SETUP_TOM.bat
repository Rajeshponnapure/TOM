@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo   TOM setup and native desktop rebuild
echo ============================================================
echo.

call setup_python311_env.bat
if errorlevel 1 exit /b 1

set "PY=.venv311\Scripts\python.exe"
"%PY%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
if errorlevel 1 (
  echo .venv311 is not Python 3.11. Setup cannot continue.
  pause
  exit /b 1
)

echo Cleaning old build output...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Building dist\tom_desktop_app.exe...
"%PY%" -m PyInstaller tom_desktop_app.spec --clean --noconfirm
if errorlevel 1 (
  echo BUILD FAILED.
  pause
  exit /b 1
)

if not exist "dist\tom_desktop_app.exe" (
  echo Build finished but dist\tom_desktop_app.exe was not created.
  pause
  exit /b 1
)

echo Creating Desktop shortcut "TOM"...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=[Environment]::GetFolderPath('Desktop'); $w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut((Join-Path $d 'TOM.lnk')); $s.TargetPath='%CD%\dist\tom_desktop_app.exe'; $s.WorkingDirectory='%CD%'; if (Test-Path '%CD%\resources\tom_icon.ico') { $s.IconLocation='%CD%\resources\tom_icon.ico' }; $s.Description='TOM - Professional AI Assistant'; $s.Save()"

echo TOM setup complete.
echo Use launch_tom_ui.bat for source launch or Desktop TOM shortcut for exe launch.
pause
endlocal
