"""add_email_reminder_columns

Revision ID: 4a880e721aef
Revises: 39550a9f12bf
Create Date: 2026-08-27 22:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a880e721aef'
down_revision: Union[str, None] = '39550a9f12bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('medai_appointments', sa.Column('confirmation_email_sent', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('medai_appointments', sa.Column('reminder_email_sent', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('medai_appointments', sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_medai_appointments_reminder_email_sent'), 'medai_appointments', ['reminder_email_sent'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_medai_appointments_reminder_email_sent'), table_name='medai_appointments')
    op.drop_column('medai_appointments', 'reminder_sent_at')
    op.drop_column('medai_appointments', 'reminder_email_sent')
    op.drop_column('medai_appointments', 'confirmation_email_sent')
