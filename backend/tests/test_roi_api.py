"""ROI API 测试

测试 ROI 管理 REST API 的基本功能。
Requirements: 3.1, 3.2, 3.5
"""

import re
import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.roi import ROI
from app.models.video_stream import StreamStatus, StreamType, VideoStream
from app.schemas.roi import ROICreate, ROIUpdate, Point, DensityThresholds


# UUID v4 正则表达式
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE
)


@pytest.fixture
async def test_db():
    """创建测试数据库会话"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # 启用 SQLite 外键约束
    from sqlalchemy import event
    
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
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
async def test_stream(test_db: AsyncSession) -> VideoStream:
    """创建测试用视频流"""
    stream = VideoStream(
        id=str(uuid.uuid4()),
        name="测试视频流",
        type=StreamType.RTSP,
        status=StreamStatus.STOPPED,
        source_url="rtsp://test.com/stream"
    )
    test_db.add(stream)
    await test_db.commit()
    await test_db.refresh(stream)
    return stream


class TestROICreation:
    """ROI 创建测试"""

    @pytest.mark.asyncio
    async def test_create_roi_returns_valid_id(self, test_db: AsyncSession, test_stream: VideoStream):
        """测试创建 ROI 返回有效的 ID
        
        Requirements: 3.1
        """
        roi = ROI(
            id=str(uuid.uuid4()),
            stream_id=test_stream.id,
            name="前区",
            points=[{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}, {"x": 0, "y": 100}],
            density_thresholds={"low": 0.3, "medium": 0.6, "high": 0.8}
        )
        
        test_db.add(roi)
        await test_db.commit()
        await test_db.refresh(roi)
        
        assert roi.id is not None
        assert UUID_PATTERN.match(roi.id)
        assert roi.stream_id == test_stream.id
        assert roi.name == "前区"
        assert len(roi.points) == 4

    @pytest.mark.asyncio
    async def test_create_multiple_rois_for_stream(self, test_db: AsyncSession, test_stream: VideoStream):
        """测试为同一视频流创建多个 ROI
        
        Requirements: 3.2
        """
        roi_names = ["前区", "中区", "后区"]
        
        for name in roi_names:
            roi = ROI(
                id=str(uuid.uuid4()),
                stream_id=test_stream.id,
                name=name,
                points=[{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}],
                density_thresholds={"low": 0.3, "medium": 0.6, "high": 0.8}
            )
            test_db.add(roi)
        
        await test_db.commit()
        
        # 刷新 stream 以加载关联的 ROIs
        await test_db.refresh(test_stream)
        
        assert len(test_stream.rois) == 3
        assert set(r.name for r in test_stream.rois) == set(roi_names)


class TestROIUpdate:
    """ROI 更新测试"""

    @pytest.mark.asyncio
    async def test_update_roi_name(self, test_db: AsyncSession, test_stream: VideoStream):
        """测试更新 ROI 名称
        
        Requirements: 3.5
        """
        roi = ROI(
            id=str(uuid.uuid4()),
            stream_id=test_stream.id,
            name="原名称",
            points=[{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}],
            density_thresholds={"low": 0.3, "medium": 0.6, "high": 0.8}
        )
        test_db.add(roi)
        await test_db.commit()
        
        # 更新名称
        roi.name = "新名称"
        await test_db.commit()
        await test_db.refresh(roi)
        
        assert roi.name == "新名称"

    @pytest.mark.asyncio
    async def test_update_roi_points(self, test_db: AsyncSession, test_stream: VideoStream):
        """测试更新 ROI 多边形顶点
        
        Requirements: 3.5
        """
        roi = ROI(
            id=str(uuid.uuid4()),
            stream_id=test_stream.id,
            name="测试区域",
            points=[{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}],
            density_thresholds={"low": 0.3, "medium": 0.6, "high": 0.8}
        )
        test_db.add(roi)
        await test_db.commit()
        
        # 更新顶点
        new_points = [{"x": 10, "y": 10}, {"x": 200, "y": 10}, {"x": 200, "y": 200}, {"x": 10, "y": 200}]
        roi.points = new_points
        await test_db.commit()
        await test_db.refresh(roi)
        
        assert len(roi.points) == 4
        assert roi.points[0]["x"] == 10

    @pytest.mark.asyncio
    async def test_update_roi_thresholds(self, test_db: AsyncSession, test_stream: VideoStream):
        """测试更新 ROI 密度阈值
        
        Requirements: 3.5
        """
        roi = ROI(
            id=str(uuid.uuid4()),
            stream_id=test_stream.id,
            name="测试区域",
            points=[{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}],
            density_thresholds={"low": 0.3, "medium": 0.6, "high": 0.8}
        )
        test_db.add(roi)
        await test_db.commit()
        
        # 更新阈值
        roi.density_thresholds = {"low": 0.2, "medium": 0.5, "high": 0.9}
        await test_db.commit()
        await test_db.refresh(roi)
        
        assert roi.density_thresholds["low"] == 0.2
        assert roi.density_thresholds["medium"] == 0.5
        assert roi.density_thresholds["high"] == 0.9


class TestROIDeletion:
    """ROI 删除测试"""

    @pytest.mark.asyncio
    async def test_delete_roi(self, test_db: AsyncSession, test_stream: VideoStream):
        """测试删除 ROI
        
        Requirements: 3.2
        """
        roi = ROI(
            id=str(uuid.uuid4()),
            stream_id=test_stream.id,
            name="待删除区域",
            points=[{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}],
            density_thresholds={"low": 0.3, "medium": 0.6, "high": 0.8}
        )
        test_db.add(roi)
        await test_db.commit()
        
        roi_id = roi.id
        
        # 删除 ROI
        await test_db.delete(roi)
        await test_db.commit()
        
        # 验证已删除
        from sqlalchemy import select
        result = await test_db.execute(select(ROI).where(ROI.id == roi_id))
        deleted_roi = result.scalar_one_or_none()
        
        assert deleted_roi is None

    @pytest.mark.asyncio
    async def test_cascade_delete_rois_when_stream_deleted(self, test_db: AsyncSession, test_stream: VideoStream):
        """测试删除视频流时级联删除关联的 ROI
        
        Requirements: 3.2
        """
        # 创建多个 ROI
        roi_ids = []
        for i in range(3):
            roi = ROI(
                id=str(uuid.uuid4()),
                stream_id=test_stream.id,
                name=f"区域{i}",
                points=[{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}],
                density_thresholds={"low": 0.3, "medium": 0.6, "high": 0.8}
            )
            test_db.add(roi)
            roi_ids.append(roi.id)
        
        await test_db.commit()
        
        # 删除视频流
        await test_db.delete(test_stream)
        await test_db.commit()
        
        # 验证所有 ROI 都已删除
        from sqlalchemy import select
        for roi_id in roi_ids:
            result = await test_db.execute(select(ROI).where(ROI.id == roi_id))
            assert result.scalar_one_or_none() is None


class TestROISchemaValidation:
    """ROI Schema 验证测试"""

    def test_roi_create_schema_valid(self):
        """测试有效的 ROI 创建 Schema"""
        data = ROICreate(
            name="测试区域",
            points=[
                Point(x=0, y=0),
                Point(x=100, y=0),
                Point(x=100, y=100),
            ],
            density_thresholds=DensityThresholds(low=0.3, medium=0.6, high=0.8)
        )
        
        assert data.name == "测试区域"
        assert len(data.points) == 3

    def test_roi_create_schema_minimum_points(self):
        """测试 ROI 至少需要 3 个顶点"""
        with pytest.raises(ValueError):
            ROICreate(
                name="测试区域",
                points=[
                    Point(x=0, y=0),
                    Point(x=100, y=0),
                ],
                density_thresholds=DensityThresholds(low=0.3, medium=0.6, high=0.8)
            )

    def test_roi_create_schema_negative_coordinates_rejected(self):
        """测试负坐标被拒绝"""
        with pytest.raises(ValueError):
            ROICreate(
                name="测试区域",
                points=[
                    Point(x=-1, y=0),
                    Point(x=100, y=0),
                    Point(x=100, y=100),
                ],
                density_thresholds=DensityThresholds(low=0.3, medium=0.6, high=0.8)
            )

    def test_density_thresholds_order_validation(self):
        """测试密度阈值顺序验证"""
        with pytest.raises(ValueError):
            DensityThresholds(low=0.6, medium=0.3, high=0.8)

    def test_roi_update_schema_partial_update(self):
        """测试 ROI 更新 Schema 支持部分更新"""
        # 只更新名称
        data = ROIUpdate(name="新名称")
        assert data.name == "新名称"
        assert data.points is None
        assert data.density_thresholds is None
        
        # 只更新顶点
        data = ROIUpdate(points=[
            Point(x=0, y=0),
            Point(x=100, y=0),
            Point(x=100, y=100),
        ])
        assert data.name is None
        assert len(data.points) == 3
