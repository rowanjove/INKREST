@echo off
chcp 65001 >nul
title Novel Agent
echo ========================================
echo   Novel Agent - Multi-Agent Novel Generator
echo ========================================
echo.
echo Starting server...
echo Open http://127.0.0.1:8000 in your browser
echo Press Ctrl+C to stop
echo.

REM Try exe first, fallback to python
if exist "dist\NovelAgent.exe" (
    dist\NovelAgent.exe --no-browser
) else (
    python main.py --no-browser
)

pause
