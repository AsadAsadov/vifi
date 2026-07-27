@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
    echo Python tapilmadi. Python 3.11+ qurasdir ve "Add Python to PATH" sec.
    pause
    exit /b 1
)

py -3 wifi_technician.py
if errorlevel 1 pause
