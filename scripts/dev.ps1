# Скрипт для запуска Dev окружения (Backend + Frontend)
# Запуск: .\scripts\dev.ps1 (из корня проекта)

Write-Host "=== Запуск Dev окружения ===" -ForegroundColor Cyan
Write-Host ""

# 1. Проверка существования папок
if (-not (Test-Path "backend")) {
    Write-Host "[ERROR] Папка 'backend' не найдена!" -ForegroundColor Red
    Write-Host "Убедись, что ты запускаешь скрипт из корня проекта." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path "frontend")) {
    Write-Host "[ERROR] Папка 'frontend' не найдена!" -ForegroundColor Red
    Write-Host "Убедись, что ты запускаешь скрипт из корня проекта." -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Папки backend и frontend найдены" -ForegroundColor Green
Write-Host ""

# 2. Запуск Backend в новом окне терминала
Write-Host "Запускаю Backend (FastAPI) в новом окне..." -ForegroundColor Cyan

$backendPath = Join-Path $PSScriptRoot "..\backend"
$backendCommand = "cd '$backendPath'; .\venv\Scripts\Activate.ps1; Write-Host 'Backend запущен на http://127.0.0.1:8000' -ForegroundColor Green; uvicorn app.main:app --reload"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCommand

Write-Host "[OK] Backend запускается в отдельном окне" -ForegroundColor Green
Start-Sleep -Seconds 2
Write-Host ""

# 3. Запуск Frontend в текущем окне
Write-Host "Запускаю Frontend (Next.js) в текущем окне..." -ForegroundColor Cyan
Write-Host "[OK] Frontend будет доступен на http://localhost:3000" -ForegroundColor Green
Write-Host ""
Write-Host "=== Нажми Ctrl+C для остановки Frontend ===" -ForegroundColor Yellow
Write-Host ""

Set-Location frontend
npm run dev
