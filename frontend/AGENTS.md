<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-07-06 | Updated: 2026-07-06 -->

# frontend

## Purpose

Next.js 16 (App Router) + React 19 приложение онлайн-школы маникюра: публичный лендинг, личный кабинет ученика с защищёнными видео-уроками (Kinescope) и админ-панель для управления курсами, модулями, уроками, галереей и продажами. Стилизация — Tailwind v4 + shadcn-паттерн (`components.json`, стиль `new-york`). Формы — `react-hook-form` + `zod`. Единственный слой общения с backend — `src/lib/api.ts`.

## Key Files

| File | Description |
|------|-------------|
| `package.json` | Скрипты `dev`/`build`/`start`/`lint`; **нет `npm test`** — регрессии ловятся lint + build + backend pytest |
| `next.config.ts` | CSP-заголовки (разрешены Kinescope, YouTube, Cloudflare Insights), `images.remotePatterns` (Kinescope, Railway, `lucysmirnova.ru`, `api.lucysmirnova.ru/uploads`) |
| `tsconfig.json` | `strict: true`, алиас `@/*` → `./src/*` |
| `eslint.config.mjs` | `eslint-config-next` (core-web-vitals + typescript); намеренно ослаблены `react-hooks/set-state-in-effect`, `@typescript-eslint/no-explicit-any` (warn), `react/no-unescaped-entities` (off) — техдолг, см. комментарий в файле |
| `postcss.config.mjs` | Подключает `@tailwindcss/postcss` |
| `components.json` | shadcn-конфиг: style `new-york`, `rsc: true`, base color `slate`, иконки `lucide`, alias `@/components`, `@/lib`, `@/lib/utils` |
| `.env.example` | Шаблон `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SITE_URL` |
| `src/proxy.ts` | Next.js middleware — см. `src/AGENTS.md` |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `src/` | Исходный код приложения (`app/`, `components/`, `lib/`, `proxy.ts`) |
| `public/` | Статика: фото работ (11 категорий), галерея, лендинг-медиа, uploads |

## For AI Agents

### Working In This Directory

- Env-файлы читаются **только** из каталога `frontend/` (`frontend/.env.local`). Корневой `.env` репозитория Next.js **не видит**. Реальный `.env.local` не коммитить и не цитировать в чате — только `.env.example`.
- `NEXT_PUBLIC_API_URL` и `NEXT_PUBLIC_SITE_URL` нужны на этапе **build**, а не runtime (Next.js инлайнит `NEXT_PUBLIC_*` в бандл). При отсутствии — fallback в `src/lib/env.ts` (`localhost:8000/api` / `https://api.lucysmirnova.ru/api` в зависимости от `NODE_ENV`).
- Все обращения к backend — только через `src/lib/api.ts` (`apiFetch` + доменные функции). Не дублировать `API_BASE_URL`, не делать `fetch` напрямую к API-эндпоинтам.
- Server Components — по умолчанию; `'use client'` — только там, где нужны хуки/интерактивность/браузерные API.
- Новые UI-примитивы добавлять через shadcn CLI (`components.json`) либо вручную по образцу существующих в `src/components/ui/`, не создавая параллельный набор.

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

- Публичные списочные/лендинговые данные (`getPublishedCourses`, `getLandingPayload`, `getPublicCourseModules`) грузятся через `fetch` с `next: { revalidate: 120 }` — ISR на 2 минуты, без авторизации.
- Авторизованные запросы идут через `apiFetch` — httpOnly cookies + CSRF-заголовок (`X-CSRF-Token` для unsafe-методов) + автоматический retry через `/auth/refresh` при 401.
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
- `sonner` — toast-уведомления.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
