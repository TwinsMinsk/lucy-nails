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
| [`scripts/`](scripts/) | PowerShell: `dev.ps1`, setup, и т.д. |
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
| [`backend/requirements.txt`](backend/requirements.txt) | Зависимости Python |

## Frontend (`frontend/`)

| Путь | Назначение |
|------|------------|
| [`frontend/src/app/`](frontend/src/app/) | Next.js App Router: публичные, protected, admin маршруты |
| [`frontend/src/components/`](frontend/src/components/) | UI (shadcn), layout, course, landing |
| [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts) | Клиент API, `NEXT_PUBLIC_API_URL` |
| [`frontend/src/lib/schemas.ts`](frontend/src/lib/schemas.ts) | Схемы/валидации (Zod и т.п.) |
| [`frontend/components.json`](frontend/components.json) | Конфиг shadcn/ui |
| [`frontend/package.json`](frontend/package.json) | Скрипты: `dev`, `build`, `lint` |
| [`frontend/.env.example`](frontend/.env.example) | Шаблон для `frontend/.env.local` |

## Тесты и качество

- **Backend:** `ruff check backend/app backend/tests`, `pytest backend/tests` — см. [`AGENTS.md`](AGENTS.md).
- **Frontend:** `npm run lint`, `npm run build` из каталога `frontend`.

## Известный техдолг (для осторожности)

- Seed пользователей при старте и CORS «для отладки» в [`backend/app/main.py`](backend/app/main.py) — пересмотреть перед жёстким production-hardening (см. [`AGENTS.md`](AGENTS.md)).
- В frontend нет скрипта `npm test`; UI-регрессии пока через lint + ручная проверка + backend-тесты.
