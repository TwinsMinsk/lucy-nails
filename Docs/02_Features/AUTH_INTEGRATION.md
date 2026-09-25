# Auth integration

> **Версия:** 2.0
> **Дата:** 26.08.2026
> **Статус:** реализовано; живой межподдоменный smoke обязателен перед GO

## Контракт

- Ученик использует email + пароль.
- Access/refresh находятся в HttpOnly Secure cookies; несекретный `auth_session` marker используется frontend только для UX.
- Изменяющие запросы с cookie требуют CSRF token.
- Refresh token связан с записью `AuthSession`, поэтому отдельную сессию можно отозвать.
- Смена/сброс пароля инвалидирует прежние токены согласно token version/session policy.
- Owner/admin обязаны завершить TOTP MFA setup/login; резервные коды хранятся только в виде хешей и одноразовы.

## Guest checkout activation

После подтверждённой оплаты нового email backend создаёт аккаунт без известного пароля и ставит в outbox одноразовую ссылку установки пароля. Срок ссылки — 24 часа. Для существующего аккаунта приходит уведомление об открытом доступе без изменения пароля.

Редирект Prodamus не авторизует пользователя и не создаёт доступ. Источник истины — валидный webhook и `Entitlement`.

## Срок доступа

Срок не является свойством auth. Он читается из активного `Entitlement`; значение снимка берётся из `Course.access_days` при checkout. Каноническое значение текущего курса — 30 дней. Старое тестовое обещание 365 дней удалено.

## Development seed

Startup seed выполняется только при `ENVIRONMENT=development`. Пароли задаются `SEED_ADMIN_PASSWORD`/`SEED_STUDENT_PASSWORD`; CLI `seed_data.py` требует значения не короче 12 символов и не логирует их. В staging/production seed запрещён конфигурацией.

## Обязательный staging smoke

1. Login/refresh/logout между frontend и API subdomains.
2. CSRF rejection без token и success с token.
3. Guest activation: одноразовость и expiry.
4. Mandatory MFA owner/admin, backup code и session revoke.
5. Student/analyst не получают административные permissions.
