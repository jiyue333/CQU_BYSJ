"""API 路由模块"""

from app.api import rois, roi_templates, streams, websockets, alerts, feedback

__all__ = [
    "rois",
    "roi_templates",
    "alerts",
    "feedback",
    "streams",
    "websockets",
]
