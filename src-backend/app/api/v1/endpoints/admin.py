import uuid
import datetime
import json
import base64
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.api.deps import require_role
from app.core.database import get_db
from app.core.security import Role, hash_password
from app.domain.models.user import User
from app.domain.models.audit_log import AuditLog
from app.domain.models.pa_templates import PATemplate
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


class TemplatePatchRequest(BaseModel):
    is_active: Optional[bool] = None
    name: Optional[str] = None


class TemplateAdminResponseSchema(BaseModel):
    id: uuid.UUID
    name: str
    fields: list
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


@router.post("/templates", response_model=TemplateAdminResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_template(
    file: UploadFile = File(...),
    schema_data: str = Form(...),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role(Role.ADMIN)),
):
    """Admin-only multipart form upload for PA templates."""
    try:
        schema = json.loads(schema_data)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON schema")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty binary file")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Templates must be PDF format")

    encoded_file = base64.b64encode(file_bytes).decode("utf-8")

    new_template = PATemplate(
        id=uuid.uuid4(),
        name=schema.get("name", file.filename),
        fields=schema.get("fields", []),
        file_content=encoded_file,
        is_active=True
    )
    db.add(new_template)

    # Audit log for template creation
    audit_log = AuditLog(
        user_id=admin_user.id,
        action="CREATE_TEMPLATE",
        resource_type="template",
        resource_id=str(new_template.id)
    )
    db.add(audit_log)

    await db.commit()
    await db.refresh(new_template)
    return new_template


@router.patch("/templates/{id}", response_model=TemplateAdminResponseSchema)
async def patch_template(
    id: str,
    payload: TemplatePatchRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role(Role.ADMIN)),
):
    """Admin-only toggle active status for a template."""
    try:
        uid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Template not found")

    template = await db.get(PATemplate, uid)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if payload.is_active is not None:
        template.is_active = payload.is_active
    if payload.name is not None:
        template.name = payload.name
    db.add(template)

    # Audit log for template update
    audit_log = AuditLog(
        user_id=admin_user.id,
        action="UPDATE_TEMPLATE",
        resource_type="template",
        resource_id=str(template.id)
    )
    db.add(audit_log)

    await db.commit()
    await db.refresh(template)
    return template
