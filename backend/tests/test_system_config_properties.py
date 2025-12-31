"""SystemConfig 属性测试

Property 7: 配置范围约束
*For any* 推理频率配置，值应在 1-3 范围内；配置持久化后重启应保持
**Validates: Requirements 8.3, 8.4**

Feature: crowd-counting-system, Property 7: 配置范围约束
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from pydantic import ValidationError

from app.schemas.system_config import (
    SystemConfigBase,
    SystemConfigCreate,
    SystemConfigUpdate,
    SystemConfigResponse,
)


# 策略：生成有效的推理频率 (1-3)
valid_fps_strategy = st.integers(min_value=1, max_value=3)

# 策略：生成无效的推理频率
invalid_fps_strategy = st.one_of(
    st.integers(max_value=0),
    st.integers(min_value=4),
)

# 策略：生成有效的置信度阈值 (0-1)
valid_confidence_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)

# 策略：生成无效的置信度阈值
invalid_confidence_strategy = st.one_of(
    st.floats(max_value=-0.01, allow_nan=False, allow_infinity=False),
    st.floats(min_value=1.01, allow_nan=False, allow_infinity=False),
)

# 策略：生成有效的热力图网格大小 (5-100)
valid_grid_size_strategy = st.integers(min_value=5, max_value=100)

# 策略：生成有效的衰减因子 (0-1)
valid_decay_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)


class TestInferenceFpsConstraint:
    """推理频率约束属性测试"""

    @given(fps=valid_fps_strategy)
    @settings(max_examples=100)
    def test_valid_fps_accepted(self, fps: int):
        """Property: 有效的推理频率 (1-3) 应被接受
        
        *For any* fps 在 1-3 范围内，配置应被成功创建
        **Validates: Requirements 8.3**
        """
        config = SystemConfigCreate(inference_fps=fps)
        assert config.inference_fps == fps
        assert 1 <= config.inference_fps <= 3

    @given(fps=invalid_fps_strategy)
    @settings(max_examples=100)
    def test_invalid_fps_rejected(self, fps: int):
        """Property: 无效的推理频率应被拒绝
        
        *For any* fps 不在 1-3 范围内，配置创建应失败
        **Validates: Requirements 8.3**
        """
        with pytest.raises(ValidationError):
            SystemConfigCreate(inference_fps=fps)

    @given(fps=valid_fps_strategy)
    @settings(max_examples=100)
    def test_fps_preserved_after_serialization(self, fps: int):
        """Property: 推理频率在序列化后应保持不变
        
        *For any* 有效的 fps，序列化/反序列化后值应保持不变
        **Validates: Requirements 8.4**
        """
        original = SystemConfigCreate(inference_fps=fps)
        
        # 序列化为 JSON
        json_str = original.model_dump_json()
        
        # 反序列化
        restored = SystemConfigCreate.model_validate_json(json_str)
        
        assert restored.inference_fps == original.inference_fps


class TestConfidenceThresholdConstraint:
    """置信度阈值约束属性测试"""

    @given(threshold=valid_confidence_strategy)
    @settings(max_examples=100)
    def test_valid_confidence_accepted(self, threshold: float):
        """Property: 有效的置信度阈值 (0-1) 应被接受
        
        *For any* threshold 在 0-1 范围内，配置应被成功创建
        **Validates: Requirements 8.1**
        """
        config = SystemConfigCreate(confidence_threshold=threshold)
        assert 0.0 <= config.confidence_threshold <= 1.0

    @given(threshold=invalid_confidence_strategy)
    @settings(max_examples=100)
    def test_invalid_confidence_rejected(self, threshold: float):
        """Property: 无效的置信度阈值应被拒绝
        
        *For any* threshold 不在 0-1 范围内，配置创建应失败
        **Validates: Requirements 8.1**
        """
        assume(threshold < 0 or threshold > 1)  # 确保是无效值
        with pytest.raises(ValidationError):
            SystemConfigCreate(confidence_threshold=threshold)

    @given(threshold=valid_confidence_strategy)
    @settings(max_examples=100)
    def test_confidence_preserved_after_serialization(self, threshold: float):
        """Property: 置信度阈值在序列化后应保持不变
        
        *For any* 有效的 threshold，序列化/反序列化后值应保持不变
        **Validates: Requirements 8.4**
        """
        original = SystemConfigCreate(confidence_threshold=threshold)
        
        # 序列化为 JSON
        json_str = original.model_dump_json()
        
        # 反序列化
        restored = SystemConfigCreate.model_validate_json(json_str)
        
        assert abs(restored.confidence_threshold - original.confidence_threshold) < 1e-10


class TestConfigPersistence:
    """配置持久化属性测试"""

    @given(
        fps=valid_fps_strategy,
        confidence=valid_confidence_strategy,
        grid_size=valid_grid_size_strategy,
        decay=valid_decay_strategy,
    )
    @settings(max_examples=100)
    def test_full_config_round_trip(
        self, 
        fps: int, 
        confidence: float, 
        grid_size: int, 
        decay: float
    ):
        """Property: 完整配置序列化后反序列化应返回等价对象
        
        *For any* 有效的配置组合，JSON 序列化/反序列化应保持一致
        **Validates: Requirements 8.4**
        """
        original = SystemConfigCreate(
            inference_fps=fps,
            confidence_threshold=confidence,
            heatmap_grid_size=grid_size,
            heatmap_decay=decay,
        )
        
        # 序列化为 JSON
        json_str = original.model_dump_json()
        
        # 反序列化
        restored = SystemConfigCreate.model_validate_json(json_str)
        
        # 验证等价性
        assert restored.inference_fps == original.inference_fps
        assert abs(restored.confidence_threshold - original.confidence_threshold) < 1e-10
        assert restored.heatmap_grid_size == original.heatmap_grid_size
        assert abs(restored.heatmap_decay - original.heatmap_decay) < 1e-10

    @given(
        fps=valid_fps_strategy,
        confidence=valid_confidence_strategy,
        grid_size=valid_grid_size_strategy,
        decay=valid_decay_strategy,
    )
    @settings(max_examples=100)
    def test_config_dict_round_trip(
        self, 
        fps: int, 
        confidence: float, 
        grid_size: int, 
        decay: float
    ):
        """Property: 配置转换为 dict 后应能重建
        
        模拟数据库存储和读取过程
        *For any* 有效的配置，转换为 dict 后应能重建等价对象
        **Validates: Requirements 8.4**
        """
        original = SystemConfigCreate(
            inference_fps=fps,
            confidence_threshold=confidence,
            heatmap_grid_size=grid_size,
            heatmap_decay=decay,
        )
        
        # 转换为 dict（模拟存储）
        data = original.model_dump()
        
        # 从 dict 重建（模拟读取）
        restored = SystemConfigCreate(**data)
        
        assert restored == original


class TestConfigUpdate:
    """配置更新属性测试"""

    @given(fps=valid_fps_strategy)
    @settings(max_examples=100)
    def test_partial_update_fps_only(self, fps: int):
        """Property: 部分更新只修改指定字段
        
        *For any* 有效的 fps，部分更新应只包含该字段
        **Validates: Requirements 8.3**
        """
        update = SystemConfigUpdate(inference_fps=fps)
        
        # 只有 fps 被设置
        assert update.inference_fps == fps
        assert update.confidence_threshold is None
        assert update.heatmap_grid_size is None
        assert update.heatmap_decay is None

    @given(
        fps=st.one_of(st.none(), valid_fps_strategy),
        confidence=st.one_of(st.none(), valid_confidence_strategy),
    )
    @settings(max_examples=100)
    def test_update_preserves_none_values(
        self, 
        fps: int | None, 
        confidence: float | None
    ):
        """Property: 更新请求中的 None 值应被保留
        
        *For any* 更新请求，None 值表示不更新该字段
        **Validates: Requirements 8.4**
        """
        update = SystemConfigUpdate(
            inference_fps=fps,
            confidence_threshold=confidence,
        )
        
        # 序列化后反序列化
        json_str = update.model_dump_json(exclude_none=True)
        restored = SystemConfigUpdate.model_validate_json(json_str)
        
        # None 值应被保留（或在 exclude_none 后不存在）
        if fps is not None:
            assert restored.inference_fps == fps
        if confidence is not None:
            assert abs(restored.confidence_threshold - confidence) < 1e-10


class TestDefaultValues:
    """默认值属性测试"""

    def test_default_values_are_valid(self):
        """Property: 默认配置值应在有效范围内
        
        **Validates: Requirements 8.3, 8.4**
        """
        config = SystemConfigCreate()
        
        # 验证默认值
        assert config.confidence_threshold == 0.5
        assert config.inference_fps == 2
        assert config.heatmap_grid_size == 20
        assert config.heatmap_decay == 0.3
        
        # 验证默认值在有效范围内
        assert 0.0 <= config.confidence_threshold <= 1.0
        assert 1 <= config.inference_fps <= 3
        assert 5 <= config.heatmap_grid_size <= 100
        assert 0.0 <= config.heatmap_decay <= 1.0

    def test_default_values_preserved_after_serialization(self):
        """Property: 默认值在序列化后应保持不变
        
        **Validates: Requirements 8.4**
        """
        original = SystemConfigCreate()
        
        # 序列化后反序列化
        json_str = original.model_dump_json()
        restored = SystemConfigCreate.model_validate_json(json_str)
        
        assert restored == original
