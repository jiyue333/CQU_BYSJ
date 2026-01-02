"""SystemConfig Pydantic Schemas

系统配置相关的请求/响应数据模型。
方案 F 扩展：新增渲染相关配置字段。
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.roi import DensityThresholds


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
        description="推理频率 (1-3)，已废弃，保留兼容"
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
    default_density_thresholds: DensityThresholds = Field(
        default_factory=DensityThresholds,
        description="默认密度阈值配置"
    )
    # 方案 F 渲染配置
    render_fps: int = Field(
        24,
        ge=1,
        le=60,
        description="渲染输出帧率 (1-60)"
    )
    render_infer_stride: int = Field(
        3,
        ge=1,
        le=10,
        description="推理步长，每 N 帧推理一次 (1-10)"
    )
    render_overlay_alpha: float = Field(
        0.4,
        ge=0.0,
        le=1.0,
        description="热力图叠加透明度 (0-1)"
    )

    @field_validator("inference_fps")
    @classmethod
    def validate_inference_fps(cls, v: int) -> int:
        """验证推理频率在有效范围内"""
        if not 1 <= v <= 3:
            raise ValueError("推理频率必须在 1-3 范围内")
        return v
    
    @field_validator("render_infer_stride")
    @classmethod
    def validate_render_infer_stride(cls, v: int) -> int:
        """验证推理步长在有效范围内"""
        if not 1 <= v <= 10:
            raise ValueError("推理步长必须在 1-10 范围内")
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
        description="推理频率（已废弃）"
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
    default_density_thresholds: Optional[DensityThresholds] = Field(
        None,
        description="默认密度阈值配置"
    )
    # 方案 F 渲染配置
    render_fps: Optional[int] = Field(
        None,
        ge=1,
        le=60,
        description="渲染输出帧率"
    )
    render_infer_stride: Optional[int] = Field(
        None,
        ge=1,
        le=10,
        description="推理步长"
    )
    render_overlay_alpha: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="热力图叠加透明度"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("inference_fps")
    @classmethod
    def validate_inference_fps(cls, v: Optional[int]) -> Optional[int]:
        """验证推理频率在有效范围内"""
        if v is not None and not 1 <= v <= 3:
            raise ValueError("推理频率必须在 1-3 范围内")
        return v
    
    @field_validator("render_infer_stride")
    @classmethod
    def validate_render_infer_stride(cls, v: Optional[int]) -> Optional[int]:
        """验证推理步长在有效范围内"""
        if v is not None and not 1 <= v <= 10:
            raise ValueError("推理步长必须在 1-10 范围内")
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
    # 方案 F 渲染配置（全局默认值）
    render_fps: int = Field(24, description="渲染输出帧率")
    render_infer_stride: int = Field(3, description="推理步长")
    render_overlay_alpha: float = Field(0.4, description="热力图叠加透明度")
    render_max_concurrent: int = Field(2, description="最大并发渲染数")


class ConfigPreset(BaseModel):
    """配置预设"""
    id: str = Field(..., description="预设 ID")
    name: str = Field(..., description="预设名称")
    render_fps: int = Field(..., description="渲染输出帧率")
    render_infer_stride: int = Field(..., description="推理步长")
    heatmap_decay: float = Field(..., description="热力图衰减因子")
    render_overlay_alpha: float = Field(..., description="热力图透明度")


class ConfigPresetListResponse(BaseModel):
    """配置预设列表响应"""
    presets: list[ConfigPreset] = Field(..., description="预设列表")
    total: int = Field(..., description="总数")
