"""WebSocket 结果推送服务

桥接 Redis Streams → WebSocket 客户端。
包含心跳机制、慢客户端处理、断点续传功能。
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


class ResultPushService:
    """WebSocket 结果推送服务
    
    职责：
    - 管理 WebSocket 连接
    - 消费 Redis Streams 检测结果
    - 推送结果到订阅的客户端
    - 心跳检测和慢客户端处理
    """
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self.connections: Dict[str, Set[WebSocket]] = {}  # stream_id -> websockets
        self.last_heartbeat: Dict[WebSocket, float] = {}  # websocket -> 最后心跳时间
        self.pending_messages: Dict[WebSocket, int] = {}  # websocket -> 待发送消息数
        self.last_ids: Dict[str, str] = {}  # stream_id -> last_message_id
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
        self._listener_task = asyncio.create_task(self._redis_listener())
        logger.info("ResultPushService started")
    
    async def stop(self):
        """停止服务"""
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        logger.info("ResultPushService stopped")
    
    async def subscribe(self, websocket: WebSocket, stream_id: str):
        """处理 WebSocket 连接订阅
        
        Args:
            websocket: WebSocket 连接
            stream_id: 要订阅的视频流 ID
        """
        # 确保 Redis 监听器已启动
        await self.start()
        
        await websocket.accept()
        
        # 注册连接
        if stream_id not in self.connections:
            self.connections[stream_id] = set()
        self.connections[stream_id].add(websocket)
        self.last_heartbeat[websocket] = time.time()
        self.pending_messages[websocket] = 0
        
        # 初始化 last_id 为 "$" 避免历史消息重放
        self.last_ids.setdefault(stream_id, "$")
        
        logger.info(f"WebSocket subscribed to stream {stream_id}")
        
        try:
            while True:
                # 使用 wait_for 实现心跳超时检测
                try:
                    message = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=settings.ws_heartbeat_interval + settings.ws_heartbeat_timeout
                    )
                    
                    # 处理消息
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type")
                        
                        if msg_type == "ping":
                            # 心跳响应
                            self.last_heartbeat[websocket] = time.time()
                            await websocket.send_text(json.dumps({
                                "type": "pong",
                                "ts": data.get("ts")
                            }))
                        elif msg_type == "recover":
                            # 断点续传请求
                            last_id = data.get("last_id", "0")
                            await self._send_recovery_messages(websocket, stream_id, last_id)
                    except json.JSONDecodeError:
                        pass
                        
                except asyncio.TimeoutError:
                    # 心跳超时，断开连接
                    logger.warning(f"WebSocket heartbeat timeout for stream {stream_id}")
                    break
                    
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected from stream {stream_id}")
        except Exception as e:
            logger.error(f"WebSocket error for stream {stream_id}: {e}")
        finally:
            # 清理连接
            self._cleanup_connection(websocket, stream_id)
    
    def _cleanup_connection(self, websocket: WebSocket, stream_id: str):
        """清理 WebSocket 连接"""
        if stream_id in self.connections:
            self.connections[stream_id].discard(websocket)
            if not self.connections[stream_id]:
                del self.connections[stream_id]
                # 清理该 stream 的 last_id，避免内存泄漏
                self.last_ids.pop(stream_id, None)
        self.last_heartbeat.pop(websocket, None)
        self.pending_messages.pop(websocket, None)

    async def _redis_listener(self):
        """监听 Redis Streams，转发到 WebSocket"""
        client = await self._get_redis()
        
        while self._running:
            try:
                # 快照当前连接列表，避免迭代时修改
                stream_ids = list(self.connections.keys())
                
                if not stream_ids:
                    await asyncio.sleep(0.1)
                    continue
                
                # 构建要读取的 streams，使用 "$" 作为默认值避免历史重放
                streams = {}
                for stream_id in stream_ids:
                    streams[f"result:{stream_id}"] = self.last_ids.get(stream_id, "$")
                
                # 阻塞读取 Redis Streams
                # 注意：redis-py 的 xread 返回格式为 [(stream_name, [(id, data), ...]), ...]
                messages = await client.xread(
                    streams, 
                    block=settings.stream_read_block_ms, 
                    count=settings.stream_read_count
                )
                
                if not messages:
                    continue
                
                for stream_key, entries in messages:
                    # 安全解析 stream_id
                    if isinstance(stream_key, bytes):
                        stream_key = stream_key.decode()
                    stream_id = stream_key.removeprefix("result:")
                    
                    for msg_id, data in entries:
                        if isinstance(msg_id, bytes):
                            msg_id = msg_id.decode()
                        self.last_ids[stream_id] = msg_id
                        
                        # 获取结果数据
                        result_data = data.get("data") or data.get(b"data", b"{}")
                        if isinstance(result_data, bytes):
                            result_data = result_data.decode()
                        
                        # 推送给所有订阅该 stream_id 的 WebSocket 客户端
                        await self._broadcast(stream_id, result_data, msg_id)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Redis listener error: {e}")
                await asyncio.sleep(1)  # 错误后等待重试
    
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

    async def _broadcast(self, stream_id: str, data: str, msg_id: str):
        """广播消息到所有订阅的客户端"""
        if stream_id not in self.connections:
            return
        
        # 安全解析 JSON 数据
        try:
            parsed_data = json.loads(data) if isinstance(data, str) else data
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON data for stream {stream_id}: {data[:100]}")
            parsed_data = {"raw": data}
        
        # 包装消息，添加 msg_id 用于断点续传
        message = json.dumps({
            "type": "result",
            "msg_id": msg_id,
            "data": parsed_data
        })
        
        for ws in self.connections[stream_id].copy():
            try:
                # 检查慢客户端
                pending = self.pending_messages.get(ws, 0)
                if pending >= settings.ws_slow_client_threshold:
                    logger.warning(f"Slow client detected, dropping message for stream {stream_id}")
                    continue  # 丢弃消息，不阻塞
                
                self.pending_messages[ws] = pending + 1
                
                # 使用带超时的发送，避免阻塞
                success = await self._send_with_timeout(ws, message)
                if success:
                    self.pending_messages[ws] = max(0, self.pending_messages.get(ws, 0) - 1)
                else:
                    # 发送失败，清理连接
                    self._cleanup_connection(ws, stream_id)
                
            except Exception as e:
                logger.error(f"Failed to send to WebSocket: {e}")
                self._cleanup_connection(ws, stream_id)
    
    async def _send_recovery_messages(self, websocket: WebSocket, stream_id: str, last_id: str):
        """发送断点续传消息"""
        client = await self._get_redis()
        
        try:
            # 使用 ( 前缀排除 last_id 本身，避免重复投递
            messages = await client.xrange(
                f"result:{stream_id}",
                min=f"({last_id}" if last_id != "0" else "-",
                max="+",
                count=settings.stream_recover_count
            )
            
            for msg_id, data in messages:
                if isinstance(msg_id, bytes):
                    msg_id = msg_id.decode()
                
                result_data = data.get("data") or data.get(b"data", b"{}")
                if isinstance(result_data, bytes):
                    result_data = result_data.decode()
                
                message = json.dumps({
                    "type": "recovery",
                    "msg_id": msg_id,
                    "data": json.loads(result_data) if isinstance(result_data, str) else result_data
                })
                
                await websocket.send_text(message)
                
            # 发送恢复完成消息
            await websocket.send_text(json.dumps({
                "type": "recovery_complete",
                "count": len(messages)
            }))
            
        except Exception as e:
            logger.error(f"Failed to send recovery messages: {e}")


# 全局结果推送服务实例
_result_push_service: Optional[ResultPushService] = None


def get_result_push_service() -> ResultPushService:
    """获取结果推送服务（单例）"""
    global _result_push_service
    if _result_push_service is None:
        _result_push_service = ResultPushService()
    return _result_push_service
