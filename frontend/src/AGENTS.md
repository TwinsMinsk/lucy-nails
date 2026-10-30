# src

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose

Корень исходного кода Next.js-приложения: маршруты App Router (`app/`), React-компоненты (`components/`), клиентские и серверные утилиты и API-клиент (`lib/`), настройка Vitest (`test/`), а также `proxy.ts` (преемник middleware в Next.js 16), защищающий приватные и админ-маршруты редиректом на логин.

## Key Files

| File | Description |
|------|-------------|
| `proxy.ts` | Next.js proxy (`export function proxy`). Матчит `/dashboard/:path*`, `/profile/:path*`, `/courses/:path*`, `/admin/:path*`. Считает "защищёнными" пути под `/admin`, `/dashboard`, `/profile` и `/courses/[id]/lessons/*`; при отсутствии cookie `auth_session=1` редиректит на `/auth/login?next=<path>`. Это UX-guard, а не источник авторизации — реальная проверка прав всегда на backend (FastAPI `Depends`). |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `app/` | Маршруты App Router: публичный лендинг, `(public)`/`(protected)` группы, `admin/`, `payment-success/`, `privacy/`, `terms/` |
| `components/` | React-компоненты: `ui/` (shadcn), `analytics/`, `certificate/`, `course/`, `landing/`, `layout/`, `legal/` |
| `lib/` | API-клиент, env-хелперы, схемы валидации, санитайзер HTML, форматирование дат, согласие и аналитика, контент лендинга |
| `test/` | `setup.ts` — глобальная настройка Vitest: `@testing-library/jest-dom/vitest` и in-memory mock `window.localStorage` |

## For AI Agents

### Working In This Directory

- `proxy.ts` — только UX-редирект по наличию cookie `auth_session=1` (её выставляет `saveTokens` в `src/lib/api.ts` после логина, подтверждения MFA и refresh). Не путать с проверкой ролей/прав — это делает backend. Не полагаться на proxy как единственный слой защиты страниц.
- При добавлении нового защищённого маршрута — обновить `matcher` и/или `isProtectedPath` в `proxy.ts`, иначе proxy его не увидит.
- Импорты между `app/`, `components/`, `lib/` — через алиас `@/*` (см. `tsconfig.json` в `frontend/`), не через относительные `../../..`.

### Testing Requirements

Unit-тесты лежат рядом с кодом (`*.test.ts`, `*.test.tsx`; конфиг `../vitest.config.ts`). Запуск из `frontend/`: `npm test` или `npx vitest run <путь>`. Для `proxy.ts` автотестов нет: Playwright-спеки выставляют cookie заранее. Его изменения проверяются вручную (переход на защищённый путь без сессии → редирект на `/auth/login?next=...`) плюс `npm run build` / `npm run lint` из `frontend/`.

### Common Patterns

- Route groups `(public)` и `(protected)` не влияют на URL — используются только для организации сегментов; собственных `layout.tsx` в них нет (есть корневой и `app/admin/layout.tsx`).
- Клиентские компоненты помечаются `"use client"` в первой строке файла; серверные — без директивы (по умолчанию).

## Dependencies

### Internal

- `app/`, `components/`, `lib/` — см. локальные `AGENTS.md` в каждом каталоге.

### External

- `next/server` (`NextResponse`, `NextRequest`) — для `proxy.ts`.
- `@testing-library/jest-dom` — для `test/setup.ts`.

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
