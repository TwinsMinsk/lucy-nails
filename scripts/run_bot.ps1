
# Скрипт для запуска Telegram бота
Write-Host "=== Запуск Telegram Bot ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path "backend")) {
    Write-Host "[ERROR] Папка 'backend' не найдена!" -ForegroundColor Red
    exit 1
}

$backendPath = Join-Path $PSScriptRoot "..\backend"
Set-Location $backendPath

# Активация окружения и запуск
.\venv\Scripts\Activate.ps1
$env:PYTHONPATH = $PWD
python app/bot/main.py
