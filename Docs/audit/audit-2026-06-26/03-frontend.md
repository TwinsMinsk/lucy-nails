# 03 — Frontend (Next.js 16 App Router / React 19 / Tailwind v4 / shadcn)

Дата: 2026-06-26. Baseline: `npm run lint` → 0 errors, 3 warnings; `npm run build` → success (Next 16.1.4 Turbopack, 18 маршрутов). См. [05-tests-ci.md](05-tests-ci.md).

## Дисциплина API-клиента — отлично
- Единый клиент `frontend/src/lib/api.ts` (`apiFetch`, 45 рёбер в Graphify) с инъекцией токена, CSRF, refresh-flow на 401.
- Прямые `fetch(` присутствуют только **внутри** `api.ts` (сам клиент `:122`, refresh `:81`, upload `:163`, публичные SSR-данные с `revalidate` `:324,:776`). **Обходов клиента в компонентах нет** — подтверждено.

## Типобезопасность — хорошо
- `tsconfig.json`: `strict: true`. Подавлений типов (`@ts-ignore`/`@ts-expect-error`) — 0.
- ### FE-01 — Lint-предупреждения (3) · LOW · чистый рефакторинг
  - `src/app/admin/courses/page.tsx:6` — неиспользуемый импорт `Upload`.
  - `src/components/ui/editor.tsx:19` — неиспользуемый `LinkIcon`.
  - `src/components/ui/editor.tsx:31` — `editor: any` (Unexpected any). Типизировать через `Editor` из `@tiptap/react`.
  - Быстрая победа: убрать неиспользуемые импорты, типизировать параметр.

## Server/Client границы
- 37 файлов с `'use client'`. 13 из них — обёртки Radix в `components/ui/*` (accordion, dialog, select, switch, table и т.п.).
- ### Переоценка (НЕ дефект): эти обёртки `'use client'` обоснованы. Примитивы Radix используют контекст/refs/клиентские хуки; в паттерне shadcn `'use client'` для них штатно требуется. **Снимать не нужно** — снятие сломает SSR/гидрацию. Изначальная гипотеза «over-clientized» отклонена.

## Утилиты / god-узлы
- ### FE-02 — `api.ts` (890 строк) — кандидат на доменную декомпозицию · MED · чистый рефакторинг. Разнести по доменам (auth/courses/admin/payments), сохранив единый `apiFetch`. Совпадает с `CODEBASE.md:56,64`.
- `cn()` (`lib/utils.ts`, 6 строк, 97 рёбер, 22 импорта) — высокая связность **ожидаема и идиоматична** для Tailwind/shadcn. **Не трогать.**
- Мёртвого кода в `lib/` не обнаружено; все утилиты импортируются.

## Крупные client-страницы
- ### FE-03 — Разгрузить крупные admin-страницы · MED · чистый рефакторинг
  - `admin/landing/page.tsx` (969), `admin/courses/[id]/page.tsx` (591), `admin/courses/page.tsx` (474).
  - Вынести формы/секции в компоненты. Совпадает с `CODEBASE.md:64`.

## Loading/Error/SEO/доступность
- Нет файлов `error.tsx` / `loading.tsx` / `not-found.tsx` (кастомный `/_not-found` генерируется дефолтный). Обработка ошибок — через try/catch в client-компонентах. → FE-04 (добавить error/loading boundaries для protected/admin), LOW/MED, поведение не меняется существенно.
- SEO: `robots.ts`, `sitemap.ts`, метаданные на `layout.tsx`/`page.tsx`/`payment-success`. Билд подтверждает prerender статических маршрутов и `revalidate 2m` на `/` и `/sitemap.xml`.
- Доступность: опирается на WCAG-совместимые примитивы Radix; `alt` у `Image` присутствует в просмотренных местах. Грубых нарушений не выявлено.

## Зависимости (см. также [05-tests-ci.md](05-tests-ci.md))
- `npm audit`: **10 уязвимостей (4 high, 5 moderate, 1 low)** — picomatch ReDoS (транзитивно через `tinyglobby`/`next`), postcss XSS (`<8.5.10`). Фикс есть, но `--force` тянет `next@16.2.9` вне диапазона. → DEP-01, **без апгрейдов в этой фазе**.
- `npm outdated`: множество minor/patch (Radix, TipTap 3.17→3.27, framer-motion, react-hook-form, zod, tailwind 4.1→4.3); `next 16.1.4→16.2.9` (security-relevant). Мажоры: `lucide-react 0.562→1.21`, `typescript 5.9→6.0`, `eslint 9→10`.
