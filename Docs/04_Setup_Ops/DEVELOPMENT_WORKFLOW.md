# Профессиональный процесс разработки (монорепо + Railway)

Цель — не смешивать **production**, **staging** и **local**, сохранять чистую историю в Git и не ломать схему БД между окружениями.

## Роли окружений

| Окружение | Где живёт | База | Секреты / платежи |
|-----------|-----------|------|-------------------|
| **local** | Ваша машина (Windows + PowerShell) | Локальный PostgreSQL `nails_course` + отдельная `test_nails_course` для тестов | Тестовые / sandbox ключи по возможности |
| **staging** | Отдельный проект или environment в Railway (рекомендуется) | Отдельный PostgreSQL | Тестовые webhook-URL, без боевых денег |
| **production** | Текущий Railway | Production PostgreSQL из Railway | Боевые ключи только здесь |

**Правило:** не используйте production `DATABASE_URL` как «рабочую» базу при ежедневной разработке. Для платежей и Telegram — только staging или изолированные тестовые аккаунты.

## Переменные окружения (где какой файл)

- **Backend (FastAPI):** читает в порядке приоритета **переменные ОС** → файл **`<repo-root>/.env`** → **`backend/.env`** (переопределяет значения из корня, если файл есть). Логика в [`backend/app/core/config.py`](../../backend/app/core/config.py).
- **Frontend (Next.js):** по умолчанию подхватывает только **`frontend/.env.local`**, **`frontend/.env`**, и т.д. внутри папки `frontend`. Корневой `.env` Next сам не читает.
  - Шаблон: [`frontend/.env.example`](../../frontend/.env.example) — скопируйте в `frontend/.env.local` и синхронизируйте `NEXT_PUBLIC_*` с корневым [.env.example](../../.env.example).
- Корневой [`.gitignore`](../../.gitignore) исключает `.env` и `frontend/.env.local` из коммитов.

Railway задаёт переменные через Dashboard (секреты не должны попадать в Git). См. [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md).

## Локальный запуск (точные команды, PowerShell)

Все команды выполняются из **корня репозитория** (`lucy-nails`), если не указано иначе.

### 1) Быстрая проверка инструментов

```powershell
.\scripts\setup-local.ps1
```

### 2) Виртуальное окружение backend и зависимости

```powershell
python -m venv backend\venv
.\backend\venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

Без активированного venv можно вызывать:

```powershell
.\backend\venv\Scripts\pip.exe install -r backend\requirements.txt
```

### 3) PostgreSQL и базы

Создайте БД приложения и тестовую (имена должны быть согласованы с `DATABASE_URL` и логикой в `backend/tests/conftest.py`: по умолчанию из `DATABASE_URL` с `…/nails_course` получается `…/test_nails_course`).

Пример через `createdb` (если утилиты в PATH):

```powershell
createdb -U postgres nails_course
createdb -U postgres test_nails_course
```

Подробнее: [postgresql_setup.md](postgresql_setup.md), [create_database.md](create_database.md).

### 4) Корневой `.env`

```powershell
Copy-Item .env.example .env
# заполните .env (локальные пароли БД и ключи)
```

Создайте `frontend/.env.local` по [`frontend/.env.example`](../../frontend/.env.example).

### 5) Миграции Alembic (обязательно после `git pull` с новыми миграциями)

```powershell
Set-Location backend
..\backend\venv\Scripts\Activate.ps1
alembic upgrade head
Set-Location ..
```

### 6) Запуск приложения

**Вариант A — два окна (скрипт):**

```powershell
.\scripts\dev.ps1
```

**Вариант B — вручную**

Backend:

```powershell
Set-Location backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
Set-Location frontend
npm install
npm run dev
```

Проверка: Backend [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs), Frontend [http://localhost:3000](http://localhost:3000).

## Обязательные проверки перед PR / перед деплоем

Выполните локально или доверьте пайплайну GitHub Actions (см. [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)).

### Backend: линтер Ruff

Конфигурация правил: [`pyproject.toml`](../../pyproject.toml) в корне репозитория.

```powershell
.\backend\venv\Scripts\Activate.ps1
ruff check backend\app backend\tests
```

### Backend: тесты (нужна БД `test_nails_course`)

```powershell
$env:PYTHONPATH = "backend"
.\backend\venv\Scripts\python.exe -m pytest backend\tests -v
```

При необходимости однократно создайте тестовую БД через [`backend/scripts/create_test_db.py`](../../backend/scripts/create_test_db.py) (если файл есть и актуален в вашей ветке).

### Frontend: линт и production-сборка

```powershell
Set-Location frontend
npm ci
npm run lint
```
Линтер может выдавать предупреждения (warnings) — они не ломают выход `0`. Правила смягчены в `frontend/eslint.config.mjs`, постепенный возврат строгости возможен по мере рефакторинга.

Сборка:

```powershell
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8000/api"
$env:NEXT_PUBLIC_SITE_URL = "http://localhost:3000"
npm run build
Set-Location ..
```

В CI эти переменные задаются в workflow автоматически.

## Railway: миграции и два сервиса

Файл [`railway.toml`](../../railway.toml): для сервиса **backend** `startCommand` запускает сначала `alembic upgrade head`, затем `uvicorn` — так же по смыслу, как в [`backend/Procfile`](../../backend/Procfile). Это снижает риск расхождения схемы БД между деплоями.

**Важно:** переменные `NEXT_PUBLIC_*` для фронта должны быть доступны на этапе **build** в Railway — см. [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md).

## Git и ветки (рабочий цикл)

1. Актуальная `main` (или принятый у вас default branch):

   ```powershell
   git checkout main
   git pull origin main
   ```

2. Ветка задачи:

   ```powershell
   git checkout -b feature/kratkoe-opisanie
   ```

3. Маленькие коммиты с понятными сообщениями (Conventional Commits по желанию: `feat:`, `fix:`, `chore:`).

4. Перед отправкой:

   ```powershell
   git status
   git push -u origin feature/kratkoe-opisanie
   ```

5. Pull Request на `main`; после review — merge; Railway обычно деплоит с `main` (настройте в Dashboard при необходимости).

Для изменений только в БД всегда коммитьте файл миграции в [`backend/alembic/versions`](../../backend/alembic/versions) и прогоняйте Alembic на staging до production.

## Безопасность секретов

- Если production-ключ когда-то оказался в локальном `.env` или в истории коммита — **ротируйте** ключ у провайдера (Stripe/Prodamus/Telegram и т.д.).
- Не публикуйте `.env`; при сомнениях — `git check-ignore .env`.

## Дополнительные материалы

- [AGENTS.md](../../AGENTS.md) — ориентир для AI в Cursor
- [CODEBASE.md](../../CODEBASE.md) — карта репозитория
- [README.md](../../README.md) — быстрый старт
- [dev_scripts.md](dev_scripts.md) — скрипты `dev.ps1`
- [ARCHITECTURE.md](../ARCHITECTURE.md) — устройство системы
