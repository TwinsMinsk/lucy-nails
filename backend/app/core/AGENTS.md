# core

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose

Инфраструктурный слой приложения: конфигурация из env, async-подключение к БД, хеширование паролей и JWT, FastAPI-зависимости для авторизации, rate-limiting. Не содержит бизнес-логики доменов (курсы/уроки/оплаты) — только сквозные механизмы, на которые опирается весь `app/api/` и `app/services/`.

## Key Files

| File | Description |
|------|-------------|
| `config.py` | `Settings` (pydantic-settings): DB/Redis/JWT (+ `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`, `COOKIE_DOMAIN`)/Kinescope + DRM/Prodamus/email (SMTP, `RESEND_API_KEY`, `EMAIL_FROM`, `SMTP_REQUIRED_FOR_PAYMENT_EMAIL`)/Telegram/dev-seed (`SEED_ADMIN_PASSWORD`, `SEED_STUDENT_PASSWORD`)/CORS/uploads. Приоритет источников: переменные ОС → корневой `.env` → `backend/.env` (перекрывает корневой). `validate_production_safety` (`model_validator`) фейлит старт при `ENVIRONMENT=production`, если `DEBUG=True`; `JWT_SECRET_KEY` дефолтный или короче 32 символов; пустой `KINESCOPE_API_KEY`; нет DRM-ключа (`KINESCOPE_JWT_PRIVATE_KEY_PEM`/`_PATH` + `KINESCOPE_JWK_KID`) или `KINESCOPE_DRM_BASIC_USER`/`_PASS`; пустые `PRODAMUS_URL`/`PRODAMUS_SECRET_KEY`/`PRODAMUS_SHOP_ID`; `PRODAMUS_DEMO_MODE=True`; нет email-транспорта (Resend или SMTP) при `SMTP_REQUIRED_FOR_PAYMENT_EMAIL=True` (по умолчанию); `localhost`/`127.0.0.1` в `FRONTEND_URL`/`BACKEND_URL`; пустой `TRUSTED_HOSTS` |
| `database.py` | `Base` (DeclarativeBase), async `engine` (`create_async_engine`, pool из `DB_POOL_SIZE`/`DB_MAX_OVERFLOW`/`DB_POOL_RECYCLE_SECONDS`), `async_session_maker`, dependency `get_db()` — commit при успехе, rollback при исключении, close в `finally` |
| `dependencies.py` | `get_current_user` (JWT из `Authorization` или cookie `access_token`; принимает **только** `type == "access"` — refresh/reset-токены отвергаются; требует `payload["ver"] == user.token_version`, иначе 401), `require_admin` (403 если `role != "admin"`), `require_course_access` (403 если нет активной `Purchase` с `payment_status="success"` и `expires_at > now`) |
| `security.py` | `verify_password`/`get_password_hash` (bcrypt через `passlib`), `create_access_token`/`create_refresh_token` (JWT HS256, `type` claim `access`/`refresh`; claim `ver` приходит в `data` из `AuthService.create_tokens`), `create_password_reset_token(user_id, token_version)` (`type="reset"`, TTL `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`) и `verify_password_reset_token` (payload или `None`) |
| `rate_limit.py` | `limiter = Limiter(key_func=client_ip, default_limits=["200/minute"])` — импортируется в роутерах для `@limiter.limit(...)` и регистрируется как `app.state.limiter` + `SlowAPIMiddleware` в `main.py`. `client_ip(request)` берёт IP клиента из `CF-Connecting-IP`, затем левый адрес `X-Forwarded-For`, затем `get_remote_address` — иначе за общим прокси Railway/Cloudflare все клиенты попадают в одно ведро |

## For AI Agents

### Working In This Directory

- `config.py`: новую переменную добавлять как поле `Settings` с дефолтом (dev-safe) и, если она обязательна в production, — добавить проверку в `validate_production_safety`. Не глушить фейл валидации — чинить ENV на Railway/локально.
- `database.py`: политику `commit`/`rollback`/`close` в `get_db()` не менять точечно ради одного эндпоинта — она общая для всех запросов через `Depends(get_db)`. Отдельная явная сессия (`async_session_maker()` напрямую) допустима только там, где `get_db()` неприменим (webhook вне обычного request-response цикла, см. `app/api/payments.py`).
- `dependencies.py`: новые guard-зависимости (по образцу `require_admin`/`require_course_access`) добавлять сюда, не дублировать проверку роли/доступа инлайн в роутерах.
- `security.py`: алгоритм JWT (`JWT_ALGORITHM`, сейчас HS256) и bcrypt-контекст не менять без миграции существующих токенов/хешей. Все типы токенов подписаны одним секретом, поэтому каждый новый тип обязан иметь свой `type` claim, а каждый потребитель — проверять его (как `get_current_user`, `/api/auth/refresh`, `verify_password_reset_token`). Токены несут `ver` = `User.token_version`; токен без `ver` или с устаревшим `ver` отвергается.
- `rate_limit.py` — единственный `Limiter` на приложение; не создавать второй экземпляр в другом модуле. Не возвращать `key_func` на голый `get_remote_address`. Лимитер хранит счётчики в памяти процесса — в тестах их сбрасывает autouse-фикстура `_reset_rate_limiter` (`limiter.reset()`) в `backend/tests/conftest.py`.

### Testing Requirements

```powershell
ruff check backend/app/core backend/tests
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -v --tb=short
```

`backend/tests/test_production_hardening.py` — тесты именно на `validate_production_safety`; `test_auth.py` и `test_auth_password.py` — на `security.py`/`dependencies.py` через `/api/auth/*` (изоляция типов токенов, инвалидация по `token_version`, одноразовость reset-токена).

### Common Patterns

```python
async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

```python
async def require_admin(current_user = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
```

Внутренние импорты моделей делаются лениво (`from app.models.user import User` внутри функции) в `dependencies.py` — так исторически избегается циклический импорт `core` ↔ `models` (модели импортируют `Base` из `core.database`).

## Dependencies

### Internal
- `database.py` зависит от `config.py` (`settings.DATABASE_URL`, pool-настройки)
- `dependencies.py` зависит от `config.py`, `database.py`, лениво — от `app.models.user`, `app.models.purchase`
- `security.py` зависит от `config.py`

### External
- `pydantic-settings`, `sqlalchemy[asyncio]` + `asyncpg`, `python-jose`, `passlib[bcrypt]`, `slowapi`

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
