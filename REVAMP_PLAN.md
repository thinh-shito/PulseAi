# PulseAI Code Revamp Plan

This document outlines the architectural plan to rename top-level directories, convert the backend from FastAPI (Python) to NestJS (TypeScript), convert the AI agent from Node.js (TypeScript) to FastAPI (Python), and update the AI API specifications.

---

## 1. Directory Structure Rename Suggestion

To keep the monorepo clean, organized, and standardized, we propose renaming the top-level folders as follows:

| Current Folder Path | Proposed Folder Path | Rationale |
|:---|:---|:---|
| `src-backend/` | `backend/` | Removes the redundant `src-` prefix, aligning with NestJS conventions and typical monorepo standards. |
| `src-frontend/` | `frontend/` | Removes the redundant `src-` prefix, matching `backend/` and keeping standard Next.js layouts. |
| `ai/agent/` | `ai-service/` | Flattens the agent folder, promoting it to a top-level workspace since it runs as an independent deployable service. |
| `ai/mcp-server/` | `mcp-server/` | Promotes the MCP server to the top level, separating tool execution logic from the AI orchestration agent loop. |

### Proposed Top-Level Monorepo Structure:
```
PulseAi/
├── backend/             # NestJS REST API (Language conversion: Python -> NestJS)
├── frontend/            # Next.js Web Application
├── ai-service/          # Python AI Orchestration & Runs API (Language conversion: Node.js -> Python)
├── mcp-server/          # FastMCP Tool Server (Python)
├── nginx/               # Reverse Proxy configurations
├── scripts/             # Seeding & deployment utility scripts
├── docker-compose.yml   # Multi-service composition
├── ARCHITECTURE.md      # System architecture docs
└── REVAMP_PLAN.md       # This revamp roadmap
```

---

## 2. Backend Language Conversion: Python (FastAPI) to TypeScript (NestJS)

We will convert the API and Domain-Driven Design (DDD) logic from FastAPI to **NestJS (v10+)** using **TypeORM** for PostgreSQL database interaction.

### DDD Directory Mapping
We will preserve the DDD layers from the Python codebase inside the NestJS modules directory structure:

```
backend/
├── src/
│   ├── main.ts                       # App bootstrap (FastAPI main.py equivalent)
│   ├── app.module.ts                 # Root NestJS module
│   ├── core/                         # Infrastructure/Global modules (Config, Database, Security)
│   │   ├── config/                   # ConfigModule using @nestjs/config
│   │   ├── database/                 # TypeORM DatabaseModule with Postgres Driver
│   │   └── security/                 # Hashing (bcrypt), JWT, RolesGuard, and requireRole decorator
│   ├── domain/                       # Pure Domain logic (Entities, Value Objects, de-identification interfaces)
│   │   ├── models/                   # TypeORM database models (User, PA Template, Workflow, AuditLog)
│   │   └── phi-filter/               # Ported PHIFilter logic using standard de-identification rules
│   ├── infra/                        # Repository implementations mapping to database engines
│   │   └── repositories/             # UserRepository, TemplateRepository, WorkflowRepository, AuditRepository
│   ├── modules/                      # Subdomain boundaries containing Controllers, Services, and Modules
│   │   ├── auth/                     # AuthController, AuthService, Local & JWT passport strategies
│   │   ├── user/                     # UserController, UserService
│   │   ├── workflow/                 # WorkflowController, WorkflowService
│   │   ├── admin/                    # AdminController, AdminService
│   │   ├── chat/                     # ChatController, ChatService
│   │   ├── presence/                 # PresenceController, PresenceService
│   │   └── templates/                # TemplatesController, TemplatesService
│   └── common/                       # Filters, interceptors, middleware, and common decorators
│       ├── decorators/               # custom @Roles() decorator
│       ├── interceptors/             # AuditInterceptor (to ensure append-only logs for state changes)
│       └── filters/                  # HttpExceptionFilter for HIPAA/standardized error responses
├── package.json                      # NestJS dependencies & scripts
├── tsconfig.json                     # Strict TypeScript configurations
└── nest-cli.json                     # NestJS CLI options
```

### Key Library Swaps
- **FastAPI / Uvicorn** $\rightarrow$ **NestJS / Express**
- **SQLAlchemy (asyncio)** $\rightarrow$ **TypeORM** (with `pg` driver) for clean, repository-based database actions.
- **Pydantic** $\rightarrow$ **class-validator / class-transformer** to achieve type safety and runtime validation of incoming request bodies.
- **python-jose** $\rightarrow$ **@nestjs/jwt / passport-jwt** for clinical JWT verification and authentication middleware.
- **Microsoft Presidio** $\rightarrow$ Native de-identification patterns or an external API wrapper to support `PHIFilter.anonymize()`.
- **Celery + Redis** $\rightarrow$ **@nestjs/bull** (BullMQ) for high-performance background queue management.

### Strictly Enforced NestJS Rules
1. **Dependency Injection**: No global service references or global DB connections. Everything is injected via constructor dependency injection.
2. **Layer Isolation**: Controllers (`api/`) must only delegate to Services. Entities must remain decoupled from NestJS routing concerns.
3. **PHI Logging Compliance**: No patient identities should be logged. The `AuditInterceptor` and Logger will enforce masking of PHI fields.
4. **Roles/Access Guards**: All endpoints except public health checks and `/auth/login` must be decorated with `@UseGuards(JwtAuthGuard, RolesGuard)` and `@Roles(...)`.
5. **Append-Only Audit Trail**: `AuditLog` table inserts must remain strictly append-only. Mutation/Deletion queries for the `AuditLog` entity are blocked at the repository level.

---

## 3. AI Service Language Conversion: Node.js (Express) to Python (FastAPI)

We will convert the AI service (previously Node.js Express agent) to a **FastAPI** Python application. 
To follow user specifications, the application package management will use `pyproject.toml` + `uv.lock` (managed via `uv`), and the server will run using `uvicorn`.

### Package Management (`pyproject.toml`)
```toml
[project]
name = "pulseai-ai-service"
version = "1.0.0"
description = "PulseAI AI Orchestration and Runs API"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.30.0",
    "openai>=4.52.7",
    "mcp>=1.0.0",               # Python MCP SDK (FastMCP integration)
    "asyncpg>=0.29.0",          # Postgres async driver
    "python-dotenv>=1.0.1",
    "sse-starlette>=2.1.0",     # Server-Sent Events for Python FastAPI
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",
]
```

### Folder Architecture (`ai-service/`)
```
ai-service/
├── main.py                     # Entrypoint & FastAPI initialization
├── pyproject.toml              # Project description & dependency management
├── uv.lock                     # Lockfile generated by uv
├── core/
│   ├── config.py               # Settings validation & env loading via Pydantic
│   └── database.py             # asyncpg connection pool initialization
├── api/
│   ├── v1/
│   │   ├── router.py           # V1 route registration
│   │   └── endpoints/
│   │       └── runs.py         # Endpoints for creating/continuing/retrieving runs
│   └── schemas/
│       └── runs.py             # Pydantic models for run requests/responses
├── services/
│   ├── run_manager.py          # State machine and run execution logic
│   ├── mcp_client.py           # Python FastMCP client wrapper to call mcp-server tools
│   └── file_export.py          # Base64 file export to PostgreSQL (exported_files)
└── agent/
    ├── loop.py                 # Core conversational agent loop (OpenAI assistant stream)
    └── system_prompt.py        # Prompts and configuration settings for the LLM
```

---

## 4. AI Runs API Documentation & Specifications

The AI Service exposes a **Runs API** designed to decouple client invocations from the long-running LLM and MCP tool executions.

### Endpoint 1: Create Run
*Initializes a new run context, saves the user message, and launches the background agent thread.*

- **Path:** `POST /v1/runs`
- **Request Body (`CreateRunRequest`):**
  ```json
  {
    "message": "Clinical note or user request content here...",
    "file_content": "SGVsbG8gd29ybGQ=", // Optional: base64 string of DOCX/PDF
    "file_name": "clinical_note.pdf",      // Optional: required if file_content is provided
    "session_id": "uuid-v4-session-id"     // Optional: creates new session if omitted
  }
  ```
- **Response Headers:**
  - `Set-Cookie: session_id=<session_id>; HttpOnly; SameSite=Lax; Max-Age=2592000`
- **Response Body (`RunResponse`):**
  ```json
  {
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "session_id": "uuid-v4-session-id",
    "conversation_id": "uuid-v4-conversation-id",
    "status": "running",
    "created_at": "2026-06-15T00:40:00Z"
  }
  ```

---

### Endpoint 2: Continue Elicitation
*Resumes a run that is paused (e.g. waiting on human feedback or clinical corrections).*

- **Path:** `POST /v1/runs/{run_id}/continue`
- **Request Body (`ContinueRunRequest`):**
  ```json
  {
    "message": "Here is the requested clinical correction..."
  }
  ```
- **Response Body (`RunResponse`):**
  ```json
  {
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "running",
    "updated_at": "2026-06-15T00:41:00Z"
  }
  ```

---

### Endpoint 3: Run Status
*Retrieves current status, errors, and output artifacts of the run.*

- **Path:** `GET /v1/runs/{run_id}`
- **Response Body (`RunStatusResponse`):**
  ```json
  {
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "session_id": "uuid-v4-session-id",
    "conversation_id": "uuid-v4-conversation-id",
    "status": "completed", // running | completed | failed | waiting_for_input
    "result": {
      "response": "Prior authorization form generated successfully.",
      "file_ready": {
        "file_id": "uuid-v4-file-id",
        "file_name": "filled_prior_auth.docx",
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
      }
    },
    "error": null,
    "created_at": "2026-06-15T00:40:00Z",
    "updated_at": "2026-06-15T00:42:00Z"
  }
  ```

---

### Endpoint 4: Stream Event Source (SSE)
*Establishes a Server-Sent Events (SSE) connection to stream incremental tokens, tool calls, and completion notifications in real-time.*

- **Path:** `GET /v1/runs/{run_id}/events`
- **Headers Required:**
  - `Accept: text/event-stream`
  - `Cache-Control: no-cache`
  - `Connection: keep-alive`
- **Streaming Events:**

  1. **Text Chunk Streaming (`text_delta`):**
     ```
     event: text_delta
     data: {"delta": "The patient note suggests "}
     ```

  2. **Tool Execution Start (`tool_use_start`):**
     ```
     event: tool_use_start
     data: {"name": "generate_prior_auth", "id": "call_abc123"}
     ```

  3. **Tool Execution End (`tool_result`):**
     ```
     event: tool_result
     data: {"name": "generate_prior_auth", "id": "call_abc123", "result": "Extracted prior auth data summary..."}
     ```

  4. **Generated File Ready (`file_ready`):**
     ```
     event: file_ready
     data: {"file_id": "uuid-v4", "file_name": "filled_prior_auth.docx", "mime_type": "application/vnd.openxmlformats..."}
     ```

  5. **Completion Notification (`done`):**
     ```
     event: done
     data: {}
     ```

---

## 5. UI Integration & Frontend Migration

Since the backend API transitions from FastAPI to NestJS and the AI API changes from `/api/chat` endpoints to the unified `/v1/runs` endpoints:

1. **API Endpoints Call Updates**:
   - Change chat requests in `src-frontend/components/ChatPanel.tsx` from `POST /api/chat` to `POST /v1/runs`.
   - Implement polling or active event-source listeners for `GET /v1/runs/{run_id}/events` to handle the stream.
   - Update file download links to target `/v1/runs/files/{file_id}` or the backend's respective files controller.

2. **Folder references**:
   - Reconfigure Dockerfiles and workspace setups inside `frontend/` to correctly access environment variables for the new NestJS backend.

---

## 6. Migration Roadmap & Checklist

- [ ] **Phase 1: Folder Refactoring**
  - Run Git move operations for directories.
  - Update `docker-compose.yml` to reflect new paths (`backend/`, `frontend/`, `ai-service/`, `mcp-server/`).
  - Update environment settings in Nginx configs and local env configurations.

- [ ] **Phase 2: NestJS Scaffolding**
  - Create the backend folder, initialize standard NestJS packages, setup tsconfig, lint, and database connection modules.

- [ ] **Phase 3: Porting REST APIs to NestJS**
  - Implement modules for Auth, User, Workflow, and AuditLogs sequentially.
  - Ensure all database schemas map to TypeORM and preserve strict HIPAA constraints.

- [ ] **Phase 4: Python AI Service Scaffolding**
  - Scaffold `ai-service/` using `pyproject.toml` and lock package versions using `uv lock`.

- [ ] **Phase 5: Porting the Agent Loop to Python**
  - Rewrite the Express.js agent loop in FastAPI.
  - Integrate Python FastMCP Client wrapper to communicate with the `mcp-server`.
  - Expose the 4 Runs API endpoints (`POST /v1/runs`, `POST /v1/runs/{run_id}/continue`, `GET /v1/runs/{run_id}`, `GET /v1/runs/{run_id}/events`).

- [ ] **Phase 6: Frontend/UI Alignment**
  - Adjust HTTP calls and Server-Sent Event clients in the React components to consume the Runs API.
  - Run integration tests validating end-to-end communication from the Frontend to NestJS, to the Python AI service, and through MCP tools.