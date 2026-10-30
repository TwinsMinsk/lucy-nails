# Docs

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose

Документация проекта: продуктовые требования, техническая архитектура, ops-гайды по разработке и деплою, документы по фичам и истории фаз, трекеры задач/техдолга, справочники интеграций и point-in-time аудиты. [`README.md`](README.md) в этом каталоге — короткий индекс разделов; `LAUNCH_OPERATIONS.md`, `SECRET_SCAN_TRIAGE.md` и `LAUNCH_READINESS_IMPLEMENTATION.md` в нём не перечислены, полный список — ниже.

## Key Files

| File | Description |
|------|-------------|
| [`README.md`](README.md) | Индекс/навигация по `Docs/` |
| [`PRD.md`](PRD.md) | Текущий production scope, v2.0, и go-live критерии |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Текущая v2.0 архитектура commerce/access/RBAC/outbox/analytics/operations. Датирована 26.08.2026: Alembic head и версию PostgreSQL сверять с `backend/alembic/versions/` и `compose.dev.yml` |
| [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) | Архив: первоначальный план реализации от 22.01.2026 (на основе PRD/ARCHITECTURE v1.2), не текущий backlog |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| [`02_Features/`](02_Features/) | Документы по фичам: Kinescope-интеграция (mock mode), frontend Kinescope, тестирование видео-плеера, auth-интеграция и сидинг БД, загрузка баннеров. `Kinescope.md` и `FRONTEND_KINESCOPE.md` датированы 23.01.2026; актуальный DRM-контур — [`integrations/KINESCOPE_AUTH_BACKEND.md`](integrations/KINESCOPE_AUTH_BACKEND.md) |
| [`03_Admin/`](03_Admin/) | Гайды по админ-панели: ручная выдача доступа, привязка данных фронтенда/админки |
| [`04_Setup_Ops/`](04_Setup_Ops/) | Процессные документы: [`DEVELOPMENT_WORKFLOW.md`](04_Setup_Ops/DEVELOPMENT_WORKFLOW.md) (главный процессный док — окружения, `.env`, Git, Railway), [`DEPLOY_GUIDE.md`](04_Setup_Ops/DEPLOY_GUIDE.md), [`RELEASE_CHECKLIST.md`](04_Setup_Ops/RELEASE_CHECKLIST.md) (go/no-go с доказательствами), [`STAGING.md`](04_Setup_Ops/STAGING.md) (изолированный staging-контур), [`LAUNCH_OPERATIONS.md`](04_Setup_Ops/LAUNCH_OPERATIONS.md) (08.10.2026: staging, мониторинг, полный backup с uploads, restore, приёмка), [`BACKUP_RESTORE.md`](04_Setup_Ops/BACKUP_RESTORE.md) (RPO/RTO, расписание, restore drill), [`RUNBOOKS.md`](04_Setup_Ops/RUNBOOKS.md) (инциденты: платёж, webhook, доставка, видео, возврат, откат, утечка секрета, restore), [`SECRET_SCAN_TRIAGE.md`](04_Setup_Ops/SECRET_SCAN_TRIAGE.md) (триаж находок Gitleaks и границы исключений), [`dev_scripts.md`](04_Setup_Ops/dev_scripts.md), [`postgresql_setup.md`](04_Setup_Ops/postgresql_setup.md), [`create_database.md`](04_Setup_Ops/create_database.md) |
| [`05_Phases_History/`](05_Phases_History/) | Исторические отчёты завершённых фаз (Phase 1–4.1, обновления галереи/навигации/контента уроков) — контекст, не источник текущих правил |
| [`06_Tracking/`](06_Tracking/) | [`TASKS.md`](06_Tracking/TASKS.md) (текущий трекер, обновлён 26.08.2026), [`LAUNCH_READINESS_IMPLEMENTATION.md`](06_Tracking/LAUNCH_READINESS_IMPLEMENTATION.md) (реализация и проверки launch plan, 08.10.2026), [`POST_MVP_HARDENING.md`](06_Tracking/POST_MVP_HARDENING.md) (исторический backlog, статусы — в `TASKS.md`), [`REFACTORING_ROADMAP.md`](06_Tracking/REFACTORING_ROADMAP.md), [`PROGRESS_REPORT.md`](06_Tracking/PROGRESS_REPORT.md) (история фаз 0–1), [`CONTENT.md`](06_Tracking/CONTENT.md) (контент курса, сверка с публичным production API на 26.08.2026), [`YANDEX_METRIKA.md`](06_Tracking/YANDEX_METRIKA.md) (счётчик, цели, настройки, проверка) |
| [`integrations/`](integrations/) | Справочники: [`KINESCOPE_API.md`](integrations/KINESCOPE_API.md), [`KINESCOPE_AUTH_BACKEND.md`](integrations/KINESCOPE_AUTH_BACKEND.md), [`PRODAMUS_API.md`](integrations/PRODAMUS_API.md) |
| [`audit/`](audit/) | Point-in-time аудиты: `audit-2026-06-26/`, `audit-2026-07-06/`, [`landing-copy-audit-2026-05-10.md`](audit/landing-copy-audit-2026-05-10.md); текущий источник go/no-go — [`production-readiness-2026-08-26/`](audit/production-readiness-2026-08-26/) |

## For AI Agents

### Working In This Directory

- Порядок чтения документации перед существенными изменениями (см. корневой [`CLAUDE.md`](../CLAUDE.md)): [`AGENTS.md`](../AGENTS.md) → [`CODEBASE.md`](../CODEBASE.md) → [`04_Setup_Ops/DEVELOPMENT_WORKFLOW.md`](04_Setup_Ops/DEVELOPMENT_WORKFLOW.md) → [`ARCHITECTURE.md`](ARCHITECTURE.md) → точечные [`.cursor/rules/*.mdc`](../.cursor/rules/).
- Правило обновления из [`README.md`](README.md): если меняется поведение продукта, API, схема БД, запуск или деплой — обновлять ближайший тематический документ и при необходимости [`06_Tracking/TASKS.md`](06_Tracking/TASKS.md); `README.md`/`AGENTS.md`/`CODEBASE.md` в корне остаются краткими точками входа со ссылками сюда.
- [`05_Phases_History/`](05_Phases_History/) — архив завершённых фаз; не редактировать задним числом, не путать с текущими правилами.
- [`audit/`](audit/) — снимки на дату аудита (read-only отчёты); прошлые аудиты не переписывать, для нового — новый файл/папка с датой.
- Вложенные `AGENTS.md` в подкаталогах `Docs/` намеренно не создаются — вся навигация здесь и в [`README.md`](README.md).
- Документы `04_Setup_Ops/` расходятся по дате. `LAUNCH_OPERATIONS.md` (08.10.2026) новее `BACKUP_RESTORE.md` и `STAGING.md` (26.08.2026). `BACKUP_RESTORE.md` описывает образ на PostgreSQL 15 и бэкап только `.dump`, `STAGING.md` — PostgreSQL 15, а `ops/backup/Dockerfile`, `compose.dev.yml` и CI используют PostgreSQL 17. При расхождении верить файлам репозитория.
- В `04_Setup_Ops/` команды писать в формате PowerShell, при смене env синхронизировать `.env.example` и `frontend/.env.example` (правило [`.cursor/rules/ops-setup-docs.mdc`](../.cursor/rules/ops-setup-docs.mdc)).
- В примерах API — только placeholder, без реальных ключей. `.gitleaks.toml` разрешает curl-примеры из `integrations/KINESCOPE_API.md` по точному тексту и пути, а `.gitleaksignore` — исторические находки по пути и строке; правка таких примеров может вызвать новую находку (см. [`SECRET_SCAN_TRIAGE.md`](04_Setup_Ops/SECRET_SCAN_TRIAGE.md)).

### Testing Requirements

- Автоматических проверок содержания нет, кроме secret scan: [`.github/workflows/security.yml`](../.github/workflows/security.yml) прогоняет Gitleaks по всему репозиторию, включая `Docs/`. При переносе/переименовании файлов вручную сверять относительные ссылки между документами.
- [`audit/landing-copy-audit-2026-05-10.md`](audit/landing-copy-audit-2026-05-10.md) опирается на `scripts/promo/output/<slug>/transcript_full_text.txt` как источник истины для копии лендинга — при обновлении транскриптов сверять актуальность аудита.

### Common Patterns

- Заголовок с метаданными `**Версия:**` / `**Дата:**` / `**Статус:**` — у основных документов (PRD/ARCHITECTURE/IMPLEMENTATION_PLAN) и у отчётов по фичам/фазам (`02_Features/`, `05_Phases_History/`, обычно `**Статус:** ✅ Завершено`).
- Задачи и чеклисты — маркеры `[ ]` / `[/]` / `[x]` (см. [`06_Tracking/TASKS.md`](06_Tracking/TASKS.md)). В `RELEASE_CHECKLIST.md` ручной пункт `[x]` без даты, исполнителя и доказательства не считается закрытым.
- Ссылки между документами — относительные, через `/`.

## Dependencies

### Internal

- [`CLAUDE.md`](../CLAUDE.md), [`AGENTS.md`](../AGENTS.md), [`CODEBASE.md`](../CODEBASE.md) в корне репозитория
- [`backend/app/core/config.py`](../backend/app/core/config.py), `backend/app/services/*`, `backend/alembic/versions/` — описываются в `ARCHITECTURE.md`/`integrations/`
- `frontend/src/app/*`, `frontend/components.json` — описываются в `02_Features/`, `ARCHITECTURE.md`
- [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — проверки, на которые ссылаются `DEVELOPMENT_WORKFLOW.md`/`RELEASE_CHECKLIST.md`
- [`ops/`](../ops/AGENTS.md), [`scripts/ops/`](../scripts/ops/), [`scripts/load/`](../scripts/load/README.md), [`compose.dev.yml`](../compose.dev.yml) — описываются в `04_Setup_Ops/`
- [`.github/workflows/security.yml`](../.github/workflows/security.yml), [`.gitleaks.toml`](../.gitleaks.toml), [`.gitleaksignore`](../.gitleaksignore) — описываются в `SECRET_SCAN_TRIAGE.md`

### External

- Kinescope, Prodamus, Telegram — внешние интеграции, описанные в `integrations/` и `02_Features/`
- Railway — платформа деплоя, [`DEPLOY_GUIDE.md`](04_Setup_Ops/DEPLOY_GUIDE.md), [`LAUNCH_OPERATIONS.md`](04_Setup_Ops/LAUNCH_OPERATIONS.md)
- S3-совместимое хранилище для backup — [`BACKUP_RESTORE.md`](04_Setup_Ops/BACKUP_RESTORE.md); Gitleaks — [`SECRET_SCAN_TRIAGE.md`](04_Setup_Ops/SECRET_SCAN_TRIAGE.md)

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
