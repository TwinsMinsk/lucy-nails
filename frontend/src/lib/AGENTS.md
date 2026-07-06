<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-07-06 | Updated: 2026-07-06 -->

# lib

## Purpose

Клиентские и серверные утилиты общего назначения: единственный API-клиент (`api.ts`), env-хелперы для build-time переменных Next.js, схемы валидации форм (`zod`), санитайзер HTML для пользовательского контента и слой контента лендинга (`landing/`).

## Key Files

| File | Description |
|------|-------------|
| `api.ts` | **Единственный** клиент API. Экспортирует `apiFetch<T>()` (базовый fetch с cookie-сессией, CSRF-заголовком для unsafe-методов и автоматическим retry через `/auth/refresh` при 401) и десятки доменных функций: auth (`login`, `register`, `getMe`, `logout`), уроки (`getLessonPlayUrl`, `getLesson`, `updateLessonProgress`), курсы (`getPublishedCourses`, `getPublicCourse`, `getPublicCourseModules`, `getMyCourses`, `getCourseProgress`), admin CRUD (курсы/модули/уроки/аналитика/покупки/пользователи/загрузка файлов), лендинг (`getLandingPayload`, `adminUpdateCourseLandingHero`, `adminGetGallery`, `adminReorderGallery` и т.д.), платежи (`getPaymentLink`, `getGuestPaymentLink`). Токены не хранятся в `localStorage` — сервер выставляет httpOnly cookies, фронт держит только non-httpOnly `auth_session=1` для UX (middleware, показ меню) |
| `env.ts` | `getPublicApiUrl()` / `getPublicSiteUrl()` — читают `NEXT_PUBLIC_API_URL`/`NEXT_PUBLIC_SITE_URL` с fallback по `NODE_ENV` (`development` → localhost, иначе → `api.lucysmirnova.ru`/`lucysmirnova.ru`); нормализуют trailing slash и гарантируют `/api`-суффикс/`https://`-схему |
| `navigation.ts` | `safeNextPath()` — валидирует query-параметр `?next=` (защита от open redirect: только относительные пути, не `//`, не `/auth/*`), fallback `/dashboard` |
| `sanitize.ts` | `sanitizeHtml()` — ручной DOM-based санитайзер (без внешних либ) для rich-text контента из Tiptap-редактора: whitelist тегов (`ALLOWED_TAGS`), whitelist протоколов ссылок (`http:`, `https:`, `mailto:`, `tel:`), принудительно рвёт `rel="noopener noreferrer"` + `target="_blank"` на внешних ссылках, полностью вырезает `SCRIPT/STYLE/IFRAME/OBJECT/EMBED` вместе с содержимым |
| `schemas.ts` | `zod`-схемы форм: `LoginSchema`, `RegisterSchema` (с `refine` на совпадение паролей) |
| `utils.ts` | `cn()` — `clsx` + `tailwind-merge`, стандартный shadcn-хелпер |
| `landing/course-content.ts` | Статический (fallback) контент лендинга: `landingCourse` (заголовки, тарифы `self`/`support`, буллеты), `programModules` (11 модулей с `slug`, Kinescope `promoVideoId`/`promoPosterUrl`, описания, буллеты, типичные ошибки), `galleryItems` (7 фото для общей галереи), `fallbackGalleryImages` (SVG-заглушки) |
| `landing/loader.ts` | `getLandingContent()` — server-side загрузчик: пытается получить `getLandingPayload()` с backend и мерджит **поле-в-поле** с `course-content.ts` (любое пустое/`null` значение из API → fallback на статику); модули сопоставляются по `title`; при полном отказе API возвращает `STATIC_FALLBACK` целиком |
| `landing/works-photos.ts` | **AUTO-GENERATED (`scripts/works_photos/process.py`) — не редактировать вручную.** `Record<string, WorkPhoto[]>` (`{ thumb, full }`) по всем 11 категориям в `public/works/`; ключи совпадают со `slug` в `programModules` |

## For AI Agents

### Working In This Directory

- **Не создавать** второй API-клиент и не делать `fetch()` напрямую к backend-эндпоинтам в компонентах/страницах — всё через `api.ts`. Новую доменную функцию добавлять туда же, рядом с соответствующей секцией (`AUTH`, `LESSONS`, `COURSES`, `ADMIN`, `LANDING`, `PAYMENTS`).
- `landing/works-photos.ts` — не редактировать руками; при добавлении/удалении фото в `public/works/` перегенерировать через `scripts/works_photos/process.py` (вне `frontend/`).
- Изменения в `env.ts` затрагивают и build (Railway), и локальную разработку — проверять оба сценария (`NODE_ENV=development` и `production`).
- `sanitize.ts` работает только в браузере (`typeof window === "undefined"` → возвращает `""`) — не вызывать на сервере/при SSR для контента, который должен отрендериться сразу.

### Testing Requirements

Юнит-тестов нет. Косвенная проверка — `npm run build` (ловит типовые ошибки в сигнатурах `api.ts`) и ручная проверка форм/санитайзера в dev. Изменения контрактов `api.ts` сверять с Pydantic-схемами backend (`backend/app/schemas/`) и покрытием в `backend/tests/`.

### Common Patterns

- Публичные GET-запросы без авторизации делают `fetch` напрямую с `next: { revalidate: N }` (ISR), а не через `apiFetch` (который всегда шлёт `credentials: "include"` и не поддерживает `revalidate`).
- Все `admin*` функции в `api.ts` полагаются на то, что `apiFetch` уже приложит cookie-сессию и CSRF — не передавать токены руками.
- Опциональные поля от backend (`?? null`, `nonEmptyString`, `nonEmptyArray` в `loader.ts`) — паттерн "пусто/null на бэке = используем статический fallback", а не "показываем пустое место".

## Dependencies

### Internal

- Используется из `../app/` (страницы, `layout.tsx`, `sitemap.ts`, `robots.ts`) и `../components/` (все клиентские компоненты, обращающиеся к API).

### External

- `zod` — `schemas.ts`.
- Нативные Web API (`fetch`, `document.cookie`, `localStorage`, DOM `Template`) — без дополнительных HTTP/DOM-библиотек.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
