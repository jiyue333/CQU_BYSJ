"""
历史数据 Schema

History 相关的请求/响应模型
"""

from typing import Optional

from pydantic import BaseModel, Field


class HistoryQuery(BaseModel):
    """历史查询参数"""

    source_id: str = Field(..., description="数据源 ID")
    from_time: str = Field(..., alias="from", description="开始时间 (ISO 8601)")
    to_time: str = Field(..., alias="to", description="结束时间 (ISO 8601)")
    interval: str = Field(default="1m", description="聚合间隔: 1m / 5m / 1h")

    model_config = {"populate_by_name": True}


class HistorySeriesItem(BaseModel):
    """历史趋势数据点"""

    time: str = Field(..., description="时间戳")
    total_count: int = Field(..., description="总人数")
    total_density: float = Field(..., description="总密度")


class HistoryResponse(BaseModel):
    """历史趋势响应"""

    series: list[HistorySeriesItem] = Field(default_factory=list)
