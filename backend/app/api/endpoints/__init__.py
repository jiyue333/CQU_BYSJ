"""
API 端点模块

导出所有路由
"""

from app.api.endpoints.sources import router as sources_router
from app.api.endpoints.analysis import router as analysis_router
from app.api.endpoints.regions import router as regions_router
from app.api.endpoints.alerts import router as alerts_router
from app.api.endpoints.history import router as history_router
from app.api.endpoints.status import router as status_router
from app.api.endpoints.websocket import router as websocket_router

__all__ = [
    "sources_router",
    "analysis_router",
    "regions_router",
    "alerts_router",
    "history_router",
    "status_router",
    "websocket_router",
]
