"""渲染服务控制接口

通过 Redis PubSub 发布 START/STOP 指令到 render:control 通道。
复用 inference:status Stream 上报状态（与 StatusPushService 兼容）。

方案 F：服务端渲染热力图
"""

import json
import time
import uuid
from typing import Optional

import redis.asyncio as redis

from app.core.config import settings
from app.core.redis import get_redis


class RenderControlService:
    """渲染服务控制接口
    
    职责：
    - 发布 START/STOP 指令到 render:control 通道
    - 复用 inference:status Stream 的状态上报（与 StatusPushService 兼容）
    """
    
    CONTROL_CHANNEL = "render:control"
    STATUS_STREAM = "inference:status"  # 复用现有 Stream，保持前端兼容
    
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
        *,
        render_fps: int = settings.render_fps,
        infer_stride: int = settings.render_infer_stride,
        overlay_alpha: float = settings.render_overlay_alpha,
        src_rtsp_url: str,
        dst_rtmp_url: str,
        render_stream_id: str,
    ) -> str:
        """发送 START 指令
        
        Args:
            stream_id: 原始视频流 ID
            render_fps: 渲染输出帧率（默认 24）
            infer_stride: 推理步长，每 N 帧推理一次（默认 3）
            overlay_alpha: 热力图叠加透明度（默认 0.4）
            src_rtsp_url: 源 RTSP 拉流地址（容器内）
            dst_rtmp_url: 目标 RTMP 推流地址（容器内）
            render_stream_id: 渲染流 ID（{stream_id}_heatmap）
            
        Returns:
            cmd_id: 指令唯一 ID
        """
        client = await self._get_redis()
        cmd_id = str(uuid.uuid4())
        
        message = {
            "cmd_id": cmd_id,
            "stream_id": stream_id,
            "action": "START",
            "timestamp": time.time(),
            "params": {
                "render_fps": render_fps,
                "infer_stride": infer_stride,
                "overlay_alpha": overlay_alpha,
                "src_rtsp_url": src_rtsp_url,
                "dst_rtmp_url": dst_rtmp_url,
                "render_stream_id": render_stream_id,
            }
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


# 全局渲染控制服务实例
_render_control: Optional[RenderControlService] = None


def get_render_control() -> RenderControlService:
    """获取渲染控制服务（单例）"""
    global _render_control
    if _render_control is None:
        _render_control = RenderControlService()
    return _render_control
