<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-07-06 | Updated: 2026-07-06 -->

# alembic

## Purpose
Миграции схемы БД поверх асинхронного SQLAlchemy 2 (`app/core/database.py: Base`). `env.py` конвертирует async-URL в sync-URL для самого Alembic, так что миграции пишутся и применяются синхронно (`psycopg2`), а приложение в рантайме работает через `asyncpg`.

## Key Files
| File | Description |
|------|-------------|
| `env.py` | Берёт `settings.DATABASE_URL`, заменяет `postgresql+asyncpg://` → `postgresql://` (Alembic не умеет в async-драйвер напрямую), импортирует `Base` и все модели (`User, Course, Module, Lesson, Purchase, Progress, Certificate`) для `target_metadata`, реализует online/offline режимы. |
| `script.py.mako` | Шаблон новых ревизий (`alembic revision --autogenerate`). |
| `README` | Стандартная заглушка Alembic (`Generic single-database configuration`). |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `versions/` | 7 ревизий схемы, линейная цепочка (без веток) — см. список ниже |

### Цепочка миграций (`versions/`)
| Revision | Revises | Файл | Назначение |
|----------|---------|------|------------|
| `7715f796cb35` | — (initial) | `7715f796cb35_initial_schema_with_7_tables.py` | Начальная схема: 7 таблиц (`courses` и др.). |
| `a1ca77add764` | `7715f796cb35` | `a1ca77add764_add_telegram_username.py` | `users.telegram_username`. |
| `2f3f813eeb34` | `a1ca77add764` | `2f3f813eeb34_add_lesson_content.py` | `lessons.content` (Text). |
| `c8d41b2a9f01` | `2f3f813eeb34` | `c8d41b2a9f01_production_user_phone_and_purchase_meta.py` | `users.phone` (+индекс), `purchases.paid_at`, `purchases.customer_phone`. |
| `f6e4f3b2a901` | `c8d41b2a9f01` | `f6e4f3b2a901_set_foil_lesson_kinescope_video.py` | Чисто data-миграция (`op.execute(UPDATE ...)`) — проставляет `kinescope_video_id` для урока «Как отпечатать фольгу». |
| `e7a2c8f91b04` | `f6e4f3b2a901` | `e7a2c8f91b04_add_lesson_promo_fields.py` | Промо-поля уроков для landing-превью (`promo_kinescope_video_id` и др.). |
| `b3a91d4f2c87` | `e7a2c8f91b04` | `b3a91d4f2c87_add_landing_fields_and_gallery.py` | Landing-поля `courses`/`modules` (hero copy, `landing_hero_stats` JSONB) + таблица `gallery_items`. **Head.** |

## For AI Agents

### Working In This Directory
- Любое изменение ORM-моделей в `../app/models/` **обязательно** сопровождается новой ревизией здесь. Ревизии не переписываются задним числом — новая миграция всегда добавляется в конец цепочки (`down_revision` = текущий head, сейчас `b3a91d4f2c87`).
- Тестовые фикстуры (`backend/tests/conftest.py`) строят схему через `Base.metadata.create_all`, **минуя Alembic** — расхождение между моделями и файлами миграций pytest не поймает. Оно обнаруживается только в CI на шаге `alembic upgrade head` (см. `.github/workflows/ci.yml`), который применяется к «боевой» тестовой БД (не к той, что использует pytest).
- Не редактировать существующие файлы `versions/*.py` задним числом, если они уже применялись где-либо (production/staging) — только новая ревизия.
- Data-only миграции (пример: `f6e4f3b2a901`) допустимы через `op.execute(...)`, но должны быть безопасны для повторного запуска и не ломать `upgrade head` на пустой БД.

### Testing Requirements
```powershell
cd backend
.\venv\Scripts\Activate.ps1
alembic revision --autogenerate -m "description"
alembic upgrade head
```
После генерации ревизии — обязательно открыть файл и проверить автосгенерированные `op.*`-команды вручную (autogenerate не видит переименования колонок, кастомные constraints и т.п.).

### Common Patterns
- Заголовок ревизии — docstring с человекочитаемым описанием, `Revision ID`, `Revises`, `Create Date`.
- Простые аддитивные изменения — `op.add_column(table, sa.Column(...))`, при необходимости `op.create_index(...)`.
- JSONB-поля — через `sqlalchemy.dialects.postgresql.JSONB(astext_type=sa.Text())` (см. `b3a91d4f2c87`).

## Dependencies

### Internal
`app.core.config.settings.DATABASE_URL`, `app.core.database.Base`, `app.models.*` (регистрация метаданных для autogenerate).

### External
`alembic`, `sqlalchemy`, `psycopg2-binary` (sync-драйвер, используется только на этапе миграций).

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
