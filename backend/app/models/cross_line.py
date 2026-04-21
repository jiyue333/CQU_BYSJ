"""
Cross-Line 配置模型

存储用户自定义的计数线段（两点定义）
用于 YOLO ObjectCounter 的 cross-line 计数
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Index, String, Integer, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.video_source import VideoSource


class CrossLine(Base):
    """计数线段模型"""

    __tablename__ = "cross_lines"

    # 主键
    line_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 外键
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("video_sources.source_id", ondelete="CASCADE"), nullable=False
    )

    # 线段信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="线段名称")
    start_x: Mapped[float] = mapped_column(Float, nullable=False, comment="起点 x% (0-100)")
    start_y: Mapped[float] = mapped_column(Float, nullable=False, comment="起点 y% (0-100)")
    end_x: Mapped[float] = mapped_column(Float, nullable=False, comment="终点 x% (0-100)")
    end_y: Mapped[float] = mapped_column(Float, nullable=False, comment="终点 y% (0-100)")
    direction: Mapped[str] = mapped_column(String(10), nullable=False, default="in", comment="计数方向")
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="#00FF00", comment="显示颜色")
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="是否启用 0/1")

    # 时间戳
    created_at: Mapped[str] = mapped_column(
        String(30), nullable=False, default=lambda: datetime.utcnow().isoformat() + "Z"
    )
    updated_at: Mapped[str] = mapped_column(
        String(30), nullable=False, default=lambda: datetime.utcnow().isoformat() + "Z"
    )

    # 关系
    video_source: Mapped["VideoSource"] = relationship("VideoSource")

    # 表约束和索引
    __table_args__ = (
        UniqueConstraint("source_id", "name", name="uq_crossline_source_name"),
        Index("idx_crosslines_source_id", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<CrossLine(id={self.line_id}, name={self.name})>"
