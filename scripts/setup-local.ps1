# Скрипт настройки локального окружения для Windows (без Docker)
# Запуск: .\scripts\setup-local.ps1

Write-Host "=== Настройка локального окружения для Nails Course ===" -ForegroundColor Cyan
Write-Host ""

# Проверка Python
$pythonVersion = python --version 2>&1
if ($pythonVersion -match "Python 3\.(1[1-9]|[2-9][0-9])") {
    Write-Host "[OK] $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "[!] Python 3.11+ не найден. Скачайте: https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

# Проверка Node.js
$nodeVersion = node --version 2>&1
if ($nodeVersion -match "v(1[8-9]|[2-9][0-9])") {
    Write-Host "[OK] Node.js $nodeVersion" -ForegroundColor Green
} else {
    Write-Host "[!] Node.js 18+ не найден. Скачайте: https://nodejs.org/" -ForegroundColor Red
    exit 1
}

# Проверка PostgreSQL
$pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
if ($pgService) {
    Write-Host "[OK] PostgreSQL найден" -ForegroundColor Green
} else {
    Write-Host "[!] PostgreSQL не найден." -ForegroundColor Yellow
    Write-Host "    Скачайте: https://www.postgresql.org/download/windows/" -ForegroundColor Yellow
    Write-Host "    Или используйте облачный сервис (Railway, Supabase)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Настройка Backend ===" -ForegroundColor Yellow

Set-Location -Path $PSScriptRoot\..\backend -ErrorAction SilentlyContinue
if (-not (Test-Path "backend")) {
    New-Item -ItemType Directory -Path "..\backend" -Force | Out-Null
}
Set-Location -Path $PSScriptRoot\..

# Backend: создание venv
if (-not (Test-Path "backend\venv")) {
    Write-Host "Создание виртуального окружения..." -ForegroundColor Cyan
    python -m venv backend\venv
}

Write-Host ""
Write-Host "=== Готово! ===" -ForegroundColor Green
Write-Host ""
Write-Host "Следующие шаги:" -ForegroundColor White
Write-Host "1. Создайте базу данных PostgreSQL: createdb nails_course" -ForegroundColor White
Write-Host "2. Скопируйте .env.example в .env и заполните" -ForegroundColor White
Write-Host "3. Backend: cd backend && .\venv\Scripts\Activate.ps1 && pip install -r requirements.txt" -ForegroundColor White
Write-Host "4. Frontend: cd frontend && npm install" -ForegroundColor White
