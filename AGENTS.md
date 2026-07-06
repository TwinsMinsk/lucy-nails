<!-- Generated: manual | Updated: 2026-07-06 (deepinit: добавлена иерархия AGENTS.md) -->

# AGENTS.md — ориентир для AI в Cursor

Этот файл — **главная точка входа** для агента в Cursor. Детальные правила: [`.cursor/rules/`](.cursor/rules). Карта кода: [`CODEBASE.md`](CODEBASE.md).

## Иерархия AGENTS.md

В ключевых каталогах лежат локальные `AGENTS.md` с деталями по этой части кода; тег `<!-- Parent: ../AGENTS.md -->` в каждом из них ведёт к родителю. Перед работой в каталоге читай его `AGENTS.md`:

- [`backend/AGENTS.md`](backend/AGENTS.md) — backend в целом (Procfile, requirements, служебные скрипты)
  - [`backend/app/AGENTS.md`](backend/app/AGENTS.md) — FastAPI-приложение: `main.py`, lifespan, middleware
    - [`api/`](backend/app/api/AGENTS.md) · [`bot/`](backend/app/bot/AGENTS.md) · [`core/`](backend/app/core/AGENTS.md) · [`models/`](backend/app/models/AGENTS.md) · [`schemas/`](backend/app/schemas/AGENTS.md) · [`services/`](backend/app/services/AGENTS.md)
  - [`backend/alembic/AGENTS.md`](backend/alembic/AGENTS.md) — миграции БД
  - [`backend/tests/AGENTS.md`](backend/tests/AGENTS.md) — pytest, тестовая БД
- [`frontend/AGENTS.md`](frontend/AGENTS.md) — Next.js-приложение, env, проверки
  - [`frontend/src/AGENTS.md`](frontend/src/AGENTS.md) → [`app/`](frontend/src/app/AGENTS.md) · [`components/`](frontend/src/components/AGENTS.md) · [`lib/`](frontend/src/lib/AGENTS.md)
  - [`frontend/public/AGENTS.md`](frontend/public/AGENTS.md) — статика и фото работ
- [`scripts/AGENTS.md`](scripts/AGENTS.md) — dev-скрипты; детали: [`promo/`](scripts/promo/AGENTS.md), [`kinescope/`](scripts/kinescope/AGENTS.md)
- [`Docs/AGENTS.md`](Docs/AGENTS.md) — карта документации

## Стек

- **Frontend:** Next.js **16** (App Router), React **19**, TypeScript, Tailwind CSS, Radix/shadcn-паттерн — [`frontend/`](frontend/), [`frontend/components.json`](frontend/components.json).
- **Backend:** Python **3.11+**, FastAPI, SQLAlchemy 2 **async**, Alembic, Pydantic v2 — [`backend/app/`](backend/app/).
- **БД:** PostgreSQL 15 (asyncpg), Redis опционально.
- **Интеграции:** Kinescope, Prodamus, Telegram — см. сервисы в [`backend/app/services/`](backend/app/services/).

## Обязательно прочитать перед существенными изменениями

1. [`CODEBASE.md`](CODEBASE.md) — где что лежит.
2. [`Docs/04_Setup_Ops/DEVELOPMENT_WORKFLOW.md`](Docs/04_Setup_Ops/DEVELOPMENT_WORKFLOW.md) — окружения, `.env`, команды, Git, Railway, проверки.
3. [`Docs/ARCHITECTURE.md`](Docs/ARCHITECTURE.md) — архитектура и схема данных.
4. [`Docs/06_Tracking/TASKS.md`](Docs/06_Tracking/TASKS.md) — текущие задачи и отложенный backlog.

## Наведение порядка и крупный рефакторинг

- Делить работу на маленькие PR/коммиты: сначала документы и правила, затем `.gitignore`/артефакты, потом backend/frontend по доменам.
- Перед изменением runtime-кода сначала понять текущий контракт через тесты, API-схемы и страницы-потребители.
- Не смешивать рефакторинг с изменением поведения, если это не зафиксировано в задаче и не покрыто проверкой.
- Если файл уже большой, рефакторить вокруг понятной границы ответственности: роутер, сервис, схема, компонент, hook, API client.

## Секреты и `.env`

- **Не** вставлять реальные ключи в чат, PR и примеры кода.
- **Не** коммитить `.env`, `frontend/.env.local`. Шаблоны: [`.env.example`](.env.example), [`frontend/.env.example`](frontend/.env.example).
- Backend читает корневой `.env` и при необходимости `backend/.env` — см. [`backend/app/core/config.py`](backend/app/core/config.py).
- Next.js читает переменные из каталога `frontend/` (например `frontend/.env.local`).

## Команды проверки (как в CI)

Из корня репозитория:

**Backend:**

```powershell
pip install -r backend/requirements.txt
ruff check backend/app backend/tests
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -v --tb=short
```

(Нужны БД `nails_course` и `test_nails_course` — см. workflow-документ.)

**Frontend:**

```powershell
cd frontend
npm ci
npm run lint
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8000/api"
$env:NEXT_PUBLIC_SITE_URL = "http://localhost:3000"
npm run build
```

Полный пайплайн: [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Локальный запуск (Windows)

См. [`README.md`](README.md) и [`scripts/dev.ps1`](scripts/dev.ps1).

## Локальные артефакты и медиа

- `promo-clips/`, `video-lessons/` и `scripts/promo/output/` — локальные тяжёлые файлы, не коммитить.
- Промо-пайплайн: [`scripts/promo/README.md`](scripts/promo/README.md), метаданные программы: [`scripts/promo/program.json`](scripts/promo/program.json).
- Если видео нужно сохранить надолго, хранить его вне Git (Kinescope/облако/LFS по отдельному решению), а в репозитории держать только код, метаданные и документацию.

## Правила кода (кратко)

- **Auth:** через FastAPI dependencies (`get_current_user`, admin-guards). **Не** опираться на RLS в БД для авторизации приложения.
- **ORM:** только async-сессии; при необходимости eager-loading (`selectinload`).
- **Транзакции:** не менять политику `commit`/`rollback` точечно; сначала сверить [`backend/app/core/database.py`](backend/app/core/database.py) и места явных `commit`.
- **Next.js:** Server Components по умолчанию; `'use client'` только где нужна интерактивность.
- **Изменение схемы БД:** всегда с миграцией Alembic в [`backend/alembic/versions/`](backend/alembic/versions/).
- **Деплой:** Railway — [`railway.toml`](railway.toml), гайды в [`Docs/04_Setup_Ops/`](Docs/04_Setup_Ops/).

## Язык

- Ответы пользователю — **на русском**, если пользователь пишет по-русски.
- Комментарии в коде и имена переменных — **как уже принято в затрагиваемом файле** (в проекте встречается русская документация в docstring/UI).

## Справочный архив Antigravity

Папка [`.agent/`](.agent/) и [`GEMINI.md`](GEMINI.md) — наследие предыдущей IDE. Для Cursor **приоритет**: `AGENTS.md` → `.cursor/rules` → затем точечное чтение `.agent/skills/...` по задаче.

## Известный техдолг (не ломать неосторожно)

- В [`backend/app/main.py`](backend/app/main.py): стартовый seed пользователей с известными паролями и широкий CORS — для production нужна отдельная политика (env-only origins, выключить seed или только `development`).
- Во frontend нет скрипта `npm test` — регрессии ловятся lint + build + backend pytest.
