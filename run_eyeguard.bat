@echo off
REM EyeGuard Launcher for Windows
REM This script starts the Django server and opens the browser

ECHO.
ECHO ============================================================
ECHO         EyeGuard Camera Management System
ECHO ============================================================
ECHO.

REM Get the directory where this batch file is located
SET SCRIPT_DIR=%~dp0

REM Change to project directory
cd /d "%SCRIPT_DIR%"

REM Check if Python is installed
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    ECHO.
    ECHO [ERROR] Python is not installed or not in PATH
    ECHO Please install Python 3.8+ from https://www.python.org/
    ECHO Make sure to check "Add Python to PATH" during installation
    ECHO.
    PAUSE
    EXIT /B 1
)

REM Run the launcher
ECHO [*] Starting EyeGuard launcher...
python launcher.py

PAUSE
