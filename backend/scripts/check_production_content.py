"""Validate production course content before a release."""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.database import async_session_maker  # noqa: E402
from app.models.course import Course  # noqa: E402
from app.models.lesson import Lesson  # noqa: E402
from app.models.module import Module  # noqa: E402


async def main() -> int:
    async with async_session_maker() as db:
        published_courses = await db.execute(select(Course).where(Course.is_published.is_(True)))
        courses = published_courses.scalars().all()
        if not courses:
            print("No published courses found.", file=sys.stderr)
            return 1

        missing_video_ids = await db.execute(
            select(Course.title, Module.title, Lesson.title)
            .join(Module, Module.course_id == Course.id)
            .join(Lesson, Lesson.module_id == Module.id)
            .where(
                Course.is_published.is_(True),
                Module.is_published.is_(True),
                Lesson.is_preview.is_(False),
                (Lesson.kinescope_video_id.is_(None)) | (Lesson.kinescope_video_id == ""),
            )
        )
        missing = missing_video_ids.all()
        if missing:
            print("Closed production lessons without kinescope_video_id:", file=sys.stderr)
            for course_title, module_title, lesson_title in missing:
                print(f"- {course_title} / {module_title} / {lesson_title}", file=sys.stderr)
            return 1

    print("Production content checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
