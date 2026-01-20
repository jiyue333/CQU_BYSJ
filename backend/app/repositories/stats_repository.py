"""
聚合统计 Repository

StatsAggregated 的数据库操作
"""

import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.stats_aggregated import StatsAggregated, RegionStatsData


class StatsRepository:
    """统计仓储"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, stat: StatsAggregated) -> StatsAggregated:
        """创建统计记录"""
        self.db.add(stat)
        self.db.commit()
        self.db.refresh(stat)
        return stat

    def create_with_region_stats(
        self,
        source_id: str,
        time_bucket: str,
        interval_type: str,
        total_count_avg: float,
        total_count_max: int,
        total_count_min: int,
        total_density_avg: float,
        region_stats: dict[str, dict],
        crowd_index_avg: float,
        sample_count: int,
    ) -> StatsAggregated:
        """创建包含区域统计的记录"""
        stat = StatsAggregated(
            source_id=source_id,
            time_bucket=time_bucket,
            interval_type=interval_type,
            total_count_avg=total_count_avg,
            total_count_max=total_count_max,
            total_count_min=total_count_min,
            total_density_avg=total_density_avg,
            region_stats=json.dumps(region_stats, ensure_ascii=False),
            crowd_index_avg=crowd_index_avg,
            sample_count=sample_count,
        )
        return self.create(stat)

    def bulk_create(self, stats: list[StatsAggregated]) -> list[StatsAggregated]:
        """批量创建统计记录"""
        self.db.add_all(stats)
        self.db.commit()
        for stat in stats:
            self.db.refresh(stat)
        return stats

    def get_by_id(self, stat_id: int) -> Optional[StatsAggregated]:
        """根据 ID 获取统计"""
        return self.db.get(StatsAggregated, stat_id)

    def get_by_time_range(
        self,
        source_id: str,
        interval_type: str,
        time_from: str,
        time_to: str,
        region_id: Optional[str] = None,
    ) -> list[StatsAggregated]:
        """
        按时间范围查询统计数据

        Args:
            source_id: 数据源 ID
            interval_type: 聚合粒度 (1m/5m/1h/1d)
            time_from: 开始时间
            time_to: 结束时间
            region_id: 可选，筛选包含指定区域的记录
        """
        stmt = (
            select(StatsAggregated)
            .where(
                StatsAggregated.source_id == source_id,
                StatsAggregated.interval_type == interval_type,
                StatsAggregated.time_bucket >= time_from,
                StatsAggregated.time_bucket <= time_to,
            )
            .order_by(StatsAggregated.time_bucket)
        )
        results = list(self.db.scalars(stmt).all())

        # 如果指定了区域 ID，过滤包含该区域的记录
        if region_id:
            results = [
                s for s in results
                if region_id in s.get_region_stats_dict()
            ]

        return results

    def get_region_stats_by_time_range(
        self,
        source_id: str,
        interval_type: str,
        time_from: str,
        time_to: str,
        region_id: str,
    ) -> list[dict]:
        """
        获取指定区域在时间范围内的统计数据

        Args:
            region_id: 区域 ID

        Returns:
            [{"time": "2024-01-01T10:00:00Z", "name": "前区", "avg": 50, "max": 65, "min": 40, "crowd_index": 0.8}, ...]
        """
        stats = self.get_by_time_range(source_id, interval_type, time_from, time_to)
        result = []
        for stat in stats:
            region_data = stat.get_region_stats_dict()
            if region_id in region_data:
                r = region_data[region_id]
                result.append({
                    "time": stat.time_bucket,
                    "name": r.name,
                    "avg": r.avg,
                    "max": r.max,
                    "min": r.min,
                    "crowd_index": r.crowd_index,
                })
        return result

    def get_latest(
        self,
        source_id: str,
        interval_type: str,
        limit: int = 60,
    ) -> list[StatsAggregated]:
        """获取最新的统计数据"""
        stmt = (
            select(StatsAggregated)
            .where(
                StatsAggregated.source_id == source_id,
                StatsAggregated.interval_type == interval_type,
            )
            .order_by(StatsAggregated.time_bucket.desc())
            .limit(limit)
        )
        # 按时间正序返回
        return list(reversed(list(self.db.scalars(stmt).all())))

    def upsert(self, stat: StatsAggregated) -> StatsAggregated:
        """插入或更新统计记录（基于唯一约束）"""
        existing = self.get_by_bucket(stat.source_id, stat.interval_type, stat.time_bucket)
        if existing:
            # 更新现有记录
            existing.total_count_avg = stat.total_count_avg
            existing.total_count_max = stat.total_count_max
            existing.total_count_min = stat.total_count_min
            existing.total_density_avg = stat.total_density_avg
            existing.region_stats = stat.region_stats
            existing.crowd_index_avg = stat.crowd_index_avg
            existing.sample_count = stat.sample_count
            self.db.commit()
            self.db.refresh(existing)
            return existing
        return self.create(stat)

    def get_by_bucket(
        self,
        source_id: str,
        interval_type: str,
        time_bucket: str,
    ) -> Optional[StatsAggregated]:
        """根据时间桶获取统计"""
        stmt = select(StatsAggregated).where(
            StatsAggregated.source_id == source_id,
            StatsAggregated.interval_type == interval_type,
            StatsAggregated.time_bucket == time_bucket,
        )
        return self.db.scalars(stmt).first()

    def delete_old_stats(self, source_id: str, interval_type: str, before: str) -> int:
        """删除旧统计数据"""
        stmt = select(StatsAggregated).where(
            StatsAggregated.source_id == source_id,
            StatsAggregated.interval_type == interval_type,
            StatsAggregated.time_bucket < before,
        )
        stats = list(self.db.scalars(stmt).all())
        count = len(stats)
        for stat in stats:
            self.db.delete(stat)
        self.db.commit()
        return count

    def delete_by_source_id(self, source_id: str) -> int:
        """删除数据源的所有统计"""
        stmt = select(StatsAggregated).where(StatsAggregated.source_id == source_id)
        stats = list(self.db.scalars(stmt).all())
        count = len(stats)
        for stat in stats:
            self.db.delete(stat)
        self.db.commit()
        return count
