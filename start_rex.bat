@echo off
TITLE R.E.X Launcher
echo [REX] Configuring environment...
set "PATH=C:\Program Files\nodejs;%PATH%"

:: 1. Cleanup ports
powershell -Command "Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).OwningProcess -Force -ErrorAction SilentlyContinue; Stop-Process -Id (Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue).OwningProcess -Force -ErrorAction SilentlyContinue"

:: 2. Start Backend
echo [REX] Launching Backend...
start "REX Backend" cmd /k "venv\Scripts\python backend/server.py"

:: 3. Start Frontend (Vite + Electron)
echo [REX] Launching Frontend...

:: Start Vite
start "REX Vite" cmd /k "npm run dev:vite"

:: Wait for Vite
timeout /t 5 /nobreak >nul

:: Start Electron using isolated binary
echo [REX] Launching Electron...
start "REX Electron" cmd /k "electron_dist_backup\electron.exe ."

echo [REX] Launched.
