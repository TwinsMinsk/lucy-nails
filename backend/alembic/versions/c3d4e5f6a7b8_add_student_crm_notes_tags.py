"""add student CRM notes and tags

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "student_notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_student_notes_user_id", "student_notes", ["user_id"])
    op.create_index("ix_student_notes_author_id", "student_notes", ["author_id"])
    op.create_table(
        "student_tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_student_tags_name", "student_tags", ["name"], unique=True)
    op.create_table(
        "student_tag_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["assigned_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tag_id"], ["student_tags.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "tag_id", name="uq_student_tag_assignment"),
    )
    op.create_index(
        "ix_student_tag_assignments_user_id", "student_tag_assignments", ["user_id"]
    )
    op.create_index(
        "ix_student_tag_assignments_tag_id", "student_tag_assignments", ["tag_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_student_tag_assignments_tag_id", table_name="student_tag_assignments")
    op.drop_index("ix_student_tag_assignments_user_id", table_name="student_tag_assignments")
    op.drop_table("student_tag_assignments")
    op.drop_index("ix_student_tags_name", table_name="student_tags")
    op.drop_table("student_tags")
    op.drop_index("ix_student_notes_author_id", table_name="student_notes")
    op.drop_index("ix_student_notes_user_id", table_name="student_notes")
    op.drop_table("student_notes")
