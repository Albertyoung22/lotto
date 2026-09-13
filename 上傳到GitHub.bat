@echo off
chcp 65001 >nul
title 上傳至 GitHub - https://github.com/Albertyoung22/lotto
cd /d "%~dp0"

echo ======================================================================
echo   台灣彩券 · 威力彩 Web / AI 系統 - 一鍵上傳至 GitHub
echo   目標儲存庫: https://github.com/Albertyoung22/lotto
echo ======================================================================
echo.

where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [錯誤] 系統未偵測到 Git 指令，請先安裝 Git for Windows: https://git-scm.com/
    pause
    exit /b 1
)

echo [1/5] 初始化 Git 儲存庫...
if not exist ".git" (
    git init
)

echo [2/5] 設定遠端儲存庫 origin...
git remote get-url origin >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    git remote set-url origin https://github.com/Albertyoung22/lotto.git
) else (
    git remote add origin https://github.com/Albertyoung22/lotto.git
)

echo [3/5] 切換至主分支 (main)...
git branch -M main

echo [4/5] 將專案檔案加入 Git 暫存區並提交...
git add -A
git commit -m "feat: Taiwan Lottery Flask Web App with Google OR-Tools AI on Render" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [提示] 檔案已是最新狀態，無需重複提交。
)

echo.
echo [5/5] 正在推送 (git push) 至 GitHub...
git push -u origin main
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ======================================================================
    echo  [成功] 程式碼已成功上傳至 https://github.com/Albertyoung22/lotto ！
    echo  現在您可以前往 Render.com 建立 Web Service 並完成部署！
    echo ======================================================================
) else (
    echo.
    echo ----------------------------------------------------------------------
    echo [提示] 若推送失敗可能是因為遠端 GitHub 儲存庫已經有檔案 (例如建立時勾選了 README)。
    echo 正在嘗試合併遠端檔案 (git pull --rebase)...
    echo ----------------------------------------------------------------------
    git pull origin main --rebase
    echo 再次嘗試推送...
    git push -u origin main
    if %ERRORLEVEL% EQU 0 (
        echo.
        echo ======================================================================
        echo  [成功] 合併後已成功上傳至 https://github.com/Albertyoung22/lotto ！
        echo ======================================================================
    ) else (
        echo.
        echo 若您想強制覆蓋遠端空儲存庫，可手動執行: git push -u origin main --force
    )
)

echo.
pause
