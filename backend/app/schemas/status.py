"""
系统状态 Schema

Status 相关的响应模型
"""

from typing import Optional

from pydantic import BaseModel, Field


class SystemStatusResponse(BaseModel):
    """系统状态响应"""

    status: str = Field(..., description="系统状态: running/stopped")
    uptime: int = Field(..., description="运行时长(秒)")
    active_sources: int = Field(default=0, description="活跃数据源数量")
    gpu_usage: Optional[float] = Field(default=None, description="GPU 使用率")
    memory_usage: Optional[float] = Field(default=None, description="内存使用率")
