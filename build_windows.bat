@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
    echo Python tapilmadi. Python 3.11+ qurasdir ve "Add Python to PATH" sec.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install "pyinstaller>=6.0,<7.0"

pyinstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name WifiTexnik ^
  wifi_technician.py

if errorlevel 1 (
    echo Build ugursuz oldu.
    pause
    exit /b 1
)

echo.
echo Hazirdir: dist\WifiTexnik.exe
pause
