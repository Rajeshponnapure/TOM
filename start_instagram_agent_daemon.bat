@echo off
setlocal

cd /d "%~dp0"

set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

"%PYTHON_EXE%" -c "from tools.instagram_agent_controller import InstagramAgentController; r=InstagramAgentController().start(); print(r.get('message','Instagram agent start command sent.'))"

endlocal