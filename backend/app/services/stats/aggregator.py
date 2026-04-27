"""
统计数据聚合服务

将实时检测的帧数据按时间窗口聚合，写入数据库
"""

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logger import logger
from app.models.stats_aggregated import StatsAggregated
from app.repositories.stats_repository import StatsRepository

# 支持的聚合间隔
INTERVAL_MINUTES = {"1m": 1, "5m": 5, "1h": 60, "1d": 1440}


@dataclass
class RegionFrameStats:
    """单帧区域统计"""
    region_id: str
    name: str
    count: int
    density: float
    in_total: int = 0
    out_total: int = 0


@dataclass
class FrameStats:
    """单帧统计数据（来自推理服务）"""
    source_id: str
    timestamp: str  # ISO8601
    total_count: int
    total_density: float
    regions: list[RegionFrameStats] = field(default_factory=list)
    dm_count_estimate: float = 0.0


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

        # 聚合区域数据
        region_data: dict[str, dict] = defaultdict(lambda: {
            "name": "",
            "counts": [],
            "densities": [],
            "in_total": 0,
            "out_total": 0,
        })

        for sample in self.samples:
            for r in sample.regions:
                region_data[r.region_id]["name"] = r.name
                region_data[r.region_id]["counts"].append(r.count)
                region_data[r.region_id]["densities"].append(r.density)
                region_data[r.region_id]["in_total"] = r.in_total
                region_data[r.region_id]["out_total"] = r.out_total

        # 计算区域聚合
        region_stats = {}
        for region_id, data in region_data.items():
            counts = data["counts"]
            densities = data["densities"]
            region_stats[region_id] = {
                "name": data["name"],
                "avg": sum(counts) / len(counts) if counts else 0,
                "max": max(counts) if counts else 0,
                "min": min(counts) if counts else 0,
                "density_avg": sum(densities) / len(densities) if densities else 0,
                "in_total": data["in_total"],
                "out_total": data["out_total"],
            }
        dm_counts = [s.dm_count_estimate for s in self.samples]

        return {
            "total_count_avg": sum(total_counts) / len(total_counts),
            "total_count_max": max(total_counts),
            "total_count_min": min(total_counts),
            "total_density_avg": sum(total_densities) / len(total_densities),
            "dm_count_avg": sum(dm_counts) / len(dm_counts) if dm_counts else 0,
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

    def flush(self, db: Session, interval: str = "1m", auto_rollup: bool = True) -> int:
        """
        将缓存数据聚合后写入数据库

        Args:
            db: 数据库会话
            interval: 聚合间隔
            auto_rollup: 是否自动上卷到更高粒度（5m/1h/1d）

        Returns:
            写入的记录数
        """
        logger.debug("刷新聚合数据到数据库")
        repo = StatsRepository(db)
        count = 0
        flushed_source_ids: list[str] = []

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
                    region_stats=json.dumps(aggregated["region_stats"], ensure_ascii=False),
                    sample_count=aggregated["sample_count"],
                )

                repo.upsert(stat)
                count += 1
                if source_id not in flushed_source_ids:
                    flushed_source_ids.append(source_id)

                logger.debug(f"聚合写入: {source_id} {time_bucket} ({bucket.sample_count} samples)")

            # 清空已处理的桶
            buckets.clear()

        # 自动上卷到更高粒度
        if auto_rollup and flushed_source_ids:
            for sid in flushed_source_ids:
                rollup_stats(db, source_id=sid)

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


def rollup_stats(db: Session, source_id: Optional[str] = None) -> int:
    """
    将 1m 粒度数据上卷为 5m/1h/1d 粒度

    从 stats_aggregated 表读取 1m 数据，聚合后写入更高粒度。
    通常由定时任务调用。

    Args:
        db: 数据库会话
        source_id: 可选，指定数据源

    Returns:
        写入的记录数
    """
    repo = StatsRepository(db)
    count = 0

    # 上卷目标：5m, 1h, 1d
    rollup_intervals = ["5m", "1h", "1d"]

    # 时间范围：过去 2 小时内的 1m 数据（足够覆盖上卷需求）
    now = datetime.utcnow()
    time_from = (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    time_to = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    # 获取需要处理的 source_id 列表
    if source_id:
        source_ids = [source_id]
    else:
        # 从 1m 数据中获取所有 source_id
        from sqlalchemy import select, distinct
        stmt = select(distinct(StatsAggregated.source_id)).where(
            StatsAggregated.interval_type == "1m"
        )
        source_ids = list(db.scalars(stmt).all())

    for sid in source_ids:
        # 获取 1m 原始数据
        stats_1m = repo.get_by_time_range(
            source_id=sid,
            interval_type="1m",
            time_from=time_from,
            time_to=time_to,
        )

        if not stats_1m:
            continue

        for target_interval in rollup_intervals:
            # 按目标时间桶分组
            buckets: dict[str, list[StatsAggregated]] = defaultdict(list)
            for s in stats_1m:
                bucket_key = _align_time_bucket(s.time_bucket, target_interval)
                buckets[bucket_key].append(s)

            # 聚合每个桶
            for bucket_key, bucket_stats in buckets.items():
                if not bucket_stats:
                    continue

                # 计算聚合值
                total_counts = [s.total_count_avg for s in bucket_stats]
                total_maxes = [s.total_count_max for s in bucket_stats]
                total_mins = [s.total_count_min for s in bucket_stats]
                total_densities = [s.total_density_avg for s in bucket_stats]
                sample_counts = [s.sample_count for s in bucket_stats]

                # 合并区域统计
                merged_regions: dict[str, dict] = defaultdict(lambda: {
                    "name": "",
                    "avgs": [],
                    "maxes": [],
                    "mins": [],
                    "densities": [],
                    "in_total": 0,
                    "out_total": 0,
                })
                ordered_bucket_stats = sorted(bucket_stats, key=lambda item: item.time_bucket)
                for s in ordered_bucket_stats:
                    region_dict = s.get_region_stats_dict()
                    for region_id, r in region_dict.items():
                        merged_regions[region_id]["name"] = r.name
                        merged_regions[region_id]["avgs"].append(r.avg)
                        merged_regions[region_id]["maxes"].append(r.max)
                        merged_regions[region_id]["mins"].append(r.min)
                        merged_regions[region_id]["densities"].append(r.density_avg)
                        merged_regions[region_id]["in_total"] = r.in_total
                        merged_regions[region_id]["out_total"] = r.out_total

                region_stats = {}
                for region_id, data in merged_regions.items():
                    region_stats[region_id] = {
                        "name": data["name"],
                        "avg": sum(data["avgs"]) / len(data["avgs"]) if data["avgs"] else 0,
                        "max": max(data["maxes"]) if data["maxes"] else 0,
                        "min": min(data["mins"]) if data["mins"] else 0,
                        "density_avg": sum(data["densities"]) / len(data["densities"]) if data["densities"] else 0,
                        "in_total": data["in_total"],
                        "out_total": data["out_total"],
                    }

                stat = StatsAggregated(
                    source_id=sid,
                    time_bucket=bucket_key,
                    interval_type=target_interval,
                    total_count_avg=sum(total_counts) / len(total_counts),
                    total_count_max=max(total_maxes),
                    total_count_min=min(total_mins),
                    total_density_avg=sum(total_densities) / len(total_densities),
                    region_stats=json.dumps(region_stats, ensure_ascii=False),
                    sample_count=sum(sample_counts),
                )

                repo.upsert(stat)
                count += 1

    logger.info(f"上卷聚合完成: 写入 {count} 条记录")
    return count


def _align_time_bucket(time_bucket: str, interval: str) -> str:
    """将时间桶对齐到目标间隔"""
    try:
        if time_bucket.endswith("Z"):
            dt = datetime.fromisoformat(time_bucket.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(time_bucket)

        if interval == "5m":
            minute = (dt.minute // 5) * 5
            dt = dt.replace(minute=minute, second=0, microsecond=0)
        elif interval == "1h":
            dt = dt.replace(minute=0, second=0, microsecond=0)
        elif interval == "1d":
            dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)

        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return time_bucket


# 全局聚合器实例
stats_aggregator = StatsAggregator()
