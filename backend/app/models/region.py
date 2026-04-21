"""
区域配置模型

存储用户自定义的检测区域（多边形）
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Index, String, Integer, Float, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.video_source import VideoSource


class Region(Base):
    """检测区域模型"""

    __tablename__ = "regions"

    # 主键
    region_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 外键
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("video_sources.source_id", ondelete="CASCADE"), nullable=False
    )

    # 区域信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="区域名称")
    points: Mapped[str] = mapped_column(Text, nullable=False, comment="JSON 多边形坐标")
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="#FF5733", comment="显示颜色")
    area_pixels: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="区域面积（像素²）")
    area_physical: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="区域物理面积（m²）")
    max_capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="最大容量（人）")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="显示顺序")
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="是否启用 0/1")

    # 预警阈值配置
    count_warning: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="人数警告阈值"
    )
    count_critical: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="人数严重阈值"
    )
    density_warning: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="密度警告阈值"
    )
    density_critical: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="密度严重阈值"
    )

    # 时间戳
    created_at: Mapped[str] = mapped_column(
        String(30), nullable=False, default=lambda: datetime.utcnow().isoformat() + "Z"
    )
    updated_at: Mapped[str] = mapped_column(
        String(30), nullable=False, default=lambda: datetime.utcnow().isoformat() + "Z"
    )

    # 关系
    video_source: Mapped["VideoSource"] = relationship("VideoSource", back_populates="regions")

    # 表约束和索引
    __table_args__ = (
        UniqueConstraint("source_id", "name", name="uq_region_source_name"),
        Index("idx_regions_source_id", "source_id"),
        Index("idx_regions_source_active", "source_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Region(id={self.region_id}, name={self.name})>"
