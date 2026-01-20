"""
聚合统计模型

存储按时间粒度聚合后的统计数据，用于历史趋势查询
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Index, String, Integer, Float, Text, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.video_source import VideoSource


class StatsAggregated(Base):
    """聚合统计模型"""

    __tablename__ = "stats_aggregated"

    # 自增主键
    stat_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 外键
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("video_sources.source_id", ondelete="CASCADE"), nullable=False
    )

    # 时间信息
    time_bucket: Mapped[str] = mapped_column(String(30), nullable=False, comment="时间桶起始时间")
    interval_type: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="聚合粒度: 1m/5m/1h/1d"
    )

    # 统计数据
    total_count_avg: Mapped[float] = mapped_column(Float, nullable=False, comment="平均人数")
    total_count_max: Mapped[int] = mapped_column(Integer, nullable=False, comment="最大人数")
    total_count_min: Mapped[int] = mapped_column(Integer, nullable=False, comment="最小人数")
    total_density_avg: Mapped[float] = mapped_column(Float, nullable=False, comment="平均密度")

    # 区域统计（JSON）
    region_stats: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="JSON 各区域统计"
    )

    # 其他指标
    crowd_index_avg: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="平均拥挤指数"
    )
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, comment="采样点数量")

    # 时间戳
    created_at: Mapped[str] = mapped_column(
        String(30), nullable=False, default=lambda: datetime.utcnow().isoformat() + "Z"
    )

    # 关系
    video_source: Mapped["VideoSource"] = relationship("VideoSource", back_populates="stats")

    # 表约束和索引
    __table_args__ = (
        CheckConstraint("interval_type IN ('1m', '5m', '1h', '1d')", name="ck_interval_type"),
        UniqueConstraint("source_id", "interval_type", "time_bucket", name="uq_stats_source_interval_time"),
        Index("idx_stats_source_interval_time", "source_id", "interval_type", "time_bucket"),
        Index("idx_stats_time_bucket", "time_bucket"),
    )

    def __repr__(self) -> str:
        return f"<StatsAggregated(id={self.stat_id}, bucket={self.time_bucket}, interval={self.interval_type})>"
