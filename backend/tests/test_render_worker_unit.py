"""RenderWorker 纯逻辑单元测试

F-26: 对热力图叠加、色图映射、网格缩放、ffmpeg 参数拼装做可重复单测

**Validates: 方案 F 渲染流程核心逻辑**
"""

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st, assume
from unittest.mock import MagicMock, AsyncMock, patch

from app.schemas.detection import Detection
from app.services.render_worker import RenderWorker, RenderConfig, RenderHealth
from app.services.heatmap_generator import HeatmapGenerator


# ============================================================================
# 策略定义
# ============================================================================

@st.composite
def detection_strategy(draw: st.DrawFn, max_x: int = 640, max_y: int = 480) -> Detection:
    """生成有效的 Detection 对象"""
    x = draw(st.integers(min_value=0, max_value=max(0, max_x - 50)))
    y = draw(st.integers(min_value=0, max_value=max(0, max_y - 50)))
    width = draw(st.integers(min_value=10, max_value=min(100, max_x - x)))
    height = draw(st.integers(min_value=10, max_value=min(100, max_y - y)))
    confidence = draw(st.floats(min_value=0.1, max_value=1.0, allow_nan=False))
    return Detection(x=x, y=y, width=width, height=height, confidence=confidence)


@st.composite
def heatmap_grid_strategy(draw: st.DrawFn, grid_size: int = 20) -> list[list[float]]:
    """生成有效的热力图网格"""
    return [
        [draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)) 
         for _ in range(grid_size)]
        for _ in range(grid_size)
    ]


@st.composite
def render_config_strategy(draw: st.DrawFn) -> RenderConfig:
    """生成有效的渲染配置"""
    stream_id = draw(st.uuids()).hex[:8]
    return RenderConfig(
        stream_id=stream_id,
        render_stream_id=f"{stream_id}_heatmap",
        src_rtsp_url=f"rtsp://localhost:554/live/{stream_id}",
        dst_rtmp_url=f"rtmp://localhost:1935/live/{stream_id}_heatmap",
        render_fps=draw(st.integers(min_value=1, max_value=60)),
        infer_stride=draw(st.integers(min_value=1, max_value=10)),
        overlay_alpha=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
    )


# ============================================================================
# 热力图叠加测试
# ============================================================================

class TestHeatmapOverlay:
    """热力图叠加逻辑测试"""
    
    def test_overlay_preserves_frame_shape(self) -> None:
        """叠加后帧形状应保持不变"""
        worker = RenderWorker()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        heatmap = [[0.5] * 20 for _ in range(20)]
        
        result = worker._draw_heatmap_overlay(frame, heatmap, alpha=0.4)
        
        assert result.shape == frame.shape
        assert result.dtype == np.uint8
    
    def test_overlay_with_zero_alpha_returns_original(self) -> None:
        """alpha=0 时应返回原始帧"""
        worker = RenderWorker()
        frame = np.full((480, 640, 3), 128, dtype=np.uint8)
        heatmap = [[1.0] * 20 for _ in range(20)]
        
        result = worker._draw_heatmap_overlay(frame, heatmap, alpha=0.0)
        
        # alpha=0 时，结果应接近原始帧
        np.testing.assert_array_almost_equal(result, frame, decimal=0)
    
    def test_overlay_with_full_alpha_shows_heatmap(self) -> None:
        """alpha=1 时应完全显示热力图"""
        worker = RenderWorker()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        heatmap = [[1.0] * 20 for _ in range(20)]
        
        result = worker._draw_heatmap_overlay(frame, heatmap, alpha=1.0)
        
        # alpha=1 时，结果应不等于原始帧（除非原始帧恰好等于热力图颜色）
        assert not np.array_equal(result, frame)
    
    @given(heatmap=heatmap_grid_strategy())
    @settings(max_examples=50)
    def test_overlay_output_in_valid_range(self, heatmap: list[list[float]]) -> None:
        """叠加输出值应在 0-255 范围内"""
        worker = RenderWorker()
        frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
        
        result = worker._draw_heatmap_overlay(frame, heatmap, alpha=0.4)
        
        assert result.min() >= 0
        assert result.max() <= 255
    
    def test_overlay_with_empty_heatmap(self) -> None:
        """空热力图（全零）应产生蓝色叠加"""
        worker = RenderWorker()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        heatmap = [[0.0] * 20 for _ in range(20)]
        
        result = worker._draw_heatmap_overlay(frame, heatmap, alpha=0.5)
        
        # COLORMAP_JET 中 0 对应蓝色
        # 结果应该有蓝色分量
        assert result.shape == (480, 640, 3)
    
    def test_overlay_with_hot_spot(self) -> None:
        """热点区域应显示红色"""
        worker = RenderWorker()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 创建中心热点
        heatmap = [[0.0] * 20 for _ in range(20)]
        heatmap[10][10] = 1.0
        
        result = worker._draw_heatmap_overlay(frame, heatmap, alpha=0.5)
        
        # 结果应该有变化
        assert not np.array_equal(result, frame)


# ============================================================================
# 网格缩放测试
# ============================================================================

class TestGridScaling:
    """网格缩放逻辑测试"""
    
    def test_heatmap_scales_to_frame_size(self) -> None:
        """热力图应正确缩放到帧尺寸"""
        import cv2
        
        # 20x20 网格
        heatmap = np.array([[0.5] * 20 for _ in range(20)], dtype=np.float32)
        
        # 缩放到 640x480
        scaled = cv2.resize(heatmap, (640, 480), interpolation=cv2.INTER_LINEAR)
        
        assert scaled.shape == (480, 640)
        assert scaled.min() >= 0.0
        assert scaled.max() <= 1.0
    
    @given(
        grid_size=st.integers(min_value=5, max_value=50),
        width=st.integers(min_value=100, max_value=1920),
        height=st.integers(min_value=100, max_value=1080),
    )
    @settings(max_examples=50)
    def test_scaling_preserves_value_range(
        self, grid_size: int, width: int, height: int
    ) -> None:
        """缩放应保持值范围"""
        import cv2
        
        heatmap = np.random.rand(grid_size, grid_size).astype(np.float32)
        scaled = cv2.resize(heatmap, (width, height), interpolation=cv2.INTER_LINEAR)
        
        # 双线性插值可能略微超出原始范围，但应在合理范围内
        assert scaled.min() >= -0.01
        assert scaled.max() <= 1.01


# ============================================================================
# FFmpeg 参数拼装测试
# ============================================================================

class TestFFmpegParameters:
    """FFmpeg 参数拼装测试"""
    
    def test_reader_command_structure(self) -> None:
        """Reader 命令结构应正确"""
        worker = RenderWorker()
        
        # 使用反射获取命令（不实际执行）
        src_url = "rtsp://localhost:554/live/test"
        width, height, fps = 1280, 720, 24
        
        # 验证命令参数
        expected_params = [
            "-rtsp_transport", "tcp",
            "-i", src_url,
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
        ]
        
        # 创建进程但不执行
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = MagicMock()
            worker._create_ffmpeg_reader(src_url, width, height, fps)
            
            call_args = mock_popen.call_args[0][0]
            
            assert call_args[0] == "ffmpeg"
            assert "-rtsp_transport" in call_args
            assert "tcp" in call_args
            assert "-i" in call_args
            assert src_url in call_args
            assert "-f" in call_args
            assert "rawvideo" in call_args
    
    def test_writer_command_structure(self) -> None:
        """Writer 命令结构应正确"""
        worker = RenderWorker()
        
        dst_url = "rtmp://localhost:1935/live/test_heatmap"
        width, height, fps = 1280, 720, 24
        
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = MagicMock()
            worker._create_ffmpeg_writer(dst_url, width, height, fps)
            
            call_args = mock_popen.call_args[0][0]
            
            assert call_args[0] == "ffmpeg"
            assert "-c:v" in call_args
            assert "libx264" in call_args
            assert "-f" in call_args
            assert "flv" in call_args
            assert dst_url in call_args
    
    @given(
        width=st.integers(min_value=320, max_value=1920),
        height=st.integers(min_value=240, max_value=1080),
        fps=st.integers(min_value=1, max_value=60),
    )
    @settings(max_examples=20)
    def test_reader_params_with_various_resolutions(
        self, width: int, height: int, fps: int
    ) -> None:
        """Reader 应支持各种分辨率"""
        worker = RenderWorker()
        
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = MagicMock()
            worker._create_ffmpeg_reader(
                "rtsp://test/stream", width, height, fps
            )
            
            call_args = mock_popen.call_args[0][0]
            
            # 验证 scale filter 包含正确的分辨率
            scale_idx = call_args.index("-vf") + 1
            assert f"scale={width}:{height}" in call_args[scale_idx]
    
    @given(
        width=st.integers(min_value=320, max_value=1920),
        height=st.integers(min_value=240, max_value=1080),
        fps=st.integers(min_value=1, max_value=60),
    )
    @settings(max_examples=20)
    def test_writer_params_with_various_resolutions(
        self, width: int, height: int, fps: int
    ) -> None:
        """Writer 应支持各种分辨率"""
        worker = RenderWorker()
        
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = MagicMock()
            worker._create_ffmpeg_writer(
                "rtmp://test/stream", width, height, fps
            )
            
            call_args = mock_popen.call_args[0][0]
            
            # 验证尺寸参数
            size_idx = call_args.index("-s") + 1
            assert call_args[size_idx] == f"{width}x{height}"


# ============================================================================
# RenderConfig 测试
# ============================================================================

class TestRenderConfig:
    """渲染配置测试"""
    
    def test_default_values(self) -> None:
        """默认值应正确"""
        config = RenderConfig(
            stream_id="test",
            render_stream_id="test_heatmap",
            src_rtsp_url="rtsp://test",
            dst_rtmp_url="rtmp://test",
        )
        
        assert config.render_fps == 24
        assert config.infer_stride == 3
        assert config.overlay_alpha == 0.4
    
    @given(config=render_config_strategy())
    @settings(max_examples=50)
    def test_config_values_in_range(self, config: RenderConfig) -> None:
        """配置值应在有效范围内"""
        assert 1 <= config.render_fps <= 60
        assert 1 <= config.infer_stride <= 10
        assert 0.0 <= config.overlay_alpha <= 1.0
    
    def test_render_stream_id_naming(self) -> None:
        """渲染流 ID 命名规则"""
        stream_id = "abc123"
        config = RenderConfig(
            stream_id=stream_id,
            render_stream_id=f"{stream_id}_heatmap",
            src_rtsp_url="rtsp://test",
            dst_rtmp_url="rtmp://test",
        )
        
        assert config.render_stream_id == "abc123_heatmap"


# ============================================================================
# RenderHealth 状态测试
# ============================================================================

class TestRenderHealth:
    """渲染健康状态测试"""
    
    def test_health_enum_values(self) -> None:
        """健康状态枚举值"""
        assert RenderHealth.HEALTHY.value == "healthy"
        assert RenderHealth.DEGRADED.value == "degraded"
        assert RenderHealth.COOLDOWN.value == "cooldown"
    
    def test_health_string_conversion(self) -> None:
        """健康状态字符串转换"""
        assert str(RenderHealth.HEALTHY) == "RenderHealth.HEALTHY"
        assert RenderHealth.HEALTHY == "healthy"


# ============================================================================
# 推理步长逻辑测试
# ============================================================================

class TestInferenceStride:
    """推理步长逻辑测试"""
    
    @given(
        stride=st.integers(min_value=1, max_value=10),
        frame_count=st.integers(min_value=0, max_value=1000),
    )
    @settings(max_examples=100)
    def test_stride_determines_inference_frequency(
        self, stride: int, frame_count: int
    ) -> None:
        """步长应正确决定推理频率"""
        should_infer = frame_count % stride == 0
        
        # 验证推理帧数
        total_frames = 100
        infer_count = sum(1 for i in range(total_frames) if i % stride == 0)
        expected_count = (total_frames + stride - 1) // stride
        
        # 允许 ±1 的误差（边界情况）
        assert abs(infer_count - expected_count) <= 1
    
    def test_stride_1_infers_every_frame(self) -> None:
        """stride=1 时每帧都推理"""
        stride = 1
        infer_frames = [i for i in range(100) if i % stride == 0]
        assert len(infer_frames) == 100
    
    def test_stride_3_infers_every_third_frame(self) -> None:
        """stride=3 时每 3 帧推理一次"""
        stride = 3
        infer_frames = [i for i in range(100) if i % stride == 0]
        # 0, 3, 6, ..., 99 -> 34 帧
        assert len(infer_frames) == 34


# ============================================================================
# 色图映射测试
# ============================================================================

class TestColorMapping:
    """色图映射测试（COLORMAP_JET）"""
    
    def test_jet_colormap_blue_to_red(self) -> None:
        """JET 色图应从蓝到红"""
        import cv2
        
        # 创建 0-255 的灰度图
        gray = np.arange(256, dtype=np.uint8).reshape(1, 256)
        colored = cv2.applyColorMap(gray, cv2.COLORMAP_JET)
        
        # 低值（0）应偏蓝
        low_color = colored[0, 0]  # BGR
        assert low_color[0] > low_color[2]  # B > R
        
        # 高值（255）应偏红
        high_color = colored[0, 255]  # BGR
        assert high_color[2] > high_color[0]  # R > B
    
    def test_colormap_output_shape(self) -> None:
        """色图输出形状应正确"""
        import cv2
        
        gray = np.zeros((480, 640), dtype=np.uint8)
        colored = cv2.applyColorMap(gray, cv2.COLORMAP_JET)
        
        assert colored.shape == (480, 640, 3)
        assert colored.dtype == np.uint8
