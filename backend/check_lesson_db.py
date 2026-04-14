
import asyncio
import uuid
import sys
import os
from pathlib import Path

# Добавляем корень проекта в sys.path, чтобы импорты 'app' работали корректно
current_file = Path(__file__).resolve()
backend_root = current_file.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from sqlalchemy import select
from app.core.database import async_session_maker, engine
from app.models.lesson import Lesson

async def check_lesson(lesson_id_str: str):
    """
    Проверяет наличие урока в базе данных по его ID.
    
    Args:
        lesson_id_str: Строковое представление UUID урока.
    """
    try:
        try:
            lesson_id = uuid.UUID(lesson_id_str)
        except ValueError:
            print(f"❌ Ошибка: '{lesson_id_str}' не является валидным UUID.")
            return

        async with async_session_maker() as session:
            # Использование session.get — наиболее эффективный способ получения записи по PK
            lesson = await session.get(Lesson, lesson_id)
            
            if lesson:
                print(f"✅ Урок найден: \"{lesson.title}\"")
                print(f"   ID:           {lesson.id}")
                print(f"   Kinescope ID: {lesson.kinescope_video_id or 'отсутствует'}")
                print(f"   Module ID:    {lesson.module_id}")
                print(f"   Order Index:  {lesson.order_index}")
                print(f"   Is Preview:   {'Да' if lesson.is_preview else 'Нет'}")
            else:
                print(f"❌ Урок с ID {lesson_id_str} не найден в базе данных.")
                
            # Показать последние уроки для помощи в отладке
            print("\nПоследние 10 уроков в БД (для справки):")
            query = select(Lesson).order_by(Lesson.created_at.desc()).limit(10)
            result = await session.execute(query)
            lessons = result.scalars().all()
            
            if not lessons:
                print("   (База данных уроков пуста)")
            for l in lessons:
                print(f" - {l.id}: {l.title} (kinescope: {l.kinescope_video_id})")
                
    except Exception as e:
        print(f"⚠️ Произошла непредвиденная ошибка: {e}")
    finally:
        # Рекомендуется закрывать engine в скриптах, чтобы не висели активные соединения
        await engine.dispose()

if __name__ == "__main__":
    # По умолчанию проверяем первый попавшийся аргумент или используем заглушку
    lid = sys.argv[1] if len(sys.argv) > 1 else "ede4f264-6bad-4b9b-adf4-e16c480ef2c7"
    
    if sys.platform == "win32":
        # Исправление для Windows: предотвращение ошибок при закрытии цикла событий
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(check_lesson(lid))
