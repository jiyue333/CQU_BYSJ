"""VideoStream Pydantic Schemas

视频流相关的请求/响应数据模型。
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.video_stream import StreamStatus, StreamType


# UUID v4 正则表达式（支持带扩展名的格式，如 xxx.mp4）
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(\.[a-z0-9]+)?$",
    re.IGNORECASE
)


class VideoStreamBase(BaseModel):
    """视频流基础 Schema"""
    name: str = Field(..., min_length=1, max_length=255, description="显示名称")


class VideoStreamCreate(VideoStreamBase):
    """创建视频流请求 Schema
    
    根据 type 不同，需要提供不同的字段：
    - file: 需要 file_id，source_url 必须为空
    - webcam: file_id 和 source_url 都必须为空
    - rtsp: 需要 source_url (RTSP 地址)，file_id 必须为空
    """
    type: StreamType = Field(..., description="视频流类型")
    source_url: Optional[str] = Field(
        None, 
        max_length=512,
        description="RTSP 地址（仅 rtsp 类型需要）"
    )
    file_id: Optional[str] = Field(
        None,
        max_length=50,
        description="文件 ID（仅 file 类型需要，格式：UUID.扩展名）"
    )

    @field_validator("source_url")
    @classmethod
    def validate_source_url_format(cls, v: Optional[str]) -> Optional[str]:
        """验证 RTSP 地址格式"""
        if v is not None:
            if not v.startswith(("rtsp://", "rtsps://")):
                raise ValueError("source_url 必须是有效的 RTSP 地址（以 rtsp:// 或 rtsps:// 开头）")
            # 基本 URL 结构验证
            if len(v) < 10:  # rtsp://x 最短
                raise ValueError("source_url 格式无效")
        return v

    @field_validator("file_id")
    @classmethod
    def validate_file_id_format(cls, v: Optional[str]) -> Optional[str]:
        """验证文件 ID 格式（UUID v4，可带扩展名如 xxx.mp4）"""
        if v is not None:
            if not UUID_PATTERN.match(v):
                raise ValueError("file_id 必须是有效的 UUID v4 格式（可带扩展名，如 xxx-xxx.mp4）")
        return v

    @model_validator(mode="after")
    def validate_type_dependencies(self) -> "VideoStreamCreate":
        """验证 type 与 file_id/source_url 的依赖关系"""
        if self.type == StreamType.FILE:
            if not self.file_id:
                raise ValueError("FILE 类型必须提供 file_id")
            if self.source_url:
                raise ValueError("FILE 类型不能提供 source_url")
        elif self.type == StreamType.RTSP:
            if not self.source_url:
                raise ValueError("RTSP 类型必须提供 source_url")
            if self.file_id:
                raise ValueError("RTSP 类型不能提供 file_id")
        elif self.type == StreamType.WEBCAM:
            if self.file_id:
                raise ValueError("WEBCAM 类型不能提供 file_id")
            if self.source_url:
                raise ValueError("WEBCAM 类型不能提供 source_url")
        return self


class VideoStreamUpdate(BaseModel):
    """更新视频流请求 Schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="显示名称")
    status: Optional[StreamStatus] = Field(None, description="状态")

    model_config = ConfigDict(extra="forbid")


class VideoStreamStart(BaseModel):
    """启动视频流请求 Schema
    
    方案 F：默认启用渲染，无需额外参数。
    保留此类用于未来扩展（如指定渲染参数）。
    """
    pass


class IceServer(BaseModel):
    """ICE 服务器配置"""
    urls: list[str] = Field(..., description="STUN/TURN 服务器地址列表")
    username: Optional[str] = Field(None, description="用户名（TURN 需要）")
    credential: Optional[str] = Field(None, description="密码（TURN 需要）")


class PublishInfo(BaseModel):
    """浏览器摄像头推流信息（webcam ingest 必需）"""
    whip_url: str = Field(..., description="WHIP 推流地址")
    token: str = Field(..., description="短期有效 token")
    expires_at: int = Field(..., description="token 过期时间戳（epoch）")
    ice_servers: list[IceServer] = Field(default_factory=list, description="STUN/TURN 服务器列表")


class VideoStreamResponse(VideoStreamBase):
    """视频流响应 Schema"""
    id: str = Field(..., alias="stream_id", description="视频流唯一标识")
    type: StreamType = Field(..., description="视频流类型")
    status: StreamStatus = Field(..., description="当前状态")
    play_url: Optional[str] = Field(None, description="播放地址 (HLS)")
    webrtc_url: Optional[str] = Field(None, description="WebRTC 播放地址")
    source_url: Optional[str] = Field(None, description="RTSP 地址")
    file_id: Optional[str] = Field(None, description="文件 ID")
    publish_info: Optional[PublishInfo] = Field(None, description="推流信息（仅 webcam 类型）")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class VideoStreamListResponse(BaseModel):
    """视频流列表响应 Schema"""
    streams: list[VideoStreamResponse] = Field(..., description="视频流列表")
    total: int = Field(..., description="总数")
