"""
数据源 Repository

VideoSource 的数据库操作
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.video_source import VideoSource


class VideoSourceRepository:
    """数据源仓储"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, source: VideoSource) -> VideoSource:
        """创建数据源"""
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def get_by_id(self, source_id: str) -> Optional[VideoSource]:
        """根据 ID 获取数据源"""
        return self.db.get(VideoSource, source_id)

    def get_all(self, skip: int = 0, limit: int = 100) -> list[VideoSource]:
        """获取所有数据源（分页）"""
        stmt = select(VideoSource).order_by(VideoSource.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def get_by_status(self, status: str) -> list[VideoSource]:
        """根据状态获取数据源"""
        stmt = select(VideoSource).where(VideoSource.status == status)
        return list(self.db.scalars(stmt).all())

    def update(self, source: VideoSource, **kwargs) -> VideoSource:
        """更新数据源"""
        for key, value in kwargs.items():
            if hasattr(source, key):
                setattr(source, key, value)
        source.updated_at = datetime.utcnow().isoformat() + "Z"
        self.db.commit()
        self.db.refresh(source)
        return source

    def update_status(self, source_id: str, status: str) -> Optional[VideoSource]:
        """更新数据源状态"""
        source = self.get_by_id(source_id)
        if source:
            return self.update(source, status=status)
        return None

    def delete(self, source_id: str) -> bool:
        """删除数据源"""
        source = self.get_by_id(source_id)
        if source:
            self.db.delete(source)
            self.db.commit()
            return True
        return False

    def count(self) -> int:
        """获取数据源总数"""
        stmt = select(VideoSource)
        return len(list(self.db.scalars(stmt).all()))

    def count_by_status(self, status: str) -> int:
        """按状态统计数量"""
        stmt = select(VideoSource).where(VideoSource.status == status)
        return len(list(self.db.scalars(stmt).all()))
