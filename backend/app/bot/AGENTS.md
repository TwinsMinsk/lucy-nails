<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-07-06 | Updated: 2026-07-06 -->

# bot

## Purpose
Отдельный Telegram-бот на библиотеке `python-telegram-bot` (не aiogram) для привязки Telegram-аккаунта студента к аккаунту на сайте через deep link. Это **самостоятельный процесс**, не роутер FastAPI и не запускается вместе с `uvicorn` — свой entry point (`main.py`), свой запуск (`scripts/run_bot.ps1` из корня репозитория), long polling.

## Key Files
| File | Description |
|------|-------------|
| `main.py` | Точка входа: проверяет `settings.TELEGRAM_BOT_TOKEN` (иначе логирует ошибку и выходит без исключения), строит `ApplicationBuilder().token(...).build()`, регистрирует `CommandHandler("start", start)`, запускает `application.run_polling()`. Вручную добавляет корень репо в `sys.path` (`sys.path.append(...)`), т.к. запускается как скрипт, а не пакет. |
| `handlers/start.py` | Хендлер команды `/start`. Без аргументов — приветствие. С аргументом (`context.args[0]`) — трактует его как JWT-токен deep link, шлёт промежуточное сообщение «⏳ Проверяю данные...», вызывает `BotAuthService.link_account`, затем редактирует то же сообщение результатом (`edit_message_text`). |
| `handlers/__init__.py` | Пустой файл-маркер пакета. |
| `services/auth.py` | `BotAuthService.link_account(token, telegram_user)` — вся логика привязки аккаунта. |
| `services/__init__.py` | Пустой файл-маркер пакета. |

## For AI Agents

### Working In This Directory
- `BotAuthService.link_account` декодирует JWT тем же секретом/алгоритмом, что и веб-аутентификация (`settings.JWT_SECRET_KEY`, `settings.JWT_ALGORITHM`), ожидает claim `sub` = `UUID` пользователя. Если понадобится где-то ещё генерировать такой deep-link токен — использовать тот же формат payload (`sub` = str(user.id)).
- Логика линковки: если `telegram_id` уже привязан к **другому** `user_id` — отказ; если к тому же — сообщение «уже привязан»; иначе — поиск пользователя по `user_id` из токена и запись `telegram_id`/`telegram_username`.
- Сессия БД открывается напрямую через `async_session_maker()` (не через `Depends(get_db)`, т.к. это не FastAPI-контекст) — при добавлении новых операций в боте следуй этому же паттерну и не забывай `commit`/`rollback` вручную.
- Ошибки в `services/auth.py` сейчас логируются через `print(...)`, а не через `logging` (в отличие от `main.py`, где настроен `logging.basicConfig`) — расхождение с остальным бэкендом, при правках в этом файле не обязательно переносить на `logging`, если задача не про это.
- Новые команды добавляются как хендлеры в `handlers/` и регистрируются в `main.py` через `application.add_handler(CommandHandler(...))`.

### Testing Requirements
Выделенных pytest-тестов для бота в `backend/tests/` нет. Проверка вручную:
```powershell
.\scripts\run_bot.ps1
```
(требует `TELEGRAM_BOT_TOKEN` в `backend/.env`; активирует `venv`, выставляет `PYTHONPATH`, запускает `python app/bot/main.py`). При изменении `BotAuthService` — проверяй сценарии через существующие фикстуры БД в `backend/tests/conftest.py` при написании unit-тестов вручную (модуля с готовыми тестами под `bot/` сейчас не существует).

### Common Patterns
- `TelegramUser` (из `telegram`) используется только для чтения (`user.id`, `user.first_name`, `user.username`) — не путать с ORM `app.models.user.User`.
- Асинхронные хендлеры `python-telegram-bot`: `async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE)`.
- Статические методы в сервисах бота (`BotAuthService` — все методы `@staticmethod`), в отличие от `app/services/*`, где сервисы чаще модуль-функции или классы с DI сессии.

## Dependencies

### Internal
`app.core.config.settings` (`TELEGRAM_BOT_TOKEN`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`), `app.core.database.async_session_maker`, `app.models.user.User`.

### External
`python-telegram-bot` (`telegram`, `telegram.ext`), `python-jose` (`jose.jwt`, `jose.JWTError`), `sqlalchemy` (async `select`).

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
