"""
通用工具函数
"""

import base64
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np


def ensure_dir(path: str | Path) -> Path:
    """确保目录存在，返回 Path 对象"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def format_timestamp(dt: datetime | None = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化时间戳"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime(fmt)


def generate_filename(prefix: str = "", suffix: str = "", ext: str = ".mp4") -> str:
    """生成带时间戳的文件名"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    parts = [p for p in [prefix, timestamp, suffix] if p]
    return "_".join(parts) + ext


def is_valid_video_file(filename: str) -> bool:
    """检查是否为有效的视频文件扩展名"""
    valid_extensions = {".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm"}
    return Path(filename).suffix.lower() in valid_extensions


def is_stream_url(url: str) -> bool:
    """检查是否为流地址"""
    return url.startswith(("rtsp://", "rtmp://", "http://", "https://"))


def encode_image_to_base64(
    image: np.ndarray, format: str = ".jpg", quality: int = 80
) -> str:
    """
    将图像编码为 base64 字符串

    Args:
        image: BGR 图像 (numpy array)
        format: 图像格式 (.jpg, .png)
        quality: JPEG 压缩质量 (1-100)

    Returns:
        base64 编码的图像字符串
    """
    params = []
    if format.lower() in [".jpg", ".jpeg"]:
        params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    elif format.lower() == ".png":
        params = [cv2.IMWRITE_PNG_COMPRESSION, 9 - quality // 12]

    _, buffer = cv2.imencode(format, image, params)
    return base64.b64encode(buffer).decode("utf-8")


def decode_base64_to_image(base64_str: str) -> np.ndarray:
    """
    将 base64 字符串解码为图像

    Args:
        base64_str: base64 编码的图像

    Returns:
        BGR 图像 (numpy array)
    """
    img_data = base64.b64decode(base64_str)
    img_array = np.frombuffer(img_data, dtype=np.uint8)
    return cv2.imdecode(img_array, cv2.IMREAD_COLOR)


def calculate_polygon_area(polygon: list[tuple[float, float]]) -> float:
    """
    计算多边形面积（鞋带公式）

    Args:
        polygon: 多边形顶点 [(x1,y1), (x2,y2), ...]

    Returns:
        面积（平方像素）
    """
    n = len(polygon)
    if n < 3:
        return 0.0

    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += polygon[i][0] * polygon[j][1]
        area -= polygon[j][0] * polygon[i][1]

    return abs(area) / 2.0


def calculate_density(count: int, area_m2: float, max_value: float = 20.0) -> float:
    """
    计算人群密度（物理密度）

    公式: density = count / area_m2
    结果范围: 0 ~ max_value
    单位: 人/m²

    Args:
        count: 区域内人数
        area_m2: 区域物理面积（平方米），由 VLM 估算
        max_value: 密度上限，默认 20.0（20人/m² 已是极端拥挤）

    Returns:
        密度值（人/m²，0 ~ max_value）
    """
    if area_m2 <= 0:
        return 0.0
    density = count / area_m2
    return min(round(density, 2), max_value)
