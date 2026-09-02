"""
Seed Script for MediAI System Accounts.
Creates initial Admin, Doctor, and Patient accounts.
Run: python seed_admin.py
"""

import asyncio
from sqlalchemy import select
from core.database.session import AsyncSessionLocal
from core.models.user import User
from core.auth.jwt_handler import hash_password
from domains.medai.models.doctor import Doctor
from domains.medai.models.patient import Patient

async def seed_accounts():
    async with AsyncSessionLocal() as session:
        print("🌱 Seeding MediAI system accounts...")

        # 1. Admin Account (admin@gmail.com)
        admin_res = await session.execute(select(User).where((User.email == "admin@gmail.com") | (User.email == "admin@medai.com")))
        admin_users = admin_res.scalars().all()
        
        # Ensure admin@gmail.com exists with admin role
        gmail_admin = next((u for u in admin_users if u.email == "admin@gmail.com"), None)
        if not gmail_admin:
            gmail_admin = User(
                email="admin@gmail.com",
                hashed_password=hash_password("Admin@123"),
                full_name="MediAI System Admin",
                role="admin",
                domain="medai",
                is_active=True,
                is_verified=True,
            )
            session.add(gmail_admin)
            print("✅ Created Admin Account: admin@gmail.com / Admin@123")
        else:
            gmail_admin.role = "admin"
            gmail_admin.is_verified = True
            gmail_admin.hashed_password = hash_password("Admin@123")
            print("✅ Updated Admin Account: admin@gmail.com / Admin@123")

        # 2. Doctor Account
        doc_res = await session.execute(select(User).where(User.email == "doctor@gmail.com"))
        doc_user = doc_res.scalar_one_or_none()
        if not doc_user:
            doc_user = User(
                email="doctor@gmail.com",
                hashed_password=hash_password("Doctor123!"),
                full_name="Dr. Sarah Jenkins",
                role="doctor",
                domain="medai",
                is_active=True,
                is_verified=True,
            )
            session.add(doc_user)
            await session.flush()

            doctor_record = Doctor(
                user_id=str(doc_user.id),
                first_name="Sarah",
                last_name="Jenkins",
                email="doctor@gmail.com",
                phone="555-0182",
                specialty="Cardiology",
                license_number="LIC-MD-98425",
                years_of_experience=12,
                consultation_fee=150.0,
                is_available=True,
            )
            session.add(doctor_record)
            print("✅ Created Doctor Account: doctor@gmail.com / Doctor123!")
        else:
            doc_user.role = "doctor"
            doc_user.is_verified = True
            doc_user.hashed_password = hash_password("Doctor123!")
            print("✅ Reset Doctor Account password: doctor@gmail.com / Doctor123!")

        # 3. Patient Account
        pat_res = await session.execute(select(User).where(User.email == "patient@gmail.com"))
        pat_user = pat_res.scalar_one_or_none()
        if not pat_user:
            pat_user = User(
                email="patient@gmail.com",
                hashed_password=hash_password("Patient123!"),
                full_name="John Doe",
                role="patient",
                domain="medai",
                is_active=True,
                is_verified=True,
            )
            session.add(pat_user)
            await session.flush()

            patient_record = Patient(
                first_name="John",
                last_name="Doe",
                email="patient@gmail.com",
                phone="555-9012",
                blood_group="O+",
                allergies="Penicillin",
            )
            session.add(patient_record)
            print("✅ Created Patient Account: patient@gmail.com / Patient123!")
        else:
            pat_user.role = "patient"
            pat_user.is_verified = True
            pat_user.hashed_password = hash_password("Patient123!")
            print("✅ Reset Patient Account password: patient@gmail.com / Patient123!")

        await session.commit()
        print("🚀 Seeding completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed_accounts())
