# 05 — Тесты и CI

Дата: 2026-06-26. Окружение: Windows, Python 3.14 (глобальный, без `backend/venv`), Node 25 / npm 11.

## Baseline quality gates (фактические результаты)

| Гейт | Команда | Результат |
|---|---|---|
| Backend lint | `ruff check backend/app backend/tests` | ✅ **PASS, 0 ошибок** (локально ruff 0.15.9) |
| Backend tests | `pytest backend/tests` | ⛔ **НЕ ЗАПУЩЕНО В ОКРУЖЕНИИ** — нет доступной PostgreSQL; ошибка инициализации `Could not parse SQLAlchemy URL` при импорте `conftest.py` (нет `psql`, БД `nails_course`/`test_nails_course` не подняты) |
| Alembic | `alembic upgrade head` | ⛔ **НЕ ЗАПУЩЕНО** — та же причина (нет БД) |
| Frontend lint | `npm run lint` | ✅ **PASS** — 0 errors, **3 warnings** (см. FE-01) |
| Frontend build | `npm run build` | ✅ **PASS** — Next 16.1.4 Turbopack, 18 маршрутов, compiled successfully |

> Результаты pytest/alembic **не выдуманы**: в этом окружении они невоспроизводимы. В CI они исполняются на сервисе PostgreSQL 15 (`ci.yml`).

### ⚠️ Несоответствие версий инструментов (DEP-02)
`requirements.txt` пинит `ruff==0.9.4`, `fastapi==0.115.6`, `pydantic==2.10.5`, `sqlalchemy==2.0.37`, `alembic==1.14.1`, `pytest==8.3.4`. В машинном (глобальном) окружении установлены более новые: ruff 0.15.9, fastapi 0.136, alembic 1.18.4, pytest 8.4.2. Локальный `ruff PASS` получен на **другой** версии, чем пинит CI. Нет выделенного venv → backend-зависимости живут в глобальном Python. Риск: «у меня проходит» ≠ CI. Рекомендация (DEP-02): venv из `requirements.txt`, выровнять версии, рассмотреть lock.

## CI (`.github/workflows/ci.yml`)
- **Backend job**: PostgreSQL 15 service → создать `test_nails_course` → `ruff check` → `alembic upgrade head` → `pytest -v`. PYTHONPATH=backend.
- **Frontend job**: Node 20, `npm ci` → `npm run lint` → `npm run build` (с `NEXT_PUBLIC_*`).
- ### CI-01 — Нет `npm test` на фронте · LOW/MED · осознанное решение. UI-регрессии ловятся lint+build+backend pytest (CLAUDE.md:50). Playwright доступен в окружении — кандидат на e2e в post-MVP.

## Покрытие тестами (`backend/tests/`, ~46 тестов в 7 файлах + conftest)
Покрыто: auth, courses/modules/lessons/progress, purchases (вебхук, идемпотентность, подпись, создание юзера, сбой письма), kinescope + kinescope_drm (JWT/DRM), admin_bootstrap, production_hardening.

### TEST-01 — Непокрытые роутеры · MED · чистый рефакторинг (добавление тестов)
Без тестов: `admin.py` (крупный CRUD, бизнес-критичный), `admin_landing.py`, `landing.py`, `upload.py`, `bot/`. Приоритет — `admin.py`.

### TEST-02 — Дрейф «схема тестов vs миграции» · MED · чистый рефакторинг
`conftest.py` строит схему через `Base.metadata.create_all`, CI применяет Alembic (`ci.yml`). Расхождение models↔migrations всплывёт только на шаге `alembic upgrade head` в CI. Рекомендация: добавить шаг/тест паритета (например, `alembic check` или автоген-диф == пусто). Уже отмечено в `CODEBASE.md:57`.

## Stray-файлы (все **отслеживаются в HEAD**, не gitignored — подтверждено `git ls-tree -r HEAD`)
| Файл | Что это | Риск |
|---|---|---|
| `test-login.txt` | плейнтекст-учётки | SEC-01 (HIGH) |
| `backend/test_courses.py` | хардкод пароля БД + деструктивный UPDATE | SEC-02 (HIGH) |
| `backend/check_lesson_db.py` | debug-скрипт (читает урок по UUID, дефолтный UUID в коде `:65`) | DEBT-01 (LOW) |
| `backend/test_payment.py` | дев-скрипт, `requests` → localhost:8000 | DEBT-01 (LOW) |
| `backend/run_test.bat` | bat-обёртка для `test_courses.py` | DEBT-01 (LOW) |

Дубля с `backend/tests/` нет (там pytest + httpx AsyncClient). Это дев-артефакты, которые не должны быть в репо. Примечание: предыдущий обзор ошибочно счёл `run_test.bat` отсутствующим — файл присутствует.
