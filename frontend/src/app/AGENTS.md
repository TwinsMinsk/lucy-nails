# app

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose

Маршруты Next.js App Router: публичный лендинг и каталог курсов, приватный кабинет ученика с видео-уроками, админ-панель управления контентом и продажами. Корневой `layout.tsx` подключает шрифты (`Inter`, `Playfair Display`), глобальный `Header`/`Footer`/`Toaster` и SEO-метаданные (`metadataBase` из `getPublicSiteUrl()`).

## Key Files

| File | Description |
|------|-------------|
| `layout.tsx` | Root layout: шрифты через `next/font/google`, `Header`/`Footer` вокруг `children`, глобальные `<Metadata>` (title template `%s — Lucy Nails Academy`, OpenGraph/Twitter card), `<Toaster />` (sonner) |
| `page.tsx` | Лендинг (`/`), секции-якоря `#about`/`#program`/`#gallery`/`#pricing`: hero, программа (`ProgramSection`), галерея (`NailsGallery`), тарифы (`PaymentButton`). Контент — через `getLandingContent()` (мердж API + статики), цены/`courseId` первого курса — через `getPublishedCourses()` с фолбэком на статичные `COURSE_DATA.prices`, модули этого курса — через `getPublicCourseModules()` (при ошибке `null`) |
| `error.tsx` | `"use client"`. Брендированная error boundary сегментов (рендерится внутри root layout): «Что-то пошло не так», кнопки `reset()` и «На главную»; ошибку пишет в `console.error` |
| `global-error.tsx` | `"use client"`. Error boundary для падений самого root layout: рендерит собственные `<html>`/`<body>` с inline-стилями (без Tailwind/шрифтов приложения) и кнопкой `reset()` |
| `not-found.tsx` | Брендированная 404: ссылки на `/` и `/dashboard`; статический `metadata.title` |
| `favicon.ico` | Metadata-файл App Router (`/favicon.ico`) |
| `globals.css` | Tailwind v4 (`@import "tailwindcss"`), `@plugin "@tailwindcss/typography"`, `@import "tw-animate-css"`, `@custom-variant dark`, кастомные CSS-переменные темы (`--primary`, `--surface`, `--text-primary` и т.д. в oklch, плюс блок `.dark`), кастомный `@utility container` (Tailwind v4 убрал авто-центрирование — возвращено вручную) |
| `robots.ts` | `MetadataRoute.Robots`: disallow `/admin`, `/dashboard`, `/profile`, `/courses/*/lessons/*`; ссылка на `sitemap.xml` |
| `sitemap.ts` | `MetadataRoute.Sitemap`: статичные `/`, `/privacy`, `/terms` + динамические `/courses/:id` из `getPublishedCourses()` (fallback на статичные при ошибке API) |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `(public)/` | Route group без auth (все страницы `auth/*` — `"use client"`): `auth/login` (`LoginSchema`, `safeNextPath`, ссылка «Забыли пароль?» → `auth/forgot-password`), `auth/register` (`RegisterSchema`, после регистрации сразу `login`), `auth/forgot-password` (`forgotPassword(email)` → письмо со ссылкой), `auth/reset-password` (`?token=` из письма через `useSearchParams` в `Suspense`, `resetPassword(token, newPassword)`, мин. 6 символов, затем редирект на `/auth/login`), `courses/[id]` (публичная серверная страница курса: `generateMetadata`, `getPublicCourse` + `getPublicCourseModules`, `ModuleList`, `CoursePaymentCTA`; при ошибке API — `notFound()`) |
| `(protected)/` | Route group за middleware-гвардом (`src/proxy.ts`), все страницы `"use client"`: `dashboard` (мои курсы, `getMyCourses`), `profile` (данные `getMe` + форма «Смена пароля» → `changePassword(current, new)`, мин. 6 символов + подтверждение), `courses/[id]/lessons/[lessonId]` (просмотр урока: `VideoPlayer`, `getCourseProgress`/`updateLessonProgress`, контент урока через `sanitizeHtml`) |
| `admin/` | Панель администратора. `admin/layout.tsx` (`"use client"`) — сайдбар-навигация и клиентская проверка `getMe().role === "admin"` (иначе редирект на `/dashboard` или `/auth/login`). Страницы: `users` (выдача доступа `adminGrantAccess`), `courses` (список + `courses/[id]` редактор модулей/уроков с `ui/editor`), `landing` (редактор hero/модулей/галереи лендинга), `purchases` (список покупок + кнопка «Отозвать» у активных → `adminRevokeAccess(purchase.id)` после `window.confirm`), `analytics` |
| `payment-success/` | Страница возврата после оплаты Prodamus (серверная, статический `metadata`) |
| `privacy/`, `terms/` | Статические юридические страницы |

## For AI Agents

### Working In This Directory

- Server Components по умолчанию; `'use client'` — только там, где нужны хуки состояния/эффекты/браузерные API (формы, карусели, дропдауны).
- `(public)` и `(protected)` — route groups, не влияют на URL. Реальная защита `(protected)` и `admin/` — на уровне `src/proxy.ts` (UX-редирект по cookie) **и** backend-эндпоинтов (источник правды по правам).
- Отдельные `AGENTS.md` для вложенных маршрутов **не создавать** — вся специфика документируется здесь.
- Публичные страницы (`page.tsx`, `sitemap.ts`, `robots.ts`, страница курса) должны переживать отказ API: оборачивать вызовы `getPublishedCourses`/`getLandingPayload`/`getPublicCourseModules` в try/catch с фолбэком на статический контент (`src/lib/landing/course-content.ts`), как уже сделано в `page.tsx` и `sitemap.ts`. Исключение — `(public)/courses/[id]`: без данных курса отдаёт `notFound()`.
- Необработанные ошибки рендера ловит `error.tsx` (в пределах root layout), падения самого `layout.tsx` — `global-error.tsx`; 404 — `not-found.tsx`. `global-error.tsx` не может опираться на CSS/компоненты приложения — правки там только inline-стилями.
- Title-шаблон `%s — Lucy Nails Academy` из `layout.tsx` дописывает суффикс сам: в `metadata.title` дочерних страниц не добавлять «— Lucy Nails Academy» (в `not-found.tsx` и `payment-success/page.tsx` он сейчас продублирован).
- Новые публичные маршруты — добавлять в `sitemap.ts` при необходимости индексации; закрытые — в `disallow` в `robots.ts`.

### Testing Requirements

Своих unit-тестов нет. Проверки — `npm run lint` и `npm run build` (см. `frontend/AGENTS.md`) плюс backend pytest для контрактов API, которые страницы потребляют через `src/lib/api.ts`.

### Common Patterns

- Метаданные страницы задаются через `export const metadata: Metadata` (статические) или `generateMetadata` (динамические, например для `courses/[id]`).
- Публичные списочные данные (`getPublishedCourses`, `getLandingPayload`) грузятся с `next: { revalidate: 120 }` (ISR), всё остальное (включая публичные `getPublicCourse`/`getPublicCourseModules`) — через `apiFetch` с cookie-сессией.
- Клиентские страницы с `useSearchParams` (как `auth/reset-password`) оборачивают содержимое в `<Suspense>`, иначе `next build` падает на prerender.
- Ошибки API на клиенте — `isAuthError(error)` → редирект на `/auth/login`, прочее — `toast.error` (см. `admin/layout.tsx`, `dashboard`).
- Курс/уроки: canonical источник структуры — `ModuleResponse`/`LessonBriefResponse` из `src/lib/api.ts`; лендинг-копирайт мержится поверх через `src/lib/landing/loader.ts`.

## Dependencies

### Internal

- `../components/` — `Header`, `Footer`, `NailsGallery`, `PaymentButton`, `ProgramSection`, `VideoPlayer`, `ModuleList`, `CoursePaymentCTA`, UI-примитивы (`Editor` в админке).
- `../lib/` — `api.ts` (все запросы к backend), `env.ts` (site/API URL), `navigation.ts` (`safeNextPath`), `schemas.ts` (формы auth), `sanitize.ts` (контент урока), `landing/` (контент лендинга).

### External

- `next/font/google` (Inter, Playfair Display), `next/image`, `lucide-react` (иконки), `sonner` (`Toaster`).

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
