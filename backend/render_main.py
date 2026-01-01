#!/usr/bin/env python
"""渲染服务入口

方案 F：服务端渲染热力图
独立进程运行，订阅 render:control 通道，执行渲染循环。

使用方法：
    python render_main.py
"""

import asyncio
import signal
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

import structlog

from app.core.config import settings
from app.core.logging import setup_logging
from app.services.render_worker import get_render_worker

logger = structlog.get_logger(__name__)


async def main():
    """主函数"""
    setup_logging()
    
    logger.info(
        "starting_render_service",
        render_fps=settings.render_fps,
        infer_stride=settings.render_infer_stride,
        max_concurrent=settings.render_max_concurrent,
    )
    
    worker = get_render_worker()
    
    # 设置信号处理
    loop = asyncio.get_event_loop()
    
    async def shutdown():
        logger.info("shutdown_signal_received")
        await worker.stop()
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
    
    # 启动 Worker
    await worker.start()
    
    # 保持运行
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await worker.stop()
    
    logger.info("render_service_stopped")


if __name__ == "__main__":
    asyncio.run(main())
