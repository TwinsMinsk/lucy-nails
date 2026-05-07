# Refactoring Roadmap

Программа наведения порядка для дальнейшей разработки. Выполнять маленькими PR: каждый шаг должен либо менять только документацию/конфиги, либо иметь понятную проверку поведения.

## 1. Репозиторий и источники правды

**Цель:** новый разработчик или AI-агент быстро понимает, где актуальная информация.

- `AGENTS.md` — краткий вход для Cursor: стек, правила безопасности, проверки, крупный техдолг.
- `CODEBASE.md` — карта репозитория и текущие зоны риска.
- `README.md` — быстрый старт и ссылки, без дублирования длинных инструкций.
- `Docs/README.md` — индекс всей документации.
- `.cursor/rules/` — короткие правила по областям, без устаревших путей.

**Готово, когда:** ссылки между этими файлами не противоречат друг другу, а подробности живут в тематических документах.

## 2. Артефакты, видео и промо

**Цель:** не засорять Git тяжёлыми локальными файлами.

- `promo-clips/` — финальные локальные промо mp4.
- `video-lessons/` — локальные исходники уроков.
- `scripts/promo/output/` — транскрипты, сегменты и промежуточные mp4.
- `scripts/promo/program.json` — метаданные, которые можно синхронизировать с БД.

**Готово, когда:** `git status` не показывает локальные mp4/pycache/output, а документация объясняет, где хранить видео вне Git.

## 3. Backend

**Цель:** сделать API-слой тоньше, а зависимости и транзакции предсказуемыми.

### 3.1 Auth dependencies

- Проверить импорты `get_current_user`, `require_admin`, access guards.
- Везде использовать `backend/app/core/dependencies.py` как единую точку.
- Убрать связность, где API-модуль импортирует guard через другой API-модуль.

**Кандидаты первой правки:**

- `backend/app/api/courses.py`, `backend/app/api/lessons.py`, `backend/app/api/purchases.py` импортируют `get_current_user` через `app.api.auth`.
- `backend/app/api/upload.py` импортирует `require_admin` через `app.api.admin`.

### 3.2 Admin API

- Разрезать `backend/app/api/admin.py` по доменам: users, courses, modules, lessons, access/analytics.
- Вынести Pydantic-схемы из router-файла в `backend/app/schemas/`.
- Сохранить текущие URL и response shape, если нет отдельной задачи на изменение API.
- Перед разрезанием добавить или расширить тесты admin CRUD/access.

**Предлагаемая структура:**

```text
backend/app/api/admin/
├── __init__.py          # собирает router с тем же prefix
├── users.py             # список пользователей и детали
├── courses.py           # CRUD курсов
├── modules.py           # CRUD модулей
├── lessons.py           # CRUD уроков
├── access.py            # ручная выдача доступа
└── analytics.py         # аналитика и покупки
```

Схемы вынести в `backend/app/schemas/admin.py` или по доменам (`admin_course.py`, `admin_lesson.py`), если один файл станет слишком большим.

### 3.3 Транзакции

- Зафиксировать решение для `backend/app/core/database.py`: авто-commit в dependency или явные commits в сервисах/роутерах.
- После решения убрать смешанный стиль.
- Документировать правило в `AGENTS.md`/backend rule.

Текущее состояние: `get_db` делает commit после успешного request, при этом отдельные endpoint/service уже вызывают `await db.commit()`. Перед изменением нужна проверка admin/payments/lesson-service сценариев.

### 3.4 Main и production-hardening

- Проверить dev-seed с известными паролями.
- Проверить CORS/Trusted Hosts/JWT defaults.
- Не менять production поведение без теста или smoke-проверки.

## 4. Frontend

**Цель:** разделить клиентский API, крупные страницы и UI-состояние по понятным границам.

### 4.1 API client

- Оставить общий `apiFetch`, обработку CSRF/auth/errors в client module.
- Разнести домены: auth, courses/modules/lessons, admin, payments, progress.
- Типы держать рядом с доменом или в отдельном `frontend/src/lib/types.ts`.
- Сохранять публичные exports на время миграции потребителей, если это снижает риск.

**Предлагаемая структура:**

```text
frontend/src/lib/api/
├── client.ts       # apiFetch, csrf, auth retry, ApiError helpers
├── auth.ts         # login/register/me/logout
├── courses.ts      # public courses, modules, my courses
├── lessons.ts      # lesson detail, play URL, progress
├── admin.ts        # admin CRUD/API
├── payments.ts     # payment links
└── types.ts        # shared DTOs, если типы нужны нескольким доменам
```

На первом PR можно оставить `frontend/src/lib/api.ts` как compatibility barrel, который реэкспортирует новые модули.

### 4.2 Лендинг

- Разделить статические fallback-данные, серверные данные из API и компоненты секций.
- Исключить рассинхрон цен/модулей между `page.tsx`, `ProgramSection` и backend.
- Документировать, какой источник данных считается главным для главной страницы.

### 4.3 Админка

- Разбить крупные client pages на формы, таблицы, dialogs и hooks.
- Переиспользовать паттерны загрузки, auth error handling и toast.
- Не менять URL админки и backend contract без отдельного шага.

### 4.4 Конфиги

- Зафиксировать Tailwind v4 через `frontend/src/app/globals.css`.
- Проверить `frontend/components.json`: alias `hooks` должен соответствовать реальной структуре или быть удалён/создан.
- Ужесточать ESLint постепенно после чистки файлов.

Текущее состояние: `frontend/components.json` указывает `hooks: "@/hooks"`, но `frontend/src/hooks/` отсутствует. Решение принять перед добавлением новых shadcn-компонентов или hooks.

## 5. Проверки и CI

**Цель:** локальные команды, docs и CI описывают один и тот же quality gate.

- Backend: `ruff check backend/app backend/tests`, Alembic upgrade, `pytest backend/tests`.
- Frontend: `npm ci`, `npm run lint`, `npm run build` с `NEXT_PUBLIC_API_URL` и `NEXT_PUBLIC_SITE_URL`.
- Миграции: добавить отдельный smoke-test на чистой БД или явно держать риск drift в документации.
- Frontend tests: принять отдельное решение, добавлять ли Vitest/Playwright, или пока оставить lint/build/manual smoke.

## 6. Проверка текущей грязной ветки

На момент создания roadmap в рабочем дереве уже были продуктовые изменения, не относящиеся к документационной уборке:

- Backend promo/course changes: `backend/app/api/*`, `backend/app/models/lesson.py`, `backend/app/schemas/lesson.py`, `backend/app/services/kinescope_service.py`, `backend/scripts/seed_data.py`, новые Alembic migrations.
- Frontend landing/program changes: `frontend/src/app/page.tsx`, `frontend/src/lib/api.ts`, `frontend/src/components/landing/*`.
- Promo tooling: `scripts/promo/*`, `scripts/__init__.py`.

Не смешивать эти изменения с PR по docs/rules/artifacts без явного решения. Перед техническим рефакторингом сделать отдельный `git diff --stat` и определить, какие файлы уже менялись пользователем.

## Рекомендуемые PR

1. Docs/rules/artifacts: источники правды, `.gitignore`, индексы.
2. Backend dependencies: auth imports без изменения поведения.
3. Backend admin tests: покрытие текущего контракта.
4. Backend admin split: доменные роутеры и схемы.
5. Frontend api split: client + доменные модули.
6. Frontend pages split: лендинг и админка.
7. Quality gates: миграционный smoke-test, frontend test decision, постепенное ужесточение lint.
