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

    # 2. Data Reconciliation: Clean / provision orphaned references before enforcing foreign keys
    try:
        # A. Nullify invalid patient user_id references
        if 'medai_patients' in tables and 'users' in tables:
            conn.execute(sa.text("""
                UPDATE medai_patients
                SET user_id = NULL
                WHERE user_id IS NOT NULL
                  AND user_id NOT IN (SELECT id FROM users)
            """))

        # B. Re-link and provision users for doctors missing from users table
        if 'medai_doctors' in tables and 'users' in tables:
            if conn.dialect.name == "postgresql":
                conn.execute(sa.text("""
                    UPDATE medai_doctors d
                    SET user_id = u.id
                    FROM users u
                    WHERE d.email = u.email
                      AND d.user_id != u.id
                """))

            conn.execute(sa.text("""
                INSERT INTO users (
                    id, email, hashed_password, full_name, role, domain,
                    is_active, is_verified, created_at, updated_at, is_deleted
                )
                SELECT
                    d.user_id,
                    d.email,
                    '$2b$12$eX.placeholder.hash.medai.doctor.account.placeholder',
                    d.first_name || ' ' || d.last_name,
                    'doctor',
                    'medai',
                    true,
                    true,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP,
                    false
                FROM medai_doctors d
                WHERE d.user_id NOT IN (SELECT id FROM users)
                  AND d.email NOT IN (SELECT email FROM users)
            """))

            conn.execute(sa.text("""
                DELETE FROM medai_doctors
                WHERE user_id NOT IN (SELECT id FROM users)
            """))

        # C. Remove orphaned appointments referencing non-existent patients or doctors
        if 'medai_appointments' in tables:
            if 'medai_patients' in tables:
                conn.execute(sa.text("""
                    DELETE FROM medai_appointments
                    WHERE patient_id NOT IN (SELECT id FROM medai_patients)
                """))
            if 'medai_doctors' in tables:
                conn.execute(sa.text("""
                    DELETE FROM medai_appointments
                    WHERE doctor_id NOT IN (SELECT id FROM medai_doctors)
                """))
    except Exception as cleanup_err:
        pass

    # 3. Add Foreign Key constraints safely (with batch_alter_table for SQLite compatibility in tests)
    pat_fks = [fk.get('name') for fk in inspector.get_foreign_keys('medai_patients')] if 'medai_patients' in tables else []
    if 'fk_medai_patients_user_id_users' not in pat_fks:
        with op.batch_alter_table('medai_patients', schema=None) as batch_op:
            batch_op.create_foreign_key(
                'fk_medai_patients_user_id_users',
                'users',
                ['user_id'],
                ['id'],
                ondelete='SET NULL',
            )

    doc_fks = [fk.get('name') for fk in inspector.get_foreign_keys('medai_doctors')] if 'medai_doctors' in tables else []
    if 'fk_medai_doctors_user_id_users' not in doc_fks:
        with op.batch_alter_table('medai_doctors', schema=None) as batch_op:
            batch_op.create_foreign_key(
                'fk_medai_doctors_user_id_users',
                'users',
                ['user_id'],
                ['id'],
                ondelete='CASCADE',
            )

    appt_fks = [fk.get('name') for fk in inspector.get_foreign_keys('medai_appointments')] if 'medai_appointments' in tables else []
    appt_indexes = [idx.get('name') for idx in inspector.get_indexes('medai_appointments')] if 'medai_appointments' in tables else []

    with op.batch_alter_table('medai_appointments', schema=None) as batch_op:
        if 'fk_medai_appointments_patient_id_medai_patients' not in appt_fks:
            batch_op.create_foreign_key(
                'fk_medai_appointments_patient_id_medai_patients',
                'medai_patients',
                ['patient_id'],
                ['id'],
                ondelete='CASCADE',
            )
        if 'fk_medai_appointments_doctor_id_medai_doctors' not in appt_fks:
            batch_op.create_foreign_key(
                'fk_medai_appointments_doctor_id_medai_doctors',
                'medai_doctors',
                ['doctor_id'],
                ['id'],
                ondelete='CASCADE',
            )
        # Composite Indexes for high-performance scheduling queries
        if 'ix_medai_appointments_doctor_scheduled' not in appt_indexes:
            batch_op.create_index(
                'ix_medai_appointments_doctor_scheduled',
                ['doctor_id', 'scheduled_at', 'status'],
                unique=False,
            )
        if 'ix_medai_appointments_patient_status' not in appt_indexes:
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
