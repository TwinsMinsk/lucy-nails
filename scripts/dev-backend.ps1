# Запуск только Backend (FastAPI)
# Запуск: .\scripts\dev-backend.ps1

Write-Host "=== Запуск Backend (FastAPI) ===" -ForegroundColor Cyan

if (-not (Test-Path "backend")) {
    Write-Host "[ERROR] Папка 'backend' не найдена!" -ForegroundColor Red
    exit 1
}

Set-Location backend

Write-Host "Активация виртуального окружения..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

Write-Host ""
Write-Host "[OK] Backend запущен на http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "[OK] Swagger UI: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host ""

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
