<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-07-06 | Updated: 2026-07-06 -->

# core

## Purpose

Инфраструктурный слой приложения: конфигурация из env, async-подключение к БД, хеширование паролей и JWT, FastAPI-зависимости для авторизации, rate-limiting. Не содержит бизнес-логики доменов (курсы/уроки/оплаты) — только сквозные механизмы, на которые опирается весь `app/api/` и `app/services/`.

## Key Files

| File | Description |
|------|-------------|
| `config.py` | `Settings` (pydantic-settings): DB/Redis/JWT/Kinescope/Prodamus/SMTP/Telegram/CORS/uploads. Приоритет источников: переменные ОС → корневой `.env` → `backend/.env` (перекрывает корневой). `validate_production_safety` (`model_validator`) фейлит старт при `ENVIRONMENT=production`, если `DEBUG=True`, дефолтный `JWT_SECRET_KEY`, пустые `KINESCOPE_API_KEY`/`PRODAMUS_*`, `localhost`/`127.0.0.1` в `FRONTEND_URL`/`BACKEND_URL`, пустой `TRUSTED_HOSTS` |
| `database.py` | `Base` (DeclarativeBase), async `engine` (`create_async_engine`, pool из `DB_POOL_SIZE`/`DB_MAX_OVERFLOW`/`DB_POOL_RECYCLE_SECONDS`), `async_session_maker`, dependency `get_db()` — commit при успехе, rollback при исключении, close в `finally` |
| `dependencies.py` | `get_current_user` (JWT из `Authorization` или cookie `access_token`, отвергает `type=refresh`), `require_admin` (403 если `role != "admin"`), `require_course_access` (403 если нет активной `Purchase` с `payment_status="success"` и `expires_at > now`) |
| `security.py` | `verify_password`/`get_password_hash` (bcrypt через `passlib`), `create_access_token`/`create_refresh_token` (JWT HS256, `type` claim `access`/`refresh`) |
| `rate_limit.py` | `limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])` — импортируется в роутерах для `@limiter.limit(...)` и регистрируется как `app.state.limiter` + `SlowAPIMiddleware` в `main.py` |

## For AI Agents

### Working In This Directory

- `config.py`: новую переменную добавлять как поле `Settings` с дефолтом (dev-safe) и, если она обязательна в production, — добавить проверку в `validate_production_safety`. Не глушить фейл валидации — чинить ENV на Railway/локально.
- `database.py`: политику `commit`/`rollback`/`close` в `get_db()` не менять точечно ради одного эндпоинта — она общая для всех запросов через `Depends(get_db)`. Отдельная явная сессия (`async_session_maker()` напрямую) допустима только там, где `get_db()` неприменим (webhook вне обычного request-response цикла, см. `app/api/payments.py`).
- `dependencies.py`: новые guard-зависимости (по образцу `require_admin`/`require_course_access`) добавлять сюда, не дублировать проверку роли/доступа инлайн в роутерах.
- `security.py`: алгоритм JWT (`JWT_ALGORITHM`, сейчас HS256) и bcrypt-контекст не менять без миграции существующих токенов/хешей.
- `rate_limit.py` — единственный `Limiter` на приложение; не создавать второй экземпляр в другом модуле.

### Testing Requirements

```powershell
ruff check backend/app/core backend/tests
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -v --tb=short
```

`backend/tests/test_production_hardening.py` — тесты именно на `validate_production_safety`; `test_auth.py` — на `security.py`/`dependencies.py` через `/api/auth/*`.

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

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
