"""
YOLO 检测服务

同时提供：
- 热力图可视化（solutions.Heatmap）
- 多区域实时人数统计（solutions.RegionCounter）
- 区域密度计算
- 区域边框和人数叠加显示
"""

import warnings
from dataclasses import dataclass, field

import cv2
import numpy as np

# 过滤 Ultralytics "No tracks found" 警告
warnings.filterwarnings("ignore", message=".*No tracks found.*")

from ultralytics import solutions

from app.utils import calculate_density, calculate_polygon_area
from app.core.config import settings


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

    # 区域边框颜色列表 (BGR)
    REGION_COLORS = [
        (246, 143, 59),   # 蓝色
        (235, 192, 91),   # 青色
        (225, 125, 47),   # 深蓝
        (111, 191, 45),   # 绿色
        (94, 106, 228),   # 红色
        (180, 130, 220),  # 粉色
    ]

    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        regions: dict[str, list[tuple]] | None = None,
        conf: float = 0.5,
        device: str = "cpu",
        colormap: int = cv2.COLORMAP_JET,
        region_line_thickness: int = 2,
    ):
        """
        Args:
            model_path: 模型路径
            regions: 区域定义 {"区域名": [(x1,y1), (x2,y2), ...]}
            conf: 置信度阈值
            device: 运行设备
            colormap: 热力图 colormap
            region_line_thickness: 区域边框线条粗细
        """
        self.regions = regions or {}
        self.region_line_thickness = region_line_thickness

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
            "show_in": False,  # 禁用进入计数显示
            "show_out": False,  # 禁用离开计数显示
        }

        # 热力图
        self.heatmap = solutions.Heatmap(colormap=colormap, **common_args)

        # 区域计数（如果有区域定义）
        self.region_counter = None
        if regions:
            self.region_counter = solutions.RegionCounter(region=regions, **common_args)

    def _draw_regions(self, frame: np.ndarray, region_counts: dict[str, int]) -> np.ndarray:
        """
        在帧上绘制区域边框和区域人数

        Args:
            frame: 输入帧
            region_counts: 各区域人数

        Returns:
            绘制后的帧
        """
        result = frame.copy()

        for idx, (name, polygon) in enumerate(self.regions.items()):
            color = self.REGION_COLORS[idx % len(self.REGION_COLORS)]
            pts = np.array(polygon, dtype=np.int32)

            # 绘制区域边框（细线）
            cv2.polylines(result, [pts], isClosed=True, color=color, thickness=self.region_line_thickness)

            # 计算区域中心位置
            M = cv2.moments(pts)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx, cy = pts[0][0], pts[0][1]

            # 绘制区域名称和人数
            count = region_counts.get(name, 0)
            label = f"{name}: {count}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 2

            # 获取文本大小
            (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)

            # 绘制背景矩形
            padding = 4
            cv2.rectangle(
                result,
                (cx - text_w // 2 - padding, cy - text_h // 2 - padding),
                (cx + text_w // 2 + padding, cy + text_h // 2 + padding),
                color,
                -1
            )

            # 绘制文本
            cv2.putText(
                result,
                label,
                (cx - text_w // 2, cy + text_h // 2),
                font,
                font_scale,
                (255, 255, 255),
                thickness,
                cv2.LINE_AA
            )

        return result

    def _draw_total_count(self, frame: np.ndarray, total_count: int) -> np.ndarray:
        """
        在右上角绘制总人数

        Args:
            frame: 输入帧
            total_count: 总人数

        Returns:
            绘制后的帧
        """
        result = frame.copy()
        h, w = result.shape[:2]

        label = f"Total: {total_count}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.8
        thickness = 2

        # 获取文本大小
        (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)

        # 右上角位置
        padding = 8
        margin = 10
        x = w - text_w - padding * 2 - margin
        y = margin

        # 绘制背景矩形（半透明效果）
        overlay = result.copy()
        cv2.rectangle(
            overlay,
            (x, y),
            (x + text_w + padding * 2, y + text_h + padding * 2),
            (0, 0, 0),
            -1
        )
        cv2.addWeighted(overlay, 0.6, result, 0.4, 0, result)

        # 绘制文本
        cv2.putText(
            result,
            label,
            (x + padding, y + text_h + padding),
            font,
            font_scale,
            (255, 255, 255),
            thickness,
            cv2.LINE_AA
        )

        return result

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
        output_frame = heatmap_result.plot_im

        # 区域计数处理
        total_count = 0
        region_counts = {}
        region_densities = {}

        if self.region_counter:
            region_result = self.region_counter(frame)
            total_count = region_result.total_tracks
            region_counts = dict(region_result.region_counts) if region_result.region_counts else {}

            # 计算各区域密度
            for name in self.regions.keys():
                count = region_counts.get(name, 0)
                area = self.region_areas.get(name, 0)
                region_densities[name] = calculate_density(
                    count, area,
                    factor=settings.DENSITY_FACTOR,
                    max_value=settings.DENSITY_MAX
                )

            # 在热力图上叠加区域边框和人数
            output_frame = self._draw_regions(output_frame, region_counts)
        else:
            # 无区域时从热力图结果获取总人数
            if hasattr(heatmap_result, "total_tracks"):
                total_count = heatmap_result.total_tracks

        # 在右上角显示总人数
        output_frame = self._draw_total_count(output_frame, total_count)

        total_density = calculate_density(
            total_count, frame.shape[0] * frame.shape[1],
            factor=settings.DENSITY_FACTOR,
            max_value=settings.DENSITY_MAX
        )

        return DetectionResult(
            frame=output_frame,
            total_count=total_count,
            total_density=total_density,
            region_counts=region_counts,
            region_densities=region_densities,
        )
