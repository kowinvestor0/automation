@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===================================================
echo [Auto Make Money] Đang khởi chạy Worker chạy ngầm 24/7...
echo ===================================================
powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command "Start-Process python.exe -ArgumentList 'core\background_worker.py' -WorkingDirectory 'D:\auto make money'"
timeout /t 2 >nul
echo [Auto Make Money] Worker đã chạy ngầm trong Windows!
echo Bạn có thể tắt cửa sổ này hoặc khởi động lại máy tính, Worker vẫn chạy 24/7.
echo.
pause
