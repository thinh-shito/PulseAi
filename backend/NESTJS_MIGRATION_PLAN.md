# NestJS Migration Implementation Plan

## Current Status
- ✅ `package.json` configured with all dependencies
- ✅ `tsconfig.json` configured with strict TypeScript settings
- ✅ Core config files: `database.config.ts`, `jwt.config.ts`, `redis.config.ts`
- ✅ DatabaseModule created

## Remaining Implementation

### 1. Core Layer (`src/core/`)

**Security** (`src/core/security/`)
- `hashing.service.ts` — bcrypt password hashing
- `jwt.strategy.ts` — JWT passport strategy
- `local.strategy.ts` — Local authentication strategy
- `roles.guard.ts` — Role-based access control guard

### 2. Domain Layer (`src/domain/`)

**Models** (`src/domain/models/`)
- `user.entity.ts` — User TypeORM entity
- `workflow.entity.ts` — Workflow TypeORM entity
- `audit-log.entity.ts` — AuditLog TypeORM entity
- `pa-template.entity.ts` — PATemplate TypeORM entity

**PHI Filter** (`src/domain/phi-filter/`)
- `phi-filter.service.ts` — PHI anonymization logic

### 3. Infrastructure Layer (`src/infra/`)

**Repositories** (`src/infra/repositories/`)
- `user.repository.ts`
- `workflow.repository.ts`
- `audit.repository.ts`
- `template.repository.ts`

**External Clients** (`src/infra/`)
- `ai-client.service.ts` — HTTP client for AI service communication

### 4. Feature Modules (`src/modules/`)

**Auth Module** (`src/modules/auth/`)
- `auth.module.ts`
- `auth.controller.ts`
- `auth.service.ts`
- `dto/login.dto.ts`, `dto/register.dto.ts`, `dto/token-response.dto.ts`

**User Module** (`src/modules/user/`)
- `user.module.ts`
- `user.controller.ts`
- `user.service.ts`

**Workflow Module** (`src/modules/workflow/`)
- `workflow.module.ts`
- `workflow.controller.ts`
- `workflow.service.ts`
- DTOs for create, update, status change

**Admin Module** (`src/modules/admin/`)
- `admin.module.ts`
- `admin.controller.ts`
- `admin.service.ts`
- DTOs for user creation, audit queries

**Chat Module** (`src/modules/chat/`)
- `chat.module.ts`
- `chat.controller.ts`
- `chat.service.ts`
- DTOs for chat requests/responses

**Presence Module** (`src/modules/presence/`)
- `presence.module.ts`
- `presence.controller.ts`
- `presence.service.ts`
- Redis integration for bitmap tracking

**Templates Module** (`src/modules/templates/`)
- `templates.module.ts`
- `templates.controller.ts`
- `templates.service.ts`
- DTOs for template operations

### 5. Common Layer (`src/common/`)

**Decorators** (`src/common/decorators/`)
- `roles.decorator.ts` — `@Roles()` decorator
- `current-user.decorator.ts` — `@CurrentUser()` decorator

**Guards** (`src/common/guards/`)
- `jwt-auth.guard.ts`
- `roles.guard.ts`

**Interceptors** (`src/common/interceptors/`)
- `audit.interceptor.ts` — Automatic audit log creation

**Filters** (`src/common/filters/`)
- `http-exception.filter.ts` — HIPAA-compliant error formatting

### 6. Root Module Updates

**`src/app.module.ts`** — Wire all modules together:
```typescript
@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true, load: [databaseConfig, jwtConfig, redisConfig] }),
    DatabaseModule,
    AuthModule,
    UserModule,
    WorkflowModule,
    AdminModule,
    ChatModule,
    PresenceModule,
    TemplatesModule,
  ],
})
export class AppModule {}
```

## Installation Command

After all files are created, run:
```bash
cd backend && npm install
```

## Files to Delete (Phase 2)

### Python Backend Code
- `backend/app/` (entire directory)
- `backend/alembic/` (entire directory)  
- `backend/tests/` (entire directory)
- `backend/requirements.txt`
- `backend/pytest.ini`
- `backend/alembic.ini`

### Python Dockerfiles
- `backend/Dockerfile` (replace with Node.js version)
- `backend/Dockerfile.prod` (replace with Node.js version)

## AI Service Cleanup (Phase 3)

### Remove TypeScript Remnants
- `ai-service/src/` (entire directory)
- `ai-service/package.json`
- `ai-service/package-lock.json`
- `ai-service/tsconfig.json`

## Next Steps

1. Complete all TypeScript file creation (~35 remaining files)
2. Run `npm install` in backend directory
3. Delete all Python files from backend
4. Delete TypeScript files from ai-service
5. Update Dockerfiles for both services
6. Update docker-compose.yml
7. Test the new NestJS backend