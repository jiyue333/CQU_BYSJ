"""
统计数据聚合服务

将实时检测的帧数据按时间窗口聚合，写入数据库
"""

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logger import logger
from app.models.stats_aggregated import StatsAggregated
from app.repositories.stats_repository import StatsRepository


@dataclass
class RegionFrameStats:
    """单帧区域统计"""
    region_id: str
    name: str
    count: int
    density: float
    crowd_index: float


@dataclass
class FrameStats:
    """单帧统计数据（来自推理服务）"""
    source_id: str
    timestamp: str  # ISO8601
    total_count: int
    total_density: float
    crowd_index: float
    regions: list[RegionFrameStats] = field(default_factory=list)


@dataclass
class AggregatedBucket:
    """聚合桶（存储一个时间窗口内的帧数据）"""
    samples: list[FrameStats] = field(default_factory=list)

    def add(self, stats: FrameStats) -> None:
        self.samples.append(stats)

    @property
    def sample_count(self) -> int:
        return len(self.samples)

    def aggregate(self) -> dict:
        """聚合计算 avg/max/min"""
        if not self.samples:
            return {}

        total_counts = [s.total_count for s in self.samples]
        total_densities = [s.total_density for s in self.samples]
        crowd_indices = [s.crowd_index for s in self.samples]

        # 聚合区域数据
        region_data: dict[str, dict] = defaultdict(lambda: {
            "name": "",
            "counts": [],
            "densities": [],
            "crowd_indices": [],
        })

        for sample in self.samples:
            for r in sample.regions:
                region_data[r.region_id]["name"] = r.name
                region_data[r.region_id]["counts"].append(r.count)
                region_data[r.region_id]["densities"].append(r.density)
                region_data[r.region_id]["crowd_indices"].append(r.crowd_index)

        # 计算区域聚合
        region_stats = {}
        for region_id, data in region_data.items():
            counts = data["counts"]
            crowd_indices_r = data["crowd_indices"]
            region_stats[region_id] = {
                "name": data["name"],
                "avg": sum(counts) / len(counts) if counts else 0,
                "max": max(counts) if counts else 0,
                "min": min(counts) if counts else 0,
                "crowd_index": sum(crowd_indices_r) / len(crowd_indices_r) if crowd_indices_r else 0,
            }

        return {
            "total_count_avg": sum(total_counts) / len(total_counts),
            "total_count_max": max(total_counts),
            "total_count_min": min(total_counts),
            "total_density_avg": sum(total_densities) / len(total_densities),
            "crowd_index_avg": sum(crowd_indices) / len(crowd_indices),
            "region_stats": region_stats,
            "sample_count": self.sample_count,
        }


class StatsAggregator:
    """
    统计聚合服务

    使用方式：
        aggregator = StatsAggregator()

        # 推理服务每帧调用
        aggregator.collect(frame_stats)

        # 定时任务每分钟调用
        aggregator.flush(db_session)
    """

    def __init__(self):
        # source_id -> time_bucket -> AggregatedBucket
        self._buffers: dict[str, dict[str, AggregatedBucket]] = defaultdict(
            lambda: defaultdict(AggregatedBucket)
        )

    def _get_time_bucket(self, timestamp: str, interval: str = "1m") -> str:
        """
        将时间戳对齐到时间桶

        Args:
            timestamp: ISO8601 时间戳
            interval: 聚合间隔 (1m/5m/1h/1d)
        """
        try:
            # 解析时间戳
            if timestamp.endswith("Z"):
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(timestamp)

            # 对齐到分钟
            if interval == "1m":
                dt = dt.replace(second=0, microsecond=0)
            elif interval == "5m":
                minute = (dt.minute // 5) * 5
                dt = dt.replace(minute=minute, second=0, microsecond=0)
            elif interval == "1h":
                dt = dt.replace(minute=0, second=0, microsecond=0)
            elif interval == "1d":
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)

            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception as e:
            logger.warning(f"时间戳解析失败: {timestamp}, {e}")
            return timestamp

    def collect(self, stats: FrameStats, interval: str = "1m") -> None:
        """
        收集单帧统计数据

        Args:
            stats: 帧统计数据
            interval: 聚合间隔
        """
        time_bucket = self._get_time_bucket(stats.timestamp, interval)
        self._buffers[stats.source_id][time_bucket].add(stats)

    def flush(self, db: Session, interval: str = "1m") -> int:
        """
        将缓存数据聚合后写入数据库

        Args:
            db: 数据库会话
            interval: 聚合间隔

        Returns:
            写入的记录数
        """
        repo = StatsRepository(db)
        count = 0

        for source_id, buckets in list(self._buffers.items()):
            for time_bucket, bucket in list(buckets.items()):
                if bucket.sample_count == 0:
                    continue

                aggregated = bucket.aggregate()

                stat = StatsAggregated(
                    source_id=source_id,
                    time_bucket=time_bucket,
                    interval_type=interval,
                    total_count_avg=aggregated["total_count_avg"],
                    total_count_max=aggregated["total_count_max"],
                    total_count_min=aggregated["total_count_min"],
                    total_density_avg=aggregated["total_density_avg"],
                    crowd_index_avg=aggregated["crowd_index_avg"],
                    region_stats=json.dumps(aggregated["region_stats"], ensure_ascii=False),
                    sample_count=aggregated["sample_count"],
                )

                repo.upsert(stat)
                count += 1

                logger.debug(f"聚合写入: {source_id} {time_bucket} ({bucket.sample_count} samples)")

            # 清空已处理的桶
            buckets.clear()

        return count

    def get_realtime_stats(self, source_id: str) -> Optional[dict]:
        """
        获取实时统计（内存中最新数据）

        Args:
            source_id: 数据源 ID

        Returns:
            最新的聚合统计，如果没有数据返回 None
        """
        if source_id not in self._buffers:
            return None

        buckets = self._buffers[source_id]
        if not buckets:
            return None

        # 获取最新的桶
        latest_bucket_key = max(buckets.keys())
        bucket = buckets[latest_bucket_key]

        if bucket.sample_count == 0:
            return None

        aggregated = bucket.aggregate()
        aggregated["time_bucket"] = latest_bucket_key
        return aggregated

    def clear(self, source_id: Optional[str] = None) -> None:
        """
        清空缓存

        Args:
            source_id: 指定数据源，None 则清空全部
        """
        if source_id:
            if source_id in self._buffers:
                del self._buffers[source_id]
        else:
            self._buffers.clear()


# 全局聚合器实例
stats_aggregator = StatsAggregator()
