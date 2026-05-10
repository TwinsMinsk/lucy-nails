"""One-off: ensure the "Фольга" module is published and its lesson has the
real Kinescope video id, so the course shows 11 modules end-to-end.

Idempotent. Transactional. If the placeholder already matches the desired
state, the script is a no-op.

Usage:
  DATABASE_URL='postgresql://user:pass@host:port/db' python backend/scripts/add_folga_module.py
"""

import os
import sys
import uuid

import psycopg2

COURSE_ID = "db11a7f7-8dfa-437b-b9da-69c641140300"
FOLGA_TITLE = "Фольга"
FOLGA_DESCRIPTION = (
    "Разберёте, как получать чистый отпечаток фольги на липком слое, базе, "
    "праймере и клее, а не надеяться на случай."
)
FOLGA_LESSON_VIDEO_ID = "4c8fb065-b27f-4f43-8267-c53241b89448"
FOLGA_LESSON_DURATION_SECONDS = 1366  # ~22m46s


def _show_modules(cur, label: str) -> None:
    cur.execute(
        """
        SELECT m.title, m.order_index, m.is_published,
               (SELECT l.kinescope_video_id FROM lessons l
                  WHERE l.module_id = m.id ORDER BY l.order_index LIMIT 1) AS first_lesson_video,
               (SELECT l.duration_seconds FROM lessons l
                  WHERE l.module_id = m.id ORDER BY l.order_index LIMIT 1) AS first_lesson_duration
        FROM modules m
        WHERE m.course_id = %s
        ORDER BY m.order_index, m.created_at
        """,
        (COURSE_ID,),
    )
    print(f"{label}:")
    for row in cur.fetchall():
        title, order, pub, vid, dur = row
        print(f"  order={order:3d}  pub={pub!s:5s}  vid={(vid or '<none>')[:36]:36s}  dur={dur or 0:5d}s  title={title}")


def main() -> int:
    raw_url = os.getenv("DATABASE_URL", "")
    if not raw_url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 2

    dsn = raw_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            _show_modules(cur, "BEFORE")

            cur.execute(
                "SELECT id, is_published FROM modules WHERE course_id = %s AND title = %s",
                (COURSE_ID, FOLGA_TITLE),
            )
            row = cur.fetchone()

            if row is None:
                module_id = uuid.uuid4()
                lesson_id = uuid.uuid4()
                cur.execute(
                    """
                    INSERT INTO modules
                      (id, course_id, title, description, order_index, is_published, created_at)
                    VALUES
                      (%s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (str(module_id), COURSE_ID, FOLGA_TITLE, FOLGA_DESCRIPTION, 0, True),
                )
                cur.execute(
                    """
                    INSERT INTO lessons
                      (id, module_id, title, description, kinescope_video_id,
                       duration_seconds, content, order_index, is_preview, created_at)
                    VALUES
                      (%s, %s, %s, NULL, %s, %s, NULL, %s, %s, NOW())
                    """,
                    (
                        str(lesson_id),
                        str(module_id),
                        FOLGA_TITLE,
                        FOLGA_LESSON_VIDEO_ID,
                        FOLGA_LESSON_DURATION_SECONDS,
                        0,
                        False,
                    ),
                )
                print(f"INSERTED module {module_id} + lesson {lesson_id}")
            else:
                module_id, was_published = row[0], row[1]

                cur.execute(
                    "UPDATE modules SET is_published = TRUE WHERE id = %s AND is_published = FALSE",
                    (str(module_id),),
                )
                published = cur.rowcount

                cur.execute(
                    """
                    UPDATE lessons
                    SET kinescope_video_id = %s,
                        duration_seconds = %s
                    WHERE module_id = %s
                      AND (kinescope_video_id IS DISTINCT FROM %s
                           OR duration_seconds IS DISTINCT FROM %s)
                    """,
                    (
                        FOLGA_LESSON_VIDEO_ID,
                        FOLGA_LESSON_DURATION_SECONDS,
                        str(module_id),
                        FOLGA_LESSON_VIDEO_ID,
                        FOLGA_LESSON_DURATION_SECONDS,
                    ),
                )
                lesson_updated = cur.rowcount

                if published == 0 and lesson_updated == 0:
                    print(f"NOOP: module {module_id} already configured correctly")
                else:
                    print(
                        f"UPDATED module {module_id}: published+={published}, lesson_rows+={lesson_updated}"
                    )

            _show_modules(cur, "AFTER")

            cur.execute(
                """
                SELECT COUNT(*) FROM modules
                WHERE course_id = %s AND is_published = TRUE
                """,
                (COURSE_ID,),
            )
            (published_count,) = cur.fetchone()
            if published_count != 11:
                raise RuntimeError(
                    f"Expected 11 published modules after change, got {published_count}; rolling back"
                )

        conn.commit()
        print("OK: committed")
        return 0
    except Exception as e:
        conn.rollback()
        print(f"FAILED: {e}; transaction rolled back", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
