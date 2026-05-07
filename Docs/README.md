# Документация Lucy-nails

Короткий индекс, чтобы не искать нужный документ по всему репозиторию.

## Главные документы

- [`PRD.md`](PRD.md) — продуктовые требования и MVP scope.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — техническая архитектура, схема данных, API и интеграции.
- [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) — исторический план реализации.

## Разработка и эксплуатация

- [`04_Setup_Ops/DEVELOPMENT_WORKFLOW.md`](04_Setup_Ops/DEVELOPMENT_WORKFLOW.md) — окружения, `.env`, локальный запуск, проверки, Git и Railway.
- [`04_Setup_Ops/DEPLOY_GUIDE.md`](04_Setup_Ops/DEPLOY_GUIDE.md) — деплой.
- [`04_Setup_Ops/RELEASE_CHECKLIST.md`](04_Setup_Ops/RELEASE_CHECKLIST.md) — go/no-go чеклист релиза.
- [`04_Setup_Ops/dev_scripts.md`](04_Setup_Ops/dev_scripts.md) — скрипты разработки.
- [`04_Setup_Ops/postgresql_setup.md`](04_Setup_Ops/postgresql_setup.md), [`04_Setup_Ops/create_database.md`](04_Setup_Ops/create_database.md) — PostgreSQL.

## Фичи и интеграции

- [`02_Features/`](02_Features/) — авторизация, Kinescope, видео-плеер, загрузки и другие фичи.
- [`03_Admin/`](03_Admin/) — админ-панель и ручное управление доступом.
- [`integrations/`](integrations/) — справочные материалы по Kinescope и Prodamus.

## Трекинг и история

- [`06_Tracking/TASKS.md`](06_Tracking/TASKS.md) — текущий трекер задач.
- [`06_Tracking/POST_MVP_HARDENING.md`](06_Tracking/POST_MVP_HARDENING.md) — backlog hardening/refactor после MVP.
- [`06_Tracking/REFACTORING_ROADMAP.md`](06_Tracking/REFACTORING_ROADMAP.md) — программа наведения порядка по docs, backend, frontend и CI.
- [`06_Tracking/CONTENT.md`](06_Tracking/CONTENT.md) — контент курса.
- [`05_Phases_History/`](05_Phases_History/) — история завершённых фаз и отчёты.

## Правило обновления

Если меняется поведение продукта, API, схема БД, запуск или деплой, обновляйте ближайший тематический документ и при необходимости `06_Tracking/TASKS.md`. `README.md`, `AGENTS.md` и `CODEBASE.md` должны оставаться краткими входными точками со ссылками сюда.
