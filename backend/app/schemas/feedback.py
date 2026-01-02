"""反馈相关 Pydantic Schemas"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FeedbackCreate(BaseModel):
    """提交反馈请求"""
    stream_id: str = Field(..., description="视频流 ID")
    message: Optional[str] = Field(None, description="反馈说明")
    payload: Optional[dict] = Field(default_factory=dict, description="反馈附加数据")


class FeedbackResponse(BaseModel):
    """反馈响应"""
    id: str = Field(..., description="反馈 ID")
    stream_id: str = Field(..., description="视频流 ID")
    message: Optional[str] = Field(None, description="反馈说明")
    payload: dict = Field(..., description="反馈附加数据")
    created_at: datetime = Field(..., description="创建时间")

    model_config = ConfigDict(from_attributes=True)
