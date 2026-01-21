@echo off
setlocal

cd /d "%~dp0"

echo ==============================
echo WaifuGen Server Launcher
echo ==============================
echo Project Dir: %cd%
echo.

echo [Step 1] Check Python (py launcher)...
where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Cannot find "py" launcher in PATH.
  echo.
  pause
  exit /b 1
)

py -3.10 --version
if errorlevel 1 (
  echo ERROR: Python 3.10 is not available via "py -3.10".
  echo Run: py -0
  echo.
  pause
  exit /b 1
)

echo.
echo [Step 2] Show Python executable...
py -3.10 -c "import sys; print(sys.executable)"
echo.

REM === Your actual server port ===
set PORT=8069

echo [Step 3] Check port %PORT% ...
netstat -ano | findstr /R /C:":%PORT% .*LISTENING"
echo.

echo [Step 4] Start uvicorn (server:app) ...
echo (Close this window to stop)
echo.

REM Make console output encoding stable
set PYTHONIOENCODING=utf-8

py -3.10 -m uvicorn server:app --host 127.0.0.1 --port 8069 --reload --no-use-colors

echo.
echo Server process ended (exit code %ERRORLEVEL%).
pause