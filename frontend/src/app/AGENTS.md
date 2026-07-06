<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-07-06 | Updated: 2026-07-06 -->

# app

## Purpose

Маршруты Next.js App Router: публичный лендинг и каталог курсов, приватный кабинет ученика с видео-уроками, админ-панель управления контентом и продажами. Корневой `layout.tsx` подключает шрифты (`Inter`, `Playfair Display`), глобальный `Header`/`Footer`/`Toaster` и SEO-метаданные (`metadataBase` из `getPublicSiteUrl()`).

## Key Files

| File | Description |
|------|-------------|
| `layout.tsx` | Root layout: шрифты через `next/font/google`, `Header`/`Footer` вокруг `children`, глобальные `<Metadata>` (title template `%s — Lucy Nails Academy`, OpenGraph/Twitter card), `<Toaster />` (sonner) |
| `page.tsx` | Лендинг (`/`): hero, программа (`ProgramSection`), галерея (`NailsGallery`), тарифы (`PaymentButton`). Контент — через `getLandingContent()` (мердж API + статики), цены/`courseId` — через `getPublishedCourses()` с фолбэком на статичные `COURSE_DATA.prices` |
| `globals.css` | Tailwind v4 (`@import "tailwindcss"`), typography-плагин, кастомные CSS-переменные темы (`--primary`, `--surface`, `--text-primary` и т.д. в oklch), кастомный `@utility container` (Tailwind v4 убрал авто-центрирование — возвращено вручную) |
| `robots.ts` | `MetadataRoute.Robots`: disallow `/admin`, `/dashboard`, `/profile`, `/courses/*/lessons/*`; ссылка на `sitemap.xml` |
| `sitemap.ts` | `MetadataRoute.Sitemap`: статичные `/`, `/privacy`, `/terms` + динамические `/courses/:id` из `getPublishedCourses()` (fallback на статичные при ошибке API) |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `(public)/` | Route group без auth: `auth/login`, `auth/register`, `courses/[id]` (публичная страница курса) |
| `(protected)/` | Route group за middleware-гвардом (`src/proxy.ts`): `dashboard` (мои курсы), `profile`, `courses/[id]/lessons/[lessonId]` (просмотр урока, `VideoPlayer`) |
| `admin/` | Панель администратора: `analytics`, `courses` (список + `courses/[id]` редактор модулей/уроков), `landing` (редактор hero/модулей/галереи лендинга), `purchases`, `users` |
| `payment-success/` | Страница возврата после оплаты Prodamus |
| `privacy/`, `terms/` | Статические юридические страницы |

## For AI Agents

### Working In This Directory

- Server Components по умолчанию; `'use client'` — только там, где нужны хуки состояния/эффекты/браузерные API (формы, карусели, дропдауны).
- `(public)` и `(protected)` — route groups, не влияют на URL. Реальная защита `(protected)` и `admin/` — на уровне `src/proxy.ts` (UX-редирект по cookie) **и** backend-эндпоинтов (источник правды по правам).
- Отдельные `AGENTS.md` для вложенных маршрутов **не создавать** — вся специфика документируется здесь.
- Публичные страницы (`page.tsx`, `sitemap.ts`, `robots.ts`, страница курса) должны переживать отказ API: оборачивать вызовы `getPublishedCourses`/`getLandingPayload`/`getPublicCourseModules` в try/catch с фолбэком на статический контент (`src/lib/landing/course-content.ts`), как уже сделано в `page.tsx` и `sitemap.ts`.
- Новые публичные маршруты — добавлять в `sitemap.ts` при необходимости индексации; закрытые — в `disallow` в `robots.ts`.

### Testing Requirements

Своих unit-тестов нет. Проверки — `npm run lint` и `npm run build` (см. `frontend/AGENTS.md`) плюс backend pytest для контрактов API, которые страницы потребляют через `src/lib/api.ts`.

### Common Patterns

- Метаданные страницы задаются через `export const metadata: Metadata` (статические) или `generateMetadata` (динамические, например для `courses/[id]`).
- Публичные списочные данные грузятся с `next: { revalidate: 120 }` (ISR), приватные — через `apiFetch` с cookie-сессией.
- Курс/уроки: canonical источник структуры — `ModuleResponse`/`LessonBriefResponse` из `src/lib/api.ts`; лендинг-копирайт мержится поверх через `src/lib/landing/loader.ts`.

## Dependencies

### Internal

- `../components/` — `Header`, `Footer`, `NailsGallery`, `PaymentButton`, `ProgramSection`, `VideoPlayer`, `ModuleList`, UI-примитивы.
- `../lib/` — `api.ts` (все запросы к backend), `env.ts` (site/API URL), `landing/` (контент лендинга).

### External

- `next/font/google` (Inter, Playfair Display), `next/image`, `lucide-react` (иконки), `sonner` (`Toaster`).

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
