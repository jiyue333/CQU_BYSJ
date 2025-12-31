"""Pydantic Schema 模块

导出所有 Pydantic schemas，便于统一导入。
"""

from app.schemas.video_stream import (
    VideoStreamBase,
    VideoStreamCreate,
    VideoStreamUpdate,
    VideoStreamStart,
    VideoStreamResponse,
    VideoStreamListResponse,
    IceServer,
    PublishInfo,
)
from app.schemas.roi import (
    Point,
    DensityThresholds,
    ROIBase,
    ROICreate,
    ROIUpdate,
    ROIResponse,
    ROIListResponse,
)
from app.schemas.detection import (
    DensityLevel,
    Detection,
    RegionStat,
    DetectionResult,
)
from app.schemas.system_config import (
    SystemConfigBase,
    SystemConfigCreate,
    SystemConfigUpdate,
    SystemConfigResponse,
    GlobalConfigResponse,
)
from app.schemas.history_stat import (
    AggregationGranularity,
    HistoryStatBase,
    HistoryStatCreate,
    HistoryStatResponse,
    HistoryQueryParams,
    HistoryListResponse,
    AggregatedStat,
    AggregatedHistoryResponse,
)

__all__ = [
    # VideoStream
    "VideoStreamBase",
    "VideoStreamCreate",
    "VideoStreamUpdate",
    "VideoStreamStart",
    "VideoStreamResponse",
    "VideoStreamListResponse",
    "IceServer",
    "PublishInfo",
    # ROI
    "Point",
    "DensityThresholds",
    "ROIBase",
    "ROICreate",
    "ROIUpdate",
    "ROIResponse",
    "ROIListResponse",
    # Detection
    "DensityLevel",
    "Detection",
    "RegionStat",
    "DetectionResult",
    # SystemConfig
    "SystemConfigBase",
    "SystemConfigCreate",
    "SystemConfigUpdate",
    "SystemConfigResponse",
    "GlobalConfigResponse",
    # HistoryStat
    "AggregationGranularity",
    "HistoryStatBase",
    "HistoryStatCreate",
    "HistoryStatResponse",
    "HistoryQueryParams",
    "HistoryListResponse",
    "AggregatedStat",
    "AggregatedHistoryResponse",
]
