<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-07-06 | Updated: 2026-07-06 -->

# Docs

## Purpose

Документация проекта: продуктовые требования, техническая архитектура, ops-гайды по разработке и деплою, документы по фичам и истории фаз, трекеры задач/техдолга, справочники интеграций и point-in-time аудиты. [`README.md`](README.md) в этом каталоге — короткий индекс по всем разделам ниже.

## Key Files

| File | Description |
|------|-------------|
| [`README.md`](README.md) | Индекс/навигация по `Docs/` |
| [`PRD.md`](PRD.md) | Продуктовые требования, v1.2, статус «Утверждён» |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Техническая архитектура, схема данных, API и интеграции (с mermaid-диаграммами), v1.2 |
| [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) | Исторический план реализации по фазам (на основе PRD/ARCHITECTURE v1.x) |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| [`02_Features/`](02_Features/) | Документы по фичам: Kinescope-интеграция (mock mode), frontend Kinescope, тестирование видео-плеера, auth-интеграция и сидинг БД, загрузка баннеров |
| [`03_Admin/`](03_Admin/) | Гайды по админ-панели: ручная выдача доступа, привязка данных фронтенда/админки |
| [`04_Setup_Ops/`](04_Setup_Ops/) | Процессные документы: [`DEVELOPMENT_WORKFLOW.md`](04_Setup_Ops/DEVELOPMENT_WORKFLOW.md) (главный процессный док — окружения, `.env`, Git, Railway), [`DEPLOY_GUIDE.md`](04_Setup_Ops/DEPLOY_GUIDE.md), [`RELEASE_CHECKLIST.md`](04_Setup_Ops/RELEASE_CHECKLIST.md), [`dev_scripts.md`](04_Setup_Ops/dev_scripts.md), [`postgresql_setup.md`](04_Setup_Ops/postgresql_setup.md), [`create_database.md`](04_Setup_Ops/create_database.md) |
| [`05_Phases_History/`](05_Phases_History/) | Исторические отчёты завершённых фаз (Phase 1–4.1, обновления галереи/навигации/контента уроков) — контекст, не источник текущих правил |
| [`06_Tracking/`](06_Tracking/) | [`TASKS.md`](06_Tracking/TASKS.md) (текущий трекер), [`POST_MVP_HARDENING.md`](06_Tracking/POST_MVP_HARDENING.md), [`REFACTORING_ROADMAP.md`](06_Tracking/REFACTORING_ROADMAP.md), `PROGRESS_REPORT.md`, [`CONTENT.md`](06_Tracking/CONTENT.md) (структура/контент курса, черновик) |
| [`integrations/`](integrations/) | Справочники: [`KINESCOPE_API.md`](integrations/KINESCOPE_API.md), [`KINESCOPE_AUTH_BACKEND.md`](integrations/KINESCOPE_AUTH_BACKEND.md), [`PRODAMUS_API.md`](integrations/PRODAMUS_API.md) |
| [`audit/`](audit/) | Аудиты на конкретную дату: [`landing-copy-audit-2026-05-10.md`](audit/landing-copy-audit-2026-05-10.md), [`audit-2026-06-26/`](audit/audit-2026-06-26/) (00-summary + тематические отчёты 01–06 + `BACKLOG.md`) |

## For AI Agents

### Working In This Directory

- Порядок чтения документации перед существенными изменениями (см. корневой [`CLAUDE.md`](../CLAUDE.md)): [`AGENTS.md`](../AGENTS.md) → [`CODEBASE.md`](../CODEBASE.md) → [`04_Setup_Ops/DEVELOPMENT_WORKFLOW.md`](04_Setup_Ops/DEVELOPMENT_WORKFLOW.md) → [`ARCHITECTURE.md`](ARCHITECTURE.md) → точечные [`.cursor/rules/*.mdc`](../.cursor/rules/).
- Правило обновления из [`README.md`](README.md): если меняется поведение продукта, API, схема БД, запуск или деплой — обновлять ближайший тематический документ и при необходимости [`06_Tracking/TASKS.md`](06_Tracking/TASKS.md); `README.md`/`AGENTS.md`/`CODEBASE.md` в корне остаются краткими точками входа со ссылками сюда.
- [`05_Phases_History/`](05_Phases_History/) — архив завершённых фаз; не редактировать задним числом, не путать с текущими правилами.
- [`audit/`](audit/) — снимки на дату аудита (read-only отчёты); прошлые аудиты не переписывать, для нового — новый файл/папка с датой.
- Вложенные `AGENTS.md` в подкаталогах `Docs/` намеренно не создаются — вся навигация здесь и в [`README.md`](README.md).

### Testing Requirements

- Автоматических проверок контента нет; при переносе/переименовании файлов вручную сверять относительные ссылки между документами.
- [`audit/landing-copy-audit-2026-05-10.md`](audit/landing-copy-audit-2026-05-10.md) опирается на `scripts/promo/output/<slug>/transcript_full_text.txt` как источник истины для копии лендинга — при обновлении транскриптов сверять актуальность аудита.

### Common Patterns

- Заголовок с метаданными `**Версия:**` / `**Дата:**` / `**Статус:**` — у основных документов (PRD/ARCHITECTURE/IMPLEMENTATION_PLAN) и у отчётов по фичам/фазам (`02_Features/`, `05_Phases_History/`, обычно `**Статус:** ✅ Завершено`).
- Задачи и чеклисты — маркеры `[ ]` / `[/]` / `[x]` (см. [`06_Tracking/TASKS.md`](06_Tracking/TASKS.md)).
- Ссылки между документами — относительные, через `/`.

## Dependencies

### Internal

- [`CLAUDE.md`](../CLAUDE.md), [`AGENTS.md`](../AGENTS.md), [`CODEBASE.md`](../CODEBASE.md) в корне репозитория
- [`backend/app/core/config.py`](../backend/app/core/config.py), `backend/app/services/*`, `backend/alembic/versions/` — описываются в `ARCHITECTURE.md`/`integrations/`
- `frontend/src/app/*`, `frontend/components.json` — описываются в `02_Features/`, `ARCHITECTURE.md`
- [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — проверки, на которые ссылаются `DEVELOPMENT_WORKFLOW.md`/`RELEASE_CHECKLIST.md`

### External

- Kinescope, Prodamus, Telegram — внешние интеграции, описанные в `integrations/` и `02_Features/`
- Railway — платформа деплоя, [`DEPLOY_GUIDE.md`](04_Setup_Ops/DEPLOY_GUIDE.md)

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
