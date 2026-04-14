# Фаза 2.3: API Уроков и Прогресса (Завершена)

## Реализованный функционал

### 1. Pydantic схемы (`app/schemas/progress.py`)
- `ProgressBase`: `watched_seconds`, `is_completed`
- `ProgressUpdate`: для обновления
- `ProgressResponse`: полный объект с датами

### 2. Сервис (`app/services/lesson_service.py`)
- `get_lesson_with_access`: Возвращает урок и флаг доступа.
- `check_access`: 
  - Разрешено если админ, превью-урок, или куплен курс.
- `update_progress`: Создает или обновляет запись в таблице `progress`.

### 3. API Endpoints (`app/api/lessons.py`)

#### GET `/api/lessons/{id}`
Возвращает детали урока.
- Если есть доступ: поле `video_url` заполнено (mock/ID).
- Если нет доступа: `video_url` и `kinescope_video_id` равны `null`.

#### POST `/api/lessons/{id}/progress`
Обновляет прогресс.
- Требует авторизации.
- Требует доступа к курсу.
- Тело: `{"watched_seconds": 120, "is_completed": false}`

## Тестирование
Backend успешно запускается.
Ошибок импорта нет.
Миграции не требуются (таблицы уже были).
