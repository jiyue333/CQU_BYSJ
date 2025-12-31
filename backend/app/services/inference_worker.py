"""推理循环 Worker

订阅 Redis PubSub inference:control 通道接收 START/STOP 指令，
按频率调用 getSnap 抓帧并执行 YOLO 推理。

设计要点：
- 只保最新帧，忙就丢（背压策略）
- 支持多路视频并发推理
- 幂等性：重复 START 忽略，重复 STOP 安全
"""

import asyncio
import json
import random
import time
from enum import Enum
from typing import Optional

import redis.asyncio as redis
import structlog

from app.core.config import settings
from app.core.redis import get_redis
from app.schemas.detection import Detection, DetectionResult, DensityLevel, RegionStat
from app.services.gateway_adapter import get_gateway_adapter, GatewayAdapter
from app.services.inference_service import InferenceService, get_inference_service

logger = structlog.get_logger(__name__)


class StreamHealth(str, Enum):
    """流健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    COOLDOWN = "cooldown"


class InferenceWorker:
    """推理循环 Worker
    
    职责：
    1. 订阅 Redis PubSub inference:control 通道
    2. 收到 START 后启动推理循环
    3. 按频率调用 getSnap 抓帧 + YOLO 推理
    4. 结果写入 Redis Streams
    """
    
    CONTROL_CHANNEL = "inference:control"
    STATUS_STREAM = "inference:status"
    RESULT_STREAM_PREFIX = "result:"
    
    # 指令过期时间（秒）
    CMD_EXPIRE_SEC = 30
    # 已处理指令缓存 TTL（秒）
    CMD_CACHE_TTL = 60
    
    def __init__(
        self,
        inference_service: Optional[InferenceService] = None,
        gateway_adapter: Optional[GatewayAdapter] = None,
    ):
        """初始化 Worker
        
        Args:
            inference_service: 推理服务实例
            gateway_adapter: 网关适配器实例
        """
        self._inference_service = inference_service
        self._gateway_adapter = gateway_adapter
        self._redis: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        
        # 活跃流状态: stream_id -> {"fps": int, "task": asyncio.Task, "running": bool}
        self._active_streams: dict[str, dict] = {}
        
        # 失败计数: stream_id -> int
        self._failure_counts: dict[str, int] = {}
        
        # 流健康状态: stream_id -> StreamHealth
        self._stream_health: dict[str, StreamHealth] = {}
        
        # 已处理的指令 ID 缓存（用于幂等）
        self._processed_cmds: dict[str, float] = {}
        
        # Worker 运行标志
        self._running = False
        
        # 推理锁（保护模型调用的线程安全）
        self._inference_lock: Optional[asyncio.Lock] = None
        
        # 热力图生成器（延迟导入避免循环依赖）
        self._heatmap_generator: Optional["HeatmapGenerator"] = None
        
        # ROI 计算器（延迟导入）
        self._roi_calculator: Optional["ROICalculator"] = None
    
    @property
    def inference_service(self) -> InferenceService:
        """获取推理服务"""
        if self._inference_service is None:
            self._inference_service = get_inference_service()
        return self._inference_service
    
    @property
    def gateway_adapter(self) -> GatewayAdapter:
        """获取网关适配器"""
        if self._gateway_adapter is None:
            self._gateway_adapter = get_gateway_adapter()
        return self._gateway_adapter
    
    async def _get_redis(self) -> redis.Redis:
        """获取 Redis 客户端"""
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis
    
    async def start(self) -> None:
        """启动 Worker"""
        if self._running:
            logger.warning("worker_already_running")
            return
        
        logger.info("starting_inference_worker")
        self._running = True
        
        # 初始化推理锁
        self._inference_lock = asyncio.Lock()
        
        # 预加载模型
        self.inference_service.load_model()
        self.inference_service.warmup()
        
        # 启动控制指令监听
        asyncio.create_task(self._listen_control_channel())
        
        # 启动指令缓存清理任务
        asyncio.create_task(self._cleanup_cmd_cache())
        
        logger.info("inference_worker_started")
    
    async def stop(self) -> None:
        """停止 Worker"""
        logger.info("stopping_inference_worker")
        self._running = False
        
        # 停止所有推理循环
        for stream_id in list(self._active_streams.keys()):
            await self.stop_stream(stream_id)
        
        # 关闭 PubSub
        if self._pubsub:
            await self._pubsub.unsubscribe(self.CONTROL_CHANNEL)
            await self._pubsub.close()
            self._pubsub = None
        
        logger.info("inference_worker_stopped")
    
    async def _listen_control_channel(self) -> None:
        """监听控制指令通道"""
        client = await self._get_redis()
        self._pubsub = client.pubsub()
        await self._pubsub.subscribe(self.CONTROL_CHANNEL)
        
        logger.info("listening_control_channel", channel=self.CONTROL_CHANNEL)
        
        while self._running:
            try:
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )
                
                if message and message["type"] == "message":
                    await self._handle_command(message["data"])
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("control_channel_error", error=str(e))
                await asyncio.sleep(1)
    
    async def _handle_command(self, data: bytes) -> None:
        """处理控制指令
        
        Args:
            data: 指令 JSON 数据
        """
        try:
            message = json.loads(data)
        except json.JSONDecodeError as e:
            logger.error("invalid_command_json", error=str(e))
            return
        
        cmd_id = message.get("cmd_id")
        stream_id = message.get("stream_id")
        action = message.get("action")
        timestamp = message.get("timestamp", 0)
        
        if not all([cmd_id, stream_id, action]):
            logger.warning("incomplete_command", message=message)
            return
        
        # 幂等检查：已处理的指令跳过
        if cmd_id in self._processed_cmds:
            logger.debug("duplicate_command_ignored", cmd_id=cmd_id)
            return
        
        # 过期检查：超过 30 秒的指令忽略
        if time.time() - timestamp > self.CMD_EXPIRE_SEC:
            logger.warning("expired_command_ignored", cmd_id=cmd_id, age_sec=time.time() - timestamp)
            return
        
        # 记录已处理
        self._processed_cmds[cmd_id] = time.time()
        
        logger.info(
            "processing_command",
            cmd_id=cmd_id,
            stream_id=stream_id,
            action=action,
        )
        
        if action == "START":
            fps = message.get("fps", settings.inference_fps)
            await self.start_stream(stream_id, fps)
        elif action == "STOP":
            await self.stop_stream(stream_id)
        else:
            logger.warning("unknown_action", action=action)
    
    async def start_stream(self, stream_id: str, fps: int = 2) -> None:
        """启动某路流的推理
        
        幂等：如果已在运行则忽略。
        
        Args:
            stream_id: 视频流 ID
            fps: 推理频率
        """
        # 幂等检查
        if stream_id in self._active_streams and self._active_streams[stream_id].get("running"):
            logger.debug("stream_already_running", stream_id=stream_id)
            return
        
        # fps 校验
        if fps <= 0:
            logger.warning("invalid_fps_fallback", stream_id=stream_id, fps=fps)
            fps = max(1, settings.inference_fps)
        
        logger.info("starting_stream_inference", stream_id=stream_id, fps=fps)
        
        # 初始化状态
        self._failure_counts[stream_id] = 0
        self._stream_health[stream_id] = StreamHealth.HEALTHY
        
        # 创建推理循环任务
        task = asyncio.create_task(self._inference_loop(stream_id, fps))
        
        self._active_streams[stream_id] = {
            "fps": fps,
            "task": task,
            "running": True,
        }
        
        # 上报状态
        await self._report_status(stream_id, "STARTED", {"fps": fps})
    
    async def stop_stream(self, stream_id: str) -> None:
        """停止某路流的推理
        
        幂等：如果未运行则安全忽略。
        
        Args:
            stream_id: 视频流 ID
        """
        if stream_id not in self._active_streams:
            logger.debug("stream_not_running", stream_id=stream_id)
            return
        
        logger.info("stopping_stream_inference", stream_id=stream_id)
        
        # 标记停止
        self._active_streams[stream_id]["running"] = False
        
        # 取消任务
        task = self._active_streams[stream_id].get("task")
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # 清理状态
        del self._active_streams[stream_id]
        self._failure_counts.pop(stream_id, None)
        self._stream_health.pop(stream_id, None)
        
        # 清理热力图 EMA 状态
        if self._heatmap_generator:
            self._heatmap_generator.reset(stream_id)
        
        # 上报状态
        await self._report_status(stream_id, "STOPPED", {})
    
    async def _inference_loop(self, stream_id: str, fps: int) -> None:
        """推理循环
        
        按频率抓帧 + 推理 + 发布结果。
        
        Args:
            stream_id: 视频流 ID
            fps: 推理频率
        """
        interval = 1.0 / fps
        last_inference_time = 0.0
        
        logger.info("inference_loop_started", stream_id=stream_id, fps=fps, interval_sec=interval)
        
        while self._active_streams.get(stream_id, {}).get("running", False):
            try:
                # 频率控制
                now = time.time()
                elapsed = now - last_inference_time
                if elapsed < interval:
                    await asyncio.sleep(interval - elapsed)
                
                # 检查是否在 COOLDOWN 状态
                if self._stream_health.get(stream_id) == StreamHealth.COOLDOWN:
                    await asyncio.sleep(1)
                    continue
                
                # 抓帧
                start_time = time.time()
                snapshot = await self._get_snapshot(stream_id)
                
                if snapshot is None:
                    await self._handle_failure(stream_id, "snapshot_failed")
                    continue
                
                # 推理（返回检测结果和图像尺寸，避免重复解码）
                result_data = await self._run_inference_with_size(stream_id, snapshot)
                
                if result_data is None:
                    await self._handle_failure(stream_id, "inference_failed")
                    continue
                
                detections, (frame_width, frame_height) = result_data
                
                # 成功：重置失败计数
                self._failure_counts[stream_id] = 0
                if self._stream_health.get(stream_id) != StreamHealth.HEALTHY:
                    self._stream_health[stream_id] = StreamHealth.HEALTHY
                    await self._report_status(stream_id, "HEALTH_UPDATE", {"health": "healthy"})
                
                # 生成热力图
                heatmap_grid = await self._generate_heatmap(stream_id, detections, frame_width, frame_height)
                
                # 计算区域统计（TODO: 从数据库获取 ROI 配置）
                region_stats = await self._calculate_region_stats(stream_id, detections, frame_width, frame_height)
                
                # 构建结果
                result = DetectionResult(
                    stream_id=stream_id,
                    timestamp=time.time(),
                    total_count=len(detections),
                    detections=detections,
                    heatmap_grid=heatmap_grid,
                    region_stats=region_stats,
                )
                
                # 发布结果
                await self._publish_result(stream_id, result)
                
                inference_time = time.time() - start_time
                last_inference_time = time.time()
                
                logger.debug(
                    "inference_complete",
                    stream_id=stream_id,
                    detection_count=len(detections),
                    inference_time_ms=round(inference_time * 1000, 2),
                )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("inference_loop_error", stream_id=stream_id, error=str(e))
                await self._handle_failure(stream_id, f"error: {e}")
        
        logger.info("inference_loop_stopped", stream_id=stream_id)
    
    async def _get_snapshot(self, stream_id: str) -> Optional[bytes]:
        """获取快照
        
        调用网关 getSnap API，带超时和退避。
        """
        try:
            snapshot = await self.gateway_adapter.get_snapshot(
                stream_id,
                timeout_sec=settings.snap_timeout_sec,
            )
            return snapshot
        except Exception as e:
            logger.warning("snapshot_error", stream_id=stream_id, error=str(e))
            return None
    
    async def _run_inference(self, stream_id: str, snapshot: bytes) -> Optional[list[Detection]]:
        """执行推理
        
        在线程池中运行以避免阻塞事件循环。
        使用锁保护模型调用的线程安全。
        """
        try:
            # 使用锁保护模型调用
            async with self._inference_lock:
                loop = asyncio.get_running_loop()
                detections = await loop.run_in_executor(
                    None,
                    self.inference_service.infer_from_bytes,
                    snapshot,
                )
            return detections
        except Exception as e:
            logger.error("inference_error", stream_id=stream_id, error=str(e))
            return None
    
    async def _run_inference_with_size(
        self, stream_id: str, snapshot: bytes
    ) -> Optional[tuple[list[Detection], tuple[int, int]]]:
        """执行推理并返回图像尺寸
        
        避免重复解码图像。
        """
        try:
            async with self._inference_lock:
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None,
                    self.inference_service.infer_with_size,
                    snapshot,
                )
            return result
        except Exception as e:
            logger.error("inference_error", stream_id=stream_id, error=str(e))
            return None
    
    async def _handle_failure(self, stream_id: str, reason: str) -> None:
        """处理失败
        
        累计失败计数，超过阈值进入 COOLDOWN。
        """
        self._failure_counts[stream_id] = self._failure_counts.get(stream_id, 0) + 1
        count = self._failure_counts[stream_id]
        
        logger.warning(
            "inference_failure",
            stream_id=stream_id,
            reason=reason,
            failure_count=count,
        )
        
        # 更新健康状态
        if count >= settings.snap_max_failures:
            await self._enter_cooldown(stream_id)
        elif count >= 3:
            if self._stream_health.get(stream_id) != StreamHealth.DEGRADED:
                self._stream_health[stream_id] = StreamHealth.DEGRADED
                await self._report_status(stream_id, "HEALTH_UPDATE", {
                    "health": "degraded",
                    "failure_count": count,
                })
        
        # 退避等待
        backoff = self._calculate_backoff(count)
        await asyncio.sleep(backoff)
    
    def _calculate_backoff(self, failure_count: int) -> float:
        """计算退避时间
        
        指数退避 + 抖动: min(base * 2^n + jitter, max)
        """
        backoff = min(
            settings.snap_backoff_base * (2 ** failure_count) + random.uniform(0, 1),
            settings.snap_backoff_max
        )
        return backoff
    
    async def _enter_cooldown(self, stream_id: str) -> None:
        """进入 COOLDOWN 状态"""
        logger.warning("entering_cooldown", stream_id=stream_id)
        
        self._stream_health[stream_id] = StreamHealth.COOLDOWN
        cooldown_until = time.time() + settings.cooldown_duration
        
        await self._report_status(stream_id, "COOLDOWN", {
            "health": "cooldown",
            "cooldown_until": cooldown_until,
            "failure_count": self._failure_counts.get(stream_id, 0),
        })
        
        # 启动恢复定时器
        asyncio.create_task(self._cooldown_recovery(stream_id))
    
    async def _cooldown_recovery(self, stream_id: str) -> None:
        """COOLDOWN 恢复"""
        await asyncio.sleep(settings.cooldown_duration)
        
        # 检查流是否仍在运行
        if stream_id not in self._active_streams:
            return
        
        logger.info("cooldown_recovery", stream_id=stream_id)
        
        # 重置状态
        self._failure_counts[stream_id] = 0
        self._stream_health[stream_id] = StreamHealth.HEALTHY
        
        await self._report_status(stream_id, "HEALTH_UPDATE", {"health": "healthy"})
    
    async def _generate_heatmap(
        self,
        stream_id: str,
        detections: list[Detection],
        frame_width: int,
        frame_height: int,
    ) -> list[list[float]]:
        """生成热力图
        
        延迟导入 HeatmapGenerator 避免循环依赖。
        """
        if self._heatmap_generator is None:
            from app.services.heatmap_generator import HeatmapGenerator
            self._heatmap_generator = HeatmapGenerator()
        
        return self._heatmap_generator.generate(
            stream_id, detections, frame_width, frame_height
        )
    
    async def _calculate_region_stats(
        self,
        stream_id: str,
        detections: list[Detection],
        frame_width: int,
        frame_height: int,
    ) -> list[RegionStat]:
        """计算区域统计
        
        TODO: 从数据库获取 ROI 配置，计算各区域密度。
        当前返回空列表，待 ROI 管理 API 实现后完善。
        """
        # 暂时返回空列表
        return []
    
    async def _publish_result(self, stream_id: str, result: DetectionResult) -> None:
        """发布检测结果到 Redis Streams"""
        client = await self._get_redis()
        stream_key = f"{self.RESULT_STREAM_PREFIX}{stream_id}"
        
        try:
            await client.xadd(
                stream_key,
                {"data": result.model_dump_json()},
                maxlen=settings.stream_result_maxlen,
                approximate=True,
            )
        except Exception as e:
            logger.error("publish_result_failed", stream_id=stream_id, error=str(e))
    
    async def _report_status(self, stream_id: str, event: str, data: dict) -> None:
        """上报状态到 Redis Streams"""
        client = await self._get_redis()
        
        message = {
            "stream_id": stream_id,
            "event": event,
            "data": data,
            "timestamp": time.time(),
        }
        
        try:
            await client.xadd(
                self.STATUS_STREAM,
                {"data": json.dumps(message)},
                maxlen=settings.stream_status_maxlen,
                approximate=True,
            )
        except Exception as e:
            logger.error("report_status_failed", stream_id=stream_id, error=str(e))
    
    async def _cleanup_cmd_cache(self) -> None:
        """定期清理已处理指令缓存"""
        while self._running:
            await asyncio.sleep(60)
            
            now = time.time()
            expired = [
                cmd_id for cmd_id, ts in self._processed_cmds.items()
                if now - ts > self.CMD_CACHE_TTL
            ]
            
            for cmd_id in expired:
                del self._processed_cmds[cmd_id]
            
            if expired:
                logger.debug("cleaned_cmd_cache", count=len(expired))
    
    def get_active_streams(self) -> list[str]:
        """获取活跃流列表"""
        return list(self._active_streams.keys())
    
    def get_stream_health(self, stream_id: str) -> Optional[StreamHealth]:
        """获取流健康状态"""
        return self._stream_health.get(stream_id)


# 全局 Worker 实例
_inference_worker: Optional[InferenceWorker] = None


def get_inference_worker() -> InferenceWorker:
    """获取推理 Worker 单例"""
    global _inference_worker
    if _inference_worker is None:
        _inference_worker = InferenceWorker()
    return _inference_worker
