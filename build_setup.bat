@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo   AUTO MAKE MONEY PRO - BUILD EXE AND SETUP INSTALLER
echo ============================================================
echo.

echo [1/3] Building AutoMakeMoney.exe with PyInstaller...
pyinstaller AutoMakeMoney.spec --noconfirm
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller build failed!
    exit /b %errorlevel%
)
echo [OK] PyInstaller build completed!
echo.

echo [2/3] Locating Inno Setup Compiler (ISCC.exe)...
set "ISCC="
if exist "C:\Users\H\AppData\Local\Programs\Inno Setup 6\ISCC.exe" set "ISCC=C:\Users\H\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
if "%ISCC%"=="" if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if "%ISCC%"=="" if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if "%ISCC%"=="" (
    echo [WARNING] Inno Setup compiler not found.
    exit /b 0
)

echo [OK] Found Inno Setup at: "%ISCC%"
echo.

echo [3/3] Compiling Setup Installer with Inno Setup...
"%ISCC%" installer\AutoMakeMoney.iss
if %errorlevel% neq 0 (
    echo [ERROR] Inno Setup compilation failed!
    exit /b %errorlevel%
)

if exist "dist\setup\AutoMakeMoney_Setup_1.0.0.exe" (
    copy /y "dist\setup\AutoMakeMoney_Setup_1.0.0.exe" "AutoMakeMoney_Setup_1.0.0.exe" >nul
)

echo.
echo ============================================================
echo   BUILD SUCCESSFUL!
echo   1. Portable App: dist\AutoMakeMoney\AutoMakeMoney.exe
echo   2. Setup Wizard: AutoMakeMoney_Setup_1.0.0.exe
echo ============================================================
