@echo off
title Auto Make Money - Status
chcp 65001 >nul
cd /d "%~dp0"

python core\status_reporter.py

echo.
pause
