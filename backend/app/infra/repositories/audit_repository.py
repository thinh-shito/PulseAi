from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models.audit_log import AuditLog
from app.infra.repositories.base_repository import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    """
    Audit Log Repository extending BaseRepository.
    Enforces HIPAA/TT46 append-only policy by disabling update and remove operations.
    """

    def __init__(self):
        super().__init__(AuditLog)

    async def update(self, db: AsyncSession, *, db_obj, obj_in) -> AuditLog:
        raise ValueError("Audit logs are immutable and cannot be updated.")

    async def remove(self, db: AsyncSession, *, id) -> AuditLog:
        raise ValueError("Audit logs are immutable and cannot be deleted.")


audit_repo = AuditRepository()
