# e2e

**Parent context:** `../AGENTS.md`
**Generated:** 2026-10-30 · **Updated:** 2026-10-30

## Purpose

Браузерные сценарии Playwright для критичных потоков: гостевая оплата, вход и регистрация, активация аккаунта, истёкший доступ, надёжность кабинета и уроков, права админки. Реальный backend не нужен: SSR ходит в API-фикстуру, а запросы из браузера подменяются через `page.route`. Это проверка контрактов, а не реальных платежей или воспроизведения Kinescope.

## Key Files

| File | Description |
|------|-------------|
| `fixtures/api-server.mjs` | API для SSR на `127.0.0.1:3016` (см. ниже) |
| `activate.spec.ts` | `/auth/activate`: установка пароля и переход на логин, токен исчезает из URL, повторная загрузка без токена, ошибки 422 и 400 дают понятное сообщение без текста валидации, страница без токена предлагает восстановление |
| `admin-operations.spec.ts` | Хелпер `staff(page, role, permissions)`. Analyst: поиск и страницы заказов за 200, даты в Москве, нет кнопки "Возврат" и запроса `/admin/refunds`. Curator: выбор курса из `/admin/access-courses` без действий `users.manage` и без запроса `/admin/courses`. Уведомления, ученики и доступы сохраняют поиск, фильтры и `offset` при перезагрузке |
| `admin-rbac.spec.ts` | Контент-менеджер с `role: "student"` и `roles: ["content_manager"]` видит только разрешённые пункты меню, `/admin/users` редиректит его на `/admin/courses` |
| `checkout.spec.ts` | Гостевая оплата: два обязательных согласия блокируют отправку и получают фокус, состав запроса `guest-link` (включая `course_id` фикстуры), подтверждённый статус на `/payment-success`. Диалог оплаты на экране 360×640 |
| `expired-access.spec.ts` | Кабинет: предложение продления истёкшего доступа, даты в `Europe/Moscow`, чат куратора только для тарифа `support`. Урок при 403 на прогресс объясняет отсутствие доступа вместо "не найдено" |
| `learning-reliability.spec.ts` | Ошибка 503 в кабинете даёт кнопку "Повторить", а не пустой аккаунт. Предпросмотр урока переживает 403 на прогресс. После 300 с обновление play-URL при отзыве доступа убирает iframe и не повторяет запрос на каждый `focus` |
| `public-smoke.spec.ts` | Лендинг и страница входа открываются. Регистрация требует оба согласия. Вход шлёт данные в API, форма имеет `method="post"`, пароль не попадает в URL |

### `fixtures/api-server.mjs`

Процесс на `node:http`, только для запросов Server Components, которые `page.route` не видит:

- `GET /health` → `{ "status": "ok" }`, по нему Playwright ждёт готовности.
- `GET /api/landing` → курс `11111111-1111-4111-8111-111111111101` ("Nail Design PRO — Playwright", `price_self: 7200`, `access_days: 45`), `hero.landing_title`, пустые `modules` и `gallery`.
- Всё остальное → `503` с `detail`, поэтому на лендинге `getPublicCourseModules` даёт `null`, а `(public)/courses/[id]` отдаёт 404.
- Заголовки: CORS для `http://127.0.0.1:3015` с credentials, `Cache-Control: no-store`.

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `fixtures/` | Вспомогательный API-сервер; спеки в нём не лежат |

## For AI Agents

### Working In This Directory

- `page.route` перехватывает только запросы браузера. Данные, которые читают Server Components, добавлять в `fixtures/api-server.mjs`; запросы клиентских компонентов — подменять `page.route("**/api/...")` в спеке.
- Локаторы привязаны к русским текстам интерфейса: при правке кнопок, заголовков или лейблов обновлять спеки.
- Ответы `route.fulfill` идут на другой origin: нужны `access-control-allow-origin` (origin приложения) и `access-control-allow-credentials: true`, а для POST с JSON ещё и обработка preflight `OPTIONS` (см. `corsHeaders` в `activate.spec.ts`).
- Гидрация: клик или ввод в SSR-разметку до подключения React теряется. Перед действием ждать ключ `__reactProps` на элементе (`page.waitForFunction` или `expect.poll`), как в `activate`, `checkout`, `public-smoke`.
- Сессия эмулируется cookie `auth_session=1` через `addCookies` (проходит `src/proxy.ts`) и подменой `**/api/auth/me`; для админки ещё `**/api/admin/team/me` с `roles` и `permissions`.
- При `PLAYWRIGHT_BASE_URL` серверы не запускаются, окружение готовит вызывающий. `checkout.spec.ts` ждёт `course_id` фикстуры, поэтому на другом API это утверждение не пройдёт.

### Testing Requirements

Из `frontend/`:

```powershell
npx playwright install chromium webkit
npm run test:e2e
npm run test:e2e -- e2e/checkout.spec.ts
npm run test:e2e -- --project=chromium
```

Конфиг `../playwright.config.ts`:

- `testDir: ./e2e`, `fullyParallel: true`, `workers: 2`, `trace: on-first-retry`. Вне CI `retries: 0` и репортер `list`, в CI `retries: 2` и репортер `github`.
- `baseURL` — `PLAYWRIGHT_BASE_URL` или `http://127.0.0.1:3015`.
- Без `PLAYWRIGHT_BASE_URL` поднимаются два сервера: `node e2e/fixtures/api-server.mjs` и `node node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port 3015` (таймаут 120 с) с `NEXT_PUBLIC_API_URL=http://127.0.0.1:3016/api`, `NEXT_PUBLIC_SITE_URL=http://127.0.0.1:3015` и пустым `NEXT_PUBLIC_YANDEX_METRIKA_ID`. `reuseExistingServer: false`: порты 3015 и 3016 должны быть свободны.
- Проекты: `chromium` (Desktop Chrome) и `mobile` (iPhone 13, движок WebKit). Каждый сценарий запускается в обоих.

CI (`.github/workflows/ci.yml`) после build ставит браузеры `npx playwright install --with-deps chromium webkit` и запускает `npm run test:e2e`. При изменении критичного потока обновлять и спеки, и Vitest.

Vitest эти файлы не запускает (`include: src/**/*.test.{ts,tsx}`), но `eslint` и `tsc` их проверяют.

### Common Patterns

- Общего модуля хелперов нет: `staff()`, `student()`, `corsHeaders()`, `json()` объявлены внутри своих спеков.
- Локаторы — по роли и лейблу (`getByRole`, `getByLabel`, `getByPlaceholder`), тексты на русском.
- Даты: backend отдаёт naive UTC. Админка всегда показывает Москву, а для кабинета часовой пояс задаётся через `test.use({ timezoneId: "Europe/Moscow" })`.
- Истечение времени эмулируется подменой `Date.now` в `page.evaluate` с последующим `focus` (`learning-reliability.spec.ts`).

## Dependencies

### Internal

- `../playwright.config.ts` — серверы и проекты.
- `../src/proxy.ts`, `../src/app/`, `../src/components/` — проверяемое приложение; `../src/lib/api.ts` — контракт запросов, которые подменяют спеки.

### External

- `@playwright/test`, Node.js `node:http` (фикстура).

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
