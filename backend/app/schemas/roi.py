"""ROI Pydantic Schemas

感兴趣区域相关的请求/响应数据模型。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Point(BaseModel):
    """多边形顶点"""
    x: float = Field(..., description="X 坐标")
    y: float = Field(..., description="Y 坐标")

    @field_validator("x", "y")
    @classmethod
    def validate_coordinate(cls, v: float) -> float:
        """验证坐标值为非负数"""
        if v < 0:
            raise ValueError("坐标值不能为负数")
        return v


class DensityThresholds(BaseModel):
    """密度阈值配置
    
    密度等级分类：
    - LOW: density < low
    - MEDIUM: low <= density < medium
    - HIGH: density >= medium
    """
    low: float = Field(0.3, ge=0.0, le=1.0, description="低密度阈值")
    medium: float = Field(0.6, ge=0.0, le=1.0, description="中密度阈值")
    high: float = Field(0.8, ge=0.0, le=1.0, description="高密度阈值（预留）")

    @model_validator(mode="after")
    def validate_thresholds_order(self) -> "DensityThresholds":
        """验证阈值顺序：low < medium < high"""
        if not (self.low < self.medium < self.high):
            raise ValueError("阈值必须满足 low < medium < high")
        return self


class ROIBase(BaseModel):
    """ROI 基础 Schema"""
    name: str = Field(..., min_length=1, max_length=255, description="区域名称")
    points: list[Point] = Field(..., min_length=3, description="多边形顶点列表（至少3个点）")
    density_thresholds: DensityThresholds = Field(
        default_factory=DensityThresholds,
        description="密度阈值配置"
    )

    @field_validator("points")
    @classmethod
    def validate_polygon(cls, v: list[Point]) -> list[Point]:
        """验证多边形有效性"""
        if len(v) < 3:
            raise ValueError("多边形至少需要3个顶点")
        return v


class ROICreate(ROIBase):
    """创建 ROI 请求 Schema"""
    pass


class ROIUpdate(BaseModel):
    """更新 ROI 请求 Schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="区域名称")
    points: Optional[list[Point]] = Field(None, min_length=3, description="多边形顶点列表")
    density_thresholds: Optional[DensityThresholds] = Field(None, description="密度阈值配置")

    model_config = ConfigDict(extra="forbid")

    @field_validator("points")
    @classmethod
    def validate_polygon(cls, v: Optional[list[Point]]) -> Optional[list[Point]]:
        """验证多边形有效性"""
        if v is not None and len(v) < 3:
            raise ValueError("多边形至少需要3个顶点")
        return v


class ROIResponse(ROIBase):
    """ROI 响应 Schema"""
    roi_id: str = Field(..., description="ROI 唯一标识")
    stream_id: str = Field(..., description="关联的视频流 ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    @classmethod
    def from_orm_with_conversion(cls, roi) -> "ROIResponse":
        """从 ORM 对象转换，处理 JSON 字段"""
        return cls(
            roi_id=roi.id,
            stream_id=roi.stream_id,
            name=roi.name,
            points=[Point(**p) for p in roi.points],
            density_thresholds=DensityThresholds(**roi.density_thresholds),
            created_at=roi.created_at,
            updated_at=roi.updated_at,
        )


class ROIListResponse(BaseModel):
    """ROI 列表响应 Schema"""
    rois: list[ROIResponse] = Field(..., description="ROI 列表")
    total: int = Field(..., description="总数")
