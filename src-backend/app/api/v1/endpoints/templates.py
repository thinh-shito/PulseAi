import io
import uuid
import base64
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, require_role
from app.core.security import Role
from app.domain.models.user import User
from app.domain.models.pa_templates import PATemplate

router = APIRouter(prefix="/templates", tags=["PA Templates"])


class TemplateResponseSchema(BaseModel):
    id: uuid.UUID
    name: str
    fields: list
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=List[TemplateResponseSchema])
async def list_templates(
    all: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.DOCTOR, Role.ADMIN)),
):
    """Retrieve active templates (or all templates if all=True and user is ADMIN)."""
    if all and current_user.role == Role.ADMIN:
        result = await db.execute(select(PATemplate))
    else:
        result = await db.execute(select(PATemplate).where(PATemplate.is_active))
    return result.scalars().all()


@router.get("/{id}/download-blank")
async def download_blank_template(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.DOCTOR, Role.ADMIN)),
):
    """Download the blank template PDF (DOCTOR and ADMIN)."""
    try:
        uid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Template not found")

    template = await db.get(PATemplate, uid)
    if not template or not template.is_active:
        raise HTTPException(status_code=404, detail="Template not found")

    try:
        file_bytes = base64.b64decode(template.file_content)
    except Exception:
        raise HTTPException(
            status_code=500, detail="Failed to decode template file content")

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=blank_{template.name}.pdf"}
    )
