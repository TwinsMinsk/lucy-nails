# Production readiness tasks

> **Последнее обновление:** 26.08.2026
> **Статус:** `[ ]` open · `[/]` in progress · `[x]` verified in code/local environment
> **Приоритет:** датированный [`production-readiness audit`](../audit/production-readiness-2026-08-26/README.md) и этот файл заменяют старые MVP-проценты.

## Реализовано в `feat/production-readiness`

### Commerce и доступ

- [x] Immutable `Order` со снимком курса, тарифа, цены, валюты, срока, customer data и UTM.
- [x] Публичный status endpoint по hashed random token и честные pending/paid/help состояния.
- [x] Snapshot amount/currency validation, signed/idempotent/reordered/concurrent webhook tests.
- [x] Разделены `Purchase` и `Entitlement`; миграционный backfill существующих успешных покупок.
- [x] `PaymentEvent` с sanitized payload/hash; `RefundRequest` workflow.
- [x] Atomic payment/access/outbox transaction; `OutboxMessage`/`DeliveryAttempt`, retry/dead letter/manual resend.
- [x] Одноразовая 24-часовая activation link вместо случайного известного пароля.
- [x] DB-backed checkout kill switch из админки без deploy и с audit reason.

### Admin, команда и безопасность

- [x] Роли `owner`, `admin`, `content_manager`, `curator`, `analyst` и отрицательные permission tests.
- [x] AuditLog для административных изменений; нельзя удалить последнего owner.
- [x] Обязательная TOTP MFA owner/admin, резервные коды, revocable sessions и forced logout.
- [x] CRM: серверный поиск/фильтры/пагинация, карточка ученика, notes/tags/history.
- [x] Операционные разделы: orders/payments/refunds, entitlements, progress, certificates, notifications, system.
- [x] Content admin и Kinescope readiness: missing ID/status/duration mismatch/provider error.
- [x] Cookie/CSRF/trusted hosts/config hardening, Redis-backed rate limit, structured correlation logs без query/PII.
- [x] Runtime dependency audits: 0 известных npm/pip runtime vulnerabilities на дату проверки.

### Аналитика, consent и Telegram

- [x] PII-free first-party events, dedupe, server financial/learning events, first/last UTM.
- [x] Overview/timeseries/funnel/sources/tariffs/cohorts/progress/refund/delivery reports и admin UI.
- [x] Consent banner: necessary/analytics, versioning и withdrawal; Метрика только в public layout.
- [x] Одноразовая Telegram link, payment/access notifications, 7/3/1 reminders, expiry и support group removal.
- [x] Email и Telegram объединены общей outbox; owner operational alerts.

### Quality и эксплуатация

- [x] Python 3.11 lock-файлы; обновлены уязвимые Next/FastAPI/Starlette/JWT dependencies.
- [x] CI: Ruff, pip-audit, PostgreSQL pytest, Alembic single head + round-trip, ESLint, Vitest, npm audit, build, Playwright.
- [x] Cross-browser guest checkout E2E в desktop Chromium и mobile WebKit.
- [x] `compose.dev.yml` для PostgreSQL 15 + Redis 7.
- [x] Backup/restore tooling с checksum, S3 encryption, retention и owner alert.
- [x] Локальный restore drill: 28 таблиц, head `1b8c9d0e1f2a`, checksum подтверждён.
- [x] Staging topology, incident runbooks и staging-only k6 launch gate подготовлены.
- [x] PRD, architecture, release checklist и датированный аудит синхронизированы.

## P0 — до deploy/go-live

- [ ] Влить/развернуть ветку, выполнить миграции и проверить production config validation. Ответственный: tech owner.
- [ ] Создать изолированный staging и развернуть web/worker/bot/Redis/backup. Ответственный: infrastructure owner.
- [ ] Пройти guest + authenticated Prodamus demo E2E, повтор/перестановку webhook, activation, login, lesson, certificate и refund workflow. Ответственные: owner + tech.
- [ ] После deploy выполнить согласованный реальный платёж и возврат: доступ ≤ 60 секунд, уведомление ≤ 2 минут. Ответственные: business owner + tech.

## P1 — launch blockers

- [ ] Вручную проверить все 11 уроков: desktop Chrome/Safari, реальный iOS и Android, DRM, seek, progress, completion, тексты и изображения. Ответственный: content owner/QA.
- [ ] Проверить истечение entitlement и Telegram reminders/removal на staging с ускоренными датами. Ответственный: QA.
- [ ] Настроить отдельный versioned encrypted S3 backup и выполнить restore drill из внешней копии. Ответственный: infrastructure owner.
- [ ] Запустить k6 gate на staging; приложить p95/error rate и DB/Redis metrics. Ответственный: tech owner.
- [ ] Проверить живые Resend/SMTP, Telegram owner chat/support group, Prodamus, Kinescope DRM и failure alerts. Ответственные: owner + tech.
- [ ] Провести юридическую/бухгалтерскую проверку оферты, privacy/cookie policy, consent, refund, retention, чеков и налоговых настроек Prodamus. Ответственный: business owner.
- [ ] Проверить rollback последнего deploy и зафиксировать фактические RPO/RTO. Ответственный: infrastructure owner.

## P2 — сразу после снятия launch blockers

- [ ] Полный WCAG 2.2 AA аудит keyboard/focus/contrast/screen reader критических flows.
- [ ] Добавить Android Chromium device farm; текущий mobile automated gate использует WebKit device emulation.
- [ ] Подключить внешний uptime/error monitoring и формальные SLO для checkout/webhook/outbox.
- [ ] Автоматизировать reconciliation с Prodamus; до этого выполнять ежедневную ручную сверку.
- [ ] Разделить `frontend/src/lib/api.ts` и остаточный `backend/app/api/admin.py` по доменам под contract tests.
- [ ] Убрать Pydantic v2 deprecation warnings (`model_validate`, `ConfigDict`).

## P3 — улучшения после запуска

- [ ] Расширить performance dashboards и долгосрочные cohort/retention отчёты после накопления данных.
- [ ] Добавить visual regression для ключевых admin/student экранов.
- [ ] Проверить оптимизацию изображений и устранить Next warning для hero `sizes`.

## Режим первых 72 часов

- [ ] Усиленный мониторинг webhook/outbox/5xx/latency.
- [ ] Ежедневная reconciliation Prodamus ↔ orders/purchases/entitlements/refunds.
- [ ] Проверка dead letter и истекающих доступов утром и вечером.
- [ ] Немедленный kill switch при платеже без доступа, неверной сумме или необрабатываемом webhook.
