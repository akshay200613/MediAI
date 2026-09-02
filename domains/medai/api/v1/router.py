"""MedAI API v1 Router – updated with all endpoints."""
from fastapi import APIRouter
from domains.medai.api.v1.patients import router as patients_router
from domains.medai.api.v1.doctors import router as doctors_router
from domains.medai.api.v1.appointments import router as appointments_router
from domains.medai.api.v1.chat import router as chat_router
from domains.medai.api.v1.rag import router as rag_router
from domains.medai.api.v1.admin import router as admin_router
from domains.medai.api.v1.doctor_dashboard import router as doctor_dashboard_router
from domains.medai.api.v1.uploads import router as uploads_router
from domains.medai.websockets.router import router as ws_router
from core.config.constants import API_V1_PREFIX

medai_v1_router = APIRouter(prefix=f"{API_V1_PREFIX}/medai", tags=["MedAI"])
medai_v1_router.include_router(patients_router, prefix="/patients", tags=["Patients"])
medai_v1_router.include_router(doctors_router, prefix="/doctors", tags=["Doctors"])
medai_v1_router.include_router(appointments_router, prefix="/appointments", tags=["Appointments"])
medai_v1_router.include_router(chat_router, prefix="/chat", tags=["AI Chat"])
medai_v1_router.include_router(rag_router, prefix="/rag", tags=["RAG Knowledge Base"])
medai_v1_router.include_router(admin_router, prefix="/admin", tags=["Admin System"])
medai_v1_router.include_router(doctor_dashboard_router, prefix="/doctor-dashboard", tags=["Doctor Dashboard"])
medai_v1_router.include_router(uploads_router, prefix="/uploads", tags=["Uploads"])
medai_v1_router.include_router(ws_router, tags=["WebSockets"])


