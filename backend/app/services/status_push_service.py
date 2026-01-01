"""WebSocket 状态推送服务

推送所有视频流的状态变更到订阅的客户端。

方案 F：监听 inference:status Stream（RenderWorker 复用此 Stream 上报状态）
事件映射：
- RENDER_STARTED / STARTED → running
- RENDER_STOPPED / STOPPED → stopped
- RENDER_ERROR / ERROR → error
- RENDER_COOLDOWN / COOLDOWN → cooldown
- HEALTH_UPDATE → 忽略（不影响前端状态）
"""

import asyncio
import json
import logging
import time
from typing import Dict, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect
import redis.asyncio as redis

from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)


class StatusPushService:
    """WebSocket 状态推送服务
    
    职责：
    - 管理状态订阅的 WebSocket 连接
    - 消费 Redis Streams 状态上报（RenderWorker 复用 inference:status）
    - 推送状态变更到所有订阅的客户端
    
    方案 F 事件映射：
    - STARTED / RENDER_STARTED → running
    - STOPPED / RENDER_STOPPED → stopped
    - ERROR / RENDER_ERROR → error
    - COOLDOWN / RENDER_COOLDOWN → cooldown
    """
    
    # RenderWorker 复用此 Stream 上报状态
    STATUS_STREAM = "inference:status"
    
    # 事件到状态的映射（支持 Inference 和 Render 两种前缀）
    EVENT_TO_STATUS = {
        # 原 Inference 事件（向后兼容）
        "STARTED": "running",
        "STOPPED": "stopped",
        "COOLDOWN": "cooldown",
        "ERROR": "error",
        # 方案 F Render 事件
        "RENDER_STARTED": "running",
        "RENDER_STOPPED": "stopped",
        "RENDER_COOLDOWN": "cooldown",
        "RENDER_ERROR": "error",
    }
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self.connections: Set[WebSocket] = set()
        self.last_heartbeat: Dict[WebSocket, float] = {}
        self.last_id: str = "0"
        self._running = False
        self._listener_task: Optional[asyncio.Task] = None
    
    async def _get_redis(self) -> redis.Redis:
        """获取 Redis 客户端"""
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis
    
    async def start(self):
        """启动 Redis Streams 监听"""
        if self._running:
            return
        self._running = True
        # 使用 "$" 作为初始 last_id，只接收新消息
        self.last_id = "$"
        self._listener_task = asyncio.create_task(self._redis_listener())
        logger.info("StatusPushService started")
    
    async def stop(self):
        """停止服务"""
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        logger.info("StatusPushService stopped")
    
    async def subscribe(self, websocket: WebSocket):
        """处理 WebSocket 连接订阅
        
        Args:
            websocket: WebSocket 连接
        """
        # 确保 Redis 监听器已启动
        await self.start()
        
        await websocket.accept()
        
        # 注册连接
        self.connections.add(websocket)
        self.last_heartbeat[websocket] = time.time()
        
        logger.info("WebSocket subscribed to status updates")
        
        try:
            while True:
                try:
                    message = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=settings.ws_heartbeat_interval + settings.ws_heartbeat_timeout
                    )
                    
                    try:
                        data = json.loads(message)
                        if data.get("type") == "ping":
                            self.last_heartbeat[websocket] = time.time()
                            await websocket.send_text(json.dumps({
                                "type": "pong",
                                "ts": data.get("ts")
                            }))
                    except json.JSONDecodeError:
                        pass
                        
                except asyncio.TimeoutError:
                    logger.warning("WebSocket heartbeat timeout for status subscription")
                    break
                    
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected from status subscription")
        except Exception as e:
            logger.error(f"WebSocket error for status subscription: {e}")
        finally:
            self._cleanup_connection(websocket)
    
    def _cleanup_connection(self, websocket: WebSocket):
        """清理 WebSocket 连接"""
        self.connections.discard(websocket)
        self.last_heartbeat.pop(websocket, None)
    
    async def _redis_listener(self):
        """监听 Redis Streams 状态上报"""
        client = await self._get_redis()
        
        while self._running:
            try:
                if not self.connections:
                    await asyncio.sleep(0.1)
                    continue
                
                # 读取状态 Stream
                messages = await client.xread(
                    {self.STATUS_STREAM: self.last_id},
                    block=settings.stream_read_block_ms,
                    count=settings.stream_read_count
                )
                
                if not messages:
                    continue
                
                for stream_key, entries in messages:
                    for msg_id, data in entries:
                        if isinstance(msg_id, bytes):
                            msg_id = msg_id.decode()
                        self.last_id = msg_id
                        
                        status_data = data.get("data") or data.get(b"data", b"{}")
                        if isinstance(status_data, bytes):
                            status_data = status_data.decode()
                        
                        await self._broadcast(status_data)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Status listener error: {e}")
                await asyncio.sleep(1)
    
    async def _send_with_timeout(
        self, 
        websocket: WebSocket, 
        message: str, 
        timeout: float = 5.0
    ) -> bool:
        """带超时的消息发送
        
        Args:
            websocket: WebSocket 连接
            message: 要发送的消息
            timeout: 超时时间（秒）
            
        Returns:
            True 发送成功，False 发送失败或超时
        """
        try:
            await asyncio.wait_for(websocket.send_text(message), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            logger.warning(f"WebSocket send timeout after {timeout}s")
            return False
        except Exception as e:
            logger.error(f"WebSocket send error: {e}")
            return False

    async def _broadcast(self, data: str):
        """广播状态消息到所有订阅的客户端
        
        方案 F：使用 EVENT_TO_STATUS 映射处理 Render 事件
        """
        # 安全解析 JSON 数据
        try:
            parsed_data = json.loads(data) if isinstance(data, str) else data
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON status data: {data[:100]}")
            parsed_data = {"raw": data}

        # Normalize events to stream status updates for frontend
        if isinstance(parsed_data, dict) and "status" not in parsed_data:
            event = parsed_data.get("event")
            if event:
                mapped_status = self.EVENT_TO_STATUS.get(event)
                if not mapped_status:
                    # Ignore non-status events (e.g. HEALTH_UPDATE)
                    return
                parsed_data["status"] = mapped_status
        
        message = json.dumps({
            "type": "status",
            "data": parsed_data
        })
        
        for ws in self.connections.copy():
            try:
                success = await self._send_with_timeout(ws, message)
                if not success:
                    self._cleanup_connection(ws)
            except Exception as e:
                logger.error(f"Failed to send status to WebSocket: {e}")
                self._cleanup_connection(ws)
    
    async def notify_status_change(self, stream_id: str, status: str, extra: dict = None):
        """主动通知状态变更（供 StreamService 调用）
        
        Args:
            stream_id: 视频流 ID
            status: 新状态
            extra: 额外信息
        """
        data = {
            "stream_id": stream_id,
            "status": status,
            "timestamp": time.time(),
            **(extra or {})
        }
        
        message = json.dumps({
            "type": "status",
            "data": data
        })
        
        for ws in self.connections.copy():
            success = await self._send_with_timeout(ws, message)
            if not success:
                self._cleanup_connection(ws)


# 全局状态推送服务实例
_status_push_service: Optional[StatusPushService] = None


def get_status_push_service() -> StatusPushService:
    """获取状态推送服务（单例）"""
    global _status_push_service
    if _status_push_service is None:
        _status_push_service = StatusPushService()
    return _status_push_service
