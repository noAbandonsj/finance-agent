"""Create the initial business records schema."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260710_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_run",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("thread_id", sa.String(length=128), nullable=False),
        sa.Column("user_query", sa.Text(), nullable=False),
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_cutoff", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analysis_run_status_started_at",
        "analysis_run",
        ["status", "started_at"],
        unique=False,
    )

    op.create_table(
        "analysis_event",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("terminal", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"], ["analysis_run.id"], name="fk_analysis_event_run_id", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "sequence", name="uq_analysis_event_run_id_sequence"),
    )
    op.create_index(
        "ix_analysis_event_run_id_sequence",
        "analysis_event",
        ["run_id", "sequence"],
        unique=False,
    )

    op.create_table(
        "tool_call_record",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("arguments_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("market_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["analysis_run.id"],
            name="fk_tool_call_record_run_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tool_call_record_run_id", "tool_call_record", ["run_id"], unique=False)

    op.create_table(
        "analysis_result",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("report_markdown", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"], ["analysis_run.id"], name="fk_analysis_result_run_id", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", name="uq_analysis_result_run_id"),
    )
    op.create_index("ix_analysis_result_run_id", "analysis_result", ["run_id"], unique=False)

    op.create_table(
        "watchlist_item",
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("security_type", sa.String(length=16), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("symbol"),
    )


def downgrade() -> None:
    op.drop_table("watchlist_item")
    op.drop_index("ix_analysis_result_run_id", table_name="analysis_result")
    op.drop_table("analysis_result")
    op.drop_index("ix_tool_call_record_run_id", table_name="tool_call_record")
    op.drop_table("tool_call_record")
    op.drop_index("ix_analysis_event_run_id_sequence", table_name="analysis_event")
    op.drop_table("analysis_event")
    op.drop_index("ix_analysis_run_status_started_at", table_name="analysis_run")
    op.drop_table("analysis_run")
