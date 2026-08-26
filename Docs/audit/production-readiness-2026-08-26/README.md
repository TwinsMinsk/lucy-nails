# Production-readiness audit Lucy Nails

> **Дата среза:** 26.08.2026
> **Аудитор/исполнитель:** Codex; внешние ручные проверки назначаются владельцам ниже
> **Ветка:** `feat/production-readiness`
> **Решение:** **NO-GO**

## 1. Executive summary

В коде построен production-grade фундамент commerce, access, RBAC/MFA, CRM, аналитики, Telegram и эксплуатации. Локальные автоматические gates зелёные: 159 backend tests, 5 frontend unit tests, 6 cross-browser E2E, единственная Alembic head, чистые runtime dependency audits и успешный локальный restore drill.

Запуск пока нельзя одобрить: релизная ветка не слита и не развёрнута, нет изолированного staging, не выполнен новый реальный платёж с возвратом, не проверены вручную все 11 уроков на физических iOS/Android, не настроено внешнее backup-хранилище и нет юридического sign-off. Это внешние, но обязательные P0/P1; автоматическими тестами их честно заменить нельзя.

## 2. Подтверждённый baseline

| Объект | Подтверждение 26.08.2026 |
|---|---|
| Текущий публичный production | [`/health`](https://api.lucysmirnova.ru/health) отвечает `ok` |
| Курс | [`course API`](https://api.lucysmirnova.ru/api/courses/db11a7f7-8dfa-437b-b9da-69c641140300): 11 модулей, 11 уроков, 17 136 секунд, 5 900/11 900 ₽ |
| Лендинг | [`landing API`](https://api.lucysmirnova.ru/api/landing): 11 техник, около 5 часов, 30 дней |
| Remote baseline | `origin/master` = `99e5854` — сертификаты |
| Релизная ветка | 22 feature/security/ops commits поверх baseline после закрытия независимого review; runtime/content baseline `5bafb89` до документационного коммита |
| Схема | PostgreSQL 15, 28 таблиц, единственная Alembic head `4e9d0e1f2a3b` |

Состояние production API подтверждает текущий продаваемый контент, но не доказывает, что новая релизная ветка развёрнута. Новые возможности ниже подтверждены кодом и локальными тестами, а не живой production-средой.

## 3. Матрица готовности

| Область | Готово в коде | Что ещё требует живой проверки |
|---|---|---|
| Заказы/оплата | Order snapshot, signed/idempotent webhook, amount/currency validation, PaymentEvent, status token, refund workflow, kill switch | Prodamus demo и один реальный payment/refund после deploy; reconciliation |
| Доступ | Entitlement отдельно от Purchase, backfill, grant/extend/suspend/revoke, expiry checks | Backfill counts на копии production; фактическое expiry/DRM |
| Доставка | Atomic outbox, email/Telegram worker, retry/dead letter/manual resend, activation link | Resend/SMTP/Telegram credentials, SLA ≤ 2 минут и failure alerts |
| Auth/team | Cookie/CSRF, RBAC 5 ролей, immutable audit, mandatory owner/admin MFA, sessions | Межподдоменный staging smoke, enrolment команды, backup codes/session revoke |
| Admin CRM | Users/orders/access/progress/certificates/notifications/system, search/filter/page/CSV, notes/tags | Операционный UAT владельца на реальных сценариях |
| Content | CRUD, publish/order, configurable price/access days, Kinescope readiness | Все 11 видео на desktop/physical iOS/Android, DRM/domain/seek/duration |
| Analytics | First-party events, UTM, financial truth, funnel/cohorts/progress/refunds/delivery, consent/Metрика | Контрольные данные, Prodamus reconciliation, consent/legal verification |
| Telegram | One-time link, access/reminders/expiry/group removal, owner alerts | Отдельные bot/chat/group в staging и production |
| Security | 0 known runtime audit findings, Redis limit, fail-closed config, PII-redacted logs | External scan after deploy, CSP/cookie/proxy validation from public edge |
| Test/CI | PostgreSQL pytest, migration round-trip, Vitest, Playwright Chromium/WebKit, SCA gates | CI run on PR, Android device farm, full WCAG, staging load |
| Operations | compose dev, structured logs, system view, backup/restore scripts/runbooks | External S3 schedule/restore, monitoring, rollback, measured RPO/RTO |

## 4. Доказательства проверок

| Проверка | Результат | Статус |
|---|---|---|
| `ruff check backend/app backend/tests scripts/ops` | all checks passed | ✅ |
| `pytest backend/tests` на PostgreSQL 15 | 159 passed, 1 skipped, 50 deprecation warnings; 154.98 s | ✅ с P2 debt |
| Alembic heads + latest downgrade/upgrade | одна head `4e9d0e1f2a3b`; round-trip успешен | ✅ |
| Vitest | 3 files, 5 tests passed | ✅ |
| ESLint | exit 0 | ✅ |
| Next production build | exit 0 | ✅ |
| Playwright Chromium + mobile WebKit | 6 passed; исправлены status-token race и legacy-role admin guard | ✅ |
| `npm audit --omit=dev --audit-level=high` | 0 vulnerabilities | ✅ |
| `pip-audit --strict -r backend/requirements.lock` | no known vulnerabilities | ✅ |
| Docker backup/restore drill | 81 928 B; SHA-256 `74fc2ca2...af0bb`; 28 tables; correct head | ✅ локально |
| k6 launch gate | script prepared, staging run absent | ❌ P1 |
| Production real payment/refund | not executed for this release | ❌ P0 |

`test_admin_routes.py` остаётся намеренно skipped в полном наборе из-за legacy fixture/route mismatch; покрытие новых admin domains находится в отдельных CRM/RBAC/MFA/report tests. Skip не скрывается и остаётся P2 для устранения.

## 5. Риски P0–P3

| ID | Sev | Риск / доказательство | Ответственный | Статус | Условие закрытия |
|---|---|---|---|---|---|
| R-01 | P0 | Релиз существует только в feature branch; `origin/master` не содержит новую commerce/security/ops модель | Tech owner | Open | review, merge, deploy, migrations, smoke и release commit recorded |
| R-02 | P0 | Нет owner-assisted Prodamus E2E и реального payment/refund после нового deploy | Business owner + tech | Open | guest/auth checkout, repeated webhook, access ≤60s, notification ≤2m, lesson, certificate, refund |
| R-03 | P1 | Изолированный staging описан, но внешние ресурсы не созданы | Infrastructure owner | Open | topology из `STAGING.md` развёрнута и smoke evidence приложен |
| R-04 | P1 | Все 11 уроков не перепроверены на physical iOS/Android/desktop для этого релиза | Content owner + QA | Open | per-lesson/device checklist, DRM/seek/progress/expiry evidence |
| R-05 | P1 | Нет российского legal/accounting sign-off | Business owner | Open | письменное согласование документов, consent, refund, чеки, НПД/налоги |
| R-06 | P1 | Backup доказан локально, но отдельный encrypted/versioned S3 и restore отсутствуют | Infrastructure owner | Open | scheduled external backup + restore drill + measured RPO/RTO |
| R-07 | P1 | Нагрузочный сценарий подготовлен, но не запускался на staging | Tech owner | Open | <1% errors, p95 <500 ms, DB/Redis metrics attached |
| R-08 | P1 | Production Redis/worker/bot/email/alerts/secrets не валидированы с новой fail-closed конфигурацией | Tech + business owner | Open | all processes healthy; controlled provider failures create alerts/retries |
| R-09 | P2 | Нет полного WCAG 2.2 AA и Android device-farm gate | QA | Open | keyboard/focus/contrast/screen reader + Android report |
| R-10 | P2 | Reconciliation с Prodamus ручная | Operations | Accepted pre-launch | daily signed reconciliation for 72 h; automation scheduled |
| R-11 | P2 | 50 Pydantic/httpx deprecation warnings и один legacy admin skip | Tech owner | Open | Pydantic v2 migration and legacy test restored/removed with rationale |
| R-12 | P2 | `api.ts` и legacy `admin.py` остаются крупными | Tech owner | Open | domain split under contract tests; no behavior change |
| R-13 | P3 | Нет visual regression и долгосрочных retention datasets | Product/tech | Backlog | add after stable production data exists |

## 6. Выполненные исправления

- Commerce: `Order`, `Entitlement`, `PaymentEvent`, `RefundRequest`, outbox/delivery, activation token, safe status polling и kill switch.
- Admin: CRM, orders/refunds/access/progress/certificates/notifications/content/system, server filters/pagination/exports.
- Team security: normalized RBAC, mandatory MFA, backup codes, revocable sessions, last-owner guard и AuditLog.
- Analytics: first-party event contract, server truth, UTM, funnel/cohort/refund/delivery dashboards, consent and Yandex goal bridge without PII.
- Telegram: one-time linking, lifecycle reminders, support group removal and owner alerts.
- Security supply chain: patched frontend/backend runtime packages, Python 3.11 locks, JWT moved to maintained cryptography stack, SCA/CodeQL/secret gates in CI.
- Operations: Redis rate limit, structured correlation logs, staging topology, PostgreSQL backup/restore with checksum/S3, incident runbooks and load gate.
- UX/testing: cross-browser checkout E2E exposed and fixed a real WebKit race after token removal from URL.

## 7. Go/No-Go

**Решение на 26.08.2026: NO-GO.** Причина — открыты R-01/R-02 P0 и R-03–R-08 P1. Кодовая ветка готова стать release candidate, но не может считаться работающим production-релизом до внешних проверок.

Порядок смены решения:

1. Review/merge → isolated staging → migrations/backfill reconciliation.
2. Полный Prodamus demo + content/device + delivery/Telegram + load + external restore.
3. Legal/accounting sign-off и rollback rehearsal.
4. Production deploy с checkout сначала выключенным, smoke и проверка системы.
5. Включить checkout, выполнить согласованный real payment/refund.
6. Закрыть P0/P1 доказательствами и подписать [`RELEASE_CHECKLIST.md`](../../04_Setup_Ops/RELEASE_CHECKLIST.md).

После `GO` первые 72 часа: ежедневная Prodamus reconciliation, контроль PaymentEvent/outbox/dead-letter/5xx/latency, утренне-вечерняя проверка истекающих доступов и немедленный kill switch при платеже без доступа.
