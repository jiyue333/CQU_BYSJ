"""
聚合统计模型

存储按时间粒度聚合后的统计数据，用于历史趋势查询
"""

import json
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Index, String, Integer, Float, Text, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.video_source import VideoSource


class RegionStatsData:
    """区域统计数据结构"""

    def __init__(self, name: str, avg: float, max: int, min: int, density_avg: float = 0.0):
        self.name = name
        self.avg = avg
        self.max = max
        self.min = min
        self.density_avg = density_avg

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "avg": self.avg,
            "max": self.max,
            "min": self.min,
            "density_avg": self.density_avg,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RegionStatsData":
        return cls(
            name=str(data.get("name", "")),
            avg=float(data.get("avg", 0)),
            max=int(data.get("max", 0)),
            min=int(data.get("min", 0)),
            density_avg=float(data.get("density_avg", 0)),
        )


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
    # 格式: {"region_id": {"name": "前区", "avg": 50, "max": 65, "min": 40, "density_avg": 1.5}}
    region_stats: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="JSON 各区域统计"
    )

    # 其他指标（crowd_index_avg 已弃用，保留列以兼容旧数据）
    crowd_index_avg: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="[已弃用] 平均拥挤指数，请使用 total_density_avg"
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

    def get_region_stats_dict(self) -> dict[str, RegionStatsData]:
        """解析 region_stats JSON 为字典 (key: region_id)"""
        if not self.region_stats:
            return {}
        try:
            raw = json.loads(self.region_stats) if isinstance(self.region_stats, str) else self.region_stats
            return {region_id: RegionStatsData.from_dict(data) for region_id, data in raw.items()}
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_region_stats_dict(self, data: dict[str, RegionStatsData]) -> None:
        """将区域统计字典序列化为 JSON"""
        self.region_stats = json.dumps(
            {region_id: stats.to_dict() for region_id, stats in data.items()},
            ensure_ascii=False
        )

    def get_region_density_avg(self, region_id: str) -> Optional[float]:
        """获取指定区域的平均密度"""
        region_data = self.get_region_stats_dict()
        if region_id in region_data:
            return region_data[region_id].density_avg
        return None

    def get_region_by_name(self, region_name: str) -> Optional[tuple[str, RegionStatsData]]:
        """根据区域名称查找区域统计 (返回 region_id 和数据)"""
        region_data = self.get_region_stats_dict()
        for region_id, data in region_data.items():
            if data.name == region_name:
                return region_id, data
        return None

    def __repr__(self) -> str:
        return f"<StatsAggregated(id={self.stat_id}, bucket={self.time_bucket}, interval={self.interval_type})>"
