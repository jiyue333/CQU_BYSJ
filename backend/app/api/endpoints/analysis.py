"""
分析控制 API

处理分析任务的启动、停止和状态查询
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.logger import logger
from app.models import VideoSource, Region, AlertConfig
from app.repositories import VideoSourceRepository, RegionRepository, AlertConfigRepository
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

    # 保存区域配置
    region_repo = RegionRepository(db)
    for region_config in request.regions:
        import json
        region = Region(
            region_id=str(uuid.uuid4()),
            source_id=request.source_id,
            name=region_config.name,
            points=json.dumps(region_config.points),
            color=region_config.color,
        )
        region_repo.create(region)

    # 保存告警配置
    if request.threshold:
        config_repo = AlertConfigRepository(db)
        existing_config = config_repo.get_by_source_id(request.source_id)
        if existing_config:
            config_repo.update(
                existing_config,
                total_warning_threshold=request.threshold.total_warning_threshold,
                total_critical_threshold=request.threshold.total_critical_threshold,
                default_region_warning=request.threshold.default_region_warning,
                default_region_critical=request.threshold.default_region_critical,
            )
        else:
            config = AlertConfig(
                config_id=str(uuid.uuid4()),
                source_id=request.source_id,
                total_warning_threshold=request.threshold.total_warning_threshold,
                total_critical_threshold=request.threshold.total_critical_threshold,
                default_region_warning=request.threshold.default_region_warning,
                default_region_critical=request.threshold.default_region_critical,
            )
            config_repo.create(config)

    # 更新数据源状态
    source_repo.update_status(request.source_id, "running")

    # 记录分析状态
    _analysis_state[request.source_id] = {
        "status": "running",
        "start_time": datetime.utcnow().isoformat() + "Z",
        "progress": 0.0,
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
            progress=state.get("progress"),
        )
    )
