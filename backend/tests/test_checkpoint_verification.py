"""Checkpoint 6: 后端核心功能验证测试

验证：
- 流管理 API 正常工作
- WebSocket 连接稳定
- 媒体网关集成正常
"""

import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocket
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.main import app
from app.models.video_stream import StreamStatus, StreamType
from app.schemas.video_stream import VideoStreamCreate
from app.services.gateway_adapter import (
    GatewayAdapter,
    StreamInfo,
    PublishInfo,
    ZLMediaKitAdapter,
)
from app.services.result_push_service import ResultPushService
from app.services.status_push_service import StatusPushService
from app.services.stream_service import StreamService


class TestStreamManagementAPI:
    """流管理 API 验证测试"""

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
            play_url="http://test/live/test.flv",
            hls_url="http://test/live/test/hls.m3u8"
        ))
        gateway.create_file_stream = AsyncMock(return_value=StreamInfo(
            stream_id="test",
            play_url="http://test/live/test.flv",
            hls_url="http://test/live/test/hls.m3u8"
        ))
        gateway.create_webcam_ingest = AsyncMock(return_value=(
            StreamInfo(
                stream_id="test",
                play_url="http://test/live/test.flv",
                hls_url="http://test/live/test/hls.m3u8"
            ),
            PublishInfo(
                whip_url="http://test/whip",
                token="test_token",
                expires_at=0,
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
        control.send_start = AsyncMock(return_value="cmd_123")
        control.send_stop = AsyncMock(return_value="cmd_456")
        return control

    @pytest.mark.asyncio
    async def test_stream_crud_operations(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """验证流的 CRUD 操作"""
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        # Create
        data = VideoStreamCreate(
            name="测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        )
        stream = await service.create(data)
        assert stream.id is not None
        assert stream.name == "测试流"
        assert stream.status == StreamStatus.STOPPED
        
        # Read
        fetched = await service.get(stream.id)
        assert fetched is not None
        assert fetched.id == stream.id
        
        # List
        streams = await service.list_all()
        assert len(streams) >= 1
        
        # Delete
        result = await service.delete(stream.id)
        assert result is True
        
        # Verify deleted
        deleted = await service.get(stream.id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_stream_lifecycle_start_stop(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """验证流的启动和停止生命周期"""
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        # Create stream
        data = VideoStreamCreate(
            name="生命周期测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        )
        stream = await service.create(data)
        assert stream.status == StreamStatus.STOPPED
        
        # Start stream
        started_stream, _ = await service.start(stream.id)
        assert started_stream.status == StreamStatus.RUNNING
        assert started_stream.play_url is not None
        
        # Verify gateway was called
        mock_gateway.create_rtsp_proxy.assert_called_once()
        mock_render_control.send_start.assert_called_once()
        
        # Stop stream
        stopped_stream = await service.stop(stream.id)
        assert stopped_stream.status == StreamStatus.STOPPED
        assert stopped_stream.play_url is None
        
        # Verify stop was called
        mock_render_control.send_stop.assert_called_once()
        mock_gateway.delete_stream.assert_called()

    @pytest.mark.asyncio
    async def test_all_stream_types_supported(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """验证所有流类型都能正常创建"""
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        # FILE type
        file_stream = await service.create(VideoStreamCreate(
            name="文件流",
            type=StreamType.FILE,
            file_id=str(uuid.uuid4())
        ))
        assert file_stream.type == StreamType.FILE
        
        # WEBCAM type
        webcam_stream = await service.create(VideoStreamCreate(
            name="摄像头流",
            type=StreamType.WEBCAM
        ))
        assert webcam_stream.type == StreamType.WEBCAM
        
        # RTSP type
        rtsp_stream = await service.create(VideoStreamCreate(
            name="RTSP流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        ))
        assert rtsp_stream.type == StreamType.RTSP


class TestWebSocketServices:
    """WebSocket 服务验证测试"""

    @pytest.mark.asyncio
    async def test_result_push_service_initialization(self):
        """验证 ResultPushService 初始化"""
        service = ResultPushService()
        
        assert service.connections == {}
        assert service.last_heartbeat == {}
        assert service.pending_messages == {}
        assert service._running is False

    @pytest.mark.asyncio
    async def test_status_push_service_initialization(self):
        """验证 StatusPushService 初始化"""
        service = StatusPushService()
        
        assert service.connections == set()
        assert service.last_heartbeat == {}
        assert service._running is False

    @pytest.mark.asyncio
    async def test_result_push_service_connection_management(self):
        """验证 ResultPushService 连接管理"""
        service = ResultPushService()
        
        # Mock WebSocket
        mock_ws = MagicMock(spec=WebSocket)
        stream_id = "test_stream"
        
        # Simulate adding connection
        if stream_id not in service.connections:
            service.connections[stream_id] = set()
        service.connections[stream_id].add(mock_ws)
        service.last_heartbeat[mock_ws] = 12345.0
        service.pending_messages[mock_ws] = 0
        
        assert mock_ws in service.connections[stream_id]
        assert mock_ws in service.last_heartbeat
        assert mock_ws in service.pending_messages
        
        # Simulate cleanup
        service._cleanup_connection(mock_ws, stream_id)
        
        assert stream_id not in service.connections
        assert mock_ws not in service.last_heartbeat
        assert mock_ws not in service.pending_messages

    @pytest.mark.asyncio
    async def test_status_push_service_connection_management(self):
        """验证 StatusPushService 连接管理"""
        service = StatusPushService()
        
        # Mock WebSocket
        mock_ws = MagicMock(spec=WebSocket)
        
        # Simulate adding connection
        service.connections.add(mock_ws)
        service.last_heartbeat[mock_ws] = 12345.0
        
        assert mock_ws in service.connections
        assert mock_ws in service.last_heartbeat
        
        # Simulate cleanup
        service._cleanup_connection(mock_ws)
        
        assert mock_ws not in service.connections
        assert mock_ws not in service.last_heartbeat


class TestGatewayAdapter:
    """媒体网关适配器验证测试"""

    def test_zlmediakit_adapter_initialization(self):
        """验证 ZLMediaKitAdapter 初始化"""
        adapter = ZLMediaKitAdapter(
            base_url="http://localhost:8080",
            secret="test_secret",
            rtsp_port=554
        )
        
        assert adapter.base_url == "http://localhost:8080"
        assert adapter.secret == "test_secret"
        assert adapter.rtsp_port == 554
        assert adapter.app == "live"

    def test_build_play_urls(self):
        """验证播放 URL 构建"""
        adapter = ZLMediaKitAdapter(
            base_url="http://localhost:8080",
            secret="test_secret",
            rtsp_port=554
        )
        
        stream_info = adapter._build_play_urls("test_stream")
        
        assert stream_info.stream_id == "test_stream"
        assert "test_stream" in stream_info.play_url
        assert stream_info.play_url.endswith(".live.flv")
        assert stream_info.hls_url is not None
        assert "hls.m3u8" in stream_info.hls_url
        assert stream_info.rtsp_url is not None
        assert "rtsp://" in stream_info.rtsp_url

    @pytest.mark.asyncio
    async def test_gateway_adapter_interface_completeness(self):
        """验证 GatewayAdapter 接口完整性"""
        adapter = ZLMediaKitAdapter(
            base_url="http://localhost:8080",
            secret="test_secret"
        )
        
        # Verify all required methods exist
        assert hasattr(adapter, 'create_rtsp_proxy')
        assert hasattr(adapter, 'create_file_stream')
        assert hasattr(adapter, 'create_webcam_ingest')
        assert hasattr(adapter, 'delete_stream')
        assert hasattr(adapter, 'get_snapshot')
        assert hasattr(adapter, 'get_stream_info')
        assert hasattr(adapter, 'health_check')
        
        # Verify methods are callable
        assert callable(adapter.create_rtsp_proxy)
        assert callable(adapter.create_file_stream)
        assert callable(adapter.create_webcam_ingest)
        assert callable(adapter.delete_stream)
        assert callable(adapter.get_snapshot)
        assert callable(adapter.get_stream_info)
        assert callable(adapter.health_check)


class TestAPIEndpoints:
    """API 端点验证测试"""

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """验证健康检查端点"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    def test_api_routes_registered(self):
        """验证 API 路由已注册"""
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        
        # Stream management routes
        assert "/api/streams" in routes
        assert "/api/streams/{stream_id}" in routes
        assert "/api/streams/{stream_id}/start" in routes
        assert "/api/streams/{stream_id}/stop" in routes
        assert "/api/streams/{stream_id}/latest-result" in routes
        
        # File routes
        assert "/api/files/upload" in routes
        assert "/api/files" in routes
        assert "/api/files/{file_id}" in routes

    def test_websocket_routes_registered(self):
        """验证 WebSocket 路由已注册"""
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        
        assert "/ws/result/{stream_id}" in routes
        assert "/ws/status" in routes


class TestServiceIntegration:
    """服务集成验证测试"""

    def test_service_imports(self):
        """验证所有服务可以正常导入"""
        from app.services.result_push_service import (
            ResultPushService,
            get_result_push_service,
        )
        from app.services.status_push_service import (
            StatusPushService,
            get_status_push_service,
        )
        from app.services.gateway_adapter import (
            GatewayAdapter,
            ZLMediaKitAdapter,
            get_gateway_adapter,
        )
        from app.services.stream_service import (
            StreamService,
            get_stream_service,
        )
        from app.services.render_control import (
            RenderControlService,
            get_render_control,
        )
        
        # All imports successful
        assert ResultPushService is not None
        assert StatusPushService is not None
        assert GatewayAdapter is not None
        assert ZLMediaKitAdapter is not None
        assert StreamService is not None
        assert RenderControlService is not None

    def test_singleton_services(self):
        """验证单例服务"""
        from app.services.result_push_service import get_result_push_service
        from app.services.status_push_service import get_status_push_service
        from app.services.gateway_adapter import get_gateway_adapter
        
        # Get instances twice
        result_service1 = get_result_push_service()
        result_service2 = get_result_push_service()
        assert result_service1 is result_service2
        
        status_service1 = get_status_push_service()
        status_service2 = get_status_push_service()
        assert status_service1 is status_service2
        
        gateway1 = get_gateway_adapter()
        gateway2 = get_gateway_adapter()
        assert gateway1 is gateway2


class TestStreamAPIHTTPLevel:
    """流管理 API HTTP 层集成测试
    
    这些测试需要运行中的 PostgreSQL、Redis 和 ZLMediaKit 服务。
    """

    @pytest.fixture(autouse=True)
    async def cleanup_db_pool(self):
        """每个测试后清理数据库连接池，避免事件循环问题"""
        yield
        # 测试结束后清理数据库连接池
        from app.core.database import engine
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_health_endpoint_works(self):
        """验证健康检查端点"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_create_and_delete_rtsp_stream(self):
        """验证创建和删除 RTSP 流的完整流程"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 创建流
            create_response = await client.post(
                "/api/streams",
                json={
                    "name": "集成测试RTSP流",
                    "type": "rtsp",
                    "source_url": "rtsp://192.168.1.100:554/stream"
                }
            )
            assert create_response.status_code == 201
            stream_data = create_response.json()
            assert "stream_id" in stream_data
            assert stream_data["name"] == "集成测试RTSP流"
            assert stream_data["type"] == "rtsp"
            assert stream_data["status"] == "stopped"
            
            stream_id = stream_data["stream_id"]
            
            # 获取流详情
            get_response = await client.get(f"/api/streams/{stream_id}")
            assert get_response.status_code == 200
            assert get_response.json()["stream_id"] == stream_id
            
            # 获取流列表
            list_response = await client.get("/api/streams")
            assert list_response.status_code == 200
            streams = list_response.json()["streams"]
            assert any(s["stream_id"] == stream_id for s in streams)
            
            # 删除流
            delete_response = await client.delete(f"/api/streams/{stream_id}")
            assert delete_response.status_code == 204
            
            # 验证已删除
            get_deleted_response = await client.get(f"/api/streams/{stream_id}")
            assert get_deleted_response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_webcam_stream(self):
        """验证创建 WEBCAM 流"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 创建流
            create_response = await client.post(
                "/api/streams",
                json={
                    "name": "集成测试摄像头流",
                    "type": "webcam"
                }
            )
            assert create_response.status_code == 201
            stream_data = create_response.json()
            assert stream_data["type"] == "webcam"
            
            # 清理
            stream_id = stream_data["stream_id"]
            await client.delete(f"/api/streams/{stream_id}")

    @pytest.mark.asyncio
    async def test_get_nonexistent_stream_returns_404(self):
        """验证获取不存在的流返回 404"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/streams/nonexistent-stream-id-12345")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_start_nonexistent_stream_returns_404(self):
        """验证启动不存在的流返回 404"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/streams/nonexistent-stream-id-12345/start")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_stop_nonexistent_stream_returns_404(self):
        """验证停止不存在的流返回 404"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/streams/nonexistent-stream-id-12345/stop")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_stream_returns_404(self):
        """验证删除不存在的流返回 404"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.delete("/api/streams/nonexistent-stream-id-12345")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_state_transition_returns_409(self):
        """验证无效状态转换返回 409"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 创建流
            create_response = await client.post(
                "/api/streams",
                json={
                    "name": "状态转换测试流",
                    "type": "rtsp",
                    "source_url": "rtsp://test.com/stream"
                }
            )
            stream_id = create_response.json()["stream_id"]
            
            # 尝试停止一个已经停止的流（应该返回 409）
            stop_response = await client.post(f"/api/streams/{stream_id}/stop")
            assert stop_response.status_code == 409
            
            # 清理
            await client.delete(f"/api/streams/{stream_id}")


class TestStreamServiceErrorHandling:
    """流服务错误处理验证测试"""

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

    @pytest.mark.asyncio
    async def test_start_rolls_back_on_inference_failure(self, test_db: AsyncSession):
        """验证推理服务启动失败时回滚网关资源"""
        mock_gateway = AsyncMock(spec=GatewayAdapter)
        mock_gateway.create_rtsp_proxy = AsyncMock(return_value=StreamInfo(
            stream_id="test",
            play_url="http://test/live/test.flv"
        ))
        mock_gateway.delete_stream = AsyncMock(return_value=True)
        
        mock_inference = AsyncMock()
        mock_inference.send_start = AsyncMock(side_effect=Exception("Inference failed"))
        mock_inference.send_stop = AsyncMock()
        
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_inference
        )
        
        # Create stream
        data = VideoStreamCreate(
            name="测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        )
        stream = await service.create(data)
        
        # Start should fail and rollback
        from app.services.stream_service import GatewayError
        with pytest.raises(GatewayError):
            await service.start(stream.id)
        
        # Verify gateway cleanup was called
        mock_gateway.delete_stream.assert_called_once_with(stream.id)
        
        # Verify stream status is ERROR
        updated_stream = await service.get(stream.id)
        assert updated_stream.status == StreamStatus.ERROR

    @pytest.mark.asyncio
    async def test_stop_succeeds_even_if_gateway_fails(self, test_db: AsyncSession):
        """验证网关失败时停止操作仍然成功"""
        mock_gateway = AsyncMock(spec=GatewayAdapter)
        mock_gateway.create_rtsp_proxy = AsyncMock(return_value=StreamInfo(
            stream_id="test",
            play_url="http://test/live/test.flv"
        ))
        mock_gateway.delete_stream = AsyncMock(side_effect=Exception("Gateway failed"))
        
        mock_inference = AsyncMock()
        mock_inference.send_start = AsyncMock()
        mock_inference.send_stop = AsyncMock()
        
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_inference
        )
        
        # Create and start stream
        data = VideoStreamCreate(
            name="测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        )
        stream = await service.create(data)
        await service.start(stream.id)
        
        # Stop should succeed even if gateway fails
        stopped_stream = await service.stop(stream.id)
        
        assert stopped_stream.status == StreamStatus.STOPPED
        assert stopped_stream.play_url is None

    @pytest.mark.asyncio
    async def test_stop_succeeds_even_if_render_control_fails(self, test_db: AsyncSession):
        """验证渲染控制失败时停止操作仍然成功"""
        mock_gateway = AsyncMock(spec=GatewayAdapter)
        mock_gateway.create_rtsp_proxy = AsyncMock(return_value=StreamInfo(
            stream_id="test",
            play_url="http://test/live/test.flv"
        ))
        mock_gateway.delete_stream = AsyncMock(return_value=True)
        
        mock_inference = AsyncMock()
        mock_inference.send_start = AsyncMock()
        mock_inference.send_stop = AsyncMock(side_effect=Exception("Inference control failed"))
        
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_inference
        )
        
        # Create and start stream
        data = VideoStreamCreate(
            name="测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        )
        stream = await service.create(data)
        await service.start(stream.id)
        
        # Stop should succeed even if inference control fails
        stopped_stream = await service.stop(stream.id)
        
        assert stopped_stream.status == StreamStatus.STOPPED
        assert stopped_stream.play_url is None

    @pytest.mark.asyncio
    async def test_delete_succeeds_even_if_gateway_fails(self, test_db: AsyncSession):
        """验证网关失败时删除操作仍然成功"""
        mock_gateway = AsyncMock(spec=GatewayAdapter)
        mock_gateway.create_rtsp_proxy = AsyncMock(return_value=StreamInfo(
            stream_id="test",
            play_url="http://test/live/test.flv"
        ))
        mock_gateway.delete_stream = AsyncMock(side_effect=Exception("Gateway failed"))
        
        mock_inference = AsyncMock()
        mock_inference.send_start = AsyncMock()
        mock_inference.send_stop = AsyncMock()
        
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_inference
        )
        
        # Create stream (not started)
        data = VideoStreamCreate(
            name="测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        )
        stream = await service.create(data)
        
        # Delete should succeed even if gateway fails
        result = await service.delete(stream.id)
        
        assert result is True
        
        # Verify stream is deleted
        deleted_stream = await service.get(stream.id)
        assert deleted_stream is None
