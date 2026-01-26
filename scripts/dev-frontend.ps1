# Запуск только Frontend (Next.js)
# Запуск: .\scripts\dev-frontend.ps1

Write-Host "=== Запуск Frontend (Next.js) ===" -ForegroundColor Cyan

if (-not (Test-Path "frontend")) {
    Write-Host "[ERROR] Папка 'frontend' не найдена!" -ForegroundColor Red
    exit 1
}

Set-Location frontend

Write-Host ""
Write-Host "[OK] Frontend будет доступен на http://localhost:3000" -ForegroundColor Green
Write-Host ""

npm run dev
