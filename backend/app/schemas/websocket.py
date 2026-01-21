"""
WebSocket Schema

实时推送相关的数据模型
"""

from typing import Optional

from pydantic import BaseModel, Field


class RegionRealtimeStats(BaseModel):
    """区域实时统计数据"""

    total_count_avg: float = Field(..., description="平均人数")
    total_count_max: int = Field(..., description="最大人数")
    total_count_min: int = Field(..., description="最小人数")
    total_density_avg: float = Field(..., description="平均密度")


class RealtimeFrame(BaseModel):
    """实时帧数据"""

    ts: str = Field(..., description="时间戳 (ISO 8601)")
    frame: str = Field(..., description="帧图像 (base64)")
    total_count: int = Field(..., description="总人数")
    total_density: float = Field(..., description="总密度")
    regions: dict[str, RegionRealtimeStats] = Field(default_factory=dict, description="各区域统计")
    entry_speed: float = Field(default=0.0, description="入场速度")


class AlertMessage(BaseModel):
    """告警消息"""

    alert_id: str = Field(..., description="告警 ID")
    alert_type: str = Field(..., description="告警类型")
    level: str = Field(..., description="级别: warning/critical")
    region_id: Optional[str] = Field(default=None, description="区域 ID")
    region_name: Optional[str] = Field(default=None, description="区域名称")
    current_value: float = Field(..., description="当前值")
    threshold: float = Field(..., description="阈值")
    timestamp: str = Field(..., description="时间戳")
    message: str = Field(..., description="告警信息")
