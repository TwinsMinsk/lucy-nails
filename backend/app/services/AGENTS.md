# services

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose

Бизнес-логика и внешние интеграции, вызываемые из `app/api/*`. Большинство сервисов — классы со `@staticmethod` без состояния (принимают `AsyncSession` первым аргументом); исключение — `KinescopeService`/`KinescopeJwtService`, которые инстанциируются как модуль-level singleton с конфигурацией из `settings`.

## Key Files

| File | Description |
|------|-------------|
| `admin_bootstrap.py` | `ensure_admin_user(db, email, password)` — создаёт/промоутит пользователя в `role="admin"` с явным паролем (мин. 12 символов), для one-off production bootstrap (не HTTP-эндпоинт) |
| `auth_service.py` | `AuthService`: `register_user` (проверка уникальности email), `authenticate_user` (bcrypt-верификация), `create_tokens(user_id, token_version)` (пара access/refresh JWT с claims `sub` + `ver`), `change_password` (проверяет текущий пароль, `False` при неверном), `set_password` (после reset-токена); оба инкрементируют `User.token_version`, commit делает роутер. `get_user_by_id` |
| `course_service.py` | `CourseService`: `get_courses`/`get_course_by_id` (с фильтром `only_published`, опц. `selectinload` модулей+уроков), `get_course_stats` (агрегаты count/sum по опубликованным модулям/урокам) |
| `email_service.py` | `EmailService`: `send_credentials` (логин/пароль после оплаты) и `send_password_reset` (ссылка сброса). Транспорт в `_send`: Resend HTTP API (`httpx`, `RESEND_ENDPOINT`) при заданном `RESEND_API_KEY` — основной путь в production (Railway блокирует исходящий SMTP), иначе SMTP через `aiosmtplib` (STARTTLS). Таймаут `EMAIL_TIMEOUT_SECONDS` на оба транспорта; From — `EMAIL_FROM` или `"<SMTP_FROM_NAME> <SMTP_USER>"`. `is_configured()` — есть Resend-ключ или `SMTP_USER`+`SMTP_PASSWORD`; без транспорта — skip с warning, ошибки самого транспорта пробрасываются вызывающему |
| `kinescope_jwt_service.py` | `KinescopeJwtService` (singleton `kinescope_jwt_service`): RS256-подпись/верификация короткоживущего JWT (`drmauthtoken`) для DRM authorization backend. Приватный ключ — `KINESCOPE_JWT_PRIVATE_KEY_PATH` (файл) или `KINESCOPE_JWT_PRIVATE_KEY_PEM` (инлайн, `\n`-экранированный, удобно для Railway); `is_configured` требует ключ + `KINESCOPE_JWK_KID`; публичная часть выводится из приватного ключа в памяти для верификации |
| `kinescope_service.py` | `KinescopeService` (singleton `kinescope_service`): `get_video_info`, `get_embed_url` (вкладывает `watermark` + опц. `drmauthtoken` от `kinescope_jwt_service`), `upload_video_file` (uploader v2). Без `KINESCOPE_API_KEY` работает в mock-режиме (dev/test); в production при отсутствии ключа кидает `KinescopeNotConfiguredError`. `get_embed_url` в production fail-closed: без настроенного DRM-подписанта тоже `KinescopeNotConfiguredError`, а не embed без `drmauthtoken` (вне production — degrade без токена) |
| `lesson_service.py` | `LessonService`: `get_lesson_by_id` (`selectinload` module→course), `check_access` (доступ = preview ИЛИ admin ИЛИ активная `Purchase`), `get_lesson_with_access`, `update_progress` (upsert `Progress`, клэмп `watched_seconds` по `duration_seconds`), `get_progress` |
| `module_service.py` | `ModuleService`: `get_course_modules`/`get_module_by_id` (фильтр по `is_published`, опц. `selectinload` уроков/курса), `get_module_stats` |
| `prodamus_service.py` | `ProdamusService`: `generate_payment_link` (GET-ссылка на `payform.ru` с плоскими `products[0][...]` в query, `urlNotification`, `demo_mode` вне production или по `PRODAMUS_DEMO_MODE`; подпись считается по **вложенной** структуре `{"products": [{...}]}`, как её восстанавливает Prodamus, — подпись по плоскому dict Prodamus отвергает), `verify_signature` (HMAC-SHA256 через `_make_signature` — рекурсивная сортировка ключей → JSON без пробелов → экранирование `/` → HMAC; demo-подпись с суффиксом `demo` к секрету принимается **только** при `PRODAMUS_DEMO_MODE` или вне production) |
| `purchase_service.py` | `PurchaseService`: `get_active_purchase` (`payment_status="success"` и `expires_at > now`), `get_user_purchases`, `get_purchase_by_id`, `get_my_courses_with_progress` (собирает список курсов ЛК с прогрессом, ближайшим незавершённым уроком, `support_chat_url` для тарифа `support`) |

## For AI Agents

### Working In This Directory

- Сервисы не поднимают `HTTPException` — это забота роутера (`app/api/*`); сервис возвращает `None`/`False`/бросает доменное исключение (`ValueError`, `KinescopeNotConfiguredError`, `KinescopeJwtNotConfiguredError`).
- `payment_status == "success" AND expires_at > now` — единственный критерий активного доступа к курсу; при добавлении новой проверки доступа переиспользовать `PurchaseService.get_active_purchase` / `LessonService.check_access`, не дублировать SQL инлайн.
- Prodamus: `verify_signature` — единственное место, где решается «оплата подтверждена»; редиректы `urlSuccess`/`urlReturn` не гарантируют оплату — не добавлять по ним логику активации доступа.
- Kinescope DRM: приватный ключ (`KINESCOPE_JWT_PRIVATE_KEY_PATH`/`_PEM`) не должен покидать сервер; не логировать и не возвращать в API его содержимое. Публичный JWK заливается в Kinescope отдельно скриптом [`scripts/kinescope/setup_drm.py`](../../../scripts/kinescope/).
- `email_service.py`: не делать отправку письма блокирующей для основного потока webhook — в `app/api/payments.py` (и в `/api/auth/forgot-password`) ошибка отправки логируется (`logger.exception`), но не откатывает уже сохранённую покупку. Новые письма — публичный метод поверх `EmailService._send`, не прямой вызов транспорта.
- Пароль пользователя менять только через `AuthService.change_password`/`set_password` (или вручную инкрементировать `token_version`), иначе старые JWT и reset-ссылки останутся валидными.
- Prodamus: при изменении состава параметров ссылки поддерживать `sign_data` в `generate_payment_link` синхронно с query — регрессия зафиксирована тестами `backend/tests/test_prodamus_signature.py`.
- Новый сервис — статик-класс с `@staticmethod` методами, первым параметром `db: AsyncSession`, по образцу `CourseService`/`ModuleService`/`LessonService`. Singleton-паттерн (`kinescope_service`, `kinescope_jwt_service`) — только для сервисов с конфигурацией/состоянием, инициализируемым один раз из `settings`.

### Testing Requirements

```powershell
ruff check backend/app/services backend/tests
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -v --tb=short
```

Точечно: `test_kinescope.py`/`test_kinescope_drm.py` (embed URL, mock-режим, DRM JWT), `test_admin_bootstrap.py` (`ensure_admin_user`), `test_purchases.py` (`PurchaseService`, доступ по покупке, письмо с паролем из webhook), `test_auth.py`/`test_auth_password.py` (`AuthService`, смена/сброс пароля), `test_prodamus_signature.py` (подпись ссылки и demo-подпись), `test_production_hardening.py` (обязательность email-транспорта).

### Common Patterns

```python
class LessonService:
    @staticmethod
    async def check_access(db: AsyncSession, user: User, lesson: Lesson) -> bool:
        if lesson.is_preview:
            return True
        if user.role == "admin":
            return True
        query = select(Purchase).where(
            and_(
                Purchase.user_id == user.id,
                Purchase.course_id == lesson.module.course_id,
                Purchase.payment_status == "success",
                Purchase.expires_at > datetime.utcnow(),
            )
        )
        result = await db.execute(query)
        return result.scalars().first() is not None
```

- Демо/mock-режим переключается по наличию секрета в `settings` (`KINESCOPE_API_KEY`, `PRODAMUS_DEMO_MODE`/`ENVIRONMENT != production`), а не по отдельному флагу — сохранять этот подход для новых внешних интеграций.

## Dependencies

### Internal
- `app/core/config.py` (`settings`), `app/core/security.py` (`get_password_hash`), `app/models/*`, `app/schemas/*` (только `auth_service.py`, `lesson_service.py`)

### External
- `httpx` (Kinescope API/uploader, Resend email API), `aiosmtplib` (SMTP-fallback), `python-jose` + `cryptography` (RS256 DRM JWT), `sqlalchemy[asyncio]`

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
