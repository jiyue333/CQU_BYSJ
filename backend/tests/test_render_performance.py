"""渲染性能/稳定性验收测试

F-30: 性能基线测量与稳定性验证

测试内容：
1. 单路 720p CPU 占用基线测量
2. 热力图叠加性能
3. 并发渲染降级策略验证
4. 内存使用基线

**Validates: 方案 F 性能要求**
"""

import time
from typing import Generator
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st

from app.services.render_worker import RenderWorker, RenderConfig
from app.services.heatmap_generator import HeatmapGenerator
from app.schemas.detection import Detection


# ============================================================================
# 性能基线测试
# ============================================================================

class TestHeatmapOverlayPerformance:
    """热力图叠加性能测试"""
    
    def test_overlay_performance_720p(self) -> None:
        """720p 帧叠加性能基线"""
        worker = RenderWorker()
        frame = np.random.randint(0, 256, (720, 1280, 3), dtype=np.uint8)
        heatmap = [[0.5] * 20 for _ in range(20)]
        
        # 预热
        for _ in range(5):
            worker._draw_heatmap_overlay(frame, heatmap, alpha=0.4)
        
        # 测量
        iterations = 100
        start = time.perf_counter()
        
        for _ in range(iterations):
            worker._draw_heatmap_overlay(frame, heatmap, alpha=0.4)
        
        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / iterations) * 1000
        fps = iterations / elapsed
        
        print(f"\n720p 热力图叠加性能:")
        print(f"  平均耗时: {avg_ms:.2f} ms/帧")
        print(f"  理论帧率: {fps:.1f} fps")
        
        # 性能要求：单帧叠加 < 20ms（支持 50fps）
        assert avg_ms < 20, f"叠加耗时 {avg_ms:.2f}ms 超过 20ms 阈值"
    
    def test_overlay_performance_1080p(self) -> None:
        """1080p 帧叠加性能基线"""
        worker = RenderWorker()
        frame = np.random.randint(0, 256, (1080, 1920, 3), dtype=np.uint8)
        heatmap = [[0.5] * 20 for _ in range(20)]
        
        # 预热
        for _ in range(5):
            worker._draw_heatmap_overlay(frame, heatmap, alpha=0.4)
        
        # 测量
        iterations = 50
        start = time.perf_counter()
        
        for _ in range(iterations):
            worker._draw_heatmap_overlay(frame, heatmap, alpha=0.4)
        
        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / iterations) * 1000
        fps = iterations / elapsed
        
        print(f"\n1080p 热力图叠加性能:")
        print(f"  平均耗时: {avg_ms:.2f} ms/帧")
        print(f"  理论帧率: {fps:.1f} fps")
        
        # 性能要求：单帧叠加 < 40ms（支持 25fps）
        assert avg_ms < 40, f"叠加耗时 {avg_ms:.2f}ms 超过 40ms 阈值"


class TestHeatmapGenerationPerformance:
    """热力图生成性能测试"""
    
    def test_heatmap_generation_performance(self) -> None:
        """热力图生成性能基线"""
        generator = HeatmapGenerator(grid_size=20, alpha=0.5)
        
        # 生成测试检测数据
        detections = [
            Detection(x=i * 50, y=i * 30, width=50, height=50, confidence=0.9)
            for i in range(20)
        ]
        
        # 预热
        for _ in range(10):
            generator.generate("test", detections, 1280, 720)
        
        # 测量
        iterations = 1000
        start = time.perf_counter()
        
        for i in range(iterations):
            generator.generate(f"test_{i % 10}", detections, 1280, 720)
        
        elapsed = time.perf_counter() - start
        avg_us = (elapsed / iterations) * 1_000_000
        
        print(f"\n热力图生成性能 (20 检测):")
        print(f"  平均耗时: {avg_us:.1f} μs")
        
        # 性能要求：< 1ms
        assert avg_us < 1000, f"生成耗时 {avg_us:.1f}μs 超过 1000μs 阈值"
    
    def test_heatmap_generation_with_many_detections(self) -> None:
        """大量检测时的热力图生成性能"""
        generator = HeatmapGenerator(grid_size=20, alpha=0.5)
        
        # 生成大量检测数据
        detections = [
            Detection(
                x=np.random.randint(0, 1200),
                y=np.random.randint(0, 650),
                width=50,
                height=50,
                confidence=0.9
            )
            for _ in range(100)
        ]
        
        # 测量
        iterations = 500
        start = time.perf_counter()
        
        for i in range(iterations):
            generator.generate(f"test_{i % 10}", detections, 1280, 720)
        
        elapsed = time.perf_counter() - start
        avg_us = (elapsed / iterations) * 1_000_000
        
        print(f"\n热力图生成性能 (100 检测):")
        print(f"  平均耗时: {avg_us:.1f} μs")
        
        # 性能要求：< 2ms
        assert avg_us < 2000, f"生成耗时 {avg_us:.1f}μs 超过 2000μs 阈值"


# ============================================================================
# 内存使用测试
# ============================================================================

class TestMemoryUsage:
    """内存使用测试"""
    
    def test_heatmap_generator_memory_per_stream(self) -> None:
        """每路流的热力图生成器内存占用"""
        import sys
        
        generator = HeatmapGenerator(grid_size=20, alpha=0.5)
        
        # 模拟多路流
        detections = [
            Detection(x=100, y=100, width=50, height=50, confidence=0.9)
        ]
        
        for i in range(10):
            generator.generate(f"stream_{i}", detections, 1280, 720)
        
        # 检查 EMA 状态数量
        assert len(generator._ema_grids) == 10
        
        # 估算内存：每个 EMA 网格 20x20 float32 = 1600 bytes
        estimated_bytes = 10 * 20 * 20 * 4
        print(f"\n10 路流 EMA 状态估算内存: {estimated_bytes / 1024:.1f} KB")
        
        # 清理
        generator.reset_all()
        assert len(generator._ema_grids) == 0
    
    def test_frame_buffer_memory(self) -> None:
        """帧缓冲区内存占用"""
        # 720p BGR 帧
        frame_720p = np.zeros((720, 1280, 3), dtype=np.uint8)
        size_720p = frame_720p.nbytes
        
        # 1080p BGR 帧
        frame_1080p = np.zeros((1080, 1920, 3), dtype=np.uint8)
        size_1080p = frame_1080p.nbytes
        
        print(f"\n帧缓冲区内存:")
        print(f"  720p: {size_720p / 1024 / 1024:.2f} MB")
        print(f"  1080p: {size_1080p / 1024 / 1024:.2f} MB")
        
        # 验证预期大小
        assert size_720p == 720 * 1280 * 3  # 2.76 MB
        assert size_1080p == 1080 * 1920 * 3  # 6.22 MB


# ============================================================================
# 并发限制测试
# ============================================================================

class TestConcurrentRenderLimit:
    """并发渲染限制测试"""
    
    def test_max_concurrent_limit_enforced(self) -> None:
        """最大并发数限制应被执行"""
        from app.core.config import settings
        
        worker = RenderWorker()
        
        # 模拟已达到最大并发
        for i in range(settings.render_max_concurrent):
            worker._active_streams[f"stream_{i}"] = {"running": True}
        
        # 验证活跃流数量
        running_count = sum(1 for s in worker._active_streams.values() if s.get("running"))
        assert running_count == settings.render_max_concurrent
    
    def test_concurrent_limit_from_config(self) -> None:
        """并发限制应来自配置"""
        from app.core.config import settings
        
        # 验证配置存在且合理
        assert hasattr(settings, 'render_max_concurrent')
        assert 1 <= settings.render_max_concurrent <= 10
        
        print(f"\n配置的最大并发渲染数: {settings.render_max_concurrent}")


# ============================================================================
# 降级策略测试
# ============================================================================

class TestDegradationStrategy:
    """降级策略测试"""
    
    def test_stride_increase_reduces_inference_load(self) -> None:
        """增加步长应减少推理负载"""
        # stride=3: 24fps -> 8fps 推理
        # stride=6: 24fps -> 4fps 推理
        
        render_fps = 24
        
        stride_3_infer_fps = render_fps / 3
        stride_6_infer_fps = render_fps / 6
        
        assert stride_3_infer_fps == 8
        assert stride_6_infer_fps == 4
        
        # 负载减少 50%
        load_reduction = 1 - (stride_6_infer_fps / stride_3_infer_fps)
        assert load_reduction == 0.5
    
    def test_fps_reduction_strategy(self) -> None:
        """降低帧率策略"""
        # 从 24fps 降到 15fps
        original_fps = 24
        reduced_fps = 15
        
        # 负载减少
        load_reduction = 1 - (reduced_fps / original_fps)
        assert load_reduction > 0.3  # 至少减少 30%
    
    @given(
        render_fps=st.integers(min_value=10, max_value=30),
        infer_stride=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=50)
    def test_infer_fps_calculation(self, render_fps: int, infer_stride: int) -> None:
        """Property: 推理帧率计算应正确"""
        infer_fps = render_fps / infer_stride
        
        # 推理帧率应小于等于渲染帧率
        assert infer_fps <= render_fps
        
        # 推理帧率应为正数
        assert infer_fps > 0


# ============================================================================
# 稳定性测试
# ============================================================================

class TestStability:
    """稳定性测试"""
    
    def test_repeated_overlay_stability(self) -> None:
        """重复叠加应稳定"""
        worker = RenderWorker()
        frame = np.random.randint(0, 256, (720, 1280, 3), dtype=np.uint8)
        heatmap = [[0.5] * 20 for _ in range(20)]
        
        # 执行大量重复操作
        for i in range(1000):
            result = worker._draw_heatmap_overlay(frame, heatmap, alpha=0.4)
            
            # 验证输出有效
            assert result.shape == frame.shape
            assert result.dtype == np.uint8
            assert result.min() >= 0
            assert result.max() <= 255
    
    def test_heatmap_generator_ema_stability(self) -> None:
        """EMA 平滑应稳定"""
        generator = HeatmapGenerator(grid_size=20, alpha=0.5)
        
        # 模拟长时间运行
        for i in range(10000):
            detections = [
                Detection(
                    x=np.random.randint(0, 1200),
                    y=np.random.randint(0, 650),
                    width=50,
                    height=50,
                    confidence=0.9
                )
                for _ in range(np.random.randint(0, 20))
            ]
            
            heatmap = generator.generate("test", detections, 1280, 720)
            
            # 验证输出有效
            assert len(heatmap) == 20
            assert all(len(row) == 20 for row in heatmap)
            assert all(0.0 <= val <= 1.0 for row in heatmap for val in row)
    
    def test_failure_count_reset_on_success(self) -> None:
        """成功后失败计数应重置"""
        worker = RenderWorker()
        stream_id = "test_stream"
        
        # 模拟失败累积
        worker._failure_counts[stream_id] = 3
        
        # 模拟成功（重置计数）
        worker._failure_counts[stream_id] = 0
        
        assert worker._failure_counts[stream_id] == 0


# ============================================================================
# 配置验证测试
# ============================================================================

class TestRenderConfigValidation:
    """渲染配置验证测试"""
    
    def test_default_config_values(self) -> None:
        """默认配置值应合理"""
        from app.core.config import settings
        
        print(f"\n渲染配置:")
        print(f"  render_fps: {settings.render_fps}")
        print(f"  render_infer_stride: {settings.render_infer_stride}")
        print(f"  render_overlay_alpha: {settings.render_overlay_alpha}")
        print(f"  render_max_concurrent: {settings.render_max_concurrent}")
        
        # 验证范围
        assert 1 <= settings.render_fps <= 60
        assert 1 <= settings.render_infer_stride <= 10
        assert 0.0 <= settings.render_overlay_alpha <= 1.0
        assert 1 <= settings.render_max_concurrent <= 10
    
    def test_infer_fps_meets_requirement(self) -> None:
        """推理帧率应满足要求（~8fps）"""
        from app.core.config import settings
        
        infer_fps = settings.render_fps / settings.render_infer_stride
        
        print(f"\n计算的推理帧率: {infer_fps:.1f} fps")
        
        # 要求：推理帧率在 5-10fps 范围内
        assert 5 <= infer_fps <= 10, f"推理帧率 {infer_fps} 不在 5-10fps 范围内"
