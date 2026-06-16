@echo off
title NEXUS AI — Surveillance System
setlocal enabledelayedexpansion

REM ── 1. Always switch to the folder containing this .bat ──────────────────────
cd /d "%~dp0"

REM ── 2. Verify the virtual environment exists ─────────────────────────────────
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found.
    echo Expected: %CD%\.venv\Scripts\python.exe
    echo.
    echo Please run in this folder:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

REM ── 3. Environment variables ─────────────────────────────────────────────────
set "KMP_DUPLICATE_LIB_OK=TRUE"
set "OPENCV_VIDEOIO_DEBUG=0"
set "OPENCV_VIDEOIO_PRIORITY_MSMF=0"
set "PYTHONPATH=%CD%"
set "PYTHONUNBUFFERED=1"

REM ── 4. Launch ─────────────────────────────────────────────────────────────────
echo [NEXUS AI] Starting from: %CD%
".venv\Scripts\python.exe" app.py %* 2>> run.log

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [NEXUS AI] Application exited with error code %ERRORLEVEL%
    echo Last 20 lines of run.log:
    echo ---------------------------------------------------
    powershell -Command "Get-Content run.log -Tail 20"
    echo ---------------------------------------------------
    pause
)
