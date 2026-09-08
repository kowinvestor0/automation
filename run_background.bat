@echo off
title Auto Make Money - Background Worker
chcp 65001 >nul
cd /d "%~dp0"

echo ====================================================================
echo  🚀 KHOI DONG TIEN TRINH CHAY NGAM 24/7 (SILENT BACKGROUND RUNNER)
echo  📌 Tu dong tim Shorts tren mang, binh luan >60s, xep lich cho tat ca ngay toi
echo  📌 Chay ngam khong can mo may / khong can giu cua so console
echo ====================================================================

start "" pythonw core\background_worker.py

echo.
echo [OK] Tien trinh chay ngam da duoc kich hoat thanh cong!
echo Nhat ky hoat dong: logs\background_worker.log
echo De dung tien trinh, chay file: stop_background.bat
echo.
timeout /t 5 >nul
