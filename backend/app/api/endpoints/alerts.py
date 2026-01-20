"""
告警配置 API

处理告警阈值配置的获取和更新
"""

import uuid
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.logger import logger
from app.models import AlertConfig
from app.repositories import AlertConfigRepository, VideoSourceRepository
from app.schemas.common import ApiResponse, OkResponse
from app.schemas.alert import (
    AlertThresholdGet,
    AlertThresholdUpdate,
    RegionThreshold,
)

router = APIRouter(prefix="/alerts", tags=["告警配置"])


@router.get("/threshold", response_model=ApiResponse[AlertThresholdGet])
async def get_threshold(
    source_id: str = Query(..., description="数据源 ID"),
    db: Session = Depends(get_db),
):
    """获取当前阈值配置"""
    # 验证数据源存在
    source_repo = VideoSourceRepository(db)
    if not source_repo.get_by_id(source_id):
        raise HTTPException(status_code=404, detail="数据源不存在")

    config_repo = AlertConfigRepository(db)
    config = config_repo.get_by_source_id(source_id)

    if config:
        # 解析区域阈值
        region_thresholds = {}
        if config.region_thresholds:
            raw = json.loads(config.region_thresholds) if isinstance(config.region_thresholds, str) else config.region_thresholds
            for name, values in raw.items():
                region_thresholds[name] = RegionThreshold(**values)

        return ApiResponse.success(
            data=AlertThresholdGet(
                total_warning_threshold=config.total_warning_threshold,
                total_critical_threshold=config.total_critical_threshold,
                default_region_warning=config.default_region_warning,
                default_region_critical=config.default_region_critical,
                region_thresholds=region_thresholds,
                cooldown_seconds=config.cooldown_seconds,
            )
        )
    else:
        # 返回默认配置
        return ApiResponse.success(
            data=AlertThresholdGet(
                total_warning_threshold=settings.ALERT_TOTAL_WARNING,
                total_critical_threshold=settings.ALERT_TOTAL_CRITICAL,
                default_region_warning=20,
                default_region_critical=50,
                region_thresholds={},
                cooldown_seconds=settings.ALERT_COOLDOWN_SECONDS,
            )
        )


@router.post("/threshold", response_model=ApiResponse[OkResponse])
async def update_threshold(
    request: AlertThresholdUpdate,
    db: Session = Depends(get_db),
):
    """更新阈值配置"""
    # 验证数据源存在
    source_repo = VideoSourceRepository(db)
    if not source_repo.get_by_id(request.source_id):
        raise HTTPException(status_code=404, detail="数据源不存在")

    config_repo = AlertConfigRepository(db)
    config = config_repo.get_by_source_id(request.source_id)

    # 构建更新参数
    update_data = {}
    if request.total_warning_threshold is not None:
        update_data["total_warning_threshold"] = request.total_warning_threshold
    if request.total_critical_threshold is not None:
        update_data["total_critical_threshold"] = request.total_critical_threshold
    if request.default_region_warning is not None:
        update_data["default_region_warning"] = request.default_region_warning
    if request.default_region_critical is not None:
        update_data["default_region_critical"] = request.default_region_critical
    if request.region_thresholds is not None:
        # 转换为 JSON 存储
        region_dict = {name: t.model_dump() for name, t in request.region_thresholds.items()}
        update_data["region_thresholds"] = json.dumps(region_dict)
    if request.cooldown_seconds is not None:
        update_data["cooldown_seconds"] = request.cooldown_seconds

    if config:
        config_repo.update(config, **update_data)
    else:
        # 创建新配置
        new_config = AlertConfig(
            config_id=str(uuid.uuid4()),
            source_id=request.source_id,
            total_warning_threshold=request.total_warning_threshold or settings.ALERT_TOTAL_WARNING,
            total_critical_threshold=request.total_critical_threshold or settings.ALERT_TOTAL_CRITICAL,
            default_region_warning=request.default_region_warning or 20,
            default_region_critical=request.default_region_critical or 50,
            region_thresholds=update_data.get("region_thresholds"),
            cooldown_seconds=request.cooldown_seconds or settings.ALERT_COOLDOWN_SECONDS,
        )
        config_repo.create(new_config)

    logger.info(f"告警配置已更新: {request.source_id}")

    return ApiResponse.success(data=OkResponse(ok=True))
