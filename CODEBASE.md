# CODEBASE — карта репозитория Lucy-nails

Краткий индекс для людей и для AI. Подробнее: [`Docs/ARCHITECTURE.md`](Docs/ARCHITECTURE.md), onboarding: [`AGENTS.md`](AGENTS.md).

## Корень

| Путь | Назначение |
|------|------------|
| [`README.md`](README.md) | Быстрый старт |
| [`AGENTS.md`](AGENTS.md) | Главный вход для Cursor Agent |
| [`pyproject.toml`](pyproject.toml) | Настройки Ruff (Python) |
| [`railway.toml`](railway.toml) | Railway monorepo сервисы |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | CI (ruff, pytest, ESLint, Next build) |
| [`.env.example`](.env.example) | Шаблон env для backend и общих ключей |
| [`compose.dev.yml`](compose.dev.yml) | Локальные PostgreSQL 15 + Redis 7 |
| [`scripts/`](scripts/) | PowerShell: `dev.ps1`, setup, и т.д. |
| [`scripts/ops/`](scripts/ops/) | PostgreSQL backup/restore с checksum/S3 |
| [`scripts/load/`](scripts/load/) | Staging-only k6 launch gate |
| [`ops/`](ops/) | Backup image и init test database |
| [`scripts/promo/`](scripts/promo/) | Пайплайн промо (Whisper, нарезка, upload/sync); метаданные — [`program.json`](scripts/promo/program.json) |
| `promo-clips/`, `video-lessons/` | Локальные тяжёлые mp4-артефакты; исключены из Git |
| [`Docs/`](Docs/) | PRD, архитектура, фазы, задачи, ops |

## Backend (`backend/`)

| Путь | Назначение |
|------|------------|
| [`backend/app/main.py`](backend/app/main.py) | FastAPI app, lifespan, CORS, подключение роутеров |
| [`backend/app/api/`](backend/app/api/) | REST роутеры (`auth`, `courses`, `payments`, `admin`, …) |
| [`backend/app/core/`](backend/app/core/) | `config.py`, `database.py`, `security.py`, `dependencies.py` |
| [`backend/app/models/`](backend/app/models/) | SQLAlchemy модели |
| [`backend/app/schemas/`](backend/app/schemas/) | Pydantic схемы |
| [`backend/app/services/`](backend/app/services/) | Бизнес-логика и интеграции (Prodamus, Kinescope, email, …) |
| [`backend/app/bot/`](backend/app/bot/) | Telegram bot (handlers, entry) |
| [`backend/alembic/`](backend/alembic/) | Миграции БД |
| [`backend/tests/`](backend/tests/) | Pytest + httpx AsyncClient |
| [`backend/requirements.lock`](backend/requirements.lock) | Зафиксированные runtime зависимости Python 3.11 |
| [`backend/requirements-dev.lock`](backend/requirements-dev.lock) | Test/development зависимости |
| [`backend/requirements-tooling.lock`](backend/requirements-tooling.lock) | Audit/tooling зависимости |

## Frontend (`frontend/`)

| Путь | Назначение |
|------|------------|
| [`frontend/src/app/`](frontend/src/app/) | Next.js App Router: публичные, protected, admin маршруты |
| [`frontend/src/components/`](frontend/src/components/) | UI (shadcn), layout, course, landing |
| [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts) | Клиент API, `NEXT_PUBLIC_API_URL` |
| [`frontend/src/lib/schemas.ts`](frontend/src/lib/schemas.ts) | Схемы/валидации (Zod и т.п.) |
| [`frontend/components.json`](frontend/components.json) | Конфиг shadcn/ui |
| [`frontend/package.json`](frontend/package.json) | Скрипты: `dev`, `build`, `lint` |
| [`frontend/e2e/`](frontend/e2e/) | Playwright Chromium/WebKit critical-flow tests |
| [`frontend/.env.example`](frontend/.env.example) | Шаблон для `frontend/.env.local` |

## Тесты и качество

- **Backend:** Ruff, pip-audit, Alembic single-head round-trip и полный PostgreSQL pytest.
- **Frontend:** ESLint, Vitest, npm audit, production build и Playwright Chromium/WebKit.
- **CI:** [`.github/workflows/ci.yml`](.github/workflows/ci.yml); CodeQL/Gitleaks — [`security.yml`](.github/workflows/security.yml).

## Известный техдолг (для осторожности)

- Development seed запускается только при `ENVIRONMENT=development`; не расширять его на staging/production.
- CORS origins и trusted hosts fail-closed в production; при изменении proxy topology повторять cookie/CSRF edge tests.
- Крупный backend admin router в [`backend/app/api/admin.py`](backend/app/api/admin.py) и frontend API client в [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts) — кандидаты на доменную декомпозицию.
- Pydantic v2 deprecation warnings и один legacy admin test skip находятся в P2 текущего аудита.

## Backlog рефакторинга

- Подробная программа: [`Docs/06_Tracking/REFACTORING_ROADMAP.md`](Docs/06_Tracking/REFACTORING_ROADMAP.md).
- **Документация:** держать `AGENTS.md` кратким, `CODEBASE.md` как карту, `README.md` как быстрый старт, подробный процесс — в [`Docs/04_Setup_Ops/DEVELOPMENT_WORKFLOW.md`](Docs/04_Setup_Ops/DEVELOPMENT_WORKFLOW.md).
- **Backend:** выровнять auth dependencies через [`backend/app/core/dependencies.py`](backend/app/core/dependencies.py), затем разобрать admin API, транзакции и Pydantic v2-паттерны.
- **Frontend:** разнести [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts) по доменам, разгрузить лендинг и крупные client-страницы админки.
- **Проверки:** сверять [`AGENTS.md`](AGENTS.md), workflow-документ и [`.github/workflows/ci.yml`](.github/workflows/ci.yml) при изменении команд качества.
