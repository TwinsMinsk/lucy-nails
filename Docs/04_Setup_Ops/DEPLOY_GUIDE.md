# 🚀 Deployment Guide: Railway + GitHub

Этот гайд поможет развернуть и запустить проект на платформе [Railway](https://railway.app/).
Твой репозиторий: [https://github.com/TwinsMinsk/lucy-nails](https://github.com/TwinsMinsk/lucy-nails)

---

## 📋 Шаг 0: Предварительная подготовка (Уже сделано мной)
Я уже подготовил кодовую базу:
1.  Создал `railway.toml` для управления Monorepo (Backend + Frontend).
2.  Настроил `.gitignore` для защиты секретов.
3.  Инициализировал Git и добавил твой репозиторий как `origin`.
4.  Сделал первый коммит.

Тебе осталось только отправить код и настроить переменные.

---

## 🛠️ Шаг 1: Загрузка кода на GitHub

Открой терминал в корне проекта (или используй VS Code) и выполни:

```powershell
# 1. Проверь статус (должно быть "clean" или готово к push)
git status

# 2. Отправь код в репозиторий
git branch -M main
git push -u origin main
```

*(Если спросит логин/пароль — используй свой GitHub аккаунт или Token)*

---

## 🚂 Шаг 2: Настройка проекта в Railway

1.  Зайди на [Railway Dashboard](https://railway.app/dashboard).
2.  Нажми **"New Project"** → **"Deploy from GitHub repo"**.
3.  Выбери репозиторий: `TwinsMinsk/lucy-nails`.
4.  Нажми **"Deploy Now"**.
    *Railway увидит файл `railway.toml` и автоматически создаст два сервиса: `backend` и `frontend`.*

### Добавление Базы Данных
1.  В открывшемся проекте нажми `Cmd+K` (или `Ctrl+K` или кнопку "New").
2.  Выбери **Database** → **PostgreSQL**.
3.  Подожди, пока она создастся.

### Добавление Redis (Опционально)
1.  Нажми "New" → **Database** → **Redis**.

---

## 🔑 Шаг 3: Переменные окружения (Environment Variables)

Самый важный этап. Тебе нужно перенести секреты из `.env` в Railway.
Перейди в настройки сервиса **backend** → вкладка **Variables**.

### 1. Переменные, которые Railway даст САМ (Не вводи их вручную!):
*Убедись, что сервисы связаны, или используй Reference Variables.*
- `DATABASE_URL` (Автоматически появится, если база добавлена в проект).
- `REDIS_URL` (Аналогично, если добавлен Redis).
- `PORT` (Railway сам управляет портом).

### 2. Переменные, которые нужно скопировать c локального `.env`:

| Variable Name | Значение (или где взять) |
| :--- | :--- |
| `ENVIRONMENT` | `production` |
| `DEBUG` | `false` |
| `JWT_SECRET_KEY` | *Придумай новый сложный длинный пароль* |
| `JWT_ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` |
| `KINESCOPE_API_KEY` | *(Взять из Kinescope ЛК)* |
| `KINESCOPE_PROJECT_ID` | *(Взять из Kinescope ЛК)* |
| `PRODAMUS_URL` | URL платёжной формы Prodamus, например `https://...prodamus.ru` |
| `PRODAMUS_SECRET_KEY` | *(Взять из Prodamus)* |
| `PRODAMUS_SHOP_ID` | *(Взять из Prodamus)* |
| `SMTP_USER` | Опционально: SMTP-логин, если включаете guest checkout с отправкой credentials |
| `SMTP_PASSWORD` | Опционально: SMTP-пароль / app password |
| `SMTP_FROM_NAME` | Опционально: `Lucy Nails Academy` |
| `FRONTEND_URL` | `https://<твое-frontend-домен>.up.railway.app` |
| `BACKEND_URL` | `https://<твой-backend-домен>.up.railway.app` |
| `CORS_ORIGINS` | Production frontend origin, например `https://lucysmirnova.ru` |
| `TRUSTED_HOSTS` | Домены backend без схемы, через запятую |
| `TELEGRAM_BOT_TOKEN` | *(Post-MVP; можно не задавать для MVP)* |
| `TELEGRAM_SUPPORT_GROUP_INVITE`| *(Post-MVP; можно не задавать для MVP)* |
| `NEXT_PUBLIC_SITE_URL` | `https://<твое-frontend-домен>.up.railway.app` (появится после деплоя фронта) |
| `NEXT_PUBLIC_API_URL` | `https://<твой-backend-домен>.up.railway.app/api` |

> **Важно:** Переменные, начинающиеся с `NEXT_PUBLIC_...`, нужно добавить **ТАКЖЕ** и в сервис **frontend**! Frontend собирается (Build) с этими переменными, поэтому они должны быть доступны на этапе сборки.

---

## 🚀 Шаг 4: Public Networking (Домены)

Чтобы сайт открывался в интернете:

1.  **Backend Service:**
    - Зайди в Settings → Networking.
    - Нажми **"Generate Domain"**.
    - Скопируй этот домен (например, `backend-production.up.railway.app`).
    - Обнови переменную `NEXT_PUBLIC_API_URL` в сервисе **frontend** (укажи этот домен + `/api`).

2.  **Frontend Service:**
    - Зайди в Settings → Networking.
    - Нажми **"Generate Domain"**.
    - Это и есть ссылка на твой сайт!
    - Обнови переменную `NEXT_PUBLIC_SITE_URL` в сервисе **backend** (для CORS и редиректов).

---

## ✅ Шаг 5: Первый запуск и проверка

1.  После настройки переменных Railway автоматически перезапустит деплой (Redeploy).
2.  Следи за вкладкой **Deployments** → **View Logs**.
    - **Backend Logs:** при старте выполняются миграции Alembic (`alembic upgrade head`), затем должен быть `Application startup complete` от Uvicorn.
    - **Frontend Logs:** Должно быть `Ready in ... ms`.
3.  В личном кабинете Prodamus настрой webhook на `BACKEND_URL` + `/api/payments/webhook`.
4.  Создай первого администратора через Railway shell backend-сервиса:

```powershell
ADMIN_EMAIL=owner@example.com ADMIN_PASSWORD="long-random-password" python scripts/create_admin.py
```

5.  Проверь production-контент:

```powershell
python scripts/check_production_content.py
```

6.  Открой публичный домен Frontend сервиса. Проверь регистрацию, вход, создание ссылки оплаты, webhook, появление доступа в кабинете и запуск урока.

**Поздравляю! Твой проект в продакшене! 🎉**
