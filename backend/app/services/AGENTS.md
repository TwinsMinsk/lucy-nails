# services

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose

Бизнес-логика и внешние интеграции, вызываемые из `app/api/*` и воркера [`app/workers/outbox.py`](../workers/outbox.py). Большинство сервисов — классы со `@staticmethod` без состояния (принимают `AsyncSession` первым аргументом); исключения: `KinescopeService`/`KinescopeJwtService` инстанциируются как модуль-level singleton с конфигурацией из `settings`, а `outbox_service.py`, `audit_service.py`, `support_access_service.py`, `payment_event_service.py`, `operations_health_service.py`, `admin_bootstrap.py` — наборы функций.

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | Маркер пакета. |
| **Доступ и оплата** | |
| `access_service.py` | `AccessService` — единая точка прав на курс. `has_active_access` (не-admin без `email_verified_at` доступа не имеет; при наличии любого `Entitlement` по паре user+course решает только он, `Purchase` — legacy-fallback), `get_active_entitlement`, `create_purchase_entitlement`, `grant_manual_access` (срок поверх активного), `revoke_entitlement`, `extend_entitlement`, `suspend_entitlement`, `restore_entitlement` (полностью возвращённую покупку нельзя продлить или восстановить), `get_active_course_accesses`, `get_expired_course_accesses`, `is_purchase_fully_refunded`, очередь Telegram-группы (`enqueue_support_group_restore`, `enqueue_support_group_removal`). |
| `support_access_service.py` | Глобальный доступ к группе поддержки: `has_active_support_entitlement`, `lock_support_membership_state` (advisory-lock транзакции на пользователя), `support_membership_lock_key`. |
| `purchase_service.py` | `PurchaseService.get_my_courses_with_progress` (ЛК: курсы из `AccessService.get_active_course_accesses`, прогресс, ближайший незавершённый урок, сертификат, `support_chat_url` для тарифа `support` и подтверждённого email). `get_active_purchase`, `get_any_successful_purchase`, `get_user_purchases`, `get_purchase_by_id` в `app/` не вызываются; для проверки прав не использовать. |
| `prodamus_service.py` | `ProdamusService`: `generate_payment_link` (GET-ссылка на `payform.ru` с `products[...]`, `urlNotification`, `demo_mode` вне production или по `PRODAMUS_DEMO_MODE`; подпись — по вложенной структуре `products`), `verify_signature` (HMAC-SHA256 по алгоритму Prodamus — рекурсивная сортировка ключей и приведение к строкам как PHP `strval` → JSON без пробелов → экранирование `/` → HMAC; demo-подпись с суффиксом `demo` к секрету принимается только вне production или при `PRODAMUS_DEMO_MODE`). `nest_form_fields` восстанавливает вложенность PHP `$_POST` из multipart-ключей `a[0][b]`. |
| `payment_event_service.py` | `build_payment_event_data` (`event_hash` по всему payload, `sanitized_payload` только из allow-list полей, без email и телефона), `new_payment_event`, `record_terminal_payment_event` (своя сессия через `async_session_maker`). |
| `refund_service.py` | `RefundService` и `RefundError`: `list_refunds`, `create_refund` (сумма заявок кроме `rejected` не больше оплаты; только реальная оплата по `paid_financial_filter`), `update_refund` (`requested` → `submitted` → `processed`/`rejected`, завершённые не переоткрываются, для `processed` обязателен `provider_reference`; при полном возврате отзывает `Entitlement` и сертификаты). |
| `runtime_settings_service.py` | `RuntimeSettingsService`: kill switch checkout (`checkout_enabled`, `set_checkout_enabled`, `CHECKOUT_KEY`); без строки в БД берётся `settings.CHECKOUT_ENABLED`. |
| **Аутентификация** | |
| `auth_service.py` | `AuthService`: `register_user` (уникальность email без учёта регистра, согласия, письмо подтверждения в outbox), `authenticate_user` (bcrypt-верификация в threadpool), `create_tokens` (пара access/refresh JWT с `ver` и опц. `sid`), `change_password`, `set_password` (оба увеличивают `token_version`), `enqueue_verification`, `confirm_mailbox` (ставит `email_verified_at`, удаляет link-токены Telegram, у неподтверждённого не-admin отвязывает Telegram). `get_user_by_id` в `app/` не вызывается. |
| `session_service.py` | `SessionService`: `issue`, `get_active`, `rotate` (несовпадение хеша refresh-токена → отзыв сессии и `None`), `revoke_all`; хелперы `hash_refresh_token`, `hmac_compare`. |
| `mfa_service.py` | `MfaService`: TOTP для ролей owner/admin. `requires_mfa` (по назначениям RBAC, а не по `User.role`), `get_credential`, `get_or_create_setup`, `decrypt_secret`, `enable` (8 backup-кодов), `verify` (TOTP или одноразовый backup-код). Секрет шифруется Fernet на ключе из `MFA_ENCRYPTION_KEY`; fallback на `JWT_SECRET_KEY` конфиг допускает только вне production/staging. |
| `admin_bootstrap.py` | `ensure_admin_user(db, email, password)` — создаёт/промоутит пользователя в `role="admin"` с явным паролем (мин. 12 символов) и назначает роль `owner`, если RBAC засеян; для one-off production bootstrap через `backend/scripts/create_admin.py` (не HTTP-эндпоинт). |
| **Контент и обучение** | |
| `course_service.py` | `CourseService`: `get_courses`/`get_course_by_id` (с фильтром `only_published`, опц. `selectinload` модулей+уроков), `get_course_stats` (агрегаты count/sum по опубликованным модулям/урокам). |
| `module_service.py` | `ModuleService`: `get_course_modules` (только опубликованные, опц. `selectinload` уроков), `get_module_by_id` (без фильтра публикации — её проверяет роутер), `get_module_stats`. |
| `lesson_service.py` | `LessonService`: `get_lesson_by_id` (`selectinload` module→course), `check_access` (доступ = preview ИЛИ admin ИЛИ `AccessService.has_active_access`), `get_lesson_with_access` (неопубликованные модуль/курс скрыты от не-admin), `update_progress` (upsert `Progress`, клэмп `watched_seconds` по `duration_seconds`, `is_completed=false` снимает отметку, события `lesson_completed`/`course_completed`, сам делает commit). `get_progress` в `app/` не вызывается. |
| `progress_service.py` | `ProgressService.get_course_completion` → `CourseCompletion` (`total_lessons`, `completed_lesson_ids`, `completed_count`, `is_complete`, `percent`); считает только уроки опубликованных модулей. |
| **Видео** | |
| `kinescope_jwt_service.py` | `KinescopeJwtService` (singleton `kinescope_jwt_service`): RS256-подпись/верификация короткоживущего JWT (`drmauthtoken`) для DRM authorization backend. Приватный ключ — `KINESCOPE_JWT_PRIVATE_KEY_PATH` (файл) или `KINESCOPE_JWT_PRIVATE_KEY_PEM` (инлайн, `\n`-экранированный, удобно для Railway); `is_configured` требует ключ + `KINESCOPE_JWK_KID`; публичная часть выводится из приватного ключа в памяти для верификации. Конфигурация читается при импорте. |
| `kinescope_service.py` | `KinescopeService` (singleton `kinescope_service`): `get_video_info`, `get_embed_url` (вкладывает `watermark` + `drmauthtoken` от `kinescope_jwt_service`), `upload_video_file` (uploader v2; в `app/` не вызывается). Без `KINESCOPE_API_KEY` работает в mock-режиме (dev/test). В production/staging при отсутствии ключа или DRM-настройки кидает `KinescopeNotConfiguredError`, незащищённый embed не отдаёт. |
| `content_health_service.py` | `ContentHealthService.check_videos`: статусы `missing_video_id`, `provider_error`, `processing`, `duration_mismatch`, `ready`; до 5 параллельных запросов к Kinescope. |
| **Сертификаты** | |
| `certificate_service.py` | `CertificateService`: `claim` (идемпотентен, проверяет email, доступ, полное прохождение, хранилище; рендерит файлы, пишет `Certificate` и outbox `certificate_issued`, сам делает commit), `get_status` (`available`/`not_available`/`issued`/`revoked`), `get_by_number`, `generate_certificate_number` (`LN-<год>-XXXXXX`). Право на сертификат (`_has_course_access`) сохраняется после обычного истечения, но не после отзыва, приостановки или полного возврата. Доменные исключения: `CertificateError`, `NoCourseAccessError`, `CourseNotCompletedError`, `CourseNotFoundError`, `CertificateStorageNotConfiguredError`, `CertificateRevokedError`. `get_for_user_course` в `app/` не вызывается. |
| `certificate_renderer.py` | Чистый синхронный рендер без БД и FastAPI: `render_certificate_png`, `png_to_pdf` (Pillow, `qrcode`, `img2pdf`). |
| `certificate_layout.py` | Константы макета диплома (A4, 300 DPI), общие с `backend/scripts/generate_certificate_template.py`; шаблон и шрифты — `app/assets/certificates/`. |
| **Уведомления, аналитика, эксплуатация** | |
| `email_service.py` | `EmailService`: Resend HTTP API при `RESEND_API_KEY`, иначе SMTP через `aiosmtplib`; таймаут 10 с, с вложением 30 с. `is_configured()` проверяет наличие транспорта; без него — warning и выход без исключения, поэтому outbox считает письмо отправленным. Письма: `send_account_activation`, `send_email_verification`, `send_access_granted`, `send_login_link`, `send_access_expiry_reminder`, `send_access_expired`, `send_password_reset`, `send_certificate_link`. `send_credentials` и `send_certificate` в `app/` не вызываются (на них ссылаются только тесты). |
| `outbox_service.py` | Транзакционный outbox: `enqueue_outbox_message`, `enqueue_owner_telegram_alert` (один раз на `dedupe_key`; без бота или чата владельца — no-op), `format_rub`, `deliver_outbox_message` (маршрут по `channel`/`kind`), `process_outbox_batch` (claim через `skip_locked`, повтор с backoff до часа, `dead_letter` после `max_attempts`, зависший `processing` забирается через 10 минут, каждая попытка — `DeliveryAttempt`), `send_telegram_message`, `remove_telegram_group_member`, `restore_telegram_group_member`. |
| `lifecycle_service.py` | `LifecycleService.schedule` (из воркера раз в `LIFECYCLE_SCAN_SECONDS`): истёкшие active-entitlement → `expired`, письма и Telegram `access_expired`, напоминания за 7/3/1 день, снятие из группы поддержки, сводка владельцу по `dead_letter`. Идемпотентно по `dedupe_key`. |
| `analytics_service.py` | `AnalyticsService.record_event` (идемпотентно по `event_id`, `ValueError` на PII и секретах в UTM/`properties`), `record_lesson_activity` (раз в день на урок), `contains_sensitive_analytics_value`. |
| `audit_service.py` | `append_audit_log` — единственная точка записи аудита; таблица append-only (триггер в миграции). |
| `operations_health_service.py` | `record_worker_heartbeat` (ключ в Redis с TTL 120 с), `operations_snapshot` (данные для `/health/operations` в `app/main.py`). |

## For AI Agents

### Working In This Directory

- Сервисы не поднимают `HTTPException` — это забота роутера (`app/api/*`); сервис возвращает `None`/`False`/бросает доменное исключение (`ValueError`, `RefundError`, `CertificateError` и наследники, `KinescopeNotConfiguredError`, `KinescopeJwtNotConfiguredError`).
- Транзакцию обычно закрывает вызывающий код: сервис делает `db.add`/`flush`. Сами коммитят `LessonService.update_progress`, `CertificateService.claim`, `process_outbox_batch`, `record_terminal_payment_event`.
- Активный доступ к курсу решает только `AccessService.has_active_access`/`LessonService.check_access`: `Entitlement` со статусом `active` в окне `starts_at`…`expires_at` плюс подтверждённый email у не-admin. `Purchase` с `payment_status="success"` и `expires_at > now` учитывается, только если по паре user+course нет ни одного `Entitlement`. При добавлении новой проверки доступа не дублировать SQL инлайн.
- `Purchase` — неизменяемая финансовая история: отзыв и возврат меняют `Entitlement`/`RefundRequest`, а не `payment_status`. Выручка считается только через `paid_financial_filter()` из `app/models/purchase.py`.
- Prodamus: `verify_signature` — единственное место, где решается «оплата подтверждена»; редиректы `urlSuccess`/`urlReturn` не гарантируют оплату — не добавлять по ним логику активации доступа.
- Kinescope DRM: приватный ключ (`KINESCOPE_JWT_PRIVATE_KEY_PATH`/`_PEM`) не должен покидать сервер; не логировать и не возвращать в API его содержимое. Публичный JWK заливается в Kinescope отдельно скриптом [`scripts/kinescope/setup_drm.py`](../../../scripts/kinescope/).
- Письма и Telegram идут только через outbox: `enqueue_outbox_message` в транзакции бизнес-операции, `dedupe_key` уникален. `EmailService.send_*` вызывает только `deliver_outbox_message`; новый `kind` нужно добавить туда, иначе сообщение уйдёт в `dead_letter`. Сбой почты не откатывает покупку.
- Telegram-группа поддержки: изменение entitlement с тарифом `support` и доставка `telegram_group_remove`/`telegram_group_restore` сериализуются через `lock_support_membership_state`; устаревшие команды воркер пропускает со статусом попытки `skipped`.
- Аудит и события: `append_audit_log` и `AnalyticsService.record_event` присоединяются к транзакции вызывающего кода.
- Новый сервис — статик-класс с `@staticmethod` методами, первым параметром `db: AsyncSession`, по образцу `CourseService`/`ModuleService`/`LessonService`. Singleton-паттерн (`kinescope_service`, `kinescope_jwt_service`) — только для сервисов с конфигурацией/состоянием, инициализируемым один раз из `settings`.

### Testing Requirements

```powershell
ruff check backend/app/services backend/tests
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -v --tb=short
```

Точечно: `test_kinescope.py`/`test_kinescope_drm.py` (embed URL, mock-режим, DRM JWT), `test_content_health.py`, `test_admin_bootstrap.py` (`ensure_admin_user`), `test_purchases.py`, `test_commerce_safety.py`, `test_expired_access.py` (доступ, webhook), `test_refunds.py` (`RefundService`), `test_prodamus_signature.py`, `test_auth*.py`, `test_mfa_sessions.py`, `test_email_ownership.py`, `test_outbox.py`, `test_telegram_notifications.py` (`LifecycleService`), `test_email_service.py`, `test_email_attachments.py`, `test_certificates.py`, `test_certificate_number.py`, `test_certificate_renderer.py`, `test_analytics_events.py`, `test_learning_events.py`, `test_operations_health.py`.

### Common Patterns

- Образец операции с доступом и деньгами: блокировка строки `with_for_update`, изменение состояния, `flush`, commit в роутере — `RefundService.update_refund`, `AccessService.extend_entitlement`.
- Mock Kinescope включается по отсутствию `KINESCOPE_API_KEY` и только вне production/staging. Demo Prodamus работает вне production или по `PRODAMUS_DEMO_MODE`: в production конфиг этот флаг отвергает, на staging требует.

## Dependencies

### Internal
- `app/core/config.py` (`settings`), `app/core/database.py` (только `payment_event_service.py`), `app/core/security.py`, `app/core/legal.py`, `app/core/uploads.py`, `app/models/*`, `app/schemas/*` (`auth_service.py`, `session_service.py`, `lesson_service.py`)

### External
- `httpx` (Kinescope, Resend, Telegram), `aiosmtplib` (email), `PyJWT` + `cryptography` (RS256 DRM JWT, Fernet), `pyotp` (MFA), `redis` (heartbeat воркера), `Pillow`, `qrcode`, `img2pdf` (сертификаты), `sqlalchemy[asyncio]`

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
