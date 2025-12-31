"""推理服务独立入口

独立运行的 YOLO 推理服务，通过 Redis 与主后端通信。
支持水平扩展，可部署多个实例处理不同的视频流。

启动方式：
    python inference_main.py

环境变量：
    REDIS_URL: Redis 连接地址
    INFERENCE_FPS: 推理帧率
    CONFIDENCE_THRESHOLD: 置信度阈值
"""

import asyncio
import signal
import sys
from typing import Optional

import structlog

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.redis import init_redis, close_redis, check_redis_connection
from app.services.inference_worker import get_inference_worker, InferenceWorker

logger = structlog.get_logger(__name__)

# 全局 worker 实例
_worker: Optional[InferenceWorker] = None


async def startup() -> None:
    """启动推理服务"""
    global _worker
    
    setup_logging()
    logger.info("inference_service_starting")
    
    # 初始化 Redis 连接
    logger.info("initializing_redis")
    await init_redis()
    
    if not await check_redis_connection():
        logger.error("redis_connection_failed")
        raise RuntimeError("Redis connection failed")
    
    logger.info("redis_connected")
    
    # 启动推理 Worker
    logger.info("starting_inference_worker")
    _worker = get_inference_worker()
    await _worker.start()
    
    logger.info("inference_service_started")


async def shutdown() -> None:
    """关闭推理服务"""
    global _worker
    
    logger.info("inference_service_shutting_down")
    
    if _worker:
        await _worker.stop()
    
    await close_redis()
    
    logger.info("inference_service_stopped")


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
        logger.info("inference_service_running", 
                   inference_fps=settings.inference_fps,
                   confidence_threshold=settings.confidence_threshold)
        await stop_event.wait()
        
    except Exception as e:
        logger.error("inference_service_error", error=str(e))
        raise
    finally:
        await shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error("inference_service_fatal_error", error=str(e))
        sys.exit(1)
