import uuid
import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import String, DateTime, Float, Text, Enum as SAEnum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


class Workflow(Base):
    """Workflow entity — tracks each Prior Authorization pipeline run."""
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[WorkflowStatus] = mapped_column(
        SAEnum(WorkflowStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=WorkflowStatus.PENDING,
        nullable=False,
    )
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    payer_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    result_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    langgraph_thread_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ClinicalRecord(Base):
    """Stores extracted clinical data after PHI de-identification."""
    __tablename__ = "clinical_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False
    )
    patient_id: Mapped[str] = mapped_column(String(100), nullable=False)
    icd10_codes: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    raw_text_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
