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
from typing import Generator

import cv2
import numpy as np

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
        """逐帧迭代器"""
        if not self.cap or not self.cap.isOpened():
            raise RuntimeError("视频源未打开")

        while True:
            success, frame = self.cap.read()
            if not success:
                break
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
    def save_source(cls, source: str, file_data: bytes | None = None) -> SaveResult:
        """
        保存视频源

        Args:
            source: 视频源（文件名或流地址）
            file_data: 上传的文件数据（仅文件类型需要）

        Returns:
            SaveResult: 保存结果
        """
        source_id = str(uuid.uuid4())

        # 判断类型
        if is_stream_url(source):
            # 流地址：只保存到数据库
            result = SaveResult(
                source_id=source_id,
                source_type=SourceType.STREAM,
                original_name=source,
                file_path=None,
            )
            # TODO: 保存到数据库
            # db.save_video_source(result)
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
            # TODO: 保存到数据库
            # db.save_video_source(result)

        return result
