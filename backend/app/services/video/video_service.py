"""
视频服务

提供：
- 视频源读取（文件、RTSP/RTMP流）
- 逐帧迭代
- 视频信息获取
- 视频源保存（文件保存 + 数据库记录）
"""

import shutil
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Generator, Optional

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.models.video_source import VideoSource
from app.repositories.video_source_repository import VideoSourceRepository
from app.utils import ensure_dir, is_stream_url


class SourceType(Enum):
    """视频源类型"""

    FILE = "file"
    STREAM = "stream"


@dataclass
class VideoInfo:
    """视频信息"""

    width: int
    height: int
    fps: float
    total_frames: int  # 流协议时为 -1


@dataclass
class SaveResult:
    """保存结果"""

    source_id: str  # 唯一标识
    source_type: SourceType
    original_name: str  # 原始名称或流地址
    file_path: str | None  # 文件保存路径（仅文件类型）


class VideoService:
    """视频服务"""

    # 视频上传目录
    UPLOAD_DIR = Path("uploads/videos")

    def __init__(self, source: str):
        """
        Args:
            source: 视频源（文件路径或流地址 rtsp://、rtmp://、http://）
        """
        self.source = source
        self.cap: cv2.VideoCapture | None = None

    @property
    def source_type(self) -> SourceType:
        """判断视频源类型"""
        if is_stream_url(self.source):
            return SourceType.STREAM
        return SourceType.FILE

    def open(self) -> bool:
        """打开视频源"""
        if self.source_type == SourceType.STREAM:
            # RTSP/RTMP: 使用 FFMPEG 后端，设置超时和缓冲
            self.cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
            self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)  # 10s 连接超时
            self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)  # 10s 读取超时
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)  # 减少缓冲延迟
        else:
            self.cap = cv2.VideoCapture(self.source)
        return self.cap.isOpened()

    def close(self) -> None:
        """关闭视频源"""
        if self.cap:
            self.cap.release()
            self.cap = None

    def get_info(self) -> VideoInfo:
        """获取视频信息"""
        if not self.cap or not self.cap.isOpened():
            raise RuntimeError("视频源未打开")

        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # 流协议无法获取总帧数
        if total_frames <= 0:
            total_frames = -1

        return VideoInfo(
            width=width,
            height=height,
            fps=fps if fps > 0 else 30.0,  # 默认 30fps
            total_frames=total_frames,
        )

    def frames(self) -> Generator[np.ndarray, None, None]:
        """逐帧迭代器（流协议自动重试）"""
        if not self.cap or not self.cap.isOpened():
            raise RuntimeError("视频源未打开")

        consecutive_failures = 0
        max_failures = 5 if self.source_type == SourceType.STREAM else 1

        while True:
            success, frame = self.cap.read()
            if not success:
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    # 流模式：尝试重连一次
                    if self.source_type == SourceType.STREAM:
                        self.cap.release()
                        self.cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
                        self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
                        self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)
                        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
                        if not self.cap.isOpened():
                            break
                        consecutive_failures = 0
                        continue
                    break
                continue
            consecutive_failures = 0
            yield frame

    def __enter__(self) -> "VideoService":
        """上下文管理器入口"""
        if not self.open():
            raise RuntimeError(f"无法打开视频源: {self.source}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器退出"""
        self.close()

    @classmethod
    def save_source(
        cls,
        source: str,
        file_data: bytes | None = None,
        db: Optional[Session] = None,
        name: Optional[str] = None,
    ) -> SaveResult:
        """
        保存视频源

        Args:
            source: 视频源（文件名或流地址）
            file_data: 上传的文件数据（仅文件类型需要）
            db: 数据库会话（可选，传入则保存到数据库）
            name: 数据源名称（可选，默认使用文件名或流地址）

        Returns:
            SaveResult: 保存结果
        """
        source_id = str(uuid.uuid4())
        source_name = name or Path(source).stem if not is_stream_url(source) else source

        # 判断类型
        if is_stream_url(source):
            # 流地址：只保存到数据库
            result = SaveResult(
                source_id=source_id,
                source_type=SourceType.STREAM,
                original_name=source,
                file_path=None,
            )

            # 保存到数据库
            if db:
                video_source = VideoSource(
                    source_id=source_id,
                    name=source_name,
                    source_type="stream",
                    status="ready",
                    stream_url=source,
                )
                repo = VideoSourceRepository(db)
                repo.create(video_source)
        else:
            # 文件：保存文件 + 数据库记录
            ensure_dir(cls.UPLOAD_DIR)

            # 生成保存路径
            suffix = Path(source).suffix or ".mp4"
            save_path = cls.UPLOAD_DIR / f"{source_id}{suffix}"

            # 保存文件
            if file_data:
                save_path.write_bytes(file_data)
            elif Path(source).exists():
                shutil.copy(source, save_path)
            else:
                raise ValueError(f"文件不存在且未提供文件数据: {source}")

            result = SaveResult(
                source_id=source_id,
                source_type=SourceType.FILE,
                original_name=source,
                file_path=str(save_path),
            )

            # 保存到数据库
            if db:
                # 获取视频信息
                video_info = None
                try:
                    with VideoService(str(save_path)) as vs:
                        video_info = vs.get_info()
                except Exception:
                    pass

                video_source = VideoSource(
                    source_id=source_id,
                    name=source_name,
                    source_type="file",
                    status="ready",
                    file_path=str(save_path),
                    video_width=video_info.width if video_info else None,
                    video_height=video_info.height if video_info else None,
                    video_fps=video_info.fps if video_info else None,
                    total_frames=video_info.total_frames if video_info else None,
                )
                repo = VideoSourceRepository(db)
                repo.create(video_source)

        return result
