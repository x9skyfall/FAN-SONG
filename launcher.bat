@echo off
title FAN SONG // TERMINAL
color 0b

:: --- ВАЖНОЕ ИСПРАВЛЕНИЕ: ПЕРЕХОД В ПАПКУ СКРИПТА ---
cd /d "%~dp0"

echo.
echo ^>^> FAN SONG ^>^> -------------------------^>
echo.
echo   [ PROJECT: SKYFALL // AUDIO INTERCEPTOR ]
echo   [ STATUS: LISTENING...                  ]
echo.

echo [1/5] Checking Python Environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
echo.
echo [ERROR] Python not found. Please install Python and check "Add to PATH".
pause
exit
)

echo.
echo [2/5] Verifying Neural Network Connection (venv)...
if not exist "venv" (
echo Creating virtual environment...
python -m venv venv
)

echo.
echo [3/5] Syncing Systems...
call venv\Scripts\activate
if %errorlevel% neq 0 (
echo [ERROR] Venv activation failed.
pause
exit
)

echo.
echo [4/5] Updating Warfare Protocols (yt-dlp fix)...
:: Обновление загрузчика для обхода 403
pip install "yt-dlp>=2024.08.01" --upgrade >nul 2>&1

if not exist "venv\installed.flag" (
echo Installing dependencies...
pip install -r requirements.txt
echo done > venv\installed.flag
)

echo.
echo [5/5] FAN SONG System Launching...
echo [INFO] Do not close this terminal.
python transcriber.py

pause