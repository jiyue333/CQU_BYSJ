"""
告警记录模型

存储历史告警信息，用于查询和分析
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Index, String, Integer, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.video_source import VideoSource


class Alert(Base):
    """告警记录模型"""

    __tablename__ = "alerts"

    # 主键
    alert_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 外键
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("video_sources.source_id", ondelete="CASCADE"), nullable=False
    )

    # 告警信息
    alert_type: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="类型: total_count / region_count"
    )
    level: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="级别: warning / critical"
    )
    region_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, comment="区域 ID"
    )
    region_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="区域名称"
    )
    current_value: Mapped[int] = mapped_column(Integer, nullable=False, comment="当前值")
    threshold: Mapped[int] = mapped_column(Integer, nullable=False, comment="触发阈值")
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="告警消息")

    # 确认状态
    is_acknowledged: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="是否确认 0/1"
    )
    acknowledged_at: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, comment="确认时间"
    )

    # 时间戳
    timestamp: Mapped[str] = mapped_column(String(30), nullable=False, comment="告警触发时间")
    created_at: Mapped[str] = mapped_column(
        String(30), nullable=False, default=lambda: datetime.utcnow().isoformat() + "Z"
    )

    # 关系
    video_source: Mapped["VideoSource"] = relationship("VideoSource", back_populates="alerts")

    # 表约束和索引
    __table_args__ = (
        CheckConstraint("alert_type IN ('total_count', 'region_count')", name="ck_alert_type"),
        CheckConstraint("level IN ('warning', 'critical')", name="ck_alert_level"),
        Index("idx_alerts_source_id", "source_id"),
        Index("idx_alerts_timestamp", "timestamp"),
        Index("idx_alerts_source_time", "source_id", "timestamp"),
        Index("idx_alerts_level", "level"),
        Index("idx_alerts_unacknowledged", "source_id", "is_acknowledged"),
    )

    def __repr__(self) -> str:
        return f"<Alert(id={self.alert_id}, type={self.alert_type}, level={self.level})>"
