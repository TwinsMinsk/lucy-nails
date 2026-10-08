"""Create synthetic load fixtures only in an explicitly named isolated database."""

import argparse
import asyncio
import json
import os
import secrets
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, uuid5

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.core.config import settings  # noqa: E402
from app.core.database import async_session_maker  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.course import Course  # noqa: E402
from app.models.module import Module  # noqa: E402
from app.models.lesson import Lesson  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.entitlement import Entitlement  # noqa: E402
from app.services.session_service import SessionService  # noqa: E402
from starlette.requests import Request  # noqa: E402


def validate_target(url: str, environment: str, confirmed: str) -> None:
    database = urlparse(url).path.lstrip("/")
    if (
        environment.lower() not in {"test", "staging"}
        or "load_staging" not in database
        or confirmed != database
    ):
        raise ValueError(
            "Fixtures require test/staging and an exactly confirmed load_staging database"
        )


async def seed(output: Path) -> None:
    def identity(value):
        return uuid5(NAMESPACE_URL, f"lucy-readiness-load:{value}")

    course_id = identity("course:11-lessons")
    lesson_ids = [identity(f"lesson:{index}") for index in range(11)]
    now = datetime.utcnow()
    learners = []
    async with async_session_maker() as db:
        if await db.get(Course, course_id) is None:
            db.add(
                Course(
                    id=course_id,
                    title="Synthetic load staging",
                    price_self=5900,
                    price_support=0,
                    is_published=True,
                    access_days=30,
                )
            )
            await db.flush()
            for index, lesson_id in enumerate(lesson_ids):
                module_id = identity(f"module:{index}")
                db.add(
                    Module(
                        id=module_id,
                        course_id=course_id,
                        title=f"Synthetic module {index}",
                        order_index=index,
                        is_published=True,
                    )
                )
                await db.flush()
                db.add(
                    Lesson(
                        id=lesson_id,
                        module_id=module_id,
                        title=f"Synthetic paid lesson {index}",
                        content="Synthetic load-only material",
                        duration_seconds=1800,
                        order_index=0,
                    )
                )
                await db.flush()
        for index in range(100):
            user_id, entitlement_id = (
                identity(f"user:{index}"),
                identity(f"entitlement:11:{index}"),
            )
            password = secrets.token_urlsafe(18)
            email = f"load-learner-{index}@example.com"
            user = await db.get(User, user_id)
            if user is None:
                user = User(id=user_id, email=email, role="student")
                db.add(user)
            user.password_hash = get_password_hash(password)
            user.email = email
            user.email_verified_at = now
            user.token_version = (user.token_version or 0) + 1
            await db.flush()
            if await db.get(Entitlement, entitlement_id) is None:
                db.add(
                    Entitlement(
                        id=entitlement_id,
                        user_id=user_id,
                        course_id=course_id,
                        source="manual",
                        tariff="self",
                        status="active",
                        starts_at=now,
                        expires_at=now + timedelta(days=30),
                        reason="Synthetic load fixture",
                    )
                )
            tokens, _ = await SessionService.issue(
                db,
                user,
                Request({"type": "http", "headers": [], "client": ("127.0.0.1", 0)}),
            )
            learners.append(
                {
                    "email": email,
                    "access_token": tokens.access_token,
                    "lesson_id": str(lesson_ids[0]),
                    "lesson_ids": [str(lesson_id) for lesson_id in lesson_ids],
                }
            )
        await db.commit()
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(
        output,
        "w",
        encoding="utf-8",
        opener=lambda path, flags: os.open(path, flags, 0o600),
    ) as stream:
        json.dump(learners, stream)
    print(
        json.dumps(
            {
                "course_id": str(course_id),
                "course_price": 5900,
                "learner_count": len(learners),
                "fixture_path": str(output),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-database", required=True)
    parser.add_argument("--output", default="scripts/load/learners.local.json")
    args = parser.parse_args()
    try:
        validate_target(
            settings.DATABASE_URL, settings.ENVIRONMENT, args.confirm_database
        )
    except ValueError as error:
        parser.error(str(error))
    asyncio.run(seed(Path(args.output)))
