# Dev Scripts — Автоматизация запуска

## Быстрый старт

### Запуск всего окружения одной командой
```powershell
.\scripts\dev.ps1
```

**Что происходит:**
1. ✅ Проверка существования папок `backend` и `frontend`
2. 🚀 Backend (FastAPI) запускается в **новом окне** терминала
3. 🚀 Frontend (Next.js) запускается в **текущем окне** терминала

**Результат:**
- Backend: http://127.0.0.1:8000
- Frontend: http://localhost:3000
- Swagger UI: http://127.0.0.1:8000/docs

---

## Остановка

**Frontend (текущее окно):**
```
Ctrl + C
```

**Backend (новое окно):**
Закрой окно или `Ctrl + C` в нём

---

## Ручной запуск (если нужно)

### Backend
```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

### Frontend
```powershell
cd frontend
npm run dev
```

---

## Troubleshooting

### Ошибка: "Папка backend/frontend не найдена"
**Причина:** Скрипт запущен не из корня проекта

**Решение:**
```powershell
cd "d:\Course nails design"
.\scripts\dev.ps1
```

### Ошибка: "venv not found"
**Причина:** Виртуальное окружение не создано

**Решение:**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\pip.exe install -r requirements.txt
```

### Ошибка: "npm: command not found"
**Причина:** Node.js не установлен

**Решение:** Установи Node.js 18+ с https://nodejs.org/

---

## Альтернативный скрипт: Только Backend

Создай `scripts/dev-backend.ps1`:
```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Альтернативный скрипт: Только Frontend

Создай `scripts/dev-frontend.ps1`:
```powershell
cd frontend
npm run dev
```
