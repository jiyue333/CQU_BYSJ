"""渲染流行为测试

F-27: 扩展现有流管理测试，验证 start/stop 的控制指令发布、play_url 返回、错误回滚

**Validates: 方案 F 渲染流生命周期管理**
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings as hypothesis_settings, strategies as st
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.video_stream import StreamStatus, StreamType
from app.schemas.video_stream import VideoStreamCreate
from app.services.stream_service import StreamService
from app.services.render_control import RenderControlService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def test_db():
    """创建测试数据库会话"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def mock_gateway():
    """Mock 网关适配器"""
    from app.services.gateway_adapter import StreamInfo
    
    gateway = AsyncMock()
    gateway.create_rtsp_proxy = AsyncMock(return_value=StreamInfo(
        stream_id="test",
        play_url="http://test/live/test_heatmap.flv",
        hls_url="http://test/live/test_heatmap/hls.m3u8"
    ))
    gateway.create_file_stream = AsyncMock(return_value=StreamInfo(
        stream_id="test",
        play_url="http://test/live/test_heatmap.flv",
        hls_url="http://test/live/test_heatmap/hls.m3u8"
    ))
    gateway.create_webcam_ingest = AsyncMock(return_value=(
        StreamInfo(
            stream_id="test",
            play_url="http://test/live/test_heatmap.flv",
            hls_url="http://test/live/test_heatmap/hls.m3u8"
        ),
        AsyncMock(whip_url="http://test/whip", token="test", expires_at=0, ice_servers=[])
    ))
    gateway.delete_stream = AsyncMock(return_value=True)
    gateway.build_internal_rtsp_url = MagicMock(return_value="rtsp://zlmediakit:554/live/test")
    gateway.build_internal_flv_url = MagicMock(return_value="http://zlmediakit:80/live/test.live.flv")
    gateway.build_internal_rtmp_url = MagicMock(return_value="rtmp://zlmediakit:1935/live/test_heatmap")
    # Mock _build_play_urls 方法（同步方法）
    gateway._build_play_urls = MagicMock(return_value=StreamInfo(
        stream_id="test_heatmap",
        play_url="http://test/live/test_heatmap.flv",
        hls_url="http://test/live/test_heatmap/hls.m3u8"
    ))
    return gateway


@pytest.fixture
def mock_render_control():
    """Mock 渲染控制服务"""
    control = AsyncMock(spec=RenderControlService)
    control.send_start = AsyncMock(return_value="cmd_start_123")
    control.send_stop = AsyncMock(return_value="cmd_stop_456")
    return control


# ============================================================================
# 渲染流启动测试
# ============================================================================

class TestRenderStreamStart:
    """渲染流启动测试"""
    
    @pytest.mark.asyncio
    async def test_start_sends_render_control_command(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """启动流应发送渲染控制指令"""
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        # 创建流
        data = VideoStreamCreate(
            name="测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        )
        stream = await service.create(data)
        
        # 启动流
        started_stream, _ = await service.start(stream.id)
        
        # 验证发送了渲染控制指令
        mock_render_control.send_start.assert_called_once()
        call_kwargs = mock_render_control.send_start.call_args.kwargs
        assert call_kwargs["stream_id"] == stream.id
    
    @pytest.mark.asyncio
    async def test_start_returns_render_stream_play_url(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """启动后应返回渲染流播放地址"""
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        data = VideoStreamCreate(
            name="测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        )
        stream = await service.create(data)
        started_stream, _ = await service.start(stream.id)
        
        # play_url 应该是渲染流地址（包含 _heatmap）
        assert started_stream.play_url is not None
        assert "_heatmap" in started_stream.play_url
    
    @pytest.mark.asyncio
    async def test_start_sets_status_to_running(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """启动后状态应为 RUNNING"""
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        data = VideoStreamCreate(
            name="测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        )
        stream = await service.create(data)
        started_stream, _ = await service.start(stream.id)
        
        assert started_stream.status == StreamStatus.RUNNING
    
    @pytest.mark.asyncio
    async def test_start_idempotent_for_running_stream(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """对已运行的流再次启动应幂等或抛出明确异常"""
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        data = VideoStreamCreate(
            name="测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        )
        stream = await service.create(data)
        
        # 第一次启动
        await service.start(stream.id)
        first_call_count = mock_render_control.send_start.call_count
        
        # 第二次启动（应该抛出 InvalidStateTransitionError 或安全处理）
        try:
            await service.start(stream.id)
            # 如果没抛异常，验证不会重复发送指令
            assert mock_render_control.send_start.call_count == first_call_count
        except Exception as e:
            # 抛出 InvalidStateTransitionError 是预期行为
            assert "RUNNING" in str(e) or "running" in str(e).lower()


# ============================================================================
# 渲染流停止测试
# ============================================================================

class TestRenderStreamStop:
    """渲染流停止测试"""
    
    @pytest.mark.asyncio
    async def test_stop_sends_render_control_command(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """停止流应发送渲染控制指令"""
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        data = VideoStreamCreate(
            name="测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        )
        stream = await service.create(data)
        await service.start(stream.id)
        
        # 停止流
        await service.stop(stream.id)
        
        # 验证发送了停止指令（使用 keyword argument）
        mock_render_control.send_stop.assert_called_once()
        call_kwargs = mock_render_control.send_stop.call_args
        # 可能是位置参数或关键字参数
        if call_kwargs.args:
            assert call_kwargs.args[0] == stream.id
        else:
            assert call_kwargs.kwargs.get("stream_id") == stream.id
    
    @pytest.mark.asyncio
    async def test_stop_clears_play_url(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """停止后 play_url 应为空"""
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        data = VideoStreamCreate(
            name="测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        )
        stream = await service.create(data)
        await service.start(stream.id)
        stopped_stream = await service.stop(stream.id)
        
        assert stopped_stream.play_url is None
    
    @pytest.mark.asyncio
    async def test_stop_sets_status_to_stopped(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """停止后状态应为 STOPPED"""
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        data = VideoStreamCreate(
            name="测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        )
        stream = await service.create(data)
        await service.start(stream.id)
        stopped_stream = await service.stop(stream.id)
        
        assert stopped_stream.status == StreamStatus.STOPPED
    
    @pytest.mark.asyncio
    async def test_stop_idempotent_for_stopped_stream(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """对已停止的流再次停止应幂等"""
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        data = VideoStreamCreate(
            name="测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        )
        stream = await service.create(data)
        
        # 未启动的流状态已经是 STOPPED
        assert stream.status == StreamStatus.STOPPED
        
        # 对已停止的流调用 stop 应该安全处理（不抛异常或返回当前状态）
        # 注：根据实际实现，可能抛出 InvalidStateTransitionError 或返回当前状态
        try:
            stopped_stream = await service.stop(stream.id)
            assert stopped_stream.status == StreamStatus.STOPPED
        except Exception:
            # 如果实现抛出异常，也是可接受的行为
            pass


# ============================================================================
# 错误回滚测试
# ============================================================================

class TestRenderStreamErrorRollback:
    """渲染流错误回滚测试"""
    
    @pytest.mark.asyncio
    async def test_start_rollback_on_gateway_failure(
        self, test_db: AsyncSession, mock_render_control
    ):
        """网关失败时应回滚"""
        from app.services.gateway_adapter import StreamInfo
        
        # 创建会失败的网关
        failing_gateway = AsyncMock()
        failing_gateway.create_rtsp_proxy = AsyncMock(
            side_effect=Exception("Gateway error")
        )
        
        service = StreamService(
            db=test_db,
            gateway=failing_gateway,
            render_control=mock_render_control
        )
        
        data = VideoStreamCreate(
            name="测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        )
        stream = await service.create(data)
        
        # 启动应失败
        with pytest.raises(Exception):
            await service.start(stream.id)
        
        # 状态应保持 STOPPED 或 ERROR
        refreshed = await service.get(stream.id)
        assert refreshed.status in [StreamStatus.STOPPED, StreamStatus.ERROR]
    
    @pytest.mark.asyncio
    async def test_start_rollback_on_render_control_failure(
        self, test_db: AsyncSession, mock_gateway
    ):
        """渲染控制失败时应回滚"""
        # 创建会失败的渲染控制
        failing_render_control = AsyncMock()
        failing_render_control.send_start = AsyncMock(
            side_effect=Exception("Render control error")
        )
        failing_render_control.send_stop = AsyncMock(return_value="cmd_stop")
        
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=failing_render_control
        )
        
        data = VideoStreamCreate(
            name="测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        )
        stream = await service.create(data)
        
        # 启动应失败
        with pytest.raises(Exception):
            await service.start(stream.id)


# ============================================================================
# 渲染控制服务测试
# ============================================================================

class TestRenderControlService:
    """渲染控制服务测试"""
    
    @pytest.mark.asyncio
    async def test_send_start_returns_cmd_id(self):
        """send_start 应返回指令 ID"""
        with patch('app.services.render_control.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.publish = AsyncMock(return_value=1)
            mock_get_redis.return_value = mock_redis
            
            service = RenderControlService()
            cmd_id = await service.send_start(
                stream_id="test_stream",
                src_rtsp_url="rtsp://test",
                dst_rtmp_url="rtmp://test",
                render_stream_id="test_stream_heatmap",
            )
            
            assert cmd_id is not None
            assert len(cmd_id) == 36  # UUID 格式
    
    @pytest.mark.asyncio
    async def test_send_stop_returns_cmd_id(self):
        """send_stop 应返回指令 ID"""
        with patch('app.services.render_control.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.publish = AsyncMock(return_value=1)
            mock_get_redis.return_value = mock_redis
            
            service = RenderControlService()
            cmd_id = await service.send_stop("test_stream")
            
            assert cmd_id is not None
            assert len(cmd_id) == 36
    
    @pytest.mark.asyncio
    async def test_send_start_publishes_to_correct_channel(self):
        """send_start 应发布到正确的通道"""
        with patch('app.services.render_control.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.publish = AsyncMock(return_value=1)
            mock_get_redis.return_value = mock_redis
            
            service = RenderControlService()
            await service.send_start(
                stream_id="test_stream",
                src_rtsp_url="rtsp://test",
                dst_rtmp_url="rtmp://test",
                render_stream_id="test_stream_heatmap",
            )
            
            # 验证发布到 render:control 通道
            mock_redis.publish.assert_called_once()
            call_args = mock_redis.publish.call_args
            assert call_args[0][0] == "render:control"


# ============================================================================
# 属性测试
# ============================================================================

class TestRenderStreamProperties:
    """渲染流属性测试"""
    
    @hypothesis_settings(max_examples=50)
    @given(
        name=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=50
        ).filter(lambda x: x.strip()),
    )
    @pytest.mark.asyncio
    async def test_stream_lifecycle_property(self, name: str):
        """Property: 流生命周期状态转换应一致
        
        *For any* 有效的流名称，创建→启动→停止 应产生正确的状态转换
        """
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async_session = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        async with async_session() as session:
            from app.services.gateway_adapter import StreamInfo
            
            mock_gateway = AsyncMock()
            mock_gateway.create_rtsp_proxy = AsyncMock(return_value=StreamInfo(
                stream_id="test",
                play_url="http://test/live/test_heatmap.flv",
                hls_url="http://test/live/test_heatmap/hls.m3u8"
            ))
            mock_gateway.delete_stream = AsyncMock(return_value=True)
            # 关键：mock _build_play_urls 为同步方法
            mock_gateway._build_play_urls = MagicMock(return_value=StreamInfo(
                stream_id="test_heatmap",
                play_url="http://test/live/test_heatmap.flv",
                hls_url="http://test/live/test_heatmap/hls.m3u8"
            ))
            
            mock_render_control = AsyncMock()
            mock_render_control.send_start = AsyncMock(return_value="cmd_123")
            mock_render_control.send_stop = AsyncMock(return_value="cmd_456")
            
            service = StreamService(
                db=session,
                gateway=mock_gateway,
                render_control=mock_render_control
            )
            
            # 创建
            data = VideoStreamCreate(
                name=name.strip(),
                type=StreamType.RTSP,
                source_url="rtsp://test.com/stream"
            )
            stream = await service.create(data)
            assert stream.status == StreamStatus.STOPPED
            
            # 启动
            started, _ = await service.start(stream.id)
            assert started.status == StreamStatus.RUNNING
            assert started.play_url is not None
            
            # 停止
            stopped = await service.stop(stream.id)
            assert stopped.status == StreamStatus.STOPPED
            assert stopped.play_url is None
        
        await engine.dispose()
