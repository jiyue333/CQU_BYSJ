"""ROI 管理 REST API

提供 ROI（感兴趣区域）的 CRUD 操作接口。
ROI 用于定义监控区域和密度阈值，支持多边形区域定义。

Requirements: 3.1, 3.2, 3.5
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger, log_error, log_info

logger = get_logger(__name__)
from app.models.roi import ROI
from app.models.video_stream import VideoStream
from app.schemas.roi import (
    ROICreate,
    ROIListResponse,
    ROIResponse,
    ROIUpdate,
)

router = APIRouter()


async def _get_stream_or_404(db: AsyncSession, stream_id: str) -> VideoStream:
    """获取视频流，不存在则抛出 404"""
    result = await db.execute(
        select(VideoStream).where(VideoStream.id == stream_id)
    )
    stream = result.scalar_one_or_none()
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )
    return stream


async def _get_roi_or_404(db: AsyncSession, stream_id: str, roi_id: str) -> ROI:
    """获取 ROI，不存在则抛出 404"""
    result = await db.execute(
        select(ROI).where(ROI.id == roi_id, ROI.stream_id == stream_id)
    )
    roi = result.scalar_one_or_none()
    if not roi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ROI {roi_id} not found in stream {stream_id}"
        )
    return roi


def _roi_to_response(roi: ROI) -> ROIResponse:
    """将 ROI 模型转换为响应 Schema"""
    return ROIResponse.from_orm_with_conversion(roi)


@router.post(
    "/{stream_id}/rois",
    response_model=ROIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建 ROI",
    description="在指定视频流上创建新的感兴趣区域（ROI）。"
)
async def create_roi(
    stream_id: str,
    data: ROICreate,
    db: AsyncSession = Depends(get_db),
) -> ROIResponse:
    """创建 ROI
    
    在指定视频流上创建新的感兴趣区域。
    ROI 定义了监控区域的多边形边界和密度阈值配置。
    
    Requirements: 3.1
    """
    # 验证视频流存在
    await _get_stream_or_404(db, stream_id)
    
    log_info(logger, "Creating ROI", stream_id=stream_id, roi_name=data.name)
    
    # 创建 ROI
    roi = ROI(
        id=str(uuid.uuid4()),
        stream_id=stream_id,
        name=data.name,
        points=[{"x": p.x, "y": p.y} for p in data.points],
        density_thresholds={
            "low": data.density_thresholds.low,
            "medium": data.density_thresholds.medium,
            "high": data.density_thresholds.high,
        },
    )
    
    db.add(roi)
    await db.commit()
    await db.refresh(roi)
    
    log_info(logger, "ROI created", stream_id=stream_id, roi_id=roi.id)
    return _roi_to_response(roi)


@router.get(
    "/{stream_id}/rois",
    response_model=ROIListResponse,
    summary="获取 ROI 列表",
    description="获取指定视频流的所有 ROI 列表。"
)
async def list_rois(
    stream_id: str,
    db: AsyncSession = Depends(get_db),
) -> ROIListResponse:
    """获取 ROI 列表
    
    获取指定视频流的所有感兴趣区域列表，按创建时间排序。
    
    Requirements: 3.2
    """
    # 验证视频流存在
    await _get_stream_or_404(db, stream_id)
    
    # 查询 ROI 列表
    result = await db.execute(
        select(ROI)
        .where(ROI.stream_id == stream_id)
        .order_by(ROI.created_at)
    )
    rois = result.scalars().all()
    
    return ROIListResponse(
        rois=[_roi_to_response(roi) for roi in rois],
        total=len(rois)
    )


@router.get(
    "/{stream_id}/rois/{roi_id}",
    response_model=ROIResponse,
    summary="获取 ROI 详情",
    description="获取指定 ROI 的详细信息。"
)
async def get_roi(
    stream_id: str,
    roi_id: str,
    db: AsyncSession = Depends(get_db),
) -> ROIResponse:
    """获取 ROI 详情
    
    获取指定感兴趣区域的详细信息，包括多边形顶点和密度阈值配置。
    """
    roi = await _get_roi_or_404(db, stream_id, roi_id)
    return _roi_to_response(roi)


@router.put(
    "/{stream_id}/rois/{roi_id}",
    response_model=ROIResponse,
    summary="更新 ROI",
    description="更新指定 ROI 的配置。支持部分更新。"
)
async def update_roi(
    stream_id: str,
    roi_id: str,
    data: ROIUpdate,
    db: AsyncSession = Depends(get_db),
) -> ROIResponse:
    """更新 ROI
    
    更新指定感兴趣区域的配置。支持部分更新，只更新提供的字段。
    配置变更后立即生效。
    
    Requirements: 3.5
    """
    roi = await _get_roi_or_404(db, stream_id, roi_id)
    
    log_info(logger, "Updating ROI", stream_id=stream_id, roi_id=roi_id)
    
    # 部分更新
    if data.name is not None:
        roi.name = data.name
    
    if data.points is not None:
        roi.points = [{"x": p.x, "y": p.y} for p in data.points]
    
    if data.density_thresholds is not None:
        roi.density_thresholds = {
            "low": data.density_thresholds.low,
            "medium": data.density_thresholds.medium,
            "high": data.density_thresholds.high,
        }
    
    await db.commit()
    await db.refresh(roi)
    
    log_info(logger, "ROI updated", stream_id=stream_id, roi_id=roi_id)
    return _roi_to_response(roi)


@router.delete(
    "/{stream_id}/rois/{roi_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除 ROI",
    description="删除指定的 ROI。"
)
async def delete_roi(
    stream_id: str,
    roi_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """删除 ROI
    
    删除指定的感兴趣区域。删除后，该区域的密度统计将不再计算。
    
    Requirements: 3.2
    """
    roi = await _get_roi_or_404(db, stream_id, roi_id)
    
    log_info(logger, "Deleting ROI", stream_id=stream_id, roi_id=roi_id)
    
    await db.delete(roi)
    await db.commit()
    
    log_info(logger, "ROI deleted", stream_id=stream_id, roi_id=roi_id)
