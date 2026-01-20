"""
API 路由配置

注册所有 API 路由
"""

from fastapi import APIRouter

from app.api.endpoints import (
    sources_router,
    analysis_router,
    regions_router,
    alerts_router,
    history_router,
    status_router,
    websocket_router,
)

# 创建主路由
api_router = APIRouter()

# 注册子路由
api_router.include_router(sources_router)
api_router.include_router(analysis_router)
api_router.include_router(regions_router)
api_router.include_router(alerts_router)
api_router.include_router(history_router)
api_router.include_router(status_router)
api_router.include_router(websocket_router)
