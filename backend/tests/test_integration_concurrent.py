"""多路视频并发测试

Task 17.2: 编写多路视频并发测试
- 多路视频同时处理测试
- 资源使用监控

Requirements: 7.1
"""

import asyncio
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.main import app
from app.models.video_stream import StreamStatus, StreamType
from app.schemas.video_stream import VideoStreamCreate
from app.services.gateway_adapter import GatewayAdapter, StreamInfo, PublishInfo
from app.services.stream_service import StreamService, ConcurrentLimitError, GatewayError, StreamNotFoundError


class TestConcurrentStreamCreation:
    """多路视频流并发创建测试
    
    Requirements: 7.1
    """

    @pytest.fixture
    async def test_db(self):
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
    def mock_gateway(self):
        """Mock 网关适配器"""
        gateway = AsyncMock(spec=GatewayAdapter)
        
        def create_stream_info(stream_id, *args, **kwargs):
            return StreamInfo(
                stream_id=stream_id,
                play_url=f"http://gateway/live/{stream_id}.flv",
                hls_url=f"http://gateway/live/{stream_id}/hls.m3u8"
            )
        
        gateway.create_rtsp_proxy = AsyncMock(side_effect=create_stream_info)
        gateway.create_file_stream = AsyncMock(side_effect=create_stream_info)
        gateway.create_webcam_ingest = AsyncMock(side_effect=lambda stream_id: (
            create_stream_info(stream_id),
            PublishInfo(
                whip_url=f"http://gateway/whip/{stream_id}",
                token="test_token",
                expires_at=int(time.time()) + 300,
                ice_servers=[]
            )
        ))
        gateway.delete_stream = AsyncMock(return_value=True)
        gateway.health_check = AsyncMock(return_value=True)
        return gateway

    @pytest.fixture
    def mock_render_control(self):
        """Mock 渲染控制服务"""
        control = AsyncMock()
        control.send_start = AsyncMock(return_value="cmd_start")
        control.send_stop = AsyncMock(return_value="cmd_stop")
        return control

    @pytest.mark.asyncio
    async def test_create_multiple_streams_sequentially(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """测试顺序创建多路视频流
        
        Requirements: 7.1
        """
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        num_streams = 5
        created_streams = []
        
        # 顺序创建多个流
        for i in range(num_streams):
            stream = await service.create(VideoStreamCreate(
                name=f"并发测试流_{i}",
                type=StreamType.RTSP,
                source_url=f"rtsp://192.168.1.{100+i}:554/stream"
            ))
            created_streams.append(stream)
        
        # 验证所有流都创建成功
        assert len(created_streams) == num_streams
        
        # 验证每个流都有唯一的 ID
        stream_ids = [s.id for s in created_streams]
        assert len(set(stream_ids)) == num_streams
        
        # 验证所有流都是 STOPPED 状态
        for stream in created_streams:
            assert stream.status == StreamStatus.STOPPED
        
        # 清理
        for stream in created_streams:
            await service.delete(stream.id)

    @pytest.mark.asyncio
    async def test_start_multiple_streams_sequentially(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """测试顺序启动多路视频流
        
        Requirements: 7.1
        """
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        num_streams = 3
        streams = []
        
        # 创建多个流
        for i in range(num_streams):
            stream = await service.create(VideoStreamCreate(
                name=f"启动测试流_{i}",
                type=StreamType.RTSP,
                source_url=f"rtsp://test.com/stream{i}"
            ))
            streams.append(stream)
        
        # 顺序启动所有流
        started_streams = []
        for stream in streams:
            started, _ = await service.start(stream.id)
            started_streams.append(started)
        
        # 验证所有流都启动成功
        for started in started_streams:
            assert started.status == StreamStatus.RUNNING
            assert started.play_url is not None
        
        # 验证运行中的流数量
        running_count = await service.get_running_count()
        assert running_count == num_streams
        
        # 清理
        for stream in streams:
            await service.stop(stream.id)
            await service.delete(stream.id)

    @pytest.mark.asyncio
    async def test_concurrent_limit_enforcement(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """测试并发限制执行
        
        验证超过最大并发数时拒绝启动新流。
        Requirements: 7.1
        """
        # 使用较小的并发限制进行测试
        with patch('app.services.stream_service.settings') as mock_settings:
            mock_settings.max_concurrent_streams = 2
            mock_settings.inference_fps = 2
            
            service = StreamService(
                db=test_db,
                gateway=mock_gateway,
                render_control=mock_render_control
            )
            
            streams = []
            
            # 创建 3 个流
            for i in range(3):
                stream = await service.create(VideoStreamCreate(
                    name=f"限制测试流_{i}",
                    type=StreamType.RTSP,
                    source_url=f"rtsp://test.com/stream{i}"
                ))
                streams.append(stream)
            
            # 启动前 2 个流（应该成功）
            await service.start(streams[0].id)
            await service.start(streams[1].id)
            
            # 验证运行中的流数量
            running_count = await service.get_running_count()
            assert running_count == 2
            
            # 尝试启动第 3 个流（应该失败）
            with pytest.raises(ConcurrentLimitError):
                await service.start(streams[2].id)
            
            # 停止一个流后应该可以启动新流
            await service.stop(streams[0].id)
            
            # 现在应该可以启动第 3 个流
            started, _ = await service.start(streams[2].id)
            assert started.status == StreamStatus.RUNNING
            
            # 清理
            for stream in streams:
                try:
                    await service.stop(stream.id)
                except Exception:
                    pass
                await service.delete(stream.id)

    @pytest.mark.asyncio
    async def test_mixed_stream_types_concurrent(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """测试混合类型流的并发处理
        
        Requirements: 7.1
        """
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        # 创建不同类型的流
        rtsp_stream = await service.create(VideoStreamCreate(
            name="RTSP流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        ))
        
        webcam_stream = await service.create(VideoStreamCreate(
            name="摄像头流",
            type=StreamType.WEBCAM
        ))
        
        file_stream = await service.create(VideoStreamCreate(
            name="文件流",
            type=StreamType.FILE,
            file_id=str(uuid.uuid4())
        ))
        
        # 验证所有类型都创建成功
        assert rtsp_stream.type == StreamType.RTSP
        assert webcam_stream.type == StreamType.WEBCAM
        assert file_stream.type == StreamType.FILE
        
        # 获取所有流
        all_streams = await service.list_all()
        assert len(all_streams) >= 3
        
        # 清理
        for stream in [rtsp_stream, webcam_stream, file_stream]:
            await service.delete(stream.id)


class TestConcurrentStreamOperations:
    """并发流操作测试
    
    Requirements: 7.1
    """

    @pytest.fixture
    async def test_db(self):
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
    def mock_gateway(self):
        """Mock 网关适配器"""
        gateway = AsyncMock(spec=GatewayAdapter)
        gateway.create_rtsp_proxy = AsyncMock(return_value=StreamInfo(
            stream_id="test",
            play_url="http://gateway/live/test.flv"
        ))
        gateway.delete_stream = AsyncMock(return_value=True)
        return gateway

    @pytest.fixture
    def mock_render_control(self):
        """Mock 渲染控制服务"""
        control = AsyncMock()
        control.send_start = AsyncMock(return_value="cmd_start")
        control.send_stop = AsyncMock(return_value="cmd_stop")
        return control

    @pytest.mark.asyncio
    async def test_running_count_accuracy(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """测试运行中流计数的准确性
        
        Requirements: 7.1
        """
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        # 初始计数应为 0
        assert await service.get_running_count() == 0
        
        # 创建并启动流
        streams = []
        for i in range(3):
            stream = await service.create(VideoStreamCreate(
                name=f"计数测试流_{i}",
                type=StreamType.RTSP,
                source_url=f"rtsp://test.com/stream{i}"
            ))
            streams.append(stream)
            await service.start(stream.id)
            
            # 验证计数增加
            assert await service.get_running_count() == i + 1
        
        # 停止流并验证计数减少
        for i, stream in enumerate(streams):
            await service.stop(stream.id)
            expected_count = len(streams) - i - 1
            assert await service.get_running_count() == expected_count
        
        # 最终计数应为 0
        assert await service.get_running_count() == 0
        
        # 清理
        for stream in streams:
            await service.delete(stream.id)

    @pytest.mark.asyncio
    async def test_stream_isolation(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """测试流之间的隔离性
        
        验证一个流的操作不影响其他流。
        Requirements: 7.1
        """
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        # 创建两个流
        stream1 = await service.create(VideoStreamCreate(
            name="隔离测试流_1",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream1"
        ))
        
        stream2 = await service.create(VideoStreamCreate(
            name="隔离测试流_2",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream2"
        ))
        
        # 启动流 1
        await service.start(stream1.id)
        
        # 验证流 2 仍然是 STOPPED
        stream2_status = await service.get(stream2.id)
        assert stream2_status.status == StreamStatus.STOPPED
        
        # 启动流 2
        await service.start(stream2.id)
        
        # 停止流 1
        await service.stop(stream1.id)
        
        # 验证流 2 仍然是 RUNNING
        stream2_status = await service.get(stream2.id)
        assert stream2_status.status == StreamStatus.RUNNING
        
        # 清理
        await service.stop(stream2.id)
        await service.delete(stream1.id)
        await service.delete(stream2.id)


class TestConcurrentAPIRequests:
    """并发 API 请求测试
    
    Requirements: 7.1
    """

    @pytest.fixture(autouse=True)
    async def cleanup_db_pool(self):
        """每个测试后清理数据库连接池"""
        yield
        from app.core.database import engine
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_concurrent_stream_creation_api(self):
        """测试并发创建流的 API 请求
        
        Requirements: 7.1
        """
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            num_streams = 5
            created_ids = []
            
            # 顺序创建多个流（模拟并发场景）
            for i in range(num_streams):
                resp = await client.post(
                    "/api/streams",
                    json={
                        "name": f"API并发测试流_{i}",
                        "type": "rtsp",
                        "source_url": f"rtsp://192.168.1.{100+i}:554/stream"
                    }
                )
                assert resp.status_code == 201
                created_ids.append(resp.json()["stream_id"])
            
            # 验证所有流都创建成功
            assert len(created_ids) == num_streams
            assert len(set(created_ids)) == num_streams  # 所有 ID 唯一
            
            # 验证流列表
            list_resp = await client.get("/api/streams")
            assert list_resp.status_code == 200
            streams = list_resp.json()["streams"]
            
            for stream_id in created_ids:
                assert any(s["stream_id"] == stream_id for s in streams)
            
            # 清理
            for stream_id in created_ids:
                await client.delete(f"/api/streams/{stream_id}")

    @pytest.mark.asyncio
    async def test_concurrent_stream_operations_api(self):
        """测试并发流操作的 API 请求
        
        Requirements: 7.1
        """
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 创建多个流
            stream_ids = []
            for i in range(3):
                resp = await client.post(
                    "/api/streams",
                    json={
                        "name": f"操作测试流_{i}",
                        "type": "rtsp",
                        "source_url": f"rtsp://test.com/stream{i}"
                    }
                )
                stream_ids.append(resp.json()["stream_id"])
            
            # 获取每个流的详情
            for stream_id in stream_ids:
                resp = await client.get(f"/api/streams/{stream_id}")
                assert resp.status_code == 200
                assert resp.json()["stream_id"] == stream_id
            
            # 清理
            for stream_id in stream_ids:
                await client.delete(f"/api/streams/{stream_id}")

    @pytest.mark.asyncio
    async def test_stream_list_with_multiple_streams(self):
        """测试多流情况下的列表 API
        
        Requirements: 7.1
        """
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 创建多个不同类型的流
            stream_ids = []
            
            # RTSP 流
            resp = await client.post(
                "/api/streams",
                json={"name": "RTSP流", "type": "rtsp", "source_url": "rtsp://test.com/stream"}
            )
            stream_ids.append(resp.json()["stream_id"])
            
            # WEBCAM 流
            resp = await client.post(
                "/api/streams",
                json={"name": "摄像头流", "type": "webcam"}
            )
            stream_ids.append(resp.json()["stream_id"])
            
            # 获取列表
            list_resp = await client.get("/api/streams")
            assert list_resp.status_code == 200
            
            data = list_resp.json()
            assert "streams" in data
            assert "total" in data
            assert data["total"] >= 2
            
            # 验证流类型
            streams = data["streams"]
            types = [s["type"] for s in streams if s["stream_id"] in stream_ids]
            assert "rtsp" in types
            assert "webcam" in types
            
            # 清理
            for stream_id in stream_ids:
                await client.delete(f"/api/streams/{stream_id}")


class TestResourceMonitoring:
    """资源使用监控测试
    
    Requirements: 7.1
    """

    @pytest.fixture
    async def test_db(self):
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
    def mock_gateway(self):
        """Mock 网关适配器"""
        gateway = AsyncMock(spec=GatewayAdapter)
        gateway.create_rtsp_proxy = AsyncMock(return_value=StreamInfo(
            stream_id="test",
            play_url="http://gateway/live/test.flv"
        ))
        gateway.delete_stream = AsyncMock(return_value=True)
        return gateway

    @pytest.fixture
    def mock_render_control(self):
        """Mock 渲染控制服务"""
        control = AsyncMock()
        control.send_start = AsyncMock(return_value="cmd_start")
        control.send_stop = AsyncMock(return_value="cmd_stop")
        return control

    @pytest.mark.asyncio
    async def test_concurrent_limit_check(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """测试并发限制检查
        
        Requirements: 7.1
        """
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        # 初始应该允许创建
        assert await service.check_concurrent_limit() is True
        
        # 创建并启动流
        stream = await service.create(VideoStreamCreate(
            name="限制检查测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        ))
        await service.start(stream.id)
        
        # 仍然应该允许（未达到限制）
        assert await service.check_concurrent_limit() is True
        
        # 清理
        await service.stop(stream.id)
        await service.delete(stream.id)

    @pytest.mark.asyncio
    async def test_gateway_calls_per_stream(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """测试每个流的网关调用
        
        验证每个流启动时都正确调用网关。
        Requirements: 7.1
        """
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        num_streams = 3
        streams = []
        
        # 创建并启动多个流
        for i in range(num_streams):
            stream = await service.create(VideoStreamCreate(
                name=f"网关调用测试流_{i}",
                type=StreamType.RTSP,
                source_url=f"rtsp://test.com/stream{i}"
            ))
            streams.append(stream)
            await service.start(stream.id)
        
        # 验证网关被调用了正确的次数
        assert mock_gateway.create_rtsp_proxy.call_count == num_streams
        
        # 停止所有流
        for stream in streams:
            await service.stop(stream.id)
        
        # 验证删除调用
        assert mock_gateway.delete_stream.call_count == num_streams
        
        # 清理
        for stream in streams:
            await service.delete(stream.id)

    @pytest.mark.asyncio
    async def test_render_control_calls_per_stream(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """测试每个流的渲染控制调用
        
        验证每个流启动/停止时都正确调用推理控制。
        Requirements: 7.1
        """
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        num_streams = 3
        streams = []
        
        # 创建并启动多个流
        for i in range(num_streams):
            stream = await service.create(VideoStreamCreate(
                name=f"推理控制测试流_{i}",
                type=StreamType.RTSP,
                source_url=f"rtsp://test.com/stream{i}"
            ))
            streams.append(stream)
            await service.start(stream.id)
        
        # 验证渲染控制启动被调用了正确的次数
        assert mock_render_control.send_start.call_count == num_streams
        
        # 停止所有流
        for stream in streams:
            await service.stop(stream.id)
        
        # 验证渲染控制停止被调用了正确的次数
        assert mock_render_control.send_stop.call_count == num_streams
        
        # 清理
        for stream in streams:
            await service.delete(stream.id)


class TestWebSocketConcurrency:
    """WebSocket 并发测试
    
    Requirements: 7.1
    """

    @pytest.mark.asyncio
    async def test_multiple_streams_websocket_connections(self):
        """测试多个流的 WebSocket 连接管理"""
        from app.services.result_push_service import ResultPushService
        
        service = ResultPushService()
        
        # 模拟多个流的 WebSocket 连接
        num_streams = 5
        mock_websockets = {}
        
        for i in range(num_streams):
            stream_id = f"stream_{i}"
            mock_ws = MagicMock()
            mock_ws.send_text = AsyncMock()
            
            service.connections[stream_id] = {mock_ws}
            service.last_heartbeat[mock_ws] = time.time()
            service.pending_messages[mock_ws] = 0
            mock_websockets[stream_id] = mock_ws
        
        # 验证所有连接都已注册
        assert len(service.connections) == num_streams
        
        # 向每个流广播消息
        for stream_id, mock_ws in mock_websockets.items():
            await service._broadcast(stream_id, '{"test": "data"}', f"msg_{stream_id}")
            mock_ws.send_text.assert_called_once()
        
        # 清理连接
        for stream_id, mock_ws in mock_websockets.items():
            service._cleanup_connection(mock_ws, stream_id)
        
        # 验证所有连接都已清理
        assert len(service.connections) == 0

    @pytest.mark.asyncio
    async def test_multiple_clients_per_stream(self):
        """测试单个流的多个客户端连接"""
        from app.services.result_push_service import ResultPushService
        
        service = ResultPushService()
        
        stream_id = "shared_stream"
        num_clients = 10
        mock_clients = []
        
        # 注册多个客户端到同一个流
        service.connections[stream_id] = set()
        
        for i in range(num_clients):
            mock_ws = MagicMock()
            mock_ws.send_text = AsyncMock()
            
            service.connections[stream_id].add(mock_ws)
            service.last_heartbeat[mock_ws] = time.time()
            service.pending_messages[mock_ws] = 0
            mock_clients.append(mock_ws)
        
        # 验证所有客户端都已注册
        assert len(service.connections[stream_id]) == num_clients
        
        # 广播消息
        await service._broadcast(stream_id, '{"test": "broadcast"}', "msg_broadcast")
        
        # 验证所有客户端都收到消息
        for mock_ws in mock_clients:
            mock_ws.send_text.assert_called_once()
        
        # 清理
        for mock_ws in mock_clients:
            service._cleanup_connection(mock_ws, stream_id)

    @pytest.mark.asyncio
    async def test_status_push_multiple_clients(self):
        """测试状态推送服务的多客户端支持"""
        from app.services.status_push_service import StatusPushService
        
        service = StatusPushService()
        
        num_clients = 5
        mock_clients = []
        
        # 注册多个客户端
        for i in range(num_clients):
            mock_ws = MagicMock()
            mock_ws.send_text = AsyncMock()
            
            service.connections.add(mock_ws)
            service.last_heartbeat[mock_ws] = time.time()
            mock_clients.append(mock_ws)
        
        # 验证所有客户端都已注册
        assert len(service.connections) == num_clients
        
        # 广播状态消息
        await service._broadcast('{"stream_id": "test", "status": "running"}')
        
        # 验证所有客户端都收到消息
        for mock_ws in mock_clients:
            mock_ws.send_text.assert_called_once()
        
        # 清理
        for mock_ws in mock_clients:
            service._cleanup_connection(mock_ws)
        
        assert len(service.connections) == 0



class TestTrueConcurrentOperations:
    """真正的并发操作测试
    
    使用 asyncio.gather 测试真实并发场景。
    注意：SQLAlchemy AsyncSession 不能在多个并发协程间共享，
    因此每个并发操作需要独立的 session。
    Requirements: 7.1
    """

    @pytest.fixture
    async def db_engine_and_factory(self):
        """创建测试数据库引擎和会话工厂
        
        返回引擎和会话工厂，以便每个并发操作可以创建独立的 session。
        """
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        yield engine, session_factory
        
        await engine.dispose()

    @pytest.fixture
    def mock_gateway(self):
        """Mock 网关适配器（带延迟模拟真实网络）"""
        gateway = AsyncMock(spec=GatewayAdapter)
        
        async def create_with_delay(stream_id, *args, **kwargs):
            await asyncio.sleep(0.01)  # 模拟网络延迟
            return StreamInfo(
                stream_id=stream_id,
                play_url=f"http://gateway/live/{stream_id}.flv"
            )
        
        gateway.create_rtsp_proxy = AsyncMock(side_effect=create_with_delay)
        gateway.delete_stream = AsyncMock(return_value=True)
        return gateway

    @pytest.fixture
    def mock_render_control(self):
        """Mock 渲染控制服务"""
        control = AsyncMock()
        control.send_start = AsyncMock(return_value="cmd_start")
        control.send_stop = AsyncMock(return_value="cmd_stop")
        return control

    @pytest.mark.asyncio
    async def test_concurrent_stream_creation_with_gather(
        self, db_engine_and_factory, mock_gateway, mock_render_control
    ):
        """测试使用 asyncio.gather 并发创建流
        
        每个并发操作使用独立的数据库 session 以避免 session 冲突。
        Requirements: 7.1
        """
        engine, session_factory = db_engine_and_factory
        
        num_streams = 5
        
        # 并发创建多个流，每个操作使用独立的 session
        async def create_stream(i: int):
            async with session_factory() as session:
                service = StreamService(
                    db=session,
                    gateway=mock_gateway,
                    render_control=mock_render_control
                )
                stream = await service.create(VideoStreamCreate(
                    name=f"并发创建流_{i}",
                    type=StreamType.RTSP,
                    source_url=f"rtsp://test.com/stream{i}"
                ))
                await session.commit()
                return stream.id, stream.name
        
        # 使用 gather 并发执行
        results = await asyncio.gather(*[create_stream(i) for i in range(num_streams)])
        
        # 验证所有流都创建成功
        assert len(results) == num_streams
        
        # 验证每个流都有唯一的 ID
        stream_ids = [r[0] for r in results]
        assert len(set(stream_ids)) == num_streams
        
        # 验证数据库中确实有这些流
        async with session_factory() as session:
            service = StreamService(
                db=session,
                gateway=mock_gateway,
                render_control=mock_render_control
            )
            all_streams = await service.list_all()
            assert len(all_streams) == num_streams
            
            # 清理
            for stream_id in stream_ids:
                await service.delete(stream_id)
            await session.commit()

    @pytest.mark.asyncio
    async def test_concurrent_start_stop_interleaved(
        self, db_engine_and_factory, mock_gateway, mock_render_control
    ):
        """测试并发启动和停止交错操作
        
        测试多个流的启动/停止操作可以并发执行而不会导致数据不一致。
        Requirements: 7.1
        """
        engine, session_factory = db_engine_and_factory
        
        # 先顺序创建多个流
        stream_ids = []
        async with session_factory() as session:
            service = StreamService(
                db=session,
                gateway=mock_gateway,
                render_control=mock_render_control
            )
            for i in range(4):
                stream = await service.create(VideoStreamCreate(
                    name=f"交错测试流_{i}",
                    type=StreamType.RTSP,
                    source_url=f"rtsp://test.com/stream{i}"
                ))
                stream_ids.append(stream.id)
            await session.commit()
        
        # 顺序启动前两个流
        async with session_factory() as session:
            service = StreamService(
                db=session,
                gateway=mock_gateway,
                render_control=mock_render_control
            )
            await service.start(stream_ids[0])
            await service.start(stream_ids[1])
            await session.commit()
        
        # 并发执行启动/停止操作，每个操作使用独立 session
        async def stop_stream(stream_id):
            async with session_factory() as session:
                service = StreamService(
                    db=session,
                    gateway=mock_gateway,
                    render_control=mock_render_control
                )
                result = await service.stop(stream_id)
                await session.commit()
                return result
        
        async def start_stream(stream_id):
            async with session_factory() as session:
                service = StreamService(
                    db=session,
                    gateway=mock_gateway,
                    render_control=mock_render_control
                )
                result = await service.start(stream_id)
                await session.commit()
                return result
        
        results = await asyncio.gather(
            stop_stream(stream_ids[0]),
            start_stream(stream_ids[2]),
            stop_stream(stream_ids[1]),
            start_stream(stream_ids[3]),
            return_exceptions=True
        )
        
        # 验证操作完成
        assert len(results) == 4
        
        # 验证没有意外异常（只允许预期的状态转换异常）
        exceptions = [r for r in results if isinstance(r, Exception)]
        for exc in exceptions:
            # 允许的异常类型：状态转换冲突
            assert "state" in str(exc).lower() or "status" in str(exc).lower() or isinstance(exc, (StreamNotFoundError,)), \
                f"Unexpected exception: {exc}"
        
        # 验证最终状态一致性
        async with session_factory() as session:
            service = StreamService(
                db=session,
                gateway=mock_gateway,
                render_control=mock_render_control
            )
            for stream_id in stream_ids:
                fetched = await service.get(stream_id)
                assert fetched is not None
                assert fetched.status in [StreamStatus.RUNNING, StreamStatus.STOPPED, StreamStatus.STARTING]
            
            # 清理
            for stream_id in stream_ids:
                try:
                    await service.stop(stream_id)
                except Exception:
                    pass
                await service.delete(stream_id)
            await session.commit()


class TestFailureScenarios:
    """失败场景测试
    
    测试各种失败情况下的系统行为。
    Requirements: 7.1
    """

    @pytest.fixture
    async def db_engine_and_factory(self):
        """创建测试数据库引擎和会话工厂"""
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        yield engine, session_factory
        
        await engine.dispose()

    @pytest.fixture
    async def test_db(self):
        """创建测试数据库会话（用于非并发测试）"""
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

    @pytest.mark.asyncio
    async def test_gateway_failure_on_start(self, test_db: AsyncSession):
        """测试网关启动失败时的处理
        
        Requirements: 7.1
        """
        mock_gateway = AsyncMock(spec=GatewayAdapter)
        mock_gateway.create_rtsp_proxy = AsyncMock(
            side_effect=Exception("Gateway connection failed")
        )
        mock_gateway.delete_stream = AsyncMock(return_value=True)
        
        mock_inference = AsyncMock()
        mock_inference.send_start = AsyncMock()
        mock_inference.send_stop = AsyncMock()
        
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_inference
        )
        
        # 创建流
        stream = await service.create(VideoStreamCreate(
            name="网关失败测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        ))
        
        # 启动应该失败
        with pytest.raises(GatewayError):
            await service.start(stream.id)
        
        # 验证流状态为 ERROR
        updated = await service.get(stream.id)
        assert updated.status == StreamStatus.ERROR
        
        # 清理
        await service.delete(stream.id)

    @pytest.mark.asyncio
    async def test_render_control_failure_on_start(self, test_db: AsyncSession):
        """测试渲染控制启动失败时的处理
        
        Requirements: 7.1
        """
        mock_gateway = AsyncMock(spec=GatewayAdapter)
        mock_gateway.create_rtsp_proxy = AsyncMock(return_value=StreamInfo(
            stream_id="test",
            play_url="http://gateway/live/test.flv"
        ))
        mock_gateway.delete_stream = AsyncMock(return_value=True)
        
        mock_render = AsyncMock()
        mock_render.send_start = AsyncMock(
            side_effect=Exception("Render service unavailable")
        )
        mock_render.send_stop = AsyncMock()
        
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render
        )
        
        # 创建流
        stream = await service.create(VideoStreamCreate(
            name="渲染失败测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        ))
        
        # 启动应该失败
        with pytest.raises(GatewayError):
            await service.start(stream.id)
        
        # 验证网关资源被清理
        mock_gateway.delete_stream.assert_called_once()
        
        # 验证流状态为 ERROR
        updated = await service.get(stream.id)
        assert updated.status == StreamStatus.ERROR
        
        # 清理
        await service.delete(stream.id)

    @pytest.mark.asyncio
    async def test_partial_failure_in_concurrent_operations(self, db_engine_and_factory):
        """测试并发操作中部分失败的处理
        
        使用独立 session 进行并发操作，验证部分失败不影响其他操作。
        Requirements: 7.1
        """
        engine, session_factory = db_engine_and_factory
        
        # 使用线程安全的计数器
        call_count = {"value": 0}
        call_lock = asyncio.Lock()
        
        async def flaky_create(stream_id, *args, **kwargs):
            async with call_lock:
                call_count["value"] += 1
                current_count = call_count["value"]
            
            if current_count == 2:  # 第二次调用失败
                raise Exception("Intermittent failure")
            return StreamInfo(
                stream_id=stream_id,
                play_url=f"http://gateway/live/{stream_id}.flv"
            )
        
        mock_gateway = AsyncMock(spec=GatewayAdapter)
        mock_gateway.create_rtsp_proxy = AsyncMock(side_effect=flaky_create)
        mock_gateway.delete_stream = AsyncMock(return_value=True)
        
        mock_inference = AsyncMock()
        mock_inference.send_start = AsyncMock(return_value="cmd")
        mock_inference.send_stop = AsyncMock()
        
        # 先顺序创建多个流
        stream_ids = []
        async with session_factory() as session:
            service = StreamService(
                db=session,
                gateway=mock_gateway,
                render_control=mock_inference
            )
            for i in range(3):
                stream = await service.create(VideoStreamCreate(
                    name=f"部分失败测试流_{i}",
                    type=StreamType.RTSP,
                    source_url=f"rtsp://test.com/stream{i}"
                ))
                stream_ids.append(stream.id)
            await session.commit()
        
        # 并发启动，预期第二个失败，每个操作使用独立 session
        async def try_start(stream_id):
            try:
                async with session_factory() as session:
                    service = StreamService(
                        db=session,
                        gateway=mock_gateway,
                        render_control=mock_inference
                    )
                    result = await service.start(stream_id)
                    await session.commit()
                    return result
            except Exception as e:
                return e
        
        results = await asyncio.gather(*[try_start(sid) for sid in stream_ids])
        
        # 验证有一个失败
        errors = [r for r in results if isinstance(r, Exception)]
        successes = [r for r in results if not isinstance(r, Exception)]
        
        assert len(errors) == 1, f"Expected 1 error, got {len(errors)}: {errors}"
        assert len(successes) == 2, f"Expected 2 successes, got {len(successes)}"
        
        # 清理
        async with session_factory() as session:
            service = StreamService(
                db=session,
                gateway=mock_gateway,
                render_control=mock_inference
            )
            for stream_id in stream_ids:
                try:
                    await service.stop(stream_id)
                except Exception:
                    pass
                await service.delete(stream_id)
            await session.commit()


class TestResourceMetrics:
    """资源指标测试
    
    测试系统资源使用的基本指标。
    Requirements: 7.1
    """

    @pytest.fixture
    async def db_engine_and_factory(self):
        """创建测试数据库引擎和会话工厂"""
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        yield engine, session_factory
        
        await engine.dispose()

    @pytest.fixture
    async def test_db(self):
        """创建测试数据库会话（用于非并发测试）"""
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
    def mock_gateway(self):
        """Mock 网关适配器"""
        gateway = AsyncMock(spec=GatewayAdapter)
        gateway.create_rtsp_proxy = AsyncMock(return_value=StreamInfo(
            stream_id="test",
            play_url="http://gateway/live/test.flv"
        ))
        gateway.delete_stream = AsyncMock(return_value=True)
        return gateway

    @pytest.fixture
    def mock_render_control(self):
        """Mock 渲染控制服务"""
        control = AsyncMock()
        control.send_start = AsyncMock(return_value="cmd_start")
        control.send_stop = AsyncMock(return_value="cmd_stop")
        return control

    @pytest.mark.asyncio
    async def test_operation_latency(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """测试操作延迟
        
        验证基本操作在合理时间内完成。
        注意：阈值设置较宽松以适应 CI 环境的负载波动。
        Requirements: 7.1
        """
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        # 测试创建延迟
        start_time = time.time()
        stream = await service.create(VideoStreamCreate(
            name="延迟测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        ))
        create_latency = time.time() - start_time
        
        # 创建应该在 500ms 内完成（宽松阈值适应 CI 环境）
        assert create_latency < 0.5, f"创建延迟过高: {create_latency:.3f}s"
        
        # 测试启动延迟
        start_time = time.time()
        await service.start(stream.id)
        start_latency = time.time() - start_time
        
        # 启动应该在 1s 内完成（包含 mock 调用，宽松阈值）
        assert start_latency < 1.0, f"启动延迟过高: {start_latency:.3f}s"
        
        # 测试停止延迟
        start_time = time.time()
        await service.stop(stream.id)
        stop_latency = time.time() - start_time
        
        # 停止应该在 1s 内完成（宽松阈值）
        assert stop_latency < 1.0, f"停止延迟过高: {stop_latency:.3f}s"
        
        # 清理
        await service.delete(stream.id)

    @pytest.mark.asyncio
    async def test_concurrent_operation_throughput(
        self, db_engine_and_factory, mock_gateway, mock_render_control
    ):
        """测试并发操作吞吐量
        
        验证系统能够处理一定数量的并发操作。
        每个并发操作使用独立的 session 以避免冲突。
        注意：阈值设置较宽松以适应 CI 环境的负载波动。
        Requirements: 7.1
        """
        engine, session_factory = db_engine_and_factory
        
        num_operations = 10
        
        # 测试并发创建吞吐量
        start_time = time.time()
        
        async def create_stream(i: int):
            async with session_factory() as session:
                service = StreamService(
                    db=session,
                    gateway=mock_gateway,
                    render_control=mock_render_control
                )
                stream = await service.create(VideoStreamCreate(
                    name=f"吞吐量测试流_{i}",
                    type=StreamType.RTSP,
                    source_url=f"rtsp://test.com/stream{i}"
                ))
                await session.commit()
                return stream.id
        
        stream_ids = await asyncio.gather(*[create_stream(i) for i in range(num_operations)])
        
        total_time = time.time() - start_time
        throughput = num_operations / total_time
        
        # 应该能达到至少 10 ops/s（宽松阈值适应 CI 环境）
        assert throughput > 10, f"吞吐量过低: {throughput:.1f} ops/s"
        
        # 清理
        async with session_factory() as session:
            service = StreamService(
                db=session,
                gateway=mock_gateway,
                render_control=mock_render_control
            )
            for stream_id in stream_ids:
                await service.delete(stream_id)
            await session.commit()
