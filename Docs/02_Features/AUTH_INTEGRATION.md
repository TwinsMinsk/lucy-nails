# Auth Integration & Database Seeding - Complete

**Дата:** 23.01.2026  
**Статус:** ✅ Завершено

---

## Выполненные задачи

### 1. ✅ Обновлен Seed скрипт (`backend/scripts/seed_data.py`)

**Изменения:**
- Добавлена функция `clear_database()` для очистки таблиц перед вставкой
- Все уроки получили `kinescope_video_id` (dummy-video-id-1 до dummy-video-id-8)
- Создаются покупки для ОБОИХ пользователей (админ + студент)
- Доступ к курсу: 365 дней (вместо 30)
- Исправлен `payment_status`: используется 'success' (согласно ENUM)

**Данные в БД:**
```
✓ Пользователей: 2
  - admin@nails-course.ru / admin123 (роль: admin)
  - student@test.ru / student123 (роль: student)

✓ Курсов: 1
  - "Дизайн ногтей: От А до Я"

✓ Модулей: 3
  - Все возможности фольги (4 урока)
  - Градиент (2 урока)
  - Френч (2 урока)

✓ Уроков: 8 (все с kinescope_video_id)

✓ Покупок: 2
  - Обе с доступом на 365 дней
  - Статус: success
  - Тариф: self

✓ Прогресс: 1 (для student@test.ru)
```

---

### 2. ✅ Расширен API Client (`frontend/src/lib/api.ts`)

**Добавленные методы:**

```typescript
// Auth
login(credentials) -> TokenResponse
register(credentials) -> UserResponse
getMe() -> UserResponse
logout() -> void

// Lessons (уже были)
getLessonPlayUrl(lessonId) -> VideoPlayResponse
getLesson(lessonId) -> LessonResponse
```

**Ключевые особенности:**
- `login()` автоматически сохраняет токены в `localStorage`
- `logout()` удаляет токены
- `apiFetch()` auto подставляет `Authorization: Bearer {token}`

---

### 3. ✅ Обновлена страница Login (`frontend/src/app/(public)/auth/login/page.tsx`)

**Изменения:**
- Замен mock `console.log()` на реальный `api.login()`
- Добавлен редирект на `/dashboard` при успехе
- Обработка ошибок с `toast.error()`
- Loading state во время запроса

**Поток:**
```
User вводит email + password
  ↓
Валидация (Zod schema)
  ↓
API: POST /auth/login
  ↓
Success: Сохранить токен → Redirect /dashboard
Error: Показать toast с ошибкой
```

---

### 4. ✅ Исправлен Bug в LessonService

**Проблема:**
- В `LessonService.check_access()` использовался `payment_status == "paid"`
- В модели Purchase ENUM: `["pending", "success", "failed"]`
- Ошибка: "paid" не существует в ENUM

**Решение:**
- Изменён на `payment_status == "success"`
- Обновлен seed скрипт аналогично

---

## Как протестировать

### 1. Запустить серверы

```powershell
# Backend (если не запущен)
.\scripts\dev.ps1

# Frontend
cd frontend
npm run dev
```

### 2. Открыть Login

```
http://localhost:3000/auth/login
```

### 3. Войти как админ

```
Email: admin@nails-course.ru
Password: admin123
```

**Ожидаемый результат:**
- ✅ Успешный вход
- ✅ Toast: "Вход выполнен успешно!"
- ✅ Редирект на `/dashboard`
- ✅ Токен сохранён в localStorage

### 4. Открыть урок

Перейти на любой урок (ID из seed данных).

**Ожидаемый результат:**
- ✅ Видео загружается (YouTube iframe в Mock-режиме)
- ✅ Нет ошибки 403 (т.к. есть активная покупка)

---

## Учётные данные (Test)

| Email | Password | Роль | Доступ к курсу |
|-------|----------|------|----------------|
| admin@nails-course.ru | admin123 | admin | ✅ 365 дней |
| student@test.ru | student123 | student | ✅ 365 дней |

---

## Технические детали

### payment_status ENUM

**Модель** (Purchase):
```python
payment_status: Mapped[str] = mapped_column(
    SQLEnum("pending", "success", "failed", name="payment_status"),
    nullable=False,
    default="pending"
)
```

**Используемые значения:**
- `pending` - Ожидает оплаты
- `success` - Оплачено ✅ (активен доступ)
- `failed` - Ошибка оплаты

### kinescope_video_id

Все уроки имеют dummy ID:
- `dummy-video-id-1`
- `dummy-video-id-2`
- ...
- `dummy-video-id-8`

В Mock-режиме KinescopeService игнорирует этот ID и возвращает YouTube тест-видео.

---

## Следующие шаги

### ✅ Completed
- [x] Seed скрипт обновлён
- [x] API Client расширен
- [x] Login page интегрирован
- [x] Bug payment_status исправлен
- [x] БД заполнена

### 🔄 Next (Optional)
- [ ] Register page integration
- [ ] Dashboard: замнить Mock на реальные API
- [ ] Logout кнопка в Header
- [ ] Protected route middleware

---

## Troubleshooting

### Проблема: "Email already registered"
**Решение:** БД уже содержит данные. Запусти seed скрипт снова:
```powershell
.\backend\venv\Scripts\python.exe .\backend\scripts\seed_data.py
```

### Проблема: 401 Unauthorized при запросе к /lessons/{id}/play
**Причина:** Токен не сохранён или истёк.
**Решение:** Залогинься снова через UI.

### Проблема: 403 Forbidden при запросе к /lessons/{id}/play
**Причина:** Нет активной покупки курса.
**Решение:** Проверь что в БД есть запись в `purchases` с `payment_status="success"` и `expires_at > now`.

---

## Статистика

```
✅ Backend изменений: 2 файла
  - seed_data.py (обновлён)
  - lesson_service.py (исправлен bug)

✅ Frontend изменений: 2 файла
  - lib/api.ts (расширен)
  - auth/login/page.tsx (интегрирован)

✅ Seed данных:
  - 2 пользователя
  - 1 курс  
  - 3 модуля
  - 8 уроков
  - 2 покупки
  - 1 прогресс

✅ Время выполнения: ~30 мин
```

---

**Интеграция авторизации завершена! Можно тестировать real login → dashboard → video player! 🚀**
