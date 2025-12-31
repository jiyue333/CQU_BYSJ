"""推理服务属性测试

Property 2: 置信度过滤
*For any* 检测结果集合和置信度阈值，返回的所有检测结果的置信度都应 >= 阈值
**Validates: Requirements 2.4, 8.1**
"""

import pytest
from hypothesis import given, settings, strategies as st

from app.schemas.detection import Detection
from app.services.inference_service import filter_by_confidence


# 生成有效的 Detection 对象
@st.composite
def detection_strategy(draw: st.DrawFn) -> Detection:
    """生成随机的 Detection 对象"""
    return Detection(
        x=draw(st.integers(min_value=0, max_value=1920)),
        y=draw(st.integers(min_value=0, max_value=1080)),
        width=draw(st.integers(min_value=1, max_value=500)),
        height=draw(st.integers(min_value=1, max_value=500)),
        confidence=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
    )


# 生成检测结果列表
detections_strategy = st.lists(detection_strategy(), min_size=0, max_size=100)

# 生成置信度阈值
threshold_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)


class TestConfidenceFilterProperty:
    """置信度过滤属性测试
    
    Feature: crowd-counting-system, Property 2: 置信度过滤
    **Validates: Requirements 2.4, 8.1**
    """
    
    @given(detections=detections_strategy, threshold=threshold_strategy)
    @settings(max_examples=100)
    def test_all_filtered_detections_meet_threshold(
        self,
        detections: list[Detection],
        threshold: float,
    ) -> None:
        """Property 2: 所有过滤后的检测结果置信度都 >= 阈值
        
        *For any* 检测结果集合和置信度阈值，
        返回的所有检测结果的置信度都应 >= 阈值
        """
        # Act
        filtered = filter_by_confidence(detections, threshold)
        
        # Assert: 所有结果的置信度都 >= 阈值
        for detection in filtered:
            assert detection.confidence >= threshold, (
                f"Detection confidence {detection.confidence} < threshold {threshold}"
            )
    
    @given(detections=detections_strategy, threshold=threshold_strategy)
    @settings(max_examples=100)
    def test_filtered_count_is_subset(
        self,
        detections: list[Detection],
        threshold: float,
    ) -> None:
        """过滤后的结果数量 <= 原始数量"""
        filtered = filter_by_confidence(detections, threshold)
        assert len(filtered) <= len(detections)
    
    @given(detections=detections_strategy, threshold=threshold_strategy)
    @settings(max_examples=100)
    def test_no_valid_detections_lost(
        self,
        detections: list[Detection],
        threshold: float,
    ) -> None:
        """所有满足阈值的检测结果都应被保留"""
        filtered = filter_by_confidence(detections, threshold)
        
        # 计算原始列表中满足阈值的数量
        expected_count = sum(1 for d in detections if d.confidence >= threshold)
        
        assert len(filtered) == expected_count, (
            f"Expected {expected_count} detections, got {len(filtered)}"
        )
    
    @given(detections=detections_strategy)
    @settings(max_examples=100)
    def test_threshold_zero_keeps_all(
        self,
        detections: list[Detection],
    ) -> None:
        """阈值为 0 时保留所有检测结果"""
        filtered = filter_by_confidence(detections, 0.0)
        assert len(filtered) == len(detections)
    
    @given(detections=detections_strategy)
    @settings(max_examples=100)
    def test_threshold_one_keeps_only_perfect(
        self,
        detections: list[Detection],
    ) -> None:
        """阈值为 1.0 时只保留置信度为 1.0 的结果"""
        filtered = filter_by_confidence(detections, 1.0)
        
        expected_count = sum(1 for d in detections if d.confidence >= 1.0)
        assert len(filtered) == expected_count
        
        for detection in filtered:
            assert detection.confidence >= 1.0


class TestConfidenceFilterEdgeCases:
    """置信度过滤边界情况测试"""
    
    def test_empty_detections(self) -> None:
        """空列表返回空列表"""
        result = filter_by_confidence([], 0.5)
        assert result == []
    
    def test_all_below_threshold(self) -> None:
        """所有检测结果都低于阈值时返回空列表"""
        detections = [
            Detection(x=0, y=0, width=100, height=100, confidence=0.3),
            Detection(x=10, y=10, width=100, height=100, confidence=0.4),
        ]
        result = filter_by_confidence(detections, 0.5)
        assert result == []
    
    def test_all_above_threshold(self) -> None:
        """所有检测结果都高于阈值时全部保留"""
        detections = [
            Detection(x=0, y=0, width=100, height=100, confidence=0.7),
            Detection(x=10, y=10, width=100, height=100, confidence=0.8),
        ]
        result = filter_by_confidence(detections, 0.5)
        assert len(result) == 2
    
    def test_exact_threshold_included(self) -> None:
        """置信度恰好等于阈值时应被保留"""
        detections = [
            Detection(x=0, y=0, width=100, height=100, confidence=0.5),
        ]
        result = filter_by_confidence(detections, 0.5)
        assert len(result) == 1
        assert result[0].confidence == 0.5
    
    def test_preserves_detection_data(self) -> None:
        """过滤后的检测结果数据完整保留"""
        original = Detection(x=100, y=200, width=50, height=60, confidence=0.9)
        result = filter_by_confidence([original], 0.5)
        
        assert len(result) == 1
        assert result[0].x == 100
        assert result[0].y == 200
        assert result[0].width == 50
        assert result[0].height == 60
        assert result[0].confidence == 0.9
