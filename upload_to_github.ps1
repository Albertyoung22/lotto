# PowerShell Script to Upload to GitHub: https://github.com/Albertyoung22/lotto
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  台灣彩券 · 威力彩 Web / AI 系統 - 推送至 GitHub" -ForegroundColor Green
Write-Host "  目標儲存庫: https://github.com/Albertyoung22/lotto" -ForegroundColor Yellow
Write-Host "======================================================================" -ForegroundColor Cyan

Set-Location -Path $PSScriptRoot

if (-not (Test-Path ".git")) {
    Write-Host "[1/5] 初始化 Git 儲存庫 (git init)..." -ForegroundColor White
    git init
}

Write-Host "[2/5] 設定遠端儲存庫 origin..." -ForegroundColor White
$existingRemote = git remote
if ($existingRemote -contains "origin") {
    git remote set-url origin https://github.com/Albertyoung22/lotto.git
} else {
    git remote add origin https://github.com/Albertyoung22/lotto.git
}

Write-Host "[3/5] 切換至 main 分支..." -ForegroundColor White
git branch -M main

Write-Host "[4/5] 加入檔案並建立提交..." -ForegroundColor White
git add -A
git commit -m "feat: Taiwan Lottery Flask Web App with Google OR-Tools AI on Render"

Write-Host "[5/5] 推送至 GitHub (git push -u origin main)..." -ForegroundColor White
git push -u origin main

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[提示] 推送遇到衝突或遠端非空，嘗試 git pull --rebase..." -ForegroundColor Yellow
    git pull origin main --rebase
    git push -u origin main
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[成功] 程式碼已成功上傳至 https://github.com/Albertyoung22/lotto ！" -ForegroundColor Green
} else {
    Write-Host "`n[注意] 若遠端有衝突且您希望直接覆蓋，可執行: git push -u origin main --force" -ForegroundColor Red
}

Write-Host "`n完成。按任意鍵離開..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
