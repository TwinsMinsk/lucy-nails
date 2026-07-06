# 06 — Документация и техдолг

Дата: 2026-06-26.

## Дрейф документации

### DOCS-01 — `Docs/ARCHITECTURE.md` отстаёт от кода · LOW · чистый рефакторинг (docs)
Детальный документ (573 строки: ER-диаграмма, список сервисов/эндпоинтов) не упоминает реально существующие:
- Модель `gallery` (`models/gallery.py`) — нет в ER-диаграмме.
- Сервисы `email_service`, `kinescope_jwt_service`, `admin_bootstrap`, `lesson_service` — нет в списке сервисов.
- Эндпоинты `/api/admin/landing/*`, `/api/upload/*`, `/api/integrations/kinescope/drm/authorize` — не описаны.

`CODEBASE.md` — намеренно высокоуровневая карта (использует обобщения и «…»), поэтому дрейф там минимален; ссылка на `Docs/06_Tracking/REFACTORING_ROADMAP.md` (`CODEBASE.md:61`) **валидна** (файл существует). `.agent/` и `GEMINI.md` — наследие, помечены как справка.

Рекомендация: один проход синхронизации ARCHITECTURE.md (модель `gallery`, 4 сервиса, 3 группы эндпоинтов). Уже стоит в backlog рефакторинга (`CODEBASE.md:62`).

## Здоровье зависимостей (список, БЕЗ апгрейдов в этой фазе)

### DEP-01 — Frontend: 10 уязвимостей npm · MED · меняет поведение (апгрейд)
`npm audit`: 4 high (picomatch ReDoS/инъекция — транзитивно через `tinyglobby`/`next`), 5 moderate (postcss XSS `<8.5.10`), 1 low. `npm audit fix` закрывает часть; полный фикс тянет `next@16.2.9` (вне диапазона). `next 16.1.4→16.2.9` — security-relevant patch. Запланировать апгрейд отдельным пунктом с прогоном build+lint.

### DEP-02 — Backend: пины `requirements.txt` отстают + нет venv · LOW/MED · чистый рефакторинг
Пины (`fastapi 0.115.6`, `pydantic 2.10.5`, `sqlalchemy 2.0.37`, `alembic 1.14.1`, `ruff 0.9.4`, `pytest 8.3.4`) старше установленного глобально (fastapi 0.136, ruff 0.15.9, …). Локальные проверки идут на иных версиях, чем CI. + потенциально неиспользуемые backend-депы: `firecrawl-py==4.22.0`, возможно `rich` (нет ссылок в `backend/app` — проверить против `scripts/`). Рекомендация: venv из requirements, ревизия лишних депов.

## Зафиксированный (известный) техдолг — сверка с реальностью
Документы `CODEBASE.md:52-57`, `Docs/06_Tracking/TASKS.md`, `POST_MVP_HARDENING.md`, `REFACTORING_ROADMAP.md` уже фиксируют: seed+CORS, отсутствие `npm test`, крупные `admin.py`/`api.ts`, дрейф схемы тестов, Redis-rate-limit, refresh-token rotation, e2e-тесты. Аудит подтверждает эти пункты и **добавляет** не зафиксированные ранее:
- Закоммиченные креды `test-login.txt` (SEC-01) и пароль БД в `test_courses.py` (SEC-02) — **новое, HIGH**.
- Блокирующий I/O в `upload.py` (BE-01), `datetime.utcnow()` (BE-02), несоответствие версий депов (DEP-02), npm-уязвимости (DEP-01).

## TODO/FIXME
- В `backend/app` и `frontend/src` маркеров TODO/FIXME практически нет — долг ведётся в трекерах, а не в коде. Это здоровый признак.

## Stray-файлы → DEBT-01
5 дев-артефактов отслеживаются в HEAD (см. [05-tests-ci.md](05-tests-ci.md)). 2 из них несут секреты (SEC-01/02), 3 — просто мусор (`check_lesson_db.py`, `test_payment.py`, `run_test.bat`). Удалить/перенести в `scripts/`.
