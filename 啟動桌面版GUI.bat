@echo off
chcp 65001 >nul
title 台灣彩券 - 威力彩桌面視窗系統
cd /d "%~dp0"
echo ============================================================
echo  正在啟動 台灣彩券 · 威力彩桌面圖形介面 (Desktop GUI)...
echo ============================================================
python lotto_gui.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 啟動失敗，請確認已安裝 Python！
    pause
)
