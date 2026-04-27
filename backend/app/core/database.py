"""
数据库配置

SQLite + SQLAlchemy 2.0
"""

import traceback

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from app.core.config import settings
from app.core.logger import logger


class Base(DeclarativeBase):
    """SQLAlchemy 模型基类"""

    pass


# 创建数据库引擎
engine = create_engine(
    settings.get_database_url(),
    echo=settings.DEBUG,  # 调试模式下打印 SQL
    connect_args={"check_same_thread": False},  # SQLite 需要
)


# 在 DEBUG 下输出每次 ROLLBACK 的调用栈（定位来源）
if settings.DEBUG:
    @event.listens_for(Session, "after_rollback")
    def _log_rollback(session: Session) -> None:
        logger.warning("DB rollback triggered. Stacktrace:\n%s", "".join(traceback.format_stack()))

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    获取数据库会话（依赖注入用）

    Usage:
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    初始化数据库（创建所有表）

    在应用启动时调用
    """
    # 确保数据目录存在
    settings.ensure_dirs()

    # 导入所有模型，确保它们被注册到 Base.metadata
    from app.models.video_source import VideoSource  # noqa: F401
    from app.models.region import Region  # noqa: F401
    from app.models.alert_config import AlertConfig  # noqa: F401
    from app.models.alert import Alert  # noqa: F401
    from app.models.stats_aggregated import StatsAggregated  # noqa: F401
    from app.models.export_task import ExportTask  # noqa: F401

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    # 轻量级迁移：为已有表添加新列（SQLite 不支持 ALTER COLUMN，但支持 ADD COLUMN）
    with engine.connect() as conn:
        from sqlalchemy import inspect as sa_inspect, text
        inspector = sa_inspect(engine)
        if "alerts" in inspector.get_table_names():
            create_sql = conn.execute(
                text("SELECT sql FROM sqlite_master WHERE type='table' AND name='alerts'")
            ).scalar() or ""
            if "region_density" not in create_sql:
                conn.execute(text("PRAGMA foreign_keys=OFF"))
                conn.execute(text("""
                    CREATE TABLE alerts_new (
                        alert_id VARCHAR(36) NOT NULL,
                        source_id VARCHAR(36) NOT NULL,
                        alert_type VARCHAR(30) NOT NULL,
                        level VARCHAR(20) NOT NULL,
                        region_id VARCHAR(36),
                        region_name VARCHAR(100),
                        current_value INTEGER NOT NULL,
                        threshold INTEGER NOT NULL,
                        message TEXT,
                        is_acknowledged INTEGER NOT NULL,
                        acknowledged_at VARCHAR(30),
                        timestamp VARCHAR(30) NOT NULL,
                        created_at VARCHAR(30) NOT NULL,
                        PRIMARY KEY (alert_id),
                        CONSTRAINT ck_alert_type CHECK (alert_type IN ('total_count', 'region_count', 'region_density')),
                        CONSTRAINT ck_alert_level CHECK (level IN ('warning', 'critical')),
                        FOREIGN KEY(source_id) REFERENCES video_sources (source_id) ON DELETE CASCADE
                    )
                """))
                conn.execute(text("""
                    INSERT INTO alerts_new (
                        alert_id, source_id, alert_type, level, region_id, region_name,
                        current_value, threshold, message, is_acknowledged, acknowledged_at,
                        timestamp, created_at
                    )
                    SELECT
                        alert_id, source_id, alert_type, level, region_id, region_name,
                        current_value, threshold, message, is_acknowledged, acknowledged_at,
                        timestamp, created_at
                    FROM alerts
                """))
                conn.execute(text("DROP TABLE alerts"))
                conn.execute(text("ALTER TABLE alerts_new RENAME TO alerts"))
                conn.execute(text("CREATE INDEX idx_alerts_level ON alerts (level)"))
                conn.execute(text("CREATE INDEX idx_alerts_unacknowledged ON alerts (source_id, is_acknowledged)"))
                conn.execute(text("CREATE INDEX idx_alerts_source_time ON alerts (source_id, timestamp)"))
                conn.execute(text("CREATE INDEX idx_alerts_source_id ON alerts (source_id)"))
                conn.execute(text("CREATE INDEX idx_alerts_timestamp ON alerts (timestamp)"))
                conn.execute(text("PRAGMA foreign_keys=ON"))
                conn.commit()
