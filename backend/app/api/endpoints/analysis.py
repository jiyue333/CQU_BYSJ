"""
分析控制 API

处理分析任务的启动、停止和状态查询
推理循环在 API 层编排：DM-Count（降频）+ YOLO（每帧）
"""

import asyncio
import base64
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.config import settings
from app.core.logger import logger
from app.models.alert import Alert as AlertModel
from app.repositories import (
    VideoSourceRepository,
    RegionRepository,
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
from app.services.density import DMCountService
from app.services.alert import AlertService, RegionAlertMetrics, RegionThresholdConfig
from app.services.stats import stats_aggregator, FrameStats, RegionFrameStats
from app.api.endpoints.websocket import ws_manager
from app.schemas.websocket import AlertMessage, RealtimeFrame, RegionRealtimeStats

router = APIRouter(prefix="/analysis", tags=["分析控制"])

# 分析状态记录
_analysis_state: dict[str, dict] = {}

# 异步任务集合
_tasks: dict[str, asyncio.Task] = {}

# 线程池：YOLO 和 DM-Count 分开
_yolo_executor = ThreadPoolExecutor(max_workers=2)
_dmcount_executor = ThreadPoolExecutor(max_workers=1)

# 参考帧目录
_REF_FRAMES_DIR = Path(settings.DATA_DIR) / "ref_frames"


def _dmcount_region_counts(
    density_map: np.ndarray,
    regions_dict: dict[str, list[tuple]],
    img_width: int,
    img_height: int,
) -> dict[str, float]:
    """在密度图上按区域多边形求和，得到每个区域的 DM-Count 人数"""
    dm_h, dm_w = density_map.shape[:2]
    result: dict[str, float] = {}
    for name, pixel_points in regions_dict.items():
        # 将像素坐标映射到密度图尺寸
        pts = np.array(
            [
                [p[0] * dm_w / img_width, p[1] * dm_h / img_height]
                for p in pixel_points
            ],
            dtype=np.int32,
        )
        mask = np.zeros((dm_h, dm_w), dtype=np.uint8)
        cv2.fillPoly(mask, [pts], 1)
        region_count = float(np.sum(density_map * mask))
        result[name] = region_count
    return result


def _get_regions_dict(regions: list, img_width: int = 0, img_height: int = 0) -> dict[str, list[tuple]]:
    """将数据库区域转换为 YOLO 服务需要的格式"""
    result = {}
    for region in regions:
        if region.points:
            try:
                points = json.loads(region.points) if isinstance(region.points, str) else region.points
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


def save_reference_frame(source_id: str, frame: np.ndarray) -> Path:
    """保存参考帧到磁盘"""
    _REF_FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    ref_path = _REF_FRAMES_DIR / f"{source_id}.jpg"
    cv2.imwrite(str(ref_path), frame)
    logger.info(f"[参考帧] 已保存: {ref_path}")
    return ref_path


def load_reference_frame(source_id: str) -> Optional[np.ndarray]:
    """从磁盘加载参考帧"""
    ref_path = _REF_FRAMES_DIR / f"{source_id}.jpg"
    if ref_path.exists():
        frame = cv2.imread(str(ref_path))
        if frame is not None:
            return frame
    return None


async def _inference_loop(source_id: str) -> None:
    """
    推理循环主函数 — 双模型协同：
    - YOLO: 每帧运行（追踪 + 区域计数 + 区域进出累计）
    - DM-Count: 每 N 帧运行（密度图 + 人数估计）
    """
    logger.info(f"推理循环启动: {source_id}")

    db = SessionLocal()

    try:
        # 1. 获取视频源信息
        source_repo = VideoSourceRepository(db)
        source = source_repo.get_by_id(source_id)
        if not source:
            logger.error(f"数据源不存在: {source_id}")
            return

        video_path = source.file_path or source.stream_url
        if not video_path:
            logger.error(f"数据源无有效路径: {source_id}")
            return

        # 2. 打开视频源
        video_service = VideoService(video_path)
        if not video_service.open():
            logger.error(f"无法打开视频源: {video_path}")
            source_repo.update_status(source_id, "error")
            return

        video_info = video_service.get_info()
        frame_interval = 1.0 / video_info.fps if video_info.fps > 0 else 1.0 / 30.0

        logger.info(f"视频源已打开: {video_path}, {video_info.width}x{video_info.height}, FPS={video_info.fps}")

        # 流源首次连接时回填视频元数据
        if source.source_type == "stream" and not source.video_width:
            source.video_width = video_info.width
            source.video_height = video_info.height
            source.video_fps = video_info.fps
            db.commit()

        # 3. 截取参考帧
        ret, first_frame = video_service.cap.read()
        if not ret:
            logger.error(f"无法读取第一帧: {source_id}")
            source_repo.update_status(source_id, "error")
            return
        save_reference_frame(source_id, first_frame)
        # 文件源：回到起始帧；流源：不支持 seek，继续读取即可
        is_stream = video_service.source_type.value == "stream"
        if not is_stream:
            video_service.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        # 4. 获取区域配置
        region_repo = RegionRepository(db)
        regions = region_repo.get_by_source_id(source_id)
        regions_dict = _get_regions_dict(regions, video_info.width, video_info.height)
        region_id_map = _get_region_id_map(regions)
        regions_by_name = {region.name: region for region in regions}

        logger.info(f"区域配置: {list(regions_dict.keys()) if regions_dict else '无'}")

        # 5. 构建区域阈值配置
        region_threshold_configs = []
        for region in regions:
            region_threshold_configs.append(RegionThresholdConfig(
                region_id=region.region_id,
                region_name=region.name,
                count_warning=region.count_warning,
                count_critical=region.count_critical,
                density_warning=region.density_warning,
                density_critical=region.density_critical,
            ))

        # 6. 初始化服务
        yolo_classes = [int(c.strip()) for c in settings.YOLO_CLASSES.split(",") if c.strip()]
        yolo_service = YOLOService(
            model_path=settings.YOLO_MODEL_PATH,
            regions=regions_dict if regions_dict else None,
            conf=settings.YOLO_CONF_THRESHOLD,
            device=settings.YOLO_DEVICE,
            classes=yolo_classes,
        )
        dmcount_service = DMCountService(
            model_name=settings.DMCOUNT_MODEL_NAME,
            model_weights=settings.DMCOUNT_MODEL_WEIGHTS,
        )
        alert_service = AlertService(cooldown_seconds=settings.ALERT_COOLDOWN_SECONDS)
        alert_service.set_region_thresholds(region_threshold_configs)
        alert_repo = AlertRepository(db)

        # 7. 推理循环
        # 架构：YOLO 每帧静默运行（追踪+区域计数+区域进出累计），DM-Count 按间隔运行（密度+渲染+推送）
        frame_count = 0
        last_flush_time = datetime.utcnow()
        last_dmcount_time = 0.0  # 上次 DM-Count 运行的 wall time
        last_source_refresh = datetime.utcnow()
        loop = asyncio.get_event_loop()

        # DM-Count 状态缓存
        dmcount_interval_sec = settings.DMCOUNT_INTERVAL_SEC
        cached_density_map: np.ndarray | None = None
        cached_dm_count: float = 0.0
        cached_heatmap_frame: np.ndarray | None = None
        cached_region_dm_counts: dict[str, float] = {}

        # 解析 YOLO 检测类别
        yolo_classes = [int(c.strip()) for c in settings.YOLO_CLASSES.split(",") if c.strip()]
        logger.info(f"YOLO 检测类别: {yolo_classes}, DM-Count 间隔: {dmcount_interval_sec}s")

        # 帧率控制
        is_stream = video_service.source_type.value == "stream"

        try:
            for frame in video_service.frames():
                frame_wall_time = loop.time()

                if asyncio.current_task().cancelled():
                    break

                # 流源：丢弃缓冲区旧帧，始终处理最新帧
                if is_stream and video_service.cap:
                    for _ in range(3):
                        if video_service.cap.grab():
                            ret, latest = video_service.cap.retrieve()
                            if ret:
                                frame = latest

                frame_count += 1
                now = datetime.utcnow()
                timestamp = now.isoformat() + "Z"

                # === YOLO: 每帧静默运行（追踪 + 区域计数 + 区域进出累计）===
                result: DetectionResult = await loop.run_in_executor(
                    _yolo_executor, yolo_service.process, frame
                )

                # === DM-Count: 按时间间隔运行（密度估计 + 热力图渲染）===
                should_render = (frame_wall_time - last_dmcount_time) >= dmcount_interval_sec
                if should_render or cached_density_map is None:
                    try:
                        density_map, dm_count = await loop.run_in_executor(
                            _dmcount_executor, dmcount_service.predict, frame
                        )
                        cached_density_map = density_map
                        cached_dm_count = dm_count
                        cached_heatmap_frame = dmcount_service.render_heatmap(frame, density_map)
                        if regions_dict:
                            cached_region_dm_counts = _dmcount_region_counts(
                                density_map, regions_dict, video_info.width, video_info.height
                            )
                        last_dmcount_time = loop.time()
                    except Exception as e:
                        logger.warning(f"[DMCount] 推理异常: {e}")
                        should_render = False  # 失败时不推送

                # === 告警检查（使用 DM-Count 数据，每帧检查）===
                region_metrics_for_alert: dict[str, RegionAlertMetrics] = {}
                # 定期刷新 source（支持运行中修改面积）
                if (now - last_source_refresh).total_seconds() >= 5:
                    db.refresh(source)
                    last_source_refresh = now
                scene_area = source.scene_area_m2 or 0.0
                total_px = video_info.width * video_info.height if video_info.width and video_info.height else 1
                for region_name, polygon in regions_dict.items():
                    region = regions_by_name.get(region_name)
                    if region is None:
                        continue
                    pixel_area = cv2.contourArea(np.array(polygon, dtype=np.float32))
                    ratio = pixel_area / total_px if total_px > 0 else 1.0
                    area_m2 = (
                        region.area_physical
                        if region.area_physical and region.area_physical > 0
                        else (scene_area * ratio if scene_area > 0 else 0.0)
                    )
                    count_value = cached_region_dm_counts.get(region_name, 0.0)
                    density_value = count_value / area_m2 if area_m2 > 0 else 0.0
                    region_metrics_for_alert[region.region_id] = RegionAlertMetrics(
                        region_id=region.region_id,
                        region_name=region_name,
                        count=count_value,
                        density=density_value,
                    )
                alerts = alert_service.check(region_metrics_for_alert)
                for alert in alerts:
                    alert_val = int(round(alert.current_value))
                    alert_th = int(round(alert.threshold))
                    alert_model = AlertModel(
                        alert_id=alert.alert_id,
                        source_id=source_id,
                        alert_type=alert.alert_type.value,
                        level=alert.level.value,
                        region_id=alert.region_id,
                        region_name=alert.region_name,
                        current_value=alert_val,
                        threshold=alert_th,
                        timestamp=timestamp,
                        message=f"{'总人数' if alert.alert_type.value == 'total_count' else alert.region_name}"
                                f"达到{alert.level.value}阈值: {alert_val}/{alert_th}",
                    )
                    try:
                        alert_repo.create(alert_model)
                    except Exception:
                        db.rollback()
                        logger.exception("告警写入失败，已跳过该条告警: %s", alert.alert_type.value)
                        continue
                    alert_msg = AlertMessage(
                        alert_id=alert.alert_id,
                        alert_type=alert.alert_type.value,
                        level=alert.level.value,
                        region_id=alert.region_id,
                        region_name=alert.region_name,
                        current_value=alert_val,
                        threshold=alert_th,
                        timestamp=timestamp,
                        message=alert_model.message or "",
                    )
                    await ws_manager.send_alert(source_id, alert_msg)

                # === 统计聚合（每帧收集，使用 DM-Count 缓存）===
                total_density = cached_dm_count / scene_area if scene_area > 0 else 0.0
                region_frame_stats = []
                for region_name, pixel_points in regions_dict.items():
                    region = regions_by_name.get(region_name)
                    if region is None:
                        continue
                    dm_region_count = cached_region_dm_counts.get(region_name, 0.0)
                    region_pixel_area = cv2.contourArea(np.array(pixel_points, dtype=np.float32))
                    region_ratio = region_pixel_area / total_px if total_px > 0 else 1.0
                    region_area_m2 = (
                        region.area_physical
                        if region.area_physical and region.area_physical > 0
                        else (scene_area * region_ratio if scene_area > 0 else 0.0)
                    )
                    region_density = dm_region_count / region_area_m2 if region_area_m2 > 0 else 0.0
                    flow_stats = result.region_flow_stats.get(region_name, {})
                    region_frame_stats.append(RegionFrameStats(
                        region_id=region.region_id,
                        name=region_name,
                        count=int(round(dm_region_count)),
                        density=round(region_density, 2),
                        in_total=int(flow_stats.get("in_total", 0)),
                        out_total=int(flow_stats.get("out_total", 0)),
                    ))

                frame_stats = FrameStats(
                    source_id=source_id,
                    timestamp=timestamp,
                    total_count=int(round(cached_dm_count)),
                    total_density=round(total_density, 2),
                    regions=region_frame_stats,
                    dm_count_estimate=cached_dm_count,
                )
                stats_aggregator.collect(frame_stats)

                if (now - last_flush_time).total_seconds() >= 60:
                    stats_aggregator.flush(db)
                    last_flush_time = now

                # === WebSocket 推送（仅 DM-Count 触发时推送画面）===
                if should_render and cached_heatmap_frame is not None:
                    # 合成输出帧：热力图 + 区域标注
                    output_frame = cached_heatmap_frame.copy()
                    if regions_dict:
                        output_frame = yolo_service._draw_regions(output_frame, result.region_counts)
                    else:
                        output_frame = yolo_service._draw_total_count(output_frame, result.total_count)

                    _, source_buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    _, buffer = cv2.imencode(".jpg", output_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    source_frame_base64 = base64.b64encode(source_buffer).decode("utf-8")
                    frame_base64 = base64.b64encode(buffer).decode("utf-8")

                    regions_realtime: dict[str, RegionRealtimeStats] = {}
                    for rf in region_frame_stats:
                        regions_realtime[rf.region_id] = RegionRealtimeStats(
                            name=rf.name,
                            count=rf.count,
                            density=rf.density,
                            in_total=rf.in_total,
                            out_total=rf.out_total,
                        )

                    density_matrix_list: list[list[float]] = []
                    if cached_density_map is not None:
                        dm_small = cv2.resize(cached_density_map.astype(float), (80, 60))
                        density_matrix_list = dm_small.tolist()

                    realtime_frame = RealtimeFrame(
                        ts=timestamp,
                        frame=frame_base64,
                        source_frame=source_frame_base64,
                        total_count=int(round(cached_dm_count)),
                        total_density=total_density,
                        dm_count_estimate=cached_dm_count,
                        regions=regions_realtime,
                        density_matrix=density_matrix_list,
                    )
                    await ws_manager.send_frame(source_id, realtime_frame)

                # 文件源帧率控制（流源不需要，自然按摄像头速率读取）
                if not is_stream:
                    elapsed = loop.time() - frame_wall_time
                    sleep_time = max(0, frame_interval - elapsed)
                    if sleep_time > 0:
                        await asyncio.sleep(sleep_time)

        except asyncio.CancelledError:
            logger.info(f"推理任务被取消: {source_id}")
            raise
        finally:
            video_service.close()
            stats_aggregator.flush(db)

    except asyncio.CancelledError:
        logger.info(f"推理循环已停止: {source_id}")
    except Exception as e:
        logger.exception(f"推理循环异常: {source_id}, {e}")
        try:
            source_repo = VideoSourceRepository(db)
            source_repo.update_status(source_id, "error")
        except Exception:
            pass
    finally:
        db.close()
        if source_id in _tasks:
            del _tasks[source_id]
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

    if request.source_id in _tasks and not _tasks[request.source_id].done():
        raise HTTPException(status_code=400, detail="分析任务已在运行中")

    source_repo.update_status(request.source_id, "running")

    _analysis_state[request.source_id] = {
        "status": "running",
        "start_time": datetime.utcnow().isoformat() + "Z",
    }
    stats_aggregator.clear(request.source_id)

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

    task = _tasks.get(request.source_id)
    if task:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        _tasks.pop(request.source_id, None)

    source_repo.update_status(request.source_id, "stopped")

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
