# bot

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose
Отдельный Telegram-бот на библиотеке `python-telegram-bot` (не aiogram) для привязки Telegram-аккаунта студента к аккаунту на сайте через deep link с одноразовым токеном. Это **самостоятельный процесс**, не роутер FastAPI и не запускается вместе с `uvicorn` — свой entry point (`main.py`), свой запуск (`python -m app.bot.main`, процесс `bot` в `backend/Procfile`; локально `scripts/run_bot.ps1` из корня репозитория), long polling.

Бот обрабатывает только входящий `/start`. Исходящие уведомления и управление участниками группы поддержки отправляет не он, а outbox-воркер (`app/services/outbox_service.py`) через Telegram HTTP API с тем же `TELEGRAM_BOT_TOKEN`.

## Key Files
| File | Description |
|------|-------------|
| `main.py` | Точка входа: проверяет `settings.TELEGRAM_BOT_TOKEN` (иначе логирует ошибку и выходит без исключения), строит `ApplicationBuilder().token(...).build()`, регистрирует `CommandHandler("start", start)`, запускает `application.run_polling()`. Вручную добавляет `backend/` в `sys.path` (`sys.path.append(...)`), чтобы работал и запуск как скрипта. |
| `handlers/start.py` | Хендлер команды `/start`. Без аргументов — приветствие. С аргументом (`context.args[0]`) — трактует его как одноразовый токен deep link, шлёт промежуточное сообщение «⏳ Проверяю данные...», вызывает `BotAuthService.link_account`, затем редактирует то же сообщение результатом (`edit_message_text`). |
| `handlers/__init__.py` | Пустой файл-маркер пакета. |
| `services/auth.py` | `BotAuthService.link_account(token, telegram_user)` — вся логика привязки аккаунта. |
| `services/__init__.py` | Пустой файл-маркер пакета. |

## For AI Agents

### Working In This Directory
- Токен выпускает `POST /api/telegram/link` (`app/api/telegram.py`): случайный `secrets.token_urlsafe(32)` с TTL 15 минут, в БД хранится только SHA-256 в `TelegramLinkToken.token_hash`, прежние неиспользованные токены пользователя удаляются. Это не JWT — `BotAuthService.link_account` ищет строку по хешу и `JWT_SECRET_KEY` не использует. Ссылка: `https://t.me/<TELEGRAM_BOT_USERNAME>?start=<token>`.
- Логика линковки: блокирует `User` и затем токен (`with_for_update`, повторное чтение с `populate_existing`), отказывает, если токен не найден, уже использован или истёк; если email не подтверждён и пользователь не admin; если `telegram_id` уже привязан к **другому** пользователю; если у пользователя уже привязан другой Telegram. Иначе записывает `telegram_id`/`telegram_username`, ставит `used_at` и делает commit. Порядок блокировок не менять.
- После привязки, при активном entitlement с тарифом `support` и заданном `TELEGRAM_SUPPORT_GROUP_INVITE`, добавляет к ответу ссылку на чат поддержки.
- Сессия БД открывается напрямую через `async_session_maker()` (не через `Depends(get_db)`, т.к. это не FastAPI-контекст) — при добавлении новых операций в боте следуй этому же паттерну и не забывай `commit`/`rollback` вручную.
- Ошибки логируются через `logger.exception`, пользователь получает нейтральный текст. Токен и его хеш не логировать.
- Новые команды добавляются как хендлеры в `handlers/` и регистрируются в `main.py` через `application.add_handler(CommandHandler(...))`.

### Testing Requirements
Отдельного тестового файла нет: `BotAuthService` проверяется в `backend/tests/test_telegram_notifications.py` (`test_telegram_link_is_one_time_and_connects_account`) и `backend/tests/test_email_ownership.py`; `backend/tests/conftest.py` подменяет `async_session_maker` в `app.bot.services.auth`. Хендлеры и `main.py` тестами не покрыты, проверка вручную:
```powershell
.\scripts\run_bot.ps1
```
(требует `TELEGRAM_BOT_TOKEN` в корневом `.env` или `backend/.env`; активирует `venv`, выставляет `PYTHONPATH`, запускает `python app/bot/main.py`).

### Common Patterns
- `TelegramUser` (из `telegram`) используется только для чтения (`user.id`, `user.first_name`, `user.username`) — не путать с ORM `app.models.user.User`.
- Асинхронные хендлеры `python-telegram-bot`: `async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE)`.
- Статические методы в сервисах бота (`BotAuthService` — все методы `@staticmethod`), в отличие от `app/services/*`, где сервисы чаще модуль-функции или классы с DI сессии.

## Dependencies

### Internal
`app.core.config.settings` (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_SUPPORT_GROUP_INVITE`), `app.core.database.async_session_maker`, `app.models.user.User`, `app.models.telegram_link.TelegramLinkToken`, `app.models.entitlement.Entitlement`.

### External
`python-telegram-bot` (`telegram`, `telegram.ext`), `sqlalchemy` (async `select`).

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
