# Инструкция: Создание БД nails_course через pgAdmin

## Вариант 1: Через pgAdmin (GUI)
1. Открой pgAdmin
2. Подключись к серверу PostgreSQL (localhost)
3. Правый клик на "Databases" → "Create" → "Database..."
4. Введи имя: `nails_course`
5. Owner: `postgres`
6. Click "Save"

## Вариант 2: Через psql (если есть в PATH)
```bash
psql -U postgres -c "CREATE DATABASE nails_course;"
```

## Вариант 3: Через Python
```python
import psycopg2
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="postgres",
    password="postgres"
)
conn.autocommit = True
cur = conn.cursor()
cur.execute("CREATE DATABASE nails_course;")
cur.close()
conn.close()
```

После создания БД выполни:
```bash
cd backend
.\venv\Scripts\alembic.exe revision --autogenerate -m "Initial schema"
.\venv\Scripts\alembic.exe upgrade head
```
