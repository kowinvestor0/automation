@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===================================================
echo [Auto Make Money] Đang dừng Worker chạy ngầm...
echo ===================================================
echo stop > "%~dp0data\worker.stop"
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*background_worker.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
if exist "%~dp0data\worker.lock" del /f /q "%~dp0data\worker.lock"
echo [Auto Make Money] Worker đã dừng hoàn toàn.
echo.
pause
