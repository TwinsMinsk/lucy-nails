<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-07-06 | Updated: 2026-07-06 -->

# api

## Purpose

Thin FastAPI-контроллеры (роутеры): по одному файлу на домен, без бизнес-логики — она вынесена в `app/services/`. Каждый файл создаёт свой `APIRouter()` и подключается в [`backend/app/main.py`](../main.py) через `include_router(..., prefix=..., tags=[...])`. Авторизация — только через `Depends` (`get_current_user`, `require_admin`, `require_course_access` из `app/core/dependencies.py`); на RLS в БД не полагаемся.

## Key Files

| File | Description |
|------|-------------|
| `admin.py` | CRUD курсов/модулей/уроков, список пользователей, покупки, аналитика, `POST /grant-access` (ручная выдача доступа) — 797 строк, известный кандидат на доменную декомпозицию |
| `admin_landing.py` | Admin-редактор лендинга: hero курса (`GET/PUT .../landing-hero`), landing-копия модулей (`GET/PUT .../landing-modules`, `.../landing`), CRUD и reorder галереи работ (`/gallery`, `/gallery/reorder`, `/gallery/{id}`) |
| `auth.py` | `/register`, `/login`, `/refresh`, `/me`, `/logout`; ставит/снимает httpOnly cookies (`access_token`, `refresh_token`, `csrf_token`), rate-limit через `limiter` |
| `courses.py` | Публичный каталог: список/детали опубликованных курсов, модули курса, `/my-progress` (прогресс пользователя по курсу, требует активную покупку или admin) |
| `landing.py` | `GET /api/landing` — единый payload для SSR главной страницы: hero первого опубликованного курса + landing-копия его модулей + опубликованная галерея |
| `lessons.py` | Детали урока (видео скрыто без доступа), `POST /{id}/progress`, `GET /{id}/play` (защищённый embed-URL через Kinescope) |
| `modules.py` | Публичные детали модуля и список его уроков (только опубликованные модуль+курс) |
| `payments.py` | Webhook Prodamus (`/webhook`, проверка HMAC-подписи, идемпотентность по `payment_id`, создание пользователя payment-first) + генерация ссылок оплаты (`/link`, `/guest-link`) |
| `purchases.py` | `POST /create` (ссылка оплаты для авторизованного пользователя), `GET /my` (мои курсы с прогрессом); переиспользует хелперы из `payments.py` |
| `upload.py` | `POST /upload` — загрузка изображений (jpg/png/webp/gif), только для админов; в production требует `UPLOAD_STORAGE_DIR` + `UPLOAD_PUBLIC_BASE_URL`, иначе 503 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `integrations/` | Внешние webhook-интеграции; сейчас один файл `kinescope.py` — DRM authorization backend (`POST /drm/authorize`), которым Kinescope проверяет право на воспроизведение защищённого видео. Basic-Auth (`KINESCOPE_DRM_BASIC_USER/PASS`), верифицирует RS256 JWT из `kinescope_jwt_service`, ищет урок по `lesson_id` из токена (fallback — по `kinescope_video_id`), проверяет доступ через `LessonService.check_access`. Отдельный `AGENTS.md` для этой директории не создаётся — она полностью описана здесь. |

## For AI Agents

### Working In This Directory

- Новый роутер — всегда `APIRouter()` в новом файле + `include_router` в [`app/main.py`](../main.py) с явным `prefix` и `tags`.
- Авторизация — только `Depends(get_current_user)` / `Depends(require_admin)` / `Depends(require_course_access)` из [`app/core/dependencies.py`](../core/dependencies.py). Не изобретать свои проверки роли инлайн.
- Публичные ручные Pydantic-схемы прямо в файле роутера — существующий паттерн (`admin.py`, `payments.py`, `upload.py`); для доменных схем, используемых несколькими роутерами, — `app/schemas/`.
- Rate limiting — декоратор `@limiter.limit("N/minute")` из [`app/core/rate_limit.py`](../core/rate_limit.py) (slowapi); обязателен на публичных/чувствительных ручках (auth, payments, DRM webhook).
- `admin.py` — не добавляй туда новые несвязанные домены; при следующей правке рассмотри разбиение по файлам (courses/modules/lessons уже разделены в других роутерах — можно взять за образец).
- Не дублировать проверку `payment_status == "success" AND expires_at > now` инлайн — использовать `PurchaseService`/`LessonService.check_access`.
- Webhook Prodamus (`payments.py`) — единственный источник правды об оплате; не считать `urlReturn`/`urlSuccess` редирект подтверждением оплаты.

### Testing Requirements

```powershell
ruff check backend/app/api backend/tests
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -v --tb=short
```

Точечно: `backend/tests/test_auth.py`, `test_courses.py`, `test_purchases.py`, `test_kinescope_drm.py`, `test_production_hardening.py` — покрывают auth, courses/purchases, DRM webhook и production-safety гарды соответственно.

### Common Patterns

```python
router = APIRouter()

@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    course = await CourseService.get_course_by_id(db, course_id, only_published=True)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course
```

- Контроллер вызывает `*Service` и оборачивает `None`/бизнес-ошибки в `HTTPException`; SQL-запросов и commit-логики в роутере быть не должно (кроме простых admin CRUD, где это уже устоявшийся паттерн в `admin.py`/`admin_landing.py`).
- `async with async_session_maker() as db:` используется там, где сессия нужна вне стандартного `Depends(get_db)` (например, в `payments.py` внутри webhook-транзакции).

## Dependencies

### Internal
- `app/core/database.py` (`get_db`, `async_session_maker`), `app/core/dependencies.py`, `app/core/rate_limit.py`, `app/core/config.py`, `app/core/security.py`
- `app/models/*`, `app/schemas/*`, `app/services/*`

### External
- `fastapi`, `pydantic`, `sqlalchemy` (async), `python-jose` (JWT в `auth.py`/`kinescope.py`), `slowapi` (rate limit)

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
