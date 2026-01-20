"""
数据库配置

SQLite + SQLAlchemy 2.0
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy 模型基类"""

    pass


# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # 调试模式下打印 SQL
    connect_args={"check_same_thread": False},  # SQLite 需要
)

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
    from app.models import (  # noqa: F401
        VideoSource,
        Region,
        AlertConfig,
        Alert,
        StatsAggregated,
        ExportTask,
    )

    # 创建所有表
    Base.metadata.create_all(bind=engine)
