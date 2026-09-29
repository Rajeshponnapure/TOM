@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo   Creating the "TOM" shortcut on your Desktop
echo ============================================================
echo.

rem ── What the shortcut opens ──────────────────────────────────────
rem Prefer the built dist\tom_desktop_app.exe when it exists (fastest, no
rem console). Otherwise run launch_tom_ui.vbs through wscript, which starts the
rem source app via .venv311\Scripts\pythonw.exe so no console window appears.
set "TOM_LNK_TARGET=%SystemRoot%\System32\wscript.exe"
rem Unquoted form on purpose: the value itself must carry the quotes so the
rem shortcut runs the script path even though it contains spaces.
set TOM_LNK_ARGS="%~dp0launch_tom_ui.vbs"
set "KIND=source app (.venv311)"
if exist "%~dp0dist\tom_desktop_app.exe" (
  set "TOM_LNK_TARGET=%~dp0dist\tom_desktop_app.exe"
  set "TOM_LNK_ARGS="
  set "KIND=built executable (dist\tom_desktop_app.exe)"
)
set "TOM_LNK_WORKDIR=%~dp0"
set "TOM_LNK_ICON=%~dp0resources\tom_icon.ico"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$d = [Environment]::GetFolderPath('Desktop'); $lnk = Join-Path $d 'TOM.lnk'; $shell = New-Object -ComObject WScript.Shell; $s = $shell.CreateShortcut($lnk); $s.TargetPath = $env:TOM_LNK_TARGET; $s.Arguments = $env:TOM_LNK_ARGS; $s.WorkingDirectory = $env:TOM_LNK_WORKDIR; if (Test-Path $env:TOM_LNK_ICON) { $s.IconLocation = $env:TOM_LNK_ICON }; $s.Description = 'TOM - Professional AI Assistant'; $s.Save(); if (Test-Path $lnk) { Write-Host ('Created: ' + $lnk) } else { Write-Host 'Shortcut was not created.'; exit 1 }"
if errorlevel 1 (
  echo.
  echo Failed to create the Desktop shortcut.
  pause
  exit /b 1
)

echo Shortcut opens the %KIND%.
echo Double-click "TOM" on your Desktop to start TOM.
echo.
pause
endlocal
