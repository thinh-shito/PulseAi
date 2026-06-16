# PulseAI — AI-Powered Prior Authorization Platform

An intelligent medical workflow automation system that streamlines prior authorization processes for hospitals using AI agents and document generation.

## 🏗️ Architecture

- **Backend:** NestJS (TypeScript) REST API with PostgreSQL + Redis
- **AI Service:** Python FastAPI with OpenAI GPT-4o integration
- **MCP Server:** FastMCP tool server for document processing
- **Frontend:** Next.js 14 (React + TypeScript)
- **Infrastructure:** Docker Compose orchestration

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for local development)
- Python 3.11+ (for local development)

### Environment Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/thinh-shito/PulseAi.git
   cd PulseAi
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Configure `.env` with your settings:**
   ```env
   # Database
   POSTGRES_USER=pulseai
   POSTGRES_PASSWORD=your_secure_password
   POSTGRES_DB=pulseai_db
   
   # Backend
   JWT_SECRET=your_jwt_secret_key
   
   # AI Service
   OPENAI_API_KEY=your_openai_api_key
   
   # Frontend
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXT_PUBLIC_AI_SERVICE_URL=http://localhost:3001
   ```

### Running the Application

#### Start All Services
```bash
docker-compose up -d
```

This will start:
- **Backend API** — http://localhost:8000
- **AI Service** — http://localhost:3001
- **MCP Server** — http://localhost:5000
- **Frontend** — http://localhost:3000
- **PostgreSQL** — (internal network only)
- **Redis** — (internal network only)

#### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f ai-service
docker-compose logs -f frontend
```

#### Stop All Services
```bash
docker-compose down
```

#### Stop and Remove Volumes (Clean Reset)
```bash
docker-compose down -v
```

#### Rebuild Services (After Code Changes)
```bash
docker-compose up -d --build
```

#### Rebuild Specific Service
```bash
docker-compose up -d --build backend
```

## 📡 API Endpoints

### Backend API (Port 8000)
- `GET /api/v1/health` — Health check
- `POST /api/v1/auth/login` — User authentication
- `POST /api/v1/auth/register` — User registration
- `GET /api/v1/auth/me` — Current user profile
- `POST /api/v1/workflow` — Create workflow
- `GET /api/v1/workflow` — List workflows
- `GET /api/v1/templates` — List PA templates
- `POST /api/v1/presence/heartbeat` — Update presence
- `GET /api/v1/admin/audit-logs` — Audit logs (ADMIN)

See [APIs.md](./APIs.md) for complete API documentation.

### AI Service (Port 3001)
- `POST /v1/runs` — Create new AI run
- `GET /v1/runs/{run_id}/events` — SSE stream for real-time updates
- `GET /v1/runs/{run_id}` — Get run status
- `POST /v1/runs/{run_id}/continue` — Continue paused run
- `GET /v1/runs/files/{file_id}` — Download generated file

## 🛠️ Development

### Backend Development (NestJS)

```bash
cd backend
npm install
npm run start:dev
```

**Note:** The NestJS backend is currently in migration. See [backend/NESTJS_MIGRATION_PLAN.md](./backend/NESTJS_MIGRATION_PLAN.md) for implementation status.

### AI Service Development (Python)

```bash
cd ai-service
pip install uv
uv pip install -r pyproject.toml
uvicorn main:app --reload --port 3001
```

### Frontend Development (Next.js)

```bash
cd frontend
npm install
npm run dev
```

## 📁 Project Structure

```
PulseAi/
├── backend/              # NestJS REST API (TypeScript)
│   ├── src/
│   │   ├── core/        # Config, database, security
│   │   ├── domain/      # Entities, business logic
│   │   ├── infra/       # Repositories, external clients
│   │   ├── modules/     # Feature modules (auth, workflow, etc.)
│   │   └── common/      # Shared decorators, guards, filters
│   ├── Dockerfile
│   └── package.json
│
├── ai-service/          # Python FastAPI AI orchestration
│   ├── agent/           # AI agent loop
│   ├── api/             # Runs API endpoints
│   ├── core/            # Config and database
│   ├── services/        # MCP client, file export
│   ├── Dockerfile
│   └── pyproject.toml
│
├── mcp-server/          # FastMCP tool server (Python)
│   ├── tools/           # Document generation tools
│   ├── utils/           # Document processors
│   └── Dockerfile
│
├── frontend/            # Next.js web application
│   ├── app/             # App router pages
│   ├── components/      # React components
│   └── Dockerfile
│
├── nginx/               # Reverse proxy (production)
├── scripts/             # Utility scripts
├── docker-compose.yml   # Development orchestration
├── docker-compose.prod.yml  # Production orchestration
└── APIs.md              # Complete API documentation
```

## 🔒 Security & Compliance

- **HIPAA Compliance:** PHI filtering and anonymization before AI processing
- **Audit Logging:** Append-only audit trail for all state-changing operations
- **Role-Based Access:** ADMIN > DOCTOR > VIEWER hierarchy
- **JWT Authentication:** Secure token-based auth with 24h expiration
- **Redis Presence:** Scalable online tracking with bitmap (O(1) operations)

## 🧪 Testing

### Backend Tests
```bash
cd backend
npm test                # Unit tests
npm run test:e2e        # E2E tests
npm run test:cov        # Coverage report
```

### AI Service Tests
```bash
cd ai-service
pytest                  # Run all tests
pytest -v              # Verbose output
pytest --cov           # Coverage report
```

## 📊 Database Migrations

### TypeORM Migrations (Backend)
```bash
cd backend
npm run migration:generate -- -n MigrationName
npm run migration:run
npm run migration:revert
```

## 🐳 Docker Commands Reference

| Command | Description |
|---------|-------------|
| `docker-compose up -d` | Start all services in detached mode |
| `docker-compose down` | Stop and remove containers |
| `docker-compose down -v` | Stop and remove containers + volumes (clean reset) |
| `docker-compose ps` | List running containers |
| `docker-compose logs -f [service]` | View logs (optional: specific service) |
| `docker-compose restart [service]` | Restart a service |
| `docker-compose up -d --build` | Rebuild and start all services |
| `docker-compose exec backend sh` | Access backend container shell |
| `docker-compose exec postgres psql -U pulseai` | Access PostgreSQL CLI |

## 📈 Monitoring & Health Checks

All services include health checks:

- **Backend:** `GET http://localhost:8000/api/v1/health`
- **PostgreSQL:** Automatic readiness check (`pg_isready`)
- **Redis:** Automatic ping check
- **AI Service:** Port 3001 availability

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 Documentation

- [API Documentation](./APIs.md) — Complete endpoint specifications
- [Architecture Guide](./ARCHITECTURE.md) — System design and data flow
- [NestJS Migration Plan](./backend/NESTJS_MIGRATION_PLAN.md) — Backend conversion roadmap
- [Migration Summary](./MIGRATION_SUMMARY.md) — Current migration status
- [Deployment Guide](./DEPLOYMENT_GUIDE.md) — Production deployment instructions

## 🔗 Links

- **Repository:** https://github.com/thinh-shito/PulseAi
- **Issues:** https://github.com/thinh-shito/PulseAi/issues

## 📄 License

This project is proprietary and confidential.

---

**Last Updated:** 2026-06-15  
**Version:** 1.0.0  
**Status:** Active Development