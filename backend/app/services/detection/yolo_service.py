"""
YOLO 检测服务

职责：
- 人物检测与追踪（model.track）
- 多区域实时人数统计
- 按区域边界统计独立进出累计
- 区域边框和人数叠加显示

注意：密度图/热力图由 DMCountService 负责，本服务不再处理。
"""

import warnings
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

warnings.filterwarnings("ignore", message=".*No tracks found.*")

from ultralytics import YOLO

from app.core.config import settings
from app.core.logger import logger

# 中文字体（懒加载）
_font_cache: dict[int, ImageFont.FreeTypeFont] = {}

_FONT_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Light.ttc",           # macOS
    "/System/Library/Fonts/PingFang.ttc",                # macOS
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",  # Linux
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Linux
    "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",         # Linux
    "C:/Windows/Fonts/msyh.ttc",                               # Windows
]


def _get_font(size: int = 16) -> ImageFont.FreeTypeFont:
    if size in _font_cache:
        return _font_cache[size]
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            font = ImageFont.truetype(path, size)
            _font_cache[size] = font
            return font
    font = ImageFont.load_default()
    _font_cache[size] = font
    return font


def _put_chinese_text(
    img: np.ndarray,
    text: str,
    position: tuple[int, int],
    font_size: int = 16,
    color: tuple[int, int, int] = (255, 255, 255),
    bg_color: tuple[int, int, int] | None = (0, 0, 0),
    bg_alpha: float = 0.6,
    padding: int = 4,
) -> np.ndarray:
    """在 OpenCV 图像上绘制支持中文的文本"""
    font = _get_font(font_size)
    # 测量文本尺寸
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x, y = position
    # 绘制背景
    if bg_color is not None:
        overlay = img.copy()
        cv2.rectangle(
            overlay,
            (x - padding, y - padding),
            (x + text_w + padding, y + text_h + padding),
            bg_color, -1,
        )
        cv2.addWeighted(overlay, bg_alpha, img, 1 - bg_alpha, 0, img)

    # 重新从 img 创建 PIL 图像（含背景）
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    # PIL 的颜色是 RGB，传入的是 BGR
    draw.text((x, y), text, font=font, fill=(color[2], color[1], color[0]))
    result = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    return result


def _draw_dashed_polyline(
    img: np.ndarray,
    pts: np.ndarray,
    color: tuple,
    thickness: int = 2,
    gap: int = 10,
) -> None:
    """绘制虚线多边形边框"""
    n = len(pts)
    for i in range(n):
        p1 = tuple(pts[i])
        p2 = tuple(pts[(i + 1) % n])
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dist = max(1, int(np.hypot(dx, dy)))
        for j in range(0, dist, gap * 2):
            s = j / dist
            e = min((j + gap) / dist, 1.0)
            sp = (int(p1[0] + dx * s), int(p1[1] + dy * s))
            ep = (int(p1[0] + dx * e), int(p1[1] + dy * e))
            cv2.line(img, sp, ep, color, thickness)


@dataclass
class DetectionResult:
    """检测结果"""

    frame: np.ndarray  # 叠加标注后的帧（无热力图）
    total_count: int  # 总人数
    region_counts: dict[str, int] = field(default_factory=dict)
    region_flow_stats: dict[str, dict[str, int]] = field(default_factory=dict)
    # 检测中心点（供外部使用）
    detection_centers: list[tuple[int, int]] = field(default_factory=list)
    smoothed_count: int = 0  # EMA 平滑后的人数


class YOLOService:
    """YOLO 检测服务 — 追踪 + 区域计数 + 区域进出累计"""

    REGION_COLORS = [
        (246, 143, 59),
        (235, 192, 91),
        (225, 125, 47),
        (111, 191, 45),
        (94, 106, 228),
        (180, 130, 220),
    ]

    def __init__(
        self,
        model_path: str | None = None,
        regions: dict[str, list[tuple]] | None = None,
        conf: float = 0.5,
        device: str = "cpu",
        classes: list[int] | None = None,
        region_line_thickness: int = 2,
    ):
        """
        Args:
            model_path: 模型路径
            regions: 区域定义 {"区域名": [(x1,y1), ...]}
            conf: 置信度阈值
            device: 运行设备
            classes: 检测类别列表，如 [0] 或 [0, 1]
            region_line_thickness: 区域边框线条粗细
        """
        model_path = model_path or settings.YOLO_MODEL_PATH
        self._classes = classes if classes else [0]

        logger.info(f"[YOLO] 初始化 YOLOService")
        logger.info(f"[YOLO] model_path = {model_path}, exists = {Path(model_path).exists()}")
        logger.info(f"[YOLO] conf = {conf}, device = {device}, classes = {self._classes}")
        logger.info(f"[YOLO] regions = {list(regions.keys()) if regions else 'None'}")

        self.regions = regions or {}
        self.conf = conf
        self.device = device
        self.region_line_thickness = region_line_thickness

        self.model = YOLO(model_path)
        self._region_polygons: dict[str, np.ndarray] = {
            name: np.array(points, dtype=np.float32)
            for name, points in self.regions.items()
        }
        self._track_region_presence: dict[int, dict[str, bool]] = defaultdict(dict)
        self._region_flow_states: dict[str, dict[str, int]] = {
            name: {"in_total": 0, "out_total": 0}
            for name in self.regions
        }

        # EMA 平滑状态
        self._ema_alpha = 0.3
        self._ema_count: float = 0.0

    def _collect_region_stats(
        self, tracked_objects: list[tuple[int, tuple[int, int]]]
    ) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
        """基于轨迹中心点计算区域实时人数和独立进出累计。"""
        region_counts = {name: 0 for name in self.regions}

        for track_id, center in tracked_objects:
            prev_presence = self._track_region_presence[track_id]
            current_presence: dict[str, bool] = {}

            for region_name, polygon in self._region_polygons.items():
                is_inside = cv2.pointPolygonTest(polygon, center, False) >= 0
                current_presence[region_name] = is_inside

                if is_inside:
                    region_counts[region_name] += 1

                was_inside = prev_presence.get(region_name)
                if was_inside is None:
                    continue
                if not was_inside and is_inside:
                    self._region_flow_states[region_name]["in_total"] += 1
                elif was_inside and not is_inside:
                    self._region_flow_states[region_name]["out_total"] += 1

            self._track_region_presence[track_id] = current_presence

        return region_counts, {
            region_name: stats.copy()
            for region_name, stats in self._region_flow_states.items()
        }

    def _draw_regions(self, frame: np.ndarray, region_counts: dict[str, int]) -> np.ndarray:
        """在帧上绘制区域边框和区域人数（虚线风格 + 半透明填充）"""
        result = frame.copy()

        for idx, (name, polygon) in enumerate(self.regions.items()):
            color = self.REGION_COLORS[idx % len(self.REGION_COLORS)]
            pts = np.array(polygon, dtype=np.int32)

            # 半透明区域填充
            overlay = result.copy()
            cv2.fillPoly(overlay, [pts], color)
            cv2.addWeighted(overlay, 0.08, result, 0.92, 0, result)

            # 虚线边框
            _draw_dashed_polyline(result, pts, color, self.region_line_thickness, gap=10)

            # 右上角区域名称标签（不显示人数）
            x_max = pts[:, 0].max()
            y_min = pts[:, 1].min()
            result = _put_chinese_text(
                result, name,
                position=(x_max - len(name) * 8 - 8, y_min + 4),
                font_size=16,
                color=(255, 255, 255),
                bg_color=color,
                bg_alpha=0.75,
                padding=5,
            )

        return result

    def _draw_total_count(self, frame: np.ndarray, total_count: int) -> np.ndarray:
        """在右上角绘制总人数"""
        result = frame.copy()
        h, w = result.shape[:2]

        label = str(total_count)
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.8
        thickness = 2
        (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)

        padding = 8
        margin = 10
        x = w - text_w - padding * 2 - margin
        y = margin

        overlay = result.copy()
        cv2.rectangle(overlay, (x, y), (x + text_w + padding * 2, y + text_h + padding * 2), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, result, 0.4, 0, result)
        cv2.putText(result, label, (x + padding, y + text_h + padding),
                    font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

        return result

    def process(self, frame: np.ndarray) -> DetectionResult:
        """
        处理单帧，返回追踪结果、区域计数和区域进出累计。

        不包含热力图渲染（由 DMCountService 负责）。
        """
        # 1. YOLO 推理
        results = self.model.track(
            frame, persist=True, classes=self._classes, conf=self.conf,
            device=self.device, verbose=False,
        )

        # 2. 提取检测框和中心点
        detection_centers: list[tuple[int, int]] = []
        tracked_objects: list[tuple[int, tuple[int, int]]] = []
        total_count = 0

        if results and len(results) > 0 and results[0].boxes is not None:
            boxes_data = results[0].boxes
            if len(boxes_data) > 0:
                boxes = boxes_data.xyxy.cpu().numpy()
                track_ids = boxes_data.id.int().cpu().tolist() if boxes_data.id is not None else []
                total_count = len(boxes)
                for idx, box in enumerate(boxes):
                    cx = int((box[0] + box[2]) / 2)
                    cy = int((box[1] + box[3]) / 2)
                    center = (cx, cy)
                    detection_centers.append(center)
                    if idx < len(track_ids):
                        tracked_objects.append((track_ids[idx], center))

        # 3. 区域计数和区域进出累计
        output_frame = frame.copy()
        region_counts, region_flow_stats = self._collect_region_stats(tracked_objects)

        if self.regions:
            output_frame = self._draw_regions(output_frame, region_counts)
        else:
            output_frame = self._draw_total_count(output_frame, total_count)

        # EMA 平滑
        self._ema_count = self._ema_alpha * total_count + (1 - self._ema_alpha) * self._ema_count
        smoothed = round(self._ema_count)

        return DetectionResult(
            frame=output_frame,
            total_count=total_count,
            region_counts=region_counts,
            region_flow_stats=region_flow_stats,
            smoothed_count=smoothed,
            detection_centers=detection_centers,
        )
