"""
区域配置 API

处理区域的增删改查
"""

import uuid
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logger import logger
from app.models import Region
from app.repositories import RegionRepository, VideoSourceRepository
from app.schemas.common import ApiResponse
from app.schemas.region import (
    RegionCreate,
    RegionUpdate,
    RegionResponse,
    RegionListResponse,
)

router = APIRouter(prefix="/regions", tags=["区域配置"])


def _region_to_response(region: Region) -> RegionResponse:
    """将 Region 模型转换为响应格式"""
    points = json.loads(region.points) if isinstance(region.points, str) else region.points
    return RegionResponse(
        region_id=region.region_id,
        source_id=region.source_id,
        name=region.name,
        points=points,
        color=region.color,
        count_warning=region.count_warning,
        count_critical=region.count_critical,
        density_warning=region.density_warning,
        density_critical=region.density_critical,
    )


@router.get("", response_model=ApiResponse[RegionListResponse])
async def list_regions(
    source_id: str = Query(..., description="数据源 ID"),
    db: Session = Depends(get_db),
):
    """获取区域列表"""
    # 验证数据源存在
    source_repo = VideoSourceRepository(db)
    if not source_repo.get_by_id(source_id):
        raise HTTPException(status_code=404, detail="数据源不存在")

    region_repo = RegionRepository(db)
    regions = region_repo.get_by_source_id(source_id)

    return ApiResponse.success(
        data=RegionListResponse(
            regions=[_region_to_response(r) for r in regions]
        )
    )


@router.post("", response_model=ApiResponse[RegionResponse])
async def create_region(
    request: RegionCreate,
    db: Session = Depends(get_db),
):
    """创建区域"""
    # 验证数据源存在
    source_repo = VideoSourceRepository(db)
    if not source_repo.get_by_id(request.source_id):
        raise HTTPException(status_code=404, detail="数据源不存在")

    region_repo = RegionRepository(db)
    region = Region(
        region_id=str(uuid.uuid4()),
        source_id=request.source_id,
        name=request.name,
        points=json.dumps(request.points),
        color=request.color,
        count_warning=request.count_warning,
        count_critical=request.count_critical,
        density_warning=request.density_warning,
        density_critical=request.density_critical,
    )
    region_repo.create(region)
    logger.info(f"区域已创建: {region.region_id}")

    return ApiResponse.success(data=_region_to_response(region))


@router.put("/{region_id}", response_model=ApiResponse[RegionResponse])
async def update_region(
    region_id: str,
    request: RegionUpdate,
    db: Session = Depends(get_db),
):
    """更新区域"""
    region_repo = RegionRepository(db)
    region = region_repo.get_by_id(region_id)

    if not region:
        raise HTTPException(status_code=404, detail="区域不存在")

    # 构建更新参数
    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.points is not None:
        update_data["points"] = json.dumps(request.points)
    if request.color is not None:
        update_data["color"] = request.color
    # 预警阈值更新（允许设置为 None 来清除）
    if "count_warning" in request.model_fields_set:
        update_data["count_warning"] = request.count_warning
    if "count_critical" in request.model_fields_set:
        update_data["count_critical"] = request.count_critical
    if "density_warning" in request.model_fields_set:
        update_data["density_warning"] = request.density_warning
    if "density_critical" in request.model_fields_set:
        update_data["density_critical"] = request.density_critical

    if update_data:
        region = region_repo.update(region, **update_data)
        logger.info(f"区域已更新: {region_id}")

    return ApiResponse.success(data=_region_to_response(region))


@router.delete("/{region_id}", response_model=ApiResponse)
async def delete_region(
    region_id: str,
    db: Session = Depends(get_db),
):
    """删除区域"""
    region_repo = RegionRepository(db)
    region = region_repo.get_by_id(region_id)

    if not region:
        raise HTTPException(status_code=404, detail="区域不存在")

    region_repo.delete(region_id)
    logger.info(f"区域已删除: {region_id}")

    return ApiResponse.success(msg="删除成功")
