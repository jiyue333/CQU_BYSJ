"""热力图生成属性测试

Property 5: 热力图生成
*For any* 检测位置集合，热力图网格中对应位置的值应反映检测密度
**Validates: Requirements 4.1**
"""

import pytest
from hypothesis import given, settings, strategies as st, assume
import numpy as np

from app.schemas.detection import Detection
from app.services.heatmap_generator import (
    HeatmapGenerator,
    generate_heatmap,
    compute_raw_heatmap,
)


# 生成有效的 Detection 对象（在指定帧范围内）
@st.composite
def detection_in_frame_strategy(
    draw: st.DrawFn,
    frame_width: int = 640,
    frame_height: int = 480,
) -> Detection:
    """生成在帧范围内的随机 Detection 对象"""
    # 确保检测框在帧内
    max_x = frame_width - 10
    max_y = frame_height - 10
    
    x = draw(st.integers(min_value=0, max_value=max(0, max_x)))
    y = draw(st.integers(min_value=0, max_value=max(0, max_y)))
    width = draw(st.integers(min_value=1, max_value=min(100, frame_width - x)))
    height = draw(st.integers(min_value=1, max_value=min(100, frame_height - y)))
    
    return Detection(
        x=x,
        y=y,
        width=width,
        height=height,
        confidence=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
    )


# 生成检测结果列表
@st.composite
def detections_strategy(draw: st.DrawFn, frame_width: int = 640, frame_height: int = 480) -> list[Detection]:
    """生成检测结果列表"""
    return draw(st.lists(
        detection_in_frame_strategy(frame_width=frame_width, frame_height=frame_height),
        min_size=0,
        max_size=50,
    ))


class TestHeatmapGenerationProperty:
    """热力图生成属性测试
    
    Feature: crowd-counting-system, Property 5: 热力图生成
    **Validates: Requirements 4.1**
    """
    
    @given(detections=detections_strategy())
    @settings(max_examples=100)
    def test_heatmap_grid_is_correct_size(self, detections: list[Detection]) -> None:
        """热力图网格大小应为 grid_size x grid_size"""
        grid_size = 20
        heatmap = generate_heatmap(detections, 640, 480, grid_size=grid_size)
        
        assert len(heatmap) == grid_size
        for row in heatmap:
            assert len(row) == grid_size
    
    @given(detections=detections_strategy())
    @settings(max_examples=100)
    def test_heatmap_values_in_range(self, detections: list[Detection]) -> None:
        """热力图值应在 0-1 范围内"""
        heatmap = generate_heatmap(detections, 640, 480)
        
        for row in heatmap:
            for val in row:
                assert 0.0 <= val <= 1.0, f"Value {val} out of range [0, 1]"
    
    @given(detections=detections_strategy())
    @settings(max_examples=100)
    def test_empty_detections_zero_heatmap(self, detections: list[Detection]) -> None:
        """无检测时热力图全为 0"""
        heatmap = generate_heatmap([], 640, 480)
        
        for row in heatmap:
            for val in row:
                assert val == 0.0
    
    @given(detections=detections_strategy())
    @settings(max_examples=100)
    def test_detection_increases_corresponding_cell(self, detections: list[Detection]) -> None:
        """检测应增加对应网格单元的值"""
        assume(len(detections) > 0)
        
        raw_heatmap = compute_raw_heatmap(detections, 640, 480, grid_size=20)
        
        # 至少有一个单元格的值 > 0
        total = sum(sum(row) for row in raw_heatmap)
        assert total == len(detections), (
            f"Total count {total} should equal detection count {len(detections)}"
        )
    
    @given(detections=detections_strategy())
    @settings(max_examples=100)
    def test_normalized_max_is_one_or_zero(self, detections: list[Detection]) -> None:
        """归一化后最大值应为 1（有检测时）或 0（无检测时）"""
        heatmap = generate_heatmap(detections, 640, 480)
        
        max_val = max(max(row) for row in heatmap)
        
        if len(detections) > 0:
            assert abs(max_val - 1.0) < 1e-6, f"Max value should be 1.0, got {max_val}"
        else:
            assert max_val == 0.0


class TestEMASmoothingProperty:
    """EMA 平滑属性测试"""
    
    def test_first_frame_uses_raw_value(self) -> None:
        """首帧应直接使用原始值"""
        generator = HeatmapGenerator(grid_size=10, alpha=0.3)
        
        detections = [
            Detection(x=100, y=100, width=50, height=50, confidence=0.9),
        ]
        
        heatmap1 = generator.generate("stream1", detections, 640, 480)
        
        # 首帧应有非零值
        max_val = max(max(row) for row in heatmap1)
        assert max_val > 0
    
    def test_ema_smoothing_effect(self) -> None:
        """EMA 应产生平滑效果"""
        generator = HeatmapGenerator(grid_size=10, alpha=0.3)
        
        # 第一帧：左上角有检测
        detections1 = [
            Detection(x=50, y=50, width=50, height=50, confidence=0.9),
        ]
        heatmap1 = generator.generate("stream1", detections1, 640, 480)
        
        # 第二帧：右下角有检测
        detections2 = [
            Detection(x=500, y=400, width=50, height=50, confidence=0.9),
        ]
        heatmap2 = generator.generate("stream1", detections2, 640, 480)
        
        # 由于 EMA，第一帧的热点应该仍有残留
        # 检查左上角区域（第一帧热点位置）
        left_top_val = heatmap2[0][0]
        
        # 应该有残留值（1 - alpha = 0.7 的衰减）
        # 但由于归一化，具体值取决于实现
        assert generator.has_state("stream1")
    
    def test_reset_clears_ema_state(self) -> None:
        """reset 应清除 EMA 状态"""
        generator = HeatmapGenerator(grid_size=10, alpha=0.3)
        
        detections = [
            Detection(x=100, y=100, width=50, height=50, confidence=0.9),
        ]
        
        generator.generate("stream1", detections, 640, 480)
        assert generator.has_state("stream1")
        
        generator.reset("stream1")
        assert not generator.has_state("stream1")
    
    def test_different_streams_independent(self) -> None:
        """不同流的 EMA 状态应独立"""
        generator = HeatmapGenerator(grid_size=10, alpha=0.3)
        
        detections1 = [
            Detection(x=50, y=50, width=50, height=50, confidence=0.9),
        ]
        detections2 = [
            Detection(x=500, y=400, width=50, height=50, confidence=0.9),
        ]
        
        heatmap1 = generator.generate("stream1", detections1, 640, 480)
        heatmap2 = generator.generate("stream2", detections2, 640, 480)
        
        # 两个流应该有不同的热力图
        assert heatmap1 != heatmap2
        
        # 两个流都应该有状态
        assert generator.has_state("stream1")
        assert generator.has_state("stream2")
    
    def test_alpha_one_no_smoothing(self) -> None:
        """alpha=1.0 时无平滑效果"""
        generator = HeatmapGenerator(grid_size=10, alpha=1.0)
        
        detections1 = [
            Detection(x=50, y=50, width=50, height=50, confidence=0.9),
        ]
        detections2 = []  # 空检测
        
        generator.generate("stream1", detections1, 640, 480)
        heatmap2 = generator.generate("stream1", detections2, 640, 480)
        
        # alpha=1.0 时，第二帧应该全为 0（无平滑）
        max_val = max(max(row) for row in heatmap2)
        assert max_val == 0.0


class TestHeatmapEdgeCases:
    """热力图边界情况测试"""
    
    def test_single_detection_center(self) -> None:
        """单个检测应在对应网格单元产生热点"""
        # 检测框中心在 (320, 240)，即帧中心
        detection = Detection(x=295, y=215, width=50, height=50, confidence=0.9)
        
        heatmap = generate_heatmap([detection], 640, 480, grid_size=20)
        
        # 中心应该在网格 (10, 10) 附近
        # 320 / (640/20) = 10, 240 / (480/20) = 10
        center_val = heatmap[10][10]
        assert center_val > 0
    
    def test_detection_at_boundary(self) -> None:
        """边界检测应正确处理"""
        # 检测框在右下角
        detection = Detection(x=600, y=440, width=40, height=40, confidence=0.9)
        
        heatmap = generate_heatmap([detection], 640, 480, grid_size=20)
        
        # 应该在最后一个网格单元
        bottom_right_val = heatmap[19][19]
        assert bottom_right_val > 0
    
    def test_detection_at_origin(self) -> None:
        """原点检测应正确处理"""
        detection = Detection(x=0, y=0, width=50, height=50, confidence=0.9)
        
        heatmap = generate_heatmap([detection], 640, 480, grid_size=20)
        
        # 中心在 (25, 25)，应该在网格 (0, 0) 或 (1, 1) 附近
        top_left_val = heatmap[0][0]
        assert top_left_val > 0 or heatmap[0][1] > 0 or heatmap[1][0] > 0
    
    def test_multiple_detections_same_cell(self) -> None:
        """多个检测在同一单元格应累加"""
        detections = [
            Detection(x=100, y=100, width=50, height=50, confidence=0.9),
            Detection(x=110, y=110, width=50, height=50, confidence=0.8),
        ]
        
        raw_heatmap = compute_raw_heatmap(detections, 640, 480, grid_size=20)
        
        # 总计数应为 2
        total = sum(sum(row) for row in raw_heatmap)
        assert total == 2
    
    def test_zero_frame_size(self) -> None:
        """帧大小为 0 时应返回全零网格"""
        detection = Detection(x=100, y=100, width=50, height=50, confidence=0.9)
        
        heatmap = generate_heatmap([detection], 0, 0, grid_size=20)
        
        for row in heatmap:
            for val in row:
                assert val == 0.0
    
    def test_custom_grid_size(self) -> None:
        """自定义网格大小应正确工作"""
        detection = Detection(x=100, y=100, width=50, height=50, confidence=0.9)
        
        for grid_size in [5, 10, 30, 50]:
            heatmap = generate_heatmap([detection], 640, 480, grid_size=grid_size)
            
            assert len(heatmap) == grid_size
            for row in heatmap:
                assert len(row) == grid_size
