"""ROI 属性测试

Property 4: ROI 配置持久化
*For any* ROI 配置，保存后读取应返回等价的配置对象
**Validates: Requirements 3.1**

Feature: crowd-counting-system, Property 4: ROI 配置持久化
"""

import json
import pytest
from hypothesis import given, strategies as st, settings, assume
from pydantic import ValidationError

from app.schemas.roi import (
    Point,
    DensityThresholds,
    ROIBase,
    ROICreate,
    ROIResponse,
)


# 策略：生成有效的坐标值（非负浮点数）
coordinate_strategy = st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False)

# 策略：生成有效的 Point
point_strategy = st.builds(
    Point,
    x=coordinate_strategy,
    y=coordinate_strategy,
)

# 策略：生成有效的多边形（至少3个点）
polygon_strategy = st.lists(point_strategy, min_size=3, max_size=20)

# 策略：生成有效的阈值（0-1之间，且满足 low < medium < high）
def valid_thresholds_strategy():
    """生成满足 low < medium < high 的阈值"""
    return st.tuples(
        st.floats(min_value=0.01, max_value=0.3, allow_nan=False),
        st.floats(min_value=0.31, max_value=0.6, allow_nan=False),
        st.floats(min_value=0.61, max_value=0.99, allow_nan=False),
    ).map(lambda t: DensityThresholds(low=t[0], medium=t[1], high=t[2]))


# 策略：生成有效的 ROI 名称
name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S")),
    min_size=1,
    max_size=100
).filter(lambda x: x.strip())


class TestPointSerialization:
    """Point 序列化属性测试"""

    @given(x=coordinate_strategy, y=coordinate_strategy)
    @settings(max_examples=100)
    def test_point_round_trip(self, x: float, y: float):
        """Property: Point 序列化后反序列化应返回等价对象
        
        *For any* 有效的坐标 (x, y)，Point 的 JSON 序列化/反序列化应保持一致
        **Validates: Requirements 3.1**
        """
        original = Point(x=x, y=y)
        
        # 序列化为 JSON
        json_str = original.model_dump_json()
        
        # 反序列化
        restored = Point.model_validate_json(json_str)
        
        # 验证等价性
        assert abs(restored.x - original.x) < 1e-10, f"x 不一致: {original.x} vs {restored.x}"
        assert abs(restored.y - original.y) < 1e-10, f"y 不一致: {original.y} vs {restored.y}"

    @given(x=coordinate_strategy, y=coordinate_strategy)
    @settings(max_examples=100)
    def test_point_dict_round_trip(self, x: float, y: float):
        """Property: Point 转换为 dict 后应能重建
        
        *For any* 有效的 Point，转换为 dict 后应能重建等价对象
        **Validates: Requirements 3.1**
        """
        original = Point(x=x, y=y)
        
        # 转换为 dict
        data = original.model_dump()
        
        # 从 dict 重建
        restored = Point(**data)
        
        assert restored == original


class TestDensityThresholdsSerialization:
    """DensityThresholds 序列化属性测试"""

    @given(thresholds=valid_thresholds_strategy())
    @settings(max_examples=100)
    def test_thresholds_round_trip(self, thresholds: DensityThresholds):
        """Property: DensityThresholds 序列化后反序列化应返回等价对象
        
        *For any* 有效的阈值配置，JSON 序列化/反序列化应保持一致
        **Validates: Requirements 3.1**
        """
        # 序列化为 JSON
        json_str = thresholds.model_dump_json()
        
        # 反序列化
        restored = DensityThresholds.model_validate_json(json_str)
        
        # 验证等价性
        assert abs(restored.low - thresholds.low) < 1e-10
        assert abs(restored.medium - thresholds.medium) < 1e-10
        assert abs(restored.high - thresholds.high) < 1e-10

    @given(thresholds=valid_thresholds_strategy())
    @settings(max_examples=100)
    def test_thresholds_order_preserved(self, thresholds: DensityThresholds):
        """Property: 阈值顺序在序列化后应保持 low < medium < high
        
        *For any* 有效的阈值配置，序列化后阈值顺序应保持不变
        **Validates: Requirements 3.1**
        """
        # 序列化为 dict
        data = thresholds.model_dump()
        
        # 从 dict 重建
        restored = DensityThresholds(**data)
        
        # 验证顺序
        assert restored.low < restored.medium < restored.high

    def test_invalid_thresholds_order_rejected(self):
        """Property: 无效的阈值顺序应被拒绝
        
        阈值必须满足 low < medium < high
        **Validates: Requirements 3.1**
        """
        # low >= medium
        with pytest.raises(ValidationError):
            DensityThresholds(low=0.5, medium=0.3, high=0.8)
        
        # medium >= high
        with pytest.raises(ValidationError):
            DensityThresholds(low=0.3, medium=0.9, high=0.8)


class TestROIConfigPersistence:
    """ROI 配置持久化属性测试"""

    @given(
        name=name_strategy,
        points=polygon_strategy,
        thresholds=valid_thresholds_strategy()
    )
    @settings(max_examples=100)
    def test_roi_config_round_trip(
        self, 
        name: str, 
        points: list[Point], 
        thresholds: DensityThresholds
    ):
        """Property: ROI 配置序列化后反序列化应返回等价对象
        
        *For any* 有效的 ROI 配置，JSON 序列化/反序列化应保持一致
        **Validates: Requirements 3.1**
        """
        assume(len(name.strip()) > 0)  # 确保名称非空
        
        original = ROICreate(
            name=name,
            points=points,
            density_thresholds=thresholds,
        )
        
        # 序列化为 JSON
        json_str = original.model_dump_json()
        
        # 反序列化
        restored = ROICreate.model_validate_json(json_str)
        
        # 验证等价性
        assert restored.name == original.name
        assert len(restored.points) == len(original.points)
        for i, (p1, p2) in enumerate(zip(restored.points, original.points)):
            assert abs(p1.x - p2.x) < 1e-10, f"Point {i} x 不一致"
            assert abs(p1.y - p2.y) < 1e-10, f"Point {i} y 不一致"
        assert abs(restored.density_thresholds.low - original.density_thresholds.low) < 1e-10
        assert abs(restored.density_thresholds.medium - original.density_thresholds.medium) < 1e-10
        assert abs(restored.density_thresholds.high - original.density_thresholds.high) < 1e-10

    @given(
        name=name_strategy,
        points=polygon_strategy,
        thresholds=valid_thresholds_strategy()
    )
    @settings(max_examples=100)
    def test_roi_json_storage_simulation(
        self, 
        name: str, 
        points: list[Point], 
        thresholds: DensityThresholds
    ):
        """Property: ROI 配置存储到 JSON 字段后应能正确恢复
        
        模拟 PostgreSQL JSON 字段的存储和读取过程
        *For any* 有效的 ROI 配置，存储到 JSON 后应能正确恢复
        **Validates: Requirements 3.1**
        """
        assume(len(name.strip()) > 0)
        
        original = ROICreate(
            name=name,
            points=points,
            density_thresholds=thresholds,
        )
        
        # 模拟存储到数据库 JSON 字段
        points_json = [p.model_dump() for p in original.points]
        thresholds_json = original.density_thresholds.model_dump()
        
        # 模拟从数据库读取
        restored_points = [Point(**p) for p in points_json]
        restored_thresholds = DensityThresholds(**thresholds_json)
        
        # 验证等价性
        assert len(restored_points) == len(original.points)
        for p1, p2 in zip(restored_points, original.points):
            assert p1 == p2
        assert restored_thresholds.low == original.density_thresholds.low
        assert restored_thresholds.medium == original.density_thresholds.medium
        assert restored_thresholds.high == original.density_thresholds.high


class TestROIValidation:
    """ROI 验证属性测试"""

    def test_polygon_minimum_points(self):
        """Property: 多边形至少需要3个顶点
        
        **Validates: Requirements 3.1**
        """
        # 2个点应该被拒绝
        with pytest.raises(ValidationError):
            ROICreate(
                name="test",
                points=[Point(x=0, y=0), Point(x=1, y=1)],
            )
        
        # 3个点应该被接受
        roi = ROICreate(
            name="test",
            points=[Point(x=0, y=0), Point(x=1, y=0), Point(x=0, y=1)],
        )
        assert len(roi.points) == 3

    def test_negative_coordinates_rejected(self):
        """Property: 负坐标应被拒绝
        
        **Validates: Requirements 3.1**
        """
        with pytest.raises(ValidationError):
            Point(x=-1, y=0)
        
        with pytest.raises(ValidationError):
            Point(x=0, y=-1)

    @given(points=polygon_strategy)
    @settings(max_examples=100)
    def test_polygon_points_count_preserved(self, points: list[Point]):
        """Property: 多边形顶点数量在序列化后应保持不变
        
        *For any* 有效的多边形，顶点数量应在序列化后保持不变
        **Validates: Requirements 3.1**
        """
        original_count = len(points)
        
        roi = ROICreate(
            name="test",
            points=points,
        )
        
        # 序列化后反序列化
        json_str = roi.model_dump_json()
        restored = ROICreate.model_validate_json(json_str)
        
        assert len(restored.points) == original_count
