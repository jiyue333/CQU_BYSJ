"""历史数据存储服务

定时保存检测统计数据到数据库，支持数据聚合查询。

Requirements: 6.1
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from sqlalchemy import func, select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_maker
from app.core.redis import get_redis
from app.models.history_stat import HistoryStat
from app.schemas.detection import DetectionResult, RegionStat
from app.schemas.history_stat import (
    AggregatedHistoryResponse,
    AggregatedStat,
    AggregationGranularity,
    HistoryListResponse,
    HistoryStatResponse,
)

logger = structlog.get_logger(__name__)


class HistoryStorageService:
    """历史数据存储服务
    
    职责：
    1. 定时从 Redis Streams 消费检测结果
    2. 保存到 PostgreSQL 数据库
    3. 提供聚合查询功能
    """
    
    RESULT_STREAM_PREFIX = "result:"
    
    # 存储间隔（秒）- 每隔多久保存一次数据
    STORAGE_INTERVAL = 5
    
    # 每次从 Redis 读取的最大消息数
    READ_COUNT = 100
    
    def __init__(self):
        self._running = False
        self._storage_task: Optional[asyncio.Task] = None
        # 记录每个 stream 最后处理的消息 ID
        self._last_ids: dict[str, str] = {}
        # 记录活跃的 stream_ids（从 inference:status 获取）
        self._active_streams: set[str] = set()
    
    async def start(self) -> None:
        """启动历史数据存储服务"""
        if self._running:
            logger.warning("history_storage_already_running")
            return
        
        logger.info("starting_history_storage_service")
        self._running = True
        self._storage_task = asyncio.create_task(self._storage_loop())
        logger.info("history_storage_service_started")
    
    async def stop(self) -> None:
        """停止历史数据存储服务"""
        logger.info("stopping_history_storage_service")
        self._running = False
        
        if self._storage_task:
            self._storage_task.cancel()
            try:
                await self._storage_task
            except asyncio.CancelledError:
                pass
        
        logger.info("history_storage_service_stopped")
    
    async def _storage_loop(self) -> None:
        """存储循环 - 定时从 Redis 读取并保存到数据库"""
        while self._running:
            try:
                await self._process_results()
                await asyncio.sleep(self.STORAGE_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("history_storage_error", error=str(e))
                await asyncio.sleep(self.STORAGE_INTERVAL)
    
    async def _process_results(self) -> None:
        """处理 Redis Streams 中的检测结果"""
        redis_client = await get_redis()
        
        # 获取所有 result:* streams
        # 使用 SCAN 命令查找所有 result: 开头的 keys
        cursor = 0
        stream_keys = []
        while True:
            cursor, keys = await redis_client.scan(
                cursor=cursor,
                match=f"{self.RESULT_STREAM_PREFIX}*",
                count=100
            )
            stream_keys.extend(keys)
            if cursor == 0:
                break
        
        if not stream_keys:
            return
        
        # 构建要读取的 streams
        streams = {}
        for key in stream_keys:
            if isinstance(key, bytes):
                key = key.decode()
            stream_id = key.removeprefix(self.RESULT_STREAM_PREFIX)
            # 使用上次处理的 ID，如果没有则从头开始
            last_id = self._last_ids.get(stream_id, "0")
            streams[key] = last_id
        
        if not streams:
            return
        
        # 读取消息（非阻塞）
        try:
            messages = await redis_client.xread(
                streams,
                count=self.READ_COUNT,
                block=0  # 非阻塞
            )
        except Exception as e:
            logger.error("redis_xread_error", error=str(e))
            return
        
        if not messages:
            return
        
        # 处理消息并保存到数据库
        async with async_session_maker() as session:
            for stream_key, entries in messages:
                if isinstance(stream_key, bytes):
                    stream_key = stream_key.decode()
                stream_id = stream_key.removeprefix(self.RESULT_STREAM_PREFIX)
                
                for msg_id, data in entries:
                    if isinstance(msg_id, bytes):
                        msg_id = msg_id.decode()
                    
                    # 更新 last_id
                    self._last_ids[stream_id] = msg_id
                    
                    # 解析数据
                    result_data = data.get("data") or data.get(b"data", b"{}")
                    if isinstance(result_data, bytes):
                        result_data = result_data.decode()
                    
                    try:
                        result_dict = json.loads(result_data)
                        await self._save_history_stat(session, result_dict)
                    except json.JSONDecodeError as e:
                        logger.warning("invalid_result_json", error=str(e))
                    except Exception as e:
                        logger.error("save_history_stat_error", error=str(e))
            
            await session.commit()
    
    async def _save_history_stat(
        self,
        session: AsyncSession,
        result_dict: dict
    ) -> None:
        """保存单条历史统计记录"""
        stream_id = result_dict.get("stream_id")
        timestamp = result_dict.get("timestamp")
        total_count = result_dict.get("total_count", 0)
        region_stats = result_dict.get("region_stats", [])
        
        if not stream_id or timestamp is None:
            return
        
        # 转换时间戳
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        
        # 创建记录
        history_stat = HistoryStat(
            stream_id=stream_id,
            timestamp=dt,
            total_count=total_count,
            region_stats=region_stats,
        )
        
        session.add(history_stat)
        logger.debug(
            "history_stat_saved",
            stream_id=stream_id,
            timestamp=dt.isoformat(),
            total_count=total_count,
        )
    
    async def save_detection_result(
        self,
        result: DetectionResult
    ) -> None:
        """直接保存检测结果（供外部调用）
        
        Args:
            result: 检测结果
        """
        async with async_session_maker() as session:
            dt = datetime.fromtimestamp(result.timestamp, tz=timezone.utc)
            
            # 转换 region_stats 为 dict 列表
            region_stats_dict = [
                {
                    "region_id": rs.region_id,
                    "region_name": rs.region_name,
                    "count": rs.count,
                    "density": rs.density,
                    "level": rs.level.value,
                }
                for rs in result.region_stats
            ]
            
            history_stat = HistoryStat(
                stream_id=result.stream_id,
                timestamp=dt,
                total_count=result.total_count,
                region_stats=region_stats_dict,
            )
            
            session.add(history_stat)
            await session.commit()



    async def query_history(
        self,
        session: AsyncSession,
        stream_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> HistoryListResponse:
        """查询历史数据（原始数据）
        
        Args:
            session: 数据库会话
            stream_id: 视频流 ID
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回记录数限制
            offset: 偏移量
            
        Returns:
            历史数据列表响应
        """
        # 构建查询条件
        conditions = [HistoryStat.stream_id == stream_id]
        
        if start_time:
            conditions.append(HistoryStat.timestamp >= start_time)
        if end_time:
            conditions.append(HistoryStat.timestamp <= end_time)
        
        # 查询总数
        count_query = select(func.count()).select_from(HistoryStat).where(
            and_(*conditions)
        )
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        # 查询数据
        query = (
            select(HistoryStat)
            .where(and_(*conditions))
            .order_by(HistoryStat.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        
        result = await session.execute(query)
        stats = result.scalars().all()
        
        # 转换为响应格式
        stat_responses = [
            HistoryStatResponse.from_orm_with_conversion(stat)
            for stat in stats
        ]
        
        return HistoryListResponse(
            stats=stat_responses,
            total=total,
            has_more=(offset + len(stats)) < total,
        )
    
    async def query_aggregated_history(
        self,
        session: AsyncSession,
        stream_id: str,
        granularity: AggregationGranularity,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> AggregatedHistoryResponse:
        """查询聚合历史数据
        
        Args:
            session: 数据库会话
            stream_id: 视频流 ID
            granularity: 聚合粒度
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            聚合历史数据响应
        """
        # 设置默认时间范围
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            # 根据粒度设置默认时间范围
            if granularity == AggregationGranularity.MINUTE:
                start_time = end_time - timedelta(hours=1)
            elif granularity == AggregationGranularity.HOUR:
                start_time = end_time - timedelta(days=1)
            else:  # DAY
                start_time = end_time - timedelta(days=30)
        
        # 根据粒度选择时间截断函数
        trunc_func = self._get_trunc_function(granularity)
        
        # 构建聚合查询
        query = text(f"""
            SELECT 
                {trunc_func} as time_bucket,
                AVG(total_count) as avg_count,
                MAX(total_count) as max_count,
                MIN(total_count) as min_count,
                COUNT(*) as sample_count
            FROM history_stats
            WHERE stream_id = :stream_id
                AND timestamp >= :start_time
                AND timestamp <= :end_time
            GROUP BY time_bucket
            ORDER BY time_bucket ASC
        """)
        
        result = await session.execute(
            query,
            {
                "stream_id": stream_id,
                "start_time": start_time,
                "end_time": end_time,
            }
        )
        
        rows = result.fetchall()
        
        # 转换为响应格式
        data = [
            AggregatedStat(
                timestamp=row.time_bucket,
                avg_count=float(row.avg_count),
                max_count=int(row.max_count),
                min_count=int(row.min_count),
                sample_count=int(row.sample_count),
            )
            for row in rows
        ]
        
        return AggregatedHistoryResponse(
            stream_id=stream_id,
            granularity=granularity,
            start_time=start_time,
            end_time=end_time,
            data=data,
        )
    
    def _get_trunc_function(self, granularity: AggregationGranularity) -> str:
        """获取 PostgreSQL 时间截断函数"""
        if granularity == AggregationGranularity.MINUTE:
            return "date_trunc('minute', timestamp)"
        elif granularity == AggregationGranularity.HOUR:
            return "date_trunc('hour', timestamp)"
        else:  # DAY
            return "date_trunc('day', timestamp)"
    
    async def delete_old_data(
        self,
        session: AsyncSession,
        retention_days: int = 30,
    ) -> int:
        """删除过期数据
        
        Args:
            session: 数据库会话
            retention_days: 数据保留天数
            
        Returns:
            删除的记录数
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=retention_days)
        
        # 使用原生 SQL 删除以获取删除数量
        query = text("""
            DELETE FROM history_stats
            WHERE timestamp < :cutoff_time
        """)
        
        result = await session.execute(query, {"cutoff_time": cutoff_time})
        await session.commit()
        
        deleted_count = result.rowcount
        if deleted_count > 0:
            logger.info(
                "old_history_data_deleted",
                deleted_count=deleted_count,
                cutoff_time=cutoff_time.isoformat(),
            )
        
        return deleted_count


# 全局历史存储服务实例
_history_storage_service: Optional[HistoryStorageService] = None


def get_history_storage_service() -> HistoryStorageService:
    """获取历史存储服务（单例）"""
    global _history_storage_service
    if _history_storage_service is None:
        _history_storage_service = HistoryStorageService()
    return _history_storage_service
