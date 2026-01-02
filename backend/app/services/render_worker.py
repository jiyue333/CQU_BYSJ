"""渲染循环 Worker

订阅 Redis PubSub render:control 通道接收 START/STOP 指令，
使用 ffmpeg 拉流解码 → YOLO 推理 → 热力图叠加 → ffmpeg 编码推流。

方案 F：服务端渲染热力图
- 严格对齐模式：推理帧同帧叠加，非推理帧复用缓存 heatmap
- 渲染 24fps / 推理 8fps（每 3 帧推理一次）
- 延迟 1-5s

设计要点：
- ffmpeg subprocess 拉流/推流，避免 OpenCV VideoCapture 容器兼容问题
- 幂等性：重复 START 忽略，重复 STOP 安全
- 状态上报到 inference:status（复用 StatusPushService）
"""

import asyncio
import json
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import cv2
import numpy as np
import redis.asyncio as redis
import structlog
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_maker
from app.core.redis import get_redis
from app.schemas.detection import Detection, DetectionResult, RegionStat
from app.schemas.roi import DensityThresholds, Point
from app.services.heatmap_generator import HeatmapGenerator
from app.services.inference_service import InferenceService, get_inference_service
from app.services.roi_calculator import ROICalculator
from app.models.roi import ROI

logger = structlog.get_logger(__name__)


class RenderHealth(str, Enum):
    """渲染健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    COOLDOWN = "cooldown"


@dataclass
class RenderConfig:
    """渲染配置"""
    stream_id: str
    render_stream_id: str
    src_rtsp_url: str
    dst_rtmp_url: str
    render_fps: int = 24
    infer_stride: int = 3
    overlay_alpha: float = 0.4


@dataclass
class CachedROI:
    """缓存的 ROI 配置"""
    roi_id: str
    name: str
    points: list[Point]
    thresholds: DensityThresholds
    area: float


@dataclass
class ROICacheEntry:
    """ROI 缓存条目"""
    rois: list[CachedROI]
    fetched_at: float


@dataclass
class RenderMetricsState:
    """渲染指标状态"""
    last_report_ts: float
    frame_count: int = 0
    infer_count: int = 0
    last_frame_ts: Optional[float] = None
    last_latency_ms: float = 0.0


class RenderWorker:
    """渲染循环 Worker
    
    职责：
    1. 订阅 Redis PubSub render:control 通道
    2. 收到 START 后启动渲染循环
    3. ffmpeg 拉流 → 推理 → 热力图叠加 → ffmpeg 推流
    4. 结果写入 Redis Streams
    5. 状态上报到 inference:status（复用 StatusPushService）
    """
    
    CONTROL_CHANNEL = "render:control"
    STATUS_STREAM = "inference:status"  # 复用现有 Stream
    RESULT_STREAM_PREFIX = "result:"
    LATEST_RESULT_PREFIX = "latest_result:"
    ROI_UPDATED_CHANNEL = "roi:updated"
    
    # 指令过期时间（秒）
    CMD_EXPIRE_SEC = 30
    # 已处理指令缓存 TTL（秒）
    CMD_CACHE_TTL = 60
    # 最大连续失败次数
    MAX_FAILURES = 5
    # COOLDOWN 持续时间（秒）
    COOLDOWN_DURATION = 60
    # ROI 缓存 TTL（秒）
    ROI_CACHE_TTL = 5
    
    def __init__(
        self,
        inference_service: Optional[InferenceService] = None,
    ):
        """初始化 Worker
        
        Args:
            inference_service: 推理服务实例
        """
        self._inference_service = inference_service
        self._redis: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        
        # 活跃流状态: stream_id -> {"config": RenderConfig, "task": asyncio.Task, "running": bool}
        self._active_streams: dict[str, dict] = {}
        
        # 失败计数: stream_id -> int
        self._failure_counts: dict[str, int] = {}
        
        # 流健康状态: stream_id -> RenderHealth
        self._stream_health: dict[str, RenderHealth] = {}
        
        # 已处理的指令 ID 缓存（用于幂等）
        self._processed_cmds: dict[str, float] = {}
        
        # Worker 运行标志
        self._running = False
        
        # 推理锁（保护模型调用的线程安全）
        self._inference_lock: Optional[asyncio.Lock] = None
        
        # 流操作锁（保护 start_stream/stop_stream 的并发安全）
        self._stream_lock: Optional[asyncio.Lock] = None
        
        # 热力图生成器
        self._heatmap_generator: Optional[HeatmapGenerator] = None

        # ROI 缓存与订阅
        self._roi_cache: dict[str, ROICacheEntry] = {}
        self._roi_cache_lock: Optional[asyncio.Lock] = None
        self._roi_pubsub: Optional[redis.client.PubSub] = None
        self._roi_listener_task: Optional[asyncio.Task] = None

        # 渲染指标状态
        self._metrics_state: dict[str, RenderMetricsState] = {}
    
    @property
    def inference_service(self) -> InferenceService:
        """获取推理服务"""
        if self._inference_service is None:
            self._inference_service = get_inference_service()
        return self._inference_service
    
    @property
    def heatmap_generator(self) -> HeatmapGenerator:
        """获取热力图生成器"""
        if self._heatmap_generator is None:
            self._heatmap_generator = HeatmapGenerator()
        return self._heatmap_generator
    
    async def _get_redis(self) -> redis.Redis:
        """获取 Redis 客户端"""
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis
    
    async def start(self) -> None:
        """启动 Worker"""
        if self._running:
            logger.warning("render_worker_already_running")
            return
        
        logger.info("starting_render_worker")
        self._running = True
        
        # 初始化锁
        self._inference_lock = asyncio.Lock()
        self._stream_lock = asyncio.Lock()
        self._roi_cache_lock = asyncio.Lock()
        
        # 预加载模型
        self.inference_service.load_model()
        self.inference_service.warmup()
        
        # 启动控制指令监听
        asyncio.create_task(self._listen_control_channel())

        # 启动 ROI 更新订阅
        self._roi_listener_task = asyncio.create_task(self._listen_roi_updates())
        
        # 启动指令缓存清理任务
        asyncio.create_task(self._cleanup_cmd_cache())
        
        logger.info("render_worker_started")
    
    async def stop(self) -> None:
        """停止 Worker"""
        logger.info("stopping_render_worker")
        self._running = False
        
        # 停止所有渲染循环
        for stream_id in list(self._active_streams.keys()):
            await self.stop_stream(stream_id)
        
        # 关闭 PubSub
        if self._pubsub:
            await self._pubsub.unsubscribe(self.CONTROL_CHANNEL)
            await self._pubsub.close()
            self._pubsub = None

        if self._roi_pubsub:
            await self._roi_pubsub.unsubscribe(self.ROI_UPDATED_CHANNEL)
            await self._roi_pubsub.close()
            self._roi_pubsub = None

        if self._roi_listener_task:
            self._roi_listener_task.cancel()
            try:
                await self._roi_listener_task
            except asyncio.CancelledError:
                pass
        
        logger.info("render_worker_stopped")
    
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

    async def _listen_roi_updates(self) -> None:
        """监听 ROI 更新通知，刷新缓存"""
        client = await self._get_redis()
        self._roi_pubsub = client.pubsub()
        await self._roi_pubsub.subscribe(self.ROI_UPDATED_CHANNEL)

        logger.info("listening_roi_updates", channel=self.ROI_UPDATED_CHANNEL)

        while self._running:
            try:
                message = await self._roi_pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )

                if message and message.get("type") == "message":
                    payload = message.get("data")
                    if isinstance(payload, bytes):
                        payload = payload.decode()
                    stream_id = payload
                    if stream_id:
                        async with self._roi_cache_lock:
                            self._roi_cache.pop(stream_id, None)
                        logger.debug("roi_cache_invalidated", stream_id=stream_id)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("roi_update_listener_error", error=str(e))
                await asyncio.sleep(1)

    async def _load_rois(self, stream_id: str) -> list[CachedROI]:
        """从数据库加载 ROI 配置"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(ROI).where(ROI.stream_id == stream_id).order_by(ROI.created_at)
            )
            rois = result.scalars().all()

        cached_rois: list[CachedROI] = []
        for roi in rois:
            points = [Point(**p) for p in roi.points]
            thresholds = DensityThresholds(**roi.density_thresholds)
            area = ROICalculator.polygon_area(points)
            cached_rois.append(
                CachedROI(
                    roi_id=roi.id,
                    name=roi.name,
                    points=points,
                    thresholds=thresholds,
                    area=area,
                )
            )

        return cached_rois

    async def _get_cached_rois(self, stream_id: str) -> list[CachedROI]:
        """获取缓存的 ROI 列表（带 TTL）"""
        now = time.time()
        if self._roi_cache_lock is None:
            self._roi_cache_lock = asyncio.Lock()

        async with self._roi_cache_lock:
            cache_entry = self._roi_cache.get(stream_id)
            if cache_entry and now - cache_entry.fetched_at < self.ROI_CACHE_TTL:
                return cache_entry.rois

        try:
            rois = await self._load_rois(stream_id)
        except Exception as e:
            logger.warning("load_rois_failed", stream_id=stream_id, error=str(e))
            rois = []

        async with self._roi_cache_lock:
            self._roi_cache[stream_id] = ROICacheEntry(rois=rois, fetched_at=now)

        return rois

    async def _calculate_region_stats(
        self,
        stream_id: str,
        detections: list[Detection],
    ) -> list[RegionStat]:
        """计算 ROI 区域统计"""
        rois = await self._get_cached_rois(stream_id)
        if not rois:
            return []

        stats: list[RegionStat] = []
        for roi in rois:
            stat = ROICalculator.calculate_region_stat(
                region_id=roi.roi_id,
                region_name=roi.name,
                polygon=roi.points,
                thresholds=roi.thresholds,
                detections=detections,
                precomputed_area=roi.area,
            )
            stats.append(stat)

        return stats
    
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
            params = message.get("params", {})
            config = RenderConfig(
                stream_id=stream_id,
                render_stream_id=params.get("render_stream_id", f"{stream_id}_heatmap"),
                src_rtsp_url=params.get("src_rtsp_url", ""),
                dst_rtmp_url=params.get("dst_rtmp_url", ""),
                render_fps=params.get("render_fps", settings.render_fps),
                infer_stride=params.get("infer_stride", settings.render_infer_stride),
                overlay_alpha=params.get("overlay_alpha", settings.render_overlay_alpha),
            )
            await self.start_stream(config)
        elif action == "STOP":
            await self.stop_stream(stream_id)
        else:
            logger.warning("unknown_action", action=action)
    
    async def start_stream(self, config: RenderConfig) -> None:
        """启动某路流的渲染
        
        幂等：如果已在运行则忽略。
        使用锁保护并发安全。
        
        Args:
            config: 渲染配置
        """
        stream_id = config.stream_id
        
        async with self._stream_lock:
            # 幂等检查
            if stream_id in self._active_streams and self._active_streams[stream_id].get("running"):
                logger.debug("stream_already_running", stream_id=stream_id)
                return
            
            # 并发限制检查
            running_count = sum(1 for s in self._active_streams.values() if s.get("running"))
            if running_count >= settings.render_max_concurrent:
                logger.warning(
                    "render_concurrent_limit_reached",
                    stream_id=stream_id,
                    limit=settings.render_max_concurrent
                )
                await self._report_status(stream_id, "ERROR", {"reason": "concurrent_limit_reached"})
                return
            
            logger.info(
                "starting_stream_render",
                stream_id=stream_id,
                render_fps=config.render_fps,
                infer_stride=config.infer_stride,
            )
            
            # 初始化状态
            self._failure_counts[stream_id] = 0
            self._stream_health[stream_id] = RenderHealth.HEALTHY
            
            # 创建渲染循环任务
            task = asyncio.create_task(self._render_loop(config))
            
            self._active_streams[stream_id] = {
                "config": config,
                "task": task,
                "running": True,
            }
        
        # 上报状态（在锁外执行，避免死锁）
        await self._report_status(stream_id, "STARTED", {
            "render_fps": config.render_fps,
            "infer_stride": config.infer_stride,
        })
    
    async def stop_stream(self, stream_id: str) -> None:
        """停止某路流的渲染
        
        幂等：如果未运行则安全忽略。
        使用锁保护并发安全。
        
        Args:
            stream_id: 视频流 ID
        """
        async with self._stream_lock:
            if stream_id not in self._active_streams:
                logger.debug("stream_not_running", stream_id=stream_id)
                return
            
            logger.info("stopping_stream_render", stream_id=stream_id)
            
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
            self._roi_cache.pop(stream_id, None)
            self._metrics_state.pop(stream_id, None)
            
            # 清理热力图 EMA 状态
            if self._heatmap_generator:
                self._heatmap_generator.reset(stream_id)
        
        # 上报状态（在锁外执行，避免死锁）
        await self._report_status(stream_id, "STOPPED", {})

    async def _render_loop(self, config: RenderConfig) -> None:
        """渲染循环
        
        ffmpeg 拉流 → 推理 → 热力图叠加 → ffmpeg 推流
        
        Args:
            config: 渲染配置
        """
        stream_id = config.stream_id
        
        # 默认分辨率（会在首帧时更新）
        width, height = 1280, 720
        frame_size = width * height * 3
        
        reader: Optional[subprocess.Popen] = None
        writer: Optional[subprocess.Popen] = None
        
        frame_count = 0
        cached_heatmap: Optional[list[list[float]]] = None
        
        logger.info(
            "render_loop_started",
            stream_id=stream_id,
            src=config.src_rtsp_url,
            dst=config.dst_rtmp_url,
        )
        
        try:
            # 启动 ffmpeg reader
            reader = self._create_ffmpeg_reader(
                config.src_rtsp_url, width, height, config.render_fps
            )
            
            # 启动 ffmpeg writer
            writer = self._create_ffmpeg_writer(
                config.dst_rtmp_url, width, height, config.render_fps
            )
            
            while self._active_streams.get(stream_id, {}).get("running", False):
                try:
                    # 检查是否在 COOLDOWN 状态
                    if self._stream_health.get(stream_id) == RenderHealth.COOLDOWN:
                        await asyncio.sleep(1)
                        continue
                    
                    # 读取帧（在线程池中执行避免阻塞）
                    raw_frame = await asyncio.get_event_loop().run_in_executor(
                        None, reader.stdout.read, frame_size
                    )
                    
                    if len(raw_frame) != frame_size:
                        await self._handle_failure(stream_id, "read_frame_failed")
                        continue
                    
                    # 转换为 numpy 数组
                    frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape((height, width, 3))
                    capture_ts = time.time()
                    
                    did_infer = False

                    # 每 N 帧推理一次（严格对齐模式）
                    if frame_count % config.infer_stride == 0:
                        did_infer = True
                        # 执行推理
                        detections = await self._run_inference(stream_id, frame)
                        
                        if detections is not None:
                            # 生成热力图
                            cached_heatmap = self.heatmap_generator.generate(
                                stream_id, detections, width, height
                            )
                            
                            # 发布结果
                            await self._publish_result(
                                stream_id, detections, cached_heatmap,
                                width, height, capture_ts
                            )
                            
                            # 重置失败计数
                            self._failure_counts[stream_id] = 0
                            if self._stream_health.get(stream_id) != RenderHealth.HEALTHY:
                                self._stream_health[stream_id] = RenderHealth.HEALTHY
                        else:
                            await self._handle_failure(stream_id, "inference_failed")
                    
                    # 叠加热力图（使用缓存的 heatmap）
                    if cached_heatmap is not None:
                        processed_frame = self._draw_heatmap_overlay(
                            frame, cached_heatmap, config.overlay_alpha
                        )
                    else:
                        processed_frame = frame
                    
                    # 写入帧（在线程池中执行避免阻塞）
                    await asyncio.get_event_loop().run_in_executor(
                        None, writer.stdin.write, processed_frame.tobytes()
                    )

                    frame_count += 1

                    # 上报指标
                    await self._maybe_report_metrics(stream_id, capture_ts, did_infer)
                    
                except asyncio.CancelledError:
                    break
                except BrokenPipeError:
                    logger.error("ffmpeg_pipe_broken", stream_id=stream_id)
                    await self._handle_failure(stream_id, "pipe_broken")
                    break
                except Exception as e:
                    logger.error("render_loop_error", stream_id=stream_id, error=str(e))
                    await self._handle_failure(stream_id, f"error: {e}")
        
        except Exception as e:
            logger.error("render_loop_init_failed", stream_id=stream_id, error=str(e))
            await self._report_status(stream_id, "ERROR", {"reason": str(e)})
        
        finally:
            # 清理 ffmpeg 进程
            if reader:
                reader.terminate()
                try:
                    reader.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    reader.kill()
            
            if writer:
                if writer.stdin:
                    try:
                        writer.stdin.close()
                    except Exception:
                        pass
                writer.terminate()
                try:
                    writer.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    writer.kill()
            
            logger.info("render_loop_stopped", stream_id=stream_id, frame_count=frame_count)
    
    def _create_ffmpeg_reader(
        self,
        src_url: str,
        width: int,
        height: int,
        fps: int,
    ) -> subprocess.Popen:
        """创建 ffmpeg 拉流解码进程
        
        支持 HTTP-FLV 和 RTSP 输入。
        使用 -vf scale 确保输出分辨率一致，避免源流分辨率不匹配问题。
        stderr 设为 DEVNULL 避免管道阻塞。
        """
        # 根据 URL 协议选择不同的输入参数
        if src_url.startswith("rtsp://"):
            # RTSP 协议需要指定传输方式
            input_args = ["-rtsp_transport", "tcp", "-i", src_url]
        else:
            # HTTP-FLV 等其他协议
            input_args = ["-i", src_url]
        
        cmd = [
            "ffmpeg",
            *input_args,
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-vf", f"scale={width}:{height}",  # 使用 scale filter 确保分辨率一致
            "-r", str(fps),
            "-an",
            "-sn",
            "-loglevel", "warning",
            "pipe:1"
        ]
        
        return subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,  # 避免 stderr 缓冲区满导致阻塞
            bufsize=width * height * 3 * 2
        )
    
    def _create_ffmpeg_writer(
        self,
        dst_url: str,
        width: int,
        height: int,
        fps: int,
    ) -> subprocess.Popen:
        """创建 ffmpeg 编码推流进程
        
        添加 -pix_fmt yuv420p 确保输出兼容性。
        stderr 设为 DEVNULL 避免管道阻塞。
        """
        cmd = [
            "ffmpeg",
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-s", f"{width}x{height}",
            "-r", str(fps),
            "-i", "pipe:0",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",  # 确保输出兼容性
            "-preset", settings.render_ffmpeg_preset,
            "-tune", settings.render_ffmpeg_tune,
            "-g", str(fps * 2),
            "-bf", "0",
            "-f", "flv",
            "-loglevel", "warning",
            dst_url
        ]
        
        return subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL,  # 避免 stderr 缓冲区满导致阻塞
            bufsize=width * height * 3 * 2
        )
    
    def _draw_heatmap_overlay(
        self,
        frame: np.ndarray,
        heatmap: list[list[float]],
        alpha: float,
    ) -> np.ndarray:
        """在帧上叠加热力图
        
        复用 demo_inference.py 的算法
        """
        h, w = frame.shape[:2]
        
        # 转换为 numpy 数组
        heatmap_array = np.array(heatmap, dtype=np.float32)
        
        # 缩放到帧尺寸
        heatmap_resized = cv2.resize(heatmap_array, (w, h), interpolation=cv2.INTER_LINEAR)
        
        # 归一化到 0-255
        heatmap_normalized = (heatmap_resized * 255).astype(np.uint8)
        
        # 应用颜色映射 (COLORMAP_JET: 蓝->绿->黄->红)
        heatmap_colored = cv2.applyColorMap(heatmap_normalized, cv2.COLORMAP_JET)
        
        # 叠加到原图
        result = cv2.addWeighted(frame, 1 - alpha, heatmap_colored, alpha, 0)
        
        return result
    
    async def _run_inference(
        self,
        stream_id: str,
        frame: np.ndarray,
    ) -> Optional[list[Detection]]:
        """执行推理
        
        使用锁保护模型调用的线程安全。
        """
        try:
            async with self._inference_lock:
                # 在线程池中执行推理
                detections = await asyncio.get_event_loop().run_in_executor(
                    None, self.inference_service.infer_from_numpy, frame
                )
                return detections
        except Exception as e:
            logger.warning("inference_error", stream_id=stream_id, error=str(e))
            return None

    async def _handle_failure(self, stream_id: str, reason: str) -> None:
        """处理失败
        
        累计失败计数，超过阈值进入 COOLDOWN。
        """
        self._failure_counts[stream_id] = self._failure_counts.get(stream_id, 0) + 1
        count = self._failure_counts[stream_id]
        
        logger.warning(
            "render_failure",
            stream_id=stream_id,
            reason=reason,
            failure_count=count,
        )
        
        if count >= self.MAX_FAILURES:
            await self._enter_cooldown(stream_id)
    
    async def _enter_cooldown(self, stream_id: str) -> None:
        """进入 COOLDOWN 状态"""
        logger.warning("entering_cooldown", stream_id=stream_id)
        
        self._stream_health[stream_id] = RenderHealth.COOLDOWN
        
        # 上报 COOLDOWN 状态
        await self._report_status(stream_id, "COOLDOWN", {
            "duration": self.COOLDOWN_DURATION,
        })
        
        # 启动恢复任务
        asyncio.create_task(self._cooldown_recovery(stream_id))
    
    async def _cooldown_recovery(self, stream_id: str) -> None:
        """COOLDOWN 恢复"""
        await asyncio.sleep(self.COOLDOWN_DURATION)
        
        if stream_id not in self._active_streams:
            return
        
        if self._stream_health.get(stream_id) == RenderHealth.COOLDOWN:
            self._stream_health[stream_id] = RenderHealth.HEALTHY
            self._failure_counts[stream_id] = 0
            
            logger.info("cooldown_recovered", stream_id=stream_id)
            await self._report_status(stream_id, "HEALTH_UPDATE", {"health": "healthy"})
    
    async def _publish_result(
        self,
        stream_id: str,
        detections: list[Detection],
        heatmap_grid: list[list[float]],
        frame_width: int,
        frame_height: int,
        capture_ts: float,
    ) -> None:
        """发布检测结果到 Redis Streams"""
        client = await self._get_redis()
        region_stats = await self._calculate_region_stats(stream_id, detections)

        result = DetectionResult(
            stream_id=stream_id,
            capture_ts=capture_ts,
            timestamp=time.time(),
            total_count=len(detections),
            frame_width=frame_width,
            frame_height=frame_height,
            detections=detections,
            heatmap_grid=heatmap_grid,
            region_stats=region_stats,
        )
        
        result_json = result.model_dump_json()
        
        try:
            # 写入结果 Stream
            stream_key = f"{self.RESULT_STREAM_PREFIX}{stream_id}"
            await client.xadd(
                stream_key,
                {"data": result_json},
                maxlen=settings.stream_result_maxlen,
                approximate=True,
            )
            
            # 写入 latest_result（供 API 查询），使用配置的 TTL
            latest_key = f"{self.LATEST_RESULT_PREFIX}{stream_id}"
            await client.set(latest_key, result_json, ex=settings.render_latest_result_ttl)
            
        except Exception as e:
            logger.error("publish_result_failed", stream_id=stream_id, error=str(e))

    async def _maybe_report_metrics(
        self,
        stream_id: str,
        capture_ts: float,
        did_infer: bool,
    ) -> None:
        """统计并按间隔上报渲染指标"""
        now = time.time()
        state = self._metrics_state.get(stream_id)
        if state is None:
            state = RenderMetricsState(last_report_ts=now)
            self._metrics_state[stream_id] = state

        state.frame_count += 1
        if did_infer:
            state.infer_count += 1
        state.last_frame_ts = capture_ts
        state.last_latency_ms = max(0.0, (now - capture_ts) * 1000.0)

        interval = max(0.5, settings.metrics_push_interval_sec)
        if now - state.last_report_ts < interval:
            return

        elapsed = max(now - state.last_report_ts, 0.001)
        render_fps_actual = state.frame_count / elapsed
        infer_fps_actual = state.infer_count / elapsed

        health = self._stream_health.get(stream_id, RenderHealth.HEALTHY)
        if health == RenderHealth.COOLDOWN:
            health_state = "cooldown"
            status = "cooldown"
        elif self._failure_counts.get(stream_id, 0) > 0:
            health_state = "degraded"
            status = "running"
        else:
            health_state = "healthy"
            status = "running"

        metrics = {
            "render_fps_actual": round(render_fps_actual, 2),
            "infer_fps_actual": round(infer_fps_actual, 2),
            "last_frame_ts": state.last_frame_ts,
            "latency_ms": round(state.last_latency_ms, 2),
            "health": health_state,
            "state": status,
        }

        state.frame_count = 0
        state.infer_count = 0
        state.last_report_ts = now

        await self._report_metrics(stream_id, status, metrics)

    async def _report_metrics(self, stream_id: str, status: str, metrics: dict) -> None:
        """上报渲染指标到状态 Stream"""
        client = await self._get_redis()
        message = {
            "stream_id": stream_id,
            "event": "METRICS",
            "status": status,
            "metrics": metrics,
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
            logger.error("report_metrics_failed", stream_id=stream_id, error=str(e))
    
    async def _report_status(self, stream_id: str, event: str, data: dict) -> None:
        """上报状态到 Redis Streams
        
        复用 inference:status Stream，与 StatusPushService 兼容。
        事件映射：
        - STARTED -> running
        - STOPPED -> stopped
        - COOLDOWN -> cooldown
        - ERROR -> error
        - HEALTH_UPDATE -> 被忽略（不影响前端状态）
        """
        client = await self._get_redis()
        
        # 事件到状态的映射（与 StatusPushService 兼容）
        event_to_status = {
            "STARTED": "running",
            "STOPPED": "stopped",
            "COOLDOWN": "cooldown",
            "ERROR": "error",
        }
        
        message = {
            "stream_id": stream_id,
            "event": event,
            "data": data,
            "timestamp": time.time(),
        }
        
        # 添加 status 字段确保 StatusPushService 能正确处理
        if event in event_to_status:
            message["status"] = event_to_status[event]
        
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
    
    def get_stream_health(self, stream_id: str) -> Optional[RenderHealth]:
        """获取流健康状态"""
        return self._stream_health.get(stream_id)


# 全局 Worker 实例
_render_worker: Optional[RenderWorker] = None


def get_render_worker() -> RenderWorker:
    """获取渲染 Worker 单例"""
    global _render_worker
    if _render_worker is None:
        _render_worker = RenderWorker()
    return _render_worker
