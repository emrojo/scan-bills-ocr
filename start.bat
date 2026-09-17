@echo off
title ScanBills OCR Service
echo ========================================================
echo         Starting ScanBills OCR Service (Local)
echo ========================================================
echo.

:: Check if Ollama is running
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Starting Ollama server in background...
    start /B "" "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
    timeout /t 3 /nobreak >nul
) else (
    echo [OK] Ollama server detected and online.
)

:: Check virtual environment
if not exist "venv\Scripts\activate.bat" (
    echo [*] Creating Python virtual environment...
    python -m venv venv
    echo [*] Installing requirements...
    call venv\Scripts\pip install -r requirements.txt
)

echo.
echo ========================================================
echo [OK] Launching FastAPI Web Server on PORT 8030
echo [OK] OPEN YOUR BROWSER AT: http://localhost:8030
echo ========================================================
echo.
call venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8030 --reload
pause
