# PulseAI — Architecture Documentation

## System Overview

PulseAI automates the Prior Authorization (PA) workflow for hospitals using multi-agent AI.
It serves two markets: **USA (HIPAA)** and **Vietnam (Thông tư 46/2018/TT-BYT)**.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 App Router (TypeScript) |
| Backend | FastAPI (Python 3.11+) |
| AI Orchestration | LangGraph |
| LLM | Azure OpenAI GPT-4o (Enterprise) |
| Database | PostgreSQL 16 (async via asyncpg) |
| Cache/Queue | Redis 7 + Celery |
| Observability | LangSmith |
| Migration | Alembic |
| Containerization | Docker + Docker Compose |

## DDD Layer Architecture

```
src-backend/app/
│
├── api/                          # Interface Layer
│   ├── deps.py                   # FastAPI dependencies (auth, db session)
│   └── v1/
│       ├── router.py             # Main v1 router
│       └── endpoints/
│           ├── auth.py           # POST /auth/login, /auth/logout
│           ├── health.py         # GET /health
│           ├── workflow.py       # POST /workflow/start, GET /workflow/{id}/stream
│           └── admin.py          # Admin-only endpoints
│
├── core/                         # Infrastructure Concerns
│   ├── config.py                 # Pydantic Settings (reads from .env)
│   ├── security.py               # JWT create/verify, password hashing, Role enum
│   └── database.py               # Async SQLAlchemy engine + session factory
│
├── domain/                       # Business Logic (Pure Python, NO framework)
│   ├── models/
│   │   ├── user.py               # User entity, Role, Session
│   │   ├── workflow.py           # Workflow entity, status states
│   │   ├── clinical_record.py    # ClinicalRecord entity
│   │   └── audit_log.py          # AuditLog entity (append-only)
│   └── phi_filter.py             # PHI de-identification (Microsoft Presidio)
│
├── infra/                        # External Adapters
│   ├── database/
│   │   └── session.py            # Async session factory
│   └── repositories/
│       ├── base_repository.py    # Generic CRUD base
│       ├── user_repository.py
│       ├── workflow_repository.py
│       └── audit_repository.py   # Append-only audit log writer
│
└── services_ai/                  # AI Orchestration Layer
    ├── state.py                  # AgentState TypedDict
    ├── nodes/
    │   ├── clinical_node.py      # ICD-10 extraction node
    │   ├── payer_router_node.py  # Insurance carrier router
    │   └── quality_node.py       # Quality scoring node
    ├── graph_builder.py          # LangGraph StateGraph assembly
    └── llm_factory.py            # Azure OpenAI / LLM factory
```

## Data Flow

```
Doctor uploads patient note
        ↓
POST /api/v1/workflow/start
        ↓
PHIFilter.anonymize(raw_text)       ← MANDATORY before any AI call
        ↓
Celery task enqueued (task_id returned)
        ↓
LangGraph: clinical_node → payer_router → [bcbs|aetna|bhyt_vn]_node
        ↓
quality_node (score 0-100)
        ↓
score < 95? → FREEZE (Human-in-the-Loop)
        ↓ POST /approve from Doctor
score ≥ 95? → submit_node → DOCX generated
        ↓
AuditLog written at every step
```

## Authentication Flow

```
POST /auth/login → JWT (access_token: 30min, refresh_token: 7d)
GET /api/v1/... → Bearer token → require_role(Role.DOCTOR) → allow/403
POST /auth/logout → JWT blacklisted in Redis
```

## Role Hierarchy

| Role | Can |
|---|---|
| ADMIN | All operations + manage users + view audit logs |
| DOCTOR | Start workflows + approve/reject PA + view own cases |
| VIEWER | Read-only: view reports, workflow statuses |

## Security Requirements

- PHI MUST be de-identified before leaving the hospital network
- TLS 1.3 required on all connections
- PostgreSQL data encrypted at rest (AES-256)
- Audit logs are immutable (append-only, no DELETE)
- Outbound firewall: only Azure OpenAI + LangSmith endpoints allowed
