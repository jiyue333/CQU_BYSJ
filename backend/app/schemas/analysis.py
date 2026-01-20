"""
分析控制 Schema

Analysis 相关的请求/响应模型
"""

from typing import Optional

from pydantic import BaseModel, Field


class RegionConfig(BaseModel):
    """区域配置（分析启动时）"""

    name: str = Field(..., description="区域名称")
    points: list[list[float]] = Field(..., description="多边形顶点坐标")
    color: str = Field(default="#FF5733", description="区域颜色")


class ThresholdConfig(BaseModel):
    """阈值配置"""

    total_warning_threshold: int = Field(default=50, description="总人数预警阈值")
    total_critical_threshold: int = Field(default=100, description="总人数严重阈值")
    default_region_warning: int = Field(default=20, description="区域默认预警阈值")
    default_region_critical: int = Field(default=50, description="区域默认严重阈值")


class AnalysisStartRequest(BaseModel):
    """开始分析请求"""

    source_id: str = Field(..., description="数据源 ID")
    regions: list[RegionConfig] = Field(default_factory=list, description="区域配置列表")
    threshold: Optional[ThresholdConfig] = Field(default=None, description="阈值配置")


class AnalysisStopRequest(BaseModel):
    """停止分析请求"""

    source_id: str = Field(..., description="数据源 ID")


class AnalysisStartResponse(BaseModel):
    """开始分析响应"""

    source_id: str = Field(..., description="数据源 ID")
    status: str = Field(default="running", description="状态")


class AnalysisStatusResponse(BaseModel):
    """分析状态响应"""

    source_id: str = Field(..., description="数据源 ID")
    status: str = Field(..., description="状态: ready/running/stopped/error")
    start_time: Optional[str] = Field(default=None, description="开始时间")
    progress: Optional[float] = Field(default=None, description="进度 (0-1)")
