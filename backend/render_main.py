"""渲染服务独立入口（方案 F）

独立运行的服务端渲染服务，通过 Redis 与主后端通信。
负责：拉流 → YOLO 推理 → 热力图叠加 → 推流

启动方式：
    python render_main.py

环境变量：
    REDIS_URL: Redis 连接地址
    ZLM_BASE_URL: ZLMediaKit 内部地址
    RENDER_FPS: 渲染帧率（默认 24）
    RENDER_INFER_STRIDE: 推理步长（默认 3，即每 3 帧推理一次）
"""

import asyncio
import signal
import sys
from typing import Optional

import structlog

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.redis import init_redis, close_redis, check_redis_connection
from app.services.render_worker import get_render_worker, RenderWorker

logger = structlog.get_logger(__name__)

# 全局 worker 实例
_worker: Optional[RenderWorker] = None


async def startup() -> None:
    """启动渲染服务"""
    global _worker
    
    setup_logging()
    logger.info("render_service_starting")
    
    # 初始化 Redis 连接
    logger.info("initializing_redis")
    await init_redis()
    
    if not await check_redis_connection():
        logger.error("redis_connection_failed")
        raise RuntimeError("Redis connection failed")
    
    logger.info("redis_connected")
    
    # 启动渲染 Worker
    logger.info("starting_render_worker")
    _worker = get_render_worker()
    await _worker.start()
    
    logger.info("render_service_started")


async def shutdown() -> None:
    """关闭渲染服务"""
    global _worker
    
    logger.info("render_service_shutting_down")
    
    if _worker:
        await _worker.stop()
    
    await close_redis()
    
    logger.info("render_service_stopped")


async def main() -> None:
    """主函数"""
    # 设置信号处理
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    
    def signal_handler():
        logger.info("received_shutdown_signal")
        stop_event.set()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        await startup()
        
        # 等待停止信号
        logger.info(
            "render_service_running",
            render_fps=settings.render_fps,
            render_infer_stride=settings.render_infer_stride,
            confidence_threshold=settings.confidence_threshold,
        )
        await stop_event.wait()
        
    except Exception as e:
        logger.error("render_service_error", error=str(e))
        raise
    finally:
        await shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error("render_service_fatal_error", error=str(e))
        sys.exit(1)
