"""
聚合统计 Repository

StatsAggregated 的数据库操作
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.stats_aggregated import StatsAggregated


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
    ) -> list[StatsAggregated]:
        """按时间范围查询统计数据"""
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
        return list(self.db.scalars(stmt).all())

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
