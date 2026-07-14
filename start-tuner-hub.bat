@echo off
setlocal
cd /d "%~dp0"

set "BUNDLED_NODE=C:\Users\YWJ\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"

where node >nul 2>nul
if %errorlevel%==0 (
  start "Tuner Hub" cmd /k "node serve-static.js"
) else (
  if exist "%BUNDLED_NODE%" (
    start "Tuner Hub" cmd /k ""%BUNDLED_NODE%" serve-static.js"
  ) else (
    echo Node.js was not found. Please install Node.js or run from Codex.
    pause
    exit /b 1
  )
)

timeout /t 2 >nul
start http://127.0.0.1:5174/
