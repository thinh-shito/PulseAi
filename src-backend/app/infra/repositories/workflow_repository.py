from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.domain.models.workflow import Workflow, ClinicalRecord
from app.infra.repositories.base_repository import BaseRepository

class WorkflowRepository(BaseRepository[Workflow]):
    """
    Workflow Repository extending BaseRepository to manage prior authorization workflows
    and associated ClinicalRecords.
    """
    def __init__(self):
        super().__init__(Workflow)

    async def get_by_user(
        self, db: AsyncSession, *, user_id, skip: int = 0, limit: int = 100
    ) -> List[Workflow]:
        query = select(self.model).filter(self.model.created_by == user_id).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_clinical_record(
        self, db: AsyncSession, *, workflow_id
    ) -> Optional[ClinicalRecord]:
        query = select(ClinicalRecord).filter(ClinicalRecord.workflow_id == workflow_id)
        result = await db.execute(query)
        return result.scalars().first()

    async def create_clinical_record(
        self, db: AsyncSession, *, obj_in: dict
    ) -> ClinicalRecord:
        db_obj = ClinicalRecord(**obj_in)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

workflow_repo = WorkflowRepository()
