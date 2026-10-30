# app

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose
Точка входа FastAPI-приложения (`main.py`) и его слои: роутеры (`api/`), бизнес-логика/интеграции (`services/`), ORM-модели и Pydantic-схемы (`models/`, `schemas/`), инфраструктура (`core/`), а также отдельные процессы, которые не являются частью FastAPI-приложения: Telegram-бот (`bot/`) и outbox-воркер (`workers/`).

## Key Files
| File | Description |
|------|-------------|
| `main.py` | Создаёт `FastAPI(...)`, регистрирует middleware, объявляет `/`, `/health` (проверка БД) и `/health/operations`, монтирует `/uploads` (если задан `UPLOAD_STORAGE_DIR`), подключает все роутеры через `include_router`, содержит `lifespan` с dev-сидом тестовых пользователей. |
| `__init__.py` | Файл-маркер пакета (только комментарий). |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `api/` | Роутеры FastAPI (thin controllers) — auth, courses, modules, lessons, purchases, payments, analytics, telegram, certificates, landing, upload, admin и `admin_*` (content, crm, certificates, refunds, reports, system, landing), integrations/kinescope (see `api/AGENTS.md`) |
| `assets/` | Статика рендера дипломов, без собственного AGENTS.md — см. ниже |
| `bot/` | Отдельный Telegram-бот, не подключён к FastAPI (see `bot/AGENTS.md`) |
| `core/` | Конфиг, БД-engine, security, rate limit, auth-зависимости, лимит upload, согласия (see `core/AGENTS.md`) |
| `models/` | SQLAlchemy ORM-модели (see `models/AGENTS.md`) |
| `schemas/` | Pydantic-схемы запросов/ответов (see `schemas/AGENTS.md`) |
| `services/` | Бизнес-логика и внешние интеграции (Prodamus, Kinescope, email, доступы, outbox, MFA/сессии, аудит, сертификаты) (see `services/AGENTS.md`) |
| `workers/` | Фоновые процессы, без собственного AGENTS.md — см. ниже |

### `workers/`
`outbox.py` — отдельный процесс доставки уведомлений: `python -m app.workers.outbox` (`worker` в `../Procfile`, `../../ops/railway/worker.toml`). Цикл `run_forever` → `run_iteration`: раз в `LIFECYCLE_SCAN_SECONDS` вызывает `LifecycleService.schedule`, затем `process_outbox_batch`, в отдельных транзакциях, чтобы сбой одного шага не блокировал другой; после итерации — `record_worker_heartbeat` (Redis, читается в `/health/operations`). Если ничего не обработано, спит `OUTBOX_POLL_SECONDS`. Логгер `httpx` держится на WARNING: на INFO он пишет полный URL запроса, а в нём токен бота.

### `assets/`
`certificates/template.png` — статичный фон диплома (перегенерируется `backend/scripts/generate_certificate_template.py`), `certificates/fonts/` — шрифты с лицензиями OFL. Читаются из `services/certificate_layout.py` и `services/certificate_renderer.py`.

## For AI Agents

### Working In This Directory
- Порядок `app.add_middleware(...)` в `main.py` важен: последний добавленный выполняется первым. Запрос проходит так: `CORSMiddleware` → `CorrelationIdMiddleware` → `CsrfProtectionMiddleware` → `SecurityHeadersMiddleware` → `TrustedHostMiddleware` (только в production/staging, если задан `TRUSTED_HOSTS`) → `UploadSizeLimitMiddleware` → `SlowAPIMiddleware` → роутер. Следствия: отказы внутренних слоёв (403 CSRF, 413, 429) получают CORS-заголовки и `X-Correlation-ID`; 403 от CSRF не получает security-заголовки; тело upload буферизуется после проверки CSRF, но до rate limit и авторизации. Не переставляй без явной причины.
- `CsrfProtectionMiddleware` — double-submit: проверяет unsafe-методы (не GET/HEAD/OPTIONS/TRACE) только если в куках есть `access_token`/`refresh_token`, и пропускает `EXEMPT_PATHS` (`/api/auth/login|register|refresh|logout|forgot-password|reset-password|activate|mfa/setup|mfa/confirm`), т.к. эти эндпоинты сами устанавливают/ротируют пару cookie+CSRF или не опираются на auth-cookie.
- `CorrelationIdMiddleware` принимает `X-Correlation-ID` от клиента только при совпадении с `_CORRELATION_ID_PATTERN` (иначе генерирует UUID), кладёт его в `request.state.correlation_id` и возвращает в ответе; это же значение попадает в `AuditLog.correlation_id`.
- В `lifespan` dev-сид срабатывает **только** в development-окружении (staging и production его не получают). Создаёт/обновляет пароль для `admin@nails-course.ru` и `student@test.ru`; пароли берутся из `SEED_ADMIN_PASSWORD`/`SEED_STUDENT_PASSWORD` или генерируются случайно с warning-логом. Это известный техдолг — не переносить в production-конфигурацию.
- `docs_url`/`redoc_url`/`openapi_url` отключаются (`None`) в production/staging; там же `SecurityHeadersMiddleware` добавляет HSTS и CSP.
- `/health/operations` закрыт заголовком `X-Monitoring-Token`: 503, если `MONITORING_TOKEN` короче 32 символов, 401 при неверном токене; отчёт — `operations_snapshot`, 503 при статусе не `ok`.
- Новый роутер добавляется в блок `# Подключение роутеров` в конце файла (импорт после `app.add_middleware(...)`, помечен `# noqa: E402` — это намеренно, см. `pyproject.toml`).
- Письма и Telegram-уведомления не отправляй из обработчика запроса: ставь сообщение в outbox (`services/outbox_service.py`), доставит `workers/outbox.py`.

### Testing Requirements
Изменения в `main.py` (middleware, lifespan, конфиг приложения) проверяются `backend/tests/test_production_hardening.py` — запускай прицельно:
```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend/tests/test_production_hardening.py -v
```
Смежные проверки: CSRF — `test_auth.py`, `test_auth_password.py`, `test_purchases.py`; лимит upload — `test_image_upload.py`; `/health/operations` — `test_operations_health.py`; воркер — `test_outbox.py`. Полный прогон и линт — см. `../AGENTS.md`.

### Common Patterns
- Middleware в `main.py` — классы-наследники `starlette.middleware.base.BaseHTTPMiddleware` с методом `async def dispatch(self, request, call_next)`. Исключение — `UploadSizeLimitMiddleware` (`core/upload_limits.py`): чистый ASGI, потому что ограничивает и буферизует тело запроса.
- Роутеры подключаются с явным `prefix` и `tags`: `app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])`. Все `admin_*`, а также `upload` монтируются под `/api/admin`.
- Статика раздаётся только если задан `settings.UPLOAD_STORAGE_DIR` (Railway Volume в проде, локальная папка в dev) — `app.mount("/uploads", StaticFiles(...))`.

## Dependencies

### Internal
`core/config.py` (`settings`), `core/database.py` (`async_session_maker`), `core/rate_limit.py` (`limiter`), `core/security.py` (`get_password_hash`), `core/upload_limits.py` (`UploadSizeLimitMiddleware`), `models/user.py` (`User`), `services/operations_health_service.py` (`operations_snapshot`), все роутеры из `api/`.

### External
`fastapi`, `slowapi`, `starlette` (middleware base classes), `sqlalchemy` (`select`, `text`).

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
