"""
WebSocket Schema

实时推送相关的数据模型
"""

from typing import Optional

from pydantic import BaseModel, Field


class RegionStats(BaseModel):
    """区域统计数据"""

    name: str = Field(..., description="区域名称")
    count: int = Field(..., description="区域人数")
    density: float = Field(..., description="区域密度")


class RealtimeFrame(BaseModel):
    """实时帧数据"""

    ts: str = Field(..., description="时间戳 (ISO 8601)")
    frame: str = Field(..., description="帧图像 (base64)")
    total_count: int = Field(..., description="总人数")
    total_density: float = Field(..., description="总密度")
    regions: list[RegionStats] = Field(default_factory=list, description="各区域统计")
    crowd_index: float = Field(default=0.0, description="拥挤指数")
    entry_speed: float = Field(default=0.0, description="入场速度")


class AlertMessage(BaseModel):
    """告警消息"""

    alert_id: str = Field(..., description="告警 ID")
    alert_type: str = Field(..., description="告警类型")
    level: str = Field(..., description="级别: warning/critical")
    region_name: Optional[str] = Field(default=None, description="区域名称")
    current_value: float = Field(..., description="当前值")
    threshold: float = Field(..., description="阈值")
    timestamp: str = Field(..., description="时间戳")
    message: str = Field(..., description="告警信息")
