@echo off
title Auto Make Money - Headless Scheduler
chcp 65001 >nul
cd /d "%~dp0"

echo ====================================================================
echo  🚀 AUTO MAKE MONEY - TIẾN TRÌNH TỰ ĐỘNG XẾP LỊCH PLANLY KỊP GIỜ
echo ====================================================================
echo.

python run_headless.py %*

echo.
echo Nhấn phím bất kỳ để thoát...
pause >nul
