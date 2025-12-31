"""密度计算属性测试

Property 3: 密度计算与等级分类
*For any* ROI 区域和检测结果，密度值应等于区域内人数除以区域面积，
且密度等级应根据阈值正确分类
**Validates: Requirements 3.3, 3.4**
"""

import pytest
from hypothesis import given, settings, strategies as st, assume

from app.schemas.detection import Detection, DensityLevel
from app.schemas.roi import DensityThresholds, Point
from app.services.roi_calculator import (
    ROICalculator,
    polygon_area,
    point_in_polygon,
    calculate_density,
    classify_density_level,
)


# 生成有效的 Point 对象
@st.composite
def point_strategy(draw: st.DrawFn, max_coord: float = 1000.0) -> Point:
    """生成随机的 Point 对象"""
    return Point(
        x=draw(st.floats(min_value=0.0, max_value=max_coord, allow_nan=False, allow_infinity=False)),
        y=draw(st.floats(min_value=0.0, max_value=max_coord, allow_nan=False, allow_infinity=False)),
    )


# 生成凸多边形（矩形）
@st.composite
def rectangle_strategy(draw: st.DrawFn) -> list[Point]:
    """生成随机矩形（保证是有效的凸多边形）"""
    x1 = draw(st.floats(min_value=0.0, max_value=500.0, allow_nan=False, allow_infinity=False))
    y1 = draw(st.floats(min_value=0.0, max_value=500.0, allow_nan=False, allow_infinity=False))
    width = draw(st.floats(min_value=10.0, max_value=500.0, allow_nan=False, allow_infinity=False))
    height = draw(st.floats(min_value=10.0, max_value=500.0, allow_nan=False, allow_infinity=False))
    
    return [
        Point(x=x1, y=y1),
        Point(x=x1 + width, y=y1),
        Point(x=x1 + width, y=y1 + height),
        Point(x=x1, y=y1 + height),
    ]


# 生成有效的 Detection 对象
@st.composite
def detection_strategy(draw: st.DrawFn) -> Detection:
    """生成随机的 Detection 对象"""
    return Detection(
        x=draw(st.integers(min_value=0, max_value=1000)),
        y=draw(st.integers(min_value=0, max_value=1000)),
        width=draw(st.integers(min_value=1, max_value=200)),
        height=draw(st.integers(min_value=1, max_value=200)),
        confidence=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
    )


# 生成有效的 DensityThresholds
@st.composite
def thresholds_strategy(draw: st.DrawFn) -> DensityThresholds:
    """生成有效的密度阈值配置"""
    low = draw(st.floats(min_value=0.1, max_value=0.3, allow_nan=False, allow_infinity=False))
    medium = draw(st.floats(min_value=0.4, max_value=0.6, allow_nan=False, allow_infinity=False))
    high = draw(st.floats(min_value=0.7, max_value=0.9, allow_nan=False, allow_infinity=False))
    return DensityThresholds(low=low, medium=medium, high=high)


class TestPolygonAreaProperty:
    """多边形面积计算属性测试"""
    
    @given(rect=rectangle_strategy())
    @settings(max_examples=100)
    def test_rectangle_area_formula(self, rect: list[Point]) -> None:
        """矩形面积应等于宽 × 高"""
        width = rect[1].x - rect[0].x
        height = rect[2].y - rect[1].y
        expected_area = width * height
        
        actual_area = polygon_area(rect)
        
        assert abs(actual_area - expected_area) < 1e-6, (
            f"Expected area {expected_area}, got {actual_area}"
        )
    
    @given(rect=rectangle_strategy())
    @settings(max_examples=100)
    def test_area_is_non_negative(self, rect: list[Point]) -> None:
        """面积应为非负数"""
        area = polygon_area(rect)
        assert area >= 0
    
    @given(rect=rectangle_strategy())
    @settings(max_examples=100)
    def test_reversed_polygon_same_area(self, rect: list[Point]) -> None:
        """顺时针和逆时针多边形面积相同"""
        area1 = polygon_area(rect)
        area2 = polygon_area(list(reversed(rect)))
        assert abs(area1 - area2) < 1e-6


class TestPointInPolygonProperty:
    """点在多边形内判断属性测试"""
    
    @given(rect=rectangle_strategy())
    @settings(max_examples=100)
    def test_center_is_inside(self, rect: list[Point]) -> None:
        """矩形中心点应在矩形内"""
        center_x = (rect[0].x + rect[2].x) / 2
        center_y = (rect[0].y + rect[2].y) / 2
        
        assert point_in_polygon((center_x, center_y), rect)
    
    @given(rect=rectangle_strategy())
    @settings(max_examples=100)
    def test_far_point_is_outside(self, rect: list[Point]) -> None:
        """远离矩形的点应在矩形外"""
        max_x = max(p.x for p in rect)
        max_y = max(p.y for p in rect)
        
        # 远离矩形的点
        far_point = (max_x + 1000, max_y + 1000)
        
        assert not point_in_polygon(far_point, rect)
    
    @given(rect=rectangle_strategy())
    @settings(max_examples=100)
    def test_vertex_is_on_boundary(self, rect: list[Point]) -> None:
        """顶点应被视为在多边形内（边界上）"""
        for vertex in rect:
            assert point_in_polygon((vertex.x, vertex.y), rect)


class TestDensityCalculationProperty:
    """密度计算属性测试
    
    Feature: crowd-counting-system, Property 3: 密度计算与等级分类
    **Validates: Requirements 3.3, 3.4**
    """
    
    @given(
        count=st.integers(min_value=0, max_value=100),
        area=st.floats(min_value=100.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_density_is_normalized(self, count: int, area: float) -> None:
        """密度值应在 0-1 范围内"""
        density = calculate_density(count, area)
        assert 0.0 <= density <= 1.0
    
    @given(area=st.floats(min_value=100.0, max_value=100000.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_zero_count_zero_density(self, area: float) -> None:
        """人数为 0 时密度为 0"""
        density = calculate_density(0, area)
        assert density == 0.0
    
    @given(
        count=st.integers(min_value=1, max_value=100),
        area1=st.floats(min_value=1000.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_larger_area_lower_density(self, count: int, area1: float) -> None:
        """相同人数，面积越大密度越低"""
        area2 = area1 * 2
        
        density1 = calculate_density(count, area1)
        density2 = calculate_density(count, area2)
        
        assert density1 >= density2


class TestDensityLevelClassificationProperty:
    """密度等级分类属性测试
    
    Feature: crowd-counting-system, Property 3: 密度计算与等级分类
    **Validates: Requirements 3.3, 3.4**
    """
    
    @given(thresholds=thresholds_strategy())
    @settings(max_examples=100)
    def test_low_density_classification(self, thresholds: DensityThresholds) -> None:
        """低于 low 阈值应分类为 LOW"""
        density = thresholds.low - 0.01
        assume(density >= 0)
        
        level = classify_density_level(density, thresholds)
        assert level == DensityLevel.LOW
    
    @given(thresholds=thresholds_strategy())
    @settings(max_examples=100)
    def test_medium_density_classification(self, thresholds: DensityThresholds) -> None:
        """在 low 和 medium 之间应分类为 MEDIUM"""
        density = (thresholds.low + thresholds.medium) / 2
        
        level = classify_density_level(density, thresholds)
        assert level == DensityLevel.MEDIUM
    
    @given(thresholds=thresholds_strategy())
    @settings(max_examples=100)
    def test_high_density_classification(self, thresholds: DensityThresholds) -> None:
        """高于 medium 阈值应分类为 HIGH"""
        density = thresholds.medium + 0.01
        assume(density <= 1.0)
        
        level = classify_density_level(density, thresholds)
        assert level == DensityLevel.HIGH
    
    @given(
        density=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        thresholds=thresholds_strategy(),
    )
    @settings(max_examples=100)
    def test_classification_is_exhaustive(
        self, density: float, thresholds: DensityThresholds
    ) -> None:
        """任何密度值都应被分类到某个等级"""
        level = classify_density_level(density, thresholds)
        assert level in [DensityLevel.LOW, DensityLevel.MEDIUM, DensityLevel.HIGH]


class TestRegionStatCalculationProperty:
    """区域统计计算属性测试"""
    
    @given(
        rect=rectangle_strategy(),
        detections=st.lists(detection_strategy(), min_size=0, max_size=50),
        thresholds=thresholds_strategy(),
    )
    @settings(max_examples=100)
    def test_count_matches_detections_in_region(
        self,
        rect: list[Point],
        detections: list[Detection],
        thresholds: DensityThresholds,
    ) -> None:
        """统计的人数应等于区域内的检测数量"""
        stat = ROICalculator.calculate_region_stat(
            region_id="test",
            region_name="Test Region",
            polygon=rect,
            thresholds=thresholds,
            detections=detections,
        )
        
        # 手动计算区域内检测数
        expected_count = sum(
            1 for d in detections
            if point_in_polygon(d.center, rect)
        )
        
        assert stat.count == expected_count
    
    @given(
        rect=rectangle_strategy(),
        detections=st.lists(detection_strategy(), min_size=0, max_size=50),
        thresholds=thresholds_strategy(),
    )
    @settings(max_examples=100)
    def test_density_is_consistent_with_count_and_area(
        self,
        rect: list[Point],
        detections: list[Detection],
        thresholds: DensityThresholds,
    ) -> None:
        """密度值应与人数和面积一致"""
        stat = ROICalculator.calculate_region_stat(
            region_id="test",
            region_name="Test Region",
            polygon=rect,
            thresholds=thresholds,
            detections=detections,
        )
        
        area = polygon_area(rect)
        expected_density = calculate_density(stat.count, area)
        
        assert abs(stat.density - expected_density) < 1e-4


class TestEdgeCases:
    """边界情况测试"""
    
    def test_triangle_area(self) -> None:
        """三角形面积计算"""
        triangle = [
            Point(x=0, y=0),
            Point(x=10, y=0),
            Point(x=5, y=10),
        ]
        area = polygon_area(triangle)
        # 三角形面积 = 底 × 高 / 2 = 10 × 10 / 2 = 50
        assert abs(area - 50.0) < 1e-6
    
    def test_point_exactly_on_edge(self) -> None:
        """点恰好在边上"""
        rect = [
            Point(x=0, y=0),
            Point(x=10, y=0),
            Point(x=10, y=10),
            Point(x=0, y=10),
        ]
        # 边上的点
        edge_point = (5, 0)
        assert point_in_polygon(edge_point, rect)
    
    def test_zero_area_returns_zero_density(self) -> None:
        """面积为 0 时密度为 0"""
        density = calculate_density(10, 0)
        assert density == 0.0
    
    def test_negative_area_returns_zero_density(self) -> None:
        """负面积时密度为 0"""
        density = calculate_density(10, -100)
        assert density == 0.0
    
    def test_boundary_threshold_values(self) -> None:
        """阈值边界值测试"""
        thresholds = DensityThresholds(low=0.3, medium=0.6, high=0.8)
        
        # 恰好等于 low 阈值
        assert classify_density_level(0.3, thresholds) == DensityLevel.MEDIUM
        
        # 恰好等于 medium 阈值
        assert classify_density_level(0.6, thresholds) == DensityLevel.HIGH
