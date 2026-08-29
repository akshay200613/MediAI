"""enforce_foreign_keys_and_indexes

Revision ID: 5b991f832cde
Revises: 4a880e721aef
Create Date: 2026-08-29 16:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5b991f832cde'
down_revision: Union[str, None] = '4a880e721aef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create chat history tables if they do not exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'medai_chat_sessions' not in tables:
        op.create_table(
            'medai_chat_sessions',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('title', sa.String(), nullable=False, server_default='New Consultation'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_medai_chat_sessions_id'), 'medai_chat_sessions', ['id'], unique=False)
        op.create_index(op.f('ix_medai_chat_sessions_user_id'), 'medai_chat_sessions', ['user_id'], unique=False)

    if 'medai_chat_messages' not in tables:
        op.create_table(
            'medai_chat_messages',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('session_id', sa.String(), nullable=False),
            sa.Column('role', sa.String(), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['session_id'], ['medai_chat_sessions.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_medai_chat_messages_id'), 'medai_chat_messages', ['id'], unique=False)
        op.create_index(op.f('ix_medai_chat_messages_session_id'), 'medai_chat_messages', ['session_id'], unique=False)

    # 2. Add Foreign Key constraints safely (with batch_alter_table for SQLite compatibility in tests)
    with op.batch_alter_table('medai_patients', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_medai_patients_user_id_users',
            'users',
            ['user_id'],
            ['id'],
            ondelete='SET NULL',
        )

    with op.batch_alter_table('medai_doctors', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_medai_doctors_user_id_users',
            'users',
            ['user_id'],
            ['id'],
            ondelete='CASCADE',
        )

    with op.batch_alter_table('medai_appointments', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_medai_appointments_patient_id_medai_patients',
            'medai_patients',
            ['patient_id'],
            ['id'],
            ondelete='CASCADE',
        )
        batch_op.create_foreign_key(
            'fk_medai_appointments_doctor_id_medai_doctors',
            'medai_doctors',
            ['doctor_id'],
            ['id'],
            ondelete='CASCADE',
        )
        # Composite Indexes for high-performance scheduling queries
        batch_op.create_index(
            'ix_medai_appointments_doctor_scheduled',
            ['doctor_id', 'scheduled_at', 'status'],
            unique=False,
        )
        batch_op.create_index(
            'ix_medai_appointments_patient_status',
            ['patient_id', 'status'],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table('medai_appointments', schema=None) as batch_op:
        batch_op.drop_index('ix_medai_appointments_patient_status')
        batch_op.drop_index('ix_medai_appointments_doctor_scheduled')
        batch_op.drop_constraint('fk_medai_appointments_doctor_id_medai_doctors', type_='foreignkey')
        batch_op.drop_constraint('fk_medai_appointments_patient_id_medai_patients', type_='foreignkey')

    with op.batch_alter_table('medai_doctors', schema=None) as batch_op:
        batch_op.drop_constraint('fk_medai_doctors_user_id_users', type_='foreignkey')

    with op.batch_alter_table('medai_patients', schema=None) as batch_op:
        batch_op.drop_constraint('fk_medai_patients_user_id_users', type_='foreignkey')

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'medai_chat_messages' in tables:
        op.drop_table('medai_chat_messages')
    if 'medai_chat_sessions' in tables:
        op.drop_table('medai_chat_sessions')
