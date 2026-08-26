# Lucy Nails production release checklist

> **Версия:** 2.0
> **Дата:** 26.08.2026
> **Текущее решение:** **NO-GO** — кодовый baseline готов, внешние P0/P1 из [`production-readiness audit`](../audit/production-readiness-2026-08-26/README.md) не закрыты.

Каждый ручной пункт получает дату, исполнителя и ссылку/ID доказательства. `[x]` без доказательства не считается закрытым.

## 1. Code baseline

- [x] Ветка основана на `origin/master` с сертификатами.
- [x] `ruff check backend/app backend/tests scripts/ops`.
- [x] Полный pytest на PostgreSQL 15: 144 passed, 1 skipped.
- [x] Alembic имеет одну head `1b8c9d0e1f2a`; latest downgrade/upgrade проходит.
- [x] Frontend ESLint, Vitest, Next production build.
- [x] Playwright: guest checkout и public/login в Chromium + mobile WebKit.
- [x] `pip-audit --strict -r backend/requirements.lock`: нет известных уязвимостей.
- [x] `npm audit --omit=dev --audit-level=high`: 0 vulnerabilities.
- [x] Git diff не содержит секретов, `.env`, backup dump, test result или тяжёлых media.
- [ ] CI релизного PR зелёный. Evidence: ______
- [ ] Code review релизного PR завершён. Evidence: ______

## 2. Staging

- [ ] Созданы отдельные frontend, API, worker, bot, PostgreSQL 15, Redis и backup cron.
- [ ] Staging не использует production DB/Redis/email recipients/Telegram chats/Prodamus form.
- [ ] `alembic upgrade head` выполнен; count/backfill сверены.
- [ ] Production-like cookie domain, CORS, CSRF, trusted proxy и CSP проверены между staging-поддоменами.
- [ ] Kinescope staging работает fail-closed без mock.
- [ ] `scripts/smoke-production.ps1` зелёный. Evidence: ______

## 3. Environment и процессы

- [ ] `ENVIRONMENT=production`, `DEBUG=false`, Python 3.11 и Node 20+.
- [ ] Уникальны JWT, MFA encryption, Prodamus, Kinescope, email, Telegram, DB, Redis и S3 secrets.
- [ ] `FRONTEND_URL`, `BACKEND_URL`, `CORS_ORIGINS`, `TRUSTED_HOSTS`, `COOKIE_DOMAIN` точны и HTTPS-only.
- [ ] `REDIS_URL` общий для API replicas; distributed rate limit проверен.
- [ ] Web, outbox worker и Telegram bot запущены как отдельные процессы и имеют restart policy.
- [ ] Owner Telegram chat получает тестовый integration alert.
- [ ] Checkout kill switch выключает новые ссылки без deploy и не закрывает webhook.
- [ ] Секреты и PII отсутствуют в структурированных логах/событиях.

## 4. Payments и delivery

- [ ] Guest checkout создаёт immutable order с фактической ценой/валютой/сроком/UTM.
- [ ] Authenticated checkout использует существующего пользователя.
- [ ] Изменение цены после создания order не вызывает mismatch и не меняет snapshot.
- [ ] Неверная подпись, сумма, валюта и статус отклоняются без доступа.
- [ ] Повторный, переставленный и конкурентный webhook не создаёт дублей.
- [ ] Оплата атомарно создаёт Purchase + Entitlement + analytics event + outbox.
- [ ] Новый гость получает одноразовую activation link; token одноразовый и истекает через 24 часа.
- [ ] Существующий пользователь получает access notification.
- [ ] Resend/SMTP и Telegram retry/dead-letter/manual resend проверены при искусственном отказе.
- [ ] Payment status показывает pending/paid/help и удаляет token из URL без WebKit race.
- [ ] Refund request создан в админке, возврат выполнен в Prodamus, provider reference и net revenue обновлены.

## 5. Content и student flow

- [ ] Production показывает ровно 11 уроков и 17 136 секунд; лендинг обещает около 5 часов и 30 дней.
- [ ] Каждый урок проверен на desktop Chrome/Safari, реальном iOS и Android.
- [ ] Для каждого видео проверены Kinescope status, duration, DRM, domain restriction, seek и отсутствие публичной download link.
- [ ] Ученик с активным entitlement смотрит урок; без/после expiry получает отказ.
- [ ] Progress сохраняется, завершение курса корректно.
- [ ] Сертификат создаётся, скачивается, повторно выдаётся и отзывается.
- [ ] Telegram link, 7/3/1 reminders, expiry и support group removal проверены.

## 6. Admin и security

- [ ] Owner/admin проходят MFA; backup code одноразовый; session revoke завершает доступ.
- [ ] Проверены отрицательные сценарии каждой роли: owner/admin/content_manager/curator/analyst.
- [ ] Нельзя снять последнего owner.
- [ ] User card показывает заказы, оплаты, доступы, прогресс, сертификаты, notes/tags и уведомления.
- [ ] Grant/extend/suspend/revoke требуют причину и попадают в AuditLog.
- [ ] Order/payment/refund, content/video readiness, notification и system screens работают с pagination/filters.
- [ ] CSV не раскрывает данные сверх permission роли.
- [ ] Upload проверяет тип/размер/имя; удаление используемого media безопасно.
- [ ] Полный keyboard/focus/contrast/screen-reader smoke критических потоков пройден.

## 7. Analytics и legal

- [ ] Проверены event dedupe и отсутствие email/phone/payment payload в analytics.
- [ ] Gross/refund/net совпадают с контрольной выборкой orders/purchases/refunds.
- [ ] Funnel, first/last UTM, tariffs, cohorts, progress и delivery отчёты сверены вручную.
- [ ] Яндекс Метрика не загружается до consent и не работает в кабинете/админке.
- [ ] Withdrawal consent прекращает analytics; Webvisor исключает контактные формы.
- [ ] Юрист/бухгалтер согласовали оферту, privacy/cookie policy, consent, refund, retention, чеки и налоги. Evidence: ______

## 8. Reliability и performance

- [ ] Ежедневный backup загружен в отдельный versioned encrypted S3; weekly immutable retention настроен.
- [ ] Внешняя копия восстановлена в отдельную DB; зафиксированы RPO ≤ 24 ч и RTO ≤ 4 ч.
- [ ] Rollback предыдущего deploy выполнен на staging и после него проходит smoke.
- [ ] k6 staging gate: 100 reads, 20 checkout, 10 webhook/s; errors < 1%, p95 < 500 ms. Evidence: ______
- [ ] Alert проверен для webhook, outbox dead letter, integration failure и backup failure.
- [ ] Runbooks оплаты, webhook, delivery, video, refund, rollback, secret leak и DB restore доступны дежурному.

## 9. Final production smoke

- [ ] Автоматический production smoke: дата/исполнитель/evidence ______
- [ ] Один согласованный реальный платёж: order/payment/purchase/entitlement IDs ______
- [ ] Доступ открыт не более чем за 60 секунд; уведомление не более чем за 2 минуты.
- [ ] Вход по activation link, просмотр защищённого урока, progress и certificate успешны.
- [ ] Реальный возврат выполнен и отражён в admin/analytics; доступ скорректирован по политике.
- [ ] Prodamus ↔ internal reconciliation не имеет необъяснённых расхождений.

## 10. Go / No-Go

Решение `GO` подписывают business owner и tech owner только если:

- [ ] все P0/P1 закрыты;
- [ ] пункты 1–9 с доказательствами закрыты;
- [ ] checkout kill switch доступен дежурному;
- [ ] назначены дежурные и канал инцидентов на первые 72 часа.

**Решение:** NO-GO / GO

**Business owner:** ______

**Tech owner:** ______

**Дата/время:** ______

**Release commit/deploy:** ______
