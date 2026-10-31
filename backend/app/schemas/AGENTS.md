# schemas

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-31

## Purpose

Pydantic v2 схемы запросов/ответов, сгруппированные по доменам, зеркалящим `app/models/`. Используются в `app/api/*` как `response_model` и тела запросов, а также в `auth_service.py`, `session_service.py` и `lesson_service.py`; преобразование ORM → схема — через `from_attributes`/`Config.from_attributes` (частично устаревший `.from_orm()`, частично `model_validate()` — см. Common Patterns).

## Key Files

| File | Description |
|------|-------------|
| `auth.py` | `UserRegister` (+ `offer_accepted`/`personal_data_consent`), `UserLogin` (+ `mfa_code`), `ChangePasswordRequest`, `ForgotPasswordRequest`, `ResetPasswordRequest`, `Token` (access/refresh/bearer), `UserResponse` (`from_attributes=True`). `_normalize_email` приводит email к strip + lowercase |
| `certificate.py` | `CertificateClaimRequest` (`validate_full_name`: нормализация и повторная проверка длины, `_FULL_NAME_PATTERN`), `CertificateResponse` с фабрикой `from_certificate(certificate, course_title)` — у отозванного сертификата скрывает `png_url`/`pdf_url`, `CertificateStatusResponse`, `CertificateVerifyResponse` (публичная проверка по номеру) |
| `course.py` | `CourseBase` (+ `access_days`)/`CourseResponse` (+ `modules_count`/`lessons_count`/`total_duration`, заполняются вручную в `courses.py`), `CourseListResponse` |
| `landing.py` | Схемы редактора лендинга: `HeroStat`, `LandingHeroResponse`/`LandingHeroUpdate`, `LandingModuleResponse`/`LandingModuleUpdate`, `GalleryItemBase`/`Create`/`Update`/`Response`, `GalleryReorderItem`, `LandingCourseSnapshot`, агрегирующий `LandingPayload` (для `GET /api/landing`) |
| `lesson.py` | `LessonBase`/`LessonResponse`/`LessonDetailResponse` (+ `video_url`), `LessonOutlineResponse` — публичная схема без ID видео с фабрикой `from_lesson(lesson)`, распаковывающей JSON `promo_highlights.bullets` в `promo_bullets`, `VideoPlayResponse` (+ `expires_in_seconds`) |
| `module.py` | `ModuleBase`/`ModuleResponse`, `ModuleWithLessonsResponse` (импортирует `LessonOutlineResponse` из `lesson.py` — единственный кросс-файловый импорт схем в модуле, объявлен после определения `ModuleResponse` во избежание цикла) |
| `progress.py` | `ProgressBase`/`ProgressUpdate`/`ProgressResponse` |
| `purchase.py` | `TariffType(str, Enum)`, `PurchaseCreate`, `PaymentStartResponse` (+ `order_id`, `status_token`), `PurchaseResponse` (роутерами сейчас не используется), `MyCourseResponse` (курс в личном кабинете: `progress`, `total_lessons`/`completed_lessons`, `last_lesson_*`, `tariff`, `expires_at`, `support_chat_url`, `certificate_number`), `ExpiredCourseResponse` (истёкший доступ для продления) |
| `ads.py` | Раздел «Реклама». Литералы `CampaignStatus`, `MaterialKind`, `MaterialStatus`, `FileRole` и `KEY_PATTERN` (`^[a-z0-9][a-z0-9_-]{0,63}$` для slug, code, key, variant). Вход синхронизации с лимитами длины и числа элементов: `AdCampaignSync` (+ `AdMaterialSync`, `AdTaskSync`, `AdCalendarSync`, `AdGroup`, `AdSection`, флаг `prune`). Ответы: `AdCampaignSummary`, `AdCampaignDetail`, `AdMaterialResponse`, `AdFileResponse` (подписанные `url`/`download_url` относительно корня API), `AdTaskResponse`, `AdCalendarEntryResponse`, `AdCommentResponse` (`is_mine`), `AdPerson`. Обновления из админки: `AdMaterialUpdate`, `AdTaskUpdate`, `AdCommentCreate`. `from_attributes` нет: ответы собирает `app/services/ads_service.py` |

## For AI Agents

### Working In This Directory

- Конфиг ORM-режима — `class Config: from_attributes = True` (старый Pydantic v1 стиль, а не `model_config = ConfigDict(...)`) — это устоявшийся паттерн во всех файлах модуля; не переписывать на `ConfigDict` точечно в одном файле. `ConfigDict` встречается только в схемах роутеров (`admin_crm.py`, `analytics.py`).
- Многие схемы дублируют `use_enum_values = True` вместе с `from_attributes = True` — сохранять оба флага при добавлении новых Response-схем над enum-полями (`role`, `tariff`, `payment_status`).
- `LessonOutlineResponse.from_lesson()` и `CertificateResponse.from_certificate()` — образцы паттерна «фабрика на schema для схлопывания ORM-состояния в плоские поля»; для новых `promo_*`/`landing_*` JSON-полей следовать этому же подходу вместо ad-hoc парсинга в роутере.
- Схемы для админ-CRUD (создание/обновление курса, модуля, урока) объявлены не здесь, а прямо в `app/api/admin.py` (`CourseCreateRequest` и т.п.) — так исторически сложилось для admin-only payload'ов. То же в `admin_crm.py`, `admin_certificates.py`, `admin_content.py`, `admin_refunds.py`, `admin_reports.py`, `admin_system.py`, а узкие схемы — в `auth.py` (`MfaSetupRequest`, `SessionResponse`), `payments.py` (`PaymentLinkRequest`, `GuestPaymentLinkRequest`), `analytics.py` (`PublicAnalyticsEvent`). `admin.py` объявляет собственные `CourseResponse`/`ModuleResponse`/`LessonResponse` — не путать с одноимёнными схемами отсюда. Новые публичные/переиспользуемые схемы добавлять в `app/schemas/`, не в роутер.
- Опциональные поля в `*Update`-схемах — всегда `| None = None` (или `Field(None, ...)`), обрабатываются в роутере через `model_dump(exclude_unset=True)` (см. `admin_landing.py`).
- Новая схема с email на входе подключает `_normalize_email` через `field_validator(..., mode="before")` (см. `auth.py`), иначе вход и регистрация разойдутся по регистру.
- `offer_accepted`/`personal_data_consent` по умолчанию `False` намеренно: проверку делает `require_consent` в эндпоинте, чтобы вернуть 422 с понятным русским текстом.

### Testing Requirements

```powershell
ruff check backend/app/schemas backend/tests
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -v --tb=short
```

Схемы не имеют отдельных unit-тестов — валидируются косвенно через API-тесты (`test_auth.py`, `test_courses.py`, `test_purchases.py`, `test_certificates.py`, `test_landing_contract.py`), которые бьют по `response_model`.

### Common Patterns

- Образец Response-схемы — `LandingModuleResponse` (`landing.py`); образец фабрики с распаковкой JSON — `LessonOutlineResponse.from_lesson` (`lesson.py`).
- В роутерах для сериализации ORM → схема одновременно встречаются `Schema.from_orm(obj)` (legacy) и `Schema.model_validate(obj)` (актуальный v2 API) — при добавлении нового кода предпочитать `model_validate`, не переписывать существующие вызовы `from_orm` без необходимости.

## Dependencies

### Internal
- Косвенно — форма моделей в `app/models/*` (поля должны соответствовать колонкам для `from_attributes`)
- `module.py` импортирует `lesson.py` (единственная внутримодульная зависимость)
- `lesson.py` и `certificate.py` лениво импортируют ORM-модели внутри фабрик

### External
- `pydantic` v2 (`BaseModel`, `Field`, `EmailStr`, `field_validator`, `TypeAdapter` — последний используется в `app/api/payments.py`, не здесь, но по той же схеме валидации)

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
