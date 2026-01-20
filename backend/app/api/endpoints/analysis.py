"""
分析控制 API

处理分析任务的启动、停止和状态查询
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logger import logger
from app.repositories import VideoSourceRepository
from app.schemas.common import ApiResponse, OkResponse
from app.schemas.analysis import (
    AnalysisStartRequest,
    AnalysisStopRequest,
    AnalysisStartResponse,
    AnalysisStatusResponse,
)

router = APIRouter(prefix="/analysis", tags=["分析控制"])

_analysis_state: dict[str, dict] = {}


@router.post("/start", response_model=ApiResponse[AnalysisStartResponse])
async def start_analysis(
    request: AnalysisStartRequest,
    db: Session = Depends(get_db),
):
    """开始分析"""
    source_repo = VideoSourceRepository(db)
    source = source_repo.get_by_id(request.source_id)

    if not source:
        raise HTTPException(status_code=404, detail="数据源不存在")

    if source.status == "running":
        raise HTTPException(status_code=400, detail="分析任务已在运行中")

    # 更新数据源状态
    source_repo.update_status(request.source_id, "running")

    # 记录分析状态
    _analysis_state[request.source_id] = {
        "status": "running",
        "start_time": datetime.utcnow().isoformat() + "Z",
    }

    logger.info(f"分析任务已启动: {request.source_id}")

    return ApiResponse.success(
        data=AnalysisStartResponse(source_id=request.source_id, status="running")
    )


@router.post("/stop", response_model=ApiResponse[OkResponse])
async def stop_analysis(
    request: AnalysisStopRequest,
    db: Session = Depends(get_db),
):
    """停止分析"""
    source_repo = VideoSourceRepository(db)
    source = source_repo.get_by_id(request.source_id)

    if not source:
        raise HTTPException(status_code=404, detail="数据源不存在")

    # 更新状态
    source_repo.update_status(request.source_id, "stopped")

    # 清除分析状态
    if request.source_id in _analysis_state:
        _analysis_state[request.source_id]["status"] = "stopped"

    logger.info(f"分析任务已停止: {request.source_id}")

    return ApiResponse.success(data=OkResponse(ok=True))


@router.get("/status", response_model=ApiResponse[AnalysisStatusResponse])
async def get_analysis_status(
    source_id: str = Query(..., description="数据源 ID"),
    db: Session = Depends(get_db),
):
    """查询分析状态"""
    source_repo = VideoSourceRepository(db)
    source = source_repo.get_by_id(source_id)

    if not source:
        raise HTTPException(status_code=404, detail="数据源不存在")

    state = _analysis_state.get(source_id, {})

    return ApiResponse.success(
        data=AnalysisStatusResponse(
            source_id=source_id,
            status=source.status,
            start_time=state.get("start_time"),
        )
    )
