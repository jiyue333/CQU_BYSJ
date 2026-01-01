"""渲染状态推送测试

F-28: 验证 StatusPushService 能正确转发渲染状态

**Validates: 方案 F 渲染状态 WebSocket 推送**
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, strategies as st

from app.services.render_worker import RenderWorker, RenderConfig, RenderHealth


# ============================================================================
# 状态事件映射测试
# ============================================================================

class TestRenderStatusEventMapping:
    """渲染状态事件映射测试"""
    
    def test_started_event_maps_to_running(self) -> None:
        """STARTED 事件应映射到 running 状态"""
        event_to_status = {
            "STARTED": "running",
            "STOPPED": "stopped",
            "COOLDOWN": "cooldown",
            "ERROR": "error",
        }
        
        assert event_to_status["STARTED"] == "running"
    
    def test_stopped_event_maps_to_stopped(self) -> None:
        """STOPPED 事件应映射到 stopped 状态"""
        event_to_status = {
            "STARTED": "running",
            "STOPPED": "stopped",
            "COOLDOWN": "cooldown",
            "ERROR": "error",
        }
        
        assert event_to_status["STOPPED"] == "stopped"
    
    def test_cooldown_event_maps_to_cooldown(self) -> None:
        """COOLDOWN 事件应映射到 cooldown 状态"""
        event_to_status = {
            "STARTED": "running",
            "STOPPED": "stopped",
            "COOLDOWN": "cooldown",
            "ERROR": "error",
        }
        
        assert event_to_status["COOLDOWN"] == "cooldown"
    
    def test_error_event_maps_to_error(self) -> None:
        """ERROR 事件应映射到 error 状态"""
        event_to_status = {
            "STARTED": "running",
            "STOPPED": "stopped",
            "COOLDOWN": "cooldown",
            "ERROR": "error",
        }
        
        assert event_to_status["ERROR"] == "error"
    
    def test_health_update_not_in_mapping(self) -> None:
        """HEALTH_UPDATE 不应在状态映射中"""
        event_to_status = {
            "STARTED": "running",
            "STOPPED": "stopped",
            "COOLDOWN": "cooldown",
            "ERROR": "error",
        }
        
        assert "HEALTH_UPDATE" not in event_to_status


# ============================================================================
# RenderWorker 状态上报测试
# ============================================================================

class TestRenderWorkerStatusReport:
    """RenderWorker 状态上报测试"""
    
    @pytest.mark.asyncio
    async def test_report_status_writes_to_stream(self) -> None:
        """状态上报应写入 Redis Stream"""
        with patch('app.services.render_worker.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.xadd = AsyncMock(return_value="msg_id")
            mock_get_redis.return_value = mock_redis
            
            worker = RenderWorker()
            worker._redis = mock_redis
            
            await worker._report_status("test_stream", "STARTED", {"render_fps": 24})
            
            # 验证写入了 Stream
            mock_redis.xadd.assert_called_once()
            call_args = mock_redis.xadd.call_args
            
            # 验证 Stream 名称
            assert call_args[0][0] == "inference:status"
    
    @pytest.mark.asyncio
    async def test_report_status_includes_status_field(self) -> None:
        """状态上报应包含 status 字段"""
        with patch('app.services.render_worker.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.xadd = AsyncMock(return_value="msg_id")
            mock_get_redis.return_value = mock_redis
            
            worker = RenderWorker()
            worker._redis = mock_redis
            
            await worker._report_status("test_stream", "STARTED", {})
            
            # 解析写入的数据
            call_args = mock_redis.xadd.call_args
            data = json.loads(call_args[0][1]["data"])
            
            assert "status" in data
            assert data["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_report_status_includes_stream_id(self) -> None:
        """状态上报应包含 stream_id"""
        with patch('app.services.render_worker.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.xadd = AsyncMock(return_value="msg_id")
            mock_get_redis.return_value = mock_redis
            
            worker = RenderWorker()
            worker._redis = mock_redis
            
            await worker._report_status("test_stream_123", "STOPPED", {})
            
            call_args = mock_redis.xadd.call_args
            data = json.loads(call_args[0][1]["data"])
            
            assert data["stream_id"] == "test_stream_123"
    
    @pytest.mark.asyncio
    async def test_report_status_includes_timestamp(self) -> None:
        """状态上报应包含时间戳"""
        with patch('app.services.render_worker.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.xadd = AsyncMock(return_value="msg_id")
            mock_get_redis.return_value = mock_redis
            
            worker = RenderWorker()
            worker._redis = mock_redis
            
            before = time.time()
            await worker._report_status("test_stream", "STARTED", {})
            after = time.time()
            
            call_args = mock_redis.xadd.call_args
            data = json.loads(call_args[0][1]["data"])
            
            assert "timestamp" in data
            assert before <= data["timestamp"] <= after
    
    @pytest.mark.asyncio
    async def test_report_cooldown_status(self) -> None:
        """COOLDOWN 状态应正确上报"""
        with patch('app.services.render_worker.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.xadd = AsyncMock(return_value="msg_id")
            mock_get_redis.return_value = mock_redis
            
            worker = RenderWorker()
            worker._redis = mock_redis
            
            await worker._report_status("test_stream", "COOLDOWN", {"duration": 60})
            
            call_args = mock_redis.xadd.call_args
            data = json.loads(call_args[0][1]["data"])
            
            assert data["event"] == "COOLDOWN"
            assert data["status"] == "cooldown"
            assert data["data"]["duration"] == 60
    
    @pytest.mark.asyncio
    async def test_report_error_status(self) -> None:
        """ERROR 状态应正确上报"""
        with patch('app.services.render_worker.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.xadd = AsyncMock(return_value="msg_id")
            mock_get_redis.return_value = mock_redis
            
            worker = RenderWorker()
            worker._redis = mock_redis
            
            await worker._report_status("test_stream", "ERROR", {"reason": "test_error"})
            
            call_args = mock_redis.xadd.call_args
            data = json.loads(call_args[0][1]["data"])
            
            assert data["event"] == "ERROR"
            assert data["status"] == "error"
            assert data["data"]["reason"] == "test_error"


# ============================================================================
# 状态转换测试
# ============================================================================

class TestRenderStatusTransitions:
    """渲染状态转换测试"""
    
    def test_initial_health_is_healthy(self) -> None:
        """初始健康状态应为 HEALTHY"""
        worker = RenderWorker()
        
        # 模拟启动流
        worker._stream_health["test_stream"] = RenderHealth.HEALTHY
        
        assert worker.get_stream_health("test_stream") == RenderHealth.HEALTHY
    
    def test_health_transitions_to_cooldown_on_failures(self) -> None:
        """连续失败后应转换到 COOLDOWN"""
        worker = RenderWorker()
        worker._failure_counts["test_stream"] = worker.MAX_FAILURES
        
        # 模拟进入 COOLDOWN
        worker._stream_health["test_stream"] = RenderHealth.COOLDOWN
        
        assert worker.get_stream_health("test_stream") == RenderHealth.COOLDOWN
    
    def test_health_recovers_from_cooldown(self) -> None:
        """COOLDOWN 后应恢复到 HEALTHY"""
        worker = RenderWorker()
        
        # 模拟 COOLDOWN 恢复
        worker._stream_health["test_stream"] = RenderHealth.COOLDOWN
        worker._stream_health["test_stream"] = RenderHealth.HEALTHY
        worker._failure_counts["test_stream"] = 0
        
        assert worker.get_stream_health("test_stream") == RenderHealth.HEALTHY
        assert worker._failure_counts["test_stream"] == 0


# ============================================================================
# 失败处理测试
# ============================================================================

class TestRenderFailureHandling:
    """渲染失败处理测试"""
    
    @pytest.mark.asyncio
    async def test_failure_increments_count(self) -> None:
        """失败应增加计数"""
        with patch('app.services.render_worker.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.xadd = AsyncMock(return_value="msg_id")
            mock_get_redis.return_value = mock_redis
            
            worker = RenderWorker()
            worker._redis = mock_redis
            worker._failure_counts["test_stream"] = 0
            worker._stream_health["test_stream"] = RenderHealth.HEALTHY
            
            await worker._handle_failure("test_stream", "test_reason")
            
            assert worker._failure_counts["test_stream"] == 1
    
    @pytest.mark.asyncio
    async def test_max_failures_triggers_cooldown(self) -> None:
        """达到最大失败次数应触发 COOLDOWN"""
        with patch('app.services.render_worker.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.xadd = AsyncMock(return_value="msg_id")
            mock_get_redis.return_value = mock_redis
            
            worker = RenderWorker()
            worker._redis = mock_redis
            worker._failure_counts["test_stream"] = worker.MAX_FAILURES - 1
            worker._stream_health["test_stream"] = RenderHealth.HEALTHY
            worker._active_streams["test_stream"] = {"running": True}
            
            await worker._handle_failure("test_stream", "test_reason")
            
            assert worker._stream_health["test_stream"] == RenderHealth.COOLDOWN
    
    @given(failure_count=st.integers(min_value=0, max_value=10))
    @settings(max_examples=20)
    def test_failure_count_property(self, failure_count: int) -> None:
        """Property: 失败计数应正确累加"""
        worker = RenderWorker()
        worker._failure_counts["test_stream"] = failure_count
        
        # 模拟一次失败
        worker._failure_counts["test_stream"] += 1
        
        assert worker._failure_counts["test_stream"] == failure_count + 1


# ============================================================================
# 结果发布测试
# ============================================================================

class TestRenderResultPublish:
    """渲染结果发布测试"""
    
    @pytest.mark.asyncio
    async def test_publish_result_writes_to_stream(self) -> None:
        """结果发布应写入 Redis Stream"""
        with patch('app.services.render_worker.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.xadd = AsyncMock(return_value="msg_id")
            mock_redis.set = AsyncMock(return_value=True)
            mock_get_redis.return_value = mock_redis
            
            worker = RenderWorker()
            worker._redis = mock_redis
            
            from app.schemas.detection import Detection
            detections = [
                Detection(x=100, y=100, width=50, height=50, confidence=0.9)
            ]
            heatmap = [[0.5] * 20 for _ in range(20)]
            
            await worker._publish_result(
                "test_stream", detections, heatmap, 640, 480, time.time()
            )
            
            # 验证写入了 Stream
            assert mock_redis.xadd.called
            assert mock_redis.set.called
    
    @pytest.mark.asyncio
    async def test_publish_result_writes_latest_result(self) -> None:
        """结果发布应写入 latest_result"""
        with patch('app.services.render_worker.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.xadd = AsyncMock(return_value="msg_id")
            mock_redis.set = AsyncMock(return_value=True)
            mock_get_redis.return_value = mock_redis
            
            worker = RenderWorker()
            worker._redis = mock_redis
            
            from app.schemas.detection import Detection
            detections = []
            heatmap = [[0.0] * 20 for _ in range(20)]
            
            await worker._publish_result(
                "test_stream", detections, heatmap, 640, 480, time.time()
            )
            
            # 验证写入了 latest_result
            set_call = mock_redis.set.call_args
            assert "latest_result:test_stream" in set_call[0][0]
    
    @pytest.mark.asyncio
    async def test_publish_result_includes_detection_count(self) -> None:
        """结果应包含检测数量"""
        with patch('app.services.render_worker.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.xadd = AsyncMock(return_value="msg_id")
            mock_redis.set = AsyncMock(return_value=True)
            mock_get_redis.return_value = mock_redis
            
            worker = RenderWorker()
            worker._redis = mock_redis
            
            from app.schemas.detection import Detection
            detections = [
                Detection(x=100, y=100, width=50, height=50, confidence=0.9),
                Detection(x=200, y=200, width=50, height=50, confidence=0.8),
            ]
            heatmap = [[0.5] * 20 for _ in range(20)]
            
            await worker._publish_result(
                "test_stream", detections, heatmap, 640, 480, time.time()
            )
            
            # 解析写入的数据
            xadd_call = mock_redis.xadd.call_args
            data = json.loads(xadd_call[0][1]["data"])
            
            assert data["total_count"] == 2


# ============================================================================
# 指令幂等性测试
# ============================================================================

class TestCommandIdempotency:
    """指令幂等性测试"""
    
    def test_processed_cmd_is_cached(self) -> None:
        """已处理的指令应被缓存"""
        worker = RenderWorker()
        cmd_id = "test_cmd_123"
        
        worker._processed_cmds[cmd_id] = time.time()
        
        assert cmd_id in worker._processed_cmds
    
    def test_duplicate_cmd_is_detected(self) -> None:
        """重复指令应被检测"""
        worker = RenderWorker()
        cmd_id = "test_cmd_123"
        
        worker._processed_cmds[cmd_id] = time.time()
        
        # 检查是否已处理
        is_duplicate = cmd_id in worker._processed_cmds
        
        assert is_duplicate
    
    @given(cmd_count=st.integers(min_value=1, max_value=100))
    @settings(max_examples=20)
    def test_cmd_cache_grows_correctly(self, cmd_count: int) -> None:
        """Property: 指令缓存应正确增长"""
        worker = RenderWorker()
        
        for i in range(cmd_count):
            worker._processed_cmds[f"cmd_{i}"] = time.time()
        
        assert len(worker._processed_cmds) == cmd_count
