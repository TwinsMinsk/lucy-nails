<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-07-06 | Updated: 2026-07-06 -->

# src

## Purpose

Корень исходного кода Next.js-приложения: маршруты App Router (`app/`), React-компоненты (`components/`), клиентские утилиты и API-клиент (`lib/`), а также edge-middleware (`proxy.ts`), защищающий приватные и админ-маршруты редиректом на логин.

## Key Files

| File | Description |
|------|-------------|
| `proxy.ts` | Next.js middleware (`export function proxy`). Матчит `/dashboard/:path*`, `/profile/:path*`, `/courses/:path*`, `/admin/:path*`. Считает "защищёнными" пути под `/admin`, `/dashboard`, `/profile` и `/courses/[id]/lessons/*`; при отсутствии cookie `auth_session=1` редиректит на `/auth/login?next=<path>`. Это UX-guard, а не источник авторизации — реальная проверка прав всегда на backend (FastAPI `Depends`). |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `app/` | Маршруты App Router: публичный лендинг, `(public)`/`(protected)` группы, `admin/` |
| `components/` | React-компоненты: `ui/` (shadcn), `course/`, `landing/`, `layout/` |
| `lib/` | API-клиент, env-хелперы, схемы валидации, санитайзер HTML, контент лендинга |

## For AI Agents

### Working In This Directory

- `proxy.ts` — только UX-редирект по наличию cookie `auth_session=1` (её выставляет `src/lib/api.ts` после логина). Не путать с проверкой ролей/прав — это делает backend. Не полагаться на middleware как единственный слой защиты страниц.
- При добавлении нового защищённого маршрута — обновить `matcher` и/или `isProtectedPath` в `proxy.ts`, иначе middleware его не увидит.
- Импорты между `app/`, `components/`, `lib/` — через алиас `@/*` (см. `tsconfig.json` в `frontend/`), не через относительные `../../..`.

### Testing Requirements

Отдельных тестов для этого уровня нет. Изменения в `proxy.ts` проверяются вручную (переход на защищённый путь без сессии → редирект на `/auth/login?next=...`) плюс `npm run build` / `npm run lint` из `frontend/`.

### Common Patterns

- Route groups `(public)` и `(protected)` не влияют на URL — используются только для организации layout'ов/сегментов.
- Клиентские компоненты помечаются `"use client"` в первой строке файла; серверные — без директивы (по умолчанию).

## Dependencies

### Internal

- `app/`, `components/`, `lib/` — см. локальные `AGENTS.md` в каждом каталоге.

### External

- `next/server` (`NextResponse`, `NextRequest`) — для `proxy.ts`.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
