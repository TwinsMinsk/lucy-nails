# Kinescope Integration

**Статус:** ✅ Реализовано (Mock Mode)  
**Дата:** 23.01.2026  
**Фаза:** 4.1

---

## Обзор

Интеграция с Kinescope API v1 для безопасной выдачи ссылок на видео с защитой от несанкционированного доступа.

## Архитектура

### Компоненты

1. **KinescopeService** (`backend/app/services/kinescope_service.py`)
   - Работа с Kinescope API
   - Генерация защищенных embed-ссылок
   - Mock-режим для разработки

2. **API Endpoint** (`GET /api/lessons/{lesson_id}/play`)
   - Проверка прав доступа
   - Выдача ссылки на видео

3. **Схемы** (`backend/app/schemas/lesson.py`)
   - `VideoPlayResponse` - ответ с данными видео

---

## API Reference

### Kinescope API v1

**Base URL:** `https://api.kinescope.io/v1`  
**Auth:** Header `Authorization: Bearer <TOKEN>`

#### Используемые эндпоинты

```
GET /videos/{video_id}
```

**Response:**
```json
{
  "title": "Название видео",
  "duration": 600,
  "poster": {
    "url": "https://..."
  }
}
```

---

## Backend Implementation

### 1. KinescopeService

```python
class KinescopeService:
    async def get_video_info(video_id: str) -> dict
    def get_embed_url(video_id: str, user: User) -> str
```

**Методы:**

- **get_video_info(video_id)** - Получает метаданные видео из API
- **get_embed_url(video_id, user)** - Генерирует защищенную ссылку для iframe

**Защита контента (Watermarks):**

Ссылка для плеера содержит query-параметры с идентификаторами пользователя:

```
https://kinescope.io/embed/{video_id}?email={user.email}&external_id={user.id}
```

Это позволяет Kinescope отображать динамический водяной знак поверх видео.

### 2. API Endpoint

**Route:** `GET /api/lessons/{lesson_id}/play`

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Response (200):**
```json
{
  "video_url": "https://kinescope.io/embed/xxx?email=...&external_id=...",
  "provider": "kinescope",
  "title": "Название урока"
}
```

**Errors:**
- `401 Unauthorized` - Не авторизован
- `403 Forbidden` - Нет доступа к курсу
- `404 Not Found` - Урок не найден или видео не настроено

**Access Control Logic:**

Доступ предоставляется если:
1. Урок помечен как превью (`is_preview=True`), ИЛИ
2. Пользователь - админ (`role="admin"`), ИЛИ
3. Есть активная покупка курса (`Purchase.payment_status="paid"` и `expires_at > now`)

---

## Mock Mode

### Назначение

Mock-режим автоматически активируется если:
- `KINESCOPE_API_KEY` не задан в `.env`, ИЛИ
- `KINESCOPE_API_KEY` пустая строка

### Поведение

**get_video_info():**
```python
{
  "title": "Demo Video",
  "duration": 600,
  "poster": "https://via.placeholder.com/1280x720/..."
}
```

**get_embed_url():**
```
https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=0
```

> **Note:** Используется безопасное YouTube-видео для тестирования фронтенда.

---

## Настройка

### Environment Variables

Добавь в `.env`:

```env
# Kinescope API (оставь пустым для Mock-режима)
KINESCOPE_API_KEY=
KINESCOPE_PROJECT_ID=
```

### Production Setup

1. Получи API ключ в [Kinescope Dashboard](https://app.kinescope.io)
2. Скопируй Project ID
3. Обнови `.env`:
   ```env
   KINESCOPE_API_KEY=your_actual_api_key
   KINESCOPE_PROJECT_ID=your_project_id
   ```

---

## Testing

### Manual Test (Mock Mode)

```bash
# 1. Авторизуйся и получи токен
POST /api/auth/login
{
  "email": "test@example.com",
  "password": "password"
}

# 2. Получи ссылку на видео (потребуется lesson_id из seed данных)
GET /api/lessons/{lesson_id}/play
Authorization: Bearer <token>
```

**Expected Response:**
```json
{
  "video_url": "https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=0",
  "provider": "kinescope",
  "title": "Название урока"
}
```

---

## Next Steps

- [ ] **4.2** - Prodamus интеграция (платежи)
- [ ] **4.3** - Telegram Bot (уведомления)
- [ ] **Frontend** - Компонент VideoPlayer для отображения iframe

---

## Changelog

### v1.0 (23.01.2026)
- ✅ Создан KinescopeService с Mock-режимом
- ✅ Реализован GET /lessons/{id}/play
- ✅ Добавлена защита watermark (email + external_id)
- ✅ Схемы VideoPlayResponse
