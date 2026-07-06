<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-07-06 | Updated: 2026-07-06 -->

# backend

## Purpose
Python-часть монорепозитория: FastAPI (async) API для платформы видео-курсов по маникюру, отдельный Telegram-бот, Alembic-миграции, pytest-тесты и одноразовые ops-скрипты. Деплоится на Railway как отдельный сервис (см. `Procfile`).

## Key Files
| File | Description |
|------|-------------|
| `Procfile` | Команда Railway для web-процесса: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` — миграции применяются перед стартом сервера. |
| `alembic.ini` | Конфиг Alembic; `script_location = alembic`, `sqlalchemy.url` — дефолт для локальной разработки (реальный URL подменяется в `alembic/env.py` из `settings.DATABASE_URL`). |
| `requirements.txt` | Зависимости: FastAPI 0.115, SQLAlchemy 2 (asyncio) + asyncpg + alembic, pydantic v2, python-jose/passlib/bcrypt (auth), slowapi (rate limit), python-telegram-bot 21.10 (бот, не aiogram), httpx, firecrawl-py, ruff/pytest (dev). |
| `.gitignore` | Исключает `venv/`, `.env*`, `logs/`, `.pytest_cache/`. |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `app/` | FastAPI-приложение (see `app/AGENTS.md`) |
| `alembic/` | Миграции схемы БД (see `alembic/AGENTS.md`) |
| `tests/` | pytest-тесты (see `tests/AGENTS.md`) |
| `scripts/` | Одноразовые/эксплуатационные CLI-утилиты, без собственного AGENTS.md — см. таблицу ниже |
| `secrets/` | Локальные секреты (например, `kinescope_drm_private.pem`); содержимое не читать и не цитировать, каталог не должен попадать в Git |

### `scripts/` — назначение файлов
| File | Description |
|------|-------------|
| `create_db.py` | Создаёт локальную БД `nails_course` (подключение к maintenance-БД `postgres` через psycopg2, параметры из `DATABASE_URL`). |
| `create_test_db.py` | То же для тестовой БД `test_nails_course`. |
| `create_admin.py` | Создаёт/повышает до admin первого продакшн-пользователя через `ensure_admin_user`; email/пароль — из env `ADMIN_EMAIL`/`ADMIN_PASSWORD`. |
| `seed_data.py` | Наполняет dev-БД тестовыми данными напрямую через psycopg2 (не через ORM); читает промо-метаданные из `scripts/promo/program.json` в корне репо, если файл есть. |
| `add_folga_module.py` | Одноразовый идемпотентный скрипт: публикует модуль «Фольга» и проставляет ему реальный Kinescope video id. |
| `sync_lessons_content.py` | Одноразовый идемпотентный скрипт синхронизации текстов курса/уроков с landing-контентом (конспекты, promo-описания, чистка «битой» кириллицы). |
| `check_production_content.py` | Валидация опубликованного контента курсов перед релизом (проверяет `Course`/`Module`/`Lesson` через ORM). |
| `fetch_docs.py` | Утилита на Firecrawl для скачивания внешней документации в файлы (использует `FIRECRAWL_API_KEY` из `.env`). |

## For AI Agents

### Working In This Directory
- Любое изменение моделей в `app/models/` **обязательно** сопровождается новой миграцией в `alembic/versions/` — иначе расхождение всплывёт только на шаге CI `alembic upgrade head`.
- Скрипты в `scripts/`, помеченные «One-off»/«Idempotent» (`add_folga_module.py`, `sync_lessons_content.py`), писались под конкретное разовое состояние БД — не обобщай их в переиспользуемые утилиты без необходимости.
- `secrets/` не читать содержимое файлов и не выводить их в чат/коммиты.
- Бот (`app/bot/`) — отдельный процесс, не роутер FastAPI; не пытайся подключить его через `include_router` в `app/main.py`.

### Testing Requirements
```powershell
ruff check backend/app backend/tests
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -v --tb=short
```
Перед тестами нужны две локальные Postgres-БД: `nails_course` и `test_nails_course` (см. `tests/AGENTS.md`).

### Common Patterns
- Все ORM-операции — через async SQLAlchemy 2 (`AsyncSession`, `select(...)`, `selectinload` для eager loading).
- Разовые скрипты добавляют корень репозитория/бэкенда в `sys.path` вручную (`sys.path.append(str(Path(__file__).resolve().parents[N]))`), т.к. запускаются не как пакет.

## Dependencies

### Internal
`app/core/config.py` (`Settings`) читается всеми слоями; `app/core/database.py` — единственный источник `async_session_maker`/`get_db`.

### External
FastAPI, SQLAlchemy 2 (async) + asyncpg, Alembic, Pydantic v2, python-jose + passlib/bcrypt, slowapi, python-telegram-bot, httpx, psycopg2-binary (sync-скрипты и Alembic).

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
