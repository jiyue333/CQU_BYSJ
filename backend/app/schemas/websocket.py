"""
WebSocket Schema

实时推送相关的数据模型
"""

from typing import Optional

from pydantic import BaseModel, Field


class RegionRealtimeStats(BaseModel):
    """区域实时统计数据"""

    name: str = Field(..., description="区域名称")
    count: int = Field(..., description="当前人数")
    density: float = Field(..., description="当前密度")
    in_total: int = Field(default=0, description="累计进入")
    out_total: int = Field(default=0, description="累计离开")


class RealtimeFrame(BaseModel):
    """实时帧数据"""

    ts: str = Field(..., description="时间戳 (ISO 8601)")
    frame: str = Field(..., description="帧图像 (base64)")
    source_frame: str = Field(..., description="原始源帧图像 (base64)")
    total_count: int = Field(..., description="总人数 (YOLO)")
    total_density: float = Field(default=0.0, description="总密度")
    dm_count_estimate: float = Field(default=0.0, description="DM-Count 人数估计")
    regions: dict[str, RegionRealtimeStats] = Field(default_factory=dict, description="各区域统计")
    density_matrix: list[list[float]] = Field(default_factory=list, description="降采样密度矩阵 (约80x60)")


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
