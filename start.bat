@echo off
title LARA - WhatsApp Voice Agent
color 0A

echo.
echo  ============================================
echo   LARA - WhatsApp Voice Laptop Agent
echo  ============================================
echo.

:: Set project root to the folder where this bat file lives
set ROOT=%~dp0
set BACKEND=%ROOT%backend
set AGENT=%ROOT%agent

echo [*] Starting all services...
echo.

:: ── 1. Start ngrok ──────────────────────────────────────────────
echo [1/3] Starting ngrok tunnel...
start "LARA - ngrok" cmd /k "title LARA - ngrok && ngrok http 8000"
timeout /t 3 /nobreak >nul

:: ── 2. Start FastAPI backend ─────────────────────────────────────
echo [2/3] Starting FastAPI backend...
start "LARA - Backend" cmd /k "title LARA - Backend && cd /d %BACKEND% && venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000"
timeout /t 4 /nobreak >nul

:: ── 3. Start laptop agent ────────────────────────────────────────
echo [3/3] Starting laptop agent...
start "LARA - Agent" cmd /k "title LARA - Agent && cd /d %AGENT% && venv\Scripts\python.exe main.py"

echo.
echo  ============================================
echo   All services started in separate windows!
echo  ============================================
echo.
echo   Ngrok URL : https://rinsing-keenness-scorch.ngrok-free.dev
echo   Backend   : http://localhost:8000
echo   Webhook   : /webhook/whatsapp
echo.
echo   Close this window or press any key to exit.
echo  ============================================
pause >nul
