"""推理服务控制接口

通过 Redis PubSub 发布 START/STOP 指令到 inference:control 通道。
通过 Redis Streams 消费推理状态上报（inference:status Stream）。
"""

import json
import time
import uuid
from typing import Optional

import redis.asyncio as redis

from app.core.config import settings
from app.core.redis import get_redis


class InferenceControlService:
    """推理服务控制接口
    
    职责：
    - 发布 START/STOP 指令到 inference:control 通道
    - 消费 inference:status Stream 的状态上报
    """
    
    CONTROL_CHANNEL = "inference:control"
    STATUS_STREAM = "inference:status"
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        """获取 Redis 客户端"""
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis
    
    async def send_start(
        self, 
        stream_id: str, 
        fps: int = 2
    ) -> str:
        """发送 START 指令
        
        Args:
            stream_id: 视频流 ID
            fps: 推理频率（1-3）
            
        Returns:
            cmd_id: 指令唯一 ID
        """
        client = await self._get_redis()
        cmd_id = str(uuid.uuid4())
        
        message = {
            "cmd_id": cmd_id,
            "stream_id": stream_id,
            "action": "START",
            "fps": fps,
            "timestamp": time.time()
        }
        
        await client.publish(self.CONTROL_CHANNEL, json.dumps(message))
        return cmd_id
    
    async def send_stop(self, stream_id: str) -> str:
        """发送 STOP 指令
        
        Args:
            stream_id: 视频流 ID
            
        Returns:
            cmd_id: 指令唯一 ID
        """
        client = await self._get_redis()
        cmd_id = str(uuid.uuid4())
        
        message = {
            "cmd_id": cmd_id,
            "stream_id": stream_id,
            "action": "STOP",
            "timestamp": time.time()
        }
        
        await client.publish(self.CONTROL_CHANNEL, json.dumps(message))
        return cmd_id
    
    async def get_latest_status(self, stream_id: str) -> Optional[dict]:
        """获取某路流的最新状态
        
        从 inference:status Stream 中查找最新的状态消息。
        """
        client = await self._get_redis()
        
        # 从最新消息开始反向查找
        messages = await client.xrevrange(
            self.STATUS_STREAM,
            count=100  # 最多查找最近 100 条
        )
        
        for msg_id, data in messages:
            try:
                msg_data = json.loads(data.get("data", "{}"))
                if msg_data.get("stream_id") == stream_id:
                    return msg_data
            except (json.JSONDecodeError, TypeError):
                continue
        
        return None


# 全局推理控制服务实例
_inference_control: Optional[InferenceControlService] = None


def get_inference_control() -> InferenceControlService:
    """获取推理控制服务（单例）"""
    global _inference_control
    if _inference_control is None:
        _inference_control = InferenceControlService()
    return _inference_control
