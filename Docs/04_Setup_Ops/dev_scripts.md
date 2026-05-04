# Dev Scripts — Автоматизация запуска

См. также полный процесс: [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md).

## Быстрый старт

### Запуск всего окружения одной командой

```powershell
.\scripts\dev.ps1
```

**Что происходит:**

1. Проверка существования папок `backend` и `frontend`.
2. Backend (FastAPI) запускается в **новом окне** PowerShell (`backend\venv`, `uvicorn … --reload`).
3. Frontend (Next.js) в **текущем окне** (`npm run dev`).

**Адреса:**

- Backend: http://127.0.0.1:8000
- Frontend: http://localhost:3000
- Swagger: http://127.0.0.1:8000/docs

**Перед первым запуском:** см. корневой [README](../../README.md) — виртуальное окружение, `pip install`, `npm install`, миграции `alembic upgrade head`. Backend читает **корневой** `.env` (обязательно для подключения к БД при запуске из `backend`).

---

## Остановка

- **Frontend (текущее окно):** `Ctrl + C`
- **Backend (отдельное окно):** закройте окно или `Ctrl + C`

---

## Раздельный запуск

### Только Backend

```powershell
.\scripts\dev-backend.ps1
```

Эквивалент:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Только Frontend

```powershell
.\scripts\dev-frontend.ps1
```

Эквивалент:

```powershell
cd frontend
npm run dev
```

Не забудьте `frontend/.env.local` (шаблон: `frontend/.env.example`) для `NEXT_PUBLIC_*`.

---

## Первоначальная настройка

```powershell
.\scripts\setup-local.ps1
```

Далее см. [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md): создание `backend\venv`, БД PostgreSQL, копирование `.env.example` → `.env`.

---

## Troubleshooting

### Ошибка: «Папка backend/frontend не найдена»

Скрипт запущен не из корня репозитория.

```powershell
cd "путь\к\lucy-nails"
.\scripts\dev.ps1
```

### Ошибка: venv не найден

```powershell
cd backend
python -m venv venv
.\venv\Scripts\pip.exe install -r requirements.txt
```

### Ошибка: npm не найден

Установите Node.js LTS с https://nodejs.org/

### Backend не видит переменные из `.env`

Убедитесь, что файл **`<корень-репо>/.env`** существует (не только `frontend/.env.local`). При необходимости можно использовать **`backend/.env`** — он переопределяет значения корневого файла.

### npm / Next: неверный API URL

Проверьте `NEXT_PUBLIC_API_URL` в **`frontend/.env.local`**.
