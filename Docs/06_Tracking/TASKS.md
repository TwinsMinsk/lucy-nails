# Task List: Платформа видео-курсов

> Статус: [ ] Not Started | [/] In Progress | [x] Done
> **Последнее обновление:** 05.05.2026

---

## Production readiness (MVP)
- [x] Инварианты: 30 дней доступа после оплаты, два тарифа, Prodamus webhook + phone/email, premium Telegram в ЛК
- [/] Полный чеклист деплоя и hardening — текущий MVP scope: безопасная покупка Prodamus, доступ к урокам, кабинет, базовая админка, Railway deploy
- [ ] Backend hardening: CORS/Trusted Hosts/JWT/seed/rate limit/Kinescope без mock в prod
- [ ] Payment hardening: идемпотентный webhook, повторы, гонки, проверки подписи и суммы
- [ ] После payment-first: письмо «доступ открыт» для уже существующих пользователей; страница «Сменить пароль» в ЛК (одноразовый пароль из письма)
- [ ] Frontend hardening: auth/session UX, protected/admin guards, безопасный payment CTA
- [ ] Staging smoke-test перед production

## Фаза 0: Setup (2-3 дня) — 90%
- [x] 0.1 Инициализация репозитория (.gitignore, README.md)
- [x] 0.2 Создание .env.example
- [x] 0.3 Setup Frontend (Next.js 16 + TypeScript + Tailwind)
  - [x] Инициализация Next.js
  - [ ] Настройка ESLint + Prettier
  - [x] Установка shadcn/ui (21 компонент)
- [x] 0.4 Setup Backend (FastAPI + PostgreSQL)
  - [x] Виртуальное окружение
  - [x] Структура папок по ARCHITECTURE.md
  - [x] requirements.txt установлен
  - [x] Ruff (линтер Python) — установлен v0.9.4
- [x] 0.5 Настройка PostgreSQL (создание БД nails_course)
- [ ] 0.6 Pre-commit hooks (Husky, lint-staged)

---

## Фаза 1: Database (3-4 дня) — 95%
- [x] 1.1 Модели SQLAlchemy (7 таблиц)
  - [x] `users`
  - [x] `courses`
  - [x] `modules`
  - [x] `lessons`
  - [x] `purchases`
  - [x] `progress`
  - [x] `certificates`
- [x] 1.2 Alembic миграции
- [x] 1.3 Seed-данные для разработки
- [ ] 1.4 Unit-тесты моделей (pytest)

---

## Фаза 2: Backend Core (1-1.5 недели) — 95%
- [x] 2.1 Аутентификация (JWT)
  - [x] POST `/api/auth/register`
  - [x] POST `/api/auth/login`
  - [x] POST `/api/auth/logout`
  - [x] GET `/api/auth/me`
  - [x] FastAPI Dependencies для прав доступа
- [x] 2.2 API Курсов и Модулей
  - [x] GET `/api/courses`
  - [x] GET `/api/courses/{id}`
  - [x] GET `/api/courses/{courseId}/modules`
  - [x] GET `/api/modules/{id}`
- [x] 2.3 API Уроков и Прогресса
  - [x] GET `/api/modules/{moduleId}/lessons`
  - [x] GET `/api/lessons/{id}`
  - [x] POST `/api/lessons/{id}/progress`
- [x] 2.4 API Покупок
  - [x] POST `/api/purchases/create`
  - [x] GET `/api/purchases/my`
- [x] 2.5 Тесты API (pytest + httpx)
  - [x] test_auth.py
  - [x] test_courses.py
  - [x] test_kinescope.py
  - [x] test_purchases.py

---

## Фаза 3: Frontend Core (1.5-2 недели) — 60%
- [x] 3.1 Layout и навигация (Header 14.7KB, Footer 2.3KB)
- [x] 3.2 Главная страница (лендинг 17.1KB)
- [x] 3.3 Страница курса (список модулей, 15KB)
- [x] 3.4 Авторизация (Login 4.9KB, Register UI)
- [x] 3.5 Личный кабинет (Dashboard 9KB — с прогрессом)
- [x] 3.6 Просмотр курса (уроки → видео, VideoPlayer 5.2KB)
- [/] 3.7 Прогресс-бар (курс + модули)
  - [x] Общий прогресс курса в Dashboard
  - [ ] Детальный прогресс по модулям
  - [ ] Навигация по модулям внутри курса
- [ ] 3.8 Тесты компонентов (Vitest)

---

## Фаза 4: Integrations (1 неделя) — 65%
- [x] 4.1 Kinescope интеграция
  - [x] Signed URL для видео
  - [x] Watermark с email
  - [x] Embed-плеер (VideoPlayer.tsx)
- [x] 4.2 Prodamus интеграция
  - [x] Email Service (aiosmtplib, HTML-письмо с кредами)
  - [x] Prodamus Service (generate_payment_link, verify_signature HMAC)
  - [x] Webhook handler POST /api/payments/webhook (registered-only checkout, идемпотентность, проверка суммы)
  - [x] Endpoint POST /api/payments/link (генерация ссылки для авторизованного пользователя)
  - [x] PaymentButton.tsx (фронтенд)
- [ ] 4.3 Telegram Bot
  - [ ] Привязка аккаунта
  - [ ] Уведомление о покупке
  - [ ] Ссылка на закрытую группу

---

## Фаза 5: Admin Panel (1 неделя) — 70%
- [x] Backend: Admin CRUD API (api/admin.py — 23.8KB)
- [x] 5.1 Admin Layout + навигация (layout.tsx 5.3KB)
- [x] 5.2 Дашборд админа (аналитика) — analytics/page.tsx (7.3KB)
- [x] 5.3 Управление пользователями — users/page.tsx (14.9KB)
- [x] 5.4 Управление контентом (курсы, модули, уроки)
  - [x] Список курсов — courses/page.tsx (26.5KB)
  - [x] Редактирование курса — courses/[id]/page.tsx (28.7KB)
- [ ] 5.5 Управление покупками — purchases/page.tsx (**заглушка**)

---

## Фаза 6: Polish & Deploy (1 неделя) — 5%
- [ ] 6.1 SEO и Meta
  - [/] Базовые meta в layout.tsx
  - [ ] Open Graph теги
  - [ ] sitemap.xml
  - [ ] robots.txt
- [ ] 6.2 PWA (manifest, service worker)
- [/] 6.3 CI/CD (GitHub Actions)
  - [x] Lint + Test на PR
  - [ ] Alembic upgrade/head check в CI
  - [ ] Auto-deploy на Railway
- [ ] 6.4 Деплой на Railway
  - [/] Backend (Dockerfile есть)
  - [ ] Frontend
  - [ ] PostgreSQL
  - [ ] Redis
  - [ ] Домен lucysmirnova.ru
- [ ] 6.5 E2E тестирование и багфикс

---

## Отложено (Post-MVP)
- [/] Refactor program: синхронизировать `AGENTS.md`, `CODEBASE.md`, `README.md`, `Docs/README.md`, `.cursor/rules/` как источники правды
- [/] Refactor program: держать `promo-clips/`, `video-lessons/`, `scripts/promo/output/` вне Git и описывать медиа как локальные/внешние артефакты
- [ ] Refactor program: разбить backend admin API, выровнять auth dependencies и политику транзакций — см. `Docs/06_Tracking/REFACTORING_ROADMAP.md`
- [ ] Refactor program: разбить frontend API client, лендинг и крупные страницы админки — см. `Docs/06_Tracking/REFACTORING_ROADMAP.md`
- [/] Refactor program: сверить локальные проверки с CI и добавить миграционный smoke-test или явную документацию drift-риска
- [ ] Payment audit log + outbox/retry для писем и админского восстановления доступа
- [ ] Redis-backed rate limits для нескольких backend-инстансов
- [ ] Refresh-token rotation/revocation и полноценная session model
- [ ] Расширенные E2E/component tests для frontend и payment/playback smoke
- [ ] Telegram-бот и уведомления
- [ ] Сертификаты (шаблон не готов)
- [ ] Уведомления об окончании доступа (за 3 дня, за 1 день)
- [ ] PWA
- [ ] Расширенная аналитика
- [ ] Страница профиля пользователя
