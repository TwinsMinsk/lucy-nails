# api

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose

Thin FastAPI-контроллеры (роутеры): по одному файлу на домен. Бизнес-логика вынесена в `app/services/`; исключения — webhook и checkout в `payments.py`, CRUD и отчёты в `admin*.py`, где транзакции и SQL живут прямо в роутере. Каждый файл создаёт свой `APIRouter()` и подключается в [`backend/app/main.py`](../main.py) через `include_router(..., prefix=..., tags=[...])`. Авторизация — только через `Depends` (`get_current_user`, `require_permission("<name>")` из `app/core/dependencies.py`); на RLS в БД не полагаемся.

## Key Files

Лимиты указаны там, где есть явный `@limiter.limit`; остальное покрывает глобальный `200/minute`. В скобках — prefix из `main.py`.

| File | Description |
|------|-------------|
| `__init__.py` | Маркер пакета. |
| `auth.py` (`/api/auth`) | `POST /register` (15/min, обязательны согласия), `/login` (30/min), `/refresh` (45/min), `/change-password`, `/reset-password`, `/activate` (10/min), `/forgot-password`, `/resend-verification` (5/min, ответ не раскрывает наличие email), `/mfa/setup`, `/mfa/confirm` (10/min, по `setup_token`), `/logout`, `GET /me`, `GET /sessions`, `DELETE /sessions/{session_id}`. Ставит/снимает cookies: `access_token` и `refresh_token` — httpOnly, `csrf_token` — читаемый JS; `secure` в production/staging. Вход с ролью owner/admin требует MFA: `403 mfa_setup_required` + `setup_token`, `401 mfa_code_required`/`mfa_code_invalid`. Refresh ротирует токен сессии, повтор старого токена отзывает сессию. |
| `courses.py` (`/api/courses`) | Публичный каталог: список/детали опубликованных курсов, `GET /{course_id}/modules` (outline уроков без основного `kinescope_video_id`), `/my-progress` (auth; нужен активный доступ или admin). |
| `modules.py` (`/api/modules`) | Публичные детали модуля и список его уроков (только опубликованные модуль+курс). |
| `landing.py` (`/api/landing`) | `GET /api/landing` — единый payload для SSR главной страницы: hero первого опубликованного курса + снимок курса (цена, срок доступа, число уроков, длительность) + landing-копия его опубликованных модулей + опубликованная галерея. |
| `lessons.py` (`/api/lessons`) | Всё под `get_current_user`. Детали урока (`content`/`video_url` скрыты без доступа, `kinescope_video_id` не отдаётся никогда), `POST /{lesson_id}/progress` (403 без доступа), `GET /{lesson_id}/play` (90/min; защищённый embed-URL, 503 при `KinescopeNotConfiguredError`). Пишет server-события `lesson_activity`, `lesson_started`. |
| `purchases.py` (`/api/purchases`) | `POST /create` (30/min; ссылка оплаты, `order_id`, `status_token`), `GET /my` (мои курсы с прогрессом), `GET /my/expired` (истёкший, но не отозванный доступ — для продления). Переиспользует хелперы из `payments.py`. |
| `payments.py` (`/api/payments`) | `POST /webhook` (120/min), `POST /guest-link` (20/min, обязательны согласия), `POST /link` (60/min, auth), `GET /orders/{order_id}/status?token=`. Продаётся только `SELLABLE_TARIFFS` (`self`); `support` — 400 на checkout, но исторические заказы webhook принимает. Kill switch — `_ensure_checkout_enabled` (503). Webhook: проверка `Sign` по `ProdamusService.verify_signature`, JSON или multipart (`nest_form_fields`), ссылка на заказ из `order_num` (`order\|<uuid>`, legacy `course\|<uuid>\|<tariff>\|<nonce>`), идемпотентность по `PaymentEvent.event_hash` и `Purchase.payment_id`, сверка email заказа, суммы (±2 коп.) и валюты. Успех — одной транзакцией в `_record_purchase_once`: `Purchase`, `Entitlement`, outbox (активация, если email не подтверждён, иначе `access_granted`), alert владельцу, событие `purchase_confirmed`. Повторная оплата заказа — `financial_incident` без второго доступа. Отказ — `_record_rejected_webhook` и 422. Непригодная атрибуция заменяется на `None` (`OptionalAttribution`, `_none_if_invalid`) и не блокирует оплату. |
| `certificates.py` (`/api`) | `POST /courses/{course_id}/certificate` (10/min, auth, идемпотентный claim; 403/404/409/410/503), `GET /courses/{course_id}/certificate` (статус), публичные `GET /certificates/verify/{certificate_number}` и `GET /certificates/{certificate_number}/file?format=pdf\|png` (30/min; 410 у отозванного). |
| `analytics.py` (`/api/analytics`) | Публичный `POST /events` (60/min, 202): только `landing_view`/`cta_click` с `source="web"`, allow-list свойств, 422 на PII в `properties` (UTM с контактными данными не отклоняется, метка отбрасывается), окно времени −7 дней…+5 минут, дедупликация по `event_id`. Финансовые и учебные события пишет только сервер. |
| `telegram.py` (`/api/telegram`) | `GET /status`, `POST /link` (5/min; одноразовый токен на 15 минут, хранится хеш; 403 без подтверждённого email кроме admin, 503 без бота), `DELETE /link`. |
| `upload.py` (`/api/admin`) | `POST /upload` — изображения jpg/jpeg/png/webp/gif, `content.manage`. Содержимое должно совпадать с расширением, файл перекодируется Pillow; лимиты 10 МБ и 20 Мп (плюс `UploadSizeLimitMiddleware` на тело запроса). В production/staging требует `UPLOAD_STORAGE_DIR` + `UPLOAD_PUBLIC_BASE_URL`, иначе 503. |
| `admin.py` (`/api/admin`) | CRUD курсов/модулей/уроков (`content.manage`; удаление курса с оплатами, заказами, доступами или сертификатами — 409), `/users` (`users.read`), `/purchases` (`commerce.read`, PII маскируется без `pii.read`), `/analytics` (`analytics.read`). Управление доступом (`access.manage`): `/grant-access` (ручной `Entitlement` без `Purchase`), `/revoke-entitlement`, `/entitlements/{entitlement_id}/extend`, `/entitlements/{entitlement_id}/{action}` (`suspend`/`restore`). `/revoke-access` (`refunds.manage`) — отзыв по покупке. Около 1100 строк. |
| `admin_crm.py` (`/api/admin`) | Операционная CRM: `/dashboard` (`analytics.read`), `/system/status` (`audit.read`), `/access-courses` (`access.manage`), `GET /students`, `/students/{user_id}`, `/entitlements` (`users.read`), `POST /students` (`access.manage`; создаёт или переиспользует аккаунт, выдаёт доступ, шлёт письмо), `/students/{user_id}/send-login-link`, `/notes`, `/tags` (`users.manage`), `/orders`, `/payment-events`, `/reconciliation` (`commerce.read`; PII в заказах маскируется без `pii.read`), `/notifications`, `/notifications/{message_id}/retry` (`notifications.manage`). |
| `admin_reports.py` (`/api/admin`) | `/reports/overview`, `timeseries`, `funnel`, `sources` (также `format=csv`, защита от формул — `_csv_safe`), `tariffs`, `cohorts`, `progress`, `refunds`, `delivery` — всё `analytics.read`. По умолчанию 30 дней, максимум 730. Деньги считаются только через `paid_financial_filter()`. |
| `admin_refunds.py` (`/api/admin`) | `GET`/`POST /refunds`, `PUT /refunds/{refund_id}` (`refunds.manage`): тонкая обёртка над `RefundService` с аудитом и alert владельцу при переходе в `processed`. |
| `admin_certificates.py` (`/api/admin`) | Реестр `GET /certificates`, `POST /certificates/{certificate_id}/reissue` (повторная отправка ссылки, не чаще раза в час; у отозванного — 409), `/revoke` (`certificates.manage`, аудит). |
| `admin_content.py` (`/api/admin`) | `POST /content/video-health` (5/min, `content.manage`) — проверка готовности видео через `ContentHealthService`. |
| `admin_landing.py` (`/api/admin`) | Admin-редактор лендинга (`content.manage`): hero курса (`GET/PUT .../landing-hero`), landing-копия модулей (`GET/PUT .../landing-modules`, `.../landing`), CRUD и reorder галереи работ (`/gallery`, `/gallery/reorder`, `/gallery/{item_id}`). |
| `admin_system.py` (`/api/admin`) | `PUT /system/checkout` (`system.manage_operations`, kill switch), `GET /team/me` (любой авторизованный; legacy admin получает `*`), `/team/roles`, `/team/users`, `PUT /team/users/{user_id}/roles`, `DELETE /team/users/{user_id}/sessions/{session_id}` (`system.manage_roles`), `/audit-logs` (`audit.read`). Последнего owner снять нельзя; смена owner/admin увеличивает `token_version` и отзывает сессии. |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `integrations/` | Внешние webhook-интеграции (prefix `/api/integrations/kinescope`); сейчас один файл `kinescope.py` — DRM authorization backend (`POST /drm/authorize`, 600/min), которым Kinescope проверяет право на воспроизведение защищённого видео. Basic-Auth (`KINESCOPE_DRM_BASIC_USER/PASS`, 503 если не заданы), верифицирует RS256 JWT из `kinescope_jwt_service`, ищет урок по `lesson_id` из токена (fallback — по `kinescope_video_id`), сверяет id видео с уроком, проверяет доступ через `LessonService.check_access`. Отдельный `AGENTS.md` для этой директории не создаётся — она полностью описана здесь. |

## For AI Agents

### Working In This Directory

- Новый роутер — всегда `APIRouter()` в новом файле + `include_router` в [`app/main.py`](../main.py) с явным `prefix` и `tags`.
- Авторизация — `Depends(get_current_user)` или `Depends(require_permission("<name>"))` из [`app/core/dependencies.py`](../core/dependencies.py). Не изобретать свои проверки роли инлайн. `require_admin` и `require_course_access` там ещё есть, но роутеры их не используют — для новых админ-ручек не брать.
- Права: `system.manage_roles`, `system.manage_operations`, `users.read`, `users.manage`, `access.manage`, `commerce.read`, `refunds.manage`, `content.manage`, `analytics.read`, `notifications.manage`, `audit.read`, `certificates.manage`, `pii.read`. Роли и права засеяны миграциями. Новое право — только с миграцией. Пользователь с `role="admin"` без назначений RBAC проходит любую проверку (legacy-fallback в `user_has_permission`).
- PII в ответах админки: условное раскрытие через `user_has_permission(db, admin, "pii.read")` + `_mask_email`/`_mask_phone`, как в `/purchases` и `/orders`.
- Мутирующее действие в CRM, управлении доступом, возвратах, сертификатах и команде пишет `append_audit_log` с `reason` и `request.state.correlation_id` в той же транзакции. CRUD контента аудит не пишет.
- Письма и Telegram из роутера не отправляются напрямую — только `enqueue_outbox_message`/`enqueue_owner_telegram_alert` в той же транзакции, доставляет воркер `app/workers/outbox.py`.
- Публичные ручные Pydantic-схемы прямо в файле роутера — существующий паттерн (`admin.py`, `admin_crm.py`, `payments.py`, `upload.py`); для доменных схем, используемых несколькими роутерами, — `app/schemas/`.
- Rate limiting — декоратор `@limiter.limit("N/minute")` из [`app/core/rate_limit.py`](../core/rate_limit.py) (slowapi; функция обязана принимать `request: Request`); обязателен на публичных/чувствительных ручках (auth, payments, DRM webhook). Глобальный лимит `200/minute` задан там же.
- CSRF: при auth-cookie небезопасные запросы требуют заголовок `x-csrf-token`; исключения — `EXEMPT_PATHS` в `CsrfProtectionMiddleware` ([`app/main.py`](../main.py)).
- `admin.py` — не добавляй туда новые несвязанные домены: новые разделы выносятся в отдельные `admin_*.py`, как `admin_crm.py`, `admin_refunds.py`, `admin_system.py`.
- Не дублировать проверку доступа инлайн — использовать `AccessService.has_active_access`/`LessonService.check_access`. Источник истины — `Entitlement`; `Purchase` — неизменяемая финансовая история, отзыв и возврат не меняют `payment_status`.
- Webhook Prodamus (`payments.py`) — единственный источник правды об оплате; не считать `urlReturn`/`urlSuccess` редирект подтверждением оплаты. Страница успеха опрашивает `GET /orders/{order_id}/status`.
- Режим production/staging определяет `settings.is_deployed` (`_is_production()` в `auth.py`, `upload.py`).

### Testing Requirements

```powershell
ruff check backend/app/api backend/tests
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -v --tb=short
```

Точечно: `test_auth*.py`, `test_email_ownership.py`, `test_mfa_sessions.py` (auth, сессии, MFA); `test_rbac_audit.py` (права, аудит); `test_admin_crm.py`, `test_admin_reports.py`, `test_admin_courses.py`, `test_admin_certificates.py`, `test_refunds.py`, `test_content_health.py` (админка); `test_purchases.py`, `test_commerce_safety.py`, `test_expired_access.py`, `test_prodamus_signature.py` (checkout, webhook, доступ); `test_courses.py`, `test_landing_contract.py`, `test_learning_events.py`; `test_certificates.py`; `test_analytics_events.py`; `test_telegram_notifications.py`; `test_image_upload.py`; `test_kinescope.py`, `test_kinescope_drm.py` (DRM webhook); `test_production_hardening.py` (production-safety гарды).

### Common Patterns

- Контроллер вызывает `*Service` и оборачивает `None`/доменные ошибки в `HTTPException` (`_refund_http_error` в `admin_refunds.py`, исключения `CertificateService` в `certificates.py`). Образец мутации админки: guard, сервис, аудит, `db.commit()` — `update_refund` в `admin_refunds.py`.
- SQL-запросов и commit-логики в роутере быть не должно, кроме устоявшихся мест: `admin.py`, `admin_crm.py`, `admin_reports.py`, `admin_system.py`, `admin_landing.py`, `payments.py`.
- `get_db` делает commit после `yield` и rollback при исключении; большинство ручек коммитит явно до ответа, `POST /api/purchases/create` полагается на commit в `get_db`.
- `async with async_session_maker() as db:` используется там, где сессия нужна вне стандартного `Depends(get_db)` (все ручки `payments.py`: своя транзакция на попытку записи webhook).
- Списки CRM: `limit`/`offset`, ответ `{items, total, limit, offset}`, фильтр `status_filter` с alias `status`.

## Dependencies

### Internal
- `app/core/database.py` (`get_db`, `async_session_maker`), `app/core/dependencies.py`, `app/core/rate_limit.py`, `app/core/config.py`, `app/core/security.py`, `app/core/legal.py` (`require_consent`, `CONSENT_VERSION`), `app/core/uploads.py`
- `app/models/*`, `app/schemas/*`, `app/services/*`

### External
- `fastapi`, `pydantic`, `sqlalchemy` (async), `PyJWT` (`auth.py`, `integrations/kinescope.py`), `slowapi` (rate limit), `Pillow` (`upload.py`)

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
