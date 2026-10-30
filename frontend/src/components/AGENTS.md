# components

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose

React-компоненты приложения, сгруппированные по назначению: `ui/` — низкоуровневые shadcn-примитивы, `course/` — просмотр курса и видео (Kinescope), `landing/` — секции публичного лендинга и оплата, `layout/` — общий Header/Footer. Отдельные `AGENTS.md` для вложенных подпапок не создаются — вся специфика описана здесь.

## Key Files

Файлов на этом уровне нет — только подпапки (см. ниже).

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `ui/` | shadcn-примитивы (style `new-york`, см. `components.json`) |
| `course/` | Компоненты просмотра курса: список модулей/уроков, видеоплеер, CTA оплаты |
| `landing/` | Секции лендинга: программа курса, галерея, карусель фото работ, оплата (в т.ч. гостевая) |
| `layout/` | `Header`, `Footer` — используются в корневом `app/layout.tsx` |

### `ui/` — shadcn-примитивы

`accordion`, `alert-dialog`, `avatar`, `badge`, `button`, `card`, `dialog`, `dropdown-menu`, `editor` (обёртка над Tiptap для rich-text полей админки), `form`, `input`, `label`, `progress`, `scroll-area`, `select`, `separator`, `sheet` (мобильное меню), `sonner` (`Toaster`; тема через `useTheme` из `next-themes`, `ThemeProvider` в приложении не подключён — фактически всегда `"system"`), `switch`, `table`, `textarea`.

`editor.tsx` экспортирует `Editor({ value, onChange, placeholder, className })` — Tiptap (`StarterKit`, `Underline`, `Link`, `Placeholder`) с собственным тулбаром; используется в `app/admin/courses/[id]`. HTML из редактора на публичной стороне выводить только через `sanitizeHtml` (`src/lib/sanitize.ts`).

### `course/`

| File | Description |
|------|-------------|
| `VideoPlayer.tsx` | `"use client"`. Грузит play-URL урока через `getLessonPlayUrl(lessonId)` (`src/lib/api.ts`) и рендерит его как `<iframe>` (Kinescope-плеер отдаёт готовый embed-URL, отдельного Kinescope SDK на фронте нет). Состояния: `idle/loading/success/error`; при 403 (`error.includes("403")` или `"access required"`) показывает отдельный UI "Доступ ограничен" вместо общей ошибки |
| `ModuleList.tsx` | Аккордеон модулей/уроков курса на `ui/accordion` (публичная витрина программы на `(public)/courses/[id]`, не для кабинета ученика — там своя разметка на странице урока). Экспортирует также типы `Module`/`Lesson` (используются в `app/page.tsx`) |
| `CoursePaymentCTA.tsx` | `"use client"`. Тонкая обёртка над `landing/PaymentButton` (`courseId`, `tariff: "self" \| "support"`, `className`) для использования на странице курса вне лендинга |

### `landing/`

| File | Description |
|------|-------------|
| `PaymentButton.tsx` | `"use client"`. Основная кнопка оплаты: если есть cookie `auth_session=1` — берёт email через `getMe()` и запрашивает `getPaymentLink()`; если сессии нет или `getMe()`/`getPaymentLink()` вернули auth-ошибку (`isAuthError`) — открывает `GuestCheckoutDialog` |
| `GuestCheckoutDialog.tsx` | `"use client"`. Модалка гостевой оплаты: форма email (обязателен) + телефон (опционален) → `getGuestPaymentLink()`; после оплаты пароль приходит на email |
| `ProgramSection.tsx` | Серверный грид карточек модулей курса. Приоритет у копирайта `modules` (уже смерженного `getLandingContent()`, иначе статический `programModules` из `src/lib/landing/course-content.ts`); поля `ModuleResponse.lessons[0]` (`promo_description`, `promo_bullets`, `duration_seconds`) из `apiModules` — только фолбэк для пустых описания/буллетов/длительности, сопоставление по `title`. Фото — `worksPhotos[slug]`, каждая вторая карточка получает `reverseMarquee` |
| `ProgramModuleCard.tsx` | Карточка одного модуля: заголовок, описание, outcome, буллеты, типичные ошибки; медиа-зона — `WorksMarquee` (если есть фото) либо плейсхолдер "Фото работ скоро появятся" |
| `WorksMarquee.tsx` | `"use client"`. Бесконечная лента фото работ модуля на `embla-carousel-react` + `embla-carousel-auto-scroll` (автопрокрутка, `stopOnMouseEnter: true`, `stopOnInteraction: false`; `reverse` — направление `backward` для чередования модулей), ручные стрелки `ChevronLeft`/`ChevronRight` (`scrollPrev`/`scrollNext`), клик по фото открывает лайтбокс (`Dialog`) с prev/next-навигацией. Использует `IntersectionObserver`, чтобы догружать всю ленту только при приближении к вьюпорту (нативный lazy loading не работает для тайлов, сдвигаемых трансформом карусели). Если фото меньше `MIN_TILES` (6) — список зацикливается повтором, чтобы заполнить вьюпорт |
| `NailsGallery.tsx` | `"use client"`. Карусель общей галереи работ на главной (`items` из `getLandingContent().gallery`; `embla-carousel-react`, без автоскролла), с ручными стрелками, точками-индикаторами (`scrollTo`) и анимацией через `framer-motion` |

### `layout/`

| File | Description |
|------|-------------|
| `Header.tsx` | `"use client"`. Разное меню для лендинга (`#about`, `#program`, `#gallery`, `#pricing`, smooth-scroll по якорям) и для кабинета (`/dashboard`); проверяет сессию через `getMe()` в `useEffect` при каждой смене `pathname`; десктоп — `DropdownMenu` с аватаром, моб. — `Sheet`; для `role === "admin"` — ссылка на `/admin/courses` |
| `Footer.tsx` | `"use client"`. Скрывается на страницах уроков (`pathname.includes("/lessons/")`, чтобы не мешать просмотру видео); содержит юридические реквизиты (ИНН, НПД) и ссылки на `/privacy`, `/terms` |

## For AI Agents

### Working In This Directory

- Новый UI-примитив — сначала проверить, нет ли аналога в `ui/`; добавлять по шаблону shadcn (`components.json`: style `new-york`, `cssVariables: true`), не создавать параллельный набор компонентов.
- `course/` и `landing/` — доменные компоненты, не примитивы; не выносить в них общую логику, которая должна жить в `ui/` или `lib/`.
- Компоненты с состоянием/эффектами/браузерными API помечать `"use client"` первой строкой файла (см. существующие файлы выше) — остальные оставлять серверными.
- Оплата — только через `PaymentButton`/`GuestCheckoutDialog`/`CoursePaymentCTA`; не дублировать вызовы `getPaymentLink`/`getGuestPaymentLink` в новых местах напрямую.

### Testing Requirements

Отдельных unit-тестов для компонентов нет. Проверки — `npm run lint` + `npm run build` (см. `frontend/AGENTS.md`); визуальные регрессии — ручная проверка в dev (`.\scripts\dev-frontend.ps1`).

### Common Patterns

- Цветовая палитра лендинга — инлайн hex/oklch (`#db3f6e`, `#D4AF37`, `#fff1f4`) прямо в Tailwind-классах, а не через тему `globals.css`; при правках сохранять согласованность с уже используемыми оттенками.
- Ошибки сети/оплаты — через `sonner` (`toast.error`/`toast.info`), не через `alert()` или молчаливый catch.
- Иконки — `lucide-react` (соответствует `iconLibrary` в `components.json`).

## Dependencies

### Internal

- `../lib/api.ts` — все сетевые вызовы (`getMe`, `getLessonPlayUrl`, `getPaymentLink`, `getGuestPaymentLink`, `logout` и т.д.).
- `../lib/utils.ts` (`cn`) — объединение классов Tailwind.
- `../lib/landing/*` — контент и типы для `landing/`-компонентов.

### External

- `@radix-ui/*` (через `ui/`), `embla-carousel-react` + `embla-carousel-auto-scroll`, `framer-motion`, `lucide-react`, `sonner`, `@tiptap/*` (в `ui/editor.tsx`).

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
