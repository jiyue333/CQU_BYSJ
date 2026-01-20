"""
数据源 Schema

VideoSource 相关的请求/响应模型
"""

from typing import Optional

from pydantic import BaseModel, Field


class VideoSourceCreate(BaseModel):
    """视频文件上传响应（文件通过 multipart 上传）"""

    pass  # 文件上传不需要 JSON body


class StreamCreate(BaseModel):
    """摄像头/推流接入请求"""

    url: str = Field(..., description="流地址 (rtsp/rtmp/http)")
    name: str = Field(..., description="数据源名称")


class VideoSourceResponse(BaseModel):
    """数据源响应"""

    source_id: str = Field(..., description="数据源 ID")
    name: str = Field(..., description="数据源名称")
    source_type: str = Field(..., description="类型: file / stream")
    status: str = Field(default="ready", description="状态: ready/running/stopped/error")
    file_path: Optional[str] = Field(default=None, description="文件路径")
    stream_url: Optional[str] = Field(default=None, description="流地址")
    video_width: Optional[int] = Field(default=None, description="视频宽度")
    video_height: Optional[int] = Field(default=None, description="视频高度")
    video_fps: Optional[float] = Field(default=None, description="帧率")
    total_frames: Optional[int] = Field(default=None, description="总帧数")
    created_at: str = Field(..., description="创建时间")

    model_config = {"from_attributes": True}


class VideoSourceListResponse(BaseModel):
    """数据源列表响应"""

    sources: list[VideoSourceResponse] = Field(default_factory=list)
