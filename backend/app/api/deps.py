"""
API 依赖注入

提供数据库会话和 Repository 实例
"""

from typing import Generator

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories import (
    VideoSourceRepository,
    RegionRepository,
    AlertConfigRepository,
    AlertRepository,
    StatsRepository,
    ExportTaskRepository,
)


def get_video_source_repo(db: Session = next(get_db())) -> VideoSourceRepository:
    """获取 VideoSourceRepository 实例"""
    return VideoSourceRepository(db)


def get_region_repo(db: Session = next(get_db())) -> RegionRepository:
    """获取 RegionRepository 实例"""
    return RegionRepository(db)


def get_alert_config_repo(db: Session = next(get_db())) -> AlertConfigRepository:
    """获取 AlertConfigRepository 实例"""
    return AlertConfigRepository(db)


def get_alert_repo(db: Session = next(get_db())) -> AlertRepository:
    """获取 AlertRepository 实例"""
    return AlertRepository(db)


def get_stats_repo(db: Session = next(get_db())) -> StatsRepository:
    """获取 StatsRepository 实例"""
    return StatsRepository(db)


def get_export_task_repo(db: Session = next(get_db())) -> ExportTaskRepository:
    """获取 ExportTaskRepository 实例"""
    return ExportTaskRepository(db)
