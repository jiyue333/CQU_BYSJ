"""
Pydantic Schemas

导出所有 Schema 供外部使用
"""

from app.schemas.common import ApiResponse, PaginationParams, OkResponse
from app.schemas.video_source import (
    VideoSourceCreate,
    VideoSourceResponse,
    VideoSourceListResponse,
    StreamCreate,
)
from app.schemas.region import (
    RegionCreate,
    RegionUpdate,
    RegionResponse,
    RegionListResponse,
)
from app.schemas.analysis import (
    AnalysisStartRequest,
    AnalysisStopRequest,
    AnalysisStatusResponse,
)
from app.schemas.alert import (
    AlertThresholdGet,
    AlertThresholdUpdate,
    AlertResponse,
    AlertListResponse,
)
from app.schemas.history import (
    HistoryQuery,
    HistorySeriesItem,
    HistoryResponse,
)
from app.schemas.export import (
    ExportRequest,
    ExportResponse,
)
from app.schemas.status import SystemStatusResponse
from app.schemas.websocket import (
    RealtimeFrame,
    RegionRealtimeStats,
    AlertMessage,
)

__all__ = [
    # Common
    "ApiResponse",
    "PaginationParams",
    "OkResponse",
    # VideoSource
    "VideoSourceCreate",
    "VideoSourceResponse",
    "VideoSourceListResponse",
    "StreamCreate",
    # Region
    "RegionCreate",
    "RegionUpdate",
    "RegionResponse",
    "RegionListResponse",
    # Analysis
    "AnalysisStartRequest",
    "AnalysisStopRequest",
    "AnalysisStatusResponse",
    # Alert
    "AlertThresholdGet",
    "AlertThresholdUpdate",
    "AlertResponse",
    "AlertListResponse",
    # History
    "HistoryQuery",
    "HistorySeriesItem",
    "HistoryResponse",
    # Export
    "ExportRequest",
    "ExportResponse",
    # Status
    "SystemStatusResponse",
    # WebSocket
    "RealtimeFrame",
    "RegionRealtimeStats",
    "AlertMessage",
]
