# Staging-контур Lucy Nails

**Дата:** 26.08.2026
**Статус:** конфигурация подготовлена; внешние ресурсы должен создать владелец аккаунтов.

Staging — отдельное окружение без production-данных. Нельзя подключать staging-приложение к production PostgreSQL, Redis, Telegram-группе или боевой форме Prodamus.

## Топология

В отдельном Railway environment создаются семь сервисов:

1. `frontend-staging` — Next.js.
2. `api-staging` — FastAPI, команда из `railway.toml`.
3. `worker-staging` — `python -m app.workers.outbox`.
4. `bot-staging` — `python -m app.bot.main`.
5. PostgreSQL 15 — только staging.
6. Redis — только staging, общий для всех экземпляров API.
7. `backup-staging` — Dockerfile `ops/backup/Dockerfile`, ежедневный cron.

## Обязательные отличия от production

- `ENVIRONMENT=staging`, `DEBUG=false`.
- Отдельные `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, `MFA_ENCRYPTION_KEY`.
- `PRODAMUS_DEMO_MODE=1`, отдельный demo webhook на staging API.
- Отдельный Resend test-domain/получатель; запрещена рассылка реальным ученикам.
- Отдельные Telegram bot, owner chat и support group.
- Отдельные Kinescope API token и DRM credentials; можно использовать копии видео без персональных данных.
- `FRONTEND_URL`, `BACKEND_URL`, `CORS_ORIGINS`, `TRUSTED_HOSTS`, `COOKIE_DOMAIN` указывают только staging-домены.
- `FORWARDED_ALLOW_IPS` содержит только подтверждённые CIDR/IP edge-proxy; wildcard `*` запрещён. Проверить, что поддельные `X-Forwarded-For`/`CF-Connecting-IP` не меняют ключ rate limit.
- `NEXT_PUBLIC_YANDEX_METRIKA_ID` пустой либо отдельный тестовый счётчик.

## Порядок развёртывания

1. Создать БД/Redis и задать environment variables без копирования секретов в Git.
2. Развернуть API, выполнить `alembic upgrade head`, проверить единственную head.
3. Развернуть worker и bot отдельными процессами.
4. Развернуть frontend и проверить cookie/CSRF между staging-поддоменами.
5. Настроить demo webhook Prodamus и DRM authorization backend Kinescope.
6. Запустить `scripts/smoke-production.ps1` на staging URL.
7. Пройти гостевую и авторизованную demo-покупку, повтор webhook, активацию, урок, сертификат, refund workflow.
8. Проверить backup и восстановить его в отдельную БД `lucy_restore_drill`.

Production deploy запрещён, пока staging smoke не приложен к release checklist с датой, исполнителем и ссылками на доказательства.
