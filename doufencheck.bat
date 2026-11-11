@echo off
chcp 65001 >nul

set PROJECT_PATH=D:\wwwroot\Python\doufencheck
set LOG_PATH=D:\wwwroot\Python\doufencheck\checkin.log

cd /d "%PROJECT_PATH%"

echo [%date% %time%] start checkin >> "%LOG_PATH%"

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

uv run python main.py >> "%LOG_PATH%" 2>&1

echo [%date% %time%] finish checkin >> "%LOG_PATH%"