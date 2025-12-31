"""FastAPI 应用入口"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    setup_logging()
    
    # 初始化数据库连接池
    from app.core.database import check_db_connection, close_db, init_db
    print("Initializing database...")
    await init_db()
    print("Checking database connection...")
    if not await check_db_connection():
        raise RuntimeError("Database connection failed")
    
    # 初始化 Redis 连接
    from app.core.redis import check_redis_connection, close_redis, init_redis
    print("Initializing Redis...")
    await init_redis()
    print("Checking Redis connection...")
    if not await check_redis_connection():
        raise RuntimeError("Redis connection failed")
    
    # TODO: 启动 Redis Streams 监听（检测结果与状态上报）
    # TODO: 启动 Redis PubSub 监听（控制指令）
    
    print("Application startup complete")
    
    yield
    
    # 清理资源
    print("Closing database connections...")
    await close_db()
    print("Closing Redis connections...")
    await close_redis()
    print("Application shutdown complete")


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


# TODO: 注册路由
# from app.api import streams, rois, config, history
# app.include_router(streams.router, prefix="/api/streams", tags=["streams"])
# app.include_router(rois.router, prefix="/api", tags=["rois"])
# app.include_router(config.router, prefix="/api/config", tags=["config"])
# app.include_router(history.router, prefix="/api", tags=["history"])
