@echo off
REM Station Hardware Agent -- manual launcher (no autostart).
REM Double-click to run; closing this window stops the agent.

setlocal
cd /d "%~dp0\.."

if not exist .venv\Scripts\python.exe (
    echo [setup] Creating venv and installing the agent. One-time, ~30s...
    python -m venv .venv
    if errorlevel 1 (
        echo [setup] Python is not on PATH. Install Python 3.11+ from python.org
        echo [setup] with "Add to PATH" ticked, then run this again.
        pause
        exit /b 1
    )
    .venv\Scripts\pip install --disable-pip-version-check .
    if errorlevel 1 ( echo [setup] install failed. See messages above. & pause & exit /b 1 )
)

if not exist .env (
    if exist .env.example (
        echo [setup] Copying .env.example to .env. Edit it and set ALLOWED_ORIGIN.
        copy /y .env.example .env >nul
    )
)

echo [run] Starting Station Hardware Agent on http://127.0.0.1:8765
.venv\Scripts\python -m hwbridge
echo [run] Agent stopped.
pause
