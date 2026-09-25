# Backup и восстановление PostgreSQL

**Цели:** RPO ≤ 24 часа, RTO ≤ 4 часа.

## Расписание и хранение

- Ежедневно: custom-format `pg_dump`, локальный SHA-256 и загрузка в отдельное S3-совместимое хранилище.
- Еженедельно: сохранить отдельную immutable/versioned копию минимум на 90 дней.
- S3 bucket должен быть не в том же Railway project, с versioning, lifecycle и отдельными credentials только на запись/чтение backup prefix.
- Шифрование: `AES256` по умолчанию либо `aws:kms` через `BACKUP_S3_SSE` и `BACKUP_S3_KMS_KEY_ID`.

Cron-контейнер собирается из `ops/backup/Dockerfile` и запускает `scripts/ops/backup_postgres.py`. Переменные: `DATABASE_URL`, `BACKUP_S3_URI`, AWS credentials, опционально `BACKUP_S3_ENDPOINT`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_OWNER_CHAT_ID`.

Успех подтверждается JSON-строкой `status=ok`, checksum и наличием `.dump` + `.sha256` в bucket. При ошибке скрипт завершается с кодом 1 и отправляет owner alert.

## Restore drill

Восстановление всегда выполняется сначала в отдельную БД, имя которой содержит `restore`, `drill`, `test` или `staging`:

```powershell
$env:RESTORE_DATABASE_URL = "postgresql://.../lucy_restore_drill"
python scripts/ops/restore_postgres.py s3://bucket/prefix/lucy-nails-YYYYMMDD.dump --confirm-database lucy_restore_drill
```

Скрипт проверяет SHA-256 и точное имя БД. Для любой БД без безопасного маркера требуется явный `--allow-production`; использовать его можно только в объявленном инциденте после двойной проверки URL.

После restore проверить:

1. `alembic_version` совпадает с релизом.
2. Количество пользователей, заказов, покупок, доступов и сертификатов согласовано с источником.
3. Нет успешной покупки без entitlement.
4. API стартует с checkout выключенным.
5. В журнал инцидента внесены времена начала/окончания и фактические RPO/RTO.

26.08.2026 локальный drill через готовый Docker-образ: архив 81 928 байт, SHA-256 `74fc2ca2eb1f6c7a4c22225b9785b6975b9888c3504c09f0346209e88f5af0bb`; восстановлено 28 таблиц, Alembic head `1b8c9d0e1f2a`. Первый прогон обнаружил несовместимость клиента PostgreSQL 17 с сервером 15, после чего образ был закреплён на `postgres:15` и повторный drill прошёл. Временная БД удалена. Это доказывает локальную процедуру, но не заменяет staging/S3 drill после создания внешних ресурсов.
