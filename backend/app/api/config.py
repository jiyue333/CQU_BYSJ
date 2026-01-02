"""配置管理 REST API

提供视频流配置的获取和更新接口。
Requirements: 8.1, 8.2, 8.3, 8.4
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger, log_error, log_info

logger = get_logger(__name__)
from app.models.system_config import SystemConfig
from app.models.video_stream import VideoStream
from app.schemas.system_config import (
    SystemConfigResponse,
    SystemConfigUpdate,
    ConfigPresetListResponse,
)

router = APIRouter()

# 配置预设（静态）
CONFIG_PRESETS = [
    {
        "id": "balanced",
        "name": "均衡",
        "render_fps": 24,
        "render_infer_stride": 3,
        "heatmap_decay": 0.5,
        "render_overlay_alpha": 0.4,
    },
    {
        "id": "low_latency",
        "name": "低延迟",
        "render_fps": 30,
        "render_infer_stride": 2,
        "heatmap_decay": 0.6,
        "render_overlay_alpha": 0.45,
    },
    {
        "id": "stable",
        "name": "稳态",
        "render_fps": 20,
        "render_infer_stride": 4,
        "heatmap_decay": 0.7,
        "render_overlay_alpha": 0.35,
    },
]


async def _get_or_create_config(
    db: AsyncSession, stream_id: str
) -> SystemConfig:
    """获取或创建流配置
    
    如果配置不存在，则创建默认配置。
    """
    # 先验证流是否存在
    stream_result = await db.execute(
        select(VideoStream).where(VideoStream.id == stream_id)
    )
    stream = stream_result.scalar_one_or_none()
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )
    
    # 查找配置
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.stream_id == stream_id)
    )
    config = result.scalar_one_or_none()
    
    # 如果不存在，创建默认配置
    if not config:
        config = SystemConfig(stream_id=stream_id)
        db.add(config)
        await db.commit()
        await db.refresh(config)
    
    return config


@router.get(
    "/presets",
    response_model=ConfigPresetListResponse,
    summary="获取配置预设",
    description="返回可选的配置预设列表"
)
async def list_config_presets() -> ConfigPresetListResponse:
    """获取配置预设列表"""
    return ConfigPresetListResponse(presets=CONFIG_PRESETS, total=len(CONFIG_PRESETS))


@router.get(
    "/{stream_id}",
    response_model=SystemConfigResponse,
    summary="获取流配置",
    description="获取指定视频流的配置。如果配置不存在，将创建默认配置。"
)
async def get_config(
    stream_id: str,
    db: AsyncSession = Depends(get_db),
) -> SystemConfigResponse:
    """获取流配置
    
    返回指定视频流的配置参数，包括：
    - confidence_threshold: 检测置信度阈值 (0-1)
    - inference_fps: 推理频率 (1-3)
    - heatmap_grid_size: 热力图网格大小
    - heatmap_decay: 热力图衰减因子
    """
    config = await _get_or_create_config(db, stream_id)
    return SystemConfigResponse.model_validate(config)


@router.put(
    "/{stream_id}",
    response_model=SystemConfigResponse,
    summary="更新流配置",
    description="更新指定视频流的配置。支持部分更新，只需提供要修改的字段。"
)
async def update_config(
    stream_id: str,
    data: SystemConfigUpdate,
    db: AsyncSession = Depends(get_db),
) -> SystemConfigResponse:
    """更新流配置
    
    支持部分更新，只需提供要修改的字段：
    - confidence_threshold: 检测置信度阈值 (0-1)
    - inference_fps: 推理频率 (1-3)
    - heatmap_grid_size: 热力图网格大小 (5-100)
    - heatmap_decay: 热力图衰减因子 (0-1)
    
    配置更新后会在下一次推理时生效。
    """
    config = await _get_or_create_config(db, stream_id)
    
    # 更新提供的字段
    update_data = data.model_dump(exclude_unset=True)
    
    log_info(logger, "Updating config", stream_id=stream_id, fields=list(update_data.keys()))
    
    for field, value in update_data.items():
        setattr(config, field, value)
    
    await db.commit()
    await db.refresh(config)
    
    log_info(logger, "Config updated", stream_id=stream_id)
    return SystemConfigResponse.model_validate(config)
