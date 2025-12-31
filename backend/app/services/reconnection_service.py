"""视频流重连服务

实现视频流的自动重连机制：
- 指数退避策略（1s → 2s → 4s → ... → 30s max）
- 重连次数限制（5 次）
- Cooldown 状态管理
- COOLDOWN 自动恢复（60 秒后自动重试 START）

Requirements: 9.1, 9.2
"""

import asyncio
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional, Awaitable

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class ReconnectionState(str, Enum):
    """重连状态"""
    IDLE = "idle"           # 空闲（未启动重连）
    RECONNECTING = "reconnecting"  # 重连中
    COOLDOWN = "cooldown"   # 冷却中
    EXHAUSTED = "exhausted"  # 重连次数耗尽


@dataclass
class StreamReconnectionInfo:
    """流重连信息"""
    stream_id: str
    state: ReconnectionState = ReconnectionState.IDLE
    attempt_count: int = 0
    last_attempt_time: float = 0.0
    cooldown_until: float = 0.0
    next_delay: float = 0.0
    last_error: Optional[str] = None
    task: Optional[asyncio.Task] = field(default=None, repr=False)


class ReconnectionService:
    """视频流重连服务
    
    管理视频流的自动重连逻辑，包括：
    - 指数退避策略
    - 重连次数限制
    - Cooldown 状态管理
    - 自动恢复
    """
    
    def __init__(
        self,
        on_reconnect: Optional[Callable[[str], Awaitable[bool]]] = None,
        on_state_change: Optional[Callable[[str, ReconnectionState, dict], Awaitable[None]]] = None,
    ):
        """初始化重连服务
        
        Args:
            on_reconnect: 重连回调函数，返回 True 表示重连成功
            on_state_change: 状态变更回调函数
        """
        self._on_reconnect = on_reconnect
        self._on_state_change = on_state_change
        self._streams: dict[str, StreamReconnectionInfo] = {}
        self._running = False
    
    def calculate_backoff(self, attempt_count: int) -> float:
        """计算退避时间
        
        使用指数退避 + 抖动: min(base * 2^n + jitter, max)
        
        Args:
            attempt_count: 当前重试次数
            
        Returns:
            退避时间（秒）
        """
        base_delay = min(
            settings.reconnect_base_delay * (2 ** attempt_count),
            settings.reconnect_max_delay
        )
        # 添加抖动 ±20%
        jitter = base_delay * settings.reconnect_jitter * (random.random() * 2 - 1)
        return max(settings.reconnect_base_delay, base_delay + jitter)
    
    def get_info(self, stream_id: str) -> Optional[StreamReconnectionInfo]:
        """获取流的重连信息"""
        return self._streams.get(stream_id)
    
    def get_state(self, stream_id: str) -> ReconnectionState:
        """获取流的重连状态"""
        info = self._streams.get(stream_id)
        return info.state if info else ReconnectionState.IDLE
    
    async def start_reconnection(self, stream_id: str, error: Optional[str] = None) -> None:
        """启动重连流程
        
        Args:
            stream_id: 视频流 ID
            error: 触发重连的错误信息
        """
        info = self._streams.get(stream_id)
        
        if info is None:
            info = StreamReconnectionInfo(stream_id=stream_id)
            self._streams[stream_id] = info
        
        # 如果已经在重连中，忽略
        if info.state == ReconnectionState.RECONNECTING:
            logger.debug("reconnection_already_in_progress", stream_id=stream_id)
            return
        
        # 如果在冷却中，检查是否可以恢复
        if info.state == ReconnectionState.COOLDOWN:
            if time.time() < info.cooldown_until:
                logger.debug(
                    "stream_in_cooldown",
                    stream_id=stream_id,
                    cooldown_remaining=info.cooldown_until - time.time()
                )
                return
        
        # 检查重连次数
        if info.attempt_count >= settings.reconnect_max_attempts:
            await self._enter_cooldown(stream_id, info)
            return
        
        info.state = ReconnectionState.RECONNECTING
        info.last_error = error
        
        logger.info(
            "starting_reconnection",
            stream_id=stream_id,
            attempt=info.attempt_count + 1,
            max_attempts=settings.reconnect_max_attempts,
            error=error
        )
        
        await self._notify_state_change(stream_id, info)
        
        # 启动重连任务
        if info.task and not info.task.done():
            info.task.cancel()
        
        info.task = asyncio.create_task(self._reconnection_loop(stream_id))
    
    async def _reconnection_loop(self, stream_id: str) -> None:
        """重连循环"""
        info = self._streams.get(stream_id)
        if not info:
            return
        
        while info.state == ReconnectionState.RECONNECTING:
            # 计算退避时间
            delay = self.calculate_backoff(info.attempt_count)
            info.next_delay = delay
            
            logger.info(
                "reconnection_attempt",
                stream_id=stream_id,
                attempt=info.attempt_count + 1,
                delay_sec=round(delay, 2)
            )
            
            # 等待退避时间
            await asyncio.sleep(delay)
            
            # 检查状态是否已变更
            if info.state != ReconnectionState.RECONNECTING:
                break
            
            # 尝试重连
            info.attempt_count += 1
            info.last_attempt_time = time.time()
            
            success = False
            if self._on_reconnect:
                try:
                    success = await self._on_reconnect(stream_id)
                except Exception as e:
                    logger.error(
                        "reconnection_callback_error",
                        stream_id=stream_id,
                        error=str(e)
                    )
                    info.last_error = str(e)
            
            if success:
                logger.info(
                    "reconnection_successful",
                    stream_id=stream_id,
                    attempts=info.attempt_count
                )
                await self.reset(stream_id)
                return
            
            # 检查是否达到最大重试次数
            if info.attempt_count >= settings.reconnect_max_attempts:
                await self._enter_cooldown(stream_id, info)
                return
            
            await self._notify_state_change(stream_id, info)
    
    async def _enter_cooldown(self, stream_id: str, info: StreamReconnectionInfo) -> None:
        """进入冷却状态"""
        info.state = ReconnectionState.COOLDOWN
        info.cooldown_until = time.time() + settings.cooldown_duration
        
        logger.warning(
            "entering_cooldown",
            stream_id=stream_id,
            attempts=info.attempt_count,
            cooldown_duration=settings.cooldown_duration
        )
        
        await self._notify_state_change(stream_id, info)
        
        # 启动自动恢复定时器
        asyncio.create_task(self._cooldown_recovery(stream_id))
    
    async def _cooldown_recovery(self, stream_id: str) -> None:
        """冷却恢复"""
        await asyncio.sleep(settings.cooldown_duration)
        
        info = self._streams.get(stream_id)
        if not info or info.state != ReconnectionState.COOLDOWN:
            return
        
        logger.info("cooldown_recovery", stream_id=stream_id)
        
        # 重置状态并尝试重连
        info.attempt_count = 0
        info.state = ReconnectionState.IDLE
        
        await self._notify_state_change(stream_id, info)
        
        # 自动重试
        await self.start_reconnection(stream_id, "cooldown_recovery")
    
    async def stop_reconnection(self, stream_id: str) -> None:
        """停止重连流程
        
        Args:
            stream_id: 视频流 ID
        """
        info = self._streams.get(stream_id)
        if not info:
            return
        
        logger.info("stopping_reconnection", stream_id=stream_id)
        
        if info.task and not info.task.done():
            info.task.cancel()
            try:
                await info.task
            except asyncio.CancelledError:
                pass
        
        info.state = ReconnectionState.IDLE
        await self._notify_state_change(stream_id, info)
    
    async def reset(self, stream_id: str) -> None:
        """重置流的重连状态
        
        Args:
            stream_id: 视频流 ID
        """
        info = self._streams.get(stream_id)
        if not info:
            return
        
        if info.task and not info.task.done():
            info.task.cancel()
            try:
                await info.task
            except asyncio.CancelledError:
                pass
        
        info.state = ReconnectionState.IDLE
        info.attempt_count = 0
        info.last_error = None
        info.cooldown_until = 0.0
        info.next_delay = 0.0
        info.task = None
        
        await self._notify_state_change(stream_id, info)
    
    def remove(self, stream_id: str) -> None:
        """移除流的重连信息
        
        Args:
            stream_id: 视频流 ID
        """
        info = self._streams.pop(stream_id, None)
        if info and info.task and not info.task.done():
            info.task.cancel()
    
    async def _notify_state_change(
        self, 
        stream_id: str, 
        info: StreamReconnectionInfo
    ) -> None:
        """通知状态变更"""
        if self._on_state_change:
            try:
                await self._on_state_change(
                    stream_id,
                    info.state,
                    {
                        "attempt_count": info.attempt_count,
                        "max_attempts": settings.reconnect_max_attempts,
                        "cooldown_until": info.cooldown_until,
                        "next_delay": info.next_delay,
                        "last_error": info.last_error,
                    }
                )
            except Exception as e:
                logger.error(
                    "state_change_callback_error",
                    stream_id=stream_id,
                    error=str(e)
                )


# 全局重连服务实例
_reconnection_service: Optional[ReconnectionService] = None


def get_reconnection_service() -> ReconnectionService:
    """获取重连服务单例"""
    global _reconnection_service
    if _reconnection_service is None:
        _reconnection_service = ReconnectionService()
    return _reconnection_service


def set_reconnection_service(service: ReconnectionService) -> None:
    """设置重连服务实例（用于测试）"""
    global _reconnection_service
    _reconnection_service = service
