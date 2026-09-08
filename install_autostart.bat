@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===================================================
echo [Auto Make Money] Cài đặt khởi động cùng Windows (Startup)...
echo ===================================================
copy /y "%~dp0launch_background.vbs" "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\AutoMakeMoneyDaemon.vbs"
echo [Auto Make Money] Đã cài đặt thành công! Worker sẽ tự động chạy ngầm mỗi khi mở máy.
echo.
pause
