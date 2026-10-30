# frontend

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose

Next.js 16 (App Router) + React 19 приложение онлайн-школы маникюра: публичный лендинг, личный кабинет ученика с защищёнными видео-уроками (Kinescope) и админ-панель для управления курсами, модулями, уроками, галереей и продажами. Стилизация — Tailwind v4 + shadcn-паттерн (`components.json`, стиль `new-york`). Формы — `react-hook-form` + `zod`. Единственный слой общения с backend — `src/lib/api.ts`.

## Key Files

| File | Description |
|------|-------------|
| `package.json` | Скрипты `dev`/`build`/`start`/`lint`; **нет `npm test`** — регрессии ловятся lint + build + backend pytest. `start` = `next start -p $PORT` (POSIX-подстановка под Railway; в Windows-`cmd` `$PORT` не раскрывается — локально используй `npm run dev`). `engines.node >= 20.9.0` |
| `next.config.ts` | `headers()` для `/:path*`: `Content-Security-Policy` (`connect-src` — origin API, вычисленный из `NEXT_PUBLIC_API_URL` на этапе build, + Kinescope + Cloudflare Insights; `frame-src` — Kinescope и YouTube; `media-src` — Kinescope; `frame-ancestors 'none'`, `object-src 'none'`; `script-src` с `'unsafe-inline' 'unsafe-eval'`), `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` (camera/microphone/geolocation выключены) и `Strict-Transport-Security` (только при `NODE_ENV=production`). `images.remotePatterns`: `kinescope.io`/`*.kinescope.io`, `*.up.railway.app`, `lucysmirnova.ru`, `www.lucysmirnova.ru`, `api.lucysmirnova.ru/uploads/**` |
| `tsconfig.json` | `strict: true`, алиас `@/*` → `./src/*` |
| `eslint.config.mjs` | `eslint-config-next` (core-web-vitals + typescript); намеренно ослаблены `react-hooks/set-state-in-effect` (off), `@typescript-eslint/no-explicit-any` (warn), `react/no-unescaped-entities` (off), `prefer-const` (warn) — техдолг, см. комментарий в файле |
| `postcss.config.mjs` | Подключает `@tailwindcss/postcss` |
| `components.json` | shadcn-конфиг: style `new-york`, `rsc: true`, base color `slate`, иконки `lucide`, alias `@/components`, `@/lib`, `@/lib/utils` |
| `.env.example` | Шаблон `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SITE_URL` (локальные значения + закомментированные production-примеры для Railway) |
| `src/proxy.ts` | Next.js middleware — см. `src/AGENTS.md` |
| `README.md` | Стоковый README от `create-next-app` (упоминает Geist/Vercel) — к проекту не относится, актуальная документация в этих `AGENTS.md` и `../Docs/` |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `src/` | Исходный код приложения (`app/`, `components/`, `lib/`, `proxy.ts`) |
| `public/` | Статика: фото работ (11 категорий), галерея, лендинг-медиа, юр. файлы, локальные uploads |

## For AI Agents

### Working In This Directory

- Env-файлы читаются **только** из каталога `frontend/` (`frontend/.env.local`). Корневой `.env` репозитория Next.js **не видит**. Реальный `.env.local` не коммитить и не цитировать в чате — только `.env.example`.
- `NEXT_PUBLIC_API_URL` и `NEXT_PUBLIC_SITE_URL` нужны на этапе **build**, а не runtime (Next.js инлайнит `NEXT_PUBLIC_*` в бандл). При отсутствии — fallback в `src/lib/env.ts` (`localhost:8000/api` / `https://api.lucysmirnova.ru/api` в зависимости от `NODE_ENV`).
- Все обращения к backend — только через `src/lib/api.ts` (`apiFetch` + доменные функции). Не дублировать `API_BASE_URL`, не делать `fetch` напрямую к API-эндпоинтам.
- Server Components — по умолчанию; `'use client'` — только там, где нужны хуки/интерактивность/браузерные API.
- Новые UI-примитивы добавлять через shadcn CLI (`components.json`) либо вручную по образцу существующих в `src/components/ui/`, не создавая параллельный набор.
- Новый внешний источник (скрипт, iframe, API-хост, CDN картинок) надо явно разрешить в CSP (`headers()` в `next.config.ts`) и/или `images.remotePatterns`, иначе браузер его заблокирует. CSP с `'unsafe-inline' 'unsafe-eval'` — компромисс под Next.js/Cloudflare, не ужесточать без проверки в production-сборке.

### Testing Requirements

Скрипта `npm test` **нет**. Перед коммитом:

```powershell
npm run lint
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8000/api"
$env:NEXT_PUBLIC_SITE_URL = "http://localhost:3000"
npm run build
```

UI-регрессии дополнительно ловятся backend pytest (контракты API, которые потребляет фронт).

### Common Patterns

- Публичные лендинговые данные (`getPublishedCourses`, `getLandingPayload`) грузятся через прямой `fetch` с `next: { revalidate: 120 }` — ISR на 2 минуты, без авторизации. `getPublicCourse`/`getPublicCourseModules` идут через `apiFetch` (без `revalidate`).
- Авторизованные запросы идут через `apiFetch` — httpOnly cookies + CSRF-заголовок (`X-CSRF-Token` из cookie `csrf_token` для unsafe-методов) + автоматический retry через `/auth/refresh` при 401.
- Ошибки API прокидываются как `Error` с текстом из `detail` (см. `parseErrorDetail` в `api.ts`); `isAuthError()` проверяет конкретно "Требуется вход в аккаунт".

## Dependencies

### Internal

- Backend FastAPI (`../backend/`) — контракт см. в Pydantic-схемах и роутерах `backend/app/api/`.

### External

- `next@16.1.4`, `react@19.2.3` — App Router, Server Components.
- `@radix-ui/*`, `class-variance-authority`, `tailwind-merge`, `lucide-react` — shadcn-паттерн UI.
- `@tiptap/*` — rich-text редактор для описаний уроков/курсов в админке.
- `embla-carousel-react` + `embla-carousel-auto-scroll` — карусели (галерея, марки работ).
- `framer-motion` — анимации.
- `react-hook-form` + `@hookform/resolvers` + `zod` — валидация форм.
- `sonner` — toast-уведомления (`ui/sonner.tsx` берёт тему через `next-themes`).
- `tailwindcss@4` + `@tailwindcss/postcss`, `@tailwindcss/typography`, `tw-animate-css` — подключаются в `src/app/globals.css`.

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
