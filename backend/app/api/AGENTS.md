# api

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose

Thin FastAPI-контроллеры (роутеры): по одному файлу на домен, без бизнес-логики — она вынесена в `app/services/`. Каждый файл создаёт свой `APIRouter()` и подключается в [`backend/app/main.py`](../main.py) через `include_router(..., prefix=..., tags=[...])`. Авторизация — только через `Depends` (`get_current_user`, `require_admin`, `require_course_access` из `app/core/dependencies.py`); на RLS в БД не полагаемся.

## Key Files

| File | Description |
|------|-------------|
| `admin.py` | CRUD курсов/модулей/уроков, список пользователей, покупки, аналитика, `POST /grant-access` (ручная выдача доступа), `POST /revoke-access` (отзыв доступа по `purchase_id` при возврате/chargeback: `payment_status="failed"` + `expires_at=now`, доступ пропадает сразу) — ~840 строк, известный кандидат на доменную декомпозицию |
| `admin_landing.py` | Admin-редактор лендинга: hero курса (`GET/PUT .../landing-hero`), landing-копия модулей (`GET/PUT .../landing-modules`, `.../landing`), CRUD и reorder галереи работ (`/gallery`, `/gallery/reorder`, `/gallery/{id}`) |
| `auth.py` | `/register`, `/login`, `/refresh`, `/me`, `/logout`, `/change-password` (нужен текущий пароль; перевыпускает cookies текущей сессии), `/forgot-password` (шлёт ссылку сброса через `EmailService.send_password_reset`, ответ одинаковый независимо от наличия email — защита от enumeration), `/reset-password` (по reset-JWT, одноразовый за счёт `token_version`); ставит/снимает cookies (`access_token`, `refresh_token`, `csrf_token`, домен — `COOKIE_DOMAIN`), rate-limit через `limiter`. `/refresh` отвергает токены с устаревшим `ver` |
| `courses.py` | Публичный каталог: список/детали опубликованных курсов, модули курса, `/my-progress` (прогресс пользователя по курсу, требует активную покупку или admin) |
| `landing.py` | `GET /api/landing` — единый payload для SSR главной страницы: hero первого опубликованного курса + landing-копия его модулей + опубликованная галерея |
| `lessons.py` | Детали урока (видео скрыто без доступа), `POST /{id}/progress`, `GET /{id}/play` (защищённый embed-URL через Kinescope; при `KinescopeNotConfiguredError` — 503, в деталях урока — `video_url=None`) |
| `modules.py` | Публичные детали модуля и список его уроков (только опубликованные модуль+курс) |
| `payments.py` | Webhook Prodamus (`/webhook`): проверка HMAC-подписи, отказ (422) без явного success-статуса (`_is_success_payment_payload` — пустой/отсутствующий статус **не** успех), проверка суммы и валюты, идемпотентность по `payment_id`, создание пользователя payment-first. Запись покупки — `_record_purchase_once` в собственной транзакции с одним повтором при `IntegrityError` (гонка двух первых оплат с одним новым email); неразрешённый конфликт пробрасывается, чтобы Prodamus повторил webhook. Письмо с паролем — после commit, ошибка отправки только логируется. Плюс генерация ссылок оплаты (`/link`, `/guest-link`) |
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
- JWT выдавать только через `AuthService.create_tokens(user.id, user.token_version)`, пароль менять только через `AuthService.change_password`/`set_password` (они инкрементируют `token_version` и тем самым гасят старые сессии и reset-ссылки). Новые auth-ручки, вызываемые до входа, нужно добавлять в `CsrfProtectionMiddleware.EXEMPT_PATHS` в `app/main.py`.

### Testing Requirements

```powershell
ruff check backend/app/api backend/tests
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -v --tb=short
```

Точечно: `backend/tests/test_auth.py`, `test_auth_password.py`, `test_courses.py`, `test_purchases.py`, `test_kinescope.py`, `test_kinescope_drm.py`, `test_production_hardening.py` — покрывают auth, смену/сброс пароля и инвалидацию токенов, courses, покупки + webhook Prodamus + admin revoke, `/play`, DRM webhook и production-safety гарды соответственно.

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

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
