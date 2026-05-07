"""
Seed данные для разработки (упрощённая версия с psycopg2).

Читает промо-метаданные из scripts/promo/program.json (если файл есть).
Пароли и параметры БД — через переменные окружения (без хардкода).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import psycopg2
from psycopg2.extras import Json, execute_values

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "backend"))

from app.core.security import get_password_hash

PROGRAM_JSON = _REPO_ROOT / "scripts" / "promo" / "program.json"


def get_connection():
    """Создаёт подключение к БД из окружения."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        database=os.getenv("POSTGRES_DB", "nails_course"),
    )


# (module_title, lesson_title, duration_seconds, kinescope_video_id, is_preview)
LANDING_MODULES: list[tuple[str, str, int, str | None, bool]] = [
    ("Фольга", "Фольга", 900, "askD5i8gAV6gvqpq5aSg8W", True),
    ("Аквариум", "Аквариум", 1800, "dummy-video-akvarium", False),
    ("Втирка", "Втирка", 1440, "dummy-video-vtirka", False),
    ("Слайдеры и наклейки", "Слайдеры и наклейки", 1260, "dummy-video-slaidery", False),
    ("Френч", "Френч", 2520, "dummy-video-french", False),
    ("Пигменты", "Пигменты", 780, "dummy-video-pigmenty", False),
    ("Стемпинг", "Стемпинг", 1080, "dummy-video-stemping", False),
    ("Стразы/объемные украшения", "Стразы/объемные украшения", 2820, "dummy-video-strazy", False),
    ("Текстуры", "Текстуры", 1500, "dummy-video-tekstury", False),
    ("Градиент", "Градиент", 1500, "dummy-video-gradient", False),
    ("Аэрография", "Аэрография", 1140, "dummy-video-aero", False),
]


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
            datetime.utcnow(),
        ),
        (
            student_id,
            "student@test.ru",
            get_password_hash("student123"),
            None,
            "student",
            datetime.utcnow(),
            datetime.utcnow(),
        ),
    ]

    execute_values(
        cur,
        """
        INSERT INTO users (id, email, password_hash, telegram_id, role, created_at, updated_at)
        VALUES %s
        """,
        users,
    )

    print("✓ Создан админ: admin@nails-course.ru (пароль: admin123)")
    print("✓ Создан студент: student@test.ru (пароль: student123)")

    return admin_id, student_id


def apply_program_promos(cur) -> None:
    """Подтягивает промо из program.json (после генерации пайплайном)."""
    if not PROGRAM_JSON.is_file():
        print("ℹ scripts/promo/program.json не найден — промо-поля не заполнены из файла")
        return

    data = json.loads(PROGRAM_JSON.read_text(encoding="utf-8"))
    count = 0
    for mod in data.get("modules", []):
        title = mod.get("title")
        promo = mod.get("promo") or {}
        if not title:
            continue
        hid = promo.get("kinescope_id")
        poster = promo.get("poster")
        desc = promo.get("description")
        bullets = promo.get("bullets") or []
        segments = promo.get("highlight_segments") or []
        highlights_obj = {"bullets": bullets, "segments": segments}
        cur.execute(
            """
            UPDATE lessons AS l SET
              promo_kinescope_video_id = COALESCE(%s, l.promo_kinescope_video_id),
              promo_poster_url = COALESCE(%s, l.promo_poster_url),
              promo_description = COALESCE(%s, l.promo_description),
              promo_highlights = COALESCE(%s, l.promo_highlights)
            FROM modules m
            WHERE l.module_id = m.id AND m.title = %s AND l.order_index = 1
            """,
            (
                hid,
                poster,
                desc,
                Json(highlights_obj),
                title,
            ),
        )
        count += cur.rowcount
    print(f"✓ Обновлено промо из program.json (строк затронуто): {count}")


def seed_course(cur):
    """Создаёт курс с модулями и по одному уроку на модуль (программа как на лендинге)."""
    course_id = str(uuid4())

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
            datetime.utcnow(),
        ),
    )
    print("✓ Создан курс: Дизайн ногтей: От А до Я")

    modules_rows = []
    module_ids: list[str] = []
    for i, (m_title, _, _, _, _) in enumerate(LANDING_MODULES, start=1):
        mid = str(uuid4())
        module_ids.append(mid)
        modules_rows.append(
            (
                mid,
                course_id,
                m_title,
                f"Модуль «{m_title}».",
                i,
                True,
                datetime.utcnow(),
            )
        )

    execute_values(
        cur,
        """
        INSERT INTO modules (id, course_id, title, description, order_index, is_published, created_at)
        VALUES %s
        """,
        modules_rows,
    )

    lesson_rows = []
    first_lesson_id: str | None = None
    for mid, (m_title, lesson_title, duration, kid, is_preview) in zip(module_ids, LANDING_MODULES, strict=True):
        lid = str(uuid4())
        if first_lesson_id is None:
            first_lesson_id = lid
        lesson_rows.append(
            (
                lid,
                mid,
                lesson_title,
                f"Урок «{lesson_title}».",
                kid,
                duration,
                1,
                is_preview,
                datetime.utcnow(),
            )
        )

    execute_values(
        cur,
        """
        INSERT INTO lessons (id, module_id, title, description, kinescope_video_id,
                            duration_seconds, order_index, is_preview, created_at)
        VALUES %s
        """,
        lesson_rows,
    )

    apply_program_promos(cur)

    print(f"✓ Создано модулей: {len(LANDING_MODULES)}, по одному уроку в каждом")

    return course_id, first_lesson_id


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
            500000,
            f"test_payment_{user_id[:8]}",
            "success",
            datetime.utcnow() + timedelta(days=365),
            datetime.utcnow(),
        ),
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
            450,
            False,
            None,
            datetime.utcnow(),
        ),
    )

    print("✓ Создан прогресс для первого урока")


def clear_database(cur):
    """Очищает все таблицы перед вставкой новых данных."""
    print("🗑️  Очистка существующих данных...")

    cur.execute(
        """
        TRUNCATE TABLE
            progress,
            purchases,
            certificates,
            lessons,
            modules,
            courses,
            users
        RESTART IDENTITY CASCADE
        """
    )

    print("✓ База данных очищена")


def main():
    """Основная функция."""
    print("\n=== Заполнение БД тестовыми данными ===\n")

    conn = get_connection()
    cur = conn.cursor()

    try:
        clear_database(cur)

        admin_id, student_id = seed_users(cur)

        course_id, first_lesson_id = seed_course(cur)

        seed_purchase(cur, admin_id, course_id, "admin@nails-course.ru")
        seed_purchase(cur, student_id, course_id, "student@test.ru")

        seed_progress(cur, student_id, first_lesson_id)

        conn.commit()

        print("\n✅ База данных успешно заполнена!")
        print("\n📊 Статистика:")
        print("   - Пользователей: 2 (1 админ + 1 студент)")
        print("   - Курсов: 1")
        print(f"   - Модулей: {len(LANDING_MODULES)}")
        print(f"   - Уроков: {len(LANDING_MODULES)}")
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
