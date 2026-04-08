# Detection 服务模块

from .yolo_service import DetectionResult, YOLOService
from .realtime_heatmap import RealtimeHeatmapRenderer

__all__ = [
    "YOLOService",
    "DetectionResult",
    "RealtimeHeatmapRenderer",
]
