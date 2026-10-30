# tests

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose
Интеграционные тесты FastAPI-приложения: pytest + `pytest-asyncio` + `httpx.AsyncClient` поверх ASGI-транспорта (без реального сетевого сервера). Покрывают auth (включая смену/сброс пароля и инвалидацию токенов), courses, purchases и webhook Prodamus, подпись Prodamus, admin bootstrap, Kinescope (обычный сервис, `/play` и DRM-webhook) и production-хардening конфигурации.

## Key Files
| File | Description |
|------|-------------|
| `conftest.py` | Общие фикстуры: тестовая БД, событийный цикл, HTTP-клиент, сброс rate limiter. См. раздел ниже. |
| `test_auth.py` | Регистрация/логин, cookie-based токены (`access_token`/`refresh_token`), `GET /api/auth/me` по cookie. |
| `test_auth_password.py` | `/api/auth/forgot-password` (одинаковый ответ), `/reset-password` (flow, невалидный/просроченный токен, одноразовость), `/change-password` (flow, неверный текущий пароль, обязательный CSRF), reset-токен не работает как access, смена пароля гасит старый access-токен. |
| `test_admin_bootstrap.py` | `ensure_admin_user` из `app/services/admin_bootstrap.py` — создание первого админа и промоушен существующего пользователя до `admin`. |
| `test_courses.py` | Эндпоинты курсов. |
| `test_purchases.py` | `parse_checkout_order_id`, создание/список покупок, ссылки оплаты (`/guest-link`, `/link` требует auth) и webhook Prodamus: идемпотентность и fallback `payment_id`, отказ без/с неверной подписью, при неуспешном/пустом статусе, чужой валюте, несовпадении суммы; создание пользователя и письмо с паролем (сбой письма не ломает идемпотентность); гонка двух оплат с одним новым email и повтор при `IntegrityError`; admin `POST /api/admin/revoke-access`. |
| `test_kinescope.py` | Интеграция с Kinescope (не DRM): `GET /api/lessons/{id}/play` — 401 без авторизации, 200 с активной покупкой, 403 без покупки и с истёкшей; mock-режим `KinescopeService`. |
| `test_kinescope_drm.py` | RS256 JWT-подпись/верификация (`KinescopeJwtService`) и webhook `/api/integrations/kinescope/drm/authorize` (happy-path + отказы), включая генерацию тестового RSA-ключа через `cryptography`. |
| `test_prodamus_signature.py` | Подпись ссылки оплаты считается по вложенной структуре `products` (и не по старой плоской форме); demo-подпись отвергается в production и принимается при `PRODAMUS_DEMO_MODE`. |
| `test_production_hardening.py` | Проверяет регистрацию `SlowAPIMiddleware` в `app.main.app`, `GET /health` (200 при доступной БД) и `validate_production_safety`: хелпер `_valid_prod(**overrides)` собирает валидный production-`Settings(_env_file=None, ...)`, а тесты ломают по одному полю и ждут `pydantic.ValidationError` — небезопасные дефолты, отсутствие email-транспорта (Resend/SMTP), `PRODAMUS_DEMO_MODE=True`, нет DRM-ключа или DRM basic auth. |

## For AI Agents

### Working In This Directory
- Нужны **две** локальные Postgres-БД: та, что указана в `DATABASE_URL` (обычно `nails_course`), и `test_nails_course`. `conftest.py` выводит имя тестовой БД автозаменой `/nails_course` → `/test_nails_course` в строке подключения; если в `DATABASE_URL` нет `/nails_course`, используется fallback `f"{DB_URL_STR}_test"`.
- Схема тестовой БД создаётся через `Base.metadata.create_all` (фикстура `prepare_database`, `scope="session"`, `autouse=True`) — **не** через `alembic upgrade head`. Это значит, что локальный прогон тестов не проверяет консистентность файлов миграций с моделями; эта проверка — только в CI (`alembic upgrade head` на отдельной БД, см. `../alembic/AGENTS.md`).
- Фикстура `db` (`scope="function"`) перед каждым тестом делает `TRUNCATE ... RESTART IDENTITY CASCADE` для `progress, purchases, certificates, lessons, modules, courses, users` — порядок важен из-за FK. При добавлении новой модели с FK на эти таблицы (или зависимой от неё) обнови список в `TRUNCATE`. `gallery_items` в список не входит — тесты галереи (если появятся) должны чистить её сами или добавить в `TRUNCATE`.
- Autouse-фикстура `_reset_rate_limiter` вызывает `limiter.reset()` перед каждым тестом: `limiter` живёт весь сеанс, и без сброса накопленные запросы дают 429 (например, на `/api/auth/login`) в поздних тестах.
- Фикстура `client` подменяет зависимость `get_db` на тестовую сессию через `app.dependency_overrides[get_db]`. Но `app/api/payments.py` (Prodamus webhook и гостевой/пользовательский checkout) открывает сессии напрямую через `async_session_maker()`, минуя `Depends(get_db)` — поэтому `conftest.py` дополнительно патчит `app.api.payments.async_session_maker = TestingSessionLocal` на уровне модуля. При появлении других мест с прямым `async_session_maker()` вместо `Depends(get_db)` их тоже придётся патчить аналогично, иначе тесты будут писать в реальную dev-БД.
- Переменные `PRODAMUS_URL`/`PRODAMUS_SECRET_KEY` выставляются в `conftest.py` через `os.environ.setdefault(...)` **до** импорта `app.main` — иначе `Settings` не соберётся валидным для тестового окружения.

### Testing Requirements
```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -v --tb=short
```
Один файл/тест:
```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend/tests/test_courses.py::test_name -v
```
Линт (обязателен в CI наравне с тестами):
```powershell
ruff check backend/app backend/tests
```

### Common Patterns
- Асинхронные тесты помечаются `@pytest.mark.asyncio`, используют инжект фикстур по имени (`client: AsyncClient`, `db: AsyncSession`) — без ручного создания сессий/клиентов внутри теста.
- HTTP-тесты идут через `client.post/get(...)` к реальным путям API (`/api/auth/register` и т.п.), а не вызывают функции роутеров напрямую.
- Уникальные email в тестах (`test_register_unique@example.com`) — защитная привычка авторов; сама фикстура `db` и так truncate-ит таблицы перед каждым тестом.
- Тесты `Settings` создают экземпляр с `_env_file=None`, чтобы локальные `.env` не влияли на результат.

## Dependencies

### Internal
`app.main.app`, `app.core.database` (`Base`, `get_db`), `app.core.config.settings`, `app.models` (импортируются целиком через `from app.models import *`, чтобы зарегистрироваться в `Base.metadata`), `app.services.admin_bootstrap`, `app.services.kinescope_jwt_service`.

### External
`pytest`, `pytest-asyncio`, `httpx` (`AsyncClient`, `ASGITransport`), `sqlalchemy[asyncio]` (`create_async_engine`, `NullPool`), `cryptography` (генерация RSA-ключей в DRM-тестах).

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
