# How to Add a New Domain

This guide explains how to add a new business domain (e.g., HR, Legal, Retail) to AI ServiceOS without changing any core platform code.

## Overview

Each domain is a self-contained Python package under `domains/`. It registers itself into the core app via a `registry.py` file.

**Estimated time:** 2–4 hours for a basic domain with models, CRUD, and AI chat.

## Step-by-Step Guide

### Step 1: Create the domain directory

```
domains/
└── hr/
    ├── __init__.py
    ├── registry.py          ← REQUIRED
    ├── models/
    ├── schemas/
    ├── repositories/
    ├── services/
    ├── api/
    │   └── v1/
    │       ├── __init__.py
    │       └── router.py
    └── ai/
        ├── agents/
        └── mcp/
            └── tools/
```

### Step 2: Create `domains/hr/registry.py`

```python
from fastapi import FastAPI
from core.config.logging import get_logger

logger = get_logger("hr.registry")

def register(app: FastAPI) -> None:
    from domains.hr.api.v1.router import hr_v1_router
    from core.ai.mcp.tool_registry import tool_registry
    from domains.hr.ai.mcp.tools import employee_tool

    # Register routes
    app.include_router(hr_v1_router)

    # Register MCP tools
    tool_registry.register_all([
        employee_tool.get_employee_info,
        employee_tool.create_leave_request,
    ])

    logger.info("HR domain registered")
```

### Step 3: Register in `apps/api/main.py`

Add **one line** to `create_app()`:

```python
# Existing
from domains.medai.registry import register as register_medai

# Add this
from domains.hr.registry import register as register_hr

def create_app() -> FastAPI:
    ...
    register_medai(app)
    register_hr(app)   # ← Add this
    ...
```

That's it. Zero changes to core code. ✅

### Step 4: Define models

Inherit from `core.models.base_model.AuditableModel`:

```python
from core.models.base_model import AuditableModel
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String

class Employee(AuditableModel):
    __tablename__ = "hr_employees"

    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    department: Mapped[str] = mapped_column(String(100))
    position: Mapped[str] = mapped_column(String(100))
```

### Step 5: Create migrations

Register your models in `core/database/migrations/env.py`:

```python
from domains.hr.models import employee  # noqa: F401
```

Then generate migration:

```bash
make migrate-new name="add_hr_employees_table"
make migrate
```

### Step 6: Implement Repository + Service

```python
# domains/hr/repositories/employee_repository.py
from core.repositories.base_repository import BaseRepository
from domains.hr.models.employee import Employee

class EmployeeRepository(BaseRepository[Employee]):
    model = Employee
```

```python
# domains/hr/services/employee_service.py
class EmployeeService:
    def __init__(self, session: AsyncSession):
        self.repo = EmployeeRepository(session)

    async def create_employee(self, data: EmployeeCreate) -> EmployeeOut:
        employee = await self.repo.create(data.model_dump())
        return EmployeeOut.model_validate(employee)
```

### Step 7: Create domain AI Agent (optional)

```python
from core.ai.agents.base_agent import BaseAgent, AgentContext, AgentResponse

class HRAgent(BaseAgent):
    name = "hr_agent"
    system_prompt = "You are an HR assistant..."

    async def run(self, context: AgentContext) -> AgentResponse:
        response = await self.llm.generate(
            context.messages,
            system_prompt=self.system_prompt,
        )
        return AgentResponse(
            content=response.content,
            agent_name=self.name,
        )
```

### Step 8: Add MCP Tools (optional)

```python
# domains/hr/ai/mcp/tools/employee_tool.py

async def get_employee_info(employee_id: str) -> dict:
    """Get HR information for an employee."""
    return {"employee_id": employee_id, "status": "active"}

async def create_leave_request(employee_id: str, days: int, reason: str) -> dict:
    """Submit a leave request for an employee."""
    return {"success": True, "request_id": "leave-001"}
```

## Checklist

- [ ] Create `domains/hr/` directory structure
- [ ] Write `registry.py` with `register(app)` function
- [ ] Add one line in `apps/api/main.py`
- [ ] Define SQLAlchemy models (inherit `AuditableModel`)
- [ ] Register models in `migrations/env.py`
- [ ] Run `make migrate-new` and `make migrate`
- [ ] Implement repository (inherit `BaseRepository`)
- [ ] Implement service (business logic)
- [ ] Define Pydantic schemas (inherit `BaseSchema`)
- [ ] Create API routes
- [ ] Create domain AI agent (extends `BaseAgent`)
- [ ] Register MCP tools in `ToolRegistry`
- [ ] Write unit tests for services
- [ ] Write integration tests for API endpoints

## Domain Conventions

| Convention | Rule |
|---|---|
| Table prefix | Use domain name (e.g., `hr_employees`, `medai_patients`) |
| API prefix | `/api/v1/{domain}/` |
| Logger name | `{domain}.{module}` |
| Agent name | `{domain}_agent` |
| Collection name | `{settings.qdrant_collection_prefix}_{domain}_knowledge` |
