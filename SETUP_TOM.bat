@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo   TOM  -  Rebuild the native desktop app (.exe)
echo          and fix the Desktop shortcut to point at it.
echo ============================================================
echo.

REM --- 1) Pick Python (prefer the project venv) ---
set "PY=python"
if exist "venv\Scripts\python.exe" set "PY=venv\Scripts\python.exe"
echo Using Python: %PY%
echo.

REM --- 2) Make sure PyInstaller is installed ---
"%PY%" -c "import PyInstaller" 1>nul 2>nul
if errorlevel 1 (
  echo Installing PyInstaller ...
  "%PY%" -m pip install pyinstaller
)

REM --- 2b) Best-effort: install the natural talk-back voice (edge-tts) + offline fallback ---
REM         (will not stop the build if it fails, e.g. no internet)
"%PY%" -c "import edge_tts" 1>nul 2>nul || "%PY%" -m pip install edge-tts pyttsx3 1>nul 2>nul

REM --- 3) Clean the old build AND the stale web-UI exe ---
echo Cleaning old build output ...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

REM --- 4) Rebuild the NATIVE app from the corrected spec ---
echo.
echo Building dist\tom_desktop_app.exe  (this can take several minutes) ...
echo.
"%PY%" -m PyInstaller tom_desktop_app.spec --clean --noconfirm
if errorlevel 1 (
  echo.
  echo *** BUILD FAILED - read the red/error messages above. ***
  pause
  exit /b 1
)
if not exist "dist\tom_desktop_app.exe" (
  echo.
  echo *** Build finished but dist\tom_desktop_app.exe was not created. ***
  pause
  exit /b 1
)

REM --- 5) Create / repair the Desktop shortcut so it opens the new exe ---
echo.
echo Creating Desktop shortcut "TOM" ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=[Environment]::GetFolderPath('Desktop'); $w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut((Join-Path $d 'TOM.lnk')); $s.TargetPath='%CD%\dist\tom_desktop_app.exe'; $s.WorkingDirectory='%CD%'; if (Test-Path '%CD%\resources\tom_icon.ico') { $s.IconLocation='%CD%\resources\tom_icon.ico' }; $s.Description='TOM - Professional AI Assistant'; $s.Save()"

echo.
echo ============================================================
echo   DONE.
echo   Double-click the "TOM" icon on your Desktop - it now
echo   opens dist\tom_desktop_app.exe (the native desktop app).
echo.
echo   If you still see an OLD icon with a different name, delete
echo   it and use the new "TOM" icon this script just created.
echo ============================================================
echo.
pause
endlocal
