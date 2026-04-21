"""
计数线段配置 API

处理 cross-line 的增删改查
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logger import logger
from app.models.cross_line import CrossLine
from app.repositories.cross_line_repository import CrossLineRepository
from app.repositories.video_source_repository import VideoSourceRepository
from app.schemas.common import ApiResponse
from app.schemas.cross_line import (
    CrossLineCreate,
    CrossLineUpdate,
    CrossLineResponse,
    CrossLineListResponse,
)

router = APIRouter(prefix="/crosslines", tags=["计数线段配置"])


def _line_to_response(line: CrossLine) -> CrossLineResponse:
    return CrossLineResponse(
        line_id=line.line_id,
        source_id=line.source_id,
        name=line.name,
        start_x=line.start_x,
        start_y=line.start_y,
        end_x=line.end_x,
        end_y=line.end_y,
        direction=line.direction,
        color=line.color,
    )


@router.get("", response_model=ApiResponse[CrossLineListResponse])
async def list_crosslines(
    source_id: str = Query(..., description="数据源 ID"),
    db: Session = Depends(get_db),
):
    """获取计数线段列表"""
    source_repo = VideoSourceRepository(db)
    if not source_repo.get_by_id(source_id):
        raise HTTPException(status_code=404, detail="数据源不存在")

    repo = CrossLineRepository(db)
    lines = repo.get_by_source_id(source_id)

    return ApiResponse.success(
        data=CrossLineListResponse(lines=[_line_to_response(l) for l in lines])
    )


@router.post("", response_model=ApiResponse[CrossLineResponse])
async def create_crossline(
    request: CrossLineCreate,
    db: Session = Depends(get_db),
):
    """创建计数线段"""
    source_repo = VideoSourceRepository(db)
    if not source_repo.get_by_id(request.source_id):
        raise HTTPException(status_code=404, detail="数据源不存在")

    repo = CrossLineRepository(db)
    line = CrossLine(
        line_id=str(uuid.uuid4()),
        source_id=request.source_id,
        name=request.name,
        start_x=request.start_x,
        start_y=request.start_y,
        end_x=request.end_x,
        end_y=request.end_y,
        direction=request.direction,
        color=request.color,
    )
    repo.create(line)
    logger.info(f"计数线段已创建: {line.line_id}")

    return ApiResponse.success(data=_line_to_response(line))


@router.put("/{line_id}", response_model=ApiResponse[CrossLineResponse])
async def update_crossline(
    line_id: str,
    request: CrossLineUpdate,
    db: Session = Depends(get_db),
):
    """更新计数线段"""
    repo = CrossLineRepository(db)
    line = repo.get_by_id(line_id)
    if not line:
        raise HTTPException(status_code=404, detail="线段不存在")

    update_data = {k: v for k, v in request.model_dump(exclude_unset=True).items()}
    if update_data:
        line = repo.update(line, **update_data)
        logger.info(f"计数线段已更新: {line_id}")

    return ApiResponse.success(data=_line_to_response(line))


@router.delete("/{line_id}", response_model=ApiResponse)
async def delete_crossline(
    line_id: str,
    db: Session = Depends(get_db),
):
    """删除计数线段"""
    repo = CrossLineRepository(db)
    if not repo.get_by_id(line_id):
        raise HTTPException(status_code=404, detail="线段不存在")

    repo.delete(line_id)
    logger.info(f"计数线段已删除: {line_id}")

    return ApiResponse.success(msg="删除成功")
