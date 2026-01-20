"""
分析控制 Schema

Analysis 相关的请求/响应模型
"""

from typing import Optional

from pydantic import BaseModel, Field


class AnalysisStartRequest(BaseModel):
    """开始分析请求"""

    source_id: str = Field(..., description="数据源 ID")


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
