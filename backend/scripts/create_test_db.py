"""
Скрипт для создания тестовой БД test_nails_course.
"""

import psycopg2
from psycopg2 import sql

def create_test_database():
    """Создаёт БД test_nails_course если её ещё нет."""
    try:
        # Подключение к postgres БД
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="Punkrock77", # Пароль из .env
            database="postgres"
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Проверка
        cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            ("test_nails_course",)
        )
        
        if cur.fetchone():
            print("✓ БД 'test_nails_course' уже существует")
        else:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(
                sql.Identifier("test_nails_course")
            ))
            print("✓ БД 'test_nails_course' успешно создана")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Ошибка при создании тестовой БД: {e}")
        return False
    
    return True


if __name__ == "__main__":
    create_test_database()
