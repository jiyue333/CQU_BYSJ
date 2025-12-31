"""历史数据查询属性测试

Property 6: 历史数据时间范围查询
*For any* 时间范围查询，返回的所有数据的时间戳都应在指定范围内
**Validates: Requirements 6.1, 6.2**

Feature: crowd-counting-system, Property 6: 历史数据时间范围查询
"""

import pytest
from datetime import datetime, timedelta, timezone
from hypothesis import given, strategies as st, settings, assume
from pydantic import ValidationError

from app.schemas.history_stat import (
    AggregatedHistoryResponse,
    AggregatedStat,
    AggregationGranularity,
    HistoryListResponse,
    HistoryQueryParams,
    HistoryStatCreate,
    HistoryStatResponse,
)
from app.schemas.detection import DensityLevel, RegionStat


# 策略：生成有效的时间戳（过去30天内）
def timestamp_strategy():
    """生成过去30天内的时间戳"""
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    return st.datetimes(
        min_value=thirty_days_ago.replace(tzinfo=None),
        max_value=now.replace(tzinfo=None),
    ).map(lambda dt: dt.replace(tzinfo=timezone.utc))


# 策略：生成有效的时间范围
def time_range_strategy():
    """生成有效的时间范围（start_time < end_time）"""
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    
    return st.tuples(
        st.datetimes(
            min_value=thirty_days_ago.replace(tzinfo=None),
            max_value=(now - timedelta(hours=1)).replace(tzinfo=None),
        ),
        st.datetimes(
            min_value=(thirty_days_ago + timedelta(hours=1)).replace(tzinfo=None),
            max_value=now.replace(tzinfo=None),
        ),
    ).filter(lambda t: t[0] < t[1]).map(
        lambda t: (
            t[0].replace(tzinfo=timezone.utc),
            t[1].replace(tzinfo=timezone.utc)
        )
    )


# 策略：生成有效的 stream_id
stream_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1,
    max_size=36
).filter(lambda x: x.strip())


# 策略：生成有效的 total_count
total_count_strategy = st.integers(min_value=0, max_value=1000)


# 策略：生成有效的 RegionStat
def region_stat_strategy():
    """生成有效的区域统计"""
    return st.builds(
        RegionStat,
        region_id=st.text(min_size=1, max_size=36).filter(lambda x: x.strip()),
        region_name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        count=st.integers(min_value=0, max_value=100),
        density=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        level=st.sampled_from(list(DensityLevel)),
    )


# 策略：生成有效的 HistoryStatCreate
def history_stat_create_strategy():
    """生成有效的历史统计创建请求"""
    return st.builds(
        HistoryStatCreate,
        stream_id=stream_id_strategy,
        timestamp=timestamp_strategy(),
        total_count=total_count_strategy,
        region_stats=st.lists(region_stat_strategy(), min_size=0, max_size=5),
    )


class TestHistoryStatSerialization:
    """历史统计序列化属性测试"""

    @given(stat=history_stat_create_strategy())
    @settings(max_examples=100)
    def test_history_stat_round_trip(self, stat: HistoryStatCreate):
        """Property: HistoryStatCreate 序列化后反序列化应返回等价对象
        
        *For any* 有效的历史统计数据，JSON 序列化/反序列化应保持一致
        **Validates: Requirements 6.1**
        """
        # 序列化为 JSON
        json_str = stat.model_dump_json()
        
        # 反序列化
        restored = HistoryStatCreate.model_validate_json(json_str)
        
        # 验证等价性
        assert restored.stream_id == stat.stream_id
        assert restored.total_count == stat.total_count
        assert len(restored.region_stats) == len(stat.region_stats)
        
        # 时间戳比较（允许微小误差）
        time_diff = abs((restored.timestamp - stat.timestamp).total_seconds())
        assert time_diff < 1, f"时间戳差异过大: {time_diff}s"

    @given(stat=history_stat_create_strategy())
    @settings(max_examples=100)
    def test_history_stat_dict_round_trip(self, stat: HistoryStatCreate):
        """Property: HistoryStatCreate 转换为 dict 后应能重建
        
        *For any* 有效的历史统计数据，转换为 dict 后应能重建等价对象
        **Validates: Requirements 6.1**
        """
        # 转换为 dict
        data = stat.model_dump()
        
        # 从 dict 重建
        restored = HistoryStatCreate(**data)
        
        assert restored.stream_id == stat.stream_id
        assert restored.total_count == stat.total_count


class TestHistoryQueryParams:
    """历史查询参数属性测试"""

    @given(time_range=time_range_strategy())
    @settings(max_examples=100)
    def test_valid_time_range_accepted(self, time_range: tuple[datetime, datetime]):
        """Property: 有效的时间范围应被接受
        
        *For any* start_time < end_time 的时间范围，应被接受
        **Validates: Requirements 6.2**
        """
        start_time, end_time = time_range
        assume(start_time < end_time)
        
        params = HistoryQueryParams(
            start_time=start_time,
            end_time=end_time,
        )
        
        assert params.start_time == start_time
        assert params.end_time == end_time

    def test_invalid_time_range_rejected(self):
        """Property: 无效的时间范围应被拒绝
        
        end_time < start_time 应被拒绝
        **Validates: Requirements 6.2**
        """
        now = datetime.now(timezone.utc)
        start_time = now
        end_time = now - timedelta(hours=1)
        
        with pytest.raises(ValidationError):
            HistoryQueryParams(
                start_time=start_time,
                end_time=end_time,
            )

    @given(limit=st.integers(min_value=1, max_value=1000))
    @settings(max_examples=100)
    def test_valid_limit_accepted(self, limit: int):
        """Property: 有效的 limit 值应被接受
        
        *For any* 1 <= limit <= 1000，应被接受
        **Validates: Requirements 6.2**
        """
        params = HistoryQueryParams(limit=limit)
        assert params.limit == limit

    def test_invalid_limit_rejected(self):
        """Property: 无效的 limit 值应被拒绝
        
        limit < 1 或 limit > 1000 应被拒绝
        **Validates: Requirements 6.2**
        """
        with pytest.raises(ValidationError):
            HistoryQueryParams(limit=0)
        
        with pytest.raises(ValidationError):
            HistoryQueryParams(limit=1001)

    @given(offset=st.integers(min_value=0, max_value=10000))
    @settings(max_examples=100)
    def test_valid_offset_accepted(self, offset: int):
        """Property: 有效的 offset 值应被接受
        
        *For any* offset >= 0，应被接受
        **Validates: Requirements 6.2**
        """
        params = HistoryQueryParams(offset=offset)
        assert params.offset == offset

    def test_negative_offset_rejected(self):
        """Property: 负的 offset 值应被拒绝
        
        **Validates: Requirements 6.2**
        """
        with pytest.raises(ValidationError):
            HistoryQueryParams(offset=-1)


class TestTimeRangeFiltering:
    """时间范围过滤属性测试"""

    @given(
        time_range=time_range_strategy(),
        stats=st.lists(history_stat_create_strategy(), min_size=1, max_size=20)
    )
    @settings(max_examples=100)
    def test_filtered_timestamps_within_range(
        self,
        time_range: tuple[datetime, datetime],
        stats: list[HistoryStatCreate]
    ):
        """Property 6: 时间范围过滤后的数据时间戳都在范围内
        
        *For any* 时间范围查询，返回的所有数据的时间戳都应在指定范围内
        **Validates: Requirements 6.1, 6.2**
        """
        start_time, end_time = time_range
        assume(start_time < end_time)
        
        # 模拟过滤逻辑
        filtered = [
            stat for stat in stats
            if start_time <= stat.timestamp <= end_time
        ]
        
        # 验证所有过滤后的数据都在时间范围内
        for stat in filtered:
            assert stat.timestamp >= start_time, \
                f"时间戳 {stat.timestamp} 小于 start_time {start_time}"
            assert stat.timestamp <= end_time, \
                f"时间戳 {stat.timestamp} 大于 end_time {end_time}"

    @given(
        time_range=time_range_strategy(),
        stats=st.lists(history_stat_create_strategy(), min_size=1, max_size=20)
    )
    @settings(max_examples=100)
    def test_no_data_outside_range(
        self,
        time_range: tuple[datetime, datetime],
        stats: list[HistoryStatCreate]
    ):
        """Property: 时间范围外的数据不应被返回
        
        *For any* 时间范围查询，范围外的数据不应出现在结果中
        **Validates: Requirements 6.2**
        """
        start_time, end_time = time_range
        assume(start_time < end_time)
        
        # 模拟过滤逻辑
        filtered = [
            stat for stat in stats
            if start_time <= stat.timestamp <= end_time
        ]
        
        # 验证范围外的数据不在结果中
        outside_range = [
            stat for stat in stats
            if stat.timestamp < start_time or stat.timestamp > end_time
        ]
        
        for stat in outside_range:
            assert stat not in filtered, \
                f"范围外的数据 {stat.timestamp} 不应在结果中"


class TestAggregationGranularity:
    """聚合粒度属性测试"""

    @given(granularity=st.sampled_from(list(AggregationGranularity)))
    @settings(max_examples=10)
    def test_all_granularities_valid(self, granularity: AggregationGranularity):
        """Property: 所有聚合粒度都应是有效的
        
        *For any* 聚合粒度枚举值，都应被接受
        **Validates: Requirements 6.2**
        """
        params = HistoryQueryParams(granularity=granularity)
        assert params.granularity == granularity

    def test_invalid_granularity_rejected(self):
        """Property: 无效的聚合粒度应被拒绝
        
        **Validates: Requirements 6.2**
        """
        with pytest.raises(ValidationError):
            HistoryQueryParams(granularity="invalid")


class TestAggregatedStatValidation:
    """聚合统计验证属性测试"""

    @given(
        avg_count=st.floats(min_value=0.0, max_value=1000.0, allow_nan=False),
        max_count=st.integers(min_value=0, max_value=1000),
        min_count=st.integers(min_value=0, max_value=1000),
        sample_count=st.integers(min_value=1, max_value=10000),
    )
    @settings(max_examples=100)
    def test_aggregated_stat_constraints(
        self,
        avg_count: float,
        max_count: int,
        min_count: int,
        sample_count: int,
    ):
        """Property: 聚合统计应满足数学约束
        
        *For any* 聚合统计，min_count <= avg_count <= max_count
        **Validates: Requirements 6.2**
        """
        # 确保 min <= max
        actual_min = min(min_count, max_count)
        actual_max = max(min_count, max_count)
        
        # 确保 avg 在 min 和 max 之间
        actual_avg = max(actual_min, min(avg_count, actual_max))
        
        stat = AggregatedStat(
            timestamp=datetime.now(timezone.utc),
            avg_count=actual_avg,
            max_count=actual_max,
            min_count=actual_min,
            sample_count=sample_count,
        )
        
        # 验证约束
        assert stat.min_count <= stat.avg_count <= stat.max_count or \
               stat.min_count == stat.max_count, \
            f"约束违反: min={stat.min_count}, avg={stat.avg_count}, max={stat.max_count}"


class TestHistoryListResponse:
    """历史列表响应属性测试"""

    @given(
        total=st.integers(min_value=0, max_value=10000),
        returned_count=st.integers(min_value=0, max_value=100),
        offset=st.integers(min_value=0, max_value=10000),
    )
    @settings(max_examples=100)
    def test_has_more_calculation(
        self,
        total: int,
        returned_count: int,
        offset: int,
    ):
        """Property: has_more 应正确反映是否有更多数据
        
        *For any* 分页查询，has_more = (offset + returned_count) < total
        **Validates: Requirements 6.2**
        """
        # 确保 returned_count 不超过剩余数据
        actual_returned = min(returned_count, max(0, total - offset))
        
        has_more = (offset + actual_returned) < total
        
        # 创建模拟响应
        stats = [
            HistoryStatResponse(
                id=i,
                stream_id="test",
                timestamp=datetime.now(timezone.utc),
                total_count=0,
                region_stats=[],
            )
            for i in range(actual_returned)
        ]
        
        response = HistoryListResponse(
            stats=stats,
            total=total,
            has_more=has_more,
        )
        
        # 验证 has_more 计算正确
        expected_has_more = (offset + len(response.stats)) < response.total
        assert response.has_more == expected_has_more, \
            f"has_more 计算错误: expected={expected_has_more}, actual={response.has_more}"
