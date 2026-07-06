<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-07-06 | Updated: 2026-07-06 -->

# scripts

## Purpose

PowerShell-скрипты для локальной разработки (запуск backend/frontend/Telegram-бота, первичная настройка окружения, smoke-проверка production) плюс подкаталоги с самостоятельными Python-утилитами: пайплайн промо-роликов, настройка Kinescope DRM, Prodamus REST-действия, Railway-админ/DRM-деплой и обработка фото работ для лендинга.

## Key Files

| File | Description |
|------|-------------|
| [`dev.ps1`](dev.ps1) | Backend в новом окне PowerShell (`backend\venv`, `uvicorn app.main:app --reload`, порт 8000) + frontend (`npm run dev`, порт 3000) в текущем окне |
| [`dev-backend.ps1`](dev-backend.ps1) | Только backend: активирует `backend\venv`, `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`; Swagger `http://127.0.0.1:8000/docs` |
| [`dev-frontend.ps1`](dev-frontend.ps1) | Только frontend: `cd frontend; npm run dev` на `http://localhost:3000` |
| [`run_bot.ps1`](run_bot.ps1) | Telegram-бот: активирует `backend\venv`, ставит `PYTHONPATH`, запускает `python app/bot/main.py` — отдельный процесс, не часть FastAPI |
| [`setup-local.ps1`](setup-local.ps1) | Проверяет Python 3.11+/Node 18+/службу PostgreSQL, создаёт `backend\venv` |
| [`smoke-production.ps1`](smoke-production.ps1) | Post-deploy smoke-check: `curl` на `{Backend}/health`, `{Frontend}/`, `/robots.txt`, `/sitemap.xml`; параметры `-FrontendUrl -BackendUrl` (обязательны); в конце напоминает про ручную проверку Prodamus webhook и Kinescope playback |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| [`promo/`](promo/) | Офлайн-пайплайн: `video-lessons/*.mp4` → транскрипт Whisper → подбор хайлайтов → сборка `promo.mp4` → опциональная загрузка в Kinescope → `program.json`. Свой [`AGENTS.md`](promo/AGENTS.md) |
| [`kinescope/`](kinescope/) | Настройка и отладка Kinescope DRM Authorization Backend (генерация ключей/JWK, регистрация webhook, подпись/проверка токенов). Свой [`AGENTS.md`](kinescope/AGENTS.md) |
| `prodamus/` | [`actions.py`](prodamus/actions.py) — автономный CLI: подписанные checkout-ссылки, верификация подписи webhook, REST-действия подписок (`setActivity`, `setSubscriptionPaymentDate`, `setSubscriptionDiscount`). Отдельный `AGENTS.md` не создаётся |
| `railway/` | [`create_admin.py`](railway/create_admin.py) — создание/апгрейд админа напрямую через `asyncpg` + `bcrypt` (без импорта backend-кода); [`push_drm_variables.ps1`](railway/push_drm_variables.ps1) — заливка Kinescope DRM-переменных из `.env` + PEM в Railway (backend-сервис). Отдельный `AGENTS.md` не создаётся |
| `works_photos/` | [`process.py`](works_photos/process.py) — обрабатывает `photo-work/*` в WebP (1024/640) для `frontend/public/works/<slug>/` и перегенерирует манифест `frontend/src/lib/landing/works-photos.ts`. Отдельный `AGENTS.md` не создаётся |

## For AI Agents

### Working In This Directory

- Все `.ps1` рассчитаны на запуск из корня репозитория (проверяют `Test-Path "backend"` / `"frontend"`) и на Windows PowerShell — не bash-синтаксис.
- Backend-скрипты активируют `backend\venv\Scripts\Activate.ps1` — venv должен существовать (создаётся `setup-local.ps1` или вручную).
- Python-утилиты в подкаталогах (`promo/`, `kinescope/`, `prodamus/`, `railway/`, `works_photos/`) самостоятельны: у каждой свои зависимости/venv, они не обязаны работать внутри backend-окружения.
- Секреты (`.env`, `*.pem`, `scripts/*/.last-setup-output.txt`) никогда не коммитить и не цитировать в чате — правила в корневом [`.gitignore`](../.gitignore).

### Testing Requirements

- Автоматических тестов для скриптов в этом каталоге нет; проверка — фактический запуск (для dev-скриптов — по логам старта Uvicorn/Next.js, для `smoke-production.ps1` — по коду возврата `curl`).
- Перед PR с изменением `.ps1` прогнать сценарий вручную на Windows PowerShell.

### Common Patterns

- PowerShell: `Write-Host -ForegroundColor` (Cyan/Green/Yellow/Red) для статусов, ранний `exit 1` при неудачной проверке предусловий.
- Python CLI в подкаталогах: `argparse`, docstring-заголовок с примером запуска и списком нужных env-переменных, `from __future__ import annotations`, ручное добавление корня репозитория в `sys.path` через `Path(__file__).resolve().parents[N]`.

## Dependencies

### Internal

- [`backend/app/main.py`](../backend/app/main.py), [`backend/app/bot/main.py`](../backend/app/bot/main.py), `backend/venv`
- `frontend/` (`npm run dev` / `npm run build`)
- [`scripts/promo/program.json`](promo/program.json) ↔ БД через `promo/sync_program_to_db.py`
- [`backend/app/services/kinescope_jwt_service.py`](../backend/app/services/kinescope_jwt_service.py) ↔ `scripts/kinescope/*`
- [`backend/app/services/prodamus_service.py`](../backend/app/services/prodamus_service.py) ↔ `scripts/prodamus/actions.py` (та же логика подписи)

### External

- PowerShell 5.1+, Node.js 18+, Python 3.11+, PostgreSQL 15
- `curl.exe` (для `smoke-production.ps1`)
- Railway CLI (`railway run` — для `railway/create_admin.py` в production и `railway/push_drm_variables.ps1`)

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
