Set-Location -Path $PSScriptRoot

Write-Host "Syncing with GitHub..."
git add -A
git commit -m "update: refine UI labels and optimize AI terminology"
git push origin main
Write-Host "Done."
