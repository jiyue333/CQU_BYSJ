"""
数据源模型

存储视频文件和摄像头流的元数据信息
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Index, String, Integer, Float, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.region import Region
    from app.models.alert_config import AlertConfig
    from app.models.alert import Alert
    from app.models.stats_aggregated import StatsAggregated
    from app.models.export_task import ExportTask


class VideoSource(Base):
    """视频数据源模型"""

    __tablename__ = "video_sources"

    # 主键
    source_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 基本信息
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="数据源名称")
    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="类型: file / stream"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ready", comment="状态: ready/running/stopped/error"
    )

    # 文件/流信息
    file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="文件存储路径")
    stream_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="流地址")

    # 视频元数据
    video_width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="视频宽度")
    video_height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="视频高度")
    video_fps: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="帧率")
    total_frames: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="总帧数")
    scene_area_m2: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="画面对应物理面积（m²）")

    # 时间戳（SQLite 用 TEXT 存储 ISO8601）
    created_at: Mapped[str] = mapped_column(
        String(30), nullable=False, default=lambda: datetime.utcnow().isoformat() + "Z"
    )
    updated_at: Mapped[str] = mapped_column(
        String(30), nullable=False, default=lambda: datetime.utcnow().isoformat() + "Z"
    )

    # 关系
    regions: Mapped[list["Region"]] = relationship(
        "Region", back_populates="video_source", cascade="all, delete-orphan"
    )
    alert_config: Mapped[Optional["AlertConfig"]] = relationship(
        "AlertConfig", back_populates="video_source", uselist=False, cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert", back_populates="video_source", cascade="all, delete-orphan"
    )
    stats: Mapped[list["StatsAggregated"]] = relationship(
        "StatsAggregated", back_populates="video_source", cascade="all, delete-orphan"
    )
    export_tasks: Mapped[list["ExportTask"]] = relationship(
        "ExportTask", back_populates="video_source", cascade="all, delete-orphan"
    )

    # 表约束和索引
    __table_args__ = (
        CheckConstraint("source_type IN ('file', 'stream')", name="ck_source_type"),
        CheckConstraint("status IN ('ready', 'running', 'stopped', 'error')", name="ck_status"),
        Index("idx_sources_status", "status"),
        Index("idx_sources_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<VideoSource(id={self.source_id}, name={self.name}, type={self.source_type})>"
