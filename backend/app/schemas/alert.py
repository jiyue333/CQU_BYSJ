"""
告警 Schema

Alert 相关的请求/响应模型
"""

from typing import Optional

from pydantic import BaseModel, Field


class RegionThreshold(BaseModel):
    """单个区域阈值"""

    warning: int = Field(..., description="预警阈值")
    critical: int = Field(..., description="严重阈值")


class AlertThresholdGet(BaseModel):
    """获取阈值配置响应"""

    total_warning_threshold: int = Field(..., description="总人数预警阈值")
    total_critical_threshold: int = Field(..., description="总人数严重阈值")
    default_region_warning: int = Field(..., description="区域默认预警阈值")
    default_region_critical: int = Field(..., description="区域默认严重阈值")
    region_thresholds: dict[str, RegionThreshold] = Field(
        default_factory=dict, description="各区域独立阈值配置"
    )
    cooldown_seconds: int = Field(default=30, description="告警冷却时间(秒)")


class AlertThresholdUpdate(BaseModel):
    """更新阈值配置请求"""

    source_id: str = Field(..., description="数据源 ID")
    total_warning_threshold: Optional[int] = Field(default=None, description="总人数预警阈值")
    total_critical_threshold: Optional[int] = Field(default=None, description="总人数严重阈值")
    default_region_warning: Optional[int] = Field(default=None, description="区域默认预警阈值")
    default_region_critical: Optional[int] = Field(default=None, description="区域默认严重阈值")
    region_thresholds: Optional[dict[str, RegionThreshold]] = Field(
        default=None, description="各区域独立阈值配置"
    )
    cooldown_seconds: Optional[int] = Field(default=None, description="告警冷却时间")


class AlertResponse(BaseModel):
    """告警响应"""

    alert_id: str = Field(..., description="告警 ID")
    source_id: str = Field(..., description="数据源 ID")
    alert_type: str = Field(..., description="告警类型: total_count/region_count/region_density")
    level: str = Field(..., description="级别: warning/critical")
    region_name: Optional[str] = Field(default=None, description="区域名称")
    current_value: float = Field(..., description="当前值")
    threshold_value: float = Field(..., description="阈值")
    message: str = Field(..., description="告警信息")
    triggered_at: str = Field(..., description="触发时间")

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    """告警列表响应"""

    alerts: list[AlertResponse] = Field(default_factory=list)
