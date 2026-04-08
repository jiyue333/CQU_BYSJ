"""
YOLO 检测服务

同时提供：
- 实时热力图可视化（自定义 RealtimeHeatmapRenderer）
- 多区域实时人数统计（solutions.RegionCounter）
- 区域物理密度计算（人/m²）
- 区域边框和人数叠加显示
"""

import warnings
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

# 过滤 Ultralytics "No tracks found" 警告
warnings.filterwarnings("ignore", message=".*No tracks found.*")

from ultralytics import YOLO, solutions

from app.utils import calculate_density, calculate_polygon_area
from app.services.detection.realtime_heatmap import RealtimeHeatmapRenderer
from app.core.config import settings
from app.core.logger import logger


@dataclass
class DetectionResult:
    """检测结果"""

    frame: np.ndarray  # 热力图叠加后的帧
    total_count: int  # 总人数
    total_density: float  # 总密度（人/m²）
    region_counts: dict[str, int] = field(default_factory=dict)  # 各区域人数
    region_densities: dict[str, float] = field(default_factory=dict)  # 各区域密度（人/m²）


class YOLOService:
    """YOLO 检测服务 - 实时热力图 + 区域计数 + 物理密度分析"""

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
        model_path: str | None = None,
        regions: dict[str, list[tuple]] | None = None,
        conf: float = 0.5,
        device: str = "cpu",
        colormap: int = cv2.COLORMAP_JET,
        region_line_thickness: int = 2,
        region_physical_areas: dict[str, float] | None = None,
    ):
        """
        Args:
            model_path: 模型路径
            regions: 区域定义 {"区域名": [(x1,y1), (x2,y2), ...]}
            conf: 置信度阈值
            device: 运行设备
            colormap: 热力图 colormap
            region_line_thickness: 区域边框线条粗细
            region_physical_areas: 各区域物理面积（m²），由 VLM 估算
        """
        model_path = model_path or settings.YOLO_MODEL_PATH

        logger.info(f"[YOLO] 初始化 YOLOService")
        logger.info(f"[YOLO] model_path = {model_path}")
        logger.info(f"[YOLO] model_path exists = {Path(model_path).exists()}")
        logger.info(f"[YOLO] model_path absolute = {Path(model_path).absolute()}")
        logger.info(f"[YOLO] conf = {conf}, device = {device}")
        logger.info(f"[YOLO] regions = {list(regions.keys()) if regions else 'None'}")
        logger.info(f"[YOLO] physical_areas = {region_physical_areas}")

        self.regions = regions or {}
        self.conf = conf
        self.device = device
        self.region_line_thickness = region_line_thickness

        # 区域物理面积（m²）
        self.region_physical_areas: dict[str, float] = region_physical_areas or {}

        # 预计算各区域像素面积（用于兼容）
        self.region_areas: dict[str, float] = {}
        for name, polygon in self.regions.items():
            self.region_areas[name] = calculate_polygon_area(polygon)

        # 直接加载 YOLO 模型（替代 solutions.Heatmap）
        self.model = YOLO(model_path)

        # 实时热力图渲染器
        self.heatmap_renderer = RealtimeHeatmapRenderer(
            colormap=colormap,
            alpha=0.5,
            sigma=40,
        )

        # 区域计数（如果有区域定义）
        common_args = {
            "model": model_path,
            "conf": conf,
            "device": device,
            "classes": [0],  # 只检测 person
            "show": False,
            "verbose": False,
            "show_in": False,
            "show_out": False,
            "iou": 0.85,
        }

        self.region_counter = None
        if regions:
            self.region_counter = solutions.RegionCounter(
                region=regions,
                line_width=0,
                show_labels=False,
                show_conf=False,
                **common_args
            )

    def _draw_regions(self, frame: np.ndarray, region_counts: dict[str, int]) -> np.ndarray:
        """
        在帧上绘制区域边框和区域人数（显示在区域右上角）

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

            # 找到区域右上角位置（x最大且y最小的点附近）
            x_min, y_min = pts.min(axis=0)
            x_max, y_max = pts.max(axis=0)

            # 右上角位置
            label_x = x_max
            label_y = y_min

            # 绘制人数（使用纯数字，避免中文问号问题）
            count = region_counts.get(name, 0)
            label = str(count)
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.7
            thickness = 2

            # 获取文本大小
            (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)

            # 调整位置使标签在区域内右上角
            padding = 6
            box_x1 = label_x - text_w - padding * 2
            box_y1 = label_y
            box_x2 = label_x
            box_y2 = label_y + text_h + padding * 2

            # 绘制背景矩形
            cv2.rectangle(
                result,
                (box_x1, box_y1),
                (box_x2, box_y2),
                color,
                -1
            )

            # 绘制文本
            cv2.putText(
                result,
                label,
                (box_x1 + padding, box_y2 - padding),
                font,
                font_scale,
                (255, 255, 255),
                thickness,
                cv2.LINE_AA
            )

        return result

    def _draw_detections(self, frame: np.ndarray, boxes: np.ndarray, confs: np.ndarray) -> np.ndarray:
        """
        在帧上绘制检测框和置信度

        Args:
            frame: 输入帧
            boxes: 检测框 [[x1,y1,x2,y2], ...]
            confs: 置信度列表

        Returns:
            绘制后的帧
        """
        result = frame.copy()

        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = map(int, box[:4])

            # 绘制检测框（绿色）
            cv2.rectangle(result, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # 绘制置信度标签
            if i < len(confs):
                conf = confs[i]
                label = f"{conf:.2f}"
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.5
                thickness = 1
                (text_w, text_h), _ = cv2.getTextSize(label, font, font_scale, thickness)

                # 背景矩形
                cv2.rectangle(result, (x1, y1 - text_h - 4), (x1 + text_w + 4, y1), (0, 255, 0), -1)
                # 文本
                cv2.putText(result, label, (x1 + 2, y1 - 2), font, font_scale, (0, 0, 0), thickness, cv2.LINE_AA)

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

        label = str(total_count)
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
            DetectionResult: 热力图帧 + 区域人数统计 + 密度（人/m²）
        """
        # 1. YOLO 推理 — 直接调用模型（替代 solutions.Heatmap）
        results = self.model.track(
            frame,
            persist=True,
            classes=[0],
            conf=self.conf,
            device=self.device,
            verbose=False,
        )

        # 2. 提取检测框和中心点
        boxes = np.empty((0, 4))
        confs = np.array([])
        detection_centers: list[tuple[int, int]] = []

        if results and len(results) > 0 and results[0].boxes is not None:
            boxes_data = results[0].boxes
            if len(boxes_data) > 0:
                boxes = boxes_data.xyxy.cpu().numpy()
                confs = boxes_data.conf.cpu().numpy()

                # 计算每个检测框的中心点（用于热力图）
                for box in boxes:
                    cx = int((box[0] + box[2]) / 2)
                    cy = int((box[1] + box[3]) / 2)
                    detection_centers.append((cx, cy))

        # 3. 生成实时热力图（纯快照，无累积）
        output_frame = self.heatmap_renderer.render(frame, detection_centers)

        # 4. 叠加检测框
        output_frame = self._draw_detections(output_frame, boxes, confs)

        # 5. 区域计数 + 密度计算
        total_count = len(detection_centers)
        region_counts = {}
        region_densities = {}

        if self.region_counter:
            # 使用帧副本，避免 RegionCounter 修改原始帧或共享状态
            region_result = self.region_counter(frame.copy())
            total_count = region_result.total_tracks
            region_counts = dict(region_result.region_counts) if region_result.region_counts else {}

            # 计算各区域物理密度（人/m²）
            for name in self.regions.keys():
                count = region_counts.get(name, 0)
                area_m2 = self.region_physical_areas.get(name, 0)
                if area_m2 > 0:
                    region_densities[name] = calculate_density(
                        count, area_m2,
                        max_value=settings.DENSITY_MAX
                    )
                else:
                    # 无物理面积时不输出密度
                    region_densities[name] = 0.0

            # 在热力图上叠加区域边框和人数
            output_frame = self._draw_regions(output_frame, region_counts)
        else:
            # 无区域时显示右上角总人数
            output_frame = self._draw_total_count(output_frame, total_count)

        # 6. 计算总体密度
        total_physical_area = sum(self.region_physical_areas.values()) if self.region_physical_areas else 0
        if total_physical_area > 0:
            total_density = calculate_density(
                total_count, total_physical_area,
                max_value=settings.DENSITY_MAX
            )
        else:
            total_density = 0.0

        return DetectionResult(
            frame=output_frame,
            total_count=total_count,
            total_density=total_density,
            region_counts=region_counts,
            region_densities=region_densities,
        )
