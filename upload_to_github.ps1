Set-Location -Path $PSScriptRoot

Write-Host "Syncing with GitHub..."
git add -A
git commit -m "feat: enhance multi-game backtest, ROI metrics, lotto_gui backtest dialog, and modern 2-tier web navigation"
git push origin main
Write-Host "Done."
