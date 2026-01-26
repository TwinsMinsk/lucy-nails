"""
Скрипт для создания БД nails_course.
"""

import psycopg2
from psycopg2 import sql

def create_database():
    """Создаёт БД nails_course если её ещё нет."""
    try:
        # Подключение к postgres БД для создания новой БД
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            database="postgres"
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Проверка существования БД
        cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            ("nails_course",)
        )
        
        if cur.fetchone():
            print("✓ БД 'nails_course' уже существует")
        else:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(
                sql.Identifier("nails_course")
            ))
            print("✓ БД 'nails_course' успешно создана")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Ошибка при создании БД: {e}")
        return False
    
    return True


if __name__ == "__main__":
    create_database()
