"""initial tables

Revision ID: 001_initial
Revises:
Create Date: 2026-06-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "doctor", "viewer", name="role"),
            nullable=False,
            server_default="viewer",
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # token_blacklist
    op.create_table(
        "token_blacklist",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("token_jti", sa.String(255), nullable=False, unique=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_token_blacklist_jti", "token_blacklist", ["token_jti"])

    # workflows
    op.create_table(
        "workflows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", sa.String(100), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "processing", "awaiting_approval",
                "approved", "rejected", "completed", "failed",
                name="workflowstatus",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("payer_type", sa.String(100), nullable=True),
        sa.Column("result_data", postgresql.JSONB, nullable=True),
        sa.Column("langgraph_thread_id", sa.String(255), nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_workflows_patient_id", "workflows", ["patient_id"])

    # clinical_records
    op.create_table(
        "clinical_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflows.id"),
            nullable=False,
        ),
        sa.Column("patient_id", sa.String(100), nullable=False),
        sa.Column("icd10_codes", postgresql.JSONB, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("raw_text_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # audit_logs — append-only
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("patient_id", sa.String(100), nullable=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_patient_id", "audit_logs", ["patient_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("clinical_records")
    op.drop_table("workflows")
    op.drop_table("token_blacklist")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS role")
    op.execute("DROP TYPE IF EXISTS workflowstatus")
