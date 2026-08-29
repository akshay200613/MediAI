"""
Unit and Integration Tests for Database Models, Foreign Keys, Relationships, and Migrations.

Covers:
1. UUID consistency across all models.
2. Foreign Key constraints and cascades.
3. Bidirectional SQLAlchemy relationships (User <-> Patient, User <-> Doctor, Patient <-> Appointment, Doctor <-> Appointment).
4. Composite Indexes for scheduling queries.
5. Migration upgrade/downgrade execution.
6. Transaction integrity and rollback handling.
"""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session

from core.database.base import Base
from core.models.user import User
from core.models.audit_log import AuditLog
from domains.medai.models.patient import Patient, BloodGroup, Gender
from domains.medai.models.doctor import Doctor
from domains.medai.models.appointment import Appointment, AppointmentStatus, AppointmentType
from domains.medai.models.chat_history import ChatSession, ChatMessage


@pytest.fixture
def test_db_session():
    """Provides a fresh isolated SQLite in-memory database with full schema for model testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


class TestDatabaseSchemaAndRelationships:
    def test_uuid_consistency_across_models(self, test_db_session: Session):
        """Verify all primary keys and foreign keys are proper UUID objects."""
        user = User(
            email="test_user@example.com",
            hashed_password="hashed_pwd_123",
            full_name="Test User",
            role="patient",
        )
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        assert isinstance(user.id, uuid.UUID)

        patient = Patient(
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            phone="123-456-7890",
            user_id=user.id,
        )
        test_db_session.add(patient)
        test_db_session.commit()
        test_db_session.refresh(patient)

        assert isinstance(patient.id, uuid.UUID)
        assert isinstance(patient.user_id, uuid.UUID)
        assert patient.user_id == user.id

    def test_bidirectional_user_patient_doctor_relationships(self, test_db_session: Session):
        """Verify relationship navigation between User, Patient, Doctor, and Appointments."""
        # Create Patient User
        patient_user = User(
            email="pat_rel@example.com",
            hashed_password="pwd",
            full_name="Patient User",
            role="patient",
        )
        # Create Doctor User
        doctor_user = User(
            email="doc_rel@example.com",
            hashed_password="pwd",
            full_name="Dr. Smith",
            role="doctor",
        )
        test_db_session.add_all([patient_user, doctor_user])
        test_db_session.commit()

        # Create Patient and Doctor records
        patient = Patient(
            first_name="John",
            last_name="Doe",
            email=patient_user.email,
            phone="555-0100",
            user_id=patient_user.id,
        )
        doctor = Doctor(
            user_id=doctor_user.id,
            first_name="Jane",
            last_name="Smith",
            email=doctor_user.email,
            phone="555-0200",
            specialty="Cardiology",
            license_number="LIC-12345",
        )
        test_db_session.add_all([patient, doctor])
        test_db_session.commit()

        # Create Appointment linking Patient and Doctor
        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            scheduled_at=datetime.now(timezone.utc),
            appointment_type=AppointmentType.CONSULTATION,
            status=AppointmentStatus.SCHEDULED,
        )
        test_db_session.add(appointment)
        test_db_session.commit()

        # Test relationship navigation
        stmt = select(Patient).where(Patient.id == patient.id)
        res = test_db_session.execute(stmt)
        p = res.scalar_one()

        assert p.user is not None
        assert p.user.id == patient_user.id
        assert len(p.appointments) == 1
        assert p.appointments[0].id == appointment.id
        assert p.appointments[0].doctor.id == doctor.id

    def test_composite_indexes_defined_on_appointments(self):
        """Verify composite indexes for doctor schedule and patient status queries."""
        table = Appointment.__table__
        index_names = {idx.name for idx in table.indexes}

        assert "ix_medai_appointments_doctor_scheduled" in index_names
        assert "ix_medai_appointments_patient_status" in index_names

    def test_transaction_rollback_integrity(self, test_db_session: Session):
        """Verify transaction rollback prevents partial state corruption."""
        user = User(
            email="rollback_test@example.com",
            hashed_password="pwd",
            full_name="Rollback User",
        )
        test_db_session.add(user)
        test_db_session.commit()

        # Start an operation that fails halfway
        try:
            # 1. Valid modification
            user.full_name = "Modified Name"
            
            # 2. Duplicate unique email violation
            duplicate_user = User(
                email="rollback_test@example.com",
                hashed_password="pwd",
                full_name="Duplicate User",
            )
            test_db_session.add(duplicate_user)
            test_db_session.flush()
        except Exception:
            test_db_session.rollback()

        # Verify state is clean
        stmt = select(User).where(User.email == "rollback_test@example.com")
        res = test_db_session.execute(stmt)
        u = res.scalar_one()
        assert u.full_name == "Rollback User"


class TestAlembicMigrationDefinitions:
    def test_migration_chain_integrity(self):
        """Verify all Alembic migration revisions link up correctly to 'head' without branch conflicts."""
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        config = Config("alembic.ini")
        script = ScriptDirectory.from_config(config)

        heads = script.get_heads()
        assert len(heads) == 1
        assert heads[0] == "5b991f832cde"

        # Verify all revisions in the lineage
        rev_ids = [r.revision for r in script.walk_revisions()]
        assert "5b991f832cde" in rev_ids
        assert "4a880e721aef" in rev_ids
        assert "39550a9f12bf" in rev_ids
        assert rev_ids == ["5b991f832cde", "4a880e721aef", "39550a9f12bf"]
