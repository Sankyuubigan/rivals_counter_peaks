@echo off
setlocal
cd /d "%~dp0.."
echo ===================================================
echo  Marvel Rivals Counter Picks - DEBUG MODE
echo  Starting local server (no game / no Overwolf)...
echo ===================================================
echo.
echo  Server runs hidden at http://localhost:8000
echo  Opening Desktop window (app mode, no browser UI)...
echo  To stop: close the Desktop window, then end python in Task Manager.
echo.

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1
timeout /t 1 >nul

start "" wscript.exe "%~dp0serve.vbs"

timeout /t 2 >nul
exit
