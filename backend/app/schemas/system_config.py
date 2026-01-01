"""SystemConfig Pydantic Schemas

系统配置相关的请求/响应数据模型。
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SystemConfigBase(BaseModel):
    """系统配置基础 Schema"""
    confidence_threshold: float = Field(
        0.5, 
        ge=0.0, 
        le=1.0, 
        description="检测置信度阈值 (0-1)"
    )
    inference_fps: int = Field(
        2, 
        ge=1, 
        le=3, 
        description="推理频率 (1-3)"
    )
    heatmap_grid_size: int = Field(
        20, 
        ge=5, 
        le=100, 
        description="热力图网格大小 (5-100)"
    )
    heatmap_decay: float = Field(
        0.5, 
        ge=0.0, 
        le=1.0, 
        description="热力图衰减因子（EMA alpha, 0-1，值越大衰减越快）"
    )

    @field_validator("inference_fps")
    @classmethod
    def validate_inference_fps(cls, v: int) -> int:
        """验证推理频率在有效范围内"""
        if not 1 <= v <= 3:
            raise ValueError("推理频率必须在 1-3 范围内")
        return v


class SystemConfigCreate(SystemConfigBase):
    """创建系统配置请求 Schema"""
    pass


class SystemConfigUpdate(BaseModel):
    """更新系统配置请求 Schema"""
    confidence_threshold: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=1.0, 
        description="检测置信度阈值"
    )
    inference_fps: Optional[int] = Field(
        None, 
        ge=1, 
        le=3, 
        description="推理频率"
    )
    heatmap_grid_size: Optional[int] = Field(
        None, 
        ge=5, 
        le=100, 
        description="热力图网格大小"
    )
    heatmap_decay: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=1.0, 
        description="热力图衰减因子"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("inference_fps")
    @classmethod
    def validate_inference_fps(cls, v: Optional[int]) -> Optional[int]:
        """验证推理频率在有效范围内"""
        if v is not None and not 1 <= v <= 3:
            raise ValueError("推理频率必须在 1-3 范围内")
        return v


class SystemConfigResponse(SystemConfigBase):
    """系统配置响应 Schema"""
    id: int = Field(..., description="配置 ID")
    stream_id: str = Field(..., description="关联的视频流 ID")

    model_config = ConfigDict(from_attributes=True)


class GlobalConfigResponse(BaseModel):
    """全局系统配置响应 Schema"""
    max_concurrent_streams: int = Field(10, description="最大并发流数")
    file_max_size_mb: int = Field(500, description="单文件最大大小（MB）")
    file_retention_days: int = Field(7, description="文件保留天数")
    auto_stop_delay: int = Field(60, description="无观看者自动停止延迟（秒）")
    cooldown_duration: int = Field(60, description="COOLDOWN 持续时间（秒）")
