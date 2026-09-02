"""add_user_name_and_role_to_audit_logs

Revision ID: 6c120f943def
Revises: 5b991f832cde
Create Date: 2026-09-01 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c120f943def'
down_revision: Union[str, None] = '5b991f832cde'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'audit_logs' in tables:
        columns = [c['name'] for c in inspector.get_columns('audit_logs')]

        if 'user_name' not in columns:
            op.add_column('audit_logs', sa.Column('user_name', sa.String(length=255), nullable=True))
        if 'user_role' not in columns:
            op.add_column('audit_logs', sa.Column('user_role', sa.String(length=50), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'audit_logs' in tables:
        columns = [c['name'] for c in inspector.get_columns('audit_logs')]
        if 'user_role' in columns:
            op.drop_column('audit_logs', 'user_role')
        if 'user_name' in columns:
            op.drop_column('audit_logs', 'user_name')
