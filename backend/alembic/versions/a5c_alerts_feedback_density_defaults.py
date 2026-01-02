"""Add alert rules/events, feedback, and default density thresholds

Revision ID: a5c_alerts_feedback
Revises: f24_render_config
Create Date: 2026-01-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a5c_alerts_feedback"
down_revision: Union[str, None] = "f24_render_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    alert_threshold_type = sa.Enum(
        "count", "density", name="alert_threshold_type"
    )
    alert_level = sa.Enum(
        "low", "medium", "high", name="alert_level"
    )
    alert_threshold_type.create(op.get_bind(), checkfirst=True)
    alert_level.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "alert_rules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("stream_id", sa.String(length=36), nullable=False),
        sa.Column("roi_id", sa.String(length=36), nullable=True),
        sa.Column("threshold_type", alert_threshold_type, nullable=False),
        sa.Column("threshold_value", sa.Float(), nullable=True),
        sa.Column("level", alert_level, nullable=False, server_default="medium"),
        sa.Column("min_duration_sec", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("cooldown_sec", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["roi_id"], ["rois.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["stream_id"], ["video_streams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_rules_stream_id", "alert_rules", ["stream_id"])
    op.create_index("ix_alert_rules_roi_id", "alert_rules", ["roi_id"])

    op.create_table(
        "alert_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("rule_id", sa.String(length=36), nullable=True),
        sa.Column("stream_id", sa.String(length=36), nullable=False),
        sa.Column("roi_id", sa.String(length=36), nullable=True),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("start_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("peak_density", sa.Float(), nullable=False, server_default="0"),
        sa.Column("count_peak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.String(length=512), nullable=True),
        sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["roi_id"], ["rois.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rule_id"], ["alert_rules.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["stream_id"], ["video_streams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_events_stream_id", "alert_events", ["stream_id"])
    op.create_index("ix_alert_events_roi_id", "alert_events", ["roi_id"])
    op.create_index("ix_alert_events_rule_id", "alert_events", ["rule_id"])

    op.create_table(
        "feedbacks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("stream_id", sa.String(length=36), nullable=False),
        sa.Column("message", sa.String(length=1024), nullable=True),
        sa.Column("payload", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["stream_id"], ["video_streams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedbacks_stream_id", "feedbacks", ["stream_id"])

    op.add_column(
        "system_configs",
        sa.Column(
            "default_density_thresholds",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text(
                "'{\"low\": 0.3, \"medium\": 0.6, \"high\": 0.8}'::json"
            ),
            comment="默认密度阈值配置 {low, medium, high}",
        ),
    )


def downgrade() -> None:
    op.drop_column("system_configs", "default_density_thresholds")

    op.drop_index("ix_feedbacks_stream_id", table_name="feedbacks")
    op.drop_table("feedbacks")

    op.drop_index("ix_alert_events_rule_id", table_name="alert_events")
    op.drop_index("ix_alert_events_roi_id", table_name="alert_events")
    op.drop_index("ix_alert_events_stream_id", table_name="alert_events")
    op.drop_table("alert_events")

    op.drop_index("ix_alert_rules_roi_id", table_name="alert_rules")
    op.drop_index("ix_alert_rules_stream_id", table_name="alert_rules")
    op.drop_table("alert_rules")

    alert_threshold_type = sa.Enum(
        "count", "density", name="alert_threshold_type"
    )
    alert_level = sa.Enum(
        "low", "medium", "high", name="alert_level"
    )
    alert_threshold_type.drop(op.get_bind(), checkfirst=True)
    alert_level.drop(op.get_bind(), checkfirst=True)
