# BACKLOG — приоритизированный план приведения в порядок

Дата: 2026-06-26 · Ветка: `refactor/cleanup`. Сортировка: сверху **квик-вины** (высокое влияние + низкий риск + поведение не меняется), снизу — **рискованное / меняющее поведение**. Каждый пункт выполняется отдельно, по одному.

Легенда: Влияние/Риск = H/M/L · Трудозатраты: S (≤30 мин) / M (~полдня) / L (1–2+ дня) · «Поведение»: меняет ли наблюдаемое поведение приложения.

## Квик-вины (делать первыми)

| ID | Область | Находка | Доказательство (file:line) | Влияние | Риск | Труд | Поведение | Исправление | Затрагиваемые файлы |
|---|---|---|---|---|---|---|---|---|---|
| SEC-01 | Security | Плейнтекст-учётки (admin/student) закоммичены, в HEAD+истории | `test-login.txt:1-5`; `git ls-tree -r HEAD`; коммит `084e40a` | H | L | S | Нет | `git rm test-login.txt`; считать пароли скомпрометированными; не хранить креды в репо | `test-login.txt` |
| SEC-02 | Security | Хардкод пароля БД + деструктивный `UPDATE courses` в stray-скрипте | `backend/test_courses.py:4-6,18-20`; коммит `058c9ac` | H | L | S | Нет | Удалить файл; ротировать пароль БД, если переиспользуется | `backend/test_courses.py` |
| DEBT-01 | Гигиена | Дев-артефакты отслеживаются в репо (3 безопасных) | `backend/check_lesson_db.py`, `backend/test_payment.py`, `backend/run_test.bat` (все в HEAD) | M | L | S | Нет | Удалить или перенести в `scripts/` | те же 3 файла |
| FE-01 | Frontend | Lint warnings: 2 неиспользуемых импорта + `any` | `frontend/src/app/admin/courses/page.tsx:6`; `frontend/src/components/ui/editor.tsx:19,31` | L | L | S | Нет | Убрать `Upload`/`LinkIcon`; типизировать `editor: Editor` | 2 файла |
| BE-04 | Backend | Гард импортируется из роутера, а не из core | `backend/app/api/upload.py:11` | L | L | S | Нет | `from app.core.dependencies import require_admin` | `upload.py` |
| SEC-04 | Security | Текст внутреннего исключения отдаётся клиенту | `backend/app/api/upload.py:85-89` | L | L | S | Почти нет | Логировать детально, вернуть обобщённый `detail` | `upload.py` |
| BE-02 | Backend | `datetime.utcnow()` deprecated (Py 3.12+) | `backend/app/api/payments.py:270`; `backend/app/core/dependencies.py:112` | L | L | S | Нет | `datetime.now(timezone.utc)` | payments.py, dependencies.py, прочие вхождения |
| CONF-02 | Security | CORS `allow_methods/headers=["*"]` с credentials (origins — allowlist) | `backend/app/main.py:132-138` | L | L | S | Нет | Явные списки методов/заголовков | `main.py` |
| BE-01 | Backend | Блокирующий `open().write()` в async-роуте загрузки | `backend/app/api/upload.py:82-84` | M | L | S | Нет (перф) | `await asyncio.to_thread(...)` или `aiofiles` | `upload.py` |

## Средний приоритет (структура/надёжность, чистый рефакторинг)

| ID | Область | Находка | Доказательство (file:line) | Влияние | Риск | Труд | Поведение | Исправление | Затрагиваемые файлы |
|---|---|---|---|---|---|---|---|---|---|
| TEST-01 | Tests | Нет тестов на admin CRUD / landing / upload / bot | `backend/tests/` (нет соответствующих файлов) | M | L | L | Нет | Добавить pytest на `admin.py` (приоритет), затем landing/upload | новые `backend/tests/test_admin*.py` |
| TEST-02 | Tests/CI | Дрейф «`create_all` в тестах vs Alembic в CI» не проверяется | `backend/tests/conftest.py:51-52`; `.github/workflows/ci.yml` (alembic step) | M | L | M | Нет | Шаг паритета моделей↔миграций (`alembic check`/автоген-диф пуст) | conftest или CI |
| BE-05 | Backend | Нет ретраев на исходящих Kinescope HTTP (таймауты есть) | `backend/app/services/kinescope_service.py:65-84,181,208` | M | L | M | Нет | Ограниченный backoff на идемпотентные GET | `kinescope_service.py` |
| FE-04 | Frontend | Нет `error.tsx`/`loading.tsx` для protected/admin | отсутствие файлов в `frontend/src/app/(protected)`, `/admin` | M | L | M | Почти нет | Добавить error/loading boundaries | новые route-файлы |
| DOCS-01 | Docs | `ARCHITECTURE.md` не описывает `gallery`, 4 сервиса, 3 группы эндпоинтов | `Docs/ARCHITECTURE.md` vs `models/gallery.py`, `services/*`, `api/admin_landing.py`,`upload.py`,`integrations/kinescope.py` | L | L | M | Нет | Один проход синхронизации | `Docs/ARCHITECTURE.md` |
| BE-03 | Backend | God-router: бизнес-логика протекла в `admin.py` | `backend/app/api/admin.py` (797 строк; ручная сборка `:239-255`; grant-access `:723+`) | M | M | L | Нет | Вынести в доменные admin-сервисы | `admin.py`, новые `services/admin_*` |
| FE-02 | Frontend | God-модуль `api.ts` (890 строк) | `frontend/src/lib/api.ts` (`apiFetch` 45 рёбер) | M | M | L | Нет | Разнести по доменам, сохранив `apiFetch` | `lib/api.ts` → `lib/api/*` |
| FE-03 | Frontend | Крупные client-страницы админки | `frontend/src/app/admin/landing/page.tsx` (969), `admin/courses/[id]/page.tsx` (591), `admin/courses/page.tsx` (474) | M | M | L | Нет | Декомпозиция на компоненты/формы | те же |
| DEP-02 | Deps | Пины `requirements.txt` отстают; нет venv; возможно лишние депы | `backend/requirements.txt` (ruff 0.9.4 vs локально 0.15.9 и т.д.); `firecrawl-py`/`rich` без ссылок в `backend/app` | M | M | M | Нет | venv из requirements, выровнять версии, ревизия лишних депов | `requirements.txt`, окружение |

## Рискованное / меняет поведение (делать последним, отдельными PR с проверкой)

| ID | Область | Находка | Доказательство (file:line) | Влияние | Риск | Труд | Поведение | Исправление | Затрагиваемые файлы |
|---|---|---|---|---|---|---|---|---|---|
| SEC-03 | Security | Seed известных слабых паролей в любом non-prod | `backend/app/main.py:79-101` (`:83-84`) | M | M | S | **Да** | Пароли из env/случайные с разовым логом; сузить гард до `ENVIRONMENT == "development"` | `main.py` |
| DEP-01 | Deps | 10 npm-уязвимостей (4 high picomatch, moderate postcss); `next` фиксится 16.2.9 | `npm audit` (frontend) | M | M | M | Возможно | `npm audit fix`; контролируемый bump `next`/postcss с прогоном lint+build | `frontend/package.json`, lock |
| CI-01 | CI | Нет автотестов фронта (`npm test` отсутствует) | `.github/workflows/ci.yml`; `frontend/package.json` (нет `test`) | M | L | L | Нет (добавление) | Component/e2e на Playwright (post-MVP) | новые тест-файлы, CI |
| BE-06 | Backend | Авто-commit в `get_db` при успехе хендлера (наблюдение) | `backend/app/core/database.py:43` | L | H | — | **Да** | НЕ менять без отдельного решения (CLAUDE.md запрещает точечные правки) — задокументировать политику | `core/database.py` |
| INTEG-01 | Security/Payments | Demo-подпись вебхука (`secret+"demo"`) принимается **во всех окружениях**, включая production, без гейта на `ENVIRONMENT`/`PRODAMUS_DEMO_MODE` | `backend/app/services/prodamus_service.py:132-137` | M | M | S | **Да** | Подтвердить продуктовое намерение (фича test-payments на prod, коммит `09eb605`). Если не нужно — принимать demo-подпись только при `PRODAMUS_DEMO_MODE`/non-prod. Сумма/валюта всё равно сверяются, поэтому не CRITICAL | `prodamus_service.py` |

---

## Приложение: предварительные находки, ОПРОВЕРГНУТЫЕ верификацией (не заводить заново)
- **Rate-limit не покрывает admin** — неверно: глобальный дефолт `200/minute` (`rate_limit.py:6` + `main.py:122`).
- **Bare except проглатывает ошибки (payments/kinescope)** — неверно: `payments.py:296-297` логирует (`logger.exception`); except-ы в kinescope типизированы/узкие.
- **Self-referential import-циклы между сервисами** — неверно: единственный межсервисный импорт ацикличен (`kinescope_service.py:12`).
- **13 over-clientized Radix-обёрток** — не дефект: `'use client'` для примитивов Radix требуется штатно.
- **Широкий открытый CORS** — переоценено: origins — явный allowlist; wildcard только методы/заголовки (→ CONF-02, LOW).
- **Seed = CRITICAL** — переоценено: гард на non-production корректен → MED (SEC-03).
- **Дрейф моделей↔миграций** — статически не подтверждён; авторитетная проверка `alembic` не запускалась (нет БД) → отслеживать через TEST-02.
