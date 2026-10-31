# components

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-31

## Purpose

React-компоненты приложения, сгруппированные по назначению: `ui/` — низкоуровневые shadcn-примитивы, `analytics/` — согласие на аналитику и счётчики, `certificate/` — получение и выгрузка сертификата, `course/` — просмотр курса и видео (Kinescope), `landing/` — секции публичного лендинга и оплата, `layout/` — общий Header/Footer, `legal/` — согласия при оплате и регистрации, `ads/` — материалы рекламных кампаний в админке. Отдельные `AGENTS.md` для вложенных подпапок не создаются — вся специфика описана здесь.

## Key Files

Файлов на этом уровне нет — только подпапки (см. ниже).

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `ui/` | shadcn-примитивы (style `new-york`, см. `components.json`) |
| `analytics/` | Баннер согласия и запуск аналитики — используются в корневом `app/layout.tsx` |
| `certificate/` | Диалог получения сертификата, кнопки выгрузки, конфетти |
| `course/` | Компоненты просмотра курса: список модулей/уроков, видеоплеер, CTA оплаты |
| `landing/` | Секции лендинга: программа курса, галерея, карусель фото работ, оплата (в т.ч. гостевая) |
| `layout/` | `Header`, `Footer` — используются в корневом `app/layout.tsx` |
| `seo/` | `JsonLd` — `<script type="application/ld+json">` с экранированием `<`, используется на лендинге |
| `legal/` | `PersonalDataConsent` — два отдельных обязательных чекбокса: принятие оферты и согласие на обработку ПДн (гостевая оплата, регистрация); сервер сохраняет время и `consent_version`. Рядом хелперы `NO_CONSENT`, `hasFullConsent`, `focusFirstMissingConsent` |
| `ads/` | Раздел «Реклама» админки (`/admin/ads`): карточки роликов, лист ролика с комментариями, суфлёр, разметка текстов кампании |

### `ui/` — shadcn-примитивы

`accordion`, `alert-dialog`, `avatar`, `badge`, `button`, `card`, `dialog`, `dropdown-menu`, `editor` (обёртка над Tiptap для rich-text полей админки), `form`, `input`, `label`, `progress`, `scroll-area`, `select`, `separator`, `sheet` (мобильное меню), `sonner` (`Toaster`), `switch`, `table`, `textarea`.

### `ads/`

Используются страницами `app/admin/ads/page.tsx` и `app/admin/ads/[id]/page.tsx`. Файлы — только по подписанным ссылкам API через `adsFileUrl()` (`src/lib/api.ts`): `<video>` и `<img>` ходят на хост API без cookies, поэтому `next.config.ts` разрешает `apiOrigin` в `media-src`.

| File | Description |
|------|-------------|
| `ReelCard.tsx` | `"use client"`. Карточка ролика в списке кампании: обложка 9:16, код, длительность, бейдж статуса (`STATUS_BADGE`), крюк; две ежедневные кнопки прямо на карточке — «Скачать видео» и «Скопировать подпись» |
| `ReelSheet.tsx` | `"use client"`. `Sheet` с деталями ролика: плеер, скачивание видео и обложки, подпись и ссылка для сторис с UTM-меткой, текст озвучки с кнопкой «Суфлёр», другие начала ролика (варианты B, C). Для `ads.manage` — смена статуса и ссылка на пост (`https://`), загрузка записи голоса и файлов (`adminUploadAdFile`: файл сырым телом, без `FormData`), удаление своих файлов. Экспортирует `CommentsSection` (комментарии по ролику; удалить можно только свой) — её же использует вкладка кампании |
| `Teleprompter.tsx` | `"use client"`. Полноэкранный текст озвучки для чтения при записи на телефон, четыре размера шрифта |
| `AdText.tsx` | `InlineText` (`**жирный**`, `` `код` ``, голые ссылки) и `RichText` (абзацы, списки `- `/`1. `, таблицы `\| a \| b \|`) для текстов кампании («О кампании», календарь). HTML не рендерится — текст приходит из локального конвейера, `dangerouslySetInnerHTML` не нужен |
| `ad-utils.ts` | Метки статусов (`STATUS_LABELS`, `STATUS_SHORT`), выбор файлов (`mainFile` — без варианта, `hookVariants`, `teamFiles`), `formatSize`, `formatSeconds`, `copyText` (Clipboard API с запасным `execCommand`), `errorText` |

### `analytics/`

| File | Description |
|------|-------------|
| `AnalyticsBootstrap.tsx` | `"use client"`, рендерит `null`. После согласия (`readConsent().analytics`) на `/` и `/courses/[id]` фиксирует UTM (`captureCheckoutAttribution`), шлёт `landing_view` (`trackPublicEvent`) и запускает Яндекс Метрику, если задан `NEXT_PUBLIC_YANDEX_METRIKA_ID`: `tag.js?id=<счётчик>`, Вебвизор, карта кликов, внешние ссылки, e-commerce через `window.dataLayer`. Один экземпляр счётчика живёт, пока посетитель на публичных страницах; SPA-переходы между ними уходят ручным `hit` (сама Метрика `pushState` не считает), уход в кабинет или админку уничтожает счётчик. `isSafeMetrikaLocation` не пускает счётчик на URL с email, телефоном или токеном. Слушает `lucy-consent-updated` и `lucy-metrika-goal`: цели `pricing_view`, `checkout_open`, `checkout` — только на публичных страницах, `purchase` — только на `/payment-success` без query, с суммой (`order_price`) и e-commerce `purchase`, с дедупликацией в `sessionStorage`. При отзыве согласия останавливает счётчик и чистит его cookies. Схема целей: `Docs/06_Tracking/YANDEX_METRIKA.md` |
| `GoalOnView.tsx` | `"use client"`, рендерит `null`. Один раз за просмотр шлёт цель Метрики, когда секция `targetId` видна на 40% (`IntersectionObserver`); на лендинге — `pricing_view` для `#pricing` |
| `ConsentBanner.tsx` | `"use client"`. Баннер на `/`, `/courses/[id]`, `/privacy`, `/terms`: "Только необходимые" / "Разрешить аналитику" → `saveConsent`; после выбора остаётся кнопка настроек. Названия кнопок цитирует `/privacy` — менять вместе. На телефоне кнопки в ряд, высота ограничена `60svh` |

### `certificate/`

| File | Description |
|------|-------------|
| `CertificateClaimDialog.tsx` | `"use client"`. Ввод фамилии и имени (`validateFullName` зеркалит `_FULL_NAME_PATTERN` из `backend/app/schemas/certificate.py`) → `claimCertificate()`, конфетти, экран успеха; отдельный экран для `status === "revoked"` |
| `CertificateActions.tsx` | `"use client"`. Скачивание PDF/PNG по `certificateFileUrl()`, "Ссылка для проверки" через `navigator.share` или буфер обмена |
| `confetti.ts` | `fireConfetti()` — динамический импорт `canvas-confetti`. `useWorker: false` обязателен: в CSP `script-src` нет `blob:` |

### `course/`

| File | Description |
|------|-------------|
| `VideoPlayer.tsx` | `"use client"`. Грузит play-URL урока через `getLessonPlayUrl(lessonId)` (`src/lib/api.ts`) и рендерит его как `<iframe>` (Kinescope-плеер отдаёт готовый embed-URL, отдельного Kinescope SDK на фронте нет). Подписанный URL живёт `expires_in_seconds` (по умолчанию 300 с): за 15 с до конца считается истёкшим и запрашивается заново при `focus`, `pageshow`, `visibilitychange`, наведении или касании плеера. Состояния: `idle/loading/success/error`; при `ApiError` 401/403 (либо `403`/`access required` в тексте ошибки) показывает отдельный UI "Доступ ограничен" и убирает iframe, при прочих ошибках — кнопку "Повторить" |
| `ModuleList.tsx` | Аккордеон модулей/уроков курса (публичная витрина программы на `(public)/courses/[id]`, не для кабинета ученика — там своя разметка на странице урока) |
| `CoursePaymentCTA.tsx` | Тонкая обёртка над `landing/PaymentButton` для использования на странице курса вне лендинга |

### `landing/`

| File | Description |
|------|-------------|
| `PaymentButton.tsx` | `"use client"`. Основная кнопка оплаты; `courseId: null` (нет опубликованного курса) её отключает. Шлёт `cta_click` (`location`: `pricing` или `dashboard_renewal`) и цель Метрики `checkout_open`. Если есть cookie `auth_session=1` — берёт email через `getMe()` и запрашивает `getPaymentLink()`; если сессии нет или `getMe()`/`getPaymentLink()` вернули auth-ошибку (`isAuthError`) — открывает `GuestCheckoutDialog` без тоста (тост повторял заголовок диалога и закрывал его кнопку на телефоне). В запрос уходит `captureCheckoutAttribution()`, перед редиректом — цель Метрики `checkout` |
| `GuestCheckoutDialog.tsx` | `"use client"`. Модалка гостевой оплаты: форма email (обязателен) + телефон (опционален) + обязательное согласие (`legal/PersonalDataConsent`, `CONSENT_VERSION`) → `getGuestPaymentLink()`; после оплаты новому покупателю приходит ссылка `/auth/activate` для создания пароля. Ссылка на вход с `next` для тех, у кого уже есть аккаунт. Поля email и телефона помечены `ym-disable-keys`: Вебвизор их не записывает |
| `ProgramSection.tsx` | Грид карточек модулей курса. Приоритет у `modules` (результат `getLandingContent()`, без них — статический `programModules`); серверные `ModuleResponse` и `lessons[0]` (промо-поля: `promo_description`, `promo_bullets`, `duration_seconds`) сопоставляются по совпадению `title` и заполняют только пустые поля. Фото — `worksPhotos[copy.slug]`. Грид обёрнут в `ProgramModulesExpander`: на экранах уже `md` видны первые `VISIBLE_ON_MOBILE` (3) карточки, остальные скрыты классом `max-md:group-data-[collapsed=true]/program:hidden`, но остаются в разметке. Константа живёт здесь, а не в клиентском модуле: импорт из `"use client"` в серверном компоненте даёт клиентскую ссылку, а не число |
| `ProgramModulesExpander.tsx` | `"use client"`. Кнопка «Показать все N модулей» (только `md:hidden`) снимает `data-collapsed` с обёртки и переводит фокус на первую открытую карточку |
| `ProgramModuleCard.tsx` | Карточка одного модуля: заголовок, описание, результат, буллеты, типичные ошибки; медиа-зона — `WorksMarquee`, если есть фото (без фото карточка показывает только текст). Ошибки — обычный список, не «пилюли»: они не кликабельны. `className` нужен `ProgramSection` для скрытия на телефоне |
| `WorksMarquee.tsx` | `"use client"`. Бесконечная лента фото работ модуля на `embla-carousel-react` + `embla-carousel-auto-scroll` (автопрокрутка, пауза при наведении, `reverse` — обратное направление для чередования модулей), ручные стрелки, клик по фото открывает лайтбокс (`Dialog`) с prev/next-навигацией. Использует `IntersectionObserver`, чтобы догружать всю ленту только при приближении к вьюпорту (нативный lazy loading не работает для тайлов, сдвигаемых трансформом карусели). Если фото меньше `MIN_TILES` (6) — список зацикливается повтором, чтобы заполнить вьюпорт. При `prefers-reduced-motion` (`useReducedMotion`) автопрокрутка не подключается |
| `NailsGallery.tsx` | `"use client"`. Карусель общей галереи работ на главной (`embla-carousel-react`, без автоскролла), с ручными стрелками и анимацией через `framer-motion` (при `prefers-reduced-motion` без пружины). У стрелок и точек русские `aria-label`, точки — кнопки высотой 24 px с `aria-current` |

### `layout/`

| File | Description |
|------|-------------|
| `Header.tsx` | `"use client"`. Разное меню для лендинга (`#about`, `#program`, `#gallery`, `#pricing`, smooth-scroll по якорям) и для кабинета (`/dashboard`); проверяет сессию через `getMe()` в `useEffect` при каждой смене `pathname`; десктоп — `DropdownMenu` с аватаром, моб. — `Sheet`. Ссылка "Админ панель" (`/admin/courses`) показывается только при `user.role === "admin"`. Email в меню помечен `ym-hide-content` для Вебвизора. Логотип — «Lucy Nails Academy» (единое имя бренда, как в письмах и сертификатах). Ссылки меню и кнопки входа — с `lg`, ниже — `Sheet`: на планшете центрированное меню наезжало на логотип |
| `Footer.tsx` | `"use client"`. Скрывается на страницах уроков (`pathname.includes("/lessons/")`, чтобы не мешать просмотру видео); содержит реквизиты ИП (ИНН, ОГРНИП, email и телефон — ссылками `mailto:`/`tel:`) и ссылки на `/privacy`, `/terms` |

## For AI Agents

### Working In This Directory

- Новый UI-примитив — сначала проверить, нет ли аналога в `ui/`; добавлять по шаблону shadcn (`components.json`: style `new-york`, `cssVariables: true`), не создавать параллельный набор компонентов.
- `course/` и `landing/` — доменные компоненты, не примитивы; не выносить в них общую логику, которая должна жить в `ui/` или `lib/`.
- Компоненты с состоянием/эффектами/браузерными API помечать `"use client"` первой строкой файла (см. существующие файлы выше) — остальные оставлять серверными.
- Оплата — только через `PaymentButton`/`GuestCheckoutDialog`/`CoursePaymentCTA`; не дублировать вызовы `getPaymentLink`/`getGuestPaymentLink` в новых местах напрямую.
- Рекламные файлы (`ads/`) — только по подписанным ссылкам из ответа API через `adsFileUrl()`; ссылки живут до 12 часов, после этого страницу нужно перезагрузить. Не подставлять путь к файлу вручную и не раздавать эти файлы через публичный `/uploads`.
- Аналитика — только через `lib/analytics-client.ts` и `lib/attribution.ts`: без согласия ничего не хранить и не отправлять, email и телефон в события и цели не передавать. Новый внешний скрипт или iframe требует правки CSP в `next.config.ts`.

### Testing Requirements

Unit-тесты рядом с кодом: `analytics/AnalyticsBootstrap.test.tsx`, `certificate/CertificateClaimDialog.test.tsx`, `course/VideoPlayer.test.tsx`, `landing/PaymentButton.test.tsx`. Запуск из `frontend/`: `npx vitest run src/components/course/VideoPlayer.test.tsx`. Также `npm run lint` + `npm run build` (см. `frontend/AGENTS.md`); оплату и плеер проверяют `e2e/checkout.spec.ts` и `e2e/learning-reliability.spec.ts`; визуальные регрессии — ручная проверка в dev (`.\scripts\dev-frontend.ps1`).

### Common Patterns

- Цветовая палитра лендинга — инлайн hex/oklch (`#db3f6e`, `#D4AF37`, `#fff1f4`) прямо в Tailwind-классах, а не через тему `globals.css`; при правках сохранять согласованность с уже используемыми оттенками.
- Ошибки сети/оплаты — через `sonner` (`toast.error`/`toast.info`), не через `alert()` или молчаливый catch.
- Иконки — `lucide-react` (соответствует `iconLibrary` в `components.json`).

## Dependencies

### Internal

- `../lib/api.ts` — все сетевые вызовы (`getMe`, `getLessonPlayUrl`, `getPaymentLink`, `getGuestPaymentLink`, `claimCertificate`, `logout` и т.д.).
- `../lib/utils.ts` (`cn`) — объединение классов Tailwind.
- `../lib/landing/*` — контент и типы для `landing/`-компонентов.
- `../lib/attribution.ts`, `../lib/analytics-client.ts`, `../lib/legal.ts`, `../lib/format.ts` — согласие, события, версия оферты, даты.

### External

- `@radix-ui/*` (через `ui/`), `embla-carousel-react` + `embla-carousel-auto-scroll`, `framer-motion`, `lucide-react`, `sonner`, `@tiptap/*` (в `ui/editor.tsx`), `canvas-confetti` (в `certificate/confetti.ts`).

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
