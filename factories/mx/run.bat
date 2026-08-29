@echo off
REM Fabrica de videos automaticos - Mexico (9:16)
REM Uso:  run.bat            -> 1 video
REM       run.bat 5          -> 5 videos
cd /d "%~dp0"

REM --- Pega aqui tus llaves si no las quieres poner en variables de entorno ---
REM set ANTHROPIC_API_KEY=sk-ant-...
REM set PEXELS_API_KEY=...

set COUNT=%1
if "%COUNT%"=="" set COUNT=1

python main.py --count %COUNT%
pause
