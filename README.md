# Платформа видео-курсов по дизайну ногтей

> Веб-платформа для продажи видео-курсов с защитой контента через Kinescope

**Cursor / AI:** см. [`AGENTS.md`](./AGENTS.md), карта репозитория [`CODEBASE.md`](./CODEBASE.md). Правила агента: [`.cursor/rules/`](./.cursor/rules/).
- **Frontend:** Next.js (см. `frontend/package.json`), TypeScript, Tailwind CSS
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0
- **Database:** PostgreSQL 15, Redis (опционально)
- **Интеграции:** Kinescope, Prodamus, Telegram Bot

**Профессиональный процесс разработки (окружения, PR, Railway, проверки):** [Docs/04_Setup_Ops/DEVELOPMENT_WORKFLOW.md](./Docs/04_Setup_Ops/DEVELOPMENT_WORKFLOW.md)

## Быстрый старт

### Запуск всего окружения одной командой
```powershell
.\scripts\dev.ps1
```

**Результат:**
- Backend: http://127.0.0.1:8000
- Frontend: http://localhost:3000
- Swagger UI: http://127.0.0.1:8000/docs

### Альтернативный запуск (раздельно)

**Backend:**
```powershell
.\scripts\dev-backend.ps1
```

**Frontend:**
```powershell
.\scripts\dev-frontend.ps1
```

---

## Ручной запуск

### 1. Клонирование и настройка

```powershell
git clone https://github.com/TwinsMinsk/lucy-nails.git
cd lucy-nails
Copy-Item .env.example .env
# Заполните корневой .env и создайте frontend/.env.local по frontend/.env.example
```

Подробнее: [DEVELOPMENT_WORKFLOW.md](./Docs/04_Setup_Ops/DEVELOPMENT_WORKFLOW.md).

### 2. Backend

```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### 3. Frontend

```bash
cd frontend
npm install
# при необходимости: скопируйте frontend/.env.example -> frontend/.env.local
npm run dev
```

## Документация

- [Professional dev workflow](./Docs/04_Setup_Ops/DEVELOPMENT_WORKFLOW.md) — окружения, команды, Git, качество перед деплоем
- [PRD](./Docs/PRD.md) — требования
- [Architecture](./Docs/ARCHITECTURE.md) — техническая архитектура
- [Tasks](./Docs/TASKS.md) — трекер задач

## Структура

```
├── frontend/       # Next.js
├── backend/        # FastAPI
├── Docs/           # Документация
└── scripts/        # Утилиты
```
