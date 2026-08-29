@echo off
REM Short-video factory - US market (9:16)
REM Usage:  run.bat        -> one video
REM         run.bat 5      -> five videos
cd /d "%~dp0"
set COUNT=%1
if "%COUNT%"=="" set COUNT=1
python main.py --count %COUNT%
pause
