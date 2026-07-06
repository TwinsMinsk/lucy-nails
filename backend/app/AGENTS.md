<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-07-06 | Updated: 2026-07-06 -->

# app

## Purpose
Точка входа FastAPI-приложения (`main.py`) и его слои: роутеры (`api/`), бизнес-логика/интеграции (`services/`), ORM-модели и Pydantic-схемы (`models/`, `schemas/`), инфраструктура (`core/`), а также отдельный Telegram-бот (`bot/`), который не является частью FastAPI-приложения.

## Key Files
| File | Description |
|------|-------------|
| `main.py` | Создаёт `FastAPI(...)`, регистрирует middleware в фиксированном порядке, monтирует `/uploads` (если задан `UPLOAD_STORAGE_DIR`), подключает все роутеры через `include_router`, содержит `lifespan` с dev-сидом тестовых пользователей. |
| `__init__.py` | Пустой файл-маркер пакета. |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `api/` | Роутеры FastAPI (thin controllers) — auth, courses, modules, lessons, purchases, payments, admin, upload, landing, admin_landing, integrations/kinescope (see `api/AGENTS.md`) |
| `bot/` | Отдельный Telegram-бот, не подключён к FastAPI (see `bot/AGENTS.md`) |
| `core/` | Конфиг, БД-engine, security, rate limit, auth-зависимости (see `core/AGENTS.md`) |
| `models/` | SQLAlchemy ORM-модели (see `models/AGENTS.md`) |
| `schemas/` | Pydantic-схемы запросов/ответов (see `schemas/AGENTS.md`) |
| `services/` | Бизнес-логика и внешние интеграции (Prodamus, Kinescope, email) (see `services/AGENTS.md`) |

## For AI Agents

### Working In This Directory
- Порядок middleware в `main.py` важен и зафиксирован: `SlowAPIMiddleware` → `TrustedHostMiddleware` (только prod, если задан `TRUSTED_HOSTS`) → `SecurityHeadersMiddleware` → `CsrfProtectionMiddleware` → `CORSMiddleware`. Не переставляй без явной причины — CSRF-проверка полагается на то, что она отработает раньше CORS, но после того, как заголовки/куки уже доступны.
- `CsrfProtectionMiddleware` — double-submit: проверяет unsafe-методы (не GET/HEAD/OPTIONS/TRACE) только если в куках есть `access_token`/`refresh_token`, и пропускает `EXEMPT_PATHS` (`/api/auth/login|register|refresh|logout`), т.к. эти эндпоинты сами устанавливают/ротируют пару cookie+CSRF.
- В `lifespan` dev-сид срабатывает **строго** при `settings.ENVIRONMENT.lower() == "development"` (не просто `!= "production"` — staging/иные значения ENVIRONMENT сид не получают). Создаёт/обновляет пароль для `admin@nails-course.ru` и `student@test.ru`; пароли берутся из `SEED_ADMIN_PASSWORD`/`SEED_STUDENT_PASSWORD` или генерируются случайно с warning-логом. Это известный техдолг — не переносить в production-конфигурацию.
- `docs_url`/`redoc_url`/`openapi_url` отключаются (`None`) в production через `_is_production()`.
- Новый роутер добавляется в блок `# Подключение роутеров` в конце файла (импорт после `app.add_middleware(...)`, помечен `# noqa: E402` — это намеренно, см. `pyproject.toml`).

### Testing Requirements
Изменения в `main.py` (middleware, lifespan, конфиг приложения) проверяются `backend/tests/test_production_hardening.py` — запускай прицельно:
```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend/tests/test_production_hardening.py -v
```
Полный прогон и линт — см. `../AGENTS.md`.

### Common Patterns
- Middleware — классы-наследники `starlette.middleware.base.BaseHTTPMiddleware` с методом `async def dispatch(self, request, call_next)`.
- Роутеры подключаются с явным `prefix` и `tags`: `app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])`.
- Статика раздаётся только если задан `settings.UPLOAD_STORAGE_DIR` (Railway Volume в проде, локальная папка в dev) — `app.mount("/uploads", StaticFiles(...))`.

## Dependencies

### Internal
`core/config.py` (`settings`), `core/database.py` (`async_session_maker`), `core/rate_limit.py` (`limiter`), `core/security.py` (`get_password_hash`), `models/user.py` (`User`), все роутеры из `api/`.

### External
`fastapi`, `slowapi`, `starlette` (middleware base classes), `sqlalchemy` (`select`).

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
