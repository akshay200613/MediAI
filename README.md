# MedAI

**MedAI** is an intelligent clinic management system powered by AI. It features patient, doctor, and appointment management with a RAG-powered medical chatbot using Google Gemini.

## Architecture

```
medai/
├── apps/           # Deployable app surfaces (FastAPI, Next.js)
├── core/           # Platform core (auth, db, AI/RAG, schemas)
│   └── ai/         # Gemini LLM + RAG pipeline
├── domains/        # Domain logic
│   └── medai/      # MedAI – Clinic Management
└── infrastructure/ # Docker configs (dev)
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose

### Local Development

```bash
# 1. Clone the repo
git clone https://github.com/your-org/medai.git
cd medai

# 2. Setup (creates .env.local from template)
make setup

# 3. Edit your credentials
vim .env.local   # Add GOOGLE_API_KEY

# 4. Start infrastructure (PostgreSQL, Redis, Qdrant)
make docker-up

# 5. Run migrations
make migrate

# 6. Start the API
make dev

# 7. Start the frontend (new terminal)
make dev-frontend
```

### Access Points
| Service | URL |
|---|---|
| API (FastAPI) | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Frontend | http://localhost:3000 |

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 15, TypeScript, Tailwind CSS |
| **Backend** | FastAPI, Python 3.11 |
| **Database** | PostgreSQL (async SQLAlchemy) |
| **Cache/Sessions** | Redis |
| **Vector DB** | Qdrant |
| **AI** | Google Gemini 2.5 Flash, RAG Pipeline |
| **Migrations** | Alembic |

## API Reference

### Authentication
```
POST /api/v1/auth/register   – Register a new user
POST /api/v1/auth/login      – Login and get JWT tokens
POST /api/v1/auth/refresh    – Refresh access token
```

### Patients
```
GET    /api/v1/medai/patients          – List patients
POST   /api/v1/medai/patients          – Create patient
GET    /api/v1/medai/patients/{id}     – Get patient
PATCH  /api/v1/medai/patients/{id}     – Update patient
DELETE /api/v1/medai/patients/{id}     – Soft delete patient
```

### Doctors
```
GET    /api/v1/medai/doctors           – List doctors
POST   /api/v1/medai/doctors           – Create doctor
GET    /api/v1/medai/doctors/{id}      – Get doctor
PATCH  /api/v1/medai/doctors/{id}      – Update doctor
DELETE /api/v1/medai/doctors/{id}      – Soft delete doctor
```

### Appointments
```
GET    /api/v1/medai/appointments      – List appointments
POST   /api/v1/medai/appointments      – Create appointment
GET    /api/v1/medai/appointments/{id} – Get appointment
PATCH  /api/v1/medai/appointments/{id} – Update appointment
DELETE /api/v1/medai/appointments/{id} – Cancel appointment
```

### AI Chat
```
POST   /api/v1/medai/chat              – Chat with Medical AI (RAG-powered)
POST   /api/v1/medai/rag/upload        – Upload documents for RAG
POST   /api/v1/medai/rag/search        – Semantic search
```

### Health
```
GET /api/v1/health  – System health check (DB, Redis, Qdrant)
```

## Testing

```bash
make test           # All tests with coverage
make test-unit      # Unit tests only
```

## License

MIT
