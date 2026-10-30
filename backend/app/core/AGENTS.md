# core

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose

Инфраструктурный слой приложения: конфигурация из env, async-подключение к БД, хеширование паролей и JWT, FastAPI-зависимости для авторизации и RBAC, rate-limiting, лимит размера upload, версия юридических согласий. Не содержит бизнес-логики доменов (курсы/уроки/оплаты) — только сквозные механизмы, на которые опирается весь `app/api/` и `app/services/`.

## Key Files

| File | Description |
|------|-------------|
| `config.py` | `Settings` (pydantic-settings): DB/Redis/мониторинг/JWT/MFA/cookies/Kinescope + DRM/Prodamus/SMTP + Resend/Telegram/lifecycle/outbox/checkout/CORS/trusted hosts/proxy/uploads/dev seed. Приоритет источников: переменные ОС → корневой `.env` → `backend/.env` (перекрывает корневой). `settings` создаётся при импорте, поэтому `validate_production_safety` (см. ниже) действует на web, воркер, бот и скрипты, импортирующие `app.*` |
| `database.py` | `Base` (DeclarativeBase), async `engine` (`create_async_engine`, `pool_pre_ping`, pool из `DB_POOL_SIZE`/`DB_MAX_OVERFLOW`/`DB_POOL_RECYCLE_SECONDS`), `async_session_maker`, dependency `get_db()` — commit при успехе, rollback при исключении, close в `finally` |
| `dependencies.py` | `get_current_user` (JWT из `Authorization` или cookie `access_token`; только `type=access`, `ver` равен `User.token_version`, при наличии `sid` — активная `AuthSession`; пишет `auth_token_version`/`auth_session_id` в `request.state`), `require_permission(name)` и `user_has_permission` (RBAC; пользователь с `role="admin"` без назначенных ролей проходит как legacy), `require_course_access` (403 без активного entitlement через `AccessService`, admin проходит всегда), `require_admin` (legacy, роутерами не используется) |
| `security.py` | `verify_password`/`get_password_hash` (bcrypt через `passlib`), `decode_auth_token` (PyJWT, лимит `MAX_AUTH_TOKEN_LENGTH`, обязательные claim `exp`/`sub`/`ver`/`type`), `create_access_token`/`create_refresh_token` (JWT HS256, `type` claim `access`/`refresh`), пары `create_*`/`verify_*` для `reset`, `activation` и `mfa_setup` токенов |
| `rate_limit.py` | `client_ip` (только peer-адрес, нормализованный Uvicorn; `X-Forwarded-For` напрямую не читает) и `limiter = Limiter(key_func=client_ip, default_limits=["200/minute"], storage_uri=...)` — хранилище `REDIS_URL`, без него `memory://`. Импортируется в роутерах для `@limiter.limit(...)` и регистрируется как `app.state.limiter` + `SlowAPIMiddleware` в `main.py` |
| `upload_limits.py` | `UploadSizeLimitMiddleware` (чистый ASGI) для `POST /api/admin/upload`: 413 сверх `MAX_MULTIPART_BYTES`, тело буферизуется во временный файл и передаётся приложению порциями |
| `uploads.py` | `upload_dir()` (`UPLOAD_STORAGE_DIR`, иначе `frontend/public/uploads`), `public_upload_url()` (`UPLOAD_PUBLIC_BASE_URL`, иначе `/uploads/...`) |
| `legal.py` | `CONSENT_VERSION` (зеркало в `frontend/src/lib/legal.ts`), `CONSENT_REQUIRED_DETAIL`, `require_consent()` — отдельные согласия с офертой и на обработку ПДн (152-ФЗ) |

### Production Checks

`validate_production_safety` (`model_validator`) фейлит старт в production/staging, если:

- **Секреты:** `DEBUG=True`; `JWT_SECRET_KEY` дефолтный или короче 32 символов; `MFA_ENCRYPTION_KEY` короче 32 символов или совпадает с `JWT_SECRET_KEY`.
- **Kinescope:** пуст `KINESCOPE_API_KEY`; нет DRM-ключа (`KINESCOPE_JWT_PRIVATE_KEY_PEM` или `KINESCOPE_JWT_PRIVATE_KEY_PATH`) и `KINESCOPE_JWK_KID`; нет `KINESCOPE_DRM_BASIC_USER`/`KINESCOPE_DRM_BASIC_PASS`.
- **Prodamus:** пусты `PRODAMUS_URL`/`PRODAMUS_SECRET_KEY`/`PRODAMUS_SHOP_ID`; `PRODAMUS_DEMO_MODE` включён в production или выключен в staging.
- **URL:** `FRONTEND_URL`/`BACKEND_URL` не HTTPS или содержат `localhost`/`127.0.0.1`; в staging они и `COOKIE_DOMAIN` не на изолированном staging-поддомене.
- **Email:** при `SMTP_REQUIRED_FOR_PAYMENT_EMAIL=True` нет транспорта (`RESEND_API_KEY` или `SMTP_USER` + `SMTP_PASSWORD`); `SMTP_START_TLS=False` в production или в staging вне приватного `*.railway.internal`.
- **Инфраструктура:** пусты `TRUSTED_HOSTS`, `COOKIE_DOMAIN`, `REDIS_URL`; `FORWARDED_ALLOW_IPS` пуст или равен `*`.
- **Telegram:** пусты `TELEGRAM_BOT_TOKEN`/`TELEGRAM_BOT_USERNAME` или `TELEGRAM_OWNER_CHAT_ID`.

`MONITORING_TOKEN` на старте не проверяется: без него `/health/operations` отвечает 503.

## For AI Agents

### Working In This Directory

- `config.py`: новую переменную добавлять как поле `Settings` с дефолтом (dev-safe) и, если она обязательна в production, — добавить проверку в `validate_production_safety` и тест в `test_production_hardening.py`. Не глушить фейл валидации — чинить ENV на Railway/локально.
- `database.py`: политику `commit`/`rollback`/`close` в `get_db()` не менять точечно ради одного эндпоинта — она общая для всех запросов через `Depends(get_db)`. Отдельная явная сессия (`async_session_maker()` напрямую) допустима только там, где `get_db()` неприменим: webhook и checkout в `app/api/payments.py`, `app/services/payment_event_service.py`, `/health*` и `lifespan` в `main.py`, воркер, бот. `backend/tests/conftest.py` подменяет фабрику сессий для payments, payment_event_service и бота — новый прямой вызов в коде под тестами нужно добавить туда же.
- `dependencies.py`: новые guard-зависимости добавлять сюда, не дублировать проверку роли/доступа инлайн в роутерах. Для admin-эндпоинтов использовать `require_permission("...")`; новые права сеются миграцией (см. `../../alembic/AGENTS.md`). Точечные проверки внутри обработчика — `user_has_permission` (пример: `pii.read`).
- `security.py`: алгоритм JWT (`JWT_ALGORITHM`, сейчас HS256) и bcrypt-контекст не менять без миграции существующих токенов/хешей. Токены без `ver` не проходят `decode_auth_token`; рост `User.token_version` инвалидирует все выданные ранее токены пользователя.
- `rate_limit.py` — единственный `Limiter` на приложение; не создавать второй экземпляр в другом модуле. Не брать IP из `X-Forwarded-For` вручную: доверие к прокси задаётся в Uvicorn (`--proxy-headers --forwarded-allow-ips`, `FORWARDED_ALLOW_IPS`).
- `legal.py`: при изменении текста оферты или согласия поднимать `CONSENT_VERSION` синхронно с `frontend/src/lib/legal.ts`.
- `upload_limits.py`: `MAX_MULTIPART_BYTES` должен оставаться больше `MAX_UPLOAD_BYTES` из `app/api/upload.py`.

### Testing Requirements

```powershell
ruff check backend/app/core backend/tests
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -v --tb=short
```

`backend/tests/test_production_hardening.py` — тесты на `validate_production_safety` и `client_ip`; `test_auth.py`, `test_auth_password.py` — на `security.py`/`dependencies.py` через `/api/auth/*`; `test_mfa_sessions.py` — на сессии и MFA; `test_rbac_audit.py` — на `require_permission`; `test_image_upload.py` — на `upload_limits.py`.

### Common Patterns

- Сессия запроса — `Depends(get_db)` (`database.py`); guard — `Depends(require_permission("content.manage"))`, образец в `app/api/admin.py`.
- Внутренние импорты моделей и сервисов делаются лениво (`from app.models.user import User` внутри функции) в `dependencies.py` — так исторически избегается циклический импорт `core` ↔ `models` (модели импортируют `Base` из `core.database`).

## Dependencies

### Internal
- `database.py`, `security.py`, `rate_limit.py`, `uploads.py` зависят от `config.py`
- `dependencies.py` зависит от `database.py`, `security.py`, лениво — от `app.models.user`, `app.models.rbac`, `app.services.session_service`, `app.services.access_service`

### External
- `pydantic-settings`, `sqlalchemy[asyncio]` + `asyncpg`, `PyJWT`, `passlib[bcrypt]`, `slowapi` + `redis`, `starlette`

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
