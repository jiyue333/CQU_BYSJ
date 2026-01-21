"""
分析控制 API

处理分析任务的启动、停止和状态查询
推理循环在 API 层编排
"""

import asyncio
import base64
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from typing import Optional

import cv2
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.config import settings
from app.core.logger import logger
from app.models.alert import Alert as AlertModel
from app.repositories import (
    VideoSourceRepository,
    RegionRepository,
    AlertConfigRepository,
    AlertRepository,
)
from app.schemas.common import ApiResponse, OkResponse
from app.schemas.analysis import (
    AnalysisStartRequest,
    AnalysisStopRequest,
    AnalysisStartResponse,
    AnalysisStatusResponse,
)
from app.services.video import VideoService
from app.services.detection import YOLOService, DetectionResult
from app.services.alert import AlertService, AlertConfig
from app.services.stats import stats_aggregator, FrameStats, RegionFrameStats
from app.api.endpoints.websocket import ws_manager
from app.schemas.websocket import RealtimeFrame, RegionRealtimeStats, AlertMessage

router = APIRouter(prefix="/analysis", tags=["分析控制"])

# 分析状态记录
_analysis_state: dict[str, dict] = {}

# 异步任务集合
_tasks: dict[str, asyncio.Task] = {}

# 线程池用于 CPU 密集型推理
_executor = ThreadPoolExecutor(max_workers=4)


def _get_regions_dict(regions: list, img_width: int = 0, img_height: int = 0) -> dict[str, list[tuple]]:
    """
    将数据库区域转换为 YOLO 服务需要的格式

    Args:
        regions: 区域配置列表
        img_width: 图像宽度（用于将百分比坐标转换为像素坐标）
        img_height: 图像高度

    Returns:
        区域字典 {name: [(x1,y1), (x2,y2), ...]}
    """
    result = {}
    for region in regions:
        if region.points:
            try:
                points = json.loads(region.points) if isinstance(region.points, str) else region.points
                # 如果提供了图像尺寸，将百分比坐标转换为像素坐标
                if img_width > 0 and img_height > 0:
                    converted_points = []
                    for p in points:
                        x = p[0] * img_width / 100.0
                        y = p[1] * img_height / 100.0
                        converted_points.append((int(x), int(y)))
                    result[region.name] = converted_points
                else:
                    result[region.name] = [tuple(p) for p in points]
            except json.JSONDecodeError:
                logger.warning(f"区域 {region.name} 的多边形点解析失败")
    return result


def _get_region_id_map(regions: list) -> dict[str, str]:
    """构建区域名称到 ID 的映射"""
    return {region.name: region.region_id for region in regions}


async def _inference_loop(source_id: str) -> None:
    """
    推理循环主函数

    Args:
        source_id: 数据源 ID
    """
    logger.info(f"推理循环启动: {source_id}")

    # 创建独立的数据库会话
    db = SessionLocal()

    try:
        # 1. 获取视频源信息
        source_repo = VideoSourceRepository(db)
        source = source_repo.get_by_id(source_id)
        if not source:
            logger.error(f"数据源不存在: {source_id}")
            return

        # 确定视频路径
        video_path = source.file_path or source.stream_url
        if not video_path:
            logger.error(f"数据源无有效路径: {source_id}")
            return

        # 2. 先打开视频源获取尺寸信息
        video_service = VideoService(video_path)
        if not video_service.open():
            logger.error(f"无法打开视频源: {video_path}")
            source_repo.update_status(source_id, "error")
            return

        video_info = video_service.get_info()
        frame_interval = 1.0 / video_info.fps if video_info.fps > 0 else 1.0 / 30.0

        logger.info(f"视频源已打开: {video_path}, 尺寸={video_info.width}x{video_info.height}, FPS={video_info.fps}")

        # 3. 获取区域配置并转换为像素坐标
        region_repo = RegionRepository(db)
        regions = region_repo.get_by_source_id(source_id)
        regions_dict = _get_regions_dict(regions, video_info.width, video_info.height)
        region_id_map = _get_region_id_map(regions)

        logger.info(f"区域配置: {list(regions_dict.keys()) if regions_dict else '无'}")

        # 4. 获取告警阈值配置
        config_repo = AlertConfigRepository(db)
        alert_config_db = config_repo.get_by_source_id(source_id)

        # 构建告警服务配置
        total_critical = settings.ALERT_TOTAL_CRITICAL
        region_thresholds = {}

        if alert_config_db:
            total_critical = alert_config_db.total_critical_threshold or total_critical

            alert_config = AlertConfig(
                total_warning_threshold=alert_config_db.total_warning_threshold or settings.ALERT_TOTAL_WARNING,
                total_critical_threshold=total_critical,
                default_region_warning=alert_config_db.default_region_warning or 20,
                default_region_critical=alert_config_db.default_region_critical or 50,
                cooldown_seconds=alert_config_db.cooldown_seconds or settings.ALERT_COOLDOWN_SECONDS,
            )

            # 解析区域阈值
            if alert_config_db.region_thresholds:
                try:
                    raw = json.loads(alert_config_db.region_thresholds) if isinstance(
                        alert_config_db.region_thresholds, str
                    ) else alert_config_db.region_thresholds
                    for name, values in raw.items():
                        alert_config.region_thresholds[name] = (values["warning"], values["critical"])
                        region_thresholds[name] = values["critical"]
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"区域阈值解析失败: {e}")
        else:
            alert_config = AlertConfig()

        # 5. 初始化服务
        yolo_service = YOLOService(
            model_path=settings.YOLO_MODEL_PATH,
            regions=regions_dict if regions_dict else None,
            conf=settings.YOLO_CONF_THRESHOLD,
            device=settings.YOLO_DEVICE,
        )
        alert_service = AlertService(config=alert_config)
        alert_repo = AlertRepository(db)

        # 6. 推理循环
        frame_count = 0
        last_flush_time = datetime.utcnow()
        loop = asyncio.get_event_loop()

        try:
            for frame in video_service.frames():
                frame_start_time = asyncio.get_event_loop().time()

                # 检查任务是否被取消
                if asyncio.current_task().cancelled():
                    break

                frame_count += 1
                now = datetime.utcnow()
                timestamp = now.isoformat() + "Z"

                # YOLO 推理（在线程池中执行，避免阻塞事件循环）
                result: DetectionResult = await loop.run_in_executor(
                    _executor, yolo_service.process, frame
                )

                # 构建各区域帧统计（确保所有配置的区域都返回，即使人数为0）
                region_frame_stats = []
                for region_name in regions_dict.keys():
                    count = result.region_counts.get(region_name, 0)
                    density = result.region_densities.get(region_name, 0.0)
                    region_frame_stats.append(RegionFrameStats(
                        region_id=region_id_map.get(region_name, ""),
                        name=region_name,
                        count=count,
                        density=density,
                    ))

                # 告警检查
                alerts = alert_service.check(result)
                for alert in alerts:
                    # 保存到数据库
                    alert_model = AlertModel(
                        alert_id=alert.alert_id,
                        source_id=source_id,
                        alert_type=alert.alert_type.value,
                        level=alert.level.value,
                        region_id=region_id_map.get(alert.region_name) if alert.region_name else None,
                        region_name=alert.region_name,
                        current_value=alert.current_value,
                        threshold=alert.threshold,
                        timestamp=timestamp,
                        message=f"{'总人数' if alert.alert_type.value == 'total_count' else alert.region_name}达到{alert.level.value}阈值: {alert.current_value}/{alert.threshold}",
                    )
                    alert_repo.create(alert_model)
                    logger.info(f"告警已保存: {alert.alert_type.value} - {alert.level.value}")

                    # WebSocket 推送告警
                    alert_msg = AlertMessage(
                        alert_id=alert.alert_id,
                        alert_type=alert.alert_type.value,
                        level=alert.level.value,
                        region_id=region_id_map.get(alert.region_name) if alert.region_name else None,
                        region_name=alert.region_name,
                        current_value=alert.current_value,
                        threshold=alert.threshold,
                        timestamp=timestamp,
                        message=alert_model.message or "",
                    )
                    await ws_manager.send_alert(source_id, alert_msg)

                # 统计聚合
                frame_stats = FrameStats(
                    source_id=source_id,
                    timestamp=timestamp,
                    total_count=result.total_count,
                    total_density=result.total_density,
                    regions=region_frame_stats,
                )
                stats_aggregator.collect(frame_stats)

                # 每分钟刷新一次聚合数据到数据库
                if (now - last_flush_time).total_seconds() >= 60:
                    stats_aggregator.flush(db)
                    last_flush_time = now

                # 编码帧为 base64（用于 WebSocket）
                _, buffer = cv2.imencode(".jpg", result.frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                frame_base64 = base64.b64encode(buffer).decode("utf-8")

                # 构造区域实时统计（简化版，仅当前帧数据）
                regions_realtime: dict[str, RegionRealtimeStats] = {}
                for rf in region_frame_stats:
                    regions_realtime[rf.region_id] = RegionRealtimeStats(
                        total_count_avg=float(rf.count),
                        total_count_max=rf.count,
                        total_count_min=rf.count,
                        total_density_avg=rf.density,
                    )

                # WebSocket 推送实时帧
                realtime_frame = RealtimeFrame(
                    ts=timestamp,
                    frame=frame_base64,
                    total_count=result.total_count,
                    total_density=result.total_density,
                    regions=regions_realtime,
                    entry_speed=0.0,  # TODO: 计算入场速度
                )
                await ws_manager.send_frame(source_id, realtime_frame)

                # 控制帧率（扣除已消耗的时间）
                elapsed = asyncio.get_event_loop().time() - frame_start_time
                sleep_time = max(0, frame_interval - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

        except asyncio.CancelledError:
            logger.info(f"推理任务被取消: {source_id}")
            raise
        finally:
            video_service.close()

            # 最后刷新一次统计数据
            stats_aggregator.flush(db)

    except asyncio.CancelledError:
        logger.info(f"推理循环已停止: {source_id}")
    except Exception as e:
        logger.exception(f"推理循环异常: {source_id}, {e}")
        # 更新状态为错误
        try:
            source_repo = VideoSourceRepository(db)
            source_repo.update_status(source_id, "error")
        except Exception:
            pass
    finally:
        db.close()

        # 清理任务引用
        if source_id in _tasks:
            del _tasks[source_id]

        # 更新状态
        if source_id in _analysis_state:
            _analysis_state[source_id]["status"] = "stopped"

        logger.info(f"推理循环结束: {source_id}")


@router.post("/start", response_model=ApiResponse[AnalysisStartResponse])
async def start_analysis(
    request: AnalysisStartRequest,
    db: Session = Depends(get_db),
):
    """开始分析"""
    source_repo = VideoSourceRepository(db)
    source = source_repo.get_by_id(request.source_id)

    if not source:
        raise HTTPException(status_code=404, detail="数据源不存在")

    # if source.status == "running":
        # raise HTTPException(status_code=400, detail="分析任务已在运行中")

    # 检查是否已有运行中的任务
    if request.source_id in _tasks and not _tasks[request.source_id].done():
        raise HTTPException(status_code=400, detail="分析任务已在运行中")

    # 更新数据源状态
    source_repo.update_status(request.source_id, "running")

    # 记录分析状态
    _analysis_state[request.source_id] = {
        "status": "running",
        "start_time": datetime.utcnow().isoformat() + "Z",
    }

    # 创建并启动推理任务
    task = asyncio.create_task(_inference_loop(request.source_id))
    _tasks[request.source_id] = task

    logger.info(f"分析任务已启动: {request.source_id}")

    return ApiResponse.success(
        data=AnalysisStartResponse(source_id=request.source_id, status="running")
    )


@router.post("/stop", response_model=ApiResponse[OkResponse])
async def stop_analysis(
    request: AnalysisStopRequest,
    db: Session = Depends(get_db),
):
    """停止分析"""
    source_repo = VideoSourceRepository(db)
    source = source_repo.get_by_id(request.source_id)

    if not source:
        raise HTTPException(status_code=404, detail="数据源不存在")

    # 取消推理任务
    task = _tasks.get(request.source_id)
    if task:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        # 任务可能在 finally 中已删除自己，用 pop 避免 KeyError
        _tasks.pop(request.source_id, None)

    # 更新状态
    source_repo.update_status(request.source_id, "stopped")

    # 清除分析状态
    if request.source_id in _analysis_state:
        _analysis_state[request.source_id]["status"] = "stopped"

    logger.info(f"分析任务已停止: {request.source_id}")

    return ApiResponse.success(data=OkResponse(ok=True))


@router.get("/status", response_model=ApiResponse[AnalysisStatusResponse])
async def get_analysis_status(
    source_id: str = Query(..., description="数据源 ID"),
    db: Session = Depends(get_db),
):
    """查询分析状态"""
    source_repo = VideoSourceRepository(db)
    source = source_repo.get_by_id(source_id)

    if not source:
        raise HTTPException(status_code=404, detail="数据源不存在")

    state = _analysis_state.get(source_id, {})

    return ApiResponse.success(
        data=AnalysisStatusResponse(
            source_id=source_id,
            status=source.status,
            start_time=state.get("start_time"),
        )
    )
