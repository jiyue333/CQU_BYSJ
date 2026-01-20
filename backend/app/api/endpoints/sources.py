"""
数据源管理 API

处理视频文件上传和摄像头流接入
"""

import uuid
from datetime import datetime

import cv2
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.logger import logger
from app.models import VideoSource
from app.repositories import VideoSourceRepository
from app.schemas.common import ApiResponse
from app.schemas.video_source import (
    StreamCreate,
    VideoSourceResponse,
    VideoSourceListResponse,
)

router = APIRouter(prefix="/sources", tags=["数据源管理"])


@router.post("/upload", response_model=ApiResponse[VideoSourceResponse])
async def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """上传视频文件"""
    # 验证文件类型
    allowed_extensions = {".mp4", ".avi", ".mov", ".mkv", ".flv"}
    file_ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {file_ext}")

    # 保存文件
    source_id = str(uuid.uuid4())
    settings.ensure_dirs()
    file_path = settings.UPLOAD_DIR / f"{source_id}{file_ext}"

    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(f"视频文件已保存: {file_path}")
    except Exception as e:
        logger.error(f"保存文件失败: {e}")
        raise HTTPException(status_code=500, detail="文件保存失败")

    # 获取视频元数据
    video_width, video_height, video_fps, total_frames = None, None, None, None
    try:
        cap = cv2.VideoCapture(str(file_path))
        if cap.isOpened():
            video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            video_fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
    except Exception as e:
        logger.warning(f"获取视频元数据失败: {e}")

    # 创建数据库记录
    repo = VideoSourceRepository(db)
    source = VideoSource(
        source_id=source_id,
        name=file.filename,
        source_type="file",
        status="ready",
        file_path=str(file_path),
        video_width=video_width,
        video_height=video_height,
        video_fps=video_fps,
        total_frames=total_frames,
    )
    repo.create(source)
    logger.info(f"数据源已创建: {source_id}")

    return ApiResponse.success(data=VideoSourceResponse.model_validate(source))


@router.post("/stream", response_model=ApiResponse[VideoSourceResponse])
async def add_stream(
    request: StreamCreate,
    db: Session = Depends(get_db),
):
    """接入摄像头/推流地址"""
    source_id = str(uuid.uuid4())

    # 验证流地址可访问性（可选）
    video_width, video_height, video_fps = None, None, None
    try:
        cap = cv2.VideoCapture(request.url)
        if cap.isOpened():
            video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            video_fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()
            logger.info(f"流地址验证成功: {request.url}")
        else:
            logger.warning(f"无法打开流地址: {request.url}")
    except Exception as e:
        logger.warning(f"验证流地址失败: {e}")

    # 创建数据库记录
    repo = VideoSourceRepository(db)
    source = VideoSource(
        source_id=source_id,
        name=request.name,
        source_type="stream",
        status="ready",
        stream_url=request.url,
        video_width=video_width,
        video_height=video_height,
        video_fps=video_fps,
    )
    repo.create(source)
    logger.info(f"流数据源已创建: {source_id}")

    return ApiResponse.success(data=VideoSourceResponse.model_validate(source))


@router.get("", response_model=ApiResponse[VideoSourceListResponse])
async def list_sources(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """获取数据源列表"""
    repo = VideoSourceRepository(db)
    sources = repo.get_all(skip=skip, limit=limit)

    return ApiResponse.success(
        data=VideoSourceListResponse(
            sources=[VideoSourceResponse.model_validate(s) for s in sources]
        )
    )


@router.delete("/{source_id}", response_model=ApiResponse)
async def delete_source(
    source_id: str,
    db: Session = Depends(get_db),
):
    """删除数据源"""
    repo = VideoSourceRepository(db)
    source = repo.get_by_id(source_id)

    if not source:
        raise HTTPException(status_code=404, detail="数据源不存在")

    # 删除关联文件
    if source.file_path:
        try:
            import os
            if os.path.exists(source.file_path):
                os.remove(source.file_path)
                logger.info(f"已删除文件: {source.file_path}")
        except Exception as e:
            logger.warning(f"删除文件失败: {e}")

    repo.delete(source_id)
    logger.info(f"数据源已删除: {source_id}")

    return ApiResponse.success(msg="删除成功")
