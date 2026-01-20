"""
YOLO 检测服务

同时提供：
- 热力图可视化（solutions.Heatmap）
- 多区域实时人数统计（solutions.RegionCounter）
- 区域密度计算
"""

import warnings
from dataclasses import dataclass, field

import cv2
import numpy as np

# 过滤 Ultralytics "No tracks found" 警告
warnings.filterwarnings("ignore", message=".*No tracks found.*")

from ultralytics import solutions

from app.utils import calculate_density, calculate_polygon_area


@dataclass
class DetectionResult:
    """检测结果"""

    frame: np.ndarray  # 热力图叠加后的帧
    total_count: int  # 总人数
    total_density: float  # 总密度
    region_counts: dict[str, int] = field(default_factory=dict)  # 各区域人数
    region_densities: dict[str, float] = field(default_factory=dict)  # 各区域密度


class YOLOService:
    """YOLO 检测服务 - 热力图 + 区域计数 + 密度分析"""

    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        regions: dict[str, list[tuple]] | None = None,
        conf: float = 0.5,
        device: str = "cpu",
        colormap: int = cv2.COLORMAP_JET,
    ):
        """
        Args:
            model_path: 模型路径
            regions: 区域定义 {"区域名": [(x1,y1), (x2,y2), ...]}
            conf: 置信度阈值
            device: 运行设备
            colormap: 热力图 colormap
        """
        self.regions = regions or {}

        # 预计算各区域面积
        self.region_areas: dict[str, float] = {}
        for name, polygon in self.regions.items():
            self.region_areas[name] = calculate_polygon_area(polygon)

        common_args = {
            "model": model_path,
            "conf": conf,
            "device": device,
            "classes": [0],  # 只检测 person
            "show": False,
            "verbose": False,  # 关闭控制台输出
        }

        # 热力图
        self.heatmap = solutions.Heatmap(colormap=colormap, **common_args)

        # 区域计数（如果有区域定义）
        self.region_counter = None
        if regions:
            self.region_counter = solutions.RegionCounter(region=regions, **common_args)

    def process(self, frame: np.ndarray) -> DetectionResult:
        """
        处理单帧，返回热力图、区域计数和密度

        Args:
            frame: BGR 图像帧

        Returns:
            DetectionResult: 热力图帧 + 区域人数统计 + 密度
        """
        # 热力图处理
        heatmap_result = self.heatmap(frame)
        heatmap_frame = heatmap_result.plot_im

        # 区域计数处理
        total_count = 0
        region_counts = {}
        region_densities = {}

        if self.region_counter:
            region_result = self.region_counter(frame)
            total_count = region_result.total_tracks
            region_counts = region_result.region_counts

            # 计算各区域密度
            for name, count in region_counts.items():
                area = self.region_areas.get(name, 0)
                region_densities[name] = calculate_density(count, area)
        else:
            # 无区域时从热力图结果获取总人数
            if hasattr(heatmap_result, "total_tracks"):
                total_count = heatmap_result.total_tracks
        total_density = calculate_density(total_count, frame.shape[0] * frame.shape[1])

        return DetectionResult(
            frame=heatmap_frame,
            total_count=total_count,
            total_density=total_density,
            region_counts=region_counts,
            region_densities=region_densities,
        )
