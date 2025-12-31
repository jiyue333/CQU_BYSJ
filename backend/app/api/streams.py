"""流管理 REST API

提供视频流的 CRUD 操作和生命周期管理接口。

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger, log_error, log_info
from app.core.redis import get_redis

logger = get_logger(__name__)
from app.models.video_stream import StreamStatus
from app.schemas.detection import DetectionResult
from app.schemas.video_stream import (
    VideoStreamCreate,
    VideoStreamListResponse,
    VideoStreamResponse,
    VideoStreamStart,
)
from app.services.stream_service import (
    ConcurrentLimitError,
    GatewayError,
    InvalidStateTransitionError,
    StreamNotFoundError,
    StreamService,
    get_stream_service,
)

router = APIRouter()


def _build_webrtc_url(play_url: str | None) -> str | None:
    """从 play_url 构建 WebRTC URL
    
    play_url 格式: http://host:port/live/streamId/hls.m3u8
    webrtc_url 格式: http://host:port/index/api/webrtc?app=live&stream=streamId&type=play
    """
    if not play_url:
        return None
    try:
        from urllib.parse import urlparse
        parsed = urlparse(play_url)
        # 从路径提取 app 和 stream
        # 格式: /live/streamId/hls.m3u8 或 /live/streamId.flv
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) >= 2:
            app = path_parts[0]  # 'live'
            stream = path_parts[1]  # streamId 或 streamId.flv
            # 移除可能的扩展名
            if '.' in stream:
                stream = stream.rsplit('.', 1)[0]
            return f"{parsed.scheme}://{parsed.netloc}/index/api/webrtc?app={app}&stream={stream}&type=play"
    except Exception:
        pass
    return None


def _stream_to_response(stream, publish_info=None) -> VideoStreamResponse:
    """将 VideoStream 模型转换为响应 Schema"""
    return VideoStreamResponse(
        stream_id=stream.id,
        name=stream.name,
        type=stream.type,
        status=stream.status,
        play_url=stream.play_url,
        webrtc_url=_build_webrtc_url(stream.play_url),
        source_url=stream.source_url,
        file_id=stream.file_id,
        publish_info=publish_info,
        created_at=stream.created_at,
        updated_at=stream.updated_at,
    )


@router.post(
    "",
    response_model=VideoStreamResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建视频流",
    description="创建新的视频流。支持三种类型：file（本地文件）、webcam（浏览器摄像头）、rtsp（RTSP 摄像头）。"
)
async def create_stream(
    data: VideoStreamCreate,
    db: AsyncSession = Depends(get_db),
) -> VideoStreamResponse:
    """创建视频流
    
    根据 type 不同，需要提供不同的字段：
    - file: 需要 file_id
    - webcam: 不需要额外字段
    - rtsp: 需要 source_url (RTSP 地址)
    """
    log_info(logger, "Creating stream", stream_type=data.type.value, name=data.name)
    service = get_stream_service(db)
    stream = await service.create(data)
    log_info(logger, "Stream created", stream_id=stream.id, stream_type=data.type.value)
    return _stream_to_response(stream)


@router.get(
    "",
    response_model=VideoStreamListResponse,
    summary="获取所有视频流",
    description="获取所有视频流列表，按创建时间倒序排列。"
)
async def list_streams(
    db: AsyncSession = Depends(get_db),
) -> VideoStreamListResponse:
    """获取所有视频流列表"""
    service = get_stream_service(db)
    streams = await service.list_all()
    return VideoStreamListResponse(
        streams=[_stream_to_response(s) for s in streams],
        total=len(streams)
    )


@router.get(
    "/{stream_id}",
    response_model=VideoStreamResponse,
    summary="获取视频流详情",
    description="获取指定视频流的详细信息，包括状态和播放地址。"
)
async def get_stream(
    stream_id: str,
    db: AsyncSession = Depends(get_db),
) -> VideoStreamResponse:
    """获取视频流详情"""
    service = get_stream_service(db)
    try:
        stream = await service.get_or_raise(stream_id)
        return _stream_to_response(stream)
    except StreamNotFoundError:
        log_error(logger, "Stream not found", stream_id=stream_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )


@router.get(
    "/{stream_id}/latest-result",
    response_model=Optional[DetectionResult],
    summary="获取最新检测结果",
    description="获取指定视频流的最新检测结果，用于 WebSocket 重连后恢复数据。"
)
async def get_latest_result(
    stream_id: str,
    db: AsyncSession = Depends(get_db),
) -> Optional[DetectionResult]:
    """获取最新检测结果
    
    从 Redis 中获取最新的检测结果，用于 WebSocket 重连后恢复数据。
    """
    # 先验证流是否存在
    service = get_stream_service(db)
    try:
        await service.get_or_raise(stream_id)
    except StreamNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )
    
    # 从 Redis 获取最新结果
    redis_client = await get_redis()
    result_key = f"latest_result:{stream_id}"
    
    result_data = await redis_client.get(result_key)
    if result_data:
        try:
            data = json.loads(result_data)
            return DetectionResult(**data)
        except (json.JSONDecodeError, ValueError):
            pass
    
    return None


@router.post(
    "/{stream_id}/start",
    response_model=VideoStreamResponse,
    summary="启动视频流",
    description="启动指定的视频流，开始播放和推理。"
)
async def start_stream(
    stream_id: str,
    options: Optional[VideoStreamStart] = None,
    db: AsyncSession = Depends(get_db),
) -> VideoStreamResponse:
    """启动视频流
    
    启动后：
    1. 网关产生可播放流（play_url 可用）
    2. 默认开启推理（可通过 enable_infer=false 关闭）
    3. 状态变为 RUNNING
    """
    log_info(logger, "Starting stream", stream_id=stream_id)
    service = get_stream_service(db)
    try:
        stream, publish_info = await service.start(stream_id, options)
        log_info(logger, "Stream started", stream_id=stream_id, status=stream.status.value)
        return _stream_to_response(stream, publish_info)
    except StreamNotFoundError:
        log_error(logger, "Stream not found for start", stream_id=stream_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )
    except ConcurrentLimitError as e:
        log_error(logger, "Concurrent limit exceeded", stream_id=stream_id, error=e)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    except InvalidStateTransitionError as e:
        log_error(logger, "Invalid state transition", stream_id=stream_id, error=e)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except GatewayError as e:
        log_error(logger, "Gateway error on start", stream_id=stream_id, error=e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )


@router.post(
    "/{stream_id}/stop",
    response_model=VideoStreamResponse,
    summary="停止视频流",
    description="停止指定的视频流，停止播放和推理。"
)
async def stop_stream(
    stream_id: str,
    db: AsyncSession = Depends(get_db),
) -> VideoStreamResponse:
    """停止视频流
    
    停止后：
    1. 停止播放流（断开 publish/pull）
    2. 强制停止推理（无论 enable_infer 设置）
    3. 状态变为 STOPPED
    """
    log_info(logger, "Stopping stream", stream_id=stream_id)
    service = get_stream_service(db)
    try:
        stream = await service.stop(stream_id)
        log_info(logger, "Stream stopped", stream_id=stream_id)
        return _stream_to_response(stream)
    except StreamNotFoundError:
        log_error(logger, "Stream not found for stop", stream_id=stream_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )
    except InvalidStateTransitionError as e:
        log_error(logger, "Invalid state transition on stop", stream_id=stream_id, error=e)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.delete(
    "/{stream_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除视频流",
    description="删除指定的视频流。如果流正在运行，会先停止再删除。"
)
async def delete_stream(
    stream_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """删除视频流
    
    如果流正在运行，会先停止再删除。
    同时删除关联的 ROI 配置和系统配置。
    """
    log_info(logger, "Deleting stream", stream_id=stream_id)
    service = get_stream_service(db)
    try:
        await service.delete(stream_id)
        log_info(logger, "Stream deleted", stream_id=stream_id)
    except StreamNotFoundError:
        log_error(logger, "Stream not found for delete", stream_id=stream_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )
