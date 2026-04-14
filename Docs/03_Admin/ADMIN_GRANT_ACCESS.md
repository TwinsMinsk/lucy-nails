# Admin Panel: Manual Grant Access - Complete

**Дата:** 23.01.2026  
**Статус:** ✅ Завершено

---

## Реализованный функционал

### Цель
Администратор может вручную выдать пользователю доступ к курсу через таблицу пользователей в админ-панели.

---

## Backend API

### ✅ Новые эндпоинты

**Файл:** `backend/app/api/admin.py`

#### 1. `GET /api/admin/courses`
Получить список всех курсов (только для админов).

**Response:**
```json
[
  {
    "id": "uuid",
    "title": "Дизайн ногтей: От А до Я",
    "description": "...",
    "price_self": 5000,
    "price_support": 20000,
    "is_published": true
  }
]
```

---

#### 2. `POST /api/admin/grant-access`
Выдать доступ к курсу пользователю.

**Request:**
```json
{
  "user_id": "uuid",
  "course_id": "uuid",
  "tariff": "self"  // или "support"
}
```

**Response:**
```json
{
  "message": "Access granted successfully",
  "purchase_id": "uuid",
  "expires_at": "2026-01-23T12:00:00"
}
```

**Логика:**
- Проверяет существование пользователя и курса
- Если покупка уже существует → **продлевает** срок доступа на 365 дней
- Если нет → **создаёт** новую покупку
- Всегда устанавливает `payment_status="success"`

---

## Frontend API Client

### ✅ Новые методы

**Файл:** `frontend/src/lib/api.ts`

```typescript
// Получить все курсы (для админов)
getAllCourses() -> AdminCourseResponse[]

// Выдать доступ к курсу
adminGrantAccess(userId, courseId, tariff?) -> GrantAccessResponse
```

**Типы:**
```typescript
interface AdminCourseResponse {
    id: string;
    title: string;
    description: string;
    price_self: number;
    price_support: number;
    is_published: boolean;
}

interface GrantAccessResponse {
    message: string;
    purchase_id: string;
    expires_at: string;
}
```

---

## Frontend UI

### ✅ Обновление страницы Users

**Файл:** `frontend/src/app/admin/users/page.tsx`

**Изменения:**

#### 1. Новая колонка "Действия"
В таблице добавлена колонка с кнопкой "Доступ":

| ID | Email | Роль | Дата регистрации | **Действия** |
|----|-------|------|------------------|--------------|
| abc... | user@... | Student | 23.01.2026 | `[🔑 Доступ]` |

#### 2. Dialog (Modal) для выдачи доступа

**Триггер:** Кнопка "Доступ" в строке пользователя

**Содержимое:**
- Заголовок: "Выдать доступ к курсу"
- Email пользователя
- Select с списком всех курсов
- Информационный блок с условиями:
  - Доступ: 365 дней
  - Тариф: Self
  - Если доступ есть - продление
- Кнопки: "Отмена" и "Выдать доступ"

#### 3. Компоненты (shadcn/ui)
Установлены и использованы:
- ✅ `Dialog` - модальное окно
- ✅ `Select` - выпадающий список курсов
- ✅ `Button` - действия
- ✅ `Badge` - роль пользователя

#### 4. UX Features
- ✅ Loading state при выдаче доступа
- ✅ Disabled кнопки "Выдать" если курс не выбран
- ✅ Toast уведомления (успех/ошибка)
- ✅ Автоматическое закрытие диалога при успехе

---

## Поток работы (User Flow)

```
1. Админ открывает /admin/users
   ↓
2. Видит таблицу всех пользователей
   ↓
3. Нажимает кнопку "Доступ" в строке пользователя
   ↓
4. Открывается Dialog
   ↓
5. Админ выбирает курс из Select
   ↓
6. Нажимает "Выдать доступ"
   ↓
7. POST /api/admin/grant-access
   ↓
8. Success:
   - Toast: "Доступ выдан!"
   - Dialog закрывается
   
   Или Error:
   - Toast с описанием ошибки
   - Dialog остаётся открытым
```

---

## Как протестировать

### 1. Подготовка
```powershell
# Backend и Frontend должны быть запущены
# Войти как admin@nails-course.ru / admin123
```

### 2. Открыть админку
```
http://localhost:3000/admin/users
```

### 3. Выдать доступ
```
1. Найди пользователя в таблице (student@test.ru)
2. Нажми кнопку "Доступ"
3. В модальном окне выбери курс
4. Нажми "Выдать доступ"

Ожидается:
✅ Toast: "Доступ выдан!"
✅ Modal закрывается
```

### 4. Проверить в БД
```sql
SELECT * FROM purchases WHERE user_id = 'id_студента';

Должна быть запись:
- payment_status: success
- expires_at: сегодня + 365 дней
- payment_id: admin_grant_XXX
```

### 5. Войти под студентом
```
1. Logout из админки
2. Login как student@test.ru / student123
3. Перейди на /dashboard

Ожидается:
✅ Новый курс отображается в списке
```

---

## Технические детали

### Установленные компоненты
```bash
npx shadcn@latest add dialog select
```

### Файлы
```
Backend:
✅ backend/app/api/admin.py (обновлён)

Frontend:
✅ frontend/src/lib/api.ts (обновлён)
✅ frontend/src/app/admin/users/page.tsx (переписан)
✅ frontend/src/components/ui/dialog.tsx (установлен)
✅ frontend/src/components/ui/select.tsx (установлен)
```

---

## Условия выдачи доступа

| Параметр | Значение |
|----------|----------|
| **Доступ** | 365 дней с момента выдачи |
| **Тариф** | self (по умолчанию) |
| **Статус** | success (оплачено) |
| **Если доступ существует** | Продлевается на 365 дней |
| **payment_id** | `admin_grant_{12 символов}` |

---

## Следующие шаги

### Приоритет Высокий
- [ ] **Фаза 5.3:** Просмотр истории покупок в админке
- [ ] **Фаза 5.4:** CRUD для курсов (создание/редактирование)

### Улучшения (опционально)
- [ ] Выбор тарифа (self/support) в форме
- [ ] Отображение текущих покупок пользователя в диалоге
- [ ] Bulk actions (выдача доступа нескольким пользователям)
- [ ] История действий админа (audit log)

---

## Troubleshooting

### Проблема: "Admin access required"
**Причина:** Вошли не под админом.  
**Решение:** Войди как `admin@nails-course.ru`.

### Проблема: Курсы не загружаются в Select
**Причина:** Backend не отвечает или нет курсов в БД.  
**Решение:** Проверь seed данные (`python seed_data.py`).

### Проблема: Dialog не открывается
**Причина:** Конфликт состояний React.  
**Решение:** Проверь Console на ошибки.

---

## Статистика

```
Backend:
  ✅ Эндпоинтов: +2 (GET courses, POST grant-access)
  ✅ Схем Pydantic: +3

Frontend:
  ✅ API методов: +2 (getAllCourses, adminGrantAccess)
  ✅ Компонентов: +2 (Dialog, Select)
  ✅ Переписано: 1 страница (users)

Время: ~30 минут
```

---

**Manual Grant Access - ГОТОВО! 🎉**

Админ теперь может:
- ✅ Посмотреть всех пользователей
- ✅ Выдать доступ к любому курсу
- ✅ Продлить существующий доступ
- ✅ Видеть подтверждения через Toast
