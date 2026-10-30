# tests

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose
Интеграционные тесты FastAPI-приложения: pytest + `pytest-asyncio` + `httpx.AsyncClient` поверх ASGI-транспорта (без реального сетевого сервера), плюс unit-тесты рендера, подписи и ops-скриптов. Покрывают auth/MFA, RBAC и аудит, CRM и отчёты, checkout и webhook, возвраты, доступ, сертификаты, Kinescope, outbox и уведомления, аналитику и production-хардening конфигурации.

## Key Files
| File | Description |
|------|-------------|
| `conftest.py` | Общие фикстуры: `event_loop`, `prepare_database`, `_reset_rate_limiter`, `db`, `client`, а также `TestingSessionLocal`. См. раздел ниже. |
| **Аутентификация** | |
| `test_auth.py` | Регистрация/логин, cookie-based токены (`access_token`/`refresh_token`), `GET /api/auth/me` по cookie, согласия при регистрации. |
| `test_auth_email_case.py` | Email без учёта регистра, в том числе legacy-записи со смешанным регистром. |
| `test_auth_password.py` | Смена, сброс и забытый пароль: одноразовость токенов, инвалидация старых сессий, CSRF. |
| `test_auth_concurrency.py` | Хеширование паролей не блокирует event loop. |
| `test_email_ownership.py` | Владение ящиком: `/resend-verification`, активация после гостевой оплаты, отказ в доступе без подтверждённого email, некорректные JWT и DRM-входы, гонки при смене пароля. |
| `test_mfa_sessions.py` | MFA owner/admin, backup-коды, список и отзыв сессий, ротация refresh и повторное использование. |
| **Админка и RBAC** | |
| `test_rbac_audit.py` | Разграничение прав по ролям, запись аудита, защита последнего owner. |
| `test_admin_bootstrap.py` | `ensure_admin_user` из `app/services/admin_bootstrap.py` — создание первого админа и промоушен существующего пользователя до `admin`. |
| `test_admin_courses.py` | Удаление курса: 409 при наличии оплат. |
| `test_admin_crm.py` | Дашборд, ученики, заказы, сверка, повтор уведомлений, маскирование PII, создание ученика и ссылка для входа. |
| `test_admin_reports.py` | Отчёты: источник денег, воронка, источники и CSV, ручные выдачи не считаются выручкой. |
| `test_admin_certificates.py` | Реестр сертификатов, отзыв и повторная отправка. |
| `test_content_health.py` | `POST /api/admin/content/video-health`: все классы ошибок видео. |
| **Каталог и обучение** | |
| `test_courses.py` | Эндпоинты курсов и уроков, скрытие контента без доступа, прогресс только по опубликованным модулям, клэмп `watched_seconds`. |
| `test_landing_contract.py` | Контракт `GET /api/landing` и срок жизни подписанной ссылки `/play`. |
| `test_learning_events.py` | Server-события обучения идемпотентны и не подделываются браузером. |
| `test_image_upload.py` | `POST /api/admin/upload`: подмена формата, лимиты размера и пикселей, перекодирование. |
| **Покупки и деньги** | |
| `test_purchases.py` | Самый большой файл: checkout, `parse_checkout_order_id`, webhook Prodamus (подпись, суммы, повторы, тарифы, legacy-ссылки), согласия, kill switch, alert владельцу, отзыв доступа. |
| `test_prodamus_signature.py` | Подпись платёжной ссылки и webhook, demo-подпись, `nest_form_fields`, PHP-приведение значений. |
| `test_refunds.py` | Workflow возврата, частичный и полный возврат, гонки, снятие из группы поддержки. |
| `test_commerce_safety.py` | Инварианты денег и доступа: полный возврат отзывает всё, гонки возврата и восстановления, вторая оплата как incident, повтор отклонённого события. |
| `test_expired_access.py` | `GET /api/purchases/my/expired`: только естественно истёкший и не продлённый доступ. |
| **Kinescope** | |
| `test_kinescope.py` | `/api/lessons/{id}/play` и `KinescopeService` (mock-режим, разбор ответа API). |
| `test_kinescope_drm.py` | RS256 JWT-подпись/верификация (`KinescopeJwtService`) и webhook `/api/integrations/kinescope/drm/authorize` (happy-path + отказы), включая генерацию тестового RSA-ключа через `cryptography`. |
| **Сертификаты** | |
| `test_certificates.py` | Claim, статусы, публичная проверка и выгрузка файла, валидация имени, гонка при commit. |
| `test_certificate_number.py` | Формат номера и повторы при коллизии (без БД). |
| `test_certificate_renderer.py` | Рендер PNG/PDF (без БД). |
| **Уведомления и аналитика** | |
| `test_outbox.py` | Повторы и доставка outbox, Telegram-группа и устаревшие команды, claim пакета, воркер `app/workers/outbox.py`, `format_rub`. |
| `test_telegram_notifications.py` | Привязка Telegram одноразовой ссылкой, `LifecycleService.schedule`, сводка владельцу по `dead_letter`. |
| `test_email_service.py` | SMTP-транспорт и STARTTLS. |
| `test_email_attachments.py` | MIME и вложения, Resend-payload, экранирование HTML сертификата. |
| `test_analytics_events.py` | Публичный сборщик: дедупликация, запрет PII и финансовых событий, атрибуция в заказе. |
| **Эксплуатация** | |
| `test_operations_health.py` | `/health/operations`: секрет мониторинга, отсутствие воркера, отставание очереди. |
| `test_production_hardening.py` | Проверяет регистрацию `SlowAPIMiddleware` в `app.main.app` и что `Settings(ENVIRONMENT="production", ...)` с небезопасными дефолтами (DEBUG=True, дефолтный `JWT_SECRET_KEY`, отсутствующие email/Kinescope/Prodamus/Redis/MFA-настройки) валится с `pydantic.ValidationError`; правила для staging и `FORWARDED_ALLOW_IPS`. |
| `test_backup_bundle.py` | `scripts/ops/backup_postgres.py` и `scripts/ops/restore_postgres.py` в корне репозитория: упаковка, защита от выхода за каталог, отказ восстанавливать в непустую БД. |

## For AI Agents

### Working In This Directory
- Нужны **две** локальные Postgres-БД: та, что указана в `DATABASE_URL` (обычно `nails_course`), и `test_nails_course`. `conftest.py` выводит имя тестовой БД автозаменой `/nails_course` → `/test_nails_course` в строке подключения; если в `DATABASE_URL` нет `/nails_course`, используется fallback `f"{DB_URL_STR}_test"`.
- Схема тестовой БД создаётся через `Base.metadata.create_all` (фикстура `prepare_database`, `scope="session"`, `autouse=True`) — **не** через `alembic upgrade head`. Это значит, что локальный прогон тестов не проверяет консистентность файлов миграций с моделями, а также триггеры и данные миграций (нет засеянных ролей и append-only триггера `audit_logs`); эта проверка — только в CI (`alembic upgrade head`, `downgrade -1`, `alembic check`, см. `../alembic/AGENTS.md`).
- Фикстура `db` (`scope="function"`) перед каждым тестом делает `TRUNCATE ... RESTART IDENTITY CASCADE` для всех таблиц, кроме `gallery_items`. При добавлении новой модели обнови список в `TRUNCATE` в `conftest.py`.
- Autouse-фикстура `_reset_rate_limiter` сбрасывает счётчики slowapi перед каждым тестом.
- Фикстура `client` подменяет зависимость `get_db` на тестовую сессию через `app.dependency_overrides[get_db]`; подмена отдаёт тот же `db` и не коммитит после `yield`, поэтому незакоммиченное ручкой другая сессия не увидит. Код, открывающий сессии напрямую через `async_session_maker()`, минует `Depends(get_db)` — поэтому `conftest.py` дополнительно патчит на уровне модуля `app.api.payments`, `app.services.payment_event_service` и `app.bot.services.auth`. При появлении других мест с прямым `async_session_maker()` вместо `Depends(get_db)` их тоже придётся патчить аналогично, иначе тесты будут писать в реальную dev-БД. `test_outbox.py` подменяет сессию воркера локально; `app/main.py` (lifespan, health-ручки) не патчится.
- Переменные `PRODAMUS_URL`/`PRODAMUS_SECRET_KEY` выставляются в `conftest.py` через `os.environ.setdefault(...)` **до** импорта `app.main` — иначе `Settings` не соберётся валидным для тестового окружения.
- Роли и права в тестовой БД отсутствуют: `role="admin"` без назначений проходит `require_permission` через legacy-fallback и не требует MFA; для проверки конкретных прав файл сам создаёт `Role`, `Permission`, `UserRoleAssignment` (см. `_staff_user` в `test_rbac_audit.py`).
- Активный доступ требует подтверждённого email: не-admin, которому нужен курс, должен иметь `email_verified_at` (при регистрации через `/api/auth/register` он пуст).

### Testing Requirements
```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -v --tb=short
```
Запускать из корня репозитория: `test_backup_bundle.py` импортирует `scripts.ops.*` оттуда.

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
- Асинхронные тесты помечаются `@pytest.mark.asyncio`, используют инжект фикстур по имени (`client: AsyncClient`, `db: AsyncSession`) — без ручного создания сессий/клиентов внутри теста. Исключение — тесты гонок: отдельные сессии через `from conftest import TestingSessionLocal` и подмена `get_db` локальным `isolated_db` (`test_commerce_safety.py`, `test_email_ownership.py`).
- HTTP-тесты идут через `client.post/get(...)` к реальным путям API (`/api/auth/register` и т.п.), а не вызывают функции роутеров напрямую.
- CSRF действует только при auth-cookie: тесты либо работают по Bearer и делают `client.cookies.clear()` после логина, либо передают заголовок `x-csrf-token` из cookie `csrf_token`.
- Настройки подменяются через `monkeypatch.setattr(settings, ...)`. Singleton-сервисы читают конфигурацию при импорте, поэтому Kinescope DRM подменяется целиком: фикстура `configured_drm` в `test_kinescope_drm.py`.
- Локальные фикстуры файлов: `certificate_storage` (`test_certificates.py`), `image_storage` (`test_image_upload.py`) — временный каталог загрузок.
- Внешние вызовы не выполняются: доставка outbox проверяется через `process_outbox_batch(db, deliver=...)` или патч `_telegram_request`, письма — через моки `EmailService`.
- Уникальные email в тестах (`test_register_unique@example.com`) — защитная привычка авторов; сама фикстура `db` и так truncate-ит таблицы перед каждым тестом.

## Dependencies

### Internal
`app.main.app`, `app.core.database` (`Base`, `get_db`), `app.core.config.settings`, `app.models` (импортируются целиком через `from app.models import *`, чтобы зарегистрироваться в `Base.metadata`), `app.api.*`, `app.services.*`, `app.workers.outbox`, `app.bot.services.auth`, `scripts.ops.backup_postgres`, `scripts.ops.restore_postgres`.

### External
`pytest`, `pytest-asyncio`, `httpx` (`AsyncClient`, `ASGITransport`), `sqlalchemy[asyncio]` (`create_async_engine`, `NullPool`), `cryptography` (генерация RSA-ключей в DRM-тестах), `Pillow` (тесты рендера и загрузки).

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
