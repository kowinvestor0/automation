@echo off
title Auto Make Money - Stop Background Worker
chcp 65001 >nul
cd /d "%~dp0"

echo ====================================================================
echo  🛑 DUNG TIEN TRINH CHAY NGAM AUTO MAKE MONEY
echo ====================================================================

echo 1 > data\worker.stop
ping 127.0.0.1 -n 2 >nul
taskkill /F /FI "WINDOWTITLE eq Auto Make Money*" 2>nul

if exist data\worker.lock (
    del /f /q data\worker.lock 2>nul
)

echo.
echo [OK] Da phat lenh dung tien trinh chay ngam!
echo.
pause
