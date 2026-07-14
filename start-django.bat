@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Python virtual environment was not found. Run activate-venv.ps1 setup first.
  pause
  exit /b 1
)

echo Starting Tuner Hub Django backend at http://127.0.0.1:8000/
echo LAN access, if allowed by Windows Firewall: http://192.168.0.106:8000/
".venv\Scripts\python.exe" "backend\manage.py" runserver 0.0.0.0:8000
