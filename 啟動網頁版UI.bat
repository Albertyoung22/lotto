@echo off
chcp 65001 >nul
title 台灣彩券 - 威力彩 Web 視覺化系統 (Flask / Waitress)
cd /d "%~dp0"
echo ============================================================
echo  正在啟動 台灣彩券 · 威力彩 Web 儀表板 (Flask / Waitress)...
echo  瀏覽器存取網址: http://127.0.0.1:5000
echo ============================================================
python app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 啟動發生異常，若尚未安裝相依套件，請執行: pip install -r requirements.txt
    pause
)
