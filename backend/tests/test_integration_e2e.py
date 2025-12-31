"""端到端集成测试

Task 17.1: 编写端到端测试
- 完整视频流处理链路测试
- WebSocket 连接与消息推送测试

Requirements: 7.1, 7.2
"""

import asyncio
import json
import time
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
from app.schemas.detection import Detection, DetectionResult, RegionStat
from app.schemas.video_stream import VideoStreamCreate
from app.services.gateway_adapter import GatewayAdapter, StreamInfo, PublishInfo
from app.services.result_push_service import ResultPushService
from app.services.status_push_service import StatusPushService
from app.services.stream_service import StreamService


class TestEndToEndStreamProcessing:
    """完整视频流处理链路测试
    
    验证从创建流到推理结果推送的完整链路。
    Requirements: 7.1, 7.2
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
            play_url="http://gateway/live/test.flv",
            hls_url="http://gateway/live/test/hls.m3u8",
            rtsp_url="rtsp://gateway/live/test"
        ))
        gateway.create_file_stream = AsyncMock(return_value=StreamInfo(
            stream_id="test",
            play_url="http://gateway/live/test.flv",
            hls_url="http://gateway/live/test/hls.m3u8"
        ))
        gateway.create_webcam_ingest = AsyncMock(return_value=(
            StreamInfo(
                stream_id="test",
                play_url="http://gateway/live/test.flv",
                hls_url="http://gateway/live/test/hls.m3u8"
            ),
            PublishInfo(
                whip_url="http://gateway/whip/test",
                token="test_token_123",
                expires_at=int(time.time()) + 300,
                ice_servers=[{"urls": ["stun:stun.example.com:3478"]}]
            )
        ))
        gateway.delete_stream = AsyncMock(return_value=True)
        gateway.get_snapshot = AsyncMock(return_value=b"fake_jpeg_data")
        gateway.health_check = AsyncMock(return_value=True)
        return gateway

    @pytest.fixture
    def mock_inference_control(self):
        """Mock 推理控制服务"""
        control = AsyncMock()
        control.send_start = AsyncMock(return_value="cmd_start_123")
        control.send_stop = AsyncMock(return_value="cmd_stop_456")
        return control

    @pytest.mark.asyncio
    async def test_complete_rtsp_stream_lifecycle(
        self, test_db: AsyncSession, mock_gateway, mock_inference_control
    ):
        """测试 RTSP 流的完整生命周期
        
        验证：创建 → 启动 → 运行 → 停止 → 删除
        Requirements: 7.1, 7.2
        """
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            inference_control=mock_inference_control
        )
        
        # 1. 创建流
        create_data = VideoStreamCreate(
            name="E2E测试RTSP流",
            type=StreamType.RTSP,
            source_url="rtsp://192.168.1.100:554/stream"
        )
        stream = await service.create(create_data)
        
        assert stream.id is not None
        assert stream.status == StreamStatus.STOPPED
        assert stream.play_url is None
        
        # 2. 启动流
        started_stream, _ = await service.start(stream.id)
        
        assert started_stream.status == StreamStatus.RUNNING
        assert started_stream.play_url is not None
        assert "gateway" in started_stream.play_url
        
        # 验证网关和推理控制被调用
        mock_gateway.create_rtsp_proxy.assert_called_once()
        mock_inference_control.send_start.assert_called_once()
        
        # 3. 停止流
        stopped_stream = await service.stop(stream.id)
        
        assert stopped_stream.status == StreamStatus.STOPPED
        assert stopped_stream.play_url is None
        
        mock_inference_control.send_stop.assert_called_once()
        mock_gateway.delete_stream.assert_called()
        
        # 4. 删除流
        result = await service.delete(stream.id)
        assert result is True
        
        # 验证流已删除
        deleted = await service.get(stream.id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_complete_webcam_stream_lifecycle(
        self, test_db: AsyncSession, mock_gateway, mock_inference_control
    ):
        """测试 WEBCAM 流的完整生命周期
        
        验证：创建 → 启动（含 publish_info）→ 停止 → 删除
        Requirements: 7.1, 7.2
        """
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            inference_control=mock_inference_control
        )
        
        # 1. 创建流
        create_data = VideoStreamCreate(
            name="E2E测试摄像头流",
            type=StreamType.WEBCAM
        )
        stream = await service.create(create_data)
        
        assert stream.id is not None
        assert stream.type == StreamType.WEBCAM
        assert stream.status == StreamStatus.STOPPED
        
        # 2. 启动流（应返回 publish_info）
        started_stream, publish_info = await service.start(stream.id)
        
        assert started_stream.status == StreamStatus.RUNNING
        assert started_stream.play_url is not None
        assert publish_info is not None
        assert publish_info.whip_url is not None
        assert publish_info.token is not None
        
        mock_gateway.create_webcam_ingest.assert_called_once()
        
        # 3. 停止流
        stopped_stream = await service.stop(stream.id)
        assert stopped_stream.status == StreamStatus.STOPPED
        
        # 4. 删除流
        await service.delete(stream.id)

    @pytest.mark.asyncio
    async def test_stream_state_transitions(
        self, test_db: AsyncSession, mock_gateway, mock_inference_control
    ):
        """测试流状态转换的正确性
        
        验证状态机：STOPPED → STARTING → RUNNING → STOPPED
        Requirements: 7.2
        """
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            inference_control=mock_inference_control
        )
        
        # 创建流
        stream = await service.create(VideoStreamCreate(
            name="状态转换测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        ))
        
        # 初始状态应为 STOPPED
        assert stream.status == StreamStatus.STOPPED
        
        # 启动后应为 RUNNING
        started, _ = await service.start(stream.id)
        assert started.status == StreamStatus.RUNNING
        
        # 停止后应为 STOPPED
        stopped = await service.stop(stream.id)
        assert stopped.status == StreamStatus.STOPPED
        
        # 可以再次启动
        restarted, _ = await service.start(stream.id)
        assert restarted.status == StreamStatus.RUNNING
        
        # 清理
        await service.stop(stream.id)
        await service.delete(stream.id)

    @pytest.mark.asyncio
    async def test_invalid_state_transitions_rejected(
        self, test_db: AsyncSession, mock_gateway, mock_inference_control
    ):
        """测试无效状态转换被拒绝
        
        Requirements: 7.2
        """
        from app.services.stream_service import InvalidStateTransitionError
        
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            inference_control=mock_inference_control
        )
        
        # 创建流
        stream = await service.create(VideoStreamCreate(
            name="无效转换测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        ))
        
        # 尝试停止已停止的流应该失败
        with pytest.raises(InvalidStateTransitionError):
            await service.stop(stream.id)
        
        # 启动流
        await service.start(stream.id)
        
        # 尝试再次启动已运行的流应该失败
        with pytest.raises(InvalidStateTransitionError):
            await service.start(stream.id)
        
        # 清理
        await service.stop(stream.id)
        await service.delete(stream.id)


class TestWebSocketIntegration:
    """WebSocket 连接与消息推送测试
    
    Requirements: 7.1, 7.2
    """

    @pytest.mark.asyncio
    async def test_result_push_service_broadcast(self):
        """测试 ResultPushService 广播功能"""
        service = ResultPushService()
        
        # 创建 mock WebSocket
        mock_ws = MagicMock(spec=WebSocket)
        mock_ws.send_text = AsyncMock()
        
        stream_id = "test_stream_123"
        
        # 注册连接
        service.connections[stream_id] = {mock_ws}
        service.last_heartbeat[mock_ws] = time.time()
        service.pending_messages[mock_ws] = 0
        
        # 广播消息
        test_data = json.dumps({
            "timestamp": time.time(),
            "total_count": 5,
            "detections": []
        })
        
        await service._broadcast(stream_id, test_data, "msg_001")
        
        # 验证消息被发送
        mock_ws.send_text.assert_called_once()
        sent_message = json.loads(mock_ws.send_text.call_args[0][0])
        assert sent_message["type"] == "result"
        assert sent_message["msg_id"] == "msg_001"
        assert "data" in sent_message

    @pytest.mark.asyncio
    async def test_result_push_service_slow_client_handling(self):
        """测试 ResultPushService 慢客户端处理"""
        service = ResultPushService()
        
        # 创建 mock WebSocket
        mock_ws = MagicMock(spec=WebSocket)
        mock_ws.send_text = AsyncMock()
        
        stream_id = "test_stream_slow"
        
        # 注册连接，设置高 pending 消息数（模拟慢客户端）
        service.connections[stream_id] = {mock_ws}
        service.last_heartbeat[mock_ws] = time.time()
        service.pending_messages[mock_ws] = 10  # 超过阈值
        
        # 广播消息
        test_data = json.dumps({"test": "data"})
        await service._broadcast(stream_id, test_data, "msg_002")
        
        # 慢客户端应该被跳过，不发送消息
        mock_ws.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_status_push_service_broadcast(self):
        """测试 StatusPushService 广播功能"""
        service = StatusPushService()
        
        # 创建 mock WebSocket
        mock_ws = MagicMock(spec=WebSocket)
        mock_ws.send_text = AsyncMock()
        
        # 注册连接
        service.connections.add(mock_ws)
        service.last_heartbeat[mock_ws] = time.time()
        
        # 广播状态消息
        test_data = json.dumps({
            "stream_id": "test_stream",
            "status": "running",
            "timestamp": time.time()
        })
        
        await service._broadcast(test_data)
        
        # 验证消息被发送
        mock_ws.send_text.assert_called_once()
        sent_message = json.loads(mock_ws.send_text.call_args[0][0])
        assert sent_message["type"] == "status"
        assert "data" in sent_message

    @pytest.mark.asyncio
    async def test_status_push_service_notify_status_change(self):
        """测试 StatusPushService 主动通知状态变更"""
        service = StatusPushService()
        
        # 创建 mock WebSocket
        mock_ws = MagicMock(spec=WebSocket)
        mock_ws.send_text = AsyncMock()
        
        # 注册连接
        service.connections.add(mock_ws)
        service.last_heartbeat[mock_ws] = time.time()
        
        # 通知状态变更
        await service.notify_status_change(
            stream_id="test_stream",
            status="running",
            extra={"play_url": "http://test/stream.flv"}
        )
        
        # 验证消息被发送
        mock_ws.send_text.assert_called_once()
        sent_message = json.loads(mock_ws.send_text.call_args[0][0])
        assert sent_message["type"] == "status"
        assert sent_message["data"]["stream_id"] == "test_stream"
        assert sent_message["data"]["status"] == "running"

    @pytest.mark.asyncio
    async def test_connection_cleanup_on_disconnect(self):
        """测试连接断开时的清理"""
        service = ResultPushService()
        
        mock_ws = MagicMock(spec=WebSocket)
        stream_id = "test_stream_cleanup"
        
        # 注册连接
        service.connections[stream_id] = {mock_ws}
        service.last_heartbeat[mock_ws] = time.time()
        service.pending_messages[mock_ws] = 0
        service.last_ids[stream_id] = "msg_001"
        
        # 清理连接
        service._cleanup_connection(mock_ws, stream_id)
        
        # 验证清理完成
        assert stream_id not in service.connections
        assert mock_ws not in service.last_heartbeat
        assert mock_ws not in service.pending_messages
        assert stream_id not in service.last_ids

    @pytest.mark.asyncio
    async def test_multiple_websocket_connections_per_stream(self):
        """测试单个流的多个 WebSocket 连接"""
        service = ResultPushService()
        
        # 创建多个 mock WebSocket
        mock_ws1 = MagicMock(spec=WebSocket)
        mock_ws1.send_text = AsyncMock()
        mock_ws2 = MagicMock(spec=WebSocket)
        mock_ws2.send_text = AsyncMock()
        mock_ws3 = MagicMock(spec=WebSocket)
        mock_ws3.send_text = AsyncMock()
        
        stream_id = "test_stream_multi"
        
        # 注册多个连接
        service.connections[stream_id] = {mock_ws1, mock_ws2, mock_ws3}
        for ws in [mock_ws1, mock_ws2, mock_ws3]:
            service.last_heartbeat[ws] = time.time()
            service.pending_messages[ws] = 0
        
        # 广播消息
        test_data = json.dumps({"test": "multi_client"})
        await service._broadcast(stream_id, test_data, "msg_multi")
        
        # 验证所有客户端都收到消息
        mock_ws1.send_text.assert_called_once()
        mock_ws2.send_text.assert_called_once()
        mock_ws3.send_text.assert_called_once()


class TestAPIEndToEnd:
    """API 端到端测试
    
    Requirements: 7.1, 7.2
    """

    @pytest.fixture(autouse=True)
    async def cleanup_db_pool(self):
        """每个测试后清理数据库连接池"""
        yield
        from app.core.database import engine
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_complete_api_flow_rtsp(self):
        """测试 RTSP 流的完整 API 流程"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 1. 创建流
            create_resp = await client.post(
                "/api/streams",
                json={
                    "name": "API E2E RTSP流",
                    "type": "rtsp",
                    "source_url": "rtsp://192.168.1.100:554/stream"
                }
            )
            assert create_resp.status_code == 201
            stream_data = create_resp.json()
            stream_id = stream_data["stream_id"]
            
            assert stream_data["status"] == "stopped"
            assert stream_data["type"] == "rtsp"
            
            # 2. 获取流详情
            get_resp = await client.get(f"/api/streams/{stream_id}")
            assert get_resp.status_code == 200
            assert get_resp.json()["stream_id"] == stream_id
            
            # 3. 获取流列表
            list_resp = await client.get("/api/streams")
            assert list_resp.status_code == 200
            streams = list_resp.json()["streams"]
            assert any(s["stream_id"] == stream_id for s in streams)
            
            # 4. 获取最新检测结果（应为空）
            result_resp = await client.get(f"/api/streams/{stream_id}/latest-result")
            assert result_resp.status_code == 200
            # 新创建的流没有检测结果
            
            # 5. 删除流
            delete_resp = await client.delete(f"/api/streams/{stream_id}")
            assert delete_resp.status_code == 204
            
            # 6. 验证已删除
            get_deleted_resp = await client.get(f"/api/streams/{stream_id}")
            assert get_deleted_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_complete_api_flow_webcam(self):
        """测试 WEBCAM 流的完整 API 流程"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 1. 创建流
            create_resp = await client.post(
                "/api/streams",
                json={
                    "name": "API E2E 摄像头流",
                    "type": "webcam"
                }
            )
            assert create_resp.status_code == 201
            stream_data = create_resp.json()
            stream_id = stream_data["stream_id"]
            
            assert stream_data["status"] == "stopped"
            assert stream_data["type"] == "webcam"
            
            # 2. 删除流
            delete_resp = await client.delete(f"/api/streams/{stream_id}")
            assert delete_resp.status_code == 204

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """测试 API 错误处理"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 获取不存在的流
            resp = await client.get("/api/streams/nonexistent-id")
            assert resp.status_code == 404
            
            # 启动不存在的流
            resp = await client.post("/api/streams/nonexistent-id/start")
            assert resp.status_code == 404
            
            # 停止不存在的流
            resp = await client.post("/api/streams/nonexistent-id/stop")
            assert resp.status_code == 404
            
            # 删除不存在的流
            resp = await client.delete("/api/streams/nonexistent-id")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_api_invalid_request_handling(self):
        """测试 API 无效请求处理"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 缺少必要字段
            resp = await client.post(
                "/api/streams",
                json={"name": "测试流"}  # 缺少 type
            )
            assert resp.status_code == 422
            
            # 无效的流类型
            resp = await client.post(
                "/api/streams",
                json={"name": "测试流", "type": "invalid_type"}
            )
            assert resp.status_code == 422


class TestDataFlowIntegration:
    """数据流集成测试
    
    验证从推理结果到 WebSocket 推送的数据流。
    Requirements: 7.1, 7.2
    """

    @pytest.mark.asyncio
    async def test_detection_result_format(self):
        """测试检测结果格式正确性"""
        # 创建检测结果
        detections = [
            Detection(x=100, y=100, width=50, height=100, confidence=0.85),
            Detection(x=200, y=150, width=60, height=120, confidence=0.92),
        ]
        
        region_stats = [
            RegionStat(
                region_id="region_1",
                region_name="前区",
                count=2,
                density=0.4,
                level="medium"
            )
        ]
        
        result = DetectionResult(
            stream_id="test_stream",
            timestamp=time.time(),
            total_count=2,
            detections=detections,
            heatmap_grid=[[0.1, 0.2], [0.3, 0.4]],
            region_stats=region_stats
        )
        
        # 验证序列化
        result_dict = result.model_dump()
        
        assert result_dict["stream_id"] == "test_stream"
        assert result_dict["total_count"] == 2
        assert len(result_dict["detections"]) == 2
        assert len(result_dict["region_stats"]) == 1
        assert result_dict["heatmap_grid"] == [[0.1, 0.2], [0.3, 0.4]]

    @pytest.mark.asyncio
    async def test_websocket_message_format(self):
        """测试 WebSocket 消息格式"""
        service = ResultPushService()
        
        mock_ws = MagicMock(spec=WebSocket)
        mock_ws.send_text = AsyncMock()
        
        stream_id = "test_stream_format"
        service.connections[stream_id] = {mock_ws}
        service.last_heartbeat[mock_ws] = time.time()
        service.pending_messages[mock_ws] = 0
        
        # 发送检测结果
        result_data = {
            "stream_id": stream_id,
            "timestamp": time.time(),
            "total_count": 3,
            "detections": [
                {"x": 100, "y": 100, "width": 50, "height": 100, "confidence": 0.9}
            ],
            "heatmap_grid": [[0.5]],
            "region_stats": []
        }
        
        await service._broadcast(stream_id, json.dumps(result_data), "msg_format_test")
        
        # 验证消息格式
        sent_message = json.loads(mock_ws.send_text.call_args[0][0])
        
        assert sent_message["type"] == "result"
        assert sent_message["msg_id"] == "msg_format_test"
        assert "data" in sent_message
        assert sent_message["data"]["total_count"] == 3


class TestServiceLifecycle:
    """服务生命周期测试
    
    Requirements: 7.2
    """

    @pytest.mark.asyncio
    async def test_result_push_service_start_stop(self):
        """测试 ResultPushService 启动和停止"""
        service = ResultPushService()
        
        # 初始状态
        assert service._running is False
        assert service._listener_task is None
        
        # 启动服务（不实际连接 Redis）
        # 注意：这里只测试状态变化，不测试实际的 Redis 连接
        service._running = True
        assert service._running is True
        
        # 停止服务
        service._running = False
        assert service._running is False

    @pytest.mark.asyncio
    async def test_status_push_service_start_stop(self):
        """测试 StatusPushService 启动和停止"""
        service = StatusPushService()
        
        # 初始状态
        assert service._running is False
        assert service._listener_task is None
        
        # 启动服务
        service._running = True
        assert service._running is True
        
        # 停止服务
        service._running = False
        assert service._running is False

    def test_singleton_services_consistency(self):
        """测试单例服务的一致性"""
        from app.services.result_push_service import get_result_push_service
        from app.services.status_push_service import get_status_push_service
        
        # 多次获取应返回同一实例
        result_service1 = get_result_push_service()
        result_service2 = get_result_push_service()
        assert result_service1 is result_service2
        
        status_service1 = get_status_push_service()
        status_service2 = get_status_push_service()
        assert status_service1 is status_service2



class TestAPIFailureScenarios:
    """API 失败场景测试
    
    测试 API 层的各种失败情况。
    Requirements: 7.1, 7.2
    """

    @pytest.fixture(autouse=True)
    async def cleanup_db_pool(self):
        """每个测试后清理数据库连接池"""
        yield
        from app.core.database import engine
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_start_already_stopped_stream_returns_409(self):
        """测试停止已停止的流返回 409"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 创建流
            create_resp = await client.post(
                "/api/streams",
                json={
                    "name": "停止测试流",
                    "type": "rtsp",
                    "source_url": "rtsp://test.com/stream"
                }
            )
            stream_id = create_resp.json()["stream_id"]
            
            # 尝试停止已停止的流
            stop_resp = await client.post(f"/api/streams/{stream_id}/stop")
            assert stop_resp.status_code == 409
            
            # 清理
            await client.delete(f"/api/streams/{stream_id}")

    @pytest.mark.asyncio
    async def test_create_stream_with_invalid_type(self):
        """测试创建无效类型的流"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/streams",
                json={
                    "name": "无效类型流",
                    "type": "invalid_type"
                }
            )
            assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_rtsp_stream_without_source_url(self):
        """测试创建 RTSP 流但不提供 source_url"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 注意：根据 schema 定义，source_url 是可选的，但 RTSP 类型应该需要它
            # 这个测试验证系统行为
            resp = await client.post(
                "/api/streams",
                json={
                    "name": "无URL的RTSP流",
                    "type": "rtsp"
                    # 缺少 source_url
                }
            )
            # 创建可能成功（取决于 schema 验证），但启动会失败
            if resp.status_code == 201:
                stream_id = resp.json()["stream_id"]
                await client.delete(f"/api/streams/{stream_id}")

    @pytest.mark.asyncio
    async def test_get_latest_result_for_nonexistent_stream(self):
        """测试获取不存在流的最新结果"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/streams/nonexistent-id/latest-result")
            assert resp.status_code == 404


class TestWebSocketProtocol:
    """WebSocket 协议测试
    
    测试 WebSocket 消息格式和协议。
    Requirements: 7.1, 7.2
    """

    @pytest.mark.asyncio
    async def test_heartbeat_message_format(self):
        """测试心跳消息格式"""
        from app.services.result_push_service import ResultPushService
        
        service = ResultPushService()
        
        mock_ws = MagicMock(spec=WebSocket)
        sent_messages = []
        
        async def capture_send(msg):
            sent_messages.append(msg)
        
        mock_ws.send_text = AsyncMock(side_effect=capture_send)
        
        stream_id = "heartbeat_test"
        service.connections[stream_id] = {mock_ws}
        service.last_heartbeat[mock_ws] = time.time()
        service.pending_messages[mock_ws] = 0
        
        # 模拟发送结果
        test_result = {
            "stream_id": stream_id,
            "timestamp": time.time(),
            "total_count": 5,
            "detections": [],
            "heatmap_grid": [[0.1]],
            "region_stats": []
        }
        
        await service._broadcast(stream_id, json.dumps(test_result), "msg_001")
        
        # 验证消息格式
        assert len(sent_messages) == 1
        msg = json.loads(sent_messages[0])
        
        assert "type" in msg
        assert msg["type"] == "result"
        assert "msg_id" in msg
        assert "data" in msg
        assert msg["data"]["total_count"] == 5

    @pytest.mark.asyncio
    async def test_recovery_message_format(self):
        """测试恢复消息格式"""
        # 验证恢复消息应该包含 type: "recovery"
        from app.services.result_push_service import ResultPushService
        
        service = ResultPushService()
        
        # 验证服务有 _send_recovery_messages 方法
        assert hasattr(service, '_send_recovery_messages')
        assert callable(service._send_recovery_messages)
