# alembic

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose
Миграции схемы БД поверх асинхронного SQLAlchemy 2 (`app/core/database.py: Base`). `env.py` конвертирует async-URL в sync-URL для самого Alembic, так что миграции пишутся и применяются синхронно (`psycopg2`), а приложение в рантайме работает через `asyncpg`. Применяются при старте web-процесса (`alembic upgrade head` в `../Procfile` и `../railway.toml`).

## Key Files
| File | Description |
|------|-------------|
| `env.py` | Берёт `settings.DATABASE_URL`, заменяет `postgresql+asyncpg://` → `postgresql://` (Alembic не умеет в async-драйвер напрямую) и подставляет в `sqlalchemy.url`; импортирует `Base` и пакет `app.models` (его `__init__.py` регистрирует все модели) для `target_metadata`, реализует online/offline режимы. |
| `script.py.mako` | Шаблон новых ревизий (`alembic revision --autogenerate`). |
| `README` | Стандартная заглушка Alembic (`Generic single-database configuration`). |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `versions/` | 28 ревизий схемы, линейная цепочка (без веток), head — `8c9d0e1f2a3b`; см. список ниже |

### Цепочка миграций (`versions/`)
Файл — `<revision>_<slug>.py`. Префиксы не отражают порядок (`0a7b8c9d0e1f` идёт после `f6a7b8c9d0e1`, есть похожие ID вроде `3d5067c10861`/`3d9d0e1f2a3b`) — порядок задаёт только `down_revision`.

| Revision | Revises | Назначение |
|----------|---------|------------|
| `7715f796cb35` | — (initial) | Начальная схема: 7 таблиц (`courses`, `users`, `certificates`, `modules`, `purchases`, `lessons`, `progress`). |
| `a1ca77add764` | `7715f796cb35` | `users.telegram_username`. |
| `2f3f813eeb34` | `a1ca77add764` | `lessons.content` (Text). |
| `c8d41b2a9f01` | `2f3f813eeb34` | `users.phone` (+индекс), `purchases.paid_at`, `purchases.customer_phone`. |
| `f6e4f3b2a901` | `c8d41b2a9f01` | Чисто data-миграция (`op.execute(UPDATE ...)`) — проставляет `kinescope_video_id` для урока «Как отпечатать фольгу». |
| `e7a2c8f91b04` | `f6e4f3b2a901` | Промо-поля уроков для landing-превью (`promo_kinescope_video_id` и др.). |
| `b3a91d4f2c87` | `e7a2c8f91b04` | Landing-поля `courses`/`modules` (hero copy, `landing_hero_stats` JSONB) + таблица `gallery_items`. |
| `d4e5f6a7b8c9` | `b3a91d4f2c87` | `users.token_version` (claim `ver` в JWT). |
| `3d5067c10861` | `d4e5f6a7b8c9` | `users.full_name`, `certificates.student_name`/`png_url`, unique `uq_certificates_user_course`. |
| `5a7b8c9d0e1f` | `3d5067c10861` | Таблица `orders`, `purchases.order_id` (unique). |
| `6b8c9d0e1f2a` | `5a7b8c9d0e1f` | `outbox_messages`, `delivery_attempts`. |
| `7c9d0e1f2a3b` | `6b8c9d0e1f2a` | `courses.access_days`, `entitlements` + backfill из успешных покупок. |
| `8d0e1f2a3b4c` | `7c9d0e1f2a3b` | `payment_events`. |
| `9e1f2a3b4c5d` | `8d0e1f2a3b4c` | `refund_requests`. |
| `a1f2b3c4d5e6` | `9e1f2a3b4c5d` | RBAC (`roles`, `permissions`, `role_permissions`, `user_role_assignments`) с посевом ролей/прав и выдачей `owner` текущим admin; `audit_logs` с триггером `audit_logs_immutable`. |
| `b2c3d4e5f6a7` | `a1f2b3c4d5e6` | `mfa_credentials`, `auth_sessions`. |
| `c3d4e5f6a7b8` | `b2c3d4e5f6a7` | `student_notes`, `student_tags`, `student_tag_assignments`. |
| `e5f6a7b8c9d0` | `c3d4e5f6a7b8` | Жизненный цикл сертификата: `certificates.status`/`revoked_at`/`revoked_by_id`/`revoke_reason`. |
| `f6a7b8c9d0e1` | `e5f6a7b8c9d0` | `analytics_events`; `orders.course_title` (backfill) и UTM-снимки `first_utm_*`/`last_utm_*`. |
| `0a7b8c9d0e1f` | `f6a7b8c9d0e1` | `telegram_link_tokens`. |
| `1b8c9d0e1f2a` | `0a7b8c9d0e1f` | `runtime_settings`, право `system.manage_operations`. |
| `2c9d0e1f2a3b` | `1b8c9d0e1f2a` | `ck_entitlements_status`: разрешён статус `expired`. |
| `3d9d0e1f2a3b` | `2c9d0e1f2a3b` | Data: инкремент `token_version` и отзыв `auth_sessions` у ролей `owner`/`admin`; downgrade намеренно пустой. |
| `4e9d0e1f2a3b` | `3d9d0e1f2a3b` | Data: право `pii.read` для `owner`/`admin`/`curator`. |
| `5f6a7b8c9d0e` | `4e9d0e1f2a3b` | Lowercase `users.email`, unique-индекс `ix_users_email_lower`; падает с `RuntimeError`, если есть дубли по регистру. |
| `6a7b8c9d0e1f` | `5f6a7b8c9d0e` | `offer_accepted_at`/`personal_data_consent_at`/`consent_version` в `orders` и `users`. |
| `7b8c9d0e1f2a` | `6a7b8c9d0e1f` | `users.email_verified_at`. |
| `8c9d0e1f2a3b` | `7b8c9d0e1f2a` | `purchases.transaction_kind` + `ck_purchase_transaction_kind`, backfill `admin_grant_*` → `manual_grant`. **Head.** |

## For AI Agents

### Working In This Directory
- Любое изменение ORM-моделей в `../app/models/` **обязательно** сопровождается новой ревизией здесь. Ревизии не переписываются задним числом — новая миграция всегда добавляется в конец цепочки (`down_revision` = текущий head, сейчас `8c9d0e1f2a3b`; при сомнении проверяй `alembic heads`).
- Тестовые фикстуры (`backend/tests/conftest.py`) строят схему через `Base.metadata.create_all`, **минуя Alembic** — расхождение между моделями и файлами миграций pytest не поймает. Оно обнаруживается только в CI (см. `.github/workflows/ci.yml`) на БД `nails_course`, не той, что использует pytest: `alembic upgrade head`, затем проверка единственного head, `alembic downgrade -1`, снова `upgrade head` и `alembic check`. Поэтому downgrade последней ревизии должен реально работать.
- Триггер `audit_logs_immutable` и функция `prevent_audit_log_mutation` существуют только в миграции `a1f2b3c4d5e6`: в pytest-схеме их нет, `alembic check` их не сравнивает.
- Не редактировать существующие файлы `versions/*.py` задним числом, если они уже применялись где-либо (production/staging) — только новая ревизия.
- Data-only миграции (примеры: `f6e4f3b2a901`, `3d9d0e1f2a3b`, `4e9d0e1f2a3b`) допустимы через `op.execute(...)`, но должны быть безопасны для повторного запуска и не ломать `upgrade head` на пустой БД.
- Новые права RBAC — миграцией с фиксированным UUID и `ON CONFLICT DO NOTHING` (права `01000000-...`, последний занятый суффикс `...013`; роли `02000000-...`), см. `4e9d0e1f2a3b`.

### Testing Requirements
Запускать из `backend/` (те же шаги, что в CI):
```powershell
cd backend
.\venv\Scripts\Activate.ps1
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic heads
alembic downgrade -1
alembic upgrade head
alembic check
```
После генерации ревизии — обязательно открыть файл и проверить автосгенерированные `op.*`-команды вручную (autogenerate не видит переименования колонок, кастомные constraints и т.п.).

### Common Patterns
- Заголовок ревизии — docstring с человекочитаемым описанием, `Revision ID`, `Revises`, `Create Date` (в `7b8c9d0e1f2a` и `8c9d0e1f2a3b` часть полей опущена; обязательны только переменные `revision`/`down_revision`).
- Простые аддитивные изменения — `op.add_column(table, sa.Column(...))`, при необходимости `op.create_index(...)`.
- Новые таблицы используют `sa.Uuid()` для PK/FK и явный `ondelete` в `sa.ForeignKeyConstraint`.
- JSONB-поля лендинга — через `sqlalchemy.dialects.postgresql.JSONB(astext_type=sa.Text())` (см. `b3a91d4f2c87`); журналы и служебные таблицы — `sa.JSON()` (см. `6b8c9d0e1f2a`, `1b8c9d0e1f2a`).

## Dependencies

### Internal
`app.core.config.settings.DATABASE_URL`, `app.core.database.Base`, `app.models.*` (регистрация метаданных для autogenerate).

### External
`alembic`, `sqlalchemy`, `psycopg2-binary` (sync-драйвер Alembic и скриптов из `../scripts/`; приложение его не использует).

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
