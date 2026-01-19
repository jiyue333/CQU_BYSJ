# Video 服务模块

from app.utils import encode_image_to_base64 as encode_frame

from .video_service import (
    SaveResult,
    SourceType,
    VideoInfo,
    VideoService,
)

__all__ = [
    "VideoService",
    "VideoInfo",
    "SourceType",
    "SaveResult",
    "encode_frame",
]
