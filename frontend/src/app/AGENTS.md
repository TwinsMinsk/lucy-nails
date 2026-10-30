# app

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose

Маршруты Next.js App Router: публичный лендинг, страницы курса и проверки сертификата, вход и активация аккаунта, приватный кабинет ученика с видео-уроками, админ-панель управления контентом, учениками, продажами и системой. Корневой `layout.tsx` подключает шрифты (`Inter`, `Playfair Display`), глобальный `Header`/`Footer`/`Toaster`, `AnalyticsBootstrap`/`ConsentBanner` и SEO-метаданные (`metadataBase` из `getPublicSiteUrl()`).

## Key Files

| File | Description |
|------|-------------|
| `layout.tsx` | Root layout: шрифты через `next/font/google`, `Header`/`Footer` вокруг `children`, глобальные `<Metadata>` (title template `%s — Lucy Nails Academy`, OpenGraph/Twitter card, иконка `/icon.svg`), `AnalyticsBootstrap`, `ConsentBanner`, `<Toaster />` (sonner) |
| `page.tsx` | Лендинг (`/`): hero, программа (`ProgramSection`), галерея (`NailsGallery`), тариф (`PaymentButton`). Контент, цена, срок доступа и `courseId` — из `getLandingContent()` (поле `course` в `LandingPayload`), модули — `getPublicCourseModules()` (ошибка → `null`). Без опубликованного курса цена не показывается ("Продажи пока недоступны"), оплата отключена. `generateMetadata`: title и description для поиска — `HOME_TITLE`/`HOME_DESCRIPTION` из `lib/seo.ts`, OpenGraph и Twitter — из hero. JSON-LD (`Organization`, `Person`, `Course` с ценой из `course`) рендерит `components/seo/JsonLd.tsx` |
| `globals.css` | Tailwind v4 (`@import "tailwindcss"`), typography-плагин, кастомные CSS-переменные темы (`--primary`, `--surface`, `--text-primary` и т.д. в oklch), кастомный `@utility container` (Tailwind v4 убрал авто-центрирование — возвращено вручную) |
| `error.tsx`, `global-error.tsx`, `not-found.tsx` | Граница ошибок, граница ошибок корневого layout (рендерит свои `<html>`/`<body>`), страница 404 |
| `robots.ts` | `MetadataRoute.Robots`: disallow `/admin`, `/dashboard`, `/profile`, `/courses/*/lessons/*`; ссылка на `sitemap.xml` |
| `sitemap.ts` | `MetadataRoute.Sitemap`: статичные `/`, `/privacy`, `/terms` + динамические `/courses/:id` из `getPublishedCourses()`, кроме курса лендинга (у него canonical `/`) (fallback на статичные при ошибке API) |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `(public)/` | Route group без auth: `auth/login` (пароль, MFA-код, настройка MFA с QR и резервными кодами, шаг подтверждения email, `?next=` через `safeNextPath`), `auth/register` (согласия `PersonalDataConsent`), `auth/activate` (первый пароль по ссылке из письма), `auth/forgot-password`, `auth/reset-password` (общий `auth/layout.tsx` задаёт title и `noindex`: сами страницы клиентские и `metadata` экспортировать не могут), `courses/[id]` (публичная страница курса; у курса лендинга canonical `/`), `certificate/[number]` (публичная проверка сертификата, свой `not-found.tsx`) |
| `(protected)/` | Route group за гвардом `src/proxy.ts`: `dashboard` (мои курсы, продление истёкшего доступа, сертификаты, чат куратора для тарифа `support`), `profile` (смена пароля, выход), `courses/[id]/lessons/[lessonId]` (просмотр урока: `VideoPlayer`, конспект через `sanitizeHtml`, прогресс, сертификат) |
| `admin/` | Панель администратора, см. раздел ниже |
| `payment-success/` | Страница возврата после оплаты Prodamus: `payment-status.tsx` опрашивает `/payments/orders/{order_id}/status?token=` (каждые 3 с, до 20 попыток), при `paid` убирает токен из URL и отправляет цель Метрики `purchase` |
| `privacy/`, `terms/` | Статические юридические страницы |

### `admin/`

Клиентская панель. `layout.tsx` загружает `getMe()` и `adminGetCapabilities()`: пустые роли или права → `/dashboard`, ошибка → `/auth/login`. Меню и маршруты фильтруются по permissions (`adminNavItems`, `adminRouteRules`), запрещённый маршрут редиректит на первый разрешённый. `permissions.tsx` даёт `AdminPermissionsContext` и `useAdminPermission(name)` для скрытия действий внутри страниц; `*` означает все права (`legacy_admin`).

| Route | Permission в layout | Назначение |
|-------|---------------------|------------|
| `/admin` | `analytics.read` | Операционный обзор (`adminGetDashboard`); сверка расхождений (`adminGetReconciliation`) при `commerce.read` |
| `/admin/users` | `users.read` | Ученики: поиск, карточка, прогресс по урокам. Создание и выдача доступа — `access.manage`; заметки, теги, ссылка для входа — `users.manage` |
| `/admin/access` | `users.read` | Доступы (entitlements): поиск и статус; отзыв, продление, смена состояния — `access.manage` |
| `/admin/orders` | `commerce.read` | Заказы, журнал webhook, сверка; возвраты — `refunds.manage` |
| `/admin/purchases` | `commerce.read` | Старая страница покупок с отзывом доступа; в меню нет, открывается только прямой ссылкой |
| `/admin/courses`, `/admin/courses/[id]` | `content.manage` | CRUD курсов, загрузка обложек, проверка видео (`adminCheckVideoHealth`); редактор модулей и уроков (`Editor`) |
| `/admin/landing` | `content.manage` | Редактор hero, модулей и галереи лендинга, импорт статической галереи в БД |
| `/admin/certificates` | `certificates.manage` | Поиск, скачивание, перевыпуск, отзыв |
| `/admin/notifications` | `notifications.manage` | Очередь сообщений: фильтры, повторная отправка |
| `/admin/analytics` | `analytics.read` | Отчёты за период, источники (`basis`: `payment`/`acquisition`), CSV (`adminReportSourcesCsvUrl`) |
| `/admin/system` | `audit.read` или `system.manage_roles` | Статус и журнал аудита — `audit.read`; роли команды — `system.manage_roles`; выключатель checkout — `system.manage_operations` |

## For AI Agents

### Working In This Directory

- Server Components по умолчанию; `'use client'` — только там, где нужны хуки состояния/эффекты/браузерные API (формы, карусели, дропдауны). Сейчас серверные страницы — `page.tsx`, `(public)/courses/[id]`, `(public)/certificate/[number]`, `payment-success/page.tsx`, `privacy`, `terms`; кабинет, auth и вся админка клиентские.
- `(public)` и `(protected)` — route groups, не влияют на URL. Реальная защита `(protected)` и `admin/` — на уровне `src/proxy.ts` (UX-редирект по cookie) **и** backend-эндпоинтов (источник правды по правам).
- Отдельные `AGENTS.md` для вложенных маршрутов **не создавать** — вся специфика документируется здесь.
- Новый маршрут админки — добавить в `adminNavItems` или `adminRouteRules` в `admin/layout.tsx`: для маршрута без правила layout не проверяет права. Проверка на backend при этом обязательна.
- Лендинг переживает отказ API: `getLandingContent()` возвращает статический контент с `course: null`, то есть маркетинг без цены и оплаты. Цену и `courseId` из статики не подставлять. `sitemap.ts` при ошибке отдаёт статичные URL. `(public)/courses/[id]` при любой ошибке API отдаёт `notFound()`, а ошибка `verifyCertificate` на странице сертификата уходит в `error.tsx`.
- Новые публичные маршруты — добавлять в `sitemap.ts` при необходимости индексации; закрытые — в `disallow` в `robots.ts`.

### Testing Requirements

Unit-тесты рядом с кодом: `home.test.tsx` (метаданные, привязка цены и checkout к опубликованному курсу), `(protected)/learning.test.tsx` (ошибки кабинета, предпросмотр, отозванный сертификат), `(public)/auth/login/page.test.tsx` (подтверждение email), `admin/operations.test.tsx` (права и фильтры в URL), `admin/analytics/page.test.tsx` (отчёты по источникам). Браузерные сценарии — `../../e2e/`.

Проверки из `frontend/`: `npm test`, `npm run lint`, `npm run build` (см. `frontend/AGENTS.md`) плюс backend pytest для контрактов API, которые страницы потребляют через `src/lib/api.ts`.

### Common Patterns

- Метаданные страницы задаются через `export const metadata: Metadata` (статические) или `generateMetadata` (динамические: лендинг, `courses/[id]`, `certificate/[number]`). Суффикс сайта добавляет title template из `layout.tsx`; к `page.tsx` того же сегмента (лендинг) шаблон не применяется. Next.js заменяет `openGraph` и `twitter` родителя целиком, поэтому страница со своим `openGraph` разворачивает `baseOpenGraph` из `lib/seo.ts`.
- Динамические `params` — `Promise`: `await params` на сервере, `use(params)` в клиентском компоненте (страница урока).
- Данные: `getLandingPayload` и `getPublishedCourses` — `next: { revalidate: 120 }` (ISR); `getPublicCourse`/`getPublicCourseModules` — `apiFetch` без кэша; `verifyCertificate` — `cache: "no-store"`; приватные — через `apiFetch` с cookie-сессией.
- Курс/уроки: canonical источник структуры — `ModuleResponse`/`LessonBriefResponse` из `src/lib/api.ts`; лендинг-копирайт мержится поверх через `src/lib/landing/loader.ts`.
- Страница урока: `403` на `getCourseProgress` допустим только для урока с `is_preview` (предпросмотр без отметки прогресса), иначе экран "Доступ к курсу закончился или ещё не открыт". Сбой загрузки кабинета и урока показывает кнопку "Повторить", а не пустое состояние.
- Секретные токены из URL (`auth/activate`, `payment-success`) читаются один раз в `useState` и убираются через `history.replaceState`.
- Страницы с `useSearchParams` обёрнуты в `Suspense`. Списки админки (`users`, `access`, `orders`, `notifications`) хранят `search`, фильтры и `offset` в URL через `router.replace`, грузят по `limit: 50` и отбрасывают устаревшие ответы счётчиком `generation`.
- Даты API выводить через `formatApiDateTime`/`formatApiDate`/`parseApiDate` из `src/lib/format.ts`: backend отдаёт naive UTC.

## Dependencies

### Internal

- `../components/` — `Header`, `Footer`, `AnalyticsBootstrap`, `ConsentBanner`, `NailsGallery`, `PaymentButton`, `ProgramSection`, `VideoPlayer`, `ModuleList`, `CoursePaymentCTA`, `CertificateActions`, `CertificateClaimDialog`, `PersonalDataConsent`, `Editor`, UI-примитивы.
- `../lib/` — `api.ts` (запросы к backend), `env.ts` (site/API URL), `format.ts`, `navigation.ts`, `sanitize.ts`, `schemas.ts`, `legal.ts`, `analytics-client.ts`, `landing/` (контент лендинга).

### External

- `next/font/google` (Inter, Playfair Display), `next/image`, `lucide-react` (иконки), `sonner` (`Toaster`), `qrcode.react` (QR для MFA), `react-hook-form` + `zod` (вход и регистрация).

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
