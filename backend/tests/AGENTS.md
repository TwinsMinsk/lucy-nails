<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-07-06 | Updated: 2026-07-06 -->

# tests

## Purpose
Интеграционные тесты FastAPI-приложения: pytest + `pytest-asyncio` + `httpx.AsyncClient` поверх ASGI-транспорта (без реального сетевого сервера). Покрывают auth, courses, purchases, admin bootstrap, Kinescope (обычный сервис и DRM-webhook) и production-хардening конфигурации.

## Key Files
| File | Description |
|------|-------------|
| `conftest.py` | Общие фикстуры: тестовая БД, событийный цикл, HTTP-клиент. См. раздел ниже. |
| `test_auth.py` | Регистрация/логин, cookie-based токены (`access_token`/`refresh_token`), `GET /api/auth/me` по cookie. |
| `test_admin_bootstrap.py` | `ensure_admin_user` из `app/services/admin_bootstrap.py` — создание первого админа и промоушен существующего пользователя до `admin`. |
| `test_courses.py` | Эндпоинты курсов. |
| `test_purchases.py` | Эндпоинты покупок. |
| `test_kinescope.py` | Интеграция с Kinescope (обычный сервис/эндпоинты, не DRM). |
| `test_kinescope_drm.py` | RS256 JWT-подпись/верификация (`KinescopeJwtService`) и webhook `/api/integrations/kinescope/drm/authorize` (happy-path + отказы), включая генерацию тестового RSA-ключа через `cryptography`. |
| `test_production_hardening.py` | Проверяет регистрацию `SlowAPIMiddleware` в `app.main.app` и что `Settings(ENVIRONMENT="production", ...)` с небезопасными дефолтами (DEBUG=True, дефолтный `JWT_SECRET_KEY`, отсутствующие SMTP/Kinescope/Prodamus креды) валится с `pydantic.ValidationError`. |

## For AI Agents

### Working In This Directory
- Нужны **две** локальные Postgres-БД: та, что указана в `DATABASE_URL` (обычно `nails_course`), и `test_nails_course`. `conftest.py` выводит имя тестовой БД автозаменой `/nails_course` → `/test_nails_course` в строке подключения; если в `DATABASE_URL` нет `/nails_course`, используется fallback `f"{DB_URL_STR}_test"`.
- Схема тестовой БД создаётся через `Base.metadata.create_all` (фикстура `prepare_database`, `scope="session"`, `autouse=True`) — **не** через `alembic upgrade head`. Это значит, что локальный прогон тестов не проверяет консистентность файлов миграций с моделями; эта проверка — только в CI (`alembic upgrade head` на отдельной БД, см. `../alembic/AGENTS.md`).
- Фикстура `db` (`scope="function"`) перед каждым тестом делает `TRUNCATE ... RESTART IDENTITY CASCADE` для `progress, purchases, certificates, lessons, modules, courses, users` — порядок важен из-за FK. При добавлении новой модели с FK на эти таблицы (или зависимой от неё) обнови список в `TRUNCATE`.
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

## Dependencies

### Internal
`app.main.app`, `app.core.database` (`Base`, `get_db`), `app.core.config.settings`, `app.models` (импортируются целиком через `from app.models import *`, чтобы зарегистрироваться в `Base.metadata`), `app.services.admin_bootstrap`, `app.services.kinescope_jwt_service`.

### External
`pytest`, `pytest-asyncio`, `httpx` (`AsyncClient`, `ASGITransport`), `sqlalchemy[asyncio]` (`create_async_engine`, `NullPool`), `cryptography` (генерация RSA-ключей в DRM-тестах).

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
