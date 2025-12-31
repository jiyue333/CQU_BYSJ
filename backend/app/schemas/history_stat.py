"""HistoryStat Pydantic Schemas

历史统计相关的请求/响应数据模型。
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.detection import DensityLevel, RegionStat


class AggregationGranularity(str, Enum):
    """聚合粒度枚举"""
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"


class HistoryStatBase(BaseModel):
    """历史统计基础 Schema"""
    total_count: int = Field(..., ge=0, description="总人数")
    region_stats: list[RegionStat] = Field(default_factory=list, description="各区域统计")


class HistoryStatCreate(HistoryStatBase):
    """创建历史统计请求 Schema"""
    stream_id: str = Field(..., description="视频流 ID")
    timestamp: datetime = Field(..., description="检测时间戳")


class HistoryStatResponse(HistoryStatBase):
    """历史统计响应 Schema"""
    id: int = Field(..., description="记录 ID")
    stream_id: str = Field(..., description="视频流 ID")
    timestamp: datetime = Field(..., description="检测时间戳")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_conversion(cls, stat) -> "HistoryStatResponse":
        """从 ORM 对象转换，处理 JSON 字段"""
        region_stats = [
            RegionStat(
                region_id=r["region_id"],
                region_name=r["region_name"],
                count=r["count"],
                density=r["density"],
                level=DensityLevel(r["level"]),
            )
            for r in (stat.region_stats or [])
        ]
        return cls(
            id=stat.id,
            stream_id=stat.stream_id,
            timestamp=stat.timestamp,
            total_count=stat.total_count,
            region_stats=region_stats,
        )


class HistoryQueryParams(BaseModel):
    """历史数据查询参数 Schema"""
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    granularity: AggregationGranularity = Field(
        AggregationGranularity.MINUTE,
        description="聚合粒度"
    )
    limit: int = Field(100, ge=1, le=1000, description="返回记录数限制")
    offset: int = Field(0, ge=0, description="偏移量")

    @field_validator("end_time")
    @classmethod
    def validate_time_range(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """验证时间范围有效性"""
        start_time = info.data.get("start_time")
        if v is not None and start_time is not None:
            if v < start_time:
                raise ValueError("end_time 必须大于等于 start_time")
        return v


class HistoryListResponse(BaseModel):
    """历史统计列表响应 Schema"""
    stats: list[HistoryStatResponse] = Field(..., description="统计记录列表")
    total: int = Field(..., description="总记录数")
    has_more: bool = Field(..., description="是否有更多数据")


class AggregatedStat(BaseModel):
    """聚合统计结果 Schema"""
    timestamp: datetime = Field(..., description="时间点")
    avg_count: float = Field(..., description="平均人数")
    max_count: int = Field(..., description="最大人数")
    min_count: int = Field(..., description="最小人数")
    sample_count: int = Field(..., description="样本数量")


class AggregatedHistoryResponse(BaseModel):
    """聚合历史数据响应 Schema"""
    stream_id: str = Field(..., description="视频流 ID")
    granularity: AggregationGranularity = Field(..., description="聚合粒度")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    data: list[AggregatedStat] = Field(..., description="聚合数据列表")
