"""
预警配置 Repository

AlertConfig 的数据库操作
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert_config import AlertConfig


class AlertConfigRepository:
    """预警配置仓储"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, config: AlertConfig) -> AlertConfig:
        """创建预警配置"""
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def get_by_id(self, config_id: str) -> Optional[AlertConfig]:
        """根据 ID 获取配置"""
        return self.db.get(AlertConfig, config_id)

    def get_by_source_id(self, source_id: str) -> Optional[AlertConfig]:
        """根据数据源 ID 获取配置（一对一）"""
        stmt = select(AlertConfig).where(AlertConfig.source_id == source_id)
        return self.db.scalars(stmt).first()

    def get_or_create(self, source_id: str, config_id: str) -> AlertConfig:
        """获取或创建配置（使用默认值）"""
        config = self.get_by_source_id(source_id)
        if config:
            return config
        # 创建默认配置
        config = AlertConfig(config_id=config_id, source_id=source_id)
        return self.create(config)

    def update(self, config: AlertConfig, **kwargs) -> AlertConfig:
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        config.updated_at = datetime.utcnow().isoformat() + "Z"
        self.db.commit()
        self.db.refresh(config)
        return config

    def update_thresholds(
        self,
        source_id: str,
        total_warning: Optional[int] = None,
        total_critical: Optional[int] = None,
        default_region_warning: Optional[int] = None,
        default_region_critical: Optional[int] = None,
        region_thresholds: Optional[str] = None,
        cooldown_seconds: Optional[int] = None,
    ) -> Optional[AlertConfig]:
        """更新阈值配置"""
        config = self.get_by_source_id(source_id)
        if not config:
            return None

        updates = {}
        if total_warning is not None:
            updates["total_warning_threshold"] = total_warning
        if total_critical is not None:
            updates["total_critical_threshold"] = total_critical
        if default_region_warning is not None:
            updates["default_region_warning"] = default_region_warning
        if default_region_critical is not None:
            updates["default_region_critical"] = default_region_critical
        if region_thresholds is not None:
            updates["region_thresholds"] = region_thresholds
        if cooldown_seconds is not None:
            updates["cooldown_seconds"] = cooldown_seconds

        if updates:
            return self.update(config, **updates)
        return config

    def delete(self, config_id: str) -> bool:
        """删除配置"""
        config = self.get_by_id(config_id)
        if config:
            self.db.delete(config)
            self.db.commit()
            return True
        return False

    def set_enabled(self, source_id: str, enabled: bool) -> Optional[AlertConfig]:
        """设置预警启用状态"""
        config = self.get_by_source_id(source_id)
        if config:
            return self.update(config, enabled=1 if enabled else 0)
        return None
