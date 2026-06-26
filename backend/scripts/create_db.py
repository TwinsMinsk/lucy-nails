"""
Скрипт для создания БД nails_course.
"""

import os

import psycopg2
from psycopg2 import sql
from sqlalchemy.engine import make_url

# Same source/default as the application (app/core/config.py).
DEFAULT_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/nails_course"


def _maintenance_conn_params() -> dict:
    """Connection params for the 'postgres' maintenance DB, parsed from DATABASE_URL."""
    url = make_url(os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL)
    return {
        "host": url.host or "localhost",
        "port": url.port or 5432,
        "user": url.username or "postgres",
        "password": url.password,
        "database": "postgres",
    }


def create_database():
    """Создаёт БД nails_course если её ещё нет."""
    try:
        # Connect to the 'postgres' maintenance DB (credentials from DATABASE_URL)
        conn = psycopg2.connect(**_maintenance_conn_params())
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
