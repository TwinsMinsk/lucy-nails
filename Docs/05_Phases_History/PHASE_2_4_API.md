# Фаза 2.4: API Покупок (Завершена)

## Реализованный функционал

### 1. Pydantic схемы (`app/schemas/purchase.py`)
- `PurchaseCreate`: `course_id`, `tariff`
- `PurchaseResponse`: полные данные о покупке, включая `payment_status`.
- `TariffType`: Enum `self` | `support`.

### 2. Сервис (`app/services/purchase_service.py`)
- `create_purchase`: 
  - Находит курс.
  - Рассчитывает цену и дату окончания (3 месяца для self, 6 месяцев для support).
  - Создает запись со статусом `pending`.
- `get_user_purchases`: Возвращает историю покупок пользователя.
- `get_purchase_by_id`: Поиск по ID.

### 3. API Endpoints (`app/api/purchases.py`)

#### POST `/api/purchases/create`
Создает заказ.
- Требует авторизации.
- Возвращает объект покупки с `payment_url` (mock-ссылка).
- Тело: `{"course_id": "...", "tariff": "self"}`

#### GET `/api/purchases/my`
История покупок.
- Требует авторизации.
- Возвращает список покупок, отсортированный по дате.
