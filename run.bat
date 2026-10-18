@echo off
setlocal EnableExtensions
title TRAKKLICENSE - Run
cd /d "%~dp0"

echo ================================================
echo   TRAKKLICENSE
echo   Launch (existing .venv)
echo ================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo Run start.bat first to create it.
    echo.
    pause
    exit /b 1
)

echo Launching the app...
rem FIX: pythonw.exe hides tracebacks (silent failures). Use python.exe + log.
if not exist "data" mkdir "data"
".venv\Scripts\python.exe" main.py 2>&1 | powershell -Command "$input | Tee-Object -FilePath 'data\launch.log'"
if errorlevel 1 (
    echo.
    echo [ERROR] The app exited with an error. See data\launch.log
    pause
)

endlocal
