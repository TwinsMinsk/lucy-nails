"""Set Kinescope video for the first foil lesson

Revision ID: f6e4f3b2a901
Revises: c8d41b2a9f01
Create Date: 2026-05-06

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f6e4f3b2a901"
down_revision: Union[str, None] = "c8d41b2a9f01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE lessons
        SET kinescope_video_id = 'askD5i8gAV6gvqpq5aSg8W'
        WHERE title = 'Как отпечатать фольгу'
          AND order_index = 1
          AND module_id IN (
              SELECT id
              FROM modules
              WHERE title = 'Все возможности фольги'
          )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE lessons
        SET kinescope_video_id = 'dummy-video-id-1'
        WHERE title = 'Как отпечатать фольгу'
          AND order_index = 1
          AND kinescope_video_id = 'askD5i8gAV6gvqpq5aSg8W'
          AND module_id IN (
              SELECT id
              FROM modules
              WHERE title = 'Все возможности фольги'
          )
        """
    )
