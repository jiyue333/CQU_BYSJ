"""
预警配置模型

存储每个数据源的预警阈值配置
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Index, String, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.video_source import VideoSource


class AlertConfig(Base):
    """预警配置模型"""

    __tablename__ = "alert_configs"

    # 主键
    config_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 外键（一对一）
    source_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("video_sources.source_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # 全局阈值
    total_warning_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=50, comment="总人数警告阈值"
    )
    total_critical_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, comment="总人数严重阈值"
    )

    # 区域默认阈值
    default_region_warning: Mapped[int] = mapped_column(
        Integer, nullable=False, default=20, comment="默认区域警告阈值"
    )
    default_region_critical: Mapped[int] = mapped_column(
        Integer, nullable=False, default=50, comment="默认区域严重阈值"
    )

    # 旧版区域阈值（JSON，已弃用；区域模型字段为权威来源）
    region_thresholds: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="[已弃用] JSON 自定义区域阈值"
    )

    # 配置
    cooldown_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30, comment="告警冷却时间"
    )
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="是否启用 0/1")

    # 时间戳
    created_at: Mapped[str] = mapped_column(
        String(30), nullable=False, default=lambda: datetime.utcnow().isoformat() + "Z"
    )
    updated_at: Mapped[str] = mapped_column(
        String(30), nullable=False, default=lambda: datetime.utcnow().isoformat() + "Z"
    )

    # 关系
    video_source: Mapped["VideoSource"] = relationship("VideoSource", back_populates="alert_config")

    # 索引
    __table_args__ = (Index("idx_alert_configs_source_id", "source_id"),)

    def __repr__(self) -> str:
        return f"<AlertConfig(id={self.config_id}, source_id={self.source_id})>"
