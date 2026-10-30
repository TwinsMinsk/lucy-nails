# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Точки входа в документацию

Перед существенными изменениями прочитай (по убыванию важности):

1. [`AGENTS.md`](AGENTS.md) — стек, проверки CI, известный техдолг.
2. [`CODEBASE.md`](CODEBASE.md) — карта репозитория.
3. [`Docs/04_Setup_Ops/DEVELOPMENT_WORKFLOW.md`](Docs/04_Setup_Ops/DEVELOPMENT_WORKFLOW.md) — окружения, env, Git, Railway.
4. [`Docs/ARCHITECTURE.md`](Docs/ARCHITECTURE.md) — архитектура и схема данных.
5. Точечные правила: [`.cursor/rules/*.mdc`](.cursor/rules/) (формат Cursor; читай как обычный markdown).

`.agent/` и `GEMINI.md` — наследие предыдущей IDE, использовать как справочник, не как источник правил.

## Команды

Все команды — из корня репозитория, кроме помеченных `(frontend)`.

### Разработка

- Backend + Frontend в двух окнах: `.\scripts\dev.ps1`
- Только backend: `.\scripts\dev-backend.ps1` → `http://127.0.0.1:8000` (Swagger `/docs`)
- Только frontend: `.\scripts\dev-frontend.ps1` → `http://localhost:3000`

### Проверки (как в [`.github/workflows/ci.yml`](.github/workflows/ci.yml))

Backend (Python 3.11):
```powershell
pip install -r backend/requirements-dev.lock -r backend/requirements-tooling.lock
pip-audit --strict -r backend/requirements.lock
ruff check backend/app backend/tests
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -v --tb=short
```

Один тест / файл:
```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend/tests/test_courses.py::test_name -v
```

Проверка миграций (`cd backend`, `$env:PYTHONPATH = "."`):
```powershell
alembic upgrade head
alembic heads            # ровно одна
alembic downgrade -1
alembic upgrade head
alembic check            # модели совпадают с миграциями
```

Frontend (`cd frontend`, Node 24 в CI):
```powershell
npm ci
npm run lint
npm test -- --run
npm audit --omit=dev --audit-level=high
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8000/api"
$env:NEXT_PUBLIC_SITE_URL = "http://localhost:3000"
npm run build
npx playwright install chromium webkit
npm run test:e2e
```

`npm test` запускает Vitest (один файл: `npx vitest run src/lib/api.test.ts`), `npm run test:e2e` — Playwright: сам поднимает Next.js и API-фикстуру на портах 3015 и 3016. В CI браузеры ставятся с `--with-deps`.

### Миграции БД

```powershell
cd backend
.\venv\Scripts\Activate.ps1
alembic revision --autogenerate -m "description"
alembic upgrade head
```

Любое изменение моделей в [`backend/app/models/`](backend/app/models/) **обязательно** сопровождается миграцией в [`backend/alembic/versions/`](backend/alembic/versions/). Тестовые фикстуры строят схему через `Base.metadata.create_all` ([`backend/tests/conftest.py`](backend/tests/conftest.py)) — расхождение между моделями и миграциями pytest не покажет, его ловит шаг `alembic check` в CI.

### Тестовая БД

Pytest требует две локальные БД: `nails_course` (берётся из `DATABASE_URL`) и `test_nails_course` (имя выводится автозаменой `/nails_course` → `/test_nails_course` в `conftest.py`). `docker compose -f compose.dev.yml up -d` создаёт обе при первом создании volume. Вручную: см. [`Docs/04_Setup_Ops/postgresql_setup.md`](Docs/04_Setup_Ops/postgresql_setup.md).

## Архитектура (что важно знать поверх кода)

### Монорепо

```
backend/   FastAPI + SQLAlchemy 2 async + Alembic + Pydantic v2
frontend/  Next.js 16 (App Router) + React 19 + Tailwind v4 + shadcn-pattern
scripts/   PowerShell (.ps1) для dev, + промо-пайплайн (Whisper/нарезка), + setup Kinescope DRM, + backup/restore, k6
ops/       образ backup, init-скрипт Postgres, конфиг backup для Railway
Docs/      PRD, архитектура, ops-гайды, трекеры
```

### Backend: трёхслойная структура

- `app/api/*.py` — thin controllers (роутеры FastAPI). Подключаются в [`backend/app/main.py`](backend/app/main.py) через `include_router`.
- `app/services/*.py` — бизнес-логика и интеграции (Prodamus, Kinescope, email).
- `app/models/`, `app/schemas/` — SQLAlchemy ORM и Pydantic схемы.
- `app/core/` — `config.py` (Settings), `database.py` (async engine, `get_db`), `security.py` (JWT/passwords), `dependencies.py` (auth deps), `rate_limit.py` (slowapi).
- Авторизация — **только** через FastAPI `Depends` (`get_current_user`, admin-guards). RLS в БД на авторизацию приложения **не** опираемся.
- Сессии БД — **только** async; eager-loading через `selectinload`. Не правь политику `commit`/`rollback` точечно без сверки [`backend/app/core/database.py`](backend/app/core/database.py).
- Telegram bot — отдельный entry в [`backend/app/bot/`](backend/app/bot/), запускается своим скриптом ([`scripts/run_bot.ps1`](scripts/run_bot.ps1)), не частью FastAPI.
- Outbox-воркер — отдельный процесс `python -m app.workers.outbox` ([`backend/app/workers/outbox.py`](backend/app/workers/outbox.py)): доставляет email и Telegram из очереди `outbox_messages`.

### Конфиг и env

- Backend читает в порядке приоритета: переменные ОС → `<repo>/.env` → `backend/.env` (опционально, переопределяет корневой). Логика: [`backend/app/core/config.py`](backend/app/core/config.py).
- Frontend (Next.js) читает env-файлы только из `frontend/` (обычно `frontend/.env.local`) — корневой `.env` он **не** читает. Для CI/Railway переменные `NEXT_PUBLIC_*` нужны на этапе **build**, не runtime.
- В production и staging [`Settings.validate_production_safety`](backend/app/core/config.py) фейлит старт при небезопасных дефолтах (DEBUG, дефолтный `JWT_SECRET_KEY`, localhost в URL и т.п.) — не глушить, чинить ENV.
- Шаблоны: [`.env.example`](.env.example), [`frontend/.env.example`](frontend/.env.example). Реальные `.env` / `.env.local` не коммитим и не цитируем в чате.

### Lifespan и стартовый seed (техдолг)

В [`backend/app/main.py`](backend/app/main.py) только при `ENVIRONMENT=development` создаются/обновляются тестовые пользователи `admin@nails-course.ru` и `student@test.ru`. Пароли берутся из `SEED_ADMIN_PASSWORD` и `SEED_STUDENT_PASSWORD`; если они пусты, генерируются при старте и пишутся в лог. Не расширяй это поведение на staging и production — гард завязан строго на `ENVIRONMENT`.

### Middleware (порядок важен)

Порядок от внешнего к внутреннему (запрос проходит слева направо): `CORSMiddleware` → `CorrelationIdMiddleware` → `CsrfProtectionMiddleware` (double-submit, активен только когда есть auth-cookie) → `SecurityHeadersMiddleware` → `TrustedHostMiddleware` (production и staging, если задан `TRUSTED_HOSTS`) → `UploadSizeLimitMiddleware` → `SlowAPIMiddleware`. В [`main.py`](backend/app/main.py) вызовы `add_middleware` идут в обратном порядке: последний добавленный оказывается внешним. CORS origins берутся из `CORS_ORIGINS` (через запятую) или fallback к `FRONTEND_URL`.

### Frontend

- App Router в [`frontend/src/app/`](frontend/src/app/): публичные / protected / admin маршруты.
- API-клиент — единый [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts) (`apiFetch` + доменные функции). Не дублируй базовый URL и не делай `fetch` напрямую к API.
- Server Components по умолчанию; `'use client'` — только где нужна интерактивность.
- UI-примитивы — [`frontend/src/components/ui/`](frontend/src/components/ui/) (shadcn-паттерн, конфиг [`frontend/components.json`](frontend/components.json)).

### Интеграции

- **Kinescope DRM:** webhook авторизации в [`backend/app/api/integrations/kinescope.py`](backend/app/api/integrations/kinescope.py); JWT-подпись в [`backend/app/services/kinescope_jwt_service.py`](backend/app/services/kinescope_jwt_service.py); приватный ключ — `KINESCOPE_JWT_PRIVATE_KEY_PATH` или `KINESCOPE_JWT_PRIVATE_KEY_PEM`. Setup публичного JWK: [`scripts/kinescope/setup_drm.py`](scripts/kinescope/). См. [`Docs/integrations/KINESCOPE_AUTH_BACKEND.md`](Docs/integrations/KINESCOPE_AUTH_BACKEND.md).
- **Prodamus:** оплата гостевая (`POST /api/payments/guest-link`) и пользовательская (`POST /api/payments/link`); webhook на `{BACKEND_URL}/api/payments/webhook` создаёт пользователя при необходимости и в той же транзакции ставит письмо в outbox: ссылку активации `/auth/activate` (аккаунт без подтверждённого email) или уведомление о доступе. Письмо отправляет outbox-воркер через [`email_service.py`](backend/app/services/email_service.py). Demo-режим включается автоматически если `ENVIRONMENT != production` или задан `PRODAMUS_DEMO_MODE`; в production флаг запрещён, в staging обязателен.

### Деплой

**Автодеплоя из `master` нет:** merge и зелёный CI ничего не выкатывают, деплой на Railway запускается вручную — порядок в [`Docs/04_Setup_Ops/DEPLOY_GUIDE.md`](Docs/04_Setup_Ops/DEPLOY_GUIDE.md).

Настройки сервисов хранятся в самом Railway, файлов конфигурации в репозитории нет: backend (`alembic upgrade head && uvicorn`), worker (`python -m app.workers.outbox`), frontend (`npm ci && npm run build`, `npm start`). Значения — [`LAUNCH_OPERATIONS.md`](Docs/04_Setup_Ops/LAUNCH_OPERATIONS.md), подробности — [`Docs/04_Setup_Ops/DEPLOY_GUIDE.md`](Docs/04_Setup_Ops/DEPLOY_GUIDE.md).

## GitHub / репозиторий и аккаунт

- Репозиторий: **`TwinsMinsk/lucy-nails`** (публичный), владелец — аккаунт **TwinsMinsk**, default-ветка **`master`**.
- В этом проекте работаем **только** под аккаунтом **TwinsMinsk**: `git push`, открытие PR и merge — под ним. Другие аккаунты не использовать.
- `origin` настроен на SSH, но на рабочей машине нет ключа для GitHub и записи в `known_hosts`, поэтому `git fetch` и `git push` через `origin` падают. Работает HTTPS с учётными данными `gh`: `git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push https://github.com/TwinsMinsk/lucy-nails.git <ветка>`.
- `gh` CLI (и GitHub MCP) должны быть залогинены в **TwinsMinsk**: `gh auth login --hostname github.com --web`. Проверка прав: `gh api repos/TwinsMinsk/lucy-nails --jq .permissions` → должно быть `"push": true`. Аккаунт `Progery222` имеет только `READ` и не может открывать PR / мерджить.
- CI триггерится только на push в `master`/`main` и на PR в них; обычный push feature-ветки CI не запускает — валидируем через PR в `master`.

## Локальные артефакты

`promo-clips/`, `video-lessons/`, `photo-work/`, `scripts/promo/output/` — тяжёлые файлы, исключены из Git. Код промо-пайплайна и метаданные — в [`scripts/promo/`](scripts/promo/) (метаданные программы — [`scripts/promo/program.json`](scripts/promo/program.json)).

## Конвенции (кратко)

- Комментарии и имена в коде — **на английском** (русские docstrings/UI-строки оставляй как есть в затрагиваемых файлах).
- Conventional Commits (`feat:`, `fix:`, `refactor:`, `chore:` …).
- `git add .` не использовать — добавлять конкретные файлы.
- `--force`, `--no-verify` — только при явном запросе пользователя.
