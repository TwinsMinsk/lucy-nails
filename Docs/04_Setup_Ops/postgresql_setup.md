# Решение проблемы с PostgreSQL

## Проблема
PostgreSQL установлен, но не запущен как служба Windows и не подключается на localhost:5432.

## Решения

### Вариант 1: pgAdmin (РЕКОМЕНДУЕТСЯ)
1. Запусти pgAdmin 4
2. Подключись к серверу (localhost)
3. Правый клик → Databases → Create → Database
4. Имя: `nails_course`
5. Owner: `postgres`
6. Save

### Вариант 2: Найти и запустить службу вручную
```powershell
# Найти PostgreSQL в Services
services.msc

# Искать "postgresql" → Start
```

### Вариант 3: Запуск PostgreSQL вручную
```powershell
# Найти путь к установке
cd "C:\Program Files\PostgreSQL\17\bin"
pg_ctl.exe start -D "C:\Program Files\PostgreSQL\17\data"
```

## После создания БД
```powershell
cd backend
.\venv\Scripts\alembic.exe revision --autogenerate -m "Initial schema with 7 tables"
.\venv\Scripts\alembic.exe upgrade head
```

## Статус
- [x] SQLAlchemy модели созданы (7 таблиц)
- [x] Alembic настроен
- [x] psycopg2 установлен
- [ ] БД nails_course создана ← **НУЖНО СДЕЛАТЬ**
- [ ] Миграция применена
