# 🏥 MediAI — Autonomous Multi-Agent Clinic & Hospital Management Platform

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Next.js-15.1-black.svg?style=for-the-badge&logo=next.js&logoColor=white" alt="Next.js 15" />
  <img src="https://img.shields.io/badge/LangGraph-StateGraph-FF6F00.svg?style=for-the-badge&logo=langchain&logoColor=white" alt="LangGraph" />
  <img src="https://img.shields.io/badge/Google%20Gemini-2.0%20Flash-4285F4.svg?style=for-the-badge&logo=google&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/Qdrant-Vector%20DB-DC2626.svg?style=for-the-badge&logo=qdrant&logoColor=white" alt="Qdrant" />
  <img src="https://img.shields.io/badge/PostgreSQL-16%20Async-336791.svg?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Redis-7%20Alpine-DC382D.svg?style=for-the-badge&logo=redis&logoColor=white" alt="Redis" />
  <img src="https://img.shields.io/badge/Prometheus%20%26%20Grafana-Observability-F46800.svg?style=for-the-badge&logo=grafana&logoColor=white" alt="Grafana" />
  <img src="https://img.shields.io/badge/License-Source--Available%20%28View%20%26%20Contribute%29-9945FF.svg?style=for-the-badge" alt="License" />
</p>

---

## 📌 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Key Features](#-key-features)
- [AI Multi-Agent & RAG Engine](#-ai-multi-agent--rag-engine)
- [Tech Stack](#-tech-stack)
- [Directory Structure](#-directory-structure)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Quick Start (One-Command / PowerShell)](#quick-start-powershell)
  - [Manual Step-by-Step Setup](#manual-step-by-step-setup)
- [Default Seed Accounts & Demo Credentials](#-default-seed-accounts--demo-credentials)
- [API Reference](#-api-reference)
- [Monitoring & Observability](#-monitoring--observability)
- [Testing & Code Quality](#-testing--code-quality)
- [Environment Variables](#-environment-variables)
- [Contributing & Development Workflow](#-contributing--development-workflow)
- [License & Terms of Use](#-license--terms-of-use)

---

## 🌟 Overview

**MediAI** is an enterprise-grade, full-stack healthcare operations and clinical intelligence platform. Built with modern microservice-ready patterns, it unites **multi-agent AI orchestration**, **hybrid medical document retrieval (RAG)**, and **real-time clinic management** into a cohesive, high-performance ecosystem.

MediAI bridges clinical workflows and patient care:
- **Intelligent Triage & Scheduling**: Autonomous LangGraph multi-agent system managing patient onboarding, clinical inquiries, triage routing, and appointment lifecycle.
- **Hybrid RAG Knowledge System**: Fusion of dense vector embeddings (Qdrant) and sparse BM25 retrieval with Cross-Encoder reranking for verified clinical document discovery.
- **Role-Centric Portals**: Dedicated, responsive experiences for **Administrators**, **Doctors**, and **Patients** built on Next.js 15 App Router.
- **Real-Time Event Engine**: Live WebSocket channels delivering instant appointment updates, queue status changes, and background reminder alerts.
- **Full Observability**: Production monitoring with Prometheus metrics and pre-configured Grafana telemetry dashboards.

---

## 🏗️ System Architecture

```
                                  ┌─────────────────────────────────────────┐
                                  │      Next.js 15 Frontend (App Router)   │
                                  │   (Patient, Doctor & Admin Portals)     │
                                  └────────────────────┬────────────────────┘
                                                       │  REST / WebSocket
                                                       ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       FastAPI Backend Platform                                            │
│                                                                                                           │
│   ┌───────────────────────────┐     ┌──────────────────────────┐     ┌────────────────────────────────┐   │
│   │ Security & Middleware     │     │ Domain Services (MedAI)  │     │ Real-time Event Bus            │   │
│   │ - JWT Auth & RBAC         │     │ - Patients & Doctors     │     │ - WebSocket Manager            │   │
│   │ - Rate Limiting & CORS    │     │ - Appointments & Audits  │     │ - Automated Reminder Scheduler │   │
│   └─────────────┬─────────────┘     └────────────┬─────────────┘     └────────────────────────────────┘   │
│                 │                                │                                                        │
│                 ▼                                ▼                                                        │
│   ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                LangGraph Multi-Agent Orchestrator                                 │   │
│   │                                                                                                   │   │
│   │   [Reception Agent]  ──►  [Supervisor Agent]  ──┬──► [Medical / Triage Agent]                     │   │
│   │                                                 ├──► [Scheduling Agent (MCP Tools)]               │   │
│   │                                                 └──► [Knowledge Agent (Hybrid RAG)]               │   │
│   └───────────────────────────────────────────────────────────────────────────────────────────────────┘   │
└──────────────────┬───────────────────────────────┬───────────────────────────────┬────────────────────────┘
                   │                               │                               │
                   ▼                               ▼                               ▼
       ┌───────────────────────┐       ┌───────────────────────┐       ┌───────────────────────┐
       │      PostgreSQL       │       │        Redis 7        │       │        Qdrant         │
       │ (Async SQLAlchemy 2)  │       │ (Cache, Rate Limit,   │       │  (Dense Vector Index  │
       │ Relational Store      │       │  Session Blacklist)   │       │   for Clinical RAG)   │
       └───────────────────────┘       └───────────────────────┘       └───────────────────────┘
```

---

## ✨ Key Features

### 1. 🤖 LangGraph Multi-Agent System
- **Supervisor Agent**: Parses user intent and intelligently coordinates specialized sub-agents.
- **Reception Agent**: Welcomes patients, gathers preliminary details, and establishes session context.
- **Medical & Triage Agent**: Assesses reported symptoms, performs risk scoring, and recommends appropriate clinical steps.
- **Scheduling Agent**: Integrates with FastMCP database tools to query doctor availability, book appointments, reschedule, and handle cancellations in real time.
- **Knowledge Agent**: Connects to the RAG pipeline to answer patient and practitioner queries from authoritative clinic guidelines.

### 2. 📚 Advanced Hybrid RAG Engine
- **Dense Vector Search**: Powered by Qdrant with Google Gemini `text-embedding-001` or SentenceTransformers.
- **Sparse Lexical Search**: Rank-BM25 keyword retrieval for precise medical terminology and nomenclature.
- **Reciprocal Rank Fusion (RRF)**: Merges sparse and dense search results for balanced recall and precision.
- **Cross-Encoder Reranker**: Post-processes candidate chunks to prioritize the most semantically relevant clinical evidence.
- **Document Ingestion**: Automated ingestion and chunking for PDF, DOCX, and text guidelines.

### 3. 👥 Multi-Role Portals (Next.js 15)
- **Patient Portal**: Self-service appointment booking, upcoming schedule overview, past medical history, and 24/7 AI health assistant.
- **Doctor Portal**: Daily schedule timeline, patient consultation details, appointment status management (Confirmed, Completed, Cancelled).
- **Admin Dashboard**: System-wide analytics, doctor & patient directory administration, real-time platform metrics, and system audit logs.

### 4. ⚡ Real-Time WebSockets & Background Jobs
- **Live WebSocket Feed**: Bi-directional updates on `/api/v1/medai/ws/appointments` for instant UI synchronization across tabs and roles.
- **Automated Reminder Scheduler**: Async background worker sending proactive notifications for upcoming appointments.

### 5. 🛡️ Security & Enterprise Standards
- **Token-Based Authentication**: Access & Refresh JWT tokens with bcrypt password hashing and token invalidation.
- **Role-Based Access Control (RBAC)**: Strict permission boundaries enforcing `admin`, `doctor`, and `patient` access policies.
- **Hardened HTTP Stack**: Security headers (HSTS, CSP, XSS-Protection, Frame Options), IP-based rate limiting, and CORS protection.

---

## 🧠 AI Multi-Agent & RAG Engine

### Agent Graph Flow

```mermaid
graph TD
    Start([User Input]) --> Reception[Reception Node]
    Reception --> Supervisor[Supervisor Node]
    Supervisor -->|intent = medical| MedNode[Medical Node]
    Supervisor -->|intent = scheduling| SchedNode[Scheduling Node]
    Supervisor -->|intent = knowledge| KnowNode[Knowledge Node]
    Supervisor -->|general query| RespNode[Response Node]
    
    SchedNode -->|needs DB action| ToolNode[MCP Tool Node]
    ToolNode --> SchedNode
    
    KnowNode -->|query collection| RAG[Hybrid RAG Engine]
    RAG --> KnowNode
    
    MedNode --> RespNode
    SchedNode --> RespNode
    KnowNode --> RespNode
    RespNode --> End([Client Response])
```

### Model Routing & Resilience
MediAI uses **LiteLLM Router** with automatic fallback handling:
- **Primary LLM**: Google Gemini 2.0 Flash (`gemini/gemini-2.0-flash`)
- **Fallback LLM**: Groq / Llama 3.3 70B Versatile (`groq/llama-3.3-70b-versatile`)
- **Embeddings**: Gemini `text-embedding-001` / HuggingFace `all-MiniLM-L6-v2`

---

## 💻 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend Framework** | Next.js 15 (App Router), React 19, TypeScript | Server and client rendered interactive portals |
| **Styling & UI** | Tailwind CSS, Framer Motion, Lucide Icons | Responsive modern design system with glassmorphic accents |
| **State & Forms** | Zustand, React Hook Form, Zod | Global application state and validated client forms |
| **Backend API** | FastAPI, Python 3.11+, Uvicorn | High-throughput async REST and WebSocket server |
| **AI & Orchestration** | LangGraph, LangChain, LiteLLM, FastMCP | Multi-agent state machines, intent routing, and tool calling |
| **Vector Database** | Qdrant | Dense vector search and document index |
| **Relational Database** | PostgreSQL 16 (Async SQLAlchemy 2.0, Alembic) | ACID-compliant transactional persistence |
| **Cache & Sessions** | Redis 7 (Alpine) | Session storage, token blacklist, rate limit sliding windows |
| **Observability** | Prometheus, Grafana, Structlog, LangSmith | Real-time metric aggregation, system dashboards, and LLM tracing |
| **Testing & Quality** | Pytest, Vitest, Playwright, Ruff, Mypy | Full-suite unit, integration, E2E, and static analysis |

---

## 📁 Directory Structure

```
medai/
├── apps/
│   ├── api/                     # FastAPI application factory, lifespan, routes & middleware
│   └── frontend/                # Next.js 15 frontend application
│       ├── src/app/
│       │   ├── (auth)/          # Authentication pages (Login, Register)
│       │   ├── (dashboard)/     # Role-based dashboards (Admin, Doctor, Patient, AI Chat)
│       │   ├── layout.tsx       # Global root layout and providers
│       │   └── globals.css      # Core design tokens and styles
│       └── package.json
├── core/                        # Platform Core & Shared Infrastructure
│   ├── ai/                      # AI Layer: LangGraph multi-agent graph, LiteLLM client, RAG pipeline
│   │   ├── graph/               # Graph builder, nodes, edges, state & FastMCP tools
│   │   ├── llm/                 # LiteLLM router & provider fallbacks
│   │   └── rag/                 # Ingestion, BM25, Qdrant retrieval, RRF fusion & reranker
│   ├── auth/                    # JWT encoding/decoding, password hashing, OAuth2 dependencies
│   ├── config/                  # Pydantic Settings, environment configurations & structured logging
│   ├── database/                # Async SQLAlchemy engine, session factory, Redis & Qdrant clients
│   ├── metrics.py               # Prometheus metrics instrumentation
│   ├── middleware/              # Security headers & rate limiter middlewares
│   └── models/                  # Base models, User, and Audit Log SQLAlchemy models
├── domains/
│   └── medai/                   # MedAI Clinic Management Domain
│       ├── api/v1/              # Domain endpoints (Patients, Doctors, Appointments, Chat, RAG, Admin)
│       ├── models/              # Patient, Doctor, Appointment, and ChatHistory models
│       ├── repositories/        # Async database repositories
│       ├── services/            # Business logic and automated reminder scheduler
│       ├── websockets/          # WebSocket connection manager and real-time event router
│       └── registry.py          # Domain registration entrypoint
├── docker/                      # Custom Dockerfiles and database initialization scripts
├── monitoring/
│   ├── prometheus/              # Prometheus scrapers and alert configs
│   └── grafana/                 # Provisioned Grafana datasources and prebuilt dashboards
├── tests/                       # Automated test suites
│   ├── unit/                    # Unit tests for services, auth, tools, and routers
│   ├── integration/             # Integration tests for database and API endpoints
│   └── e2e/                     # End-to-end tests
├── docker-compose.yml           # Multi-service container definitions
├── Makefile                     # Developer command runner
├── pyproject.toml               # Python dependencies and tool configs
└── seed_admin.py                # Initial database seed script (Admin, Doctor, Patient)
```

---

##  Getting Started

### Prerequisites
Make sure the following tools are installed on your workstation:
- **Python**: `3.11` or higher
- **Node.js**: `20.x` or higher (with `npm`)
- **Docker** & **Docker Compose**
- **uv** (recommended) or `pip`

---

### Quick Start (PowerShell)

If you are on Windows, you can use the bundled automated startup script:

```powershell
# 1. Run the one-click startup script
.\start.ps1
```

---

### Manual Step-by-Step Setup

#### 1. Clone the Repository
```bash
git clone https://github.com/your-org/medai.git
cd medai
```

#### 2. Environment Configuration
```bash
# Copy template configuration
cp .env.example .env

# Edit .env and supply your Gemini API key (and optionally Groq / LangSmith keys)
# Windows PowerShell:
# Copy-Item .env.example .env
```

#### 3. Start Infrastructure Services (Docker)
Launch PostgreSQL, Redis, Qdrant, Prometheus, and Grafana:
```bash
docker compose up -d
```
Verify that all containers are healthy:
```bash
docker compose ps
```

#### 4. Backend Setup & Migrations
```bash
# Create and activate a Python virtual environment
python -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\Activate.ps1

# Install dependencies
pip install uv
uv sync --all-extras

# Run database migrations
alembic upgrade head

# Seed initial system accounts (Admin, Doctor, Patient)
python seed_admin.py
```

#### 5. Start the FastAPI Backend
```bash
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```
- **API Server**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Reference**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

#### 6. Start the Next.js Frontend
Open a new terminal window:
```bash
cd apps/frontend
npm install
npm run dev
```
- **Web Application**: [http://localhost:3000](http://localhost:3000)

---

##  Default Seed Accounts & Demo Credentials

When you run `python seed_admin.py`, the following demo accounts are created:

| Role | Email | Password | Access / Portal Capabilities |
|---|---|---|---|
|  **System Admin** | `admin@gmail.com` | `Admin@123` | Full administrative control, system metrics, user management, audit logs |
|  **Doctor** | `doctor@gmail.com` | `Doctor123!` | Doctor dashboard, schedule manager, patient consultation records |
|  **Patient** | `patient@gmail.com` | `Patient123!` | Appointment booking, medical timeline, 24/7 AI triage chatbot |

---


### 🔐 Authentication (`/api/v1/auth`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Register a new user account | No |
| `POST` | `/api/v1/auth/login` | Authenticate and obtain JWT access & refresh tokens | No |
| `POST` | `/api/v1/auth/refresh` | Refresh an expired access token | Yes (Refresh Token) |
| `GET` | `/api/v1/auth/me` | Retrieve currently authenticated user profile | Yes (Bearer Token) |

###  Clinic Management (`/api/v1/medai`)
| Method | Endpoint | Description | Roles |
|---|---|---|---|
| `GET` / `POST` | `/api/v1/medai/patients` | List patients / Register a patient | Admin, Doctor |
| `GET` / `PATCH` / `DELETE` | `/api/v1/medai/patients/{id}` | Manage specific patient record | Admin, Doctor |
| `GET` / `POST` | `/api/v1/medai/doctors` | List doctors / Add a doctor | All (List) / Admin |
| `GET` / `PATCH` / `DELETE` | `/api/v1/medai/doctors/{id}` | Manage doctor profile & availability | Admin, Doctor |
| `GET` / `POST` | `/api/v1/medai/appointments` | Query appointments / Book appointment | Patient, Doctor, Admin |
| `GET` / `PATCH` / `DELETE` | `/api/v1/medai/appointments/{id}` | View / Reschedule / Cancel appointment | Patient, Doctor, Admin |
| `GET` | `/api/v1/medai/doctor-dashboard/summary`| Doctor metrics, today's schedule & stats | Doctor |
| `GET` | `/api/v1/medai/admin/stats` | System analytics and clinic overview | Admin |

###  AI, RAG & Real-Time
| Method | Endpoint | Description | Details |
|---|---|---|---|
| `POST` | `/api/v1/medai/chat` | Chat with the Multi-Agent Assistant | LangGraph state graph routing |
| `POST` | `/api/v1/medai/rag/upload` | Upload clinical documents (PDF, DOCX) | Chunked and embedded into Qdrant |
| `POST` | `/api/v1/medai/rag/search` | Execute hybrid semantic & lexical search | BM25 + Qdrant + RRF Reranking |
| `WS` | `/api/v1/medai/ws/appointments` | Live WebSocket channel for appointment events | Token-authenticated connection |

### 🩺 Health & Observability
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Comprehensive health check (PostgreSQL, Redis, Qdrant status) |
| `GET` | `/metrics` | Prometheus metrics scrape endpoint |

---

## 📊 Monitoring & Observability

MediAI provides out-of-the-box telemetry and monitoring infrastructure:

```
┌─────────────────────────────────────────────────────────────┐
│                       Access Points                         │
├────────────────────────┬────────────────────────────────────┤
│ Prometheus             │ http://localhost:9090              │
│ Grafana                │ http://localhost:3001              │
│ Grafana Default Login  │ User: admin | Password: medai_admin│
└────────────────────────┴────────────────────────────────────┘
```

### Pre-configured Grafana Dashboards
- **MedAI Overview Dashboard**: Monitors HTTP request rates, latency (p50, p95, p99), error rates (4xx/5xx), active WebSocket connections, database connection pools, and AI token utilization.
- **LangSmith Tracing**: Set `LANGCHAIN_TRACING_V2=true` and provide `LANGCHAIN_API_KEY` to visualize multi-agent graph runs, node transitions, and tool calls in the LangSmith Cloud console.

---

##  Testing & Code Quality

MediAI maintains rigorous automated testing and static analysis standards.

### Backend Testing (Pytest)
```bash
# Run entire test suite with coverage report
make test

# Run unit tests only
make test-unit

# Run specific test modules
pytest tests/integration/test_auth_endpoints.py -v
pytest tests/test_retrieval.py -v
```

### Frontend Testing
```bash
cd apps/frontend

# Run unit and component tests (Vitest)
npm run test

# Run test coverage
npm run test:coverage

# Run End-to-End tests (Playwright)
npm run test:e2e
```

### Code Formatting & Type Checking
```bash
# Format Python code with Ruff
make format

# Lint Python codebase
make lint

# Run strict Mypy typechecks
make typecheck

# Frontend TypeScript and ESLint checks
cd apps/frontend && npm run lint && npm run type-check
```

---

## ⚙️ Environment Variables

Key environment variables configurable in `.env`:

| Category | Variable | Default | Description |
|---|---|---|---|
| **App** | `ENVIRONMENT` | `development` | Deployment environment (`development`, `staging`, `production`) |
| **App** | `API_PORT` | `8000` | FastAPI server port |
| **App** | `ALLOWED_ORIGINS` | `http://localhost:3000,...` | CORS allowed origins |
| **Database** | `DATABASE_URL` | `postgresql+asyncpg://...` | Async PostgreSQL connection string |
| **Cache** | `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| **Vector DB** | `QDRANT_HOST` / `PORT` | `localhost:6333` | Qdrant host and port |
| **Security** | `JWT_SECRET_KEY` | *(Secret)* | Secret key used for signing JWTs |
| **Security** | `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifespan |
| **AI Models** | `GEMINI_API_KEY` | *(Required)* | Google AI Gemini API Key |
| **AI Models** | `MODEL_SUPERVISOR` | `gemini/gemini-2.0-flash` | Primary supervisor model |
| **AI Fallback** | `GROQ_API_KEY` | *(Optional)* | Groq API Key for fallback routing |
| **RAG** | `RAG_CHUNK_SIZE` | `512` | Token chunk size for document splitting |
| **RAG** | `RAG_TOP_K` | `5` | Candidate documents retrieved per search |
| **Tracing** | `LANGCHAIN_TRACING_V2` | `false` | Enable LangSmith tracing |

---

## 🤝 Contributing & Development Workflow

1. **Fork the repository** and create a feature branch:
   ```bash
   git checkout -b feature/amazing-feature
   ```
2. **Commit your changes** following conventional commit standards:
   ```bash
   git commit -m "feat(ai): add multi-modal triage analysis node"
   ```
3. **Ensure all checks pass**:
   ```bash
   make check
   make test
   ```
4. **Open a Pull Request** against the `main` branch.

---

## 📄 License & Terms of Use

Copyright (c) 2026 MediAI Contributors & Authors. All Rights Reserved.

This project is licensed under a **Source-Available (View & Contribute Only)** model:
- ✅ **Viewing & Evaluating**: You are welcome to view, study, and test the source code.
- ✅ **Contributing**: You are welcome to submit issues, discussions, and pull requests directly to this repository.
- ❌ **No External Reuse / Redistribution**: You **may not** copy, replicate, modify, or reuse this codebase (or any portion of it) in other commercial or open-source projects, products, or repositories without explicit prior written permission from the copyright holders.

For complete terms and conditions, please refer to the [LICENSE](LICENSE) file.

<p align="center">
  <sub>Built with ❤️ by the MediAI Engineering Team. Empowering clinicians and patients through intelligent automation.</sub>
</p>
