@echo off
setlocal

cd /d "%~dp0"

set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

"%PYTHON_EXE%" -c "from tools.email_agent_controller import EmailAgentController; r=EmailAgentController().start(); print(r.get('message','Email agent start command sent.'))"

endlocal