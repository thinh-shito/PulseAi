import uuid
import datetime
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.api.deps import require_role
from app.core.database import get_db
from app.core.security import Role, hash_password
from app.domain.models.user import User
from app.domain.models.audit_log import AuditLog
from app.infra.repositories.user_repository import user_repo
from app.infra.repositories.audit_repository import audit_repo

router = APIRouter(prefix="/admin", tags=["Admin Operations"])

# ─── Pydantic Schemas ────────────────────────────────────────────────────────

class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str
    role: Role

class UserResponseSchema(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: Role
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class AuditLogResponseSchema(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    action: str
    patient_id: Optional[str] = None
    workflow_id: Optional[uuid.UUID] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/users", response_model=List[UserResponseSchema])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role(Role.ADMIN)),
):
    """Retrieve all system users (ADMIN only)."""
    return await user_repo.get_multi(db, skip=skip, limit=limit)

@router.post("/users", response_model=UserResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role(Role.ADMIN)),
):
    """Create a new hospital staff user (ADMIN only)."""
    existing = await user_repo.get_by_email(db, request.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    user_data = {
        "email": request.email,
        "hashed_password": hash_password(request.password),
        "full_name": request.full_name,
        "role": request.role,
        "is_active": True
    }
    return await user_repo.create(db, obj_in=user_data)

@router.get("/audit-logs", response_model=List[AuditLogResponseSchema])
async def list_audit_logs(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role(Role.ADMIN)),
):
    """List system audit logs for compliance tracking (ADMIN only)."""
    return await audit_repo.get_multi(db, skip=skip, limit=limit)
