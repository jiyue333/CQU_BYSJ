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


class RegionHistoryStats(BaseModel):
    """区域历史统计"""

    total_count_avg: float = Field(..., description="平均人数")
    total_count_max: int = Field(..., description="最大人数")
    total_count_min: int = Field(..., description="最小人数")
    total_density_avg: float = Field(..., description="平均密度")


class CrossLineHistoryStats(BaseModel):
    """计数线历史统计"""

    name: str = Field(..., description="计数线名称")
    in_total: int = Field(default=0, description="累计进入")
    out_total: int = Field(default=0, description="累计离开")


class HistorySeriesItem(BaseModel):
    """历史趋势数据点"""

    time: str = Field(..., description="时间戳")
    total_count_avg: float = Field(..., description="平均人数")
    total_count_max: int = Field(..., description="最大人数")
    total_count_min: int = Field(..., description="最小人数")
    total_density_avg: float = Field(..., description="平均密度")
    crossline_in_total: int = Field(default=0, description="计数线累计进入")
    crossline_out_total: int = Field(default=0, description="计数线累计离开")
    crossline_stats: dict[str, CrossLineHistoryStats] = Field(default_factory=dict, description="各计数线统计")
    regions: dict[str, RegionHistoryStats] = Field(default_factory=dict, description="各区域统计")


class HistoryResponse(BaseModel):
    """历史趋势响应"""

    series: list[HistorySeriesItem] = Field(default_factory=list)
