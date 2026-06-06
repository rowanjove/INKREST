@echo off
title Novel Agent - Dev Mode
echo ==================================================
echo   Novel Agent - Starting Electron Dev Environment
echo ==================================================
echo.
echo Entering frontend directory and starting dev server...
echo.

cd /d "%~dp0web\frontend"
npm run dev

pause
