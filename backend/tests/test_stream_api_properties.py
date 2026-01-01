"""流管理 API 属性测试

Property 1: 视频源统一抽象
*For any* 视频源类型（file/webcam/rtsp），创建成功后都应返回有效的 stream_id
**Validates: Requirements 1.1, 1.2, 1.3, 1.4**

Feature: crowd-counting-system, Property 1: 视频源统一抽象
"""

import re
import uuid
from unittest.mock import AsyncMock

import pytest
from hypothesis import given, strategies as st, settings as hypothesis_settings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.video_stream import StreamStatus, StreamType, VideoStream
from app.schemas.video_stream import VideoStreamCreate
from app.services.stream_service import StreamService, get_stream_service


# UUID v4 正则表达式
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE
)


# 策略：生成有效的流名称
valid_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S")),
    min_size=1,
    max_size=100
).filter(lambda x: x.strip())

# 策略：生成有效的 RTSP URL
rtsp_url_strategy = st.from_regex(
    r"rtsp://[a-z0-9]+(\.[a-z0-9]+)*(:[0-9]+)?/[a-z0-9/]+",
    fullmatch=True
)

# 策略：生成有效的 UUID
uuid_strategy = st.uuids().map(str)


@pytest.fixture
async def test_db():
    """创建测试数据库会话"""
    # 使用内存 SQLite 数据库进行测试
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
        AsyncMock(whip_url="http://test/whip", token="test", expires_at=0, ice_servers=[])
    ))
    gateway.delete_stream = AsyncMock(return_value=True)
    return gateway


@pytest.fixture
def mock_render_control():
    """Mock 渲染控制服务"""
    control = AsyncMock()
    control.send_start = AsyncMock(return_value="cmd_123")
    control.send_stop = AsyncMock(return_value="cmd_456")
    return control


class TestVideoSourceUnifiedAbstraction:
    """Property 1: 视频源统一抽象测试
    
    *For any* 视频源类型（file/webcam/rtsp），创建成功后都应返回有效的 stream_id
    **Validates: Requirements 1.1, 1.2, 1.3, 1.4**
    """

    @pytest.mark.asyncio
    async def test_file_stream_returns_valid_stream_id(
        self, 
        test_db: AsyncSession,
        mock_gateway,
        mock_render_control,
    ):
        """Property: FILE 类型视频源创建后返回有效的 stream_id
        
        *For any* 有效的文件名和 file_id，创建 FILE 类型流应返回有效的 UUID stream_id
        **Validates: Requirements 1.1, 1.4**
        """
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        # 测试多个不同的输入
        test_cases = [
            ("视频1", str(uuid.uuid4())),
            ("Video File", str(uuid.uuid4())),
            ("测试文件_123", str(uuid.uuid4())),
        ]
        
        for name, file_id in test_cases:
            data = VideoStreamCreate(
                name=name,
                type=StreamType.FILE,
                file_id=file_id
            )
            
            stream = await service.create(data)
            
            # 验证返回有效的 stream_id
            assert stream.id is not None
            assert UUID_PATTERN.match(stream.id), f"stream_id {stream.id} 不是有效的 UUID"
            assert stream.type == StreamType.FILE

    @pytest.mark.asyncio
    async def test_file_stream_creation(self, test_db: AsyncSession, mock_gateway, mock_render_control):
        """测试 FILE 类型流创建"""
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        data = VideoStreamCreate(
            name="测试视频文件",
            type=StreamType.FILE,
            file_id=str(uuid.uuid4())
        )
        
        stream = await service.create(data)
        
        # 验证返回有效的 stream_id
        assert stream.id is not None
        assert UUID_PATTERN.match(stream.id), f"stream_id {stream.id} 不是有效的 UUID"
        assert stream.type == StreamType.FILE
        assert stream.status == StreamStatus.STOPPED

    @pytest.mark.asyncio
    async def test_webcam_stream_creation(self, test_db: AsyncSession, mock_gateway, mock_render_control):
        """测试 WEBCAM 类型流创建"""
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        data = VideoStreamCreate(
            name="浏览器摄像头",
            type=StreamType.WEBCAM
        )
        
        stream = await service.create(data)
        
        # 验证返回有效的 stream_id
        assert stream.id is not None
        assert UUID_PATTERN.match(stream.id), f"stream_id {stream.id} 不是有效的 UUID"
        assert stream.type == StreamType.WEBCAM
        assert stream.status == StreamStatus.STOPPED

    @pytest.mark.asyncio
    async def test_rtsp_stream_creation(self, test_db: AsyncSession, mock_gateway, mock_render_control):
        """测试 RTSP 类型流创建"""
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        data = VideoStreamCreate(
            name="RTSP 摄像头",
            type=StreamType.RTSP,
            source_url="rtsp://192.168.1.100:554/stream"
        )
        
        stream = await service.create(data)
        
        # 验证返回有效的 stream_id
        assert stream.id is not None
        assert UUID_PATTERN.match(stream.id), f"stream_id {stream.id} 不是有效的 UUID"
        assert stream.type == StreamType.RTSP
        assert stream.status == StreamStatus.STOPPED


    @pytest.mark.asyncio
    async def test_all_stream_types_return_valid_uuid(self, test_db: AsyncSession, mock_gateway, mock_render_control):
        """Property: 所有视频源类型创建后都返回有效的 UUID stream_id
        
        *For any* 视频源类型，创建成功后 stream_id 应该是有效的 UUID v4
        **Validates: Requirements 1.1, 1.2, 1.3, 1.4**
        """
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        test_cases = [
            VideoStreamCreate(
                name="文件流",
                type=StreamType.FILE,
                file_id=str(uuid.uuid4())
            ),
            VideoStreamCreate(
                name="摄像头流",
                type=StreamType.WEBCAM
            ),
            VideoStreamCreate(
                name="RTSP流",
                type=StreamType.RTSP,
                source_url="rtsp://test.com/stream"
            ),
        ]
        
        for data in test_cases:
            stream = await service.create(data)
            
            # 验证 stream_id 是有效的 UUID
            assert stream.id is not None, f"{data.type} 类型流的 stream_id 为空"
            assert UUID_PATTERN.match(stream.id), (
                f"{data.type} 类型流的 stream_id {stream.id} 不是有效的 UUID"
            )
            
            # 验证类型正确
            assert stream.type == data.type, (
                f"流类型不匹配：预期 {data.type}，实际 {stream.type}"
            )


class TestStreamLifecycleProperties:
    """流生命周期属性测试"""

    @pytest.mark.asyncio
    async def test_created_stream_starts_in_stopped_state(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """Property: 新创建的流初始状态为 STOPPED
        
        *For any* 新创建的流，初始状态应该是 STOPPED
        **Validates: Requirements 1.4**
        """
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        for stream_type in StreamType:
            if stream_type == StreamType.FILE:
                data = VideoStreamCreate(
                    name=f"测试{stream_type.value}",
                    type=stream_type,
                    file_id=str(uuid.uuid4())
                )
            elif stream_type == StreamType.RTSP:
                data = VideoStreamCreate(
                    name=f"测试{stream_type.value}",
                    type=stream_type,
                    source_url="rtsp://test.com/stream"
                )
            else:
                data = VideoStreamCreate(
                    name=f"测试{stream_type.value}",
                    type=stream_type
                )
            
            stream = await service.create(data)
            assert stream.status == StreamStatus.STOPPED, (
                f"{stream_type} 类型流创建后状态应为 STOPPED，实际为 {stream.status}"
            )

    @pytest.mark.asyncio
    async def test_started_stream_has_play_url(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """Property: 启动后的流应该有 play_url
        
        *For any* 成功启动的流，应该有有效的 play_url
        **Validates: Requirements 1.4**
        """
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        # 创建 RTSP 流
        data = VideoStreamCreate(
            name="测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        )
        stream = await service.create(data)
        
        # 启动流
        started_stream, _ = await service.start(stream.id)
        
        assert started_stream.status == StreamStatus.RUNNING
        assert started_stream.play_url is not None
        assert started_stream.play_url.startswith("http")

    @pytest.mark.asyncio
    async def test_stopped_stream_has_no_play_url(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """Property: 停止后的流 play_url 应该为空
        
        *For any* 停止的流，play_url 应该为 None
        **Validates: Requirements 1.5**
        """
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        # 创建并启动流
        data = VideoStreamCreate(
            name="测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        )
        stream = await service.create(data)
        await service.start(stream.id)
        
        # 停止流
        stopped_stream = await service.stop(stream.id)
        
        assert stopped_stream.status == StreamStatus.STOPPED
        assert stopped_stream.play_url is None


class TestConcurrentLimitProperties:
    """并发限制属性测试"""

    @pytest.mark.asyncio
    async def test_running_count_increases_on_start(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """Property: 启动流后运行中的流数量增加
        
        *For any* 启动操作，运行中的流数量应该增加 1
        **Validates: Requirements 7.1**
        """
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        initial_count = await service.get_running_count()
        
        # 创建并启动流
        data = VideoStreamCreate(
            name="测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        )
        stream = await service.create(data)
        await service.start(stream.id)
        
        new_count = await service.get_running_count()
        assert new_count == initial_count + 1

    @pytest.mark.asyncio
    async def test_running_count_decreases_on_stop(
        self, test_db: AsyncSession, mock_gateway, mock_render_control
    ):
        """Property: 停止流后运行中的流数量减少
        
        *For any* 停止操作，运行中的流数量应该减少 1
        **Validates: Requirements 7.1**
        """
        service = StreamService(
            db=test_db,
            gateway=mock_gateway,
            render_control=mock_render_control
        )
        
        # 创建并启动流
        data = VideoStreamCreate(
            name="测试流",
            type=StreamType.RTSP,
            source_url="rtsp://test.com/stream"
        )
        stream = await service.create(data)
        await service.start(stream.id)
        
        count_before_stop = await service.get_running_count()
        
        # 停止流
        await service.stop(stream.id)
        
        count_after_stop = await service.get_running_count()
        assert count_after_stop == count_before_stop - 1


class TestHypothesisProperties:
    """使用 Hypothesis 的真正属性测试
    
    **Feature: crowd-counting-system, Property 1: 视频源统一抽象**
    """

    @hypothesis_settings(max_examples=100)
    @given(
        name=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P", "S")),
            min_size=1,
            max_size=50
        ).filter(lambda x: x.strip()),
        file_id=st.uuids(version=4).map(str)
    )
    @pytest.mark.asyncio
    async def test_create_file_stream_returns_valid_uuid_property(self, name: str, file_id: str):
        """Property: FILE 类型流创建后返回有效的 UUID stream_id
        
        *For any* 有效的名称和 file_id，创建 FILE 类型流应返回有效的 UUID v4 stream_id
        **Validates: Requirements 1.1, 1.4**
        """
        # 每次测试创建新的数据库会话
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
            # Mock 依赖
            mock_gateway = AsyncMock()
            mock_inference = AsyncMock()
            
            service = StreamService(
                db=session,
                gateway=mock_gateway,
                render_control=mock_inference
            )
            
            data = VideoStreamCreate(
                name=name.strip(),
                type=StreamType.FILE,
                file_id=file_id
            )
            
            stream = await service.create(data)
            
            # 验证返回有效的 UUID v4
            assert stream.id is not None
            assert UUID_PATTERN.match(stream.id), f"stream_id {stream.id} 不是有效的 UUID v4"
            assert stream.type == StreamType.FILE
            assert stream.status == StreamStatus.STOPPED
        
        await engine.dispose()

    @hypothesis_settings(max_examples=100)
    @given(
        name=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P", "S")),
            min_size=1,
            max_size=50
        ).filter(lambda x: x.strip())
    )
    @pytest.mark.asyncio
    async def test_create_webcam_stream_returns_valid_uuid_property(self, name: str):
        """Property: WEBCAM 类型流创建后返回有效的 UUID stream_id
        
        *For any* 有效的名称，创建 WEBCAM 类型流应返回有效的 UUID v4 stream_id
        **Validates: Requirements 1.2, 1.4**
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
            mock_gateway = AsyncMock()
            mock_inference = AsyncMock()
            
            service = StreamService(
                db=session,
                gateway=mock_gateway,
                render_control=mock_inference
            )
            
            data = VideoStreamCreate(
                name=name.strip(),
                type=StreamType.WEBCAM
            )
            
            stream = await service.create(data)
            
            assert stream.id is not None
            assert UUID_PATTERN.match(stream.id), f"stream_id {stream.id} 不是有效的 UUID v4"
            assert stream.type == StreamType.WEBCAM
            assert stream.status == StreamStatus.STOPPED
        
        await engine.dispose()

    @hypothesis_settings(max_examples=100)
    @given(
        name=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P", "S")),
            min_size=1,
            max_size=50
        ).filter(lambda x: x.strip()),
        host=st.from_regex(r"[a-z0-9]+(\.[a-z0-9]+)*", fullmatch=True),
        port=st.integers(min_value=1, max_value=65535),
        path=st.from_regex(r"[a-z0-9/]+", fullmatch=True)
    )
    @pytest.mark.asyncio
    async def test_create_rtsp_stream_returns_valid_uuid_property(
        self, name: str, host: str, port: int, path: str
    ):
        """Property: RTSP 类型流创建后返回有效的 UUID stream_id
        
        *For any* 有效的名称和 RTSP URL，创建 RTSP 类型流应返回有效的 UUID v4 stream_id
        **Validates: Requirements 1.3, 1.4**
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
            mock_gateway = AsyncMock()
            mock_inference = AsyncMock()
            
            service = StreamService(
                db=session,
                gateway=mock_gateway,
                render_control=mock_inference
            )
            
            rtsp_url = f"rtsp://{host}:{port}/{path}"
            
            data = VideoStreamCreate(
                name=name.strip(),
                type=StreamType.RTSP,
                source_url=rtsp_url
            )
            
            stream = await service.create(data)
            
            assert stream.id is not None
            assert UUID_PATTERN.match(stream.id), f"stream_id {stream.id} 不是有效的 UUID v4"
            assert stream.type == StreamType.RTSP
            assert stream.status == StreamStatus.STOPPED
        
        await engine.dispose()
