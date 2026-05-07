# Post-MVP Hardening Backlog

Эти пункты не блокируют первый production-релиз MVP, но должны быть запланированы после стабилизации продаж и первых пользователей.

- Перевести auth на полноценные httpOnly Secure cookie sessions с refresh-token rotation/revocation.
- Подключить Redis-backed rate limit для нескольких backend-инстансов.
- Добавить payment audit/outbox: raw webhook events, retry доставки писем, историю повторных покупок.
- Расширить тесты: expired access, admin/upload, real Prodamus fixtures, frontend smoke/e2e.
- Добавить Telegram-бота, сертификаты, PWA и расширенную аналитику.

## Refactor backlog перед активной разработкой

Эти пункты можно выполнять маленькими PR без изменения пользовательского поведения.

### Репозиторий и документация

- Держать источники правды в цепочке: `AGENTS.md` → `CODEBASE.md` → `Docs/README.md` → тематические документы.
- Не хранить в Git локальные mp4 и промежуточные файлы: `promo-clips/`, `video-lessons/`, `scripts/promo/output/`.
- При добавлении новой подсистемы обновлять `CODEBASE.md`, а подробности переносить в `Docs/`.

### Backend

- Разбить `backend/app/api/admin.py` на доменные роутеры и вынести локальные Pydantic-схемы в `backend/app/schemas/`.
- Выровнять импорты auth/admin dependencies через `backend/app/core/dependencies.py`.
- Зафиксировать единую политику транзакций для `backend/app/core/database.py` и явных `commit` в роутерах/сервисах.
- Проверить dev-seed, CORS и production-hardening в `backend/app/main.py`.
- Постепенно привести Pydantic v2 usage к одному стилю `model_validate` / `from_attributes`.

### Frontend

- Разбить `frontend/src/lib/api.ts` на общий client и доменные API-модули.
- Разгрузить `frontend/src/app/page.tsx`: разделить данные лендинга, секции и API-подстановки.
- Разбить крупные client-страницы админки на компоненты, формы, диалоги и hooks.
- Согласовать `frontend/components.json`, Tailwind v4 через `globals.css` и текущую структуру hooks/lib.

### Проверки

- Сверять команды в `AGENTS.md`, `Docs/04_Setup_Ops/DEVELOPMENT_WORKFLOW.md` и `.github/workflows/ci.yml`.
- Добавить smoke-проверку Alembic на чистой БД или явно документировать отличие тестовой схемы `Base.metadata.create_all`.
- Усиливать Ruff/ESLint правила только после чистки соответствующих файлов.
