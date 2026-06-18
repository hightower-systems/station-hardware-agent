@echo off
REM Station Hardware Agent -- one-time installer for Windows autostart.
REM
REM Wires the agent into Windows Task Scheduler so it launches on every
REM logon. Run once per station (right-click -> Run as administrator).

setlocal
cd /d "%~dp0\.."

echo === Station Hardware Agent Installer ===
echo.

echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  Python is not on PATH.
    echo  Install Python 3.11+ from https://www.python.org/downloads/
    echo  and tick "Add Python to PATH" during setup, then re-run this.
    pause
    exit /b 1
)
python --version

echo.
echo [2/4] Creating virtual environment and installing the agent...
if not exist .venv\Scripts\python.exe (
    python -m venv .venv
    if errorlevel 1 ( echo  Failed to create the virtual environment. & pause & exit /b 1 )
)
.venv\Scripts\pip install --disable-pip-version-check --quiet .
if errorlevel 1 ( echo  Install failed. Check the error above. & pause & exit /b 1 )
echo  Installed.

if not exist .env (
    if exist .env.example (
        copy /y .env.example .env >nul
        echo  Copied .env.example -^> .env. Edit .env and set ALLOWED_ORIGIN.
    )
)

echo.
echo [3/4] Registering Windows Task Scheduler entry...
set "TASK_NAME=Station Hardware Agent"
set "AGENT_CMD=\"%CD%\.venv\Scripts\pythonw.exe\" -m hwbridge"

schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if not errorlevel 1 ( schtasks /Delete /TN "%TASK_NAME%" /F >nul )

schtasks /Create /TN "%TASK_NAME%" /TR %AGENT_CMD% /SC ONLOGON /RL HIGHEST /F >nul
if errorlevel 1 (
    echo  Failed to register the Task Scheduler task.
    echo  Try again as an administrator: right-click "Run as administrator".
    pause
    exit /b 1
)
echo  Task registered: "%TASK_NAME%"

echo.
echo [4/4] Done.
echo  1. Edit .env and set ALLOWED_ORIGIN to your web app's origin.
echo  2. Start now without signing out:  schtasks /Run /TN "%TASK_NAME%"
echo  3. Verify: a green tray icon, or open http://127.0.0.1:8765/status
echo     from the web app's browser tab.
echo  NOTE: Chrome/Edge also need Local Network Access allowed for your
echo        site -- see docs\browser-setup.md.
pause
