# PulseAI — API Documentation

This document provides comprehensive API specifications for all endpoints across both the **Backend Service** (FastAPI → NestJS) and the **AI Service** (Node.js → Python FastAPI).

---

## Table of Contents

1. [Backend Service APIs](#backend-service-apis)
   - [Authentication](#authentication)
   - [Health Check](#health-check)
   - [Workflow Management](#workflow-management)
   - [Admin Operations](#admin-operations)
   - [Templates](#templates)
   - [Presence Tracking](#presence-tracking)
   - [Chat Assistant](#chat-assistant)
2. [AI Service APIs](#ai-service-apis)
   - [Runs API](#runs-api)
3. [Common Patterns](#common-patterns)
4. [Authentication & Authorization](#authentication--authorization)

---

## Backend Service APIs

Base URL: `http://localhost:8000/api/v1`

All endpoints except `/health` and `/auth/login` require JWT authentication via `Authorization: Bearer <token>` header.

---

### Authentication

#### POST `/auth/login`

**Description:** Authenticate user and return JWT token.

**Authentication:** None required

**Request Body:**
```json
{
  "email": "doctor@hospital.com",
  "password": "securePassword123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "doctor@hospital.com",
    "full_name": "Dr. Jane Smith",
    "role": "DOCTOR",
    "is_active": true
  }
}
```

**Error Responses:**
- `401 Unauthorized` — Invalid credentials
- `403 Forbidden` — Account inactive

---

#### POST `/auth/register`

**Description:** Register a new user account.

**Authentication:** None required

**Request Body:**
```json
{
  "email": "newdoctor@hospital.com",
  "password": "securePassword123",
  "full_name": "Dr. John Doe",
  "role": "DOCTOR"
}
```

**Response (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "email": "newdoctor@hospital.com",
  "full_name": "Dr. John Doe",
  "role": "DOCTOR",
  "is_active": true
}
```

**Error Responses:**
- `400 Bad Request` — Email already registered or validation error

---

#### GET `/auth/me`

**Description:** Get current authenticated user's profile.

**Authentication:** Required (any role)

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "doctor@hospital.com",
  "full_name": "Dr. Jane Smith",
  "role": "DOCTOR",
  "is_active": true
}
```

---

### Health Check

#### GET `/health`

**Description:** System health check endpoint.

**Authentication:** None required

**Response (200):**
```json
{
  "status": "healthy",
  "timestamp": "2026-06-15T00:40:00Z",
  "version": "1.0.0"
}
```

---

### Workflow Management

#### POST `/workflow`

**Description:** Create a new prior authorization workflow.

**Authentication:** Required (DOCTOR, ADMIN)

**Request Body:**
```json
{
  "patient_id": "P12345",
  "patient_name": "Jane Doe",
  "insurance_provider": "Blue Cross Blue Shield",
  "procedure_code": "CPT-62310",
  "diagnosis_code": "ICD10-M54.5",
  "clinical_notes": "Patient presents with chronic lower back pain...",
  "template_id": "550e8400-e29b-41d4-a716-446655440003"
}
```

**Response (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440010",
  "patient_id": "P12345",
  "patient_name": "Jane Doe",
  "insurance_provider": "Blue Cross Blue Shield",
  "procedure_code": "CPT-62310",
  "diagnosis_code": "ICD10-M54.5",
  "status": "DRAFT",
  "clinical_notes": "Patient presents with chronic lower back pain...",
  "template_id": "550e8400-e29b-41d4-a716-446655440003",
  "created_by": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-06-15T00:40:00Z",
  "updated_at": "2026-06-15T00:40:00Z"
}
```

**Error Responses:**
- `400 Bad Request` — Validation error
- `403 Forbidden` — Insufficient permissions

---

#### GET `/workflow`

**Description:** List workflows with pagination and filtering.

**Authentication:** Required (any role)

**Query Parameters:**
- `skip` (optional, default: 0) — Pagination offset
- `limit` (optional, default: 100) — Max results per page
- `status` (optional) — Filter by status (DRAFT, IN_REVIEW, APPROVED, REJECTED)
- `patient_id` (optional) — Filter by patient ID

**Response (200):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440010",
    "patient_id": "P12345",
    "patient_name": "Jane Doe",
    "status": "DRAFT",
    "created_at": "2026-06-15T00:40:00Z"
  }
]
```

---

#### GET `/workflow/{id}`

**Description:** Get detailed workflow information.

**Authentication:** Required (any role)

**Path Parameters:**
- `id` — Workflow UUID

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440010",
  "patient_id": "P12345",
  "patient_name": "Jane Doe",
  "insurance_provider": "Blue Cross Blue Shield",
  "procedure_code": "CPT-62310",
  "diagnosis_code": "ICD10-M54.5",
  "status": "DRAFT",
  "clinical_notes": "Patient presents with chronic lower back pain...",
  "template_id": "550e8400-e29b-41d4-a716-446655440003",
  "created_by": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-06-15T00:40:00Z",
  "updated_at": "2026-06-15T00:40:00Z"
}
```

**Error Responses:**
- `404 Not Found` — Workflow does not exist

---

#### PATCH `/workflow/{id}/status`

**Description:** Update workflow status (state transition).

**Authentication:** Required (DOCTOR, ADMIN)

**Path Parameters:**
- `id` — Workflow UUID

**Request Body:**
```json
{
  "status": "IN_REVIEW",
  "notes": "Submitted for insurance review"
}
```

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440010",
  "status": "IN_REVIEW",
  "updated_at": "2026-06-15T00:42:00Z"
}
```

**Error Responses:**
- `400 Bad Request` — Invalid status transition
- `403 Forbidden` — Insufficient permissions
- `404 Not Found` — Workflow does not exist

---

### Admin Operations

#### GET `/admin/users`

**Description:** List all system users (ADMIN only).

**Authentication:** Required (ADMIN)

**Query Parameters:**
- `skip` (optional, default: 0) — Pagination offset
- `limit` (optional, default: 100) — Max results per page

**Response (200):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "doctor@hospital.com",
    "full_name": "Dr. Jane Smith",
    "role": "DOCTOR",
    "is_active": true
  }
]
```

---

#### POST `/admin/users`

**Description:** Create a new hospital staff user (ADMIN only).

**Authentication:** Required (ADMIN)

**Request Body:**
```json
{
  "email": "newstaff@hospital.com",
  "password": "tempPassword123",
  "full_name": "New Staff Member",
  "role": "VIEWER"
}
```

**Response (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "email": "newstaff@hospital.com",
  "full_name": "New Staff Member",
  "role": "VIEWER",
  "is_active": true
}
```

**Error Responses:**
- `400 Bad Request` — Email already registered

---

#### GET `/admin/audit-logs`

**Description:** List system audit logs for compliance tracking (ADMIN only).

**Authentication:** Required (ADMIN)

**Query Parameters:**
- `skip` (optional, default: 0) — Pagination offset
- `limit` (optional, default: 100) — Max results per page

**Response (200):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440020",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "action": "CREATE_WORKFLOW",
    "patient_id": "P12345",
    "workflow_id": "550e8400-e29b-41d4-a716-446655440010",
    "resource_type": "workflow",
    "resource_id": "550e8400-e29b-41d4-a716-446655440010",
    "ip_address": "192.168.1.100",
    "created_at": "2026-06-15T00:40:00Z"
  }
]
```

**Notes:**
- Audit logs are append-only and cannot be deleted or modified
- All state-changing operations automatically create audit log entries

---

#### POST `/admin/templates`

**Description:** Upload a new PA template with form fields definition (ADMIN only).

**Authentication:** Required (ADMIN)

**Request Type:** `multipart/form-data`

**Form Fields:**
- `file` (required) — PDF file upload
- `schema_data` (required) — JSON string with template metadata

**Example `schema_data`:**
```json
{
  "name": "Blue Cross Spinal Injection PA Form",
  "fields": [
    {
      "name": "patient_name",
      "type": "text",
      "required": true,
      "label": "Patient Full Name"
    },
    {
      "name": "procedure_code",
      "type": "text",
      "required": true,
      "label": "CPT Code"
    }
  ]
}
```

**Response (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440030",
  "name": "Blue Cross Spinal Injection PA Form",
  "fields": [...],
  "is_active": true
}
```

**Error Responses:**
- `400 Bad Request` — Invalid JSON schema or empty file
- `400 Bad Request` — File must be PDF format

---

#### PATCH `/admin/templates/{id}`

**Description:** Toggle template active status or update name (ADMIN only).

**Authentication:** Required (ADMIN)

**Path Parameters:**
- `id` — Template UUID

**Request Body:**
```json
{
  "is_active": false,
  "name": "Updated Template Name"
}
```

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440030",
  "name": "Updated Template Name",
  "fields": [...],
  "is_active": false
}
```

**Error Responses:**
- `404 Not Found` — Template does not exist

---

### Templates

#### GET `/templates`

**Description:** List active PA templates (or all if user is ADMIN and `all=true`).

**Authentication:** Required (DOCTOR, ADMIN)

**Query Parameters:**
- `all` (optional, default: false) — Include inactive templates (ADMIN only)

**Response (200):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440030",
    "name": "Blue Cross Spinal Injection PA Form",
    "fields": [
      {
        "name": "patient_name",
        "type": "text",
        "required": true,
        "label": "Patient Full Name"
      }
    ],
    "is_active": true
  }
]
```

---

#### GET `/templates/{id}/download-blank`

**Description:** Download the blank template PDF file.

**Authentication:** Required (DOCTOR, ADMIN)

**Path Parameters:**
- `id` — Template UUID

**Response (200):**
- **Content-Type:** `application/pdf`
- **Content-Disposition:** `attachment; filename=blank_<template_name>.pdf`
- **Body:** Binary PDF file

**Error Responses:**
- `404 Not Found` — Template does not exist or is inactive
- `500 Internal Server Error` — Failed to decode template file

---

### Presence Tracking

#### POST `/presence/heartbeat`

**Description:** Mark current user as ONLINE. Frontend should call every 30 seconds.

**Authentication:** Required (any role)

**Response (200):**
```json
{
  "online": true,
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Presence updated"
}
```

**Notes:**
- Uses Redis SETBIT — O(1) operation
- TTL expires after 60 seconds of inactivity
- Call on: login, every 30s interval, tab focus/visibility change

---

#### DELETE `/presence/offline`

**Description:** Mark current user as OFFLINE immediately.

**Authentication:** Required (any role)

**Response (204):** No content

**Notes:**
- Call on: logout, browser close (beforeunload event)

---

#### GET `/presence/me`

**Description:** Get current user's own online status and last heartbeat time.

**Authentication:** Required (any role)

**Response (200):**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "online": true,
  "last_seen": "2026-06-15T00:42:30Z"
}
```

---

#### POST `/presence/users`

**Description:** Bulk query online status for multiple user UUIDs.

**Authentication:** Required (DOCTOR, ADMIN)

**Request Body:**
```json
{
  "user_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "550e8400-e29b-41d4-a716-446655440001"
  ]
}
```

**Response (200):**
```json
{
  "550e8400-e29b-41d4-a716-446655440000": true,
  "550e8400-e29b-41d4-a716-446655440001": false
}
```

**Notes:**
- VIEWERs can only query their own presence
- Uses Redis pipeline for single round-trip regardless of list size

---

#### GET `/presence/stats`

**Description:** Get total online user count and system statistics.

**Authentication:** Required (any role)

**Response (200):**
```json
{
  "online_users": 42,
  "total_registered": 1250,
  "bitmap_key": "presence:bitmap",
  "ttl_seconds": 60
}
```

**Notes:**
- Uses Redis BITCOUNT — O(n/8) complexity
- For 1 million users, bitmap is only 125 KB

---

#### GET `/presence/stream`

**Description:** Server-Sent Events stream for real-time online count updates.

**Authentication:** Required (any role)

**Query Parameters:**
- `interval` (optional, default: 10, min: 5, max: 60) — Poll interval in seconds

**Response Headers:**
- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`
- `X-Accel-Buffering: no`

**Event Stream Format:**
```
data: {"online_users": 42, "total_registered": 1250, "timestamp": "2026-06-15T00:42:00Z"}

data: {"online_users": 43, "total_registered": 1250, "timestamp": "2026-06-15T00:42:10Z"}
```

**Notes:**
- Client should use EventSource API to consume stream
- Connection remains open until client closes or disconnects

---

### Chat Assistant

#### POST `/chat`

**Description:** Send a message to the AI chat assistant for clinical guidance.

**Authentication:** Required (any role)

**Request Body:**
```json
{
  "message": "I need to create a prior authorization for a spinal injection",
  "workflow_id": "550e8400-e29b-41d4-a716-446655440010",
  "history": [
    {
      "role": "user",
      "content": "Previous message"
    },
    {
      "role": "assistant",
      "content": "Previous response"
    }
  ]
}
```

**Response (200):**
```json
{
  "reply": "I can help you create a prior authorization workflow. Would you like to proceed?",
  "action": "offer_create_workflow",
  "anonymized": "I need to create a prior authorization for a spinal injection"
}
```

**Validation Rules:**
- `message` cannot be empty
- `message` max 10,000 characters
- `message` max 1,000 words
- `history` roles must be "user" or "assistant"

**Actions (client behavior triggers):**
- `offer_create_workflow` — Detected clinical workflow trigger phrase
- `null` — Standard chat response

**Notes:**
- All messages are automatically anonymized via `PHIFilter.anonymize()` before AI processing
- Creates `CHAT_QUERY` audit log entry
- If `workflow_id` is invalid, returns "No matching workflow found" with 200 status

---

## AI Service APIs

Base URL: `http://localhost:3001/v1`

The AI Service provides a **Runs API** to decouple long-running AI agent loops from HTTP request/response cycles.

---

### Runs API

#### POST `/runs`

**Description:** Create a new run and initialize agent loop. Returns immediately; client connects to SSE for streaming.

**Authentication:** Session-based (cookie)

**Request Body:**
```json
{
  "message": "Generate a prior authorization form for Jane Doe with spinal injection CPT-62310",
  "file_content": "SGVsbG8gd29ybGQ=",
  "file_name": "clinical_note.pdf",
  "session_id": "550e8400-e29b-41d4-a716-446655440050"
}
```

**Field Details:**
- `message` (required) — User message or clinical note content
- `file_content` (optional) — Base64 encoded DOCX/PDF file
- `file_name` (optional) — Required if `file_content` is provided
- `session_id` (optional) — Creates new session if omitted

**Response (200):**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440100",
  "session_id": "550e8400-e29b-41d4-a716-446655440050",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440100",
  "status": "running",
  "created_at": "2026-06-15T00:40:00Z"
}
```

**Response Headers:**
- `Set-Cookie: session_id=<session_id>; HttpOnly; SameSite=Lax; Max-Age=2592000`

**Next Steps:**
1. Store `run_id` from response
2. Immediately connect to `GET /runs/{run_id}/events` for streaming updates

---

#### POST `/runs/{run_id}/continue`

**Description:** Resume a paused run with additional user input (e.g., clinical corrections).

**Authentication:** Session-based (cookie)

**Path Parameters:**
- `run_id` — Run UUID

**Request Body:**
```json
{
  "message": "The patient's procedure code should be CPT-62311, not CPT-62310"
}
```

**Response (200):**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440100",
  "session_id": "550e8400-e29b-41d4-a716-446655440050",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440100",
  "status": "running",
  "created_at": "2026-06-15T00:40:00Z",
  "updated_at": "2026-06-15T00:41:00Z"
}
```

**Error Responses:**
- `404 Not Found` — Run does not exist

---

#### GET `/runs/{run_id}`

**Description:** Get current status and result of a run (polling alternative to SSE).

**Authentication:** Session-based (cookie)

**Path Parameters:**
- `run_id` — Run UUID

**Response (200):**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440100",
  "session_id": "550e8400-e29b-41d4-a716-446655440050",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440100",
  "status": "completed",
  "result": {
    "response": "Prior authorization form generated successfully.",
    "file_ready": {
      "file_id": "550e8400-e29b-41d4-a716-446655440200",
      "file_name": "filled_prior_auth.docx",
      "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }
  },
  "error": null,
  "created_at": "2026-06-15T00:40:00Z",
  "updated_at": "2026-06-15T00:42:00Z"
}
```

**Status Values:**
- `running` — Agent loop actively processing
- `completed` — Run finished successfully
- `failed` — Error occurred during execution
- `waiting_for_input` — Paused, awaiting user response

**Error Responses:**
- `404 Not Found` — Run does not exist

---

#### GET `/runs/{run_id}/events`

**Description:** Server-Sent Events stream for real-time agent loop updates.

**Authentication:** Session-based (cookie)

**Path Parameters:**
- `run_id` — Run UUID

**Request Headers:**
- `Accept: text/event-stream`
- `Cache-Control: no-cache`
- `Connection: keep-alive`

**Event Types:**

1. **`text_delta`** — Streaming text chunks from LLM
   ```
   event: text_delta
   data: {"delta": "The patient note suggests "}
   ```

2. **`tool_use_start`** — Tool execution initiated
   ```
   event: tool_use_start
   data: {"name": "generate_prior_auth", "id": "call_abc123"}
   ```

3. **`tool_result`** — Tool execution completed
   ```
   event: tool_result
   data: {"name": "generate_prior_auth", "id": "call_abc123", "result": "Extracted prior auth data summary..."}
   ```

4. **`file_ready`** — Generated file available for download
   ```
   event: file_ready
   data: {"file_id": "550e8400-e29b-41d4-a716-446655440200", "file_name": "filled_prior_auth.docx", "mime_type": "application/vnd.openxmlformats..."}
   ```

5. **`done`** — Run completed
   ```
   event: done
   data: {}
   ```

**Error Responses:**
- `404 Not Found` — Run does not exist
- `400 Bad Request` — No user message found for this run

**Client Implementation Example (JavaScript):**
```javascript
const eventSource = new EventSource(`/v1/runs/${runId}/events`);

eventSource.addEventListener('text_delta', (e) => {
  const data = JSON.parse(e.data);
  appendText(data.delta);
});

eventSource.addEventListener('file_ready', (e) => {
  const data = JSON.parse(e.data);
  showDownloadButton(data.file_id, data.file_name);
});

eventSource.addEventListener('done', () => {
  eventSource.close();
});
```

---

#### GET `/runs/files/{file_id}`

**Description:** Download an exported file (DOCX/PDF) by ID.

**Authentication:** Session-based (cookie)

**Path Parameters:**
- `file_id` — File UUID

**Response (200):**
- **Content-Type:** `application/vnd.openxmlformats-officedocument.wordprocessingml.document` or `application/pdf`
- **Content-Disposition:** `attachment; filename="<file_name>"`
- **Body:** Binary file content

**Error Responses:**
- `404 Not Found` — File does not exist

---

## Common Patterns

### Error Response Format

All error responses follow this structure:

```json
{
  "detail": "Human-readable error message"
}
```

HTTP status codes:
- `400` — Bad Request (validation error, malformed input)
- `401` — Unauthorized (missing or invalid JWT)
- `403` — Forbidden (insufficient permissions)
- `404` — Not Found (resource does not exist)
- `500` — Internal Server Error (server-side failure)

---

### Pagination

Endpoints supporting pagination use `skip` and `limit` query parameters:

```
GET /api/v1/workflow?skip=0&limit=50
```

- `skip` (default: 0) — Number of records to skip
- `limit` (default: 100, max: 500) — Number of records to return

---

### Date/Time Format

All timestamps use ISO 8601 format with UTC timezone:

```
2026-06-15T00:40:00Z
```

---

## Authentication & Authorization

### JWT Token Structure

JWT tokens contain the following claims:

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "email": "doctor@hospital.com",
  "role": "DOCTOR",
  "exp": 1718409600
}
```

### Role Hierarchy

```
ADMIN > DOCTOR > VIEWER
```

**Permission Matrix:**

| Endpoint | ADMIN | DOCTOR | VIEWER |
|:---------|:-----:|:------:|:------:|
| `/auth/*` | ✓ | ✓ | ✓ |
| `/health` | ✓ | ✓ | ✓ |
| `/workflow` (read) | ✓ | ✓ | ✓ |
| `/workflow` (create/update) | ✓ | ✓ | ✗ |
| `/templates` (read) | ✓ | ✓ | ✗ |
| `/admin/*` | ✓ | ✗ | ✗ |
| `/presence/*` | ✓ | ✓ | ✓* |

*VIEWERs can only query their own presence in bulk queries.

### PHI (Protected Health Information) Compliance

**MANDATORY RULES:**
1. NEVER log patient names, phone numbers, or ID numbers
2. ALL text sent to Azure OpenAI MUST pass through `PHIFilter.anonymize()` first
3. Use `patient_id` (UUID) in all logs, never real patient identifiers
4. Audit logs are append-only — NO delete, NO update
5. All state-changing operations MUST write to `audit_logs` table

**Anonymization Example:**
```python
from app.domain.phi_filter import anonymize_phi

original = "Patient Jane Smith, DOB 03/15/1985, SSN 123-45-6789"
anonymized = anonymize_phi(original)
# Result: "Patient [PERSON], DOB [DATE], SSN [SSN]"
```

---

## Migration Notes

### Backend: FastAPI → NestJS

When converting to NestJS:
1. Replace Pydantic schemas with `class-validator` DTOs
2. Convert SQLAlchemy async to TypeORM repositories
3. Replace FastAPI dependencies with NestJS Guards and Interceptors
4. Preserve DDD layer isolation (domain, infra, api)

### AI Service: Node.js → Python

When converting to Python:
1. Use `pyproject.toml` + `uv.lock` for dependency management
2. Replace Express.js with FastAPI
3. Use `sse-starlette` for Server-Sent Events
4. Maintain the Runs API specification exactly as documented

---

**Document Version:** 1.0.0  
**Last Updated:** 2026-06-15  
**Maintained By:** PulseAI Engineering Team