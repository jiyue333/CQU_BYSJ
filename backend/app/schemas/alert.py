"""Alert 相关 Pydantic Schemas"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AlertThresholdType(str, Enum):
    """告警阈值类型"""
    COUNT = "count"
    DENSITY = "density"


class AlertLevel(str, Enum):
    """告警等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AlertRuleBase(BaseModel):
    """告警规则基础 Schema"""
    stream_id: str = Field(..., description="关联的视频流 ID")
    roi_id: Optional[str] = Field(None, description="关联 ROI ID（为空表示全局规则）")
    threshold_type: AlertThresholdType = Field(..., description="阈值类型")
    threshold_value: Optional[float] = Field(
        None,
        ge=0.0,
        description="阈值值（为空时使用 ROI 默认阈值）"
    )
    level: AlertLevel = Field(AlertLevel.MEDIUM, description="告警等级")
    min_duration_sec: int = Field(3, ge=0, description="持续时长阈值（秒）")
    cooldown_sec: int = Field(60, ge=0, description="冷却期（秒）")
    enabled: bool = Field(True, description="是否启用")


class AlertRuleCreate(AlertRuleBase):
    """创建告警规则请求"""
    pass


class AlertRuleUpdate(BaseModel):
    """更新告警规则请求"""
    roi_id: Optional[str] = Field(None, description="关联 ROI ID")
    threshold_type: Optional[AlertThresholdType] = Field(None, description="阈值类型")
    threshold_value: Optional[float] = Field(None, ge=0.0, description="阈值值")
    level: Optional[AlertLevel] = Field(None, description="告警等级")
    min_duration_sec: Optional[int] = Field(None, ge=0, description="持续时长阈值（秒）")
    cooldown_sec: Optional[int] = Field(None, ge=0, description="冷却期（秒）")
    enabled: Optional[bool] = Field(None, description="是否启用")

    model_config = ConfigDict(extra="forbid")


class AlertRuleResponse(AlertRuleBase):
    """告警规则响应"""
    id: str = Field(..., description="告警规则 ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(from_attributes=True)


class AlertRuleListResponse(BaseModel):
    """告警规则列表响应"""
    rules: list[AlertRuleResponse] = Field(..., description="规则列表")
    total: int = Field(..., description="总数")


class AlertEventResponse(BaseModel):
    """告警事件响应"""
    id: str = Field(..., description="告警事件 ID")
    rule_id: Optional[str] = Field(None, description="关联告警规则 ID")
    stream_id: str = Field(..., description="视频流 ID")
    roi_id: Optional[str] = Field(None, description="ROI ID")
    level: AlertLevel = Field(..., description="告警等级")
    start_ts: float = Field(..., description="开始时间戳")
    end_ts: Optional[float] = Field(None, description="结束时间戳")
    peak_density: float = Field(..., description="峰值密度")
    count_peak: int = Field(..., description="峰值人数")
    message: Optional[str] = Field(None, description="告警描述")
    acknowledged: bool = Field(False, description="是否已确认")

    @classmethod
    def from_orm_with_conversion(cls, event) -> "AlertEventResponse":
        """从 ORM 对象转换，处理时间戳"""
        return cls(
            id=event.id,
            rule_id=event.rule_id,
            stream_id=event.stream_id,
            roi_id=event.roi_id,
            level=event.level,
            start_ts=event.start_ts.timestamp(),
            end_ts=event.end_ts.timestamp() if event.end_ts else None,
            peak_density=event.peak_density,
            count_peak=event.count_peak,
            message=event.message,
            acknowledged=event.acknowledged,
        )


class AlertEventListResponse(BaseModel):
    """告警事件列表响应"""
    events: list[AlertEventResponse] = Field(..., description="事件列表")
    total: int = Field(..., description="总数")
