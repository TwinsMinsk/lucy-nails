# 01 — Архитектура

Дата: 2026-06-26 · Ветка: `refactor/cleanup` · Метод: read-only (Grep/Read + Graphify; Serena недоступна).

## Карта слоёв (фактическая)

```
backend/app/
  main.py            FastAPI app, lifespan-seed, middleware-стек, include_router
  api/               thin controllers (роутеры)
    auth, courses, modules, lessons, purchases, payments,
    admin (797), admin_landing, landing, upload,
    integrations/kinescope
  services/          бизнес-логика и интеграции (10 модулей)
  models/            SQLAlchemy ORM (user, course, module, lesson, purchase, progress, certificate, gallery)
  schemas/           Pydantic v2
  core/              config, database, security, dependencies, rate_limit
  bot/               Telegram (отдельный entry, не часть FastAPI)
```

Слоистость `api → services → models/schemas` в целом соблюдена. Основное нарушение — «протёкшая» в роутеры бизнес-логика в `admin.py` (см. [02-backend.md](02-backend.md), BE-03).

## Инварианты (заявлены в CLAUDE.md / ARCHITECTURE.md — проверены против кода)

| Инвариант | Статус | Доказательство |
|---|---|---|
| Авторизация только через FastAPI `Depends` (не RLS) | ✅ подтверждён | `core/dependencies.py:21,72,89` (`get_current_user`, `require_admin`, `require_course_access`) |
| Async-only сессии БД | ✅ | `core/database.py:16-30` (`create_async_engine`, `async_sessionmaker`) |
| Eager-loading через `selectinload` | ✅ | `admin.py:232-234`, `api/integrations/kinescope.py` |
| Единая политика commit/rollback в `get_db` | ✅ (с оговоркой) | `core/database.py:40-48` — авто-commit при успехе, rollback при исключении (см. BE-06: тихий commit как осознанный компромисс) |
| Каждое изменение модели → миграция Alembic | ⚠️ не проверено динамически | 7 миграций в `alembic/versions/`; `alembic upgrade head` локально не запускался (нет БД) — см. [05-tests-ci.md](05-tests-ci.md) TEST-02 |
| Middleware-стек: SlowAPI → TrustedHost(prod) → SecurityHeaders → CSRF → CORS | ✅ | `main.py:122-138` (Starlette применяет LIFO: CORS внешний — корректно) |
| Production-safety fail-fast | ✅ | `core/config.py:129-160` |

## Граф зависимостей (Graphify)

`graphify-out/` уже построен: **5695 узлов, 7264 рёбер, 363 community, 92% extracted**.

God-узлы (наиболее связанные) — подтверждают известные точки концентрации:

| Узел | Рёбер | Трактовка |
|---|---|---|
| `User` (модель) | 115 | Центральная сущность домена — ожидаемо; не дефект |
| `cn()` | 97 | Утилита из 6 строк, 22 импорта — идиоматично для shadcn; **не трогать** (см. FE-02) |
| `Module` / `Course` / `Lesson` / `Purchase` | 69/61/59/57 | Ядро контент-модели — ожидаемо |
| `apiFetch()` | 45 | Единый фронт-клиент — концентрация оправдана, но файл `api.ts` крупный (FE-02) |
| `LessonService` | 21 | — |
| `Button()` | 21 | UI-примитив — ожидаемо |

`Prodamus - Help Documentations` (184 рёбер) — это узел **документации** (skill-доки), не код.

## Import-циклы между сервисами — ОПРОВЕРГНУТО

Предварительная гипотеза о self-referential циклах между сервисами **не подтвердилась**. Прямой межсервисный импорт ровно один и ацикличный:

- `services/kinescope_service.py:12` → `services/kinescope_jwt_service` (одностороннее, обратного импорта нет).

Локальные импорты внутри функций (`dependencies.py:39,105` импортируют модели внутри тела) — это намеренный приём против циклов `models ↔ dependencies`, не дефект.

## Вывод

Архитектура зрелая и связная: слои разделены, инварианты безопасности соблюдаются, граф показывает ожидаемые доменные god-узлы без патологических циклов. Основные структурные долги — размер `admin.py` и `api.ts` (декомпозиция, чистый рефакторинг) и пара гигиенических/security-пунктов (committed creds), вынесенных в [BACKLOG.md](BACKLOG.md).
