# lib

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose

Клиентские и серверные утилиты общего назначения: единственный API-клиент (`api.ts`), env-хелперы для build-time переменных Next.js, схемы валидации форм (`zod`), санитайзер HTML для пользовательского контента, форматирование дат и длительностей, согласие и аналитика, слой контента лендинга (`landing/`).

## Key Files

| File | Description |
|------|-------------|
| `api.ts` | **Единственный** клиент API. Экспортирует `apiFetch<T>()` (базовый fetch с cookie-сессией, CSRF-заголовком для unsafe-методов и автоматическим retry через `/auth/refresh` при 401; параллельные 401 делят один refresh), `ApiError` (`status`, `detail`), `isAuthError()` и десятки доменных функций: auth (`login`, `setupMfa`, `confirmMfa`, `register`, `resendVerification`, `getMe`, `logout`, `changePassword`, `forgotPassword`, `resetPassword`, `activateAccount`), уроки (`getLessonPlayUrl`, `getLesson`, `updateLessonProgress`), курсы (`getPublishedCourses`, `getPublicCourse`, `getPublicCourseModules`, `getMyCourses`, `getMyExpiredCourses`, `getCourseProgress`), admin (CRUD курсов/модулей/уроков, загрузка файлов, дашборд, ученики, доступы, заказы, возвраты, уведомления, команда и роли, аудит, система, сертификаты, отчёты), лендинг (`getLandingPayload`, `adminUpdateCourseLandingHero`, `adminGetGallery`, `adminReorderGallery` и т.д.), платежи (`getPaymentLink`, `getGuestPaymentLink`), аналитика (`postAnalyticsEvent`), сертификаты (`claimCertificate`, `getCertificateStatus`, `verifyCertificate`, `certificateFileUrl`). Токены сервер выставляет в httpOnly cookies, фронт держит только non-httpOnly `auth_session=1` для UX (proxy, показ меню). Старые `access_token`/`refresh_token` из `localStorage` `saveTokens` и `clearTokens` удаляют, но `getAuthToken`/`getRefreshToken` пока читают их, если они остались. Telegram-хелперы (`getTelegramStatus`, `createTelegramLink`, `disconnectTelegram`) экспортированы, в UI не подключены |
| `env.ts` | `getPublicApiUrl()` / `getPublicSiteUrl()` — читают `NEXT_PUBLIC_API_URL`/`NEXT_PUBLIC_SITE_URL` с fallback по `NODE_ENV` (`development` → localhost, иначе → `api.lucysmirnova.ru`/`lucysmirnova.ru`); нормализуют trailing slash и добавляют `/api`-суффикс к URL со схемой; значению без схемы дописывают только `https://` |
| `navigation.ts` | `safeNextPath()` — валидирует query-параметр `?next=` (защита от open redirect: только относительные пути, не `//`, без обратного слэша и управляющих символов, не `/auth/*`; проверка повторяется на каждом уровне percent-декодирования), fallback `/dashboard` |
| `sanitize.ts` | `sanitizeHtml()` — ручной DOM-based санитайзер (без внешних либ) для rich-text контента из Tiptap-редактора: whitelist тегов (`ALLOWED_TAGS`), whitelist протоколов ссылок (`http:`, `https:`, `mailto:`, `tel:`), принудительно ставит `rel="noopener noreferrer"` + `target="_blank"` на ссылках с безопасным `href`, полностью вырезает `SCRIPT/STYLE/IFRAME/OBJECT/EMBED` вместе с содержимым |
| `schemas.ts` | `zod`-схемы форм: `LoginSchema`, `RegisterSchema` (с `refine` на совпадение паролей) |
| `format.ts` | `parseApiDate()` читает naive datetime от backend как UTC; `formatApiDateTime`/`formatApiDate` выводят в `Europe/Moscow`; `formatDays`, `formatLessonDuration`, `formatCourseDuration` |
| `legal.ts` | `CONSENT_VERSION` — версия оферты и согласия на ПДн, зеркало `CONSENT_VERSION` из `backend/app/core/legal.py` |
| `attribution.ts` | Согласие на аналитику и UTM: `readConsent`, `saveConsent` (при отказе удаляет идентификаторы и атрибуцию; всегда рассылает событие `lucy-consent-updated`), `captureCheckoutAttribution` (first/last touch и `anonymous_id`; без согласия — `undefined`), `CONSENT_STORAGE_KEY`, `CONSENT_POLICY_VERSION` |
| `analytics-client.ts` | `trackPublicEvent` (`landing_view`, `cta_click` → `postAnalyticsEvent`; только при согласии, ошибки глотает) и `sendYandexGoal` (`pricing_view`, `checkout_open`, `checkout`, `purchase` с необязательным `YandexPurchase` — сумма, валюта, курс; через событие `lucy-metrika-goal`, которое слушает `AnalyticsBootstrap`) |
| `utils.ts` | `cn()` — `clsx` + `tailwind-merge`, стандартный shadcn-хелпер |
| `landing/course-content.ts` | Статический контент лендинга: `landingCourse` (заголовки, тариф `self`, буллеты), `programModules` (11 модулей с `slug`, Kinescope `promoVideoId`/`promoPosterUrl`, описания, буллеты, типичные ошибки), `galleryItems` (7 фото для общей галереи), `fallbackGalleryImages` (SVG-заглушки, нигде не импортируются) |
| `landing/loader.ts` | `getLandingContent()` — server-side загрузчик. Успешный `getLandingPayload()` авторитетен: состав и порядок модулей и галереи — как в API, цена и срок — только из `course`. `??`-fallback на `programModules` работает лишь для `null`-полей модулей, совпавших по `title` (оттуда же `slug` для фото); неизвестные модули получают `slug = id` и пустые поля. При отказе API возвращает `STATIC_FALLBACK` с `course: null` — маркетинг без цены и оплаты |
| `landing/works-photos.ts` | **AUTO-GENERATED (`scripts/works_photos/process.py`) — не редактировать вручную.** `Record<string, WorkPhoto[]>` (`{ thumb, full }`) по всем 11 категориям в `public/works/`; ключи совпадают со `slug` в `programModules` |

## For AI Agents

### Working In This Directory

- **Не создавать** второй API-клиент и не делать `fetch()` напрямую к backend-эндпоинтам в компонентах/страницах — всё через `api.ts` (исключение сейчас одно: `src/app/payment-success/payment-status.tsx`). Новую доменную функцию добавлять туда же, рядом с соответствующей секцией (`AUTH`, `LESSONS`, `COURSES`, `ADMIN`, `ADMIN CRUD`, `LANDING`, `PAYMENTS`, `CERTIFICATES`).
- `landing/works-photos.ts` — не редактировать руками; при добавлении/удалении фото в `public/works/` перегенерировать через `scripts/works_photos/process.py` (вне `frontend/`).
- Изменения в `env.ts` затрагивают и build (Railway), и локальную разработку — проверять оба сценария (`NODE_ENV=development` и `production`). `process.env.NEXT_PUBLIC_*` читать только статически.
- `sanitize.ts` работает только в браузере (`typeof window === "undefined"` → возвращает `""`) — не вызывать на сервере/при SSR для контента, который должен отрендериться сразу. Новый формат в `ui/editor.tsx` требует проверки `ALLOWED_TAGS`.
- `legal.ts` менять вместе с `backend/app/core/legal.py`. Смена `CONSENT_POLICY_VERSION` в `attribution.ts` сбрасывает сохранённое согласие на аналитику.

### Testing Requirements

Unit-тесты рядом с кодом: `api.test.ts` (query-параметры, `ApiError`, общий refresh), `attribution.test.ts`, `analytics-client.test.ts`, `format.test.ts`, `navigation.test.ts`, `landing/loader.test.ts`. Запуск из `frontend/`: `npx vitest run src/lib/api.test.ts`. Для `env.ts`, `sanitize.ts`, `schemas.ts` тестов нет. `npm run build` ловит типовые ошибки в сигнатурах `api.ts`. Изменения контрактов `api.ts` сверять с Pydantic-схемами backend (`backend/app/schemas/`) и покрытием в `backend/tests/`.

### Common Patterns

- Кэшируемые публичные GET (`getPublishedCourses`, `getLandingPayload`) делают `fetch` напрямую с `next: { revalidate: 120 }` (ISR), а не через `apiFetch` (который всегда шлёт `credentials: "include"`). `verifyCertificate` — напрямую с `cache: "no-store"`. `getPublicCourse`/`getPublicCourseModules` — через `apiFetch` без кэша.
- Все `admin*` функции в `api.ts` полагаются на то, что `apiFetch` уже приложит cookie-сессию и CSRF — не передавать токены руками. Query-параметры собирает `queryString()`, пустые значения пропускаются. `adminUploadFile` отправляет multipart мимо `apiFetch`.
- Опциональные поля лендинга в `loader.ts`: `null` у известного модуля = статический fallback, а пустая строка или пустой массив из CMS — намеренное значение, его показываем как есть.

## Dependencies

### Internal

- Используется из `../app/` (страницы, `layout.tsx`, `sitemap.ts`, `robots.ts`) и `../components/` (все клиентские компоненты, обращающиеся к API).

### External

- `zod` — `schemas.ts`; `clsx`, `tailwind-merge` — `utils.ts`.
- Нативные Web API (`fetch`, `document.cookie`, `localStorage`, DOM `Template`) — без дополнительных HTTP/DOM-библиотек.

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
