"""
导出任务模型

记录数据导出请求及其状态
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Index, String, Integer, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.video_source import VideoSource


class ExportTask(Base):
    """导出任务模型"""

    __tablename__ = "export_tasks"

    # 主键
    task_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 外键
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("video_sources.source_id", ondelete="CASCADE"), nullable=False
    )

    # 任务信息
    export_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="类型: csv/xlsx/clip/snapshot"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", comment="状态: pending/processing/completed/failed"
    )

    # 时间范围
    time_from: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, comment="数据开始时间"
    )
    time_to: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, comment="数据结束时间")

    # 文件信息
    file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="生成文件路径")
    file_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="下载URL")
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="文件大小")

    # 错误信息
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息")

    # 时间戳
    created_at: Mapped[str] = mapped_column(
        String(30), nullable=False, default=lambda: datetime.utcnow().isoformat() + "Z"
    )
    completed_at: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, comment="完成时间")

    # 关系
    video_source: Mapped["VideoSource"] = relationship("VideoSource", back_populates="export_tasks")

    # 表约束和索引
    __table_args__ = (
        CheckConstraint("export_type IN ('csv', 'xlsx', 'clip', 'snapshot')", name="ck_export_type"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')", name="ck_export_status"
        ),
        Index("idx_export_source_id", "source_id"),
        Index("idx_export_status", "status"),
        Index("idx_export_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ExportTask(id={self.task_id}, type={self.export_type}, status={self.status})>"
