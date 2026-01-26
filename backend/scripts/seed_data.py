"""
Seed данные для разработки (упрощённая версия с psycopg2).
"""

import sys
sys.path.append('d:\\Course nails design\\backend')

from datetime import datetime, timedelta
from uuid import uuid4

import psycopg2
from psycopg2.extras import execute_values

from app.core.security import get_password_hash


def get_connection():
    """Создаёт подключение к БД."""
    return psycopg2.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="Punkrock77",
        database="nails_course"
    )


def seed_users(cur):
    """Создаёт тестовых пользователей."""
    admin_id = str(uuid4())
    student_id = str(uuid4())
    
    users = [
        (
            admin_id,
            "admin@nails-course.ru",
            get_password_hash("admin123"),
            None,
            "admin",
            datetime.utcnow(),
            datetime.utcnow()
        ),
        (
            student_id,
            "student@test.ru",
            get_password_hash("student123"),
            None,
            "student",
            datetime.utcnow(),
            datetime.utcnow()
        ),
    ]
    
    execute_values(
        cur,
        """
        INSERT INTO users (id, email, password_hash, telegram_id, role, created_at, updated_at)
        VALUES %s
        """,
        users
    )
    
    print("✓ Создан админ: admin@nails-course.ru (пароль: admin123)")
    print("✓ Создан студент: student@test.ru (пароль: student123)")
    
    return admin_id, student_id


def seed_course(cur):
    """Создаёт курс с модулями и уроками."""
    course_id = str(uuid4())
    
    # Курс
    cur.execute(
        """
        INSERT INTO courses (id, title, description, preview_video_url, cover_image_url, 
                            price_self, price_support, is_published, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            course_id,
            "Дизайн ногтей: От А до Я",
            "Полный курс по дизайну ногтей для начинающих и опытных мастеров.",
            None,
            None,
            5000,
            20000,
            True,
            datetime.utcnow()
        )
    )
    print("✓ Создан курс: Дизайн ногтей: От А до Я")
    
    # Модули
    modules = [
        (str(uuid4()), course_id, "Все возможности фольги", 
         "Научитесь работать с фольгой.", 1, True, datetime.utcnow()),
        (str(uuid4()), course_id, "Градиент", 
         "Различные виды градиентов.", 2, True, datetime.utcnow()),
        (str(uuid4()), course_id, "Френч", 
         "Разнообразие форм френча.", 3, True, datetime.utcnow()),
    ]
    
    execute_values(
        cur,
        """
        INSERT INTO modules (id, course_id, title, description, order_index, is_published, created_at)
        VALUES %s
        """,
        modules
    )
    
    # Уроки для модуля 1 (с kinescope_video_id)
    module1_id = modules[0][0]
    lessons_m1 = [
        (str(uuid4()), module1_id, "Как отпечатать фольгу", 
         "Базовая техника работы с фольгой.", "dummy-video-id-1", 900, 1, True, datetime.utcnow()),
        (str(uuid4()), module1_id, "Сложные вариации дизайнов", 
         "Комбинирование с хлопьями.", "dummy-video-id-2", 1200, 2, False, datetime.utcnow()),
        (str(uuid4()), module1_id, "Поталь", 
         "Работа с поталью.", "dummy-video-id-3", 600, 3, False, datetime.utcnow()),
        (str(uuid4()), module1_id, "Битое стекло", 
         "Дизайн Аврора.", "dummy-video-id-4", 1800, 4, False, datetime.utcnow()),
    ]
    
    # Уроки для модуля 2 (с kinescope_video_id)
    module2_id = modules[1][0]
    lessons_m2 = [
        (str(uuid4()), module2_id, "Виды легких градиентов", 
         "Пастельное омбре.", "dummy-video-id-5", 900, 1, False, datetime.utcnow()),
        (str(uuid4()), module2_id, "Молочный градиент", 
         "На блёстки и на цвет.", "dummy-video-id-6", 1200, 2, False, datetime.utcnow()),
    ]
    
    # Уроки для модуля 3 (с kinescope_video_id)
    module3_id = modules[2][0]
    lessons_m3 = [
        (str(uuid4()), module3_id, "Разнообразие форм и линейный френч", 
         "Классический френч.", "dummy-video-id-7", 1500, 1, False, datetime.utcnow()),
        (str(uuid4()), module3_id, "Креативный френч", 
         "С линиями, втиркой.", "dummy-video-id-8", 1200, 2, False, datetime.utcnow()),
    ]
    
    all_lessons = lessons_m1 + lessons_m2 + lessons_m3
    
    execute_values(
        cur,
        """
        INSERT INTO lessons (id, module_id, title, description, kinescope_video_id, 
                            duration_seconds, order_index, is_preview, created_at)
        VALUES %s
        """,
        all_lessons
    )
    
    print(f"✓ Создан модуль 1: Все возможности фольги ({len(lessons_m1)} уроков)")
    print(f"✓ Создан модуль 2: Градиент ({len(lessons_m2)} уроков)")
    print(f"✓ Создан модуль 3: Френч ({len(lessons_m3)} уроков)")
    
    return course_id, all_lessons[0][0]  # course_id и first_lesson_id


def seed_purchase(cur, user_id, course_id, user_email):
    """Создаёт тестовую покупку."""
    purchase_id = str(uuid4())
    
    cur.execute(
        """
        INSERT INTO purchases (id, user_id, course_id, tariff, amount_kopecks, 
                              payment_id, payment_status, expires_at, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            purchase_id,
            user_id,
            course_id,
            "self",
            500000,  # 5000 руб
            f"test_payment_{user_id[:8]}",
            "success",  # Используем 'success' согласно ENUM в модели
            datetime.utcnow() + timedelta(days=365),  # 1 год доступа
            datetime.utcnow()
        )
    )
    
    print(f"✓ Создана покупка для {user_email} (тариф: self, доступ: 365 дней)")


def seed_progress(cur, student_id, first_lesson_id):
    """Создаёт тестовый прогресс."""
    progress_id = str(uuid4())
    
    cur.execute(
        """
        INSERT INTO progress (id, user_id, lesson_id, watched_seconds, 
                             is_completed, completed_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            progress_id,
            student_id,
            first_lesson_id,
            450,  # 7.5 минут из 15
            False,
            None,
            datetime.utcnow()
        )
    )
    
    print("✓ Создан прогресс для первого урока")


def clear_database(cur):
    """Очищает все таблицы перед вставкой новых данных."""
    print("🗑️  Очистка существующих данных...")
    
    # TRUNCATE удаляет все данные и сбрасывает AUTO_INCREMENT
    # CASCADE автоматически удалит данные из зависимых таблиц
    cur.execute("""
        TRUNCATE TABLE 
            progress, 
            purchases, 
            certificates, 
            lessons, 
            modules, 
            courses, 
            users 
        RESTART IDENTITY CASCADE
    """)
    
    print("✓ База данных очищена")


def main():
    """Основная функция."""
    print("\n=== Заполнение БД тестовыми данными ===\n")
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # 0. Очистка существующих данных
        clear_database(cur)
        
        # 1. Пользователи
        admin_id, student_id = seed_users(cur)
        
        # 2. Курс с модулями и уроками
        course_id, first_lesson_id = seed_course(cur)
        
        # 3. Покупки (для обоих пользователей)
        seed_purchase(cur, admin_id, course_id, "admin@nails-course.ru")
        seed_purchase(cur, student_id, course_id, "student@test.ru")
        
        # 4. Прогресс
        seed_progress(cur, student_id, first_lesson_id)
        
        conn.commit()
        
        print("\n✅ База данных успешно заполнена!")
        print("\n📊 Статистика:")
        print("   - Пользователей: 2 (1 админ + 1 студент)")
        print("   - Курсов: 1")
        print("   - Модулей: 3")
        print("   - Уроков: 8 (все с kinescope_video_id)")
        print("   - Покупок: 2 (обе с доступом на 365 дней)")
        print("   - Прогресс: 1")
        
        print("\n🔑 Учётные данные:")
        print("   Админ: admin@nails-course.ru / admin123")
        print("   Студент: student@test.ru / student123")
        print("\n💡 Оба пользователя имеют доступ к курсу!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Ошибка: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
