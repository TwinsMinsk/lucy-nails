# models

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose

SQLAlchemy 2 async ORM-модели (`Mapped`/`mapped_column`, `DeclarativeBase` из `app/core/database.py`). Каждая модель — таблица PostgreSQL; `app/models/__init__.py` реэкспортирует все классы для `from app.models import ...`. Схема БД версионируется через Alembic — модели сами по себе не создают таблицы в production.

## Key Files

| File | Description |
|------|-------------|
| `user.py` | `User` → `users`. `email` (unique, index; плюс функциональный unique-индекс `ix_users_email_lower`), `email_verified_at`, `phone` (index, опц.), `password_hash`, `telegram_id` (unique)/`telegram_username`, `full_name`, `role` (`SQLEnum("student","admin")`), `token_version` (claim `ver` в JWT), consent-поля (`offer_accepted_at`, `personal_data_consent_at`, `consent_version`). Связи: `purchases`, `progress`, `certificates`, `entitlements`, `role_assignments`, `mfa_credential`, `auth_sessions` (все `cascade="all, delete-orphan"`), `orders` (без cascade) |
| `course.py` | `Course` → `courses`. `price_self`/`price_support` (рубли), `is_published`, `access_days`, плюс блок `landing_*` полей (title/subtitle/description/audience/support_note/hero_stats JSON/benefits JSON/instructor_image_url) — override для лендинга, NULL → фронт берёт дефолт из `course-content.ts`. Связи: `modules` (order_by `order_index`), `purchases`, `certificates`, `entitlements`, `orders` (без cascade, FK `RESTRICT`) |
| `module.py` | `Module` → `modules`. FK `course_id` (`CASCADE`), `order_index`, `is_published`, плюс `landing_*` override-поля (description/outcome/bullets JSON/mistakes JSON/duration_label). Связи: `course`, `lessons` (order_by `order_index`) |
| `lesson.py` | `Lesson` → `lessons`. FK `module_id` (`CASCADE`), `kinescope_video_id`, `duration_seconds`, `content` (конспект), `order_index`, `is_preview` (бесплатный доступ), плюс промо-блок для лендинга (`promo_kinescope_video_id`, `promo_poster_url`, `promo_description`, `promo_highlights` JSON). Связи: `module`, `progress` |
| `progress.py` | `Progress` → `progress`. FK `user_id`/`lesson_id` (оба `CASCADE`), `UniqueConstraint("user_id", "lesson_id")`, `watched_seconds`, `is_completed`, `completed_at` |
| `purchase.py` | `Purchase` → `purchases`. Финансовая запись: FK `user_id`/`course_id` (`CASCADE`), `order_id` (`SET NULL`, unique), `tariff` (`SQLEnum self/support`), `amount_kopecks`, `transaction_kind` (`paid`/`manual_grant`, CHECK), `payment_id` (unique, index — идемпотентность webhook), `payment_status` (`SQLEnum pending/success/failed`), `paid_at`, `customer_phone`, `expires_at`. `paid_financial_filter()` — фильтр настоящих оплат для отчётов |
| `order.py` | `Order` → `orders`. Неизменяемый снимок checkout до редиректа на Prodamus: `user_id` (`SET NULL`, пуст при гостевом checkout), `course_id` (`RESTRICT`), `course_title`, `tariff`, `customer_email`, `amount_kopecks`, `access_days`, `status`, `status_token_hash`, UTM-снимки `first_utm_*`/`last_utm_*`, consent-поля, `paid_at` |
| `entitlement.py` | `Entitlement` → `entitlements`. Право доступа к курсу, отделённое от финансов, — основа проверки доступа (`AccessService`): `source_purchase_id` (`SET NULL`, unique), `granted_by_id`, `source`, `tariff`, `status` (CHECK `active/suspended/revoked/expired`), `starts_at`, `expires_at`, `reason`, `revoked_at` |
| `payment_event.py` | `PaymentEvent` → `payment_events`. Очищенный журнал событий провайдера: `event_hash` (unique — идемпотентность), `external_event_id`, `order_reference`, `event_type`, `processing_status`, `sanitized_payload`, `error_code`, связи `order`/`purchase` (`SET NULL`) |
| `refund.py` | `RefundRequest` → `refund_requests`. Внутренний workflow возврата (сам возврат выполняется в Prodamus): `purchase_id`/`created_by_id` (`RESTRICT`), `processed_by_id` (`SET NULL`), `amount_kopecks`, `reason`, `status`, `provider_reference` |
| `outbox.py` | `OutboxMessage` → `outbox_messages`: `kind`, `channel`, `recipient`, `payload`, `status`, `attempts`/`max_attempts`, `next_attempt_at`, `locked_at`, `dedupe_key` (unique). `DeliveryAttempt` → `delivery_attempts`: история попыток (`CASCADE`). Обрабатывается `app/workers/outbox.py` |
| `rbac.py` | `Role` → `roles`, `Permission` → `permissions`, M2M-таблица `role_permissions`, `UserRoleAssignment` → `user_role_assignments` (unique `user_id`+`role_id`). Роли и права сеются миграциями, проверка — `require_permission` |
| `audit_log.py` | `AuditLog` → `audit_logs`. Append-only журнал админ-действий: `actor_user_id` (`SET NULL`), `action`, `object_type`/`object_id`, `old_value`/`new_value`, `reason`, `correlation_id`. Неизменяемость держит триггер `audit_logs_immutable` из миграции |
| `auth_security.py` | `MfaCredential` → `mfa_credentials` (unique `user_id`, `secret_encrypted`, `backup_code_hashes`, `enabled_at`). `AuthSession` → `auth_sessions` (`refresh_token_hash`, `ip_address`, `user_agent`, `last_seen_at`, `expires_at`, `revoked_at`) |
| `crm.py` | `StudentNote` → `student_notes` (`author_id` `RESTRICT`), `StudentTag` → `student_tags` (unique `name`), `StudentTagAssignment` → `student_tag_assignments` (unique `user_id`+`tag_id`, `assigned_by_id` `RESTRICT`) |
| `analytics_event.py` | `AnalyticsEvent` → `analytics_events`. First-party события без PII: `event_id` (unique), `event_name`, `source`, `happened_at`, `anonymous_id`, FK `SET NULL` на `users`/`orders`/`courses`/`lessons`, `utm_*`, `properties` |
| `telegram_link.py` | `TelegramLinkToken` → `telegram_link_tokens`. Одноразовые токены привязки Telegram: `user_id` (`CASCADE`), `token_hash` (SHA-256, unique), `expires_at`, `used_at` |
| `runtime_setting.py` | `RuntimeSetting` → `runtime_settings`. Нечувствительные операционные настройки из админки: PK `key` (строка), `value`, `updated_by_id` (`SET NULL`), `updated_at` |
| `certificate.py` | `Certificate` → `certificates`. FK `user_id`/`course_id` (`CASCADE`, unique-пара `uq_certificates_user_course`), `certificate_number` (unique), `student_name`, `pdf_url`/`png_url`, `issued_at`, `status`, `revoked_at`, `revoked_by_id` (`SET NULL`), `revoke_reason` |
| `gallery.py` | `GalleryItem` → `gallery_items`. Без FK (глобальная галерея для лендинга): `order_index`, `image_url`, `title`, `caption`, `alt`, `is_published` |

## For AI Agents

### Working In This Directory

- ЖЕЛЕЗНОЕ правило: любое изменение модели (новое поле, индекс, FK, enum-значение) **обязательно** сопровождается миграцией `alembic revision --autogenerate -m "..."` в [`backend/alembic/versions/`](../../alembic/versions/) и `alembic upgrade head`. Тестовые фикстуры строят схему через `Base.metadata.create_all` ([`backend/tests/conftest.py`](../../tests/conftest.py)), поэтому расхождение модель↔миграция не проявится локально в pytest — только в CI на шагах `alembic upgrade head` и `alembic check`.
- Новую модель — добавить импорт и в `__all__` в `models/__init__.py`, а таблицу — в `TRUNCATE` фикстуры `db` в `backend/tests/conftest.py`.
- JSON-колонки лендинга (`landing_hero_stats`, `landing_benefits`, `landing_bullets`, `landing_mistakes`, `promo_highlights`) — `JSONB`, хранят обычные Python `list`/`dict`; сериализация в Pydantic-схемы — в `app/schemas/landing.py`/`app/schemas/lesson.py`. Журналы и служебные таблицы (`payload`, `sanitized_payload`, `properties`, `old_value`/`new_value`, `backup_code_hashes`, `value`) — `JSON`. Не добавлять кастомные типы колонок без необходимости.
- Каскады (`cascade="all, delete-orphan"`) уже расставлены по родительским моделям (`User`, `Course`, `Module`, `Lesson`, `Role`, `OutboxMessage`) — при добавлении новой дочерней модели следовать этому паттерну, а не полагаться на `ON DELETE` FK без ORM-cascade. Исключение — финансовая и аудиторская история: `Order`, `RefundRequest`, `PaymentEvent`, `AuditLog` не каскадятся, у них FK `RESTRICT` или `SET NULL`.
- `Purchase` — финансы, `Entitlement` — доступ: не проверять доступ по `Purchase` и не считать выручку по `Entitlement`. Отчёты строить через `paid_financial_filter()`, он исключает ручные выдачи.
- Секреты и токены хранить только в виде хешей или шифротекста (`token_hash`, `status_token_hash`, `refresh_token_hash`, `backup_code_hashes`, `secret_encrypted`).
- Не опираться на RLS/DB-level авторизацию — все проверки доступа (роль, право, активный entitlement) делаются в `app/core/dependencies.py` / `app/services/*` на уровне приложения.

### Testing Requirements

```powershell
ruff check backend/app/models backend/tests
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -v --tb=short
```

После правки модели дополнительно проверить миграцию:
```powershell
cd backend
.\venv\Scripts\Activate.ps1
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic check
```

### Common Patterns

- Образец типичной модели — `module.py`: `Mapped`/`mapped_column`, `relationship(back_populates=...)` со строковыми forward references (F821 для каталога отключён в `pyproject.toml`).
- PK — `uuid.UUID` с `default=uuid.uuid4`; исключения — строковый `RuntimeSetting.key` и составной PK `role_permissions`.
- FK — с явным `ondelete` (`CASCADE`, `SET NULL` или `RESTRICT`) и почти всегда с `index=True`.
- Старые перечисления — `SQLEnum` (`user_role`, `tariff_type`, `payment_status`); новые статусы — `String`, при необходимости с `CheckConstraint` (`ck_entitlements_status`, `ck_purchase_transaction_kind`). Новое значение перечисления или CHECK требует миграции.
- Время — naive UTC (`default=datetime.utcnow`).
- Eager-loading при выборке связей — только через `selectinload` в сервисах и роутерах (`app/services/*`, `app/api/*`), не `joinedload`/lazy в модели.

## Dependencies

### Internal
- `app/core/database.py` (`Base`)

### External
- `sqlalchemy` 2.x (`Mapped`, `mapped_column`, async ORM, `postgresql.JSONB`)

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
