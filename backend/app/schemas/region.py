"""
区域 Schema

Region 相关的请求/响应模型
"""

from typing import Optional

from pydantic import BaseModel, Field


class RegionCreate(BaseModel):
    """创建区域请求"""

    source_id: str = Field(..., description="所属数据源 ID")
    name: str = Field(..., description="区域名称")
    points: list[list[float]] = Field(..., description="多边形顶点坐标 [[x1,y1], [x2,y2], ...]")
    color: str = Field(default="#FF5733", description="区域颜色 (Hex)")


class RegionUpdate(BaseModel):
    """更新区域请求"""

    name: Optional[str] = Field(default=None, description="区域名称")
    points: Optional[list[list[float]]] = Field(default=None, description="多边形顶点坐标")
    color: Optional[str] = Field(default=None, description="区域颜色")


class RegionResponse(BaseModel):
    """区域响应"""

    region_id: str = Field(..., description="区域 ID")
    source_id: str = Field(..., description="所属数据源 ID")
    name: str = Field(..., description="区域名称")
    points: list[list[float]] = Field(..., description="多边形顶点坐标")
    color: str = Field(..., description="区域颜色")

    model_config = {"from_attributes": True}


class RegionListResponse(BaseModel):
    """区域列表响应"""

    regions: list[RegionResponse] = Field(default_factory=list)
