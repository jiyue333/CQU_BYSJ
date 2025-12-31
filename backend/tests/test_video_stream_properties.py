"""VideoStream 属性测试

Property 8: 流状态一致性
*For any* stream_id，状态转换应遵循：starting → running/error，running → stopped/error/cooldown
**Validates: Requirements 9.4**

Feature: crowd-counting-system, Property 8: 流状态一致性
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

from app.models.video_stream import (
    StreamStatus,
    StreamType,
    VALID_STATUS_TRANSITIONS,
    is_valid_status_transition,
)


# 策略：生成随机的 StreamStatus
stream_status_strategy = st.sampled_from(list(StreamStatus))
stream_type_strategy = st.sampled_from(list(StreamType))


class TestStreamStatusTransitions:
    """流状态转换属性测试"""

    @given(status=stream_status_strategy)
    @settings(max_examples=100)
    def test_same_status_transition_not_valid(self, status: StreamStatus):
        """Property: 相同状态转换不是有效的状态转换
        
        *For any* 状态 S，从 S 转换到 S 不是有效的状态转换
        （需要显式在转换矩阵中定义才有效）
        **Validates: Requirements 9.4**
        """
        # 相同状态转换不在转换矩阵中，所以不是有效转换
        assert is_valid_status_transition(status, status) is False

    @given(from_status=stream_status_strategy, to_status=stream_status_strategy)
    @settings(max_examples=100)
    def test_valid_transitions_match_matrix(
        self, from_status: StreamStatus, to_status: StreamStatus
    ):
        """Property: 状态转换结果与转换矩阵一致
        
        *For any* 状态对 (from, to)，is_valid_status_transition 的结果
        应该与 VALID_STATUS_TRANSITIONS 矩阵一致
        **Validates: Requirements 9.4**
        """
        # 检查是否在有效转换矩阵中
        expected_valid = to_status in VALID_STATUS_TRANSITIONS.get(from_status, set())
        actual_valid = is_valid_status_transition(from_status, to_status)
        
        assert actual_valid == expected_valid, (
            f"状态转换 {from_status} → {to_status} 预期 {expected_valid}，实际 {actual_valid}"
        )


    @given(from_status=stream_status_strategy)
    @settings(max_examples=100)
    def test_starting_can_only_go_to_running_or_error(self, from_status: StreamStatus):
        """Property: STARTING 状态只能转换到 RUNNING 或 ERROR
        
        *For any* STARTING 状态，只有 RUNNING 和 ERROR 是有效的目标状态
        **Validates: Requirements 9.4**
        """
        assume(from_status == StreamStatus.STARTING)
        
        valid_targets = {StreamStatus.RUNNING, StreamStatus.ERROR}
        
        for target in StreamStatus:
            result = is_valid_status_transition(from_status, target)
            expected = target in valid_targets
            assert result == expected, (
                f"STARTING → {target}: 预期 {expected}，实际 {result}"
            )

    @given(from_status=stream_status_strategy)
    @settings(max_examples=100)
    def test_running_can_go_to_stopped_error_or_cooldown(self, from_status: StreamStatus):
        """Property: RUNNING 状态可以转换到 STOPPED、ERROR 或 COOLDOWN
        
        *For any* RUNNING 状态，STOPPED、ERROR、COOLDOWN 是有效的目标状态
        **Validates: Requirements 9.4**
        """
        assume(from_status == StreamStatus.RUNNING)
        
        valid_targets = {
            StreamStatus.STOPPED, 
            StreamStatus.ERROR, 
            StreamStatus.COOLDOWN,
        }
        
        for target in StreamStatus:
            result = is_valid_status_transition(from_status, target)
            expected = target in valid_targets
            assert result == expected, (
                f"RUNNING → {target}: 预期 {expected}，实际 {result}"
            )

    @given(from_status=stream_status_strategy)
    @settings(max_examples=100)
    def test_terminal_states_can_only_restart(self, from_status: StreamStatus):
        """Property: 终止状态（STOPPED/ERROR/COOLDOWN）只能转换到 STARTING
        
        *For any* 终止状态，只有 STARTING 是有效的目标状态
        **Validates: Requirements 9.4**
        """
        terminal_states = {StreamStatus.STOPPED, StreamStatus.ERROR, StreamStatus.COOLDOWN}
        assume(from_status in terminal_states)
        
        valid_targets = {StreamStatus.STARTING}
        
        for target in StreamStatus:
            result = is_valid_status_transition(from_status, target)
            expected = target in valid_targets
            assert result == expected, (
                f"{from_status} → {target}: 预期 {expected}，实际 {result}"
            )


class TestStreamStatusTransitionSequences:
    """流状态转换序列测试"""

    @given(
        st.lists(
            stream_status_strategy,
            min_size=2,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_transition_sequence_validity(self, status_sequence: list[StreamStatus]):
        """Property: 状态转换序列中每一步都应该可验证
        
        *For any* 状态序列，每一步转换的有效性都可以通过 is_valid_status_transition 判断
        **Validates: Requirements 9.4**
        """
        for i in range(len(status_sequence) - 1):
            from_status = status_sequence[i]
            to_status = status_sequence[i + 1]
            
            # 验证函数不会抛出异常
            result = is_valid_status_transition(from_status, to_status)
            assert isinstance(result, bool), (
                f"is_valid_status_transition 应该返回 bool，实际返回 {type(result)}"
            )

    def test_all_states_have_at_least_one_valid_transition(self):
        """Property: 每个状态至少有一个有效的转换目标
        
        *For any* 状态，至少存在一个有效的转换目标（包括自身）
        **Validates: Requirements 9.4**
        """
        for status in StreamStatus:
            valid_targets = [
                target for target in StreamStatus
                if is_valid_status_transition(status, target)
            ]
            assert len(valid_targets) >= 1, (
                f"状态 {status} 没有任何有效的转换目标"
            )

    def test_no_direct_transition_from_starting_to_stopped(self):
        """Property: 不能从 STARTING 直接转换到 STOPPED
        
        STARTING 状态必须先变成 RUNNING 才能 STOPPED
        **Validates: Requirements 9.4**
        """
        assert is_valid_status_transition(
            StreamStatus.STARTING, StreamStatus.STOPPED
        ) is False

    def test_no_direct_transition_from_starting_to_cooldown(self):
        """Property: 不能从 STARTING 直接转换到 COOLDOWN
        
        STARTING 状态必须先变成 RUNNING 才能进入 COOLDOWN
        **Validates: Requirements 9.4**
        """
        assert is_valid_status_transition(
            StreamStatus.STARTING, StreamStatus.COOLDOWN
        ) is False
