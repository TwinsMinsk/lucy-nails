# ops

**Parent context:** `../AGENTS.md`
**Generated:** 2026-10-30 · **Updated:** 2026-10-30

## Purpose

Инфраструктурные конфиги без прикладного кода: образ backup-job, init-скрипт локального PostgreSQL и TOML-настройки Railway для сервисов, которых нет в корневом `railway.toml` (outbox worker и backup cron). Логика бэкапа живёт в [`scripts/ops/`](../scripts/ops/), процедуры — в [`Docs/04_Setup_Ops/`](../Docs/04_Setup_Ops/).

## Key Files

| File | Description |
|------|-------------|
| [`backup/Dockerfile`](backup/Dockerfile) | Образ на `postgres:17` (даёт `pg_dump`, `pg_restore`, `psql`) плюс `awscli`, `ca-certificates`, `python3`. Копирует `scripts/ops/backup_postgres.py` и `restore_postgres.py` в `/app`; `CMD` запускает backup в `/tmp/backups`. Контекст сборки — корень репозитория. `AWS_*_CHECKSUM_*=when_required` отключает заголовки CRC64NVME, которые `aws-cli` 2.23+ шлёт по умолчанию |
| [`postgres/init/01-test-database.sql`](postgres/init/01-test-database.sql) | Идемпотентно создаёт `test_nails_course` через `\gexec` (нужен `psql`) |
| [`railway/backup.toml`](railway/backup.toml) | Backup cron: builder `DOCKERFILE`, `dockerfilePath = "ops/backup/Dockerfile"`, тот же старт, что `CMD` образа, `cronSchedule = "0 1 * * *"`, `restartPolicyType = "NEVER"` |
| [`railway/worker.toml`](railway/worker.toml) | Outbox worker: builder `RAILPACK`, `pip install -r requirements.lock`, старт `python -m app.workers.outbox`, `ON_FAILURE` до 10 перезапусков. Пути заданы относительно корня сервиса `/backend` |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `backup/` | Образ для запуска `scripts/ops/*` |
| `postgres/init/` | SQL для `/docker-entrypoint-initdb.d` локального контейнера |
| `railway/` | Config-файлы сервисов Railway, которые не описаны в корневом `railway.toml` |

## For AI Agents

### Working In This Directory

- **`railway.toml`.** Корневой файл описывает только `[service.backend]` и `[service.frontend]` и на `ops/railway/` не ссылается; рядом есть `backend/railway.toml` и `frontend/railway.toml`. Привязка TOML к сервису задаётся в настройках Railway, в репозитории её нет. Ожидаемые значения — в таблице [`LAUNCH_OPERATIONS.md`](../Docs/04_Setup_Ops/LAUNCH_OPERATIONS.md): worker — root `/backend`, config `/ops/railway/worker.toml`; backup — root `/`, config `/ops/railway/backup.toml`.
- **Что доказывают TOML.** По `LAUNCH_OPERATIONS.md` эти файлы описывают задуманные настройки и не подтверждают действующие; там же описаны отказ от Config as Code и дата отключения. Перед правкой свериться с этим документом.
- **`compose.dev.yml`.** Монтирует `postgres/init/` в `/docker-entrypoint-initdb.d` (read-only). Скрипт выполняется только при первой инициализации volume `lucy_postgres17_data`; для уже существующего volume — `backend/scripts/create_test_db.py` или [`postgresql_setup.md`](../Docs/04_Setup_Ops/postgresql_setup.md). CI этот файл не использует и создаёт БД сам.
- **`scripts/ops`.** Перенос или переименование `backup_postgres.py`/`restore_postgres.py` ломает `COPY` в Dockerfile и импорты в `backend/tests/test_backup_bundle.py`. Восстановление в контейнере — `python3 /app/restore_postgres.py`.
- **Версия PostgreSQL.** `postgres:17` задан в Dockerfile, `compose.dev.yml` и `.github/workflows/ci.yml`; менять согласованно. [`BACKUP_RESTORE.md`](../Docs/04_Setup_Ops/BACKUP_RESTORE.md) ещё упоминает закрепление на `postgres:15` и фиксирует несовместимость клиента 17 с сервером 15, а `STAGING.md` указывает PostgreSQL 15.
- **Переменные backup.** В TOML их нет, они задаются окружением сервиса: `DATABASE_URL`, `BACKUP_S3_URI`, `BACKUP_REQUIRE_S3`, `BACKUP_S3_ENDPOINT`, `BACKUP_S3_SSE`, `BACKUP_S3_KMS_KEY_ID`, `BACKUP_RETENTION_DAYS`, `BACKUP_REQUIRE_UPLOADS`, `BACKUP_UPLOADS_DIR` или `BACKUP_UPLOADS_URL` с `BACKUP_UPLOADS_TOKEN`, `BACKUP_UPLOADS_MARKER`, `BACKUP_HEARTBEAT_URL`, AWS credentials, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_OWNER_CHAT_ID`.
- **Значения по умолчанию.** Без `BACKUP_REQUIRE_S3=true` и `BACKUP_S3_URI` job завершается с `status=ok`, а архив остаётся только в `/tmp/backups` контейнера: volume в `backup.toml` не описан. Полный backup с uploads требует настроек из `LAUNCH_OPERATIONS.md`.
- **Безопасность.** Секреты в Dockerfile и TOML не записывать. Backup, restore и изменения в Railway — только по явному запросу. Restore — только в пустую отдельную БД; `--allow-production` — только в объявленном инциденте.
- **`.dockerignore`.** Его нет, поэтому локальная сборка передаёт демону весь корень репозитория, включая локальные `.env` и тяжёлые медиа, хотя в образ попадают только два файла.

### Testing Requirements

- Автотестов на сами конфиги нет: CI не собирает образ и не проверяет TOML. Логику CLI покрывает `python -m pytest backend/tests/test_backup_bundle.py` из корня репозитория.
- Ручная проверка: `docker compose -f compose.dev.yml config`, `docker build -f ops/backup/Dockerfile .` из корня. Restore drill — по `BACKUP_RESTORE.md` и `LAUNCH_OPERATIONS.md`, по запросу пользователя.

### Common Patterns

- TOML — секции `[build]` и `[deploy]`, как в `backend/railway.toml`.
- Команды продублированы: `startCommand` в `backup.toml` повторяет `CMD` Dockerfile, а `worker.toml` — строку `worker:` в `backend/Procfile`. Менять вместе.
- Init SQL — числовой префикс в имени и идемпотентность (`WHERE NOT EXISTS`).

## Dependencies

### Internal

- [`scripts/ops/backup_postgres.py`](../scripts/ops/backup_postgres.py), [`scripts/ops/restore_postgres.py`](../scripts/ops/restore_postgres.py), [`backend/tests/test_backup_bundle.py`](../backend/tests/test_backup_bundle.py)
- [`compose.dev.yml`](../compose.dev.yml), [`railway.toml`](../railway.toml), [`backend/railway.toml`](../backend/railway.toml), [`frontend/railway.toml`](../frontend/railway.toml), [`backend/Procfile`](../backend/Procfile)
- [`backend/app/workers/outbox.py`](../backend/app/workers/outbox.py), [`backend/requirements.lock`](../backend/requirements.lock)
- [`LAUNCH_OPERATIONS.md`](../Docs/04_Setup_Ops/LAUNCH_OPERATIONS.md), [`BACKUP_RESTORE.md`](../Docs/04_Setup_Ops/BACKUP_RESTORE.md), [`STAGING.md`](../Docs/04_Setup_Ops/STAGING.md), [`RELEASE_CHECKLIST.md`](../Docs/04_Setup_Ops/RELEASE_CHECKLIST.md), [`RUNBOOKS.md`](../Docs/04_Setup_Ops/RUNBOOKS.md)

### External

- Docker: образ `postgres:17`, Debian-пакет `awscli`
- Railway: builders `DOCKERFILE` и `RAILPACK`, cron
- S3-совместимое хранилище и Telegram Bot API — для выгрузки backup и alert из `scripts/ops/backup_postgres.py`

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
