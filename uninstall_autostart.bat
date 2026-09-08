@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===================================================
echo [Auto Make Money] Hủy khởi động cùng Windows...
echo ===================================================
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\AutoMakeMoneyDaemon.vbs" (
    del /f /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\AutoMakeMoneyDaemon.vbs"
    echo [Auto Make Money] Đã gỡ bỏ khỏi thư mục Startup.
) else (
    echo [Auto Make Money] Chưa được cài đặt trong thư mục Startup.
)
echo.
pause
