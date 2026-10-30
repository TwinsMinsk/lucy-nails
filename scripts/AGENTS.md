# scripts

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose

PowerShell-скрипты для локальной разработки (запуск backend/frontend/Telegram-бота, первичная настройка окружения, smoke-проверка production) плюс подкаталоги с самостоятельными утилитами: пайплайн промо-роликов, пересборка субтитров уроков, настройка Kinescope DRM, Prodamus REST-действия, Railway-админ/DRM-деплой, обработка фото работ для лендинга, нагрузочная приёмка на staging (k6) и PostgreSQL backup/restore.

## Key Files

| File | Description |
|------|-------------|
| [`dev.ps1`](dev.ps1) | Backend в новом окне PowerShell (`backend\venv`, `uvicorn app.main:app --reload`, порт 8000) + frontend (`npm run dev`, порт 3000) в текущем окне |
| [`dev-backend.ps1`](dev-backend.ps1) | Только backend: активирует `backend\venv`, `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`; Swagger `http://127.0.0.1:8000/docs` |
| [`dev-frontend.ps1`](dev-frontend.ps1) | Только frontend: `cd frontend; npm run dev` на `http://localhost:3000` |
| [`run_bot.ps1`](run_bot.ps1) | Telegram-бот: активирует `backend\venv`, ставит `PYTHONPATH`, запускает `python app/bot/main.py` — отдельный процесс, не часть FastAPI |
| [`setup-local.ps1`](setup-local.ps1) | Проверяет Python 3.11+/Node 18+/службу PostgreSQL, создаёт `backend\venv`; проверка Node мягче требования `frontend/package.json` (`>=20.9.0`) |
| [`smoke-production.ps1`](smoke-production.ps1) | Post-deploy smoke-check, также для staging URL: `curl` на `{Backend}/health`, `{Frontend}/`, `/robots.txt`, `/sitemap.xml`; параметры `-FrontendUrl -BackendUrl` (обязательны); в конце напоминает про ручную проверку Prodamus webhook и Kinescope playback |
| [`__init__.py`](__init__.py) | Пустой; делает `scripts` пакетом для импортов `scripts.promo.*` и `scripts.ops.*` (их использует [`backend/tests/test_backup_bundle.py`](../backend/tests/test_backup_bundle.py)) |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| [`promo/`](promo/) | Офлайн-пайплайн: `video-lessons/*.mp4` → транскрипт Whisper → подбор хайлайтов → сборка `promo.mp4` → опциональная загрузка в Kinescope → `program.json`. Свой [`AGENTS.md`](promo/AGENTS.md) |
| [`kinescope/`](kinescope/) | Настройка и отладка Kinescope DRM Authorization Backend (генерация ключей/JWK, регистрация webhook, подпись/проверка токенов). Свой [`AGENTS.md`](kinescope/AGENTS.md) |
| [`subtitles/`](subtitles/) | Пересборка субтитров и мягкий цветокор: `video-lessons/*.mp4` → распознавание со словными таймкодами → правка терминов → разбивка по правилам вещательных субтитров → вжигание поверх матовой плашки, скрывающей старые вшитые титры → `video-lessons-remastered/<slug>/`. Свой [`AGENTS.md`](subtitles/AGENTS.md) |
| `load/` | Staging-only k6 gate. [`launch-readiness.js`](load/launch-readiness.js): `LOAD_PROFILE=acceptance` — 50 учеников 15 минут, 100 на 5 минут, 10 checkout и 50 повторов webhook; `smoke` — 5 учеников 60 секунд и та же денежная проба. Требует `ALLOW_STAGING_LOAD=true`, localhost или staging-хост в `API_BASE_URL` и отдельные session-bound токены из [`seed_staging.py`](load/seed_staging.py) (`--confirm-database`, `--output`; пустая БД с `load_staging` в имени, `ENVIRONMENT=test/staging`). Порядок приёмки — [`README.md`](load/README.md). Отдельный `AGENTS.md` не создаётся |
| `ops/` | Проверяемые PostgreSQL backup/restore CLI с SHA-256, S3 и Telegram alert. [`backup_postgres.py`](ops/backup_postgres.py) (`--output-dir`, `--uploads-dir`): `.dump` или `.tar` с uploads и `manifest.json`. [`restore_postgres.py`](ops/restore_postgres.py) (позиционный `source`, `--confirm-database`, `--database-url`, `--uploads-dir`, `--allow-production`): только в пустую БД. Образ и cron — [`ops/AGENTS.md`](../ops/AGENTS.md), процедуры — [`BACKUP_RESTORE.md`](../Docs/04_Setup_Ops/BACKUP_RESTORE.md), [`LAUNCH_OPERATIONS.md`](../Docs/04_Setup_Ops/LAUNCH_OPERATIONS.md). Отдельный `AGENTS.md` не создаётся. [`redact_telegram_tokens.py`](ops/redact_telegram_tokens.py) (`--apply`, без него только считает строки) — разовая очистка токена бота в `outbox_messages.last_error` и `delivery_attempts.error`, нужен `asyncpg`. |
| `prodamus/` | [`actions.py`](prodamus/actions.py) — автономный CLI (`link`, `verify-sign`, `set-activity`, `set-payment-date`, `set-discount`): подписанные checkout-ссылки, верификация подписи webhook, REST-действия подписок (`setActivity`, `setSubscriptionPaymentDate`, `setSubscriptionDiscount`). Отдельный `AGENTS.md` не создаётся |
| `railway/` | [`create_admin.py`](railway/create_admin.py) — создание/апгрейд админа напрямую через `asyncpg` + `bcrypt` (без импорта backend-кода; аргументы `<email> [<password>]`); [`push_drm_variables.ps1`](railway/push_drm_variables.ps1) — заливка Kinescope DRM-переменных из `.env` + PEM в Railway (backend-сервис). Отдельный `AGENTS.md` не создаётся |
| `works_photos/` | [`process.py`](works_photos/process.py) — обрабатывает `photo-work/*` в WebP (1024/640) для `frontend/public/works/<slug>/` и перегенерирует манифест `frontend/src/lib/landing/works-photos.ts`. Отдельный `AGENTS.md` не создаётся |

## For AI Agents

### Working In This Directory

- `dev*.ps1` и `run_bot.ps1` рассчитаны на запуск из корня репозитория (проверяют `Test-Path "backend"` / `"frontend"`); все `.ps1` — на Windows PowerShell, не bash-синтаксис.
- Backend-скрипты активируют `backend\venv\Scripts\Activate.ps1` — venv должен существовать (создаётся `setup-local.ps1` или вручную).
- Python-утилиты в подкаталогах (`promo/`, `kinescope/`, `prodamus/`, `railway/`, `works_photos/`) самостоятельны: у каждой свои зависимости/venv, они не обязаны работать внутри backend-окружения. `ops/` — stdlib и внешние CLI, кроме `redact_telegram_tokens.py` (нужен `asyncpg`). Исключение — `load/seed_staging.py`: импортирует `backend/app` и запускается в backend-окружении.
- `load/`, `ops/`, `railway/`, `kinescope/setup_drm.py` и `prodamus/actions.py set-*` меняют реальные данные или внешние сервисы; запускать только по явному запросу пользователя. k6-сценарий создаёт тестовые данные и не удаляет их; restore с `--allow-production` — только в объявленном инциденте.
- Секреты (`.env`, `*.pem`, `scripts/*/.last-setup-output.txt`, токены в `scripts/load/learners.local.json`) никогда не коммитить и не цитировать в чате — правила в корневом [`.gitignore`](../.gitignore). `load-summary.local.json` из `load/README.md` в `.gitignore` нет: не добавлять его в Git.
- Новый скрипт упомянуть в [`dev_scripts.md`](../Docs/04_Setup_Ops/dev_scripts.md) или README (правило [`.cursor/rules/ops-scripts.mdc`](../.cursor/rules/ops-scripts.mdc)).

### Testing Requirements

- `ops/` покрыт [`backend/tests/test_backup_bundle.py`](../backend/tests/test_backup_bundle.py) (бандл, маркер uploads, guards restore) и [`backend/tests/test_telegram_token_redaction.py`](../backend/tests/test_telegram_token_redaction.py) (скрипт очистки). Запускать из корня через `python -m pytest`, как в CI, чтобы импортировался `scripts.ops`. CI линтует только `backend/app backend/tests`, поэтому `ruff check scripts/ops` — вручную.
- Для остальных скриптов автотестов нет; проверка — фактический запуск (для dev-скриптов — по логам старта Uvicorn/Next.js, для `smoke-production.ps1` — по коду возврата `curl`).
- `load/` — только на изолированном окружении, сначала `LOAD_PROFILE=smoke`. Gate: `http_req_failed <1%`, p95 `<500 ms`, `checks >99%`.
- Перед PR с изменением `.ps1` прогнать сценарий вручную на Windows PowerShell.

### Common Patterns

- PowerShell: `Write-Host -ForegroundColor` (Cyan/Green/Yellow/Red) для статусов, ранний `exit 1` при неудачной проверке предусловий.
- Python CLI в подкаталогах: обычно `argparse`, docstring-заголовок с примером запуска и списком нужных env-переменных, `from __future__ import annotations`, ручное добавление корня репозитория в `sys.path` через `Path(__file__).resolve().parents[N]` (`seed_staging.py` добавляет `backend/`).
- CLI, которые пишут в БД: `--confirm-database` должен точно совпасть с именем БД (`seed_staging.py`, `restore_postgres.py`).

## Dependencies

### Internal

- [`backend/app/main.py`](../backend/app/main.py), [`backend/app/bot/main.py`](../backend/app/bot/main.py), `backend/venv`
- `frontend/` (`npm run dev` / `npm run build`)
- [`scripts/promo/program.json`](promo/program.json) ↔ БД через `promo/sync_program_to_db.py`
- [`backend/app/services/kinescope_jwt_service.py`](../backend/app/services/kinescope_jwt_service.py) ↔ `scripts/kinescope/*`
- [`backend/app/services/prodamus_service.py`](../backend/app/services/prodamus_service.py) ↔ `scripts/prodamus/actions.py` (та же логика подписи)
- [`.claude/skills/kinescope-actions/`](../.claude/skills/kinescope-actions/SKILL.md), [`.claude/skills/prodamus-actions/`](../.claude/skills/prodamus-actions/SKILL.md) — обёртки над `kinescope/drm_actions.py` и `prodamus/actions.py`
- [`ops/backup/Dockerfile`](../ops/backup/Dockerfile) копирует `scripts/ops/*.py` в образ
- `load/seed_staging.py` → `backend/app/core/*`, `backend/app/models/*`, [`session_service.py`](../backend/app/services/session_service.py)
- `load/launch-readiness.js` → API `backend/app/api/` ([`payments.py`](../backend/app/api/payments.py), [`courses.py`](../backend/app/api/courses.py), [`lessons.py`](../backend/app/api/lessons.py))

### External

- PowerShell 5.1+, Node.js `>=20.9.0` (`frontend/package.json`), Python 3.11 ([`.python-version`](../.python-version), CI), PostgreSQL 17 и Redis 7 ([`compose.dev.yml`](../compose.dev.yml))
- `curl.exe` (для `smoke-production.ps1`)
- Railway CLI (`railway run` — для `railway/create_admin.py` в production, `railway variable set` — для `railway/push_drm_variables.ps1`)
- `k6` (для `load/`); `pg_dump`, `pg_restore`, `psql`, `aws` CLI (для `ops/`)

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
