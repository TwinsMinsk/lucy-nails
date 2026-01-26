# Фаза 2.5: Тесты API (Завершена)

## Реализованные тесты (`backend/tests/`)
Все тесты написаны с использованием `pytest` и `pytest-asyncio`, клиент `httpx.AsyncClient`.

### 1. Настройка окружения (`conftest.py`)
- Создана отдельная тестовая база данных `test_nails_course`.
- Реализована фикстура `prepare_database` (создание таблиц перед сессией).
- Реализована фикстура `db` (очистка данных `TRUNCATE` перед каждым тестом).
- Реализован Override зависимости `get_db`.

### 2. Тесты Аутентификации (`test_auth.py`)
- `test_register_user`: Успешная регистрация (проверка ответа и БД).
- `test_login_user`: Вход и получением JWT токена.
- `test_get_me`: Получение профиля по токену.

### 3. Тесты Курсов (`test_courses.py`)
- `test_get_courses_empty`: Пустой список.
- `test_get_courses_list`: Список с фильтрацией/сортировкой.
- `test_get_course_detail`: Детали курса.
- `test_get_modules_and_lessons`: Иерархия курс -> модули -> уроки.
- `test_lesson_detail`: Проверка доступа к уроку (требует логина).

### 4. Тесты Покупок (`test_purchases.py`)
- `test_create_and_list_purchases`: Создание заказа и получение истории.

## Результаты
- **9 тестов пройдено**.
- Исправлены проблемы с Pydantic валидацией (UUID, Enum).
- Исправлены проблемы с `MissingGreenlet` (expire_on_commit=False).

## Запуск
```powershell
.\backend\venv\Scripts\python.exe backend/scripts/create_test_db.py  # Один раз
$env:PYTHONPATH="backend"; .\backend\venv\Scripts\python.exe -m pytest backend/tests -v
```
