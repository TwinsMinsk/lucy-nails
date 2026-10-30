# frontend

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose

Next.js 16 (App Router) + React 19 приложение онлайн-школы маникюра: публичный лендинг с гостевой оплатой, личный кабинет ученика с защищёнными видео-уроками (Kinescope) и сертификатами, админ-панель с ролевым доступом для управления курсами, лендингом, учениками, доступами, заказами, сертификатами, уведомлениями и аналитикой. Стилизация — Tailwind v4 + shadcn-паттерн (`components.json`, стиль `new-york`). Формы входа и регистрации — `react-hook-form` + `zod`, остальные — контролируемый state. Единственный слой общения с backend — `src/lib/api.ts`.

## Key Files

| File | Description |
|------|-------------|
| `package.json` | Скрипты `dev`, `build`, `start` (`next start -p $PORT`, рассчитан на Railway), `lint`, Vitest `test` и `test:unit` (оба `vitest run`), Playwright `test:e2e`; `engines.node` `>=20.9.0` |
| `next.config.ts` | Заголовки для всех путей: CSP (origin API из `NEXT_PUBLIC_API_URL`, Kinescope, YouTube только во `frame-src`, Cloudflare Insights, Яндекс Метрика: `mc.yandex.*`, `mc.webvisor.*`, `wss://`, `yastatic.net`), `frame-ancestors` только для доменов Метрики (просмотр Вебвизора и карт), `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, HSTS только в production. `images.remotePatterns`: Kinescope, `*.up.railway.app`, `lucysmirnova.ru`, `www.lucysmirnova.ru`, `api.lucysmirnova.ru/uploads/**` |
| `tsconfig.json` | `strict: true`, алиас `@/*` → `./src/*` |
| `eslint.config.mjs` | `eslint-config-next` (core-web-vitals + typescript); намеренно ослаблены `react-hooks/set-state-in-effect` (off), `@typescript-eslint/no-explicit-any` (warn), `react/no-unescaped-entities` (off), `prefer-const` (warn) — техдолг, см. комментарий в файле |
| `postcss.config.mjs` | Подключает `@tailwindcss/postcss` |
| `components.json` | shadcn-конфиг: style `new-york`, `rsc: true`, base color `slate`, иконки `lucide`, alias `@/components`, `@/components/ui`, `@/lib`, `@/lib/utils` (alias `@/hooks` объявлен, каталога нет) |
| `vitest.config.ts` | jsdom, `src/test/setup.ts`, тесты `src/**/*.test.{ts,tsx}`, `restoreMocks: true`, алиас `@` |
| `playwright.config.ts` | Сервера, проекты и `PLAYWRIGHT_BASE_URL` — см. `e2e/AGENTS.md` |
| `.env.example` | Шаблон `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SITE_URL`, опционального `NEXT_PUBLIC_YANDEX_METRIKA_ID` |
| `src/proxy.ts` | Next.js proxy (преемник middleware) — см. `src/AGENTS.md` |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `src/` | Исходный код приложения (`app/`, `components/`, `lib/`, `test/`, `proxy.ts`) |
| `public/` | Статика: фото работ (11 категорий), галерея, лендинг-медиа, юридические файлы, uploads |
| `e2e/` | Playwright-сценарии и API-фикстура для SSR — см. `e2e/AGENTS.md` |

## For AI Agents

### Working In This Directory

- Env-файлы читаются **только** из каталога `frontend/` (`frontend/.env.local`). Корневой `.env` репозитория Next.js **не видит**. Реальный `.env.local` не коммитить и не цитировать в чате — только `.env.example`.
- `NEXT_PUBLIC_API_URL` и `NEXT_PUBLIC_SITE_URL` нужны на этапе **build**, а не runtime (Next.js инлайнит `NEXT_PUBLIC_*` в бандл). При отсутствии — fallback в `src/lib/env.ts` (`localhost:8000/api` / `https://api.lucysmirnova.ru/api` в зависимости от `NODE_ENV`). `NEXT_PUBLIC_YANDEX_METRIKA_ID` опционален: без него счётчик не загружается.
- `NEXT_PUBLIC_*` читать только статическим обращением (`process.env.NEXT_PUBLIC_X`): динамический `process.env[name]` в браузерный бандл не подставляется (см. комментарий в `src/lib/env.ts`).
- Все обращения к backend — только через `src/lib/api.ts` (`apiFetch` + доменные функции). Не дублировать `API_BASE_URL`, не делать `fetch` напрямую к API-эндпоинтам. Единственное исключение сейчас — опрос статуса заказа в `src/app/payment-success/payment-status.tsx`.
- `npm start` рассчитан на Railway (`$PORT`); локально — `npm run dev` или `.\scripts\dev-frontend.ps1` из корня репозитория.
- Server Components — по умолчанию; `'use client'` — только там, где нужны хуки/интерактивность/браузерные API.
- Новые UI-примитивы добавлять через shadcn CLI (`components.json`) либо вручную по образцу существующих в `src/components/ui/`, не создавая параллельный набор.

### Testing Requirements

Перед коммитом:

```powershell
npm run lint
npm test -- --run
npx tsc --noEmit --incremental false
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8000/api"
$env:NEXT_PUBLIC_SITE_URL = "http://localhost:3000"
npm run build
```

`npm test` уже запускает `vitest run`, флаг `-- --run` повторяет шаг CI. Один файл: `npx vitest run src/lib/api.test.ts`. CI (`.github/workflows/ci.yml`, Node 24): `npm ci` → lint → `npm test -- --run` → `npm audit --omit=dev --audit-level=high` → build → Playwright. Отдельного шага `tsc` в CI нет.

Браузерная проверка: `npm run test:e2e`. По умолчанию Playwright запускает изолированные SSR API-фикстуры на 3016 и Next.js на 3015; существующие серверы не переиспользует. При явном `PLAYWRIGHT_BASE_URL` окружение готовит вызывающий. Это проверка контрактов, а не реальных платежей или воспроизведения Kinescope. Подробности — `e2e/AGENTS.md`.

### Common Patterns

- Публичные списочные/лендинговые данные (`getPublishedCourses`, `getLandingPayload`) грузятся через `fetch` с `next: { revalidate: 120 }` — ISR на 2 минуты, без авторизации. `getPublicCourse` и `getPublicCourseModules` идут через `apiFetch` без кэша, `verifyCertificate` — `fetch` с `cache: "no-store"`.
- Авторизованные запросы идут через `apiFetch` — httpOnly cookies + CSRF-заголовок (`X-CSRF-Token` для unsafe-методов) + автоматический retry через `/auth/refresh` при 401 (параллельные 401 делят один refresh).
- Ошибки API прокидываются как `ApiError` (`status`, `detail`, текст из `parseErrorDetail` в `api.ts`); неудавшийся refresh даёт обычный `Error`, и `isAuthError()` проверяет конкретно "Требуется вход в аккаунт".
- Права админки приходят из `GET /admin/team/me` (`adminGetCapabilities`), а не из `user.role` — см. `src/app/AGENTS.md`.

## Dependencies

### Internal

- Backend FastAPI (`../backend/`) — контракт см. в Pydantic-схемах и роутерах `backend/app/api/`.

### External

- `next@^16.4.3` (в lock 16.4.3), `react@19.2.3` — App Router, Server Components.
- `@radix-ui/*`, `class-variance-authority`, `tailwind-merge`, `lucide-react` — shadcn-паттерн UI.
- `@tiptap/*` — rich-text редактор конспектов уроков в админке.
- `embla-carousel-react` + `embla-carousel-auto-scroll` — карусели (галерея, марки работ).
- `framer-motion` — анимации.
- `react-hook-form` + `@hookform/resolvers` + `zod` — валидация форм.
- `sonner` + `next-themes` — toast-уведомления.
- `qrcode.react` — QR для настройки MFA на странице входа.
- `canvas-confetti` — конфетти при получении сертификата.
- Dev: `vitest`, `jsdom`, `@testing-library/*` — unit-тесты; `@playwright/test` — e2e.

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.

<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
