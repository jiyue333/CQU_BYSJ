"""
区域 Repository

Region 的数据库操作
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.region import Region


class RegionRepository:
    """区域仓储"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, region: Region) -> Region:
        """创建区域"""
        self.db.add(region)
        self.db.commit()
        self.db.refresh(region)
        return region

    def get_by_id(self, region_id: str) -> Optional[Region]:
        """根据 ID 获取区域"""
        return self.db.get(Region, region_id)

    def get_by_source_id(self, source_id: str, active_only: bool = True) -> list[Region]:
        """获取数据源的所有区域"""
        stmt = select(Region).where(Region.source_id == source_id)
        if active_only:
            stmt = stmt.where(Region.is_active == 1)
        stmt = stmt.order_by(Region.display_order)
        return list(self.db.scalars(stmt).all())

    def get_by_name(self, source_id: str, name: str) -> Optional[Region]:
        """根据数据源和名称获取区域"""
        stmt = select(Region).where(Region.source_id == source_id, Region.name == name)
        return self.db.scalars(stmt).first()

    def update(self, region: Region, **kwargs) -> Region:
        """更新区域"""
        for key, value in kwargs.items():
            if hasattr(region, key):
                setattr(region, key, value)
        region.updated_at = datetime.utcnow().isoformat() + "Z"
        self.db.commit()
        self.db.refresh(region)
        return region

    def delete(self, region_id: str) -> bool:
        """删除区域"""
        region = self.get_by_id(region_id)
        if region:
            self.db.delete(region)
            self.db.commit()
            return True
        return False

    def delete_by_source_id(self, source_id: str) -> int:
        """删除数据源的所有区域"""
        regions = self.get_by_source_id(source_id, active_only=False)
        count = len(regions)
        for region in regions:
            self.db.delete(region)
        self.db.commit()
        return count

    def set_active(self, region_id: str, is_active: bool) -> Optional[Region]:
        """设置区域启用状态"""
        region = self.get_by_id(region_id)
        if region:
            return self.update(region, is_active=1 if is_active else 0)
        return None
