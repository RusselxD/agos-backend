"""Persist reading-log report snapshots and completed PDF exports."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reading_reports",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("analysis_text", sa.Text(), nullable=False),
        sa.Column("analysis_error", sa.Text()),
        sa.Column("analysis_started_at", sa.DateTime(timezone=True)),
        sa.Column("analysis_completed_at", sa.DateTime(timezone=True)),
        sa.Column("analysis_model", sa.String(100)),
        sa.Column("prompt_version", sa.String(20), nullable=False),
        sa.Column("template_version", sa.String(20), nullable=False),
        sa.Column("pdf_content", sa.LargeBinary()),
        sa.Column("pdf_created_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("created_by", "request_id", name="uq_reading_report_request"),
    )
    op.create_index("ix_reading_reports_created_by", "reading_reports", ["created_by"])
    op.create_index("ix_reading_reports_expires_at", "reading_reports", ["expires_at"])


def downgrade():
    op.drop_table("reading_reports")
