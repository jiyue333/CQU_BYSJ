"""
WebSocket API

实时数据推送和告警消息推送
"""

import json
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.logger import logger

router = APIRouter(prefix="/ws", tags=["WebSocket"])


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # source_id -> set of WebSocket connections
        self.realtime_connections: Dict[str, Set[WebSocket]] = {}
        self.alert_connections: Dict[str, Set[WebSocket]] = {}

    async def connect_realtime(self, websocket: WebSocket, source_id: str):
        """连接实时数据推送"""
        await websocket.accept()
        if source_id not in self.realtime_connections:
            self.realtime_connections[source_id] = set()
        self.realtime_connections[source_id].add(websocket)
        logger.info(f"WebSocket realtime 连接: {source_id}")

    async def connect_alerts(self, websocket: WebSocket, source_id: str):
        """连接告警推送"""
        await websocket.accept()
        if source_id not in self.alert_connections:
            self.alert_connections[source_id] = set()
        self.alert_connections[source_id].add(websocket)
        logger.info(f"WebSocket alerts 连接: {source_id}")

    def disconnect_realtime(self, websocket: WebSocket, source_id: str):
        """断开实时数据连接"""
        if source_id in self.realtime_connections:
            self.realtime_connections[source_id].discard(websocket)
            if not self.realtime_connections[source_id]:
                del self.realtime_connections[source_id]
        logger.info(f"WebSocket realtime 断开: {source_id}")

    def disconnect_alerts(self, websocket: WebSocket, source_id: str):
        """断开告警连接"""
        if source_id in self.alert_connections:
            self.alert_connections[source_id].discard(websocket)
            if not self.alert_connections[source_id]:
                del self.alert_connections[source_id]
        logger.info(f"WebSocket alerts 断开: {source_id}")

    async def broadcast_realtime(self, source_id: str, data: dict):
        """广播实时数据"""
        if source_id in self.realtime_connections:
            message = json.dumps(data)
            disconnected = set()
            for connection in self.realtime_connections[source_id]:
                try:
                    await connection.send_text(message)
                except Exception:
                    disconnected.add(connection)
            # 清理断开的连接
            for conn in disconnected:
                self.realtime_connections[source_id].discard(conn)

    async def broadcast_alert(self, source_id: str, data: dict):
        """广播告警消息"""
        if source_id in self.alert_connections:
            message = json.dumps(data)
            disconnected = set()
            for connection in self.alert_connections[source_id]:
                try:
                    await connection.send_text(message)
                except Exception:
                    disconnected.add(connection)
            # 清理断开的连接
            for conn in disconnected:
                self.alert_connections[source_id].discard(conn)


# 全局连接管理器
manager = ConnectionManager()


@router.websocket("/realtime")
async def websocket_realtime(
    websocket: WebSocket,
    source_id: str = Query(..., description="数据源 ID"),
):
    """实时推理数据推送"""
    await manager.connect_realtime(websocket, source_id)
    try:
        while True:
            # 保持连接，等待客户端消息或断开
            data = await websocket.receive_text()
            # 可以处理客户端发来的控制消息
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect_realtime(websocket, source_id)


@router.websocket("/alerts")
async def websocket_alerts(
    websocket: WebSocket,
    source_id: str = Query(..., description="数据源 ID"),
):
    """预警消息推送"""
    await manager.connect_alerts(websocket, source_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect_alerts(websocket, source_id)


def get_ws_manager() -> ConnectionManager:
    """获取 WebSocket 管理器实例"""
    return manager
