# bot

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-11-25

## Purpose
Telegram-бот школы: привязка Telegram к аккаунту сайта (`/start <token>`) и бот поддержки (диалог клиента с операторами в группе с темами). Вся обработка обновлений — один сервис [`app/services/telegram_helpdesk_service.py`](../services/telegram_helpdesk_service.py) (`process_update(db, update_dict)`), у него два транспорта:

- **production** — вебхук `POST /api/telegram/webhook` ([`app/api/telegram_webhook.py`](../api/telegram_webhook.py)); отдельный процесс бота не нужен, вебхук включает [`backend/scripts/telegram_webhook.py`](../../scripts/telegram_webhook.py) `set`;
- **локальная разработка** — этот каталог: long polling на `python-telegram-bot` (`python -m app.bot.main`, процесс `bot` в `backend/Procfile`, `scripts/run_bot.ps1`). Polling работает, только пока у бота нет вебхука.

Уведомления о доступе и алерты владельцу отправляет не бот, а outbox-воркер (`app/services/outbox_service.py`) через Telegram HTTP API с тем же `TELEGRAM_BOT_TOKEN`.

## Key Files
| File | Description |
|------|-------------|
| `main.py` | Точка входа polling: проверяет `settings.TELEGRAM_BOT_TOKEN` (иначе логирует ошибку и выходит без исключения), строит `ApplicationBuilder().token(...).build()`, регистрирует `TypeHandler(Update, handle_update)` для всех обновлений и `run_polling(allowed_updates=ALLOWED_UPDATES)`. Вручную добавляет `backend/` в `sys.path`. При `InvalidToken` пишет сообщение без токена и выходит с кодом 1; логгер `httpx` держится на WARNING, потому что на INFO он пишет URL с токеном. |
| `handlers/updates.py` | `handle_update`: `update.to_dict()` → `process_update` в своей сессии `async_session_maker()`. `HelpdeskTransientError` только логируется (getUpdates уже сдвинул offset). |
| `handlers/__init__.py` | Пустой файл-маркер пакета. |
| `services/auth.py` | `BotAuthService.link_account(token, telegram_user)` — вся логика привязки аккаунта; вызывается из `telegram_helpdesk_service` для `/start <token>` в обоих транспортах. |
| `services/__init__.py` | Пустой файл-маркер пакета. |

## For AI Agents

### Working In This Directory
- Новую логику бота добавлять в `telegram_helpdesk_service.py`, а не в хендлеры PTB: иначе вебхук и polling разойдутся.
- **Исключение из правила outbox.** Пересылка сообщений клиент ↔ тема операторов, подтверждения клиенту и ответы на команды — живой диалог, поэтому сервис зовёт Bot API напрямую через `outbox_service.call_telegram_api` (маскировка токена, таймаут 10 с, `TelegramApiError` с `status_code`/`description`/`transient`). Неудачная пересылка ответа оператора сообщается в теме, неудачная пересылка сообщения клиента — клиенту; временная ошибка (`transient`) даёт 503 и повторную доставку. Алерты владельцу по-прежнему только через outbox.
- Токен выпускает `POST /api/telegram/link` (`app/api/telegram.py`): случайный `secrets.token_urlsafe(32)` (43 символа) с TTL 15 минут, в БД хранится только SHA-256 в `TelegramLinkToken.token_hash`. Ссылка: `https://t.me/<TELEGRAM_BOT_USERNAME>?start=<token>`. Параметр `o_<43 символа>` — подписанная ссылка на заказ (`app/services/support_links.py`), а не токен привязки; 43-символьный токен, случайно начавшийся с `o_`, по-прежнему идёт в привязку.
- Логика привязки (`services/auth.py`): блокирует `User` и затем токен (`with_for_update`, повторное чтение с `populate_existing`), отказывает, если токен не найден, уже использован или истёк; если email не подтверждён и пользователь не admin; если `telegram_id` уже привязан к **другому** пользователю; если у пользователя уже привязан другой Telegram. Иначе записывает `telegram_id`/`telegram_username`, ставит `used_at` и делает commit. Порядок блокировок не менять. Тексты ответов не менять.
- После привязки, при активном entitlement с тарифом `support` и заданном `TELEGRAM_SUPPORT_GROUP_INVITE`, добавляет к ответу ссылку на чат поддержки старого тарифа (не путать с группой операторов `TELEGRAM_HELPDESK_CHAT_ID`).
- Сессия БД в `services/auth.py` открывается напрямую через `async_session_maker()` и сама коммитит.
- Ошибки логируются через `logger.exception`, пользователь получает нейтральный текст. Токен, его хеш, тексты сообщений и email клиентов не логировать.

### Testing Requirements
`backend/tests/test_telegram_helpdesk.py` — вебхук (секрет, размер тела, идемпотентность, 503), `/start` во всех вариантах, пересылка в обе стороны, команды, флуд-лимит, карточка клиента; Bot API подменяется на уровне httpx в `outbox_service`. `BotAuthService` — в `test_telegram_notifications.py` и `test_email_ownership.py`; `conftest.py` подменяет `async_session_maker` в `app.bot.services.auth`. Запуск polling с неверным токеном — `test_telegram_token_redaction.py`. Вручную:
```powershell
.\scripts\run_bot.ps1
```
(требует `TELEGRAM_BOT_TOKEN` тестового бота без вебхука в корневом `.env` или `backend/.env`).

### Common Patterns
- Обновления — сырые dict Bot API (`update.to_dict()` в polling), а не объекты PTB: сервис не зависит от транспорта.
- Статические методы в `BotAuthService`; хелпдеск — модуль функций.

## Dependencies

### Internal
`app.services.telegram_helpdesk_service`, `app.core.config.settings` (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_SUPPORT_GROUP_INVITE`), `app.core.database.async_session_maker`, `app.models.user.User`, `app.models.telegram_link.TelegramLinkToken`, `app.models.entitlement.Entitlement`.

### External
`python-telegram-bot` (только polling-транспорт и тип `telegram.User`), `sqlalchemy` (async `select`).

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
