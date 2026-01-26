# Инструкция по ручному тестированию Kinescope Integration

## Быстрый старт

### 1. Запуск сервера (если не запущен)

```powershell
# Из корня проекта
.\scripts\dev.ps1
```

Сервер запустится на `http://localhost:8000`

### 2. Проверка Mock-режима

Mock-режим активен по умолчанию (так как `KINESCOPE_API_KEY` не задан).

**Проверить:**
```powershell
# Проверить переменную окружения
$env:KINESCOPE_API_KEY
# Должно быть пусто или не задано
```

---

## Тестирование API

### Шаг 1: Регистрация пользователя

```bash
POST http://localhost:8000/api/auth/register
Content-Type: application/json

{
  "email": "test@example.com",
  "password": "test123"
}
```

**Expected Response (201):**
```json
{
  "id": "uuid...",
  "email": "test@example.com",
  "role": "student",
  ...
}
```

### Шаг 2: Вход (получение токена)

```bash
POST http://localhost:8000/api/auth/login
Content-Type: application/json

{
  "email": "test@example.com",
  "password": "test123"
}
```

**Expected Response (200):**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

**Сохрани** `access_token` для следующих запросов.

### Шаг 3: Получить список уроков

Сначала нужен ID урока из seed данных.

```bash
GET http://localhost:8000/api/courses
```

Выбери любой курс, перейди к его модулям, затем к урокам, и возьми `lesson_id`.

### Шаг 4: Запрос видео (превью урок)

Если урок является preview (`is_preview=true`), доступ будет предоставлен без покупки:

```bash
GET http://localhost:8000/api/lessons/{lesson_id}/play
Authorization: Bearer YOUR_ACCESS_TOKEN
```

**Expected Response (200):**
```json
{
  "video_url": "https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=0",
  "provider": "kinescope",
  "title": "Название урока"
}
```

### Шаг 5: Запрос видео (платный урок без покупки)

Для урока с `is_preview=false` и без активной покупки:

**Expected Response (403):**
```json
{
  "detail": "Course access required. Please purchase the course to watch this lesson."
}
```

---

## Проверка через Swagger UI

1. Открой в браузере: http://localhost:8000/docs
2. Найди секцию **lessons**
3. Найди эндпоинт `GET /api/lessons/{lesson_id}/play`
4. Нажми **"Try it out"**
5. Введи `lesson_id` (любой из seed данных)
6. Нажми **"Authorize"** и введи токен: `Bearer YOUR_ACCESS_TOKEN`
7. Нажми **"Execute"**

**Результат:**
- Код `200` - успех (для preview уроков)
- Код `403` - нет доступа (для платных уроков без покупки)
- Код `401` - не авторизован

---

## Проверка Mock-режима

### В Python консоли:

```powershell
# Активируй venv
.\backend\venv\Scripts\Activate.ps1

# Запусти Python
python

# В консоли Python:
>>> from app.services.kinescope_service import kinescope_service
>>> from app.models.user import User
>>> import uuid
>>> 
>>> # Создаем фейкового пользователя
>>> user = User(
...     id=uuid.uuid4(),
...     email="test@example.com",
...     password_hash="hash",
...     role="student"
... )
>>> 
>>> # Проверяем Mock-режим
>>> kinescope_service.is_mock_mode
True
>>> 
>>> # Получаем URL
>>> url = kinescope_service.get_embed_url("fake_video_id", user)
>>> print(url)
https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=0
>>> 
>>> # Получаем метаданные
>>> import asyncio
>>> info = asyncio.run(kinescope_service.get_video_info("fake_id"))
>>> print(info)
{'title': 'Demo Video', 'duration': 600, 'poster': '...'}
```

---

## Тестирование с реальным Kinescope API

### Настройка

1. Получи API ключ в [Kinescope Dashboard](https://app.kinescope.io)
2. Обнови `.env`:
   ```env
   KINESCOPE_API_KEY=your_real_api_key
   KINESCOPE_PROJECT_ID=your_project_id
   ```
3. Перезапусти сервер

### После настройки

Mock-режим автоматически отключится.

**Проверь:**
```python
>>> from app.services.kinescope_service import kinescope_service
>>> kinescope_service.is_mock_mode
False
```

**Теперь:**
- `get_video_info()` будет делать реальные запросы к API
- `get_embed_url()` вернет ссылку вида:
  ```
  https://kinescope.io/embed/{video_id}?email=user@example.com&external_id=uuid...
  ```

---

## Проблемы и решения

### 401 Unauthorized
**Причина:** Токен не передан или истек.  
**Решение:** Получи новый токен через `/api/auth/login`.

### 403 Forbidden
**Причина:** Нет доступа к курсу (нет активной покупки).  
**Решение:** 
- Используй preview урок (`is_preview=true`)
- Или создай покупку через админку/API
- Или войди под админом (`role="admin"`)

### 404 Not Found
**Причина:** Урок не существует или у него нет `kinescope_video_id`.  
**Решение:** Проверь наличие урока в БД и что поле `kinescope_video_id` заполнено.

---

## Автоматические тесты

Запуск всех тестов:

```powershell
$env:PYTHONPATH="backend"
.\backend\venv\Scripts\python.exe -m pytest backend\tests\test_kinescope.py -v
```

**Ожидаемый результат:**
```
3 passed, 10 warnings
```

---

## Следующие шаги

После успешного тестирования backend интеграции:
1. **Frontend:** Создать компонент `VideoPlayer` для отображения iframe
2. **Prodamus:** Интеграция платежной системы (Фаза 4.2)
3. **Telegram Bot:** Уведомления и привязка аккаунта (Фаза 4.3)

---

## Полезные ссылки

- 📄 [KINESCOPE.md](./integrations/KINESCOPE.md) - Полная документация
- 📄 [PHASE_4.1_SUMMARY.md](./PHASE_4.1_SUMMARY.md) - Сводка реализации
- 🌐 [Kinescope API Docs](https://kinescope.io/docs/api)
- 🌐 FastAPI Swagger: http://localhost:8000/docs
