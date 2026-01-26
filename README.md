# Платформа видео-курсов по дизайну ногтей

> Веб-платформа для продажи видео-курсов с защитой контента через Kinescope

## Tech Stack

- **Frontend:** Next.js 14+, TypeScript, Tailwind CSS
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0
- **Database:** PostgreSQL 15, Redis
- **Интеграции:** Kinescope, Prodamus, Telegram Bot

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

```bash
git clone <repo-url>
cd Course-nails-design
cp .env.example .env
# Заполни .env своими ключами
```

### 2. Backend

```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

## Документация

- [PRD](./Docs/PRD.md) — требования
- [Architecture](./Docs/ARCHITECTURE.md) — техническая архитектура
- [Tasks](./Docs/TASKS.md) — трекер задач

## Структура

```
├── frontend/       # Next.js 14
├── backend/        # FastAPI
├── Docs/           # Документация
└── scripts/        # Утилиты
```
