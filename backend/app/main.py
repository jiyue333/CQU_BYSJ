"""FastAPI 应用入口

提供应用生命周期管理和路由注册。
使用结构化日志记录应用状态。

Requirements: 9.3
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.core.config import settings
from app.core.logging import setup_logging, bind_context

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    setup_logging()
    
    logger.info("application_starting", app_name=settings.app_name)
    
    # 初始化数据库连接池
    from app.core.database import check_db_connection, close_db, init_db
    logger.info("initializing_database")
    await init_db()
    logger.info("checking_database_connection")
    if not await check_db_connection():
        logger.error("database_connection_failed")
        raise RuntimeError("Database connection failed")
    logger.info("database_connected")
    
    # 初始化 Redis 连接
    from app.core.redis import check_redis_connection, close_redis, init_redis
    logger.info("initializing_redis")
    await init_redis()
    logger.info("checking_redis_connection")
    if not await check_redis_connection():
        logger.error("redis_connection_failed")
        raise RuntimeError("Redis connection failed")
    logger.info("redis_connected")
    
    # 启动 WebSocket 推送服务
    from app.services.result_push_service import get_result_push_service
    from app.services.status_push_service import get_status_push_service
    from app.services.alert_service import get_alert_service
    logger.info("starting_websocket_push_services")
    result_push_service = get_result_push_service()
    status_push_service = get_status_push_service()
    alert_service = get_alert_service()
    await result_push_service.start()
    await status_push_service.start()
    await alert_service.start()
    logger.info("websocket_push_services_started")
    
    # 启动历史数据存储服务
    from app.services.history_storage_service import get_history_storage_service
    logger.info("starting_history_storage_service")
    history_storage_service = get_history_storage_service()
    await history_storage_service.start()
    logger.info("history_storage_service_started")
    
    logger.info("application_startup_complete")
    
    yield
    
    logger.info("application_shutting_down")
    
    # 停止 WebSocket 推送服务
    logger.info("stopping_websocket_push_services")
    await result_push_service.stop()
    await status_push_service.stop()
    await alert_service.stop()
    
    # 停止历史数据存储服务
    logger.info("stopping_history_storage_service")
    await history_storage_service.stop()
    
    # 清理资源
    logger.info("closing_database_connections")
    await close_db()
    logger.info("closing_redis_connections")
    await close_redis()
    
    logger.info("application_shutdown_complete")


app = FastAPI(
    title="人流计数与密度分析系统",
    description="基于 YOLO 的实时人流计数与密度分析系统 API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """健康检查"""
    return {"status": "ok"}


# 注册路由
from app.api import config, files, history, rois, roi_templates, streams, websockets, alerts, feedback
app.include_router(streams.router, prefix="/api/streams", tags=["streams"])
app.include_router(rois.router, prefix="/api/streams", tags=["rois"])
app.include_router(roi_templates.router, prefix="/api/rois", tags=["rois"])
app.include_router(history.router, prefix="/api/streams", tags=["history"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])
app.include_router(websockets.router, prefix="/ws", tags=["websockets"])
