"""流生命周期管理服务

StreamService 负责：
- 视频流 CRUD 操作
- 状态转换管理
- 并发限制检查
- 与媒体网关交互
- 与推理服务交互
"""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.video_stream import StreamStatus, StreamType, VideoStream
from app.schemas.video_stream import (
    PublishInfo,
    VideoStreamCreate,
    VideoStreamStart,
)
from app.services.gateway_adapter import (
    GatewayAdapter,
    StreamInfo,
    get_gateway_adapter,
)
from app.services.inference_control import (
    InferenceControlService,
    get_inference_control,
)


class StreamServiceError(Exception):
    """流服务错误基类"""
    pass


class StreamNotFoundError(StreamServiceError):
    """流不存在错误"""
    pass


class ConcurrentLimitError(StreamServiceError):
    """并发限制错误"""
    pass


class InvalidStateTransitionError(StreamServiceError):
    """无效状态转换错误"""
    pass


class GatewayError(StreamServiceError):
    """网关错误"""
    pass


class StreamService:
    """流生命周期管理服务"""
    
    def __init__(
        self,
        db: AsyncSession,
        gateway: Optional[GatewayAdapter] = None,
        inference_control: Optional[InferenceControlService] = None
    ):
        self.db = db
        self.gateway = gateway or get_gateway_adapter()
        self.inference_control = inference_control or get_inference_control()
    
    async def get_running_count(self) -> int:
        """获取当前运行中的流数量"""
        result = await self.db.execute(
            select(func.count(VideoStream.id)).where(
                VideoStream.status == StreamStatus.RUNNING
            )
        )
        return result.scalar() or 0
    
    async def check_concurrent_limit(self) -> bool:
        """检查是否超过并发限制
        
        Returns:
            True 如果未超过限制，False 如果已达到限制
        """
        running_count = await self.get_running_count()
        return running_count < settings.max_concurrent_streams
    
    async def create(self, data: VideoStreamCreate) -> VideoStream:
        """创建视频流
        
        Args:
            data: 创建请求数据
            
        Returns:
            创建的视频流对象
            
        Raises:
            ConcurrentLimitError: 超过并发限制
        """
        # 检查并发限制（创建时不检查，启动时检查）
        
        stream_id = str(uuid.uuid4())
        
        stream = VideoStream(
            id=stream_id,
            name=data.name,
            type=data.type,
            status=StreamStatus.STOPPED,  # 创建后默认停止状态
            source_url=data.source_url,
            file_id=data.file_id,
        )
        
        self.db.add(stream)
        await self.db.flush()
        await self.db.refresh(stream)
        
        return stream
    
    async def get(self, stream_id: str) -> Optional[VideoStream]:
        """获取视频流"""
        result = await self.db.execute(
            select(VideoStream).where(VideoStream.id == stream_id)
        )
        return result.scalar_one_or_none()
    
    async def get_or_raise(self, stream_id: str) -> VideoStream:
        """获取视频流，不存在则抛出异常"""
        stream = await self.get(stream_id)
        if stream is None:
            raise StreamNotFoundError(f"Stream {stream_id} not found")
        return stream
    
    async def list_all(self) -> list[VideoStream]:
        """获取所有视频流"""
        result = await self.db.execute(
            select(VideoStream).order_by(VideoStream.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def delete(self, stream_id: str) -> bool:
        """删除视频流
        
        如果流正在运行，先停止再删除。
        """
        stream = await self.get_or_raise(stream_id)
        
        # 如果正在运行，先停止
        if stream.status == StreamStatus.RUNNING:
            await self.stop(stream_id)
        
        # 删除网关中的流
        await self.gateway.delete_stream(stream_id)
        
        # 删除数据库记录
        await self.db.delete(stream)
        await self.db.flush()
        
        return True

    async def start(
        self, 
        stream_id: str, 
        options: Optional[VideoStreamStart] = None
    ) -> tuple[VideoStream, Optional[PublishInfo]]:
        """启动视频流
        
        Args:
            stream_id: 视频流 ID
            options: 启动选项
            
        Returns:
            (更新后的视频流, 推流信息（仅 webcam 类型）)
            
        Raises:
            StreamNotFoundError: 流不存在
            ConcurrentLimitError: 超过并发限制
            InvalidStateTransitionError: 无效状态转换
            GatewayError: 网关错误
        """
        options = options or VideoStreamStart()
        stream = await self.get_or_raise(stream_id)
        
        # 检查状态转换是否有效
        if not stream.can_transition_to(StreamStatus.STARTING):
            raise InvalidStateTransitionError(
                f"Cannot start stream in {stream.status} status"
            )
        
        # 检查并发限制
        if not await self.check_concurrent_limit():
            raise ConcurrentLimitError(
                f"Concurrent stream limit ({settings.max_concurrent_streams}) reached"
            )
        
        # 更新状态为 STARTING
        stream.status = StreamStatus.STARTING
        await self.db.flush()
        
        publish_info: Optional[PublishInfo] = None
        
        try:
            # 根据类型调用网关创建流
            stream_info: Optional[StreamInfo] = None
            
            if stream.type == StreamType.RTSP:
                stream_info = await self.gateway.create_rtsp_proxy(
                    stream_id=stream_id,
                    rtsp_url=stream.source_url,
                )
            elif stream.type == StreamType.FILE:
                file_path = f"{settings.file_storage_path}/{stream.file_id}"
                stream_info = await self.gateway.create_file_stream(
                    stream_id=stream_id,
                    file_path=file_path,
                )
            elif stream.type == StreamType.WEBCAM:
                stream_info, publish_info = await self.gateway.create_webcam_ingest(
                    stream_id=stream_id
                )
            
            if stream_info:
                stream.play_url = stream_info.play_url
            
            # 更新状态为 RUNNING
            stream.status = StreamStatus.RUNNING
            await self.db.flush()
            
            # 如果启用推理，发送 START 指令
            if options.enable_infer:
                await self.inference_control.send_start(
                    stream_id=stream_id,
                    fps=settings.inference_fps
                )
            
        except Exception as e:
            # 网关错误，更新状态为 ERROR
            stream.status = StreamStatus.ERROR
            await self.db.flush()
            raise GatewayError(f"Failed to start stream: {e}") from e
        
        await self.db.refresh(stream)
        
        # 转换 publish_info 为 schema
        schema_publish_info = None
        if publish_info:
            from app.schemas.video_stream import PublishInfo as PublishInfoSchema, IceServer
            schema_publish_info = PublishInfoSchema(
                whip_url=publish_info.whip_url,
                token=publish_info.token,
                expires_at=publish_info.expires_at,
                ice_servers=[
                    IceServer(urls=s.get("urls", []), username=s.get("username"), credential=s.get("credential"))
                    for s in publish_info.ice_servers
                ]
            )
        
        return stream, schema_publish_info
    
    async def stop(self, stream_id: str) -> VideoStream:
        """停止视频流
        
        Args:
            stream_id: 视频流 ID
            
        Returns:
            更新后的视频流
            
        Raises:
            StreamNotFoundError: 流不存在
            InvalidStateTransitionError: 无效状态转换
        """
        stream = await self.get_or_raise(stream_id)
        
        # 检查状态转换是否有效
        if not stream.can_transition_to(StreamStatus.STOPPED):
            raise InvalidStateTransitionError(
                f"Cannot stop stream in {stream.status} status"
            )
        
        # 发送 STOP 指令（无论 enable_infer 设置，强制停止推理）
        await self.inference_control.send_stop(stream_id=stream_id)
        
        # 删除网关中的流
        await self.gateway.delete_stream(stream_id)
        
        # 更新状态为 STOPPED
        stream.status = StreamStatus.STOPPED
        stream.play_url = None
        await self.db.flush()
        await self.db.refresh(stream)
        
        return stream
    
    async def update_status(
        self, 
        stream_id: str, 
        new_status: StreamStatus
    ) -> VideoStream:
        """更新流状态
        
        Args:
            stream_id: 视频流 ID
            new_status: 新状态
            
        Returns:
            更新后的视频流
            
        Raises:
            StreamNotFoundError: 流不存在
            InvalidStateTransitionError: 无效状态转换
        """
        stream = await self.get_or_raise(stream_id)
        
        if not stream.can_transition_to(new_status):
            raise InvalidStateTransitionError(
                f"Cannot transition from {stream.status} to {new_status}"
            )
        
        stream.status = new_status
        await self.db.flush()
        await self.db.refresh(stream)
        
        return stream


def get_stream_service(db: AsyncSession) -> StreamService:
    """获取流服务实例"""
    return StreamService(db=db)
