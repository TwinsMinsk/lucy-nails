# backend

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose
Python-часть монорепозитория: FastAPI (async) API для платформы видео-курсов по маникюру, два отдельных процесса (outbox-воркер уведомлений и Telegram-бот), Alembic-миграции, pytest-тесты и одноразовые ops-скрипты. Деплоится на Railway как отдельный сервис (см. `Procfile`; настройки сервиса хранятся в Railway, значения — [`LAUNCH_OPERATIONS.md`](../Docs/04_Setup_Ops/LAUNCH_OPERATIONS.md)).

## Key Files
| File | Description |
|------|-------------|
| `Procfile` | Railway processes: `web` (`alembic upgrade head`, затем `uvicorn app.main:app` с `--proxy-headers --forwarded-allow-ips`), `worker` (`python -m app.workers.outbox`), `bot` (`python -m app.bot.main`). |
| `alembic.ini` | Конфиг Alembic; `script_location = alembic`, `prepend_sys_path = .` (запускать из `backend/`), `sqlalchemy.url` — дефолт для локальной разработки (реальный URL подменяется в `alembic/env.py` из `settings.DATABASE_URL`). |
| `requirements.txt` / `requirements.lock` | Только production runtime: FastAPI/Starlette, SQLAlchemy/asyncpg/Alembic, PyJWT+cryptography, Redis rate limit, email/Telegram/certificates. |
| `requirements-dev.*` / `requirements-tooling.*` | Pytest/Ruff и отдельные audit/docs utilities; не устанавливаются в runtime image. |
| `.gitignore` | Исключает `venv/`, `__pycache__/`, `*.pyc`/`*.pyo`, `.env`, `.env.*`, `logs/`, `.pytest_cache/`. |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `app/` | FastAPI-приложение, воркер и бот (see `app/AGENTS.md`) |
| `alembic/` | Миграции схемы БД (see `alembic/AGENTS.md`) |
| `tests/` | pytest-тесты (see `tests/AGENTS.md`) |
| `scripts/` | Одноразовые/эксплуатационные CLI-утилиты, без собственного AGENTS.md — см. таблицу ниже |
| `secrets/` | Только локально (игнорируется корневым `.gitignore`, в чистом checkout отсутствует): секреты, например `kinescope_drm_private.pem`; содержимое не читать и не цитировать, каталог не должен попадать в Git |

### `scripts/` — назначение файлов
| File | Description |
|------|-------------|
| `create_db.py` | Создаёт локальную БД `nails_course` (подключение к maintenance-БД `postgres` через psycopg2, параметры из `DATABASE_URL`). |
| `create_test_db.py` | То же для тестовой БД `test_nails_course`. |
| `create_admin.py` | Создаёт/повышает до admin первого продакшн-пользователя через `ensure_admin_user` (пароль от 12 символов; если RBAC-роли посеяны, назначает `owner`); email/пароль — из env `ADMIN_EMAIL`/`ADMIN_PASSWORD`. |
| `seed_data.py` | Наполняет dev-БД актуальными Course/Purchase/Entitlement/RBAC данными. **Сначала делает `TRUNCATE ... CASCADE`, проверки окружения нет** — подключение из `POSTGRES_*`, запускать только на локальной БД. Требует `SEED_*_PASSWORD` (от 12 символов) и не логирует их. |
| `add_folga_module.py` | Одноразовый идемпотентный скрипт (psycopg2, `DATABASE_URL`): публикует модуль «Фольга» и проставляет ему реальный Kinescope video id. |
| `sync_lessons_content.py` | Одноразовый идемпотентный скрипт (psycopg2, `DATABASE_URL`) синхронизации текстов курса/уроков с landing-контентом (конспекты, promo-описания, чистка «битой» кириллицы). |
| `check_production_content.py` | Валидация опубликованного контента перед релизом через ORM: есть опубликованные курсы, у закрытых уроков опубликованных модулей задан `kinescope_video_id`. |
| `generate_certificate_template.py` | Генерирует статичный фон диплома `app/assets/certificates/template.png` (разметка — `app/services/certificate_layout.py`). |
| `fetch_docs.py` | Утилита на Firecrawl для скачивания внешней документации в файлы (использует `FIRECRAWL_API_KEY` из `backend/.env`, зависимости — `requirements-tooling.*`). |

## For AI Agents

### Working In This Directory
- Любое изменение моделей в `app/models/` **обязательно** сопровождается новой миграцией в `alembic/versions/` — иначе расхождение всплывёт только в CI на шагах `alembic upgrade head` и `alembic check`.
- Скрипты в `scripts/`, помеченные «One-off»/«Idempotent» (`add_folga_module.py`, `sync_lessons_content.py`), писались под конкретное разовое состояние БД — не обобщай их в переиспользуемые утилиты без необходимости.
- `secrets/` не читать содержимое файлов и не выводить их в чат/коммиты.
- Бот (`app/bot/`) и воркер (`app/workers/`) — отдельные процессы, не роутеры FastAPI; не пытайся подключить их через `include_router` в `app/main.py`.

### Testing Requirements
```powershell
ruff check backend/app backend/tests
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -v --tb=short
```
Перед тестами нужны две локальные Postgres-БД: `nails_course` и `test_nails_course` (см. `tests/AGENTS.md`).

### Common Patterns
- Все ORM-операции — через async SQLAlchemy 2 (`AsyncSession`, `select(...)`, `selectinload` для eager loading).
- Скрипты, импортирующие `app.*` (`create_admin.py`, `check_production_content.py`, `generate_certificate_template.py`, `seed_data.py`), добавляют `backend/` в `sys.path` вручную, т.к. запускаются не как пакет. Скрипты на чистом psycopg2 (`create_db.py`, `create_test_db.py`, `add_folga_module.py`, `sync_lessons_content.py`) от `app` не зависят.

## Dependencies

### Internal
`app/core/config.py` (`Settings`) читается всеми слоями; `app/core/database.py` — единственный источник `async_session_maker`/`get_db`.

### External
FastAPI, SQLAlchemy 2 (async) + asyncpg, Alembic, Pydantic v2, PyJWT + cryptography, passlib/bcrypt, pyotp, Redis/slowapi, python-telegram-bot, httpx, aiosmtplib, Pillow/qrcode/img2pdf, psycopg2-binary.

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
