<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-07-06 | Updated: 2026-07-06 -->

# schemas

## Purpose

Pydantic v2 схемы запросов/ответов, сгруппированные по доменам, зеркалящим `app/models/`. Используются в `app/api/*` как `response_model` и тела запросов; преобразование ORM → схема — через `from_attributes`/`Config.from_attributes` (частично устаревший `.from_orm()`, частично `model_validate()` — см. Common Patterns).

## Key Files

| File | Description |
|------|-------------|
| `auth.py` | `UserRegister`, `UserLogin`, `Token` (access/refresh/bearer), `UserResponse` (`from_attributes=True`) |
| `course.py` | `CourseBase`/`CourseResponse` (+ `modules_count`/`lessons_count`/`total_duration`, заполняются вручную в `courses.py`), `CourseListResponse` |
| `landing.py` | Схемы редактора лендинга: `HeroStat`, `LandingHeroResponse`/`LandingHeroUpdate`, `LandingModuleResponse`/`LandingModuleUpdate`, `GalleryItemBase`/`Create`/`Update`/`Response`, `GalleryReorderItem`, агрегирующий `LandingPayload` (для `GET /api/landing`) |
| `lesson.py` | `LessonBase`/`LessonResponse`/`LessonDetailResponse` (+ `video_url`), `LessonOutlineResponse` — публичная схема без ID видео с фабрикой `from_lesson(lesson)`, распаковывающей JSON `promo_highlights.bullets` в `promo_bullets`, `VideoPlayResponse` |
| `module.py` | `ModuleBase`/`ModuleResponse`, `ModuleWithLessonsResponse` (импортирует `LessonOutlineResponse` из `lesson.py` — единственный кросс-файловый импорт схем в модуле, объявлен после определения `ModuleResponse` во избежание цикла) |
| `progress.py` | `ProgressBase`/`ProgressUpdate`/`ProgressResponse` |
| `purchase.py` | `TariffType(str, Enum)`, `PurchaseCreate`, `PaymentStartResponse`, `PurchaseResponse`, `MyCourseResponse` (курс в личном кабинете: `progress`, `total_lessons`/`completed_lessons`, `last_lesson_*`, `support_chat_url`) |

## For AI Agents

### Working In This Directory

- Конфиг ORM-режима — `class Config: from_attributes = True` (старый Pydantic v1 стиль, а не `model_config = ConfigDict(...)`) — это устоявшийся паттерн во всех файлах модуля; не переписывать на `ConfigDict` точечно в одном файле.
- Многие схемы дублируют `use_enum_values = True` вместе с `from_attributes = True` — сохранять оба флага при добавлении новых Response-схем над enum-полями (`role`, `tariff`, `payment_status`).
- `LessonOutlineResponse.from_lesson()` — образец паттерна «фабрика на schema для схлопывания JSON-колонки в плоское поле»; для новых `promo_*`/`landing_*` JSON-полей следовать этому же подходу вместо ad-hoc парсинга в роутере.
- Схемы для админ-CRUD (создание/обновление курса, модуля, урока) объявлены не здесь, а прямо в `app/api/admin.py` (`CourseCreateRequest` и т.п.) — так исторически сложилось для admin-only payload'ов; новые публичные/переиспользуемые схемы добавлять в `app/schemas/`, не в роутер.
- Опциональные поля в `*Update`-схемах — всегда `| None = None` (или `Field(None, ...)`), обрабатываются в роутере через `model_dump(exclude_unset=True)` (см. `admin_landing.py`).

### Testing Requirements

```powershell
ruff check backend/app/schemas backend/tests
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -v --tb=short
```

Схемы не имеют отдельных unit-тестов — валидируются косвенно через API-тесты (`test_auth.py`, `test_courses.py`, `test_purchases.py`), которые бьют по `response_model`.

### Common Patterns

```python
class LandingModuleResponse(BaseModel):
    id: UUID
    title: str
    order_index: int
    landing_bullets: list[str] | None = None

    class Config:
        from_attributes = True
```

```python
@classmethod
def from_lesson(cls, lesson: Any) -> LessonOutlineResponse:
    ph = lesson.promo_highlights if isinstance(lesson.promo_highlights, dict) else {}
    bullets = list(ph.get("bullets") or [])
    return cls(..., promo_bullets=bullets)
```

- В роутерах для сериализации ORM → схема одновременно встречаются `Schema.from_orm(obj)` (legacy) и `Schema.model_validate(obj)` (актуальный v2 API) — при добавлении нового кода предпочитать `model_validate`, не переписывать существующие вызовы `from_orm` без необходимости.

## Dependencies

### Internal
- Косвенно — форма моделей в `app/models/*` (поля должны соответствовать колонкам для `from_attributes`)
- `module.py` импортирует `lesson.py` (единственная внутримодульная зависимость)

### External
- `pydantic` v2 (`BaseModel`, `Field`, `EmailStr`, `TypeAdapter` — последний используется в `app/api/payments.py`, не здесь, но по той же схеме валидации)

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
