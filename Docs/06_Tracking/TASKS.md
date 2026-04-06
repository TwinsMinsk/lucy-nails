# Task List: Платформа видео-курсов

> Статус: [ ] Not Started | [/] In Progress | [x] Done

---

## Фаза 0: Setup (2-3 дня)
- [x] 0.1 Инициализация репозитория (.gitignore, README.md)
- [x] 0.2 Создание .env.example
- [x] 0.3 Setup Frontend (Next.js 14 + TypeScript + Tailwind)
  - [x] Инициализация Next.js
  - [ ] Настройка ESLint + Prettier
  - [ ] Установка shadcn/ui
- [x] 0.4 Setup Backend (FastAPI + PostgreSQL)
  - [x] Виртуальное окружение
  - [x] Структура папок по ARCHITECTURE.md
  - [x] requirements.txt установлен
  - [ ] Настройка Ruff (линтер Python)
- [x] 0.5 Настройка PostgreSQL (создание БД nails_course)
- [ ] 0.6 Pre-commit hooks (Husky, lint-staged)

---

## Фаза 1: Database (3-4 дня)
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

## Фаза 2: Backend Core (1-1.5 недели)
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

---

## Фаза 3: Frontend Core (1.5-2 недели)
- [ ] 3.1 Layout и навигация (Header, Footer)
- [ ] 3.2 Главная страница
- [ ] 3.3 Страница курса (список модулей)
- [ ] 3.4 Авторизация (Login, Register UI)
- [ ] 3.5 Личный кабинет (Dashboard)
- [ ] 3.6 Просмотр курса (модули → уроки → видео)
- [ ] 3.7 Прогресс-бар (курс + модули)
- [ ] 3.8 Тесты компонентов (Vitest)

---

## Фаза 4: Integrations (1 неделя)
- [x] 4.1 Kinescope интеграция
  - [x] Signed URL для видео
  - [x] Watermark с email
  - [x] Embed-плеер
- [x] 4.2 Prodamus интеграция
  - [x] Email Service (aiosmtplib, HTML-письмо с кредами)
  - [x] Prodamus Service (generate_payment_link, verify_signature HMAC)
  - [x] Webhook handler POST /api/payments/webhook (авто-регистрация пользователя)
  - [x] Endpoint POST /api/payments/link (генерация ссылки для фронта)
- [ ] 4.3 Telegram Bot
  - [ ] Привязка аккаунта
  - [ ] Уведомление о покупке
  - [ ] Ссылка на закрытую группу

---

## Фаза 5: Admin Panel (1 неделя)
- [ ] 5.1 Дашборд админа (аналитика)
- [ ] 5.2 Управление пользователями
- [ ] 5.3 Управление контентом (курсы, модули, уроки)

---

## Фаза 6: Polish & Deploy (1 неделя)
- [ ] 6.1 SEO и Meta
- [ ] 6.2 PWA (manifest, service worker)
- [ ] 6.3 CI/CD (GitHub Actions)
  - [ ] Lint + Test на PR
  - [ ] Auto-deploy на Railway
- [ ] 6.4 Деплой на Railway
  - [ ] Backend
  - [ ] Frontend
  - [ ] PostgreSQL
  - [ ] Redis
  - [ ] Домен lucysmirnova.ru
- [ ] 6.5 E2E тестирование и багфикс

---

## Отложено (Post-MVP)
- [ ] Сертификаты (шаблон не готов)
- [ ] Уведомления об окончании доступа (за 3 дня, за 1 день)
- [ ] Расширенная аналитика
