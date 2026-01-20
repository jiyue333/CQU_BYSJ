"""
WebSocket API

实时数据推送（简化版，单连接模式）
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.logger import logger
from app.schemas.websocket import RealtimeFrame, AlertMessage

router = APIRouter(prefix="/ws", tags=["WebSocket"])


class ConnectionManager:
    """WebSocket 连接管理器（单连接模式）"""

    def __init__(self):
        # source_id -> WebSocket 连接
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, source_id: str) -> None:
        """建立连接"""
        await websocket.accept()

        # 如果已有连接，先断开旧连接
        if source_id in self._connections:
            try:
                await self._connections[source_id].close()
            except Exception:
                pass

        self._connections[source_id] = websocket
        logger.info(f"WebSocket 连接已建立: {source_id}")

    def disconnect(self, source_id: str) -> None:
        """断开连接"""
        if source_id in self._connections:
            del self._connections[source_id]
            logger.info(f"WebSocket 连接已断开: {source_id}")

    def is_connected(self, source_id: str) -> bool:
        """检查是否已连接"""
        return source_id in self._connections

    async def send_frame(self, source_id: str, frame: RealtimeFrame) -> bool:
        """
        发送实时帧数据

        Args:
            source_id: 数据源 ID
            frame: 实时帧数据

        Returns:
            是否发送成功
        """
        if source_id not in self._connections:
            return False

        try:
            websocket = self._connections[source_id]
            await websocket.send_json({
                "type": "frame",
                "data": frame.model_dump(),
            })
            return True
        except Exception as e:
            logger.warning(f"WebSocket 发送帧失败: {source_id}, {e}")
            self.disconnect(source_id)
            return False

    async def send_alert(self, source_id: str, alert: AlertMessage) -> bool:
        """
        发送告警消息

        Args:
            source_id: 数据源 ID
            alert: 告警消息

        Returns:
            是否发送成功
        """
        if source_id not in self._connections:
            return False

        try:
            websocket = self._connections[source_id]
            await websocket.send_json({
                "type": "alert",
                "data": alert.model_dump(),
            })
            return True
        except Exception as e:
            logger.warning(f"WebSocket 发送告警失败: {source_id}, {e}")
            self.disconnect(source_id)
            return False


# 全局连接管理器
ws_manager = ConnectionManager()


@router.websocket("/realtime")
async def websocket_realtime(
    websocket: WebSocket,
    source_id: str = Query(..., description="数据源 ID"),
):
    """
    实时推理数据推送

    连接后将接收:
    - type: "frame" - 实时帧数据 (RealtimeFrame)
    - type: "alert" - 告警消息 (AlertMessage)
    """
    await ws_manager.connect(websocket, source_id)
    try:
        while True:
            # 保持连接，等待客户端消息或断开
            data = await websocket.receive_text()
            # 处理心跳
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(source_id)
    except Exception as e:
        logger.warning(f"WebSocket 异常: {source_id}, {e}")
        ws_manager.disconnect(source_id)


def get_ws_manager() -> ConnectionManager:
    """获取 WebSocket 管理器实例"""
    return ws_manager
