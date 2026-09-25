"""add normalized RBAC and immutable audit log

Revision ID: a1f2b3c4d5e6
Revises: 9e1f2a3b4c5d
Create Date: 2026-08-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1f2b3c4d5e6"
down_revision: Union[str, None] = "9e1f2a3b4c5d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=True)
    op.create_table(
        "permissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_permissions_name", "permissions", ["name"], unique=True)
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("permission_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )
    op.create_table(
        "user_role_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_role_assignment"),
    )
    op.create_index("ix_user_role_assignments_user_id", "user_role_assignments", ["user_id"])
    op.create_index("ix_user_role_assignments_role_id", "user_role_assignments", ["role_id"])
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("object_type", sa.String(100), nullable=False),
        sa.Column("object_id", sa.String(255), nullable=True),
        sa.Column("old_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("actor_user_id", "action", "object_type", "object_id", "correlation_id", "created_at"):
        op.create_index(f"ix_audit_logs_{column}", "audit_logs", [column])

    op.execute(
        """
        INSERT INTO permissions (id, name, description) VALUES
        ('01000000-0000-0000-0000-000000000001', 'system.manage_roles', 'Manage team roles'),
        ('01000000-0000-0000-0000-000000000002', 'users.read', 'Read student profiles'),
        ('01000000-0000-0000-0000-000000000003', 'users.manage', 'Manage student profiles'),
        ('01000000-0000-0000-0000-000000000004', 'access.manage', 'Grant and revoke course access'),
        ('01000000-0000-0000-0000-000000000005', 'commerce.read', 'Read orders and payments'),
        ('01000000-0000-0000-0000-000000000006', 'refunds.manage', 'Manage refunds'),
        ('01000000-0000-0000-0000-000000000007', 'content.manage', 'Manage courses and landing'),
        ('01000000-0000-0000-0000-000000000008', 'analytics.read', 'Read analytics'),
        ('01000000-0000-0000-0000-000000000009', 'notifications.manage', 'Manage notifications'),
        ('01000000-0000-0000-0000-000000000010', 'audit.read', 'Read audit and system status'),
        ('01000000-0000-0000-0000-000000000011', 'certificates.manage', 'Manage certificates')
        """
    )
    op.execute(
        """
        INSERT INTO roles (id, name, description, is_system, created_at) VALUES
        ('02000000-0000-0000-0000-000000000001', 'owner', 'Platform owner', true, now()),
        ('02000000-0000-0000-0000-000000000002', 'admin', 'Operations administrator', true, now()),
        ('02000000-0000-0000-0000-000000000003', 'content_manager', 'Course content manager', true, now()),
        ('02000000-0000-0000-0000-000000000004', 'curator', 'Student curator', true, now()),
        ('02000000-0000-0000-0000-000000000005', 'analyst', 'Read-only analyst', true, now())
        """
    )
    role_permission_queries = (
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT '02000000-0000-0000-0000-000000000001'::uuid, id FROM permissions
        """,
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT '02000000-0000-0000-0000-000000000002'::uuid, id FROM permissions
        WHERE name <> 'system.manage_roles'
        """,
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT '02000000-0000-0000-0000-000000000003'::uuid, id FROM permissions
        WHERE name = 'content.manage'
        """,
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT '02000000-0000-0000-0000-000000000004'::uuid, id FROM permissions
        WHERE name IN ('users.read', 'access.manage', 'notifications.manage', 'certificates.manage')
        """,
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT '02000000-0000-0000-0000-000000000005'::uuid, id FROM permissions
        WHERE name IN ('analytics.read', 'commerce.read', 'audit.read')
        """,
    )
    for query in role_permission_queries:
        op.execute(query)
    op.execute(
        """
        INSERT INTO user_role_assignments (id, user_id, role_id, assigned_by_id, created_at)
        SELECT gen_random_uuid(), id, '02000000-0000-0000-0000-000000000001', NULL, now()
        FROM users WHERE role = 'admin'
        ON CONFLICT (user_id, role_id) DO NOTHING
        """
    )
    op.execute(
        """
        CREATE FUNCTION prevent_audit_log_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_logs_immutable
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_logs_immutable ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_log_mutation()")
    for column in reversed(("actor_user_id", "action", "object_type", "object_id", "correlation_id", "created_at")):
        op.drop_index(f"ix_audit_logs_{column}", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_user_role_assignments_role_id", table_name="user_role_assignments")
    op.drop_index("ix_user_role_assignments_user_id", table_name="user_role_assignments")
    op.drop_table("user_role_assignments")
    op.drop_table("role_permissions")
    op.drop_index("ix_permissions_name", table_name="permissions")
    op.drop_table("permissions")
    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_table("roles")
