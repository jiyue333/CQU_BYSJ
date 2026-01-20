"""
系统状态 API

获取系统运行状态
"""

import time
import psutil

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories import VideoSourceRepository
from app.schemas.common import ApiResponse
from app.schemas.status import SystemStatusResponse

router = APIRouter(tags=["系统状态"])

# 应用启动时间
_start_time = time.time()


@router.get("/status", response_model=ApiResponse[SystemStatusResponse])
async def get_system_status(
    db: Session = Depends(get_db),
):
    """获取系统运行状态"""
    # 计算运行时长
    uptime = int(time.time() - _start_time)

    # 统计活跃数据源
    source_repo = VideoSourceRepository(db)
    active_sources = source_repo.count_by_status("running")

    # 获取内存使用率
    memory_usage = psutil.virtual_memory().percent / 100

    # GPU 使用率（如果可用）
    gpu_usage = None
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu_usage = gpus[0].load
    except ImportError:
        pass

    return ApiResponse.success(
        data=SystemStatusResponse(
            status="running",
            uptime=uptime,
            active_sources=active_sources,
            gpu_usage=gpu_usage,
            memory_usage=memory_usage,
        )
    )
