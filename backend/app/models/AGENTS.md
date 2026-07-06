<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-07-06 | Updated: 2026-07-06 -->

# models

## Purpose

SQLAlchemy 2 async ORM-модели (`Mapped`/`mapped_column`, `DeclarativeBase` из `app/core/database.py`). Каждая модель — таблица PostgreSQL; `app/models/__init__.py` реэкспортирует все классы для `from app.models import ...`. Схема БД версионируется через Alembic — модели сами по себе не создают таблицы в production.

## Key Files

| File | Description |
|------|-------------|
| `user.py` | `User` → `users`. `email` (unique, index), `phone` (index, опц.), `password_hash`, `telegram_id`/`telegram_username`, `role` (`SQLEnum("student","admin")`). Связи: `purchases`, `progress`, `certificates` (все `cascade="all, delete-orphan"`) |
| `course.py` | `Course` → `courses`. `price_self`/`price_support` (рубли), `is_published`, плюс блок `landing_*` полей (title/subtitle/description/audience/support_note/hero_stats JSON/benefits JSON/instructor_image_url) — override для лендинга, NULL → фронт берёт дефолт из `course-content.ts`. Связи: `modules` (order_by `order_index`), `purchases`, `certificates` |
| `module.py` | `Module` → `modules`. FK `course_id` (`CASCADE`), `order_index`, `is_published`, плюс `landing_*` override-поля (description/outcome/bullets JSON/mistakes JSON/duration_label). Связи: `course`, `lessons` (order_by `order_index`) |
| `lesson.py` | `Lesson` → `lessons`. FK `module_id` (`CASCADE`), `kinescope_video_id`, `duration_seconds`, `content` (конспект), `order_index`, `is_preview` (бесплатный доступ), плюс промо-блок для лендинга (`promo_kinescope_video_id`, `promo_poster_url`, `promo_description`, `promo_highlights` JSON). Связи: `module`, `progress` |
| `progress.py` | `Progress` → `progress`. FK `user_id`/`lesson_id` (оба `CASCADE`), `UniqueConstraint("user_id", "lesson_id")`, `watched_seconds`, `is_completed`, `completed_at` |
| `purchase.py` | `Purchase` → `purchases`. FK `user_id`/`course_id` (`CASCADE`), `tariff` (`SQLEnum self/support`), `amount_kopecks`, `payment_id` (unique, index — идемпотентность webhook), `payment_status` (`SQLEnum pending/success/failed`), `expires_at` — основа проверки доступа к курсу |
| `certificate.py` | `Certificate` → `certificates`. FK `user_id`/`course_id` (`CASCADE`), `certificate_number` (unique), `pdf_url` |
| `gallery.py` | `GalleryItem` → `gallery_items`. Без FK (глобальная галерея для лендинга): `order_index`, `image_url`, `title`, `caption`, `alt`, `is_published` |

## For AI Agents

### Working In This Directory

- ЖЕЛЕЗНОЕ правило: любое изменение модели (новое поле, индекс, FK, enum-значение) **обязательно** сопровождается миграцией `alembic revision --autogenerate -m "..."` в [`backend/alembic/versions/`](../../alembic/versions/) и `alembic upgrade head`. Тестовые фикстуры строят схему через `Base.metadata.create_all` ([`backend/tests/conftest.py`](../../tests/conftest.py)), поэтому расхождение модель↔миграция не проявится локально в pytest — только в CI на шаге `alembic upgrade head`.
- Новую модель — добавить импорт и в `__all__` в `models/__init__.py`.
- JSON-колонки (`landing_hero_stats`, `landing_benefits`, `landing_bullets`, `landing_mistakes`, `promo_highlights`) хранят обычные Python `list`/`dict`; сериализация в Pydantic-схемы — в `app/schemas/landing.py`/`app/schemas/lesson.py`, не добавлять кастомные типы колонок без необходимости.
- Каскады (`cascade="all, delete-orphan"`) уже расставлены по родительским моделям (`User`, `Course`, `Module`) — при добавлении новой дочерней модели следовать этому паттерну, а не полагаться на `ON DELETE` FK без ORM-cascade.
- Не опираться на RLS/DB-level авторизацию — все проверки доступа (роль, активная покупка) делаются в `app/core/dependencies.py` / `app/services/*` на уровне приложения.

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
```

### Common Patterns

```python
class Module(Base):
    __tablename__ = "modules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    course: Mapped["Course"] = relationship(back_populates="modules")
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="module", cascade="all, delete-orphan", order_by="Lesson.order_index")
```

- Все PK — `uuid.UUID` с `default=uuid.uuid4`, все FK — с `ondelete="CASCADE"` и `index=True`.
- Eager-loading при выборке связей — только через `selectinload` в сервисах (`app/services/*`), не `joinedload`/lazy в модели.

## Dependencies

### Internal
- `app/core/database.py` (`Base`)

### External
- `sqlalchemy` 2.x (`Mapped`, `mapped_column`, async ORM)

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
